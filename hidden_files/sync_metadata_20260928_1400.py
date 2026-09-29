#!/usr/bin/env python3
"""2026-09-28 14:00 PT post-batch metadata + static-copy sync (RMD 11 rows).

1. Recount data_quality / data_quality_detailed buckets from live
   _total_source labels (11 rows repaired -> def14a_verified_20260928,
   now 29; relabels stay inside the verified class so verified_total
   stays 7044); component_mismatch unchanged at 34; last_audit=2026-09-28.
2. Re-assert company aggregates: RMD re-anchored by the repair script
   (fiscal_year=2024 total_neo_compensation 26,636,897; CEO Farrell
   total_compensation unchanged 14,120,829; pay_ratio 179 unchanged).
3. Pay-ratio screen (guard section 11 rule) asserted unchanged
   (394/10/13/97) - RMD's CEO anchor did not move, so no band changes.
4. Sync static copies: README audit-trail entry appended (RMD queue item
   retired from the remaining-investigations list), js/app.js
   dataq-phantom-block numbers (65 batches, $2,800,955,989 removed /
   $550,284,451 restored / net $2,250,671,538). Coverage-block and
   payratio-block already read 2026-09-28 / current screen - asserted,
   not rewritten.
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
    HERE, "compensation_backup_20260928_1400_pre_sync.json"))

verified_total = sum(v for k, v in cnt.items()
                     if k == "verified" or str(k).startswith("def14a_verified_"))
assert verified_total == 7044, verified_total
assert cnt["component_mismatch"] == 34, cnt["component_mismatch"]
assert cnt["def14a_verified_20260928"] == 29, cnt["def14a_verified_20260928"]
assert cnt["verified"] == 5645, cnt["verified"]
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
rmd = companies["RMD"]
s = sum(e["total"] for e in rmd["executives"] if e["year"] == rmd["fiscal_year"])
assert rmd["fiscal_year"] == 2024
assert s == 26636897, f"RMD anchor {s}"
assert rmd["total_neo_compensation"] == 26636897
assert rmd["total_compensation"] == 14120829
assert rmd["ceo_name"] == "Michael Farrell"
assert rmd["pay_ratio"] == 179
print("RMD anchors asserted: neo 26,636,897 / CEO 14,120,829 (unchanged) / pay_ratio 179")

# 3. pay-ratio screen (guard section 11 rule) - unchanged expected
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
assert (w, t2, h, o) == (394, 10, 13, 97), (w, t2, h, o)
print(f"pay-ratio screen unchanged: within={w} near2x={t2} near0.5x={h} differ={o}")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)

print("live recount verified_total:", verified_total, "| $1-$2 verified rows:", delta12)

# 4. README audit trail: retire the RMD queue item, append the 14:00 entry
rm = os.path.join(REPO, "README.md")
txt = open(rm, encoding="utf-8").read()

old_queue = ("RMD 8 rows + MRNA Bancel 2025 + HUM Shetty 2023/2024 + PGR "
             "Griffith 2024-clean queued as separate investigations "
             "(distinct signatures, each needs its own filing re-read).")
assert txt.count(old_queue) == 1, "README queue anchor not found/unique"
new_queue = ("MRNA Bancel 2025 + HUM Shetty 2023/2024 + PGR Griffith 2024-clean "
             "remain queued as separate investigations (distinct signatures, "
             "each needs its own filing re-read).")
entry = (new_queue + " 2026-09-28 14:00 PT DQ batch: RMD queued investigation "
    "closed - 13-row whole-company SCT re-read from the 2025 DEF 14A "
    "(acc. 0000943819-25-000079, filed 2026-10-02; FY ended 2026-06-30; "
    "transcribed via the sanctioned browser recovery path after the VM egress "
    "proxy timed out on www.sec.gov and browser.open was 403-blocked). Key "
    "filing fact: RMD's SCT has NO Bonus and NO Pension/NQDC columns "
    "(Name / Year / Salary / Stock Awards / Option Awards / Non-Equity "
    "Incentive / All Other / Total); the filing intro confirms every NEO "
    "draws a real salary, so the stored salary==0 values are parser "
    "corruption. Two understatement families: (A) split-currency Family B on "
    "the 8 2025/2024 non-CEO rows (standalone '$' cells; parser mapped "
    "filing.salary->stored.stock_awards, filing.stock->stored.neip, dropped "
    "NEIP/All Other, recomputed total=salary+stock; e.g. Ghoshal 2025 "
    "$3,051,738 vs filing $3,652,455); (B) stock-drop shift on the 3 2023 "
    "rows (Farrell/Ghoshal/Sandercock: parser dropped the Stock Awards cell, "
    "filing.stock->stored.option_awards, filing.options->stored.all_other, "
    "dropped NEIP/All Other, recomputed total; e.g. Farrell 2023 $12,128,186 "
    "vs filing $13,868,641). Farrell 2025/2024 verified clean to the dollar, "
    "untouched. All 13 transcribed rows foot exactly; Ghoshal 2025 All Other "
    "$50,716 cross-checks vs the filing's (f) sub-table. 11 rows relabeled "
    "def14a_verified_20260928. FY2024 neo comp re-anchored $24,599,030->"
    "$26,636,897; CEO total_compensation unchanged $14,120,829, pay ratio "
    "stays 179. Net batch phantom -$6,818,888 (restoration - both families "
    "understate the filing, unlike Family A). verified_total unchanged at "
    "7,044 (99.5%), component_mismatch unchanged at 34. Pay-ratio screen "
    "unchanged: 394/514 within tolerance, 10 near 2x, 13 near 0.5x, 97 "
    "differ otherwise.")
txt = txt.replace(old_queue, entry, 1)
open(rm, "w", encoding="utf-8").write(txt)

# js/app.js modal copies
js = os.path.join(REPO, "js", "app.js")
jst = open(js, encoding="utf-8").read()

jst2, n = re.subn(
    r"<div id=\"dataq-phantom-block\"><h4>Phantom compensation removed \(as of the 2026-09-28 screen\)</h4>' \+\n"
    r"\s*'<p>\$2,800,955,989 of parser-invented compensation removed across 64 re-verification batches since 2026-09-12, partly offset by \$543,465,563 of genuine missing NEO rows restored filing-verbatim\. Net: \$2,257,490,426\.</p></div>'",
    '<div id="dataq-phantom-block"><h4>Phantom compensation removed (as of the 2026-09-28 screen)</h4>\' +\n'
    "                '<p>$2,800,955,989 of parser-invented compensation removed across 65 re-verification batches since 2026-09-12, partly offset by $550,284,451 of genuine missing NEO rows restored filing-verbatim. Net: $2,250,671,538.</p></div>'",
    jst, count=1)
assert n == 1, "js phantom-block not found"
jst = jst2

# coverage-block + payratio-block already current (2026-09-28 screen) - assert
assert '<div id="dataq-coverage-block"><h4>Coverage (last audit 2026-09-28)</h4>' in jst, \
    "js coverage-block drifted"
assert "As of the 2026-09-28 screen: 394 of 514 screened companies" in jst, \
    "js payratio-block drifted"

open(js, "w", encoding="utf-8").write(jst)
print("sync complete")
