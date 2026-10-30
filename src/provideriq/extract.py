"""Extraction: turn a page's text into a structured provider record.

Extractors
  mock      regex/heuristics only, no API key (offline demo + baseline)
  mock-llm  heuristics PLUS deliberately injected hallucinations, to show the
            verification layer catching them (clearly a simulation)
  gemini    Google Gemini REST API
  anthropic Anthropic Messages REST API
"""
import json, os, re, time, time
import requests
from .validate import PHONE_RE, EMAIL_RE

SCHEMA_KEYS = ["name", "type", "address", "suburb", "state", "postcode",
               "phone", "email", "website", "services"]

# ---- Prompt v3 (see docs/PROMPTS.md for v1 and v2 and why they changed) ----
PROMPT_V3 = """You extract structured data about ONE Australian healthcare provider
from the page text below.

Rules:
1. Use ONLY information present in the text. Never guess or use outside knowledge.
2. If a field is not in the text, return null (services: empty list). Do not invent.
3. state must be one of NSW, VIC, QLD, SA, WA, TAS, NT, ACT. postcode is 4 digits.
4. type is one of: hospital, general practice, specialist, dental, allied health, other.
5. phone: copy the main published number exactly as written.
6. services: up to 8 short items, each copied or closely taken from the text.
7. Return ONLY a JSON object with exactly these keys, no markdown, no commentary:
{keys}

PAGE TEXT:
\"\"\"
{text}
\"\"\"
"""

ADDR_RE = re.compile(
    r"(\d+[A-Za-z]?(?:[-/]\d+)?\s[^,\n]{3,50}),\s*([A-Za-z' ]{3,30})\s+"
    r"(NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\s+(\d{4})")


def classify(name, text):
    n = (name or "").lower()
    t = text.lower()
    if "hospital" in n: return "hospital"
    if "dental" in n or "dentist" in n: return "dental"
    if any(k in n for k in ("physio", "allied", "podiatry")): return "allied health"
    if any(k in n for k in ("medical", "gp", "family practice", "general practice", "clinic")):
        return "general practice"
    if "specialist" in t: return "specialist"
    return "other"


def extract_heuristic(page):
    t = page.text
    name = page.h1 or re.split(r"\s[|\-–]\s", page.title)[0].strip()
    phone = next((m.group(0) for m in PHONE_RE.finditer(t)), None)
    email = next((m.group(0) for m in EMAIL_RE.finditer(t)), None)
    addr = ADDR_RE.search(t)
    rec = dict.fromkeys(SCHEMA_KEYS)
    rec.update(name=name or None, type=classify(name, t), phone=phone, email=email,
               website=page.source or None, services=[])
    if addr:
        rec.update(address=addr.group(1).strip(), suburb=addr.group(2).strip(),
                   state=addr.group(3), postcode=addr.group(4))
    return rec


# Simulated model errors, keyed by sample file stem (for the demo only)
MOCK_HALLUCINATIONS = {
    "northgate-gp": {"phone": "02 5550 9999", "services": ["Travel vaccinations", "Sleep studies"]},
}


def extract_mock_llm(page):
    rec = extract_heuristic(page)
    stem = os.path.splitext(os.path.basename(page.source or ""))[0]
    rec.update(MOCK_HALLUCINATIONS.get(stem, {}))
    return rec


def _parse_json(raw):
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0) if m else raw)


_MODELS = None


def _gemini_models():
    global _MODELS
    if _MODELS is None:
        key = os.environ["GEMINI_API_KEY"]
        names = []
        first = os.getenv("GEMINI_MODEL")
        if first:
            names.append(first)
        try:
            r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                             params={"key": key, "pageSize": 200}, timeout=30)
            for m in r.json().get("models", []):
                n = m["name"].replace("models/", "")
                if ("generateContent" in m.get("supportedGenerationMethods", [])
                        and "flash" in n and n not in names
                        and not any(x in n for x in ("image", "tts", "live", "audio", "embed", "exp"))):
                    names.append(n)
        except Exception:
            pass
        _MODELS = names or ["gemini-3.8-flash"]
    return _MODELS


def _call_gemini(prompt):
    key = os.environ["GEMINI_API_KEY"]
    last = ""
    for _round in range(2):
        for model in _gemini_models()[:6]:
            try:
                r = requests.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
                    params={"key": key}, timeout=40,
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": 0}})
            except requests.RequestException as e:
                last = model + ": " + str(e)[:80]
                print("model failed:", last)
                continue
            if r.status_code == 200:
                try:
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    last = model + ": empty reply"
                    print("model failed:", last)
                    continue
                print("model used:", model)
                return text
            last = model + " " + str(r.status_code)
            print("model failed:", last)
        time.sleep(15)
    raise RuntimeError("all models failed. Last: " + last)


def _call_anthropic(prompt):
    r = requests.post(
        "https://api.anthropic.com/v1/messages", timeout=60,
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": os.environ["ANTHROPIC_MODEL"], "max_tokens": 1000, "temperature": 0,
              "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status()
    return r.json()["content"][0]["text"]


def extract_llm(page, provider):
    call = {"gemini": _call_gemini, "anthropic": _call_anthropic}[provider]
    prompt = PROMPT_V3.format(keys=", ".join(SCHEMA_KEYS), text=page.text[:12000])
    data = None
    for _attempt in range(2):  # one repair retry if the JSON is malformed
        raw = call(prompt)
        try:
            data = _parse_json(raw)
            break
        except (json.JSONDecodeError, ValueError):
            prompt += "\n\nYour last reply was not valid JSON. Return ONLY the JSON object."
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError("model did not return a valid JSON object")
    rec = {k: data.get(k) for k in SCHEMA_KEYS}
    rec["services"] = rec.get("services") or []
    rec["website"] = rec.get("website") or page.source
    return rec


def extract(page, extractor):
    if extractor == "mock":
        return extract_heuristic(page)
    if extractor == "mock-llm":
        return extract_mock_llm(page)
    return extract_llm(page, extractor)
