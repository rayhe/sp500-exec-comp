#!/usr/bin/env python3
"""2026-09-27 22:00 PT post-batch metadata + static-copy sync
(AEE/CHD/JCI/KMB/LW/WEC/WRB/XEL, 23 rows).

1. Recount data_quality / data_quality_detailed buckets from live
   _total_source labels (22 rows verified -> def14a_verified_20260927,
   1 row verified -> component_mismatch [JCI Brandt 2023, genuine filing-side
   $349,039 arithmetic inconsistency]); verified_total 7045 -> 7044
   (component_mismatch rows are not counted in verified_total);
   last_audit=2026-09-27.
2. Refresh company aggregates the repair script did not cover: the 2024
   repairs sit in the anchor fiscal_year for AEE, JCI, KMB, WEC, XEL
   (their fiscal_year=2024), so total_neo_compensation goes stale unless
   re-summed. LW's aggregate was fixed in the repair script; its
   ceo total_compensation (Michael J. Smith) was still the corrupted
   2024-row value 5,695,862 -> filing-verbatim 3,222,931 (guard section 6).
3. Sync the static description copies in README.md (line 11) and the
   data-quality methodology line (33 -> 34 mismatch list, +JCI Brandt 2023
   entry) + js/app.js modal copies.
4. Append the batch audit-trail entry to the README methodology log.
"""
import json
import os
import re
import shutil
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
REPO = os.path.join(HERE, "..")

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

cnt = Counter()
delta12 = 0
COMP8 = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "pension_change", "all_other"]

def _int_or_zero(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else 0

for c in data["companies"]:
    for e in c["executives"]:
        lab = e.get("_total_source")
        cnt[lab] += 1
        if lab == "verified" or str(lab).startswith("def14a_verified"):
            s = sum(_int_or_zero(e.get(k)) for k in COMP8)
            if abs(s - _int_or_zero(e.get("total"))) in (1, 2):
                delta12 += 1

shutil.copy2(JSON_PATH, os.path.join(
    HERE, "compensation_backup_20260927_2200_pre_sync.json"))

verified_total = sum(v for k, v in cnt.items()
                     if k == "verified" or str(k).startswith("def14a_verified_"))
assert verified_total == 7044, verified_total
assert cnt["component_mismatch"] == 34, cnt["component_mismatch"]
assert cnt["def14a_verified_20260927"] == 73, cnt["def14a_verified_20260927"]
assert cnt["verified"] == 5674, cnt["verified"]

for block_key in ("data_quality", "data_quality_detailed"):
    block = data["metadata"][block_key]
    ordered = {}
    for k in sorted(cnt.keys()):
        if k not in ("verified_total", "last_audit"):
            ordered[k] = cnt[k]
    if "rounding" not in ordered:
        ordered["rounding"] = 0
    ordered["verified_total"] = verified_total
    ordered["last_audit"] = "2026-09-27"
    block.clear()
    block.update(ordered)

# 2. company aggregates (guard section 5 convention: sum of fiscal_year rows)
EXPECTED_ANCHORS = {
    'AEE': 20292698,
    'JCI': 32969068,
    'KMB': 39434072,
    'WEC': 24162368,
    'XEL': 24688114,
    'LW': 7922428,   # set by the repair script; re-assert here
}
companies = {c["ticker"]: c for c in data["companies"]}
for ticker, want in EXPECTED_ANCHORS.items():
    c = companies[ticker]
    fy = c["fiscal_year"]
    s = sum(e["total"] for e in c["executives"] if e["year"] == fy)
    assert s == want, f"ANCHOR-SYNC {ticker} FY{fy} sum {s} != {want}"
    old = c["total_neo_compensation"]
    c["total_neo_compensation"] = want
    if old != want:
        print(f"{ticker} total_neo_compensation {old:,} -> {want:,}")

# LW CEO total (guard section 6): Smith's filing-verbatim FY2024 SCT total
lw = companies["LW"]
smith24 = next(e for e in lw["executives"]
               if e["name"] == "Michael J. Smith" and e["year"] == 2024)
assert smith24["total"] == 3222931
print(f"LW total_compensation {lw['total_compensation']:,} -> 3,222,931")
lw["total_compensation"] = 3222931

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)

print("live recount:", dict(cnt))
print("verified_total:", verified_total, "| $1-$2 verified rows:", delta12)

# 3. README static copies
rm = os.path.join(REPO, "README.md")
txt = open(rm, encoding="utf-8").read()

# description line (line 11)
txt2, n = re.subn(
    r"99\.5% verified component-total consistency \(7,045 of 7,078 records, 33 filing-side",
    "99.5% verified component-total consistency (7,044 of 7,078 records, 34 filing-side",
    txt, count=1)
assert n == 1, "README line-11 description not found"
txt = txt2

# methodology mismatch list: 33 -> 34, append Brandt entry
txt2, n = re.subn(
    r"33 filing-side component mismatches \(",
    "34 filing-side component mismatches (", txt, count=1)
assert n == 1, "README mismatch-list count not found"
txt = txt2
txt2, n = re.subn(
    r"(GNRC Taffe 2023 Δ\$299 — all documented in-record, values match filings verbatim\))",
    r"GNRC Taffe 2023 Δ$299; JCI Brandt 2023 Δ$349,039 — all documented in-record, values match filings verbatim)",
    txt, count=1)
assert n == 1, "README mismatch-list tail not found"
txt = txt2

# 4. append the 22:00 batch audit-trail entry
txt2, n = re.subn(
    r"CPT \(Camden Property Trust, 2 rows: Campo/Oden 2025 - salary==0, bonus==0, distinct signature\) is a "
    r"new tripwire find queued for its own investigation, not the salary-drop family\.",
    "CPT (Camden Property Trust, 2 rows: Campo/Oden 2025 - salary==0, bonus==0, distinct signature) is a "
    "new tripwire find queued for its own investigation, not the salary-drop family. "
    "2026-09-27 22:00 PT DQ batch: salary-drop column-shift repair across AEE (4 rows: Singh 2024/2023, "
    "Birk 2024/2023) + CHD (de Maynadier 2023) + JCI (Brandt 2024/2023) + KMB (Hicks 2024, Melucci 2023) + "
    "WEC (Garvin 2024/2023) + WRB (Sgaglione 2023) + XEL (Rome 2024/2023, Van Abel 2023, O'Connor 2024/2023) "
    "= 17 rows, plus the LW (6 rows) split-currency / footnote-split-bonus family: Smith 2026 stock "
    "$90,121, Wilks 2026 stock $59,712, Madarieta 2025 stock $51,923 (filing renders Stock Awards as a "
    "standalone '$' cell + separate number cell; parser dropped the values and recomputed totals without "
    "them - negative phantom), Wilks 2025 stock $1,433,699 misattributed to non_equity_incentive, "
    "Schroeder 2025 (bonus renders as '(6)' + '--' cells; parser dropped stock_awards and shifted "
    "filing.stock->stored.options, filing.neip->stored.all_other), Smith 2024 salary-drop shift. "
    "All filing-verbatim re-reads from the 2026 DEF 14A SCTs (AEE acc. 0001104659-26-037756; CHD "
    "acc. 0001193125-26-115994; JCI acc. 0001104659-26-004565; KMB acc. 0001628280-26-020404; LW "
    "acc. 0001679273-26-000036; WEC acc. 0000783325-26-000035; WRB acc. 0001193125-26-170583; XEL "
    "acc. 0000072903-26-000063). 5 bonus-content shift variants caught as tripwire-miss siblings "
    "(nonzero salary cell): AEE Singh 2023 ($250,000 bonus), JCI Brandt 2023 ($750,000), XEL Rome 2023 "
    "($200,000), XEL Van Abel 2023 ($200,000), XEL O'Connor 2023 ($100,000). JCI Brandt 2023 is a genuine "
    "filing-side arithmetic inconsistency (components $4,314,666 vs printed $3,965,627, delta $349,039, "
    "re-read digit-by-digit incl. raw cell markup; not an NEO in the 2025 proxy so no restatement column) "
    "- stored verbatim, printed total retained, labeled component_mismatch. XEL name artifacts repaired: "
    "\"Tim O'ConnorFormer\" -> \"Tim O'Connor\" (3 rows), \"Ryan LongEVP\" -> \"Ryan Long\", "
    "\"Michael LambEVP\" -> \"Michael Lamb\". All other SCT rows in all 8 companies verified clean. "
    "FY2024 neo comp re-anchored: AEE $24,719,385->$20,292,698; JCI $35,452,524->$32,969,068; KMB "
    "$43,954,286->$39,434,072; WEC $26,184,933->$24,162,368; XEL $30,386,344->$24,688,114; LW "
    "$10,395,359->$7,922,428 (Smith 2024 repair); LW CEO total_compensation $5,695,862->$3,222,931 "
    "(Smith FY2024 filing-verbatim). Net batch phantom -$48,220,385. 22 rows relabeled "
    "def14a_verified_20260927; verified_total 7,045->7,044 (Brandt 2023 moved to component_mismatch), "
    "component_mismatch 33->34. Guard section-8 tripwire fully drained (0 remaining); CPT 4-row "
    "salary==0/bonus==0 signature (Campo/Oden/Jessett/Baker 2025) still queued as a separate investigation.",
    txt, count=1)
assert n == 1, "README audit-trail anchor not found"
txt = txt2

txt2, n = re.subn(r"\d+ `verified` rows carry \$1",
                  f"{delta12} `verified` rows carry $1", txt, count=1)
assert n == 1, "README modal $1-$2 copy not found"
txt = txt2
open(rm, "w", encoding="utf-8").write(txt)

# js/app.js modal copies
js = os.path.join(REPO, "js", "app.js")
jst = open(js, encoding="utf-8").read()
jst2, n = re.subn(r"\d+ <em>verified</em> rows carry \$1",
                  f"{delta12} <em>verified</em> rows carry $1", jst, count=1)
assert n == 1, "js modal copy not found"
open(js, "w", encoding="utf-8").write(jst2)

print("sync complete")
