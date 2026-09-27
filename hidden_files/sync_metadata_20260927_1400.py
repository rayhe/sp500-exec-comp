#!/usr/bin/env python3
"""2026-09-27 14:00 PT post-batch metadata + static-copy sync (GNRC/CTSH/INVH).

Follows the sync_metadata_20260927_1000.py pattern:
1. Recount data_quality / data_quality_detailed buckets from live
   _total_source labels (20 rows verified -> def14a_verified_20260927,
   1 row verified -> component_mismatch [GNRC Taffe 2023, $299 filing-side]);
   verified_total 7046 -> 7045; component_mismatch 32 -> 33; last_audit=2026-09-27.
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
    HERE, "compensation_backup_20260927_1400_pre_sync.json"))

verified_total = sum(v for k, v in cnt.items()
                     if k == "verified" or str(k).startswith("def14a_verified_"))
assert verified_total == 7045, verified_total
assert cnt["component_mismatch"] == 33, cnt["component_mismatch"]

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

txt2, n = re.subn(r"99\.5% verified component-total consistency \(7,046 of 7,078 records, 32 filing-side",
                  "99.5% verified component-total consistency (7,045 of 7,078 records, 33 filing-side",
                  txt, count=1)
assert n == 1, "README line-11 description not found"
txt = txt2

txt2, n = re.subn(r"99\.5% verified \(7,046 of 7,078 total NEO records\), 0 rounding-gap rows, 0 recomputed",
                  "99.5% verified (7,045 of 7,078 total NEO records), 0 rounding-gap rows, 0 recomputed",
                  txt, count=1)
assert n == 1, "README methodology line not found"
txt = txt2

txt2, n = re.subn(r"32 filing-side component mismatches \(WAB 2023",
                  "33 filing-side component mismatches (WAB 2023",
                  txt, count=1)
assert n == 1, "README mismatch-list head not found"
txt = txt2

# extend the mismatch enumeration with the new GNRC entry
txt2, n = re.subn(r"Block Weber 2025 Δ\$1 filing-side rounding — all documented in-record",
                  "Block Weber 2025 Δ$1 filing-side rounding; GNRC Taffe 2023 Δ$299 — all documented in-record",
                  txt, count=1)
assert n == 1, "README mismatch-list tail not found"
txt = txt2

txt2, n = re.subn(r"guard section-8 candidate set now 33 rows / 13 tickers\.",
                  "guard section-8 candidate set now 33 rows / 13 tickers. "
                  "2026-09-27 14:00 PT DQ batch: GNRC (5 rows) + CTSH (12 rows) + INVH (4 rows) "
                  "column-shift repair, continuing the DG/PCG/FITB salary-drop family. GNRC 2023/2024 rows "
                  "(Wilde, Ragen, Taffe) repaired filing-verbatim from the 2026 DEF 14A SCT "
                  "(acc. 0001104659-26-051499, table 90; no pension column), 2023/2024 columns cross-checked "
                  "identical vs the 2025 DEF 14A SCT (acc. 0001104659-25-040848, table 89). "
                  "Taffe 2023 components sum $2,231,414 vs printed $2,231,115 - a genuine $299 filing-side "
                  "arithmetic inconsistency present in BOTH proxies (digit-by-digit re-read; relabeled "
                  "component_mismatch per the SBUX/FDS taxonomy). CTSH 2025 rows (Kumar, Dalal, Gummadi, Ayyar) "
                  "repaired from the 2026 DEF 14A SCT (acc. 0001308179-26-000290, table 164; no options column); "
                  "CTSH 2023/2024 rows (Kumar, Dalal x2, Gummadi x2, Kim, Ayyar x2) repaired from the same filing "
                  "(2023/2024 columns cross-checked identical vs the 2025 DEF 14A SCT, acc. 0001359948-25-000472, "
                  "table 137 - no restatements); the 2023/2024 parse had mapped filing columns onto the wrong "
                  "stored fields, dropping the NEIP and All Other components (CTSH was net UNDERSTATED). "
                  "INVH Olsen 2023/2024 repaired from the 2026 DEF 14A SCT (acc. 0001193125-26-126310, table 266); "
                  "INVH Solls: the 2026 proxy SCT carries a filing-side YEAR MISALIGNMENT (its Solls '2024' column "
                  "is actually 2023 data, its '2023' column is actually 2022 data, the true 2024 column is missing) - "
                  "decisively adjudicated by the 2025 DEF 14A SCT (acc. 0000950170-25-049911, table 144) AND the "
                  "2024 DEF 14A SCT (acc. 0001193125-24-085370, table 323), which agree Solls 2024 = "
                  "$523,077/$1,000,036/$666,437/$13,800/$2,203,350 and Solls 2023 = "
                  "$512,116/$950,031/$504,946/$13,200/$1,980,293; every other INVH NEO's 2023/2024 columns agree "
                  "across all three proxies, so the slip is isolated to Solls in the 2026 proxy. All 21 rows foot "
                  "exactly except Taffe 2023; 20 relabeled def14a_verified_20260927. FY2024 neo comp re-anchored: "
                  "GNRC $20,785,267->$17,323,762, CTSH $37,379,426->$40,131,135, INVH $27,939,900->$24,540,685; "
                  "net batch delta -$3.55M (GNRC -$7.81M incl. 2023 rows, CTSH +$12.29M understatement corrected, "
                  "INVH -$8.04M incl. 2023 rows). verified_total 7,046->7,045 (99.5%), component_mismatch 32->33; "
                  "guard section-8 candidate set now 13 rows / 9 tickers (AEE, CHD, D, GWW, JCI, KDP, LW, WEC, WRB).",
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
