#!/usr/bin/env python3
"""DQ repair batch (2026-10-11 02:00 PT run).

Findings from the 02:00 PT 5-critic eval-iterate pass (data-freshness
screen of the 2026-10-06 FY2025 anchor promotion):

1. available_years ordering: 18 companies carry ASCENDING available_years
   (e.g. [2023, 2024, 2025]) while the repo convention (500 companies) is
   DESCENDING ([2025, 2024, 2023]). A repair script wrote them unsorted;
   the pre-commit metadata guard never asserted order. Repair: sort
   descending in place.

2. proxy_fiscal_year staleness: 11 companies have proxy_fiscal_year !=
   max(available_years). Established semantics (apply_dq_20260928_1400:
   "aggregate anchor = fiscal_year, NOT proxy_fiscal_year; RMD
   fiscal_year=2024, proxy_fiscal_year=2025"; apply_roster_add:
   proxy_fiscal_year = the source proxy's fiscal year; BRK-B
   fiscal_year=2024 anchor on a FY2025 filing keeps proxy_fiscal_year=2025)
   is proxy_fiscal_year := latest fiscal year covered by the source
   filing == max(available_years). proxy_fiscal_year is the CSV-export
   fallback year for exec rows missing year (js/app.js ~15625), so a stale
   value mislabels exports.
   - 5 stale at 2024 (AVGO, DOV, HSY, NFLX, PAYC) -> 2025 (FY2025 proxies
     filed 2026-03/04; all have FY2025 SCT rows in executives[])
   - 5 bogus at 2026 (BNY, MRSH, VRT, BE, ILMN) -> 2025 (calendar-FY
     companies; the +1 looks like a repair-script artifact)
   - WMT 2024 -> 2026 (April 2026 proxy covers FY2026 ended 2026-01-31)
   All 11 have exec rows for the target year; the filing genuinely covers
   it. BRK-B (anchor 2024, proxy_fy 2025 = max years) already satisfied
   the rule and is the documented anchor/filing-year divergence.

Guard follow-up (same run): check_metadata_consistency.py gains section
20 asserting available_years is descending and proxy_fiscal_year ==
max(available_years), so neither class can recur.

Backup: data/compensation_backup_20261011_0200_pre_ayearorder.json
"""
import json
import os

TOP = "/home/hatch/repos/sp500-exec-comp"
PATH = os.path.join(TOP, "data", "compensation.json")

REORDER = ["AVGO", "AWK", "BA", "BLK", "CNC", "CRL", "DIS", "DOV", "DTE",
           "FDS", "GE", "HSY", "JPM", "MCO", "NFLX", "PAYC", "WMT", "ZTS"]

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

companies = {c["ticker"]: c for c in data["companies"]}

reordered, pf_fixed = [], []
for t in REORDER:
    c = companies[t]
    y = c.get("available_years") or []
    want = sorted(y, reverse=True)
    if y != want:
        c["available_years"] = want
        reordered.append((t, y, want))

for c in data["companies"]:
    y = c.get("available_years") or []
    if y and c.get("proxy_fiscal_year") != max(y):
        old = c.get("proxy_fiscal_year")
        c["proxy_fiscal_year"] = max(y)
        pf_fixed.append((c["ticker"], old, max(y)))

# DQ-repair freshness convention (guard section 3): bump both stamps.
data["last_updated"] = "2026-10-11"
data["metadata"]["last_dq_repair"] = "2026-10-11"

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
    f.write("\n")

print(f"reordered available_years: {len(reordered)}")
for t, old, new in reordered:
    print(f"  {t}: {old} -> {new}")
print(f"proxy_fiscal_year repairs: {len(pf_fixed)}")
for t, old, new in pf_fixed:
    print(f"  {t}: {old} -> {new}")
