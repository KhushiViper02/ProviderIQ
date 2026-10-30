"""End-to-end run: load pages -> extract -> validate -> dedupe -> export."""
import argparse, glob, json, os, re
from collections import Counter
from .textutil import parse_html
from .extract import extract
from .validate import validate, status_for, find_duplicates
from .export import export_all


def load_pages(source_dir):
    pages = []
    for path in sorted(glob.glob(os.path.join(source_dir, "*.html"))):
        html = open(path, encoding="utf-8").read()
        m = re.match(r"<!-- source: (\S+) -->", html)
        pages.append(parse_html(html, m.group(1) if m else path))
    return pages


def run(source="samples", extractor="mock", out_dir="outputs"):
    ok, failed = [], []
    for page in load_pages(source):
        try:
            raw = extract(page, extractor)
        except Exception as e:  # one bad page must not stop the whole run
            print('extraction failed:', str(e)[:300])
            print('extraction failed:', str(e)[:300])
            failed.append({"name": page.h1 or page.source, "score": 0, "status": "rejected",
                           "flags": [f"extraction_error:{e.__class__.__name__}"],
                           "source_url": page.source, "services": []})
            continue
        rec = validate(raw, page.text)
        rec["source_url"] = page.source
        ok.append(rec)
    ok.sort(key=lambda r: -r["score"])  # keep the highest-quality copy as the original
    find_duplicates(ok)
    for r in ok:
        r["status"] = status_for(r)
    records = ok + failed
    summary = {
        "extractor": extractor, "total": len(records),
        "by_status": dict(Counter(r["status"] for r in records)),
        "avg_score": round(sum(r["score"] for r in records) / max(1, len(records)), 1),
        "flag_counts": dict(Counter(f for r in records for f in r["flags"])),
    }
    export_all(records, summary, out_dir)
    return records, summary


def main():
    ap = argparse.ArgumentParser(description="ProviderIQ pipeline")
    ap.add_argument("--source", default=os.getenv("SOURCE", "samples"), help="folder of .html pages")
    ap.add_argument("--extractor", default=os.getenv("EXTRACTOR", "mock"),
                    choices=["mock", "mock-llm", "gemini", "anthropic"])
    ap.add_argument("--out", default="outputs")
    a = ap.parse_args()
    _, s = run(a.source, a.extractor, a.out)
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
