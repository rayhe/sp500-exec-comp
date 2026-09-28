#!/usr/bin/env python3
"""2026-09-27 18:00 PT post-batch metadata + static-copy sync (GWW/KDP).

Follows the sync_metadata_20260927_1400.py pattern:
1. Recount data_quality / data_quality_detailed buckets from live
   _total_source labels (9 rows verified -> def14a_verified_20260927,
   2 rows def14a_verified_20260917 -> def14a_verified_20260927 [KDP Gamgort,
   Priyadarshi 2023]); verified_total stays 7045; component_mismatch stays 33
   (all 11 rows foot exactly); last_audit=2026-09-27.
2. Sync the static description copies in README.md (line 11) and the
   data-quality methodology line (line 99) + js/app.js modal copies.
3. Append the batch audit-trail entry to the README methodology log.
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
    HERE, "compensation_backup_20260927_1800_pre_sync.json"))

verified_total = sum(v for k, v in cnt.items()
                     if k == "verified" or str(k).startswith("def14a_verified_"))
assert verified_total == 7045, verified_total
assert cnt["component_mismatch"] == 33, cnt["component_mismatch"]
assert cnt["def14a_verified_20260927"] == 11 + 20 + 9 + 11, cnt["def14a_verified_20260927"]

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

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)

print("live recount:", dict(cnt))
print("verified_total:", verified_total, "| $1-$2 verified rows:", delta12)

# 2. README static copies
rm = os.path.join(REPO, "README.md")
txt = open(rm, encoding="utf-8").read()

# description line (line 11) - verified count unchanged at 7,045
txt2, n = re.subn(r"99\.5% verified component-total consistency \(7,045 of 7,078 records, 33 filing-side",
                  "99.5% verified component-total consistency (7,045 of 7,078 records, 33 filing-side",
                  txt, count=1)
assert n == 1, "README line-11 description not found"
txt = txt2

# append the 18:00 batch audit-trail entry
txt2, n = re.subn(
    r"guard section-8 candidate set now 13 rows / 9 tickers \(AEE, CHD, D, GWW, JCI, KDP, LW, WEC, WRB\)\.",
    "guard section-8 candidate set now 13 rows / 9 tickers (AEE, CHD, D, GWW, JCI, KDP, LW, WEC, WRB). "
    "2026-09-27 18:00 PT DQ batch: GWW (6 rows) + KDP (5 rows) salary-drop column-shift repair, "
    "continuing the DG/PCG/FITB/GNRC/CTSH/INVH family. GWW 2023/2024 rows (Merriwether, Robbins, "
    "Berardinelli-Krantz) repaired filing-verbatim from the 2026 DEF 14A SCT "
    "(acc. 0001104659-26-025575, filed 2026-03-10; Salary|Bonus|Stock|NEIP|All Other|Total - no options "
    "and no pension columns), 2023 columns cross-checked identical vs the 2025 DEF 14A SCT "
    "(acc. 0001104659-25-021496, filed 2025-03-07) - no restatements. Berardinelli-Krantz 2023 is the "
    "bonus-content shift variant: filing Bonus $900,000 landed in stored.salary, every component one "
    "column left, filing total->stored.all_other, total recomputed ~1.9x. KDP Johnson 2024, Johnson 2023, "
    "Gamgort 2023, Priyadarshi 2023 repaired from the 2026 DEF 14A SCT (acc. 0001193125-26-177266, filed "
    "2026-04-24; same 6-column layout), 2023 columns cross-checked identical vs the 2025 DEF 14A SCT "
    "(acc. 0001193125-25-096767, filed 2025-04-25) - no restatements. KDP Cofer 2023 is the same "
    "bonus-content variant (filing Bonus $8,000,000 landed in stored.salary): stored row $51,656,479 -> "
    "filing-verbatim $25,916,701, the largest single-row phantom in the campaign. Both siblings were "
    "tripwire-misses (nonzero salary cell) caught during the filing re-reads. All 11 rows foot exactly; "
    "11 relabeled def14a_verified_20260927. FY2024 neo comp re-anchored: GWW $29,274,137->$21,117,346 "
    "(Merriwether -$3,028,192; Robbins -$2,927,551; Berardinelli-Krantz -$2,201,048), "
    "KDP $25,739,390->$23,310,189 (Johnson -$2,429,201); 2023 rows repaired but not anchor year "
    "(Merriwether -$2,985,581; Robbins -$2,985,581; Berardinelli-Krantz -$4,228,773; Johnson -$2,179,347; "
    "Gamgort -$6,120,095; Priyadarshi -$2,577,558; Cofer -$25,739,778); net batch phantom -$57,402,705. "
    "verified_total unchanged at 7,045/7,078 (99.5%), component_mismatch unchanged at 33; "
    "guard section-8 candidate set now 15 rows / 9 tickers (AEE, CHD, CPT, JCI, KMB, LW, WEC, WRB, XEL). "
    "CPT (Camden Property Trust, 2 rows: Campo/Oden 2025 - salary==0, bonus==0, distinct signature) is a "
    "new tripwire find queued for its own investigation, not the salary-drop family.",
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
