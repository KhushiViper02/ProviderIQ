"""Verification layer: format checks, postcode/state consistency, grounding
(is every AI-extracted value actually present in the source page?), dedupe, scoring."""
import re
from difflib import SequenceMatcher

PHONE_RE = re.compile(
    r"(?:\(0[2378]\)|0[2378])[\s-]?\d{4}[\s-]?\d{4}|04\d{2}[\s-]?\d{3}[\s-]?\d{3}"
    r"|1[38]00[\s-]?\d{3}[\s-]?\d{3}|13[\s-]?\d{2}[\s-]?\d{2}"
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
STATES = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}

# Australia Post postcode ranges (inclusive)
_RANGES = {
    "NSW": [(1000, 1999), (2000, 2599), (2619, 2898), (2921, 2999)],
    "ACT": [(200, 299), (2600, 2618), (2900, 2920)],
    "VIC": [(3000, 3999), (8000, 8999)],
    "QLD": [(4000, 4999), (9000, 9999)],
    "SA": [(5000, 5799)],
    "WA": [(6000, 6797)],
    "TAS": [(7000, 7799)],
    "NT": [(800, 999)],
}


def digits(s):
    return re.sub(r"\D", "", s or "")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def normalize_phone(p):
    d = digits(p)
    if not d:
        return ""
    if len(d) == 10 and d[0] == "0":
        return f"{d[:2]} {d[2:6]} {d[6:]}" if d[1] in "2378" else f"{d[:4]} {d[4:7]} {d[7:]}"
    if len(d) == 10 and d[:4] in ("1300", "1800"):
        return f"{d[:4]} {d[4:7]} {d[7:]}"
    if len(d) == 6 and d[:2] == "13":
        return f"{d[:2]} {d[2:4]} {d[4:]}"
    return ""  # not a valid Australian number


def valid_email(e):
    return bool(e) and bool(EMAIL_RE.fullmatch(e.strip()))


def postcode_state_ok(state, postcode):
    try:
        pc = int(postcode)
    except (TypeError, ValueError):
        return None  # unknown
    if state not in _RANGES:
        return None
    return any(lo <= pc <= hi for lo, hi in _RANGES[state])


def grounded(field, value, source_text):
    """True if the value can be found in the page text (guards against hallucination)."""
    if not value:
        return True
    if field == "phone":
        found = {digits(m.group(0)) for m in PHONE_RE.finditer(source_text)}
        return digits(value) in found
    if field == "postcode":
        return re.search(rf"\b{re.escape(str(value))}\b", source_text) is not None
    if field in ("email", "website"):
        return value.lower() in source_text.lower() or field == "website"
    return norm(value) in norm(source_text)


def validate(rec, source_text):
    """Return (record with score/status/flags)."""
    flags = []
    score = 0
    rec = dict(rec)
    raw_phone = rec.get("phone") or ""
    rec["phone"] = normalize_phone(raw_phone)
    if raw_phone and not rec["phone"]:
        flags.append("invalid_phone_format")

    # completeness (max 100)
    score += 20 if rec.get("name") else 0
    score += 20 if rec.get("phone") else 0
    addr_parts = [rec.get("address"), rec.get("suburb"), rec.get("state"), rec.get("postcode")]
    score += int(20 * sum(bool(x) for x in addr_parts) / 4)
    score += 10 if rec.get("email") else 0
    score += 10 if rec.get("website") else 0
    score += 10 if rec.get("type") else 0
    score += 10 if rec.get("services") else 0

    # missing-field flags
    for f in ("name", "phone", "address", "state", "postcode"):
        if not rec.get(f):
            flags.append(f"missing_{f}")

    # format checks
    if rec.get("email") and not valid_email(rec["email"]):
        flags.append("invalid_email"); score -= 10
    if rec.get("state") and rec["state"] not in STATES:
        flags.append("invalid_state"); score -= 10
    ok = postcode_state_ok(rec.get("state"), rec.get("postcode"))
    if ok is False:
        flags.append("postcode_state_mismatch"); score -= 25

    # grounding: every AI-extracted value must appear in the source page
    for f in ("name", "phone", "email", "suburb", "postcode"):
        if rec.get(f) and not grounded(f, rec[f], source_text):
            flags.append(f"ungrounded_{f}"); score -= 30
    bad = [s for s in rec.get("services", []) if not grounded("services", s, source_text)]
    if bad:
        flags.append("ungrounded_services"); score -= 10
        rec["services"] = [s for s in rec["services"] if s not in bad]

    rec["score"] = max(0, min(100, score))
    rec["flags"] = flags
    return rec


def status_for(rec):
    hard = {"postcode_state_mismatch", "invalid_state"}
    if rec["score"] < 50:
        return "rejected"
    if rec["score"] >= 80 and not (set(rec["flags"]) & hard) \
            and not any(f.startswith("ungrounded") for f in rec["flags"]) \
            and not rec.get("duplicate_of"):
        return "verified"
    return "needs_review"


def find_duplicates(records, threshold=0.88):
    """Mark later records that look like an earlier one (same postcode, similar name)."""
    for i, a in enumerate(records):
        if a.get("duplicate_of"):
            continue
        for b in records[i + 1:]:
            if b.get("duplicate_of") or a.get("postcode") != b.get("postcode"):
                continue
            if SequenceMatcher(None, norm(a["name"]), norm(b["name"])).ratio() >= threshold:
                b["duplicate_of"] = a["name"]
                b.setdefault("flags", []).append("possible_duplicate")
    return records
