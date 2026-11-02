#!/usr/bin/env python3
"""Guard: the component_mismatch queue cannot silently drift.

Background: _total_source == 'component_mismatch' marks NEO rows whose
SCT components do not sum to the filing-printed total. The queue holds
three intentional classes (307th review, 2026-11-01, adjudicated
filing-verbatim):
  1. genuine >$2 filing-side arithmetic gaps (8 rows; e.g. FDS Shan 2023
     $30,936, NEE Sieving 2023 $50,001) - re-verified, labels retained;
  2. $1 filing-side rounding gaps (19 rows) - documented in the
     enrichment-review commit messages, labels retained;
  3. incomplete component columns where the filing's SCT has no such
     column (17 rows; e.g. APH stock_awards n/a, CDNS/RF/TSCO SCTs that
     do not foot) - re-verified, labels retained.
The one resolvable row (CLX Bellet 2025) was repaired in the 307th
review when the 2026 proxy restated the total to the component sum.

Checks (all static - one JSON load, <2s):
  Q1 HARD FAIL: any executive row with complete components whose
     |sum - total| > 2 is NOT tagged component_mismatch. A new untagged
     mismatch is the column-shift / dropped-column parse-error class
     (277th/278th/306th reviews) escaping review.
  Q2 HARD FAIL: any row tagged component_mismatch whose complete
     components sum EXACTLY to the stored total. A diff-0 tagged row is
     definitionally stale - the tag must be cleared (the CLX repair is
     the precedent).

The intentional classes print as INFO and never block: a $1-gap row
(0 < |diff| <= 2, tagged) or an incomplete-column row (tagged, some
component None) is expected population, reported for the run log.

Usage:
  scripts/check_component_mismatch_queue.py              # same checks
  scripts/check_component_mismatch_queue.py --static-only # same checks

Exit: 0 = queue consistent; 1 = drift (loud); 2 = infra (JSON unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import sys

REPO = "/home/hatch/repos/sp500-exec-comp"
DATA = f"{REPO}/data/compensation.json"
COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]

if "--static-only" in sys.argv:
    pass  # static half is the whole check; flag accepted for the hook runner

try:
    data = json.load(open(DATA, encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    print(f"INFRA: cannot read {DATA}: {exc}")
    sys.exit(2)

untagged = []   # Q1 violations
stale = []      # Q2 violations
n_dollar_gap = 0
n_genuine = 0
n_incomplete = 0

for c in data["companies"]:
    for e in c.get("executives", []):
        if e.get("_total_source") != "component_mismatch":
            vals = [e.get(k) for k in COMPS]
            if e.get("total") is None or any(v is None for v in vals):
                continue
            if abs(sum(vals) - e["total"]) > 2:
                untagged.append(
                    f"{c['ticker']} {e['name']} {e['year']}: "
                    f"sum={sum(vals)} total={e['total']}")
            continue
        # tagged rows: classify
        vals = [e.get(k) for k in COMPS]
        if e.get("total") is None or any(v is None for v in vals):
            n_incomplete += 1
            continue
        diff = sum(vals) - e["total"]
        if diff == 0:
            stale.append(f"{c['ticker']} {e['name']} {e['year']}")
        elif abs(diff) <= 2:
            n_dollar_gap += 1
        else:
            n_genuine += 1

print(f"component_mismatch queue: {n_genuine} genuine >$2 gaps, "
      f"{n_dollar_gap} $1 rounding gaps, {n_incomplete} incomplete-column rows")

failures = []
if untagged:
    failures.append("Q1 untagged >$2 component mismatches (parse-error class):")
    failures.extend(f"  {u}" for u in untagged)
if stale:
    failures.append("Q2 fully-stale component_mismatch tags (diff == 0, clear them):")
    failures.extend(f"  {s}" for s in stale)

if failures:
    print("FAIL:")
    print("\n".join(failures))
    sys.exit(1)

print("PASS: no untagged mismatches, no stale tags")
sys.exit(0)
