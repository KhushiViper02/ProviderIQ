"""Write Excel (3 review sheets + summary), CSV and JSON (for the dashboard)."""
import csv, json, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

COLS = ["name", "type", "address", "suburb", "state", "postcode", "phone", "email",
        "website", "services", "score", "status", "flags", "duplicate_of", "source_url"]


def _row(r):
    out = []
    for c in COLS:
        v = r.get(c, "")
        out.append("; ".join(v) if isinstance(v, list) else (v or ""))
    return out


def export_all(records, summary, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    json.dump({"summary": summary, "records": records},
              open(os.path.join(out_dir, "providers.json"), "w"), indent=2)
    with open(os.path.join(out_dir, "providers.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(COLS)
        for r in records: w.writerow(_row(r))

    wb = Workbook()
    ws = wb.active; ws.title = "Summary"
    ws.append(["Extractor", summary["extractor"]]); ws.append(["Total records", summary["total"]])
    ws.append(["Average quality score", summary["avg_score"]]); ws.append([])
    ws.append(["Status", "Count"])
    for k, v in summary["by_status"].items(): ws.append([k, v])
    ws.append([]); ws.append(["Flag", "Count"])
    for k, v in summary["flag_counts"].items(): ws.append([k, v])

    fills = {"verified": "D5EDE9", "needs_review": "FBEFD2", "rejected": "F6D5CF"}
    for status, title in (("verified", "Verified"), ("needs_review", "Needs review"), ("rejected", "Rejected")):
        sh = wb.create_sheet(title); sh.append(COLS)
        for c in sh[1]: c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor=fills[status])
        for r in records:
            if r["status"] == status: sh.append(_row(r))
        for i, c in enumerate(COLS, 1): sh.column_dimensions[get_column_letter(i)].width = 22
        sh.freeze_panes = "A2"
    wb.save(os.path.join(out_dir, "providers.xlsx"))
