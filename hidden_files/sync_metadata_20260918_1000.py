#!/usr/bin/env python3
"""2026-09-18 10:00 PT post-batch metadata + static-copy sync.

Brings the repo back under the check_metadata_consistency.py guard after the
10:00 PT DQ batch:
1. Re-anchors the 6 flagged companies' aggregates to their fiscal_year rows
   (site convention: aggregates anchor to fiscal_year, enforced by the guard;
   the 06:00 batch's tickers already comply).
2. Recounts data_quality / data_quality_detailed buckets from live
   _total_source labels (canonical keys), recomputes verified_total, sets
   last_audit=2026-09-18 in both blocks, title_coverage=6843/6843.
3. Syncs hand-typed headline numbers in README.md / index.html / js/app.js and
   appends the batch audit-trail entry to README.
"""
import json
import os
import shutil
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
REPO = os.path.join(HERE, "..")

LABEL_TO_KEY = {
    "verified": "verified",
    "DEF14A-verified 2026-09-07": "def14a_verified_20260907",
    "DEF14A-verified 2026-09-08": "def14a_verified_20260908",
    "DEF14A-verified 2026-09-09": "def14a_verified_20260909",
    "DEF14A-verified 2026-09-10": "def14a_verified_20260910",
    "recomputed": "recomputed",
    "rounding": "rounding",
    "incomplete_components": "incomplete_components",
    "bloated_component": "bloated_component",
    "recomputed_implausible_total": "recomputed_implausible_total",
    "def14a_verified_20260907": "def14a_verified_20260907",
    "def14a_verified_20260908": "def14a_verified_20260908",
    "def14a_verified_20260909": "def14a_verified_20260909",
    "def14a_verified_20260910": "def14a_verified_20260910",
    "def14a_verified_20260912": "def14a_verified_20260912",
    "def14a_verified_20260916": "def14a_verified_20260916",
    "def14a_verified_20260917": "def14a_verified_20260917",
    "def14a_verified_20260918": "def14a_verified_20260918",
    "component_mismatch": "component_mismatch",
}
VERIFIED_KEYS = {"verified"} | {k for k in LABEL_TO_KEY.values()
                                if k.startswith("def14a_verified_")}

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
shutil.copy2(JSON_PATH, os.path.join(HERE, "compensation_backup_20260918_1000_pre_sync.json"))
companies = {c["ticker"]: c for c in data["companies"]}
n = sum(len(c["executives"]) for c in data["companies"])

# 1. re-anchor aggregates to fiscal_year (guard-enforced convention)
for ticker in ("SMCI", "ROP", "MET", "TRGP", "VRSN", "FRT"):
    c = companies[ticker]
    fy = c["fiscal_year"]
    rows = [e for e in c["executives"] if e["year"] == fy]
    old = (c["total_neo_compensation"], c["neo_count"])
    c["total_neo_compensation"] = sum(e["total"] for e in rows)
    c["neo_count"] = len(rows)
    print(f"{ticker}: FY{fy} agg {old[0]} -> {c['total_neo_compensation']}, n {old[1]} -> {c['neo_count']}")

# 2. recount buckets
cnt = Counter()
for c in data["companies"]:
    for e in c["executives"]:
        cnt[LABEL_TO_KEY.get(e["_total_source"], e["_total_source"])] += 1
vt = sum(cnt.get(k, 0) for k in VERIFIED_KEYS)
meta = data["metadata"]
for block_name in ("data_quality", "data_quality_detailed"):
    block = meta[block_name]
    for key in set(LABEL_TO_KEY.values()):
        if key in block:
            block[key] = cnt.get(key, 0)
    block["verified_total"] = vt
    block["last_audit"] = "2026-09-18"
meta["title_coverage"] = f"{n}/{n}"
pct = f"{vt / n * 100:.1f}%"
rounding = meta["data_quality"].get("rounding", 0)
recomputed = meta["data_quality"].get("recomputed", 0)
mismatch = meta["data_quality"].get("component_mismatch", 0)
print(f"n={n} vt={vt} pct={pct} rounding={rounding} recomputed={recomputed} mismatch={mismatch}")

# $1-$2 delta recount (8-component set, verified-family rows only)
F8 = ["salary", "bonus", "stock_awards", "option_awards", "non_equity_incentive",
      "pension_nqdc", "pension_change", "all_other"]
n12 = 0
for c in data["companies"]:
    for r in c["executives"]:
        src = r.get("_total_source", "")
        if src != "verified" and not src.startswith("def14a_verified"):
            continue
        s = sum(r.get(k) if isinstance(r.get(k), int) else 0 for k in F8)
        if abs(s - (r.get("total") or 0)) in (1, 2):
            n12 += 1
print("n12 =", n12)

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, separators=(",", ":"))

# 3. static-copy sync
def sub(path, old, new, count=1):
    p = os.path.join(REPO, path)
    with open(p, encoding="utf-8") as f:
        text = f.read()
    assert text.count(old) >= count, f"{path}: pattern not found: {old[:70]!r} (count {text.count(old)})"
    text = text.replace(old, new, count)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{path}: replaced {old[:60]!r}...")

fv = lambda x: f"{x:,}"
sub("README.md",
    "99.7% verified component-total consistency (6,798 of 6,819 records, "
    "21 filing-side component mismatches, 0 rounding-gap rows; last audit 2026-09-12",
    f"{pct} verified component-total consistency ({fv(vt)} of {fv(n)} records, "
    f"{mismatch} filing-side component mismatches, 0 rounding-gap rows; last audit 2026-09-18")
sub("README.md",
    "| `verified` | Components and total match the filing SCT verbatim. "
    "Includes `def14a_verified_YYYYMMDD` re-verification passes | 6,798 (99.7%) |",
    f"| `verified` | Components and total match the filing SCT verbatim. "
    f"Includes `def14a_verified_YYYYMMDD` re-verification passes | {fv(vt)} ({pct}) |")
sub("README.md",
    "Component-total consistency verified: 99.7% verified (6,798 of 6,819 total NEO records), "
    "0 rounding-gap rows, 0 recomputed",
    f"Component-total consistency verified: {pct} verified ({fv(vt)} of {fv(n)} total NEO records), "
    "0 rounding-gap rows, 0 recomputed")
sub("README.md",
    "21 filing-side component mismatches (WAB 2023 CHF-conversion artifact",
    f"{mismatch} filing-side component mismatches (WAB 2023 CHF-conversion artifact")
sub("README.md", "6,819 rows):", f"{fv(n)} rows):")
sub("README.md", "307 `verified` rows carry $1\u2013$2 deltas",
    f"{n12} `verified` rows carry $1\u2013$2 deltas")
sub("index.html", "6,819 Named Executive Officer records",
    f"{fv(n)} Named Executive Officer records")
sub("js/app.js",
    "6,798 of 6,819 NEO rows verified (99.7%): 0 rounding, 0 recomputed, 21 component_mismatch",
    f"{fv(vt)} of {fv(n)} NEO rows verified ({pct}): 0 rounding, 0 recomputed, {mismatch} component_mismatch")
sub("js/app.js", "307 <em>verified</em> rows carry $1&ndash;$2 deltas",
    f"{n12} <em>verified</em> rows carry $1&ndash;$2 deltas")
sub("js/app.js", "Coverage (last audit 2026-09-12)", "Coverage (last audit 2026-09-18)")
sub("js/app.js", "|| '2026-09-12'", "|| '2026-09-18'")

# 4. README audit-trail entry for this batch
trail = (
    " 2026-09-18 10:00 PT batch: missing-NEO-row restoration across 5 thin-coverage companies "
    "(24 rows: SMCI x2 Liang 2023/2025, TRGP x8 Pryor/McDonie/Muraro/Byers, CTRA x4 Sirgo/DeShazer, "
    "VRSN x4 Kilguss/Calys, MET x6 McCallion/Debel - all filing-verbatim from 2026 DEF 14A SCTs, "
    "15 filings re-fetched from EDGAR) + MET 9-row column-shift repair (SCT has no Bonus column; "
    "stock->bonus and option->stock mislabeled, now foot exactly) + FRT 7-row salary/bonus shift "
    "repair (salary zeroed and filed under bonus; Wood 2025 / Guglielmone 2024+2023 / Becker 2024 "
    "$1 filing-side gaps kept verbatim, component_mismatch) + CPRT Stearns 2023 fabricated-"
    "reconciliation revert (all_other 5295->5250 filing-verbatim, -$45 filing-side gap) + "
    "SCT-verbatim title sync across all 15 companies + name merges (ROP Neil Hunn->L. Neil Hunn, "
    "MET Michel A Khalaf->Michel A. Khalaf, IPG Christopher F. Carroll->Christopher Carroll); "
    "company aggregates re-anchored to primary fiscal_year on all 9 touched tickers; 24 rows "
    f"labeled def14a_verified_20260918; $1-$2 delta rows {n12}; headline buckets {pct} "
    f"({fv(vt)}/{fv(n)})."
)
p = os.path.join(REPO, "README.md")
with open(p, encoding="utf-8") as f:
    text = f.read()
anchor = "headline buckets 99.7% (6,798/6,819)."
assert anchor in text, "audit-trail anchor not found"
text = text.replace(anchor, anchor + trail, 1)
with open(p, "w", encoding="utf-8") as f:
    f.write(text)
print("README: audit-trail entry appended")
