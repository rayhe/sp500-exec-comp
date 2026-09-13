#!/usr/bin/env python3
"""2026-09-13 10:00 PT primary-source DQ batch.

1) APH (Amphenol, 2026 DEF 14A filed 2026-04-08, SCT L2590-2641; pay ratio
   L3750-3759): the 2025/2023 SCT rows for Lampo, Walter, Doherty, Straub were
   parsed from the All Other Compensation subtable (salary = life-insurance
   imputed comp, total = all-other total) and the 09-04 "fix" cemented them as
   "verified". All 7 corrupted rows are re-extracted from the SCT verbatim.
   Also repairs the stock/option column swap on all 14 APH rows: Amphenol
   grants options only (SCT Stock Awards column = n/a), so the grant values
   move stock_awards -> option_awards. The 09-04 repair also cemented the
   filing's own Lampo 2023 arithmetic error (components sum 3,778,717 vs
   printed total 3,715,717, delta $63,000 filer-side) under "verified"; that
   row is now honestly labeled component_mismatch with the delta documented
   in-record.
2) LHX (2025 DEF 14A filed 2025-03-07, Fiscal 2024 SCT): 4 org-label rows
   renamed to the real NEOs (Kenneth Bedingfield CFO, Samir Mehta President
   Communication Systems) and the dropped Jonathan Rambeau 2023 row restored.
3) EG review-queue item closed with no data change: Andrade 2025 stub
   ($48,077 salary / $54,089 total) confirmed genuine partial-year row per the
   2026-proxy CD&A (Former President and CEO, left 2025-01-05).

Net: 6782 -> 6783 records (Rambeau +1); verified bucket net unchanged
(6336 - 1 Lampo 2023 out, + 1 Rambeau in); component_mismatch 20 -> 21.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "data", "compensation.json")

FIX_NOTE_APH = (
    "2026-09-13 10:00 PT: re-extracted from the APH 2026 DEF 14A Summary "
    "Compensation Table (filed 2026-04-08) verbatim; supersedes the 2026-09-04 "
    "note. The prior parse had read the All Other Compensation footnote table "
    "as SCT rows (salary = life-insurance imputed comp, total = all-other "
    "total) on the 2025/2023 rows, and mislabeled the option grants as "
    "stock_awards (Amphenol grants options only; the SCT Stock Awards column "
    "is n/a)."
)

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

companies = {c["ticker"]: c for c in data["companies"]}

# ---------------------------------------------------------------- APH rows
# Exact SCT rows: (name, title, year, salary, bonus, stock, options, non-eq,
#                  pension, all_other, total)
APH_ROWS = [
    ("R.A. Norwitt", "President & Chief Executive Officer", 2025,
     1565000, 0, 0, 14649006, 5634000, 10200, 493082, 22351288),
    ("R.A. Norwitt", "President & Chief Executive Officer", 2024,
     1510000, 0, 0, 10460894, 5005650, 0, 180206, 17156750),
    ("R.A. Norwitt", "President & Chief Executive Officer", 2023,
     1455000, 0, 0, 9098783, 0, 8800, 382124, 10944707),
    ("C.A. Lampo", "Executive Vice President & Chief Financial Officer", 2025,
     730000, 0, 0, 4195103, 1460000, 3000, 137924, 6526027),
    ("C.A. Lampo", "Executive Vice President & Chief Financial Officer", 2024,
     705000, 0, 0, 3355232, 1168538, 0, 54068, 5282838),
    ("C.A. Lampo", "Executive Vice President & Chief Financial Officer", 2023,
     680000, 0, 0, 2981331, 0, 2600, 114786, 3715717),
    ("L. Walter", "President, Harsh Environment Solutions Division", 2025,
     815000, 0, 0, 3570760, 1304000, 2100, 139680, 5831540),
    ("L. Walter", "President, Harsh Environment Solutions Division", 2024,
     785000, 0, 0, 2855866, 1000875, 0, 140769, 4782510),
    ("L. Walter", "President, Harsh Environment Solutions Division", 2023,
     755000, 0, 0, 3484008, 1047563, 24200, 143566, 5454337),
    ("W.J. Doherty", "President, Communications Solutions Division", 2025,
     750000, 0, 0, 3570760, 1200000, 0, 136809, 5657569),
    ("W.J. Doherty", "President, Communications Solutions Division", 2024,
     715000, 0, 0, 2855866, 1072500, 0, 58680, 4702046),
    ("W.J. Doherty", "President, Communications Solutions Division", 2023,
     680000, 0, 0, 3484008, 0, 0, 120660, 4284668),
    ("P.J. Straub", "President, Interconnect and Sensor Systems Division", 2025,
     600000, 0, 0, 3570760, 912000, 0, 87986, 5170746),
    ("P.J. Straub", "President, Interconnect and Sensor Systems Division", 2024,
     575000, 0, 0, 2855866, 474375, 0, 50875, 3956116),
]

aph = companies["APH"]
assert len(aph["executives"]) == 14, f"APH row count drift: {len(aph['executives'])}"

for (name, title, year, sal, bon, stk, opt, neq, pen, oth, tot) in APH_ROWS:
    row = next(
        e for e in aph["executives"]
        if e["year"] == year
        and re.sub(r"\.$", "", e["name"].replace(" ", "")) == re.sub(r"\.$", "", name.replace(" ", ""))
    )
    # sanity: filing-side arithmetic (Lampo 2023 is the known filer typo)
    foot = sal + bon + stk + opt + neq + pen + oth
    if (name, year) == ("C.A. Lampo", 2023):
        assert foot - tot == 63000, f"Lampo 2023 filing delta drift: {foot - tot}"
    else:
        assert foot == tot, f"{name} {year}: components {foot} != total {tot}"
    row.update({
        "name": name,
        "title": title,
        "salary": sal,
        "bonus": bon,
        "stock_awards": stk,
        "option_awards": opt,
        "non_equity_incentive": neq,
        "pension_nqdc": pen,
        "all_other": oth,
        "total": tot,
        "_fix_note": FIX_NOTE_APH,
    })
    if (name, year) == ("C.A. Lampo", 2023):
        row["_total_source"] = "component_mismatch"
        row["_fix_note"] += (
            " Filing-side arithmetic error on this row: printed components "
            "sum to $3,778,717 but the filing prints total $3,715,717 "
            "(delta $63,000, filer-side); stored verbatim."
        )
    else:
        row["_total_source"] = "verified"

# ---------------------------------------------------------------- APH level
aph["total_neo_compensation"] = 45537170  # FY2025: 22351288+6526027+5831540+5657569+5170746
aph["pay_ratio"] = 1188                    # 2026 proxy: 1,188:1
aph["median_worker_pay"] = 18816           # 2026 proxy
assert aph["fiscal_year"] == 2025
assert sum(e["total"] for e in aph["executives"] if e["year"] == 2025) == 45537170

# ---------------------------------------------------------------- LHX rows
RENAMES = [
    # (old_name, year, new_name, new_title)
    ("Missile Solutions", 2024, "Kenneth Bedingfield",
     "Senior Vice President and Chief Financial Officer"),
    ("Missile Solutions", 2023, "Kenneth Bedingfield",
     "Senior Vice President and Chief Financial Officer"),
    ("Mission Systems", 2024, "Samir Mehta", "President, Communication Systems"),
    ("Spectrum Dominance", 2023, "Samir Mehta", "President, Communication Systems"),
]
lhx = companies["LHX"]
for old, year, new_name, new_title in RENAMES:
    row = next(e for e in lhx["executives"] if e["name"] == old and e["year"] == year)
    row["name"] = new_name
    row["title"] = new_title
    row["_fix_note"] = (
        "2026-09-13 10:00 PT: org-label name repaired to the real NEO per the "
        "LHX 2025 DEF 14A (filed 2025-03-07) Fiscal 2024 Summary Compensation "
        "Table; components and total unchanged (already correct)."
    )

# Edward Zoiss title expansion per the same SCT
for e in lhx["executives"]:
    if e["name"] == "Edward Zoiss" and e["year"] in (2024, 2023):
        e["title"] = "President, Space & Airborne Systems"

# Restored dropped Rambeau 2023 row
lhx["executives"].append({
    "name": "Jonathan Rambeau",
    "title": "President, Integrated Mission Systems",
    "year": 2023,
    "salary": 725000,
    "bonus": 0,
    "stock_awards": 1910722,
    "option_awards": 637550,
    "non_equity_incentive": 605400,
    "pension_nqdc": 0,
    "all_other": 22651,
    "total": 3901323,
    "_total_source": "verified",
    "_fix_note": (
        "2026-09-13 10:00 PT: row was dropped by the original parse; restored "
        "from the LHX 2025 DEF 14A (filed 2025-03-07) Fiscal 2024 SCT verbatim "
        "(components foot exactly)."
    ),
})
assert len(lhx["executives"]) == 15, f"LHX row count drift: {len(lhx['executives'])}"
# FY2024 aggregates (LHX fiscal_year 2024) must be untouched by renames
assert sum(e["total"] for e in lhx["executives"] if e["year"] == 2024) == 42601322
assert len([e for e in lhx["executives"] if e["year"] == 2024]) == 5

# ---------------------------------------------------------------- metadata
n = sum(len(c.get("executives", [])) for c in data["companies"])
assert n == 6783, f"record count drift: {n}"
meta = data["metadata"]
meta["total_neo_records"] = n
meta["total_executives"] = n
meta["title_coverage"] = f"{n}/{n}"
meta["description"] = meta["description"].replace("6781 NEO records", "6783 NEO records")
meta["last_updated"] = "2026-09-13"

for block in ("data_quality", "data_quality_detailed"):
    dq = meta[block]
    dq["verified"] = 6336            # 6336 - 1 (Lampo 2023 -> component_mismatch) + 1 (Rambeau 2023)
    dq["component_mismatch"] = 21
    dq["verified_total"] = 6762     # unchanged: 6336 + 217 + 109 + 63 + 13 + 24

with open(JSON_PATH, "w", encoding="utf-8") as f:
    # Repo format discipline: single-line compact JSON, no trailing newline,
    # default separators, ensure_ascii=False (matches every prior DQ batch).
    json.dump(data, f, ensure_ascii=False)

print(f"records={n} APH_total=45537170 LHX_FY2024_total=42601322 verified_total=6762 mismatch=21")
