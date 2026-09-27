#!/usr/bin/env python3
"""2026-09-27 10:00 PT post-batch metadata + static-copy sync (PCG/FITB).

Follows the sync_metadata_20260918_1000.py pattern:
1. Recount data_quality / data_quality_detailed buckets from live
   _total_source labels (9 rows moved verified -> def14a_verified_20260927);
   verified_total unchanged at 7046; last_audit=2026-09-27.
2. Sync the $1-$2 verified-delta modal copies in README.md and js/app.js
   (326 -> 328: PCG Glickman 2024 and Singh 2024 now foot with $1
   filing-side deltas after repair, staying `verified` per taxonomy).
3. Append the batch audit-trail entry to the README methodology log.
"""
import json
import os
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
        # guard-exact $1-$2 recount: 8-component set over the verified family
        if lab == "verified" or str(lab).startswith("def14a_verified"):
            s = sum(_int_or_zero(e.get(k)) for k in COMP8)
            if abs(s - _int_or_zero(e.get("total"))) in (1, 2):
                delta12 += 1

shutil.copy2(JSON_PATH, os.path.join(
    HERE, "compensation_backup_20260927_1000_pre_sync.json"))

verified_total = sum(v for k, v in cnt.items()
                     if k == "verified" or str(k).startswith("def14a_verified_"))

for block_key in ("data_quality", "data_quality_detailed"):
    block = data["metadata"][block_key]
    block.clear()
    for k in sorted(cnt.keys()):
        block[k] = cnt[k]
    # preserve canonical key order style: keep insertion sorted, then move
    # the aggregate keys to the end like previous batches
    ordered = {}
    for k in sorted(cnt.keys()):
        if k not in ("verified_total", "last_audit"):
            ordered[k] = cnt[k]
    # keep explicit rounding:0 (guard reads it with no .get default; absence
    # renders "None rounding-gap rows" in the static-copy check)
    if "rounding" not in ordered:
        ordered["rounding"] = 0
    ordered["verified_total"] = verified_total
    ordered["last_audit"] = "2026-09-27"
    block.clear()
    block.update(ordered)

print("live recount:", dict(cnt))
print("verified_total:", verified_total, "| $1-$2 verified rows:", delta12)
assert verified_total == 7046, verified_total

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)

# 2. sync modal copies (guard-exact delta recount; idempotent regex replace)
import re
rm = os.path.join(REPO, "README.md")
txt = open(rm, encoding="utf-8").read()
txt2, n_rm = re.subn(r"\d+ `verified` rows carry \$1",
                     f"{delta12} `verified` rows carry $1", txt, count=1)
assert n_rm == 1, "README modal copy not found"
txt = txt2

js = os.path.join(REPO, "js", "app.js")
jst = open(js, encoding="utf-8").read()
jst2, n_js = re.subn(r"\d+ <em>verified</em> rows carry \$1",
                     f"{delta12} <em>verified</em> rows carry $1", jst, count=1)
assert n_js == 1, "js modal copy not found"
jst = jst2
open(js, "w", encoding="utf-8").write(jst)
open(rm, "w", encoding="utf-8").write(txt)  # persist modal sync even when audit-trail is skipped

# 3. append batch audit-trail entry to the README methodology log (idempotent)
entry = (
    " 2026-09-27 10:00 PT DQ batch: PCG (5 rows) + FITB (4 rows) salary-drop"
    " column-shift repair, same family as the 06:00 PT DG batch — the parser"
    " dropped the Salary cell, filing.stock->stored.bonus and every component"
    " one column left, filing total->stored.all_other, stored total recomputed"
    " ~2x. All 9 repaired filing-verbatim: PCG 2024 rows (Glickman, Singh,"
    " Waghray) from the 2026 DEF 14A SCT (acc. 0001004980-26-000020, table"
    " 111; name->row mapping anchored by the (6) pension footnote dollars);"
    " PCG 2023 rows (Glickman, Williams) from the 2025 DEF 14A SCT"
    " (acc. 0001004980-25-000073, table 118); FITB 2024 (Preston) from the"
    " 2026 DEF 14A SCT (acc. 0001193125-26-098679, table 282); FITB 2023"
    " (Leonard, Shaffer, Lavender) from the 2025 DEF 14A SCT"
    " (acc. 0001193125-25-045653, table 280), cross-checked identical between"
    " the 2025 and 2026 proxies. Glickman 2024 and Singh 2024 foot with $1"
    " filing-side deltas (stay `verified` per taxonomy); all others foot"
    " exactly. PCG FY2024 neo comp re-anchored $63,543,232->$54,976,924"
    " (Glickman -$2,539,985; Singh -$3,754,998; Waghray -$2,271,325) and"
    " FITB FY2024 neo comp re-anchored $40,135,176->$38,168,200 (Preston"
    " -$1,966,976); 2023 rows repaired but not anchor year (Glickman"
    " -$3,005,429; Williams -$952,756; Leonard -$2,748,644; Shaffer"
    " -$1,889,976; Lavender -$1,864,495); ~$21.0M phantom compensation"
    " removed; 9 rows relabeled def14a_verified_20260927; verified_total"
    " unchanged at 7,046/7,078 (99.5%); guard section-8 candidate set now"
    " 33 rows / 13 tickers."
)
anchor = "guard section 8 widened to the generalized band (1 < tot/ao < 2, salary-plausible absolute gap) - 37 remaining candidate rows across 15 tickers now warn for filing-by-filing verification; verified_total 7,046/7,078 (99.5%)."
assert anchor in txt, "README methodology anchor not found"
if "2026-09-27 10:00 PT DQ batch" not in txt:
    txt = txt.replace(anchor, anchor + entry, 1)
    open(rm, "w", encoding="utf-8").write(txt)
    print("audit-trail appended")
else:
    print("audit-trail already present; skipped duplicate append")
print("README + js/app.js synced")
