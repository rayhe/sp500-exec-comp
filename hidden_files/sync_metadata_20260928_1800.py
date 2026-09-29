#!/usr/bin/env python3
"""2026-09-28 18:00 PT post-batch metadata + static-copy sync (MRNA + HUM, 15 rows).

1. Recount data_quality / data_quality_detailed buckets from live
   _total_source labels (15 rows 'verified' -> def14a_verified_20260928,
   now 44; relabels stay inside the verified class so verified_total
   stays 7044; component_mismatch unchanged at 34; last_audit=2026-09-28).
2. Re-assert company aggregates: MRNA re-anchored by the repair script
   (fiscal_year=2024 total_neo_compensation 63,638,941; CEO Bancel
   total_compensation 19,876,180; pay_ratio 93 unchanged); HUM
   (fiscal_year=2025 total_neo_compensation 65,725,589; CEO Rechtin
   total_compensation unchanged 18,757,075; pay_ratio 226 unchanged).
3. Pay-ratio screen (guard section 11 rule): MRNA moves near-2x ->
   within-tolerance on the corrected CEO anchor (93.2/93 = 1.0025), so the
   screen moves 394/10/13/97 -> 395/9/13/97.
4. Sync static copies: README audit-trail entry appended (MRNA + HUM queue
   items retired; PGR Griffith 2024-clean remains queued), js/app.js
   dataq-phantom-block numbers via phantom_record.record_batch (66 batches,
   $2,834,529,215 gross removed / $550,284,451 restored / net $2,284,244,764
   - batch net delta +$33,573,226 counts to gross_removed per convention) and dataq-payratio-block
   counts (395 within / 9 near 2x / 13 near 0.5x / 97 differ).
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
    HERE, "compensation_backup_20260928_1800_pre_sync.json"))

verified_total = sum(v for k, v in cnt.items()
                     if k == "verified" or str(k).startswith("def14a_verified_"))
assert verified_total == 7044, verified_total
assert cnt["component_mismatch"] == 34, cnt["component_mismatch"]
assert cnt["def14a_verified_20260928"] == 44, cnt["def14a_verified_20260928"]
assert cnt["verified"] == 5630, cnt["verified"]
assert delta12 == 328, delta12

for block_key in ("data_quality", "data_quality_detailed"):
    block = data["metadata"][block_key]
    ordered = {}
    for k in sorted(cnt.keys()):
        if k not in ("verified_total", "last_audit"):
            ordered[k] = cnt[k]
    if "rounding" not in ordered:
        ordered["rounding"] = 0
    ordered["verified_total"] = verified_total
    ordered["last_audit"] = "2026-09-28"
    block.clear()
    block.update(ordered)

# 2. company aggregates (guard section 5 convention: sum of fiscal_year rows)
companies = {c["ticker"]: c for c in data["companies"]}
mrna = companies["MRNA"]
s = sum(e["total"] for e in mrna["executives"] if e["year"] == 2024)
assert mrna["fiscal_year"] == 2024
assert s == 63638941, f"MRNA anchor {s}"
assert mrna["total_neo_compensation"] == 63638941
assert mrna["total_compensation"] == 19876180
assert mrna["ceo_name"] == "Stéphane Bancel"
assert mrna["pay_ratio"] == 93
assert mrna["median_worker_pay"] == 213200
print("MRNA anchors asserted: neo 63,638,941 / CEO 19,876,180 / pay_ratio 93")

hum = companies["HUM"]
s = sum(e["total"] for e in hum["executives"] if e["year"] == 2025)
assert hum["fiscal_year"] == 2025
assert s == 65725589, f"HUM anchor {s}"
assert hum["total_neo_compensation"] == 65725589
assert hum["total_compensation"] == 18757075
assert hum["ceo_name"] == "James A. Rechtin"
assert hum["pay_ratio"] == 226
assert hum["median_worker_pay"] == 82935
print("HUM anchors asserted: neo 65,725,589 / CEO 18,757,075 (unchanged) / pay_ratio 226")

# 3. pay-ratio screen (guard section 11 rule)
w = t2 = h = o = 0
for c in data["companies"]:
    pr = c.get("pay_ratio")
    mw = c.get("median_worker_pay")
    ct = c.get("total_compensation")
    if pr in (None, 0) or mw in (None, 0) or ct is None:
        continue
    r = (ct / mw) / pr
    if abs(r - 1) <= max(2 / pr, 0.03):
        w += 1
    elif 1.9 <= r <= 2.1:
        t2 += 1
    elif 0.4 <= r <= 0.6:
        h += 1
    else:
        o += 1
assert (w, t2, h, o) == (395, 9, 13, 97), (w, t2, h, o)
print(f"pay-ratio screen: within={w} near2x={t2} near0.5x={h} differ={o}")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)

print("live recount verified_total:", verified_total, "| $1-$2 verified rows:", delta12)

# 4. README audit trail: retire MRNA/HUM queue items, append the 18:00 entry
rm = os.path.join(REPO, "README.md")
txt = open(rm, encoding="utf-8").read()

old_queue = ("MRNA Bancel 2025 + HUM Shetty 2023/2024 + PGR Griffith 2024-clean "
             "remain queued as separate investigations (distinct signatures, "
             "each needs its own filing re-read).")
new_queue = ("PGR Griffith 2024-clean remains queued as a separate "
             "investigation (distinct signature, needs its own filing "
             "re-read).")
if txt.count(old_queue) != 1:
    assert new_queue in txt, "README queue anchor neither old nor new"
entry = (new_queue + " 2026-09-28 18:00 PT DQ batch: MRNA + HUM queued "
    "investigations closed - 23-row whole-company SCT re-reads, cell-by-cell, "
    "from the primary 2026 DEF 14A HTML filings (fetched from EDGAR via the "
    "VM egress proxy; www.sec.gov reachable this run). MRNA (acc. "
    "0001308179-26-000081, filed 2026-03-16): SCT has NO pension column "
    "(Name / Year / Salary / Non-Equity Plan Incentive / Bonus / Stock / "
    "Options / All Other / Total); 2024/2023 columns cross-checked identical "
    "vs the 2025 DEF 14A SCT (acc. 0001308179-25-000082) - no restatements. "
    "Two families: (A) salary-drop column shift on all 8 2023/2024 rows "
    "(parser dropped the Salary cell; filing.NEIP->stored.salary, "
    "filing.stock->stored.bonus, filing.options->stored.stock, "
    "filing.all_other->stored.options, filing.total->stored.all_other, "
    "stored.total recomputed ~1.9-2x; e.g. Bancel 2024 $38,126,475 vs filing "
    "$19,876,180); (B) split-currency Family B on Bancel 2025 ONLY (the "
    "latest-year row renders each value preceded by a standalone '$' cell; "
    "the other 2025 rows render normally and parsed clean) - parser mapped "
    "filing.salary->stored.non_equity_incentive, filing.NEIP->stored."
    "stock_awards, dropped stock/options/all_other, recomputed "
    "total=salary+NEIP, UNDERSTATES the filing ($5,980,099 vs $19,932,217). "
    "HUM (acc. 0001104659-26-024393, filed 2026-03-06): columns include Bonus "
    "and Pension; Shetty 2024/2023 cross-checked identical vs the 2025 DEF "
    "14A SCT (acc. 0001193125-25-048976) - no restatements. One family: "
    "'bonus-only' parse on 6 rows (Mellet/Mehta/O'Hara/Shetty 2025, Shetty "
    "2024/2023 - all carry footnote markers (5)/(6)/(7)/(8) in the name cell; "
    "the 5 clean rows Rechtin x2 / Diamond x3 parsed fine): parser kept only "
    "the Bonus cell (landing in stored.option_awards for 2025 rows, "
    "stored.stock_awards for the Shetty continuation rows) and recomputed "
    "stored.total = bonus alone, UNDERSTATES the filing (e.g. Mellet 2025 "
    "$6,000,000 vs filing $18,922,704; Shetty 2023 $1,400,000 vs "
    "$4,581,941). All 23 transcribed rows foot exactly; the 8 clean rows "
    "match stored 'verified' rows field-for-field. 15 rows relabeled "
    "def14a_verified_20260928. FY2024 neo comp re-anchored: MRNA "
    "$122,912,406->$63,638,941; MRNA CEO total_compensation $38,126,475->"
    "$19,876,180 (Bancel FY2024 filing-verbatim), pay ratio stays 93 "
    "(19,876,180/213,200=93.2). HUM FY2025 neo comp re-anchored "
    "$34,190,005->$65,725,589 (restoration); HUM CEO unchanged $18,757,075, "
    "pay ratio stays 226. Net batch phantom: -$88,128,132 removed (all MRNA "
    "Family A) / +$54,554,906 restored (Bancel 2025 +$13,952,118; HUM "
    "+$40,602,788) = -$33,573,226. verified_total unchanged at 7,044 "
    "(99.5%), component_mismatch unchanged at 34. Pay-ratio screen: 395/514 "
    "within tolerance, 9 near 2x, 13 near 0.5x, 97 differ otherwise (MRNA "
    "moves near-2x->within-tolerance on the corrected CEO anchor).")
txt = txt.replace(old_queue, entry, 1)
open(rm, "w", encoding="utf-8").write(txt)

# js/app.js modal copies
js = os.path.join(REPO, "js", "app.js")
jst = open(js, encoding="utf-8").read()

old_phantom = ("$2,800,955,989 of parser-invented compensation removed across 65 "
               "re-verification batches since 2026-09-12, partly offset by "
               "$550,284,451 of genuine missing NEO rows restored "
               "filing-verbatim. Net: $2,250,671,538.")
new_phantom = ("$2,834,529,215 of parser-invented compensation removed across 66 "
               "re-verification batches since 2026-09-12, partly offset by "
               "$550,284,451 of genuine missing NEO rows restored "
               "filing-verbatim. Net: $2,284,244,764.")  # superseded: phantom_record is the source of truth
assert jst.count(old_phantom) == 1, "js phantom-block not found/unique"
jst = jst.replace(old_phantom, new_phantom, 1)

old_pr1 = "As of the 2026-09-28 screen: 394 of 514 screened companies"
new_pr1 = "As of the 2026-09-28 screen: 395 of 514 screened companies"
assert jst.count(old_pr1) == 1, "js payratio-block (within) not found/unique"
jst = jst.replace(old_pr1, new_pr1, 1)

old_pr2 = "within 3% tolerance; 10 cluster near 2x, 13 near 0.5x, 97 differ otherwise."
new_pr2 = "within 3% tolerance; 9 cluster near 2x, 13 near 0.5x, 97 differ otherwise."
assert jst.count(old_pr2) == 1, "js payratio-block (bands) not found/unique"
jst = jst.replace(old_pr2, new_pr2, 1)

assert '<div id=\"dataq-coverage-block\"><h4>Coverage (last audit 2026-09-28)</h4>' in jst, \
    "js coverage-block drifted"

open(js, "w", encoding="utf-8").write(jst)
print("sync complete")
