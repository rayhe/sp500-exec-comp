#!/usr/bin/env python3
"""2026-09-28 02:00 PT post-batch metadata + static-copy sync (CPT 12 + PGR 6).

1. Recount data_quality / data_quality_detailed buckets from live
   _total_source labels (18 rows verified -> def14a_verified_20260928);
   verified_total unchanged at 7044 (relabels stay inside the verified
   class); component_mismatch unchanged at 34; last_audit=2026-09-28.
2. Re-assert company aggregates: CPT re-anchored by the repair script
   (total_neo_compensation 21,936,889; CEO Jessett total_compensation
   4,151,948); PGR aggregates were already correct.
3. Sync static copies: README line-11 description (last audit date),
   README audit-trail entry, js/app.js dataq-coverage-block date,
   dataq-phantom-block numbers (64 batches, $2,800,955,989 removed /
   $543,465,563 restored / net $2,257,490,426), dataq-payratio-block screen
   (CPT moves differ->near-0.5x: 394 within / 10 near 2x / 13 near 0.5x /
   97 differ, 514 screened).
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
    HERE, "compensation_backup_20260928_0200_pre_sync.json"))

verified_total = sum(v for k, v in cnt.items()
                     if k == "verified" or str(k).startswith("def14a_verified_"))
assert verified_total == 7044, verified_total
assert cnt["component_mismatch"] == 34, cnt["component_mismatch"]
assert cnt["def14a_verified_20260928"] == 18, cnt["def14a_verified_20260928"]
assert cnt["verified"] == 5656, cnt["verified"]
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
cpt = companies["CPT"]
s = sum(e["total"] for e in cpt["executives"] if e["year"] == cpt["fiscal_year"])
assert s == 21936889, f"CPT anchor {s}"
assert cpt["total_neo_compensation"] == 21936889
assert cpt["total_compensation"] == 4151948
assert cpt["ceo_name"] == "Alexander J. Jessett"
print("CPT anchors asserted: neo 21,936,889 / CEO 4,151,948")
pgr = companies["PGR"]
ps = sum(e["total"] for e in pgr["executives"] if e["year"] == pgr["fiscal_year"])
assert ps == pgr["total_neo_compensation"] == 33733783
print("PGR anchors asserted: neo 33,733,783 (2024 rows clean)")

# pay-ratio screen (guard section 11 rule)
w = t2 = h = o = 0
for c in data["companies"]:
    pr = c.get("pay_ratio"); mw = c.get("median_worker_pay")
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
print(f"pay-ratio screen: within={w} near2x={t2} near0.5x={h} differ={o}")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)

print("live recount:", dict(cnt))
print("verified_total:", verified_total, "| $1-$2 verified rows:", delta12)

# 3. README static copies
rm = os.path.join(REPO, "README.md")
txt = open(rm, encoding="utf-8").read()

txt2, n = re.subn(
    r"0 rounding-gap rows; last audit 2026-09-27;",
    "0 rounding-gap rows; last audit 2026-09-28;",
    txt, count=1)
assert n == 1, "README line-11 last-audit not found"
txt = txt2

# 4. append the 02:00 batch audit-trail entry
anchor = ("Guard section-8 tripwire fully drained (0 remaining); CPT 4-row "
          "salary==0/bonus==0 signature (Campo/Oden/Jessett/Baker 2025) still "
          "queued as a separate investigation.")
assert anchor in txt, "README audit-trail anchor not found"
entry = (anchor + " 2026-09-28 02:00 PT DQ batch: CPT queued investigation "
    "closed - 12-row whole-company SCT re-read from the 2026 DEF 14A "
    "(acc. 0001628280-26-021581, filed 2026-03-27) shows two corruption "
    "families: (A) classic salary-drop column shift on the 2024/2023 rows "
    "(8 rows: parser dropped the Salary cell, filing.stock->stored.salary, "
    "filing.neip->stored.stock, filing.all_other->stored.neip, "
    "filing.total->stored.all_other, stored.total recomputed ~1.9x); "
    "(B) split-currency variant on the 2025 rows (4 rows: the proxy renders "
    "the latest-year row with standalone '$' cells before each value, same "
    "rendering as LW's 2026-07-30 proxy; parser mapped "
    "filing.salary->stored.stock_awards, filing.stock->stored.all_other, "
    "dropped NEIP/All Other, recomputed total=salary+stock - stored "
    "UNDERSTATES the filing, e.g. Campo/Oden 2025 $5,663,589 vs filing "
    "$8,317,514). Sibling scan (salary==0 & bonus==0 & stock>0, 23 rows "
    "dataset-wide) caught PGR Griffith 2025 carrying the exact Family B "
    "signature; whole-company PGR re-read from the 2026 DEF 14A "
    "(acc. 0000080661-26-000099, filed 2026-03-23) shows Griffith 2025 = "
    "Family B ($12,094,509 vs filing $17,705,924) plus all five 2023 rows = "
    "Family A (Griffith 2023 $30,279,005 vs filing $15,636,618; Sauerland, "
    "Callahan, Bailo, Murphy 2023 same shift). PGR 2024 rows and all other "
    "2025 rows verified clean. 2023/2024 columns cross-checked identical vs "
    "the 2025 DEF 14As (CPT acc. 0000906345-25-000014; PGR "
    "acc. 0000080661-25-000018) - no restatements. CPT SCT NEIP composition "
    "spot-verified: NEIP = Performance Award Program payout + cash portion "
    "of annual bonus (Campo 2025: 2,313,245 + 337,680 = 2,650,925). All 18 "
    "rows foot exactly; 18 relabeled def14a_verified_20260928. FY2024 neo "
    "comp re-anchored: CPT $41,193,426->$21,936,889; CPT CEO "
    "total_compensation $7,676,133->$4,151,948 (Jessett FY2024 "
    "filing-verbatim); PGR aggregates already correct (2024 rows clean). "
    "Net batch phantom -$52,230,124 (CPT -$29,465,012, PGR -$22,765,112). "
    "verified_total unchanged at 7,044 (99.5%), component_mismatch unchanged "
    "at 34. Pay-ratio screen as of 2026-09-28: 394/514 within tolerance, 10 "
    "near 2x, 13 near 0.5x, 97 differ otherwise (CPT moves differ->near-0.5x "
    "on the corrected CEO anchor). Remaining salary==0/bonus==0/stock>0 "
    "rows triaged: TSLA Musk 2025 genuine ($158.36B verified), ARES 6 rows "
    "genuine partnership structure (rebuilt digit-by-digit 2026-09-24), "
    "RMD 8 rows + MRNA Bancel 2025 + HUM Shetty 2023/2024 + PGR Griffith "
    "2024-clean queued as separate investigations (distinct signatures, "
    "each needs its own filing re-read).")
txt = txt.replace(anchor, entry, 1)
open(rm, "w", encoding="utf-8").write(txt)

# js/app.js modal copies
js = os.path.join(REPO, "js", "app.js")
jst = open(js, encoding="utf-8").read()

jst2, n = re.subn(
    r"<div id=\"dataq-coverage-block\"><h4>Coverage \(last audit 2026-09-27\)</h4>",
    '<div id="dataq-coverage-block"><h4>Coverage (last audit 2026-09-28)</h4>',
    jst, count=1)
assert n == 1, "js coverage-block not found"
jst = jst2

jst2, n = re.subn(
    r"<div id=\"dataq-phantom-block\"><h4>Phantom compensation removed \(as of the 2026-09-27 screen\)</h4>' \+\n"
    r"\s*'<p>\$2,748,725,865 of parser-invented compensation removed across 63 re-verification batches since 2026-09-12, partly offset by \$543,465,563 of genuine missing NEO rows restored filing-verbatim\. Net: \$2,205,260,302\.</p></div>'",
    '<div id="dataq-phantom-block"><h4>Phantom compensation removed (as of the 2026-09-28 screen)</h4>\' +\n'
    "                '<p>$2,800,955,989 of parser-invented compensation removed across 64 re-verification batches since 2026-09-12, partly offset by $543,465,563 of genuine missing NEO rows restored filing-verbatim. Net: $2,257,490,426.</p></div>'",
    jst, count=1)
assert n == 1, "js phantom-block not found"
jst = jst2

jst2, n = re.subn(
    r"As of the 2026-09-27 screen: 394 of 514 screened companies\\' disclosed ratios match <code>total_compensation / median_worker_pay</code> within 3% tolerance; 10 cluster near 2x, 12 near 0\.5x, 98 differ otherwise\.",
    "As of the 2026-09-28 screen: 394 of 514 screened companies\\\\' disclosed ratios match <code>total_compensation / median_worker_pay</code> within 3% tolerance; 10 cluster near 2x, 13 near 0.5x, 97 differ otherwise.",
    jst, count=1)
assert n == 1, "js payratio-block not found"
jst = jst2

open(js, "w", encoding="utf-8").write(jst)
print("sync complete")
