import json, sys, time
sys.path.insert(0, "src")
from provideriq import extract as E
from provideriq.pipeline import load_pages
from provideriq.validate import validate, status_for

KEYS = E.SCHEMA_KEYS
V1 = "Extract the clinic details from this page and give them as JSON:\n\n{text}"
V2 = ("Extract details about one Australian healthcare provider from the text below. "
      "Return ONLY a JSON object with exactly these keys: " + ", ".join(KEYS) + ". "
      "state is one of NSW, VIC, QLD, SA, WA, TAS, NT, ACT. services is a list.\n\nTEXT:\n{text}")
V3 = E.PROMPT_V3.format(keys=", ".join(KEYS), text="{text}")
PROMPTS = {"v1 (basic)": V1, "v2 (schema)": V2, "v3 (grounded)": V3}

source = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
pages = load_pages(source)
rows = []
for name, tmpl in PROMPTS.items():
    s = dict(json=0, schema=0, ungrounded=0, verified=0, score=0, n=0)
    for page in pages:
        s["n"] += 1
        prompt = tmpl.replace("{text}", page.text[:12000])
        try:
            raw = E._call_gemini(prompt)
            data = E._parse_json(raw)
            if isinstance(data, list) and data:
                data = data[0]
            s["json"] += 1
        except Exception as e:
            print("call failed:", str(e)[:100])
            continue
        finally:
            time.sleep(2)
        if all(k in data for k in KEYS):
            s["schema"] += 1
        rec = {k: data.get(k) for k in KEYS}
        rec["services"] = rec.get("services") or []
        if not isinstance(rec["services"], list):
            rec["services"] = []
        rec["website"] = rec.get("website") or page.source
        try:
            out = validate(rec, page.text)
        except Exception:
            continue
        s["ungrounded"] += sum(f.startswith("ungrounded") for f in out["flags"])
        s["verified"] += status_for(out) == "verified"
        s["score"] += out["score"]
    rows.append((name, s))

lines = ["| Prompt | Valid JSON | Exact schema | Ungrounded fields | Verified | Avg score |", "|---|---|---|---|---|---|"]
for name, s in rows:
    n = s["n"]
    lines.append(f"| {name} | {s['json']}/{n} | {s['schema']}/{n} | {s['ungrounded']} | {s['verified']}/{n} | {round(s['score']/max(1,n),1)} |")
text = "\n".join(lines)
print("\n" + text)
open("prompt_eval_results.md", "w", encoding="utf-8").write(text + "\n")
print("\nSaved to prompt_eval_results.md")
