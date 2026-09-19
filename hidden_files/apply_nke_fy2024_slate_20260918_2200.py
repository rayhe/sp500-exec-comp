#!/usr/bin/env python3
"""NKE FY2024 anchor-slate completion (2026-09-18 22:00 PT batch).

Nike's anchor fiscal_year is 2024 but its FY2024 NEO slate was incomplete:
only Matthew Friend's FY2024 row was stored (parsed from the FY2026 proxy's
SCT, which carries FY2024 rows only for still-NEOs). The FY2025 DEF 14A
(accession 0000320187-25-000048, filed 2025-07-17, re-fetched from EDGAR
2026-09-18) Summary Compensation Table gives the full FY2024 NEO slate;
restores the 3 missing rows filing-verbatim and re-anchors the company
aggregates to the full FY2024 slate.

New rows (all components foot the printed total exactly, delta $0):
  John Donahoe II  2024  Former President and Chief Executive Officer
      1,557,692 / 0 / 12,400,986 / 6,836,722 / 1,950,000 / 0 / 6,439,301 / 29,184,701
  Craig Williams   2024  Executive Vice President, Chief Commercial Officer
      1,272,115 / 0 / 5,221,473 / 2,878,629 / 975,000 / 0 / 16,500 / 10,363,717
  Heidi O'Neill    2024  Former President, Consumer, Product & Brand
      1,298,077 / 0 / 5,221,473 / 2,878,629 / 975,000 / 0 / 26,208 / 10,399,387

Metadata: NKE neo_count 1->4, total_neo_compensation 10,390,510->60,338,315.
Headline: 6,863->6,866 records, verified_total 6,835->6,838 (99.6%).
"""
import json
import os
import re
import shutil
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..")
JSON_PATH = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(
    HERE, "compensation_backup_20260918_2200_pre_nkefy2024.json"
)

NEW_ROWS = [
    {
        "name": "John Donahoe II",
        "title": "Former President and Chief Executive Officer",
        "year": 2024,
        "salary": 1557692,
        "bonus": 0,
        "stock_awards": 12400986,
        "option_awards": 6836722,
        "non_equity_incentive": 1950000,
        "pension_nqdc": 0,
        "all_other": 6439301,
        "total": 29184701,
        "_total_source": "def14a_verified_20260918",
        "_parse_note": "2026-09-18: restored from Nike FY2025 DEF 14A SCT "
        "(acc. 0000320187-25-000048, filed 2025-07-17, re-fetched from EDGAR). "
        "Filing total $29,184,701 retained verbatim; components foot exactly. "
        "All Other $6,439,301 includes non-competition agreement payout (fn 6).",
    },
    {
        "name": "Craig Williams",
        "title": "Executive Vice President, Chief Commercial Officer",
        "year": 2024,
        "salary": 1272115,
        "bonus": 0,
        "stock_awards": 5221473,
        "option_awards": 2878629,
        "non_equity_incentive": 975000,
        "pension_nqdc": 0,
        "all_other": 16500,
        "total": 10363717,
        "_total_source": "def14a_verified_20260918",
        "_parse_note": "2026-09-18: restored from Nike FY2025 DEF 14A SCT "
        "(acc. 0000320187-25-000048, filed 2025-07-17, re-fetched from EDGAR). "
        "Filing total $10,363,717 retained verbatim; components foot exactly.",
    },
    {
        "name": "Heidi O'Neill",
        "title": "Former President, Consumer, Product & Brand",
        "year": 2024,
        "salary": 1298077,
        "bonus": 0,
        "stock_awards": 5221473,
        "option_awards": 2878629,
        "non_equity_incentive": 975000,
        "pension_nqdc": 0,
        "all_other": 26208,
        "total": 10399387,
        "_total_source": "def14a_verified_20260918",
        "_parse_note": "2026-09-18: restored from Nike FY2025 DEF 14A SCT "
        "(acc. 0000320187-25-000048, filed 2025-07-17, re-fetched from EDGAR). "
        "Filing total $10,399,387 retained verbatim; components foot exactly.",
    },
]

COMP_KEYS = [
    "salary", "bonus", "stock_awards", "option_awards",
    "non_equity_incentive", "pension_nqdc", "pension_change", "all_other",
]


def main():
    shutil.copy(JSON_PATH, BACKUP)
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    companies = data["companies"]
    nke = next(c for c in companies if c["ticker"] == "NKE")

    # 1. sanity: the 3 rows must not already exist; components must foot
    existing = {(e["name"], e["year"]) for e in nke.get("executives", [])}
    for r in NEW_ROWS:
        assert (r["name"], r["year"]) not in existing, f"already stored: {r}"
        s = sum(r.get(k) or 0 for k in COMP_KEYS)
        assert s == r["total"], f"{r['name']}: components {s} != total {r['total']}"

    # 2. add rows (insertion order: by year, then SCT order of the filing)
    anchor = [e for e in nke["executives"] if e["year"] == 2024]
    other = [e for e in nke["executives"] if e["year"] != 2024]
    # filing SCT order for FY2024 slate: Donahoe, Friend, Williams, O'Neill
    nke["executives"] = NEW_ROWS + anchor + other

    # 3. re-anchor company aggregates to FY2024 slate
    fy = nke["fiscal_year"]
    assert fy == 2024
    slate = [e for e in nke["executives"] if e["year"] == fy]
    assert len(slate) == 4
    nke["neo_count"] = len(slate)
    nke["total_neo_compensation"] = sum(e["total"] for e in slate)
    print("NKE neo_count:", nke["neo_count"],
          "total_neo_compensation:", f"{nke['total_neo_compensation']:,}")

    # 4. metadata recount sync
    meta = data["metadata"]
    n = sum(len(c.get("executives", [])) for c in companies)
    assert n == 6866, n
    meta["total_neo_records"] = n
    meta["total_executives"] = n
    title_gaps = sum(
        1 for c in companies for e in c.get("executives", []) if not e.get("title")
    )
    meta["title_coverage"] = f"{n - title_gaps}/{n}"
    meta["description"] = meta["description"].replace("6863 NEO records",
                                                     "6866 NEO records")
    for block_name in ("data_quality", "data_quality_detailed"):
        block = meta.get(block_name)
        if block is not None and "def14a_verified_20260918" in block:
            block["def14a_verified_20260918"] += 3
            block["verified_total"] += 3
    dq = meta["data_quality"]
    print("verified_total:", dq["verified_total"],
          "def14a_verified_20260918:", dq["def14a_verified_20260918"])

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
        f.write("\n")

    # 5. static-copy sync (README.md / index.html / js/app.js)
    vt, total = dq["verified_total"], n
    pct = f"{vt / total * 100:.1f}%"
    rounding = dq.get("rounding", 0)
    recomputed = dq.get("recomputed", 0)
    mismatch = dq.get("component_mismatch")

    edits = [
        (os.path.join(REPO, "README.md"), [
            ("(6,835 of 6,863 records, 28 filing-side component mismatches",
             f"({vt:,} of {total:,} records, {mismatch} filing-side component mismatches"),
        ]),
        (os.path.join(REPO, "index.html"), [
            ("6,863 Named Executive Officer records",
             f"{total:,} Named Executive Officer records"),
        ]),
        (os.path.join(REPO, "js", "app.js"), [
            ("6,835 of 6,863 NEO rows verified (99.6%)",
             f"{vt:,} of {total:,} NEO rows verified ({pct})"),
        ]),
    ]
    for path, pairs in edits:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for old, new in pairs:
            assert old in text, f"pattern missing in {path}: {old!r}"
            text = text.replace(old, new, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    print("static copies synced:", vt, "/", total, pct)

    # 6. README audit-trail append (convention: each batch extends line 11)
    audit = ("; 2026-09-18 22:00 PT batch: NKE FY2024 anchor-slate completion "
             "(3 rows: Donahoe II $29.18M, Williams $10.36M, O'Neill $10.40M, "
             "filing-verbatim from FY2025 DEF 14A SCT acc. 0000320187-25-000048 "
             "re-fetched from EDGAR, all foot exactly); neo_count 1->4, "
             "total_neo_compensation $10.39M->$60.34M re-anchored; headline "
             f"buckets {pct} ({vt:,}/{total:,}).")
    with open(os.path.join(REPO, "README.md"), encoding="utf-8") as f:
        lines = f.readlines()
    assert lines[10].rstrip("\n").endswith(")."), "audit-trail anchor lost"
    lines[10] = lines[10].rstrip("\n") + audit + "\n"
    with open(os.path.join(REPO, "README.md"), "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("README audit trail appended")


if __name__ == "__main__":
    main()
