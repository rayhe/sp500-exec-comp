#!/usr/bin/env python3
"""Regression guard: the dataq pay-ratio "Fiscal-year roll" bullet's vintage
claim must stay data-true.

New failure-mode class (2026-10-12 02:00 PT run): a documented deviation
claim whose truth lives in the data, not in the copy. The dataq pay-ratio
methodology modal's "Fiscal-year roll" bullet says the anchor reflects
FY2025 SCT totals "while the disclosed ratio and median worker pay remain
the FY2024 figures from the 2025 proxy season". The existing
check_payratio_proxyseason_copy.py only asserts the bullet is
SELF-consistent (P == Y+1) - nothing asserts the claim matches the data.

Filing-grounded spot verification this run (2026 DEF 14A pay-ratio
disclosures vs stored fields):
  AAPL stored 650:1 / $114,738 - 2026 proxy discloses 533:1 / $139,483
    (FY2025); stored pair is the 2025 proxy's FY2024 figure.
  MO   stored 169:1 / $158,795 - 2026 proxy discloses 147:1 / $166,721
    (FY2025); stored pair is the 2025 proxy's FY2024 figure.
  META stored median $417,400   - 2026 proxy discloses $388,200 (FY2025);
    stored median is FY2024-vintage (ratio 65:1 coincidentally matches).
The FY2025 anchor promotion (2026-10-06) moved SCT totals without
re-extracting pay-ratio fields, so the bullet's claim is TRUE today - but if
a future pipeline refresh re-extracts ratios to FY2025, the bullet becomes
the fossilized false claim of the 2026-10-11 23:30 class. This guard is the
tripwire: it classifies each company's ratio vintage from the data
(ratio x median vs CEO-name-matched FY2024/FY2025 SCT totals, 3% band,
exactly one year matching = distinguishable) and requires the FY2024
majority the bullet asserts.

Checks (static, fast, runs in the pre-commit hook):
  S1 the bullet still carries the FY2024-vintage claim (couples guard to
     copy: rewriting the bullet forces a conscious guard update).
  S2 of the vintage-distinguishable companies, >= 75% are FY2024-vintage.
     Currently 87% (316/362); a genuine FY2025 ratio refresh flips the
     majority and trips the guard.

Usage:
  scripts/check_payratio_vintage_truth.py
  scripts/check_payratio_vintage_truth.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")
COMP_JSON = os.path.join(REPO, "data", "compensation.json")

THRESHOLD = 0.75

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def name_parts(name):
    toks = [p for p in name.replace(".", "").split() if p]
    if len(toks) >= 2:
        return toks[0], toks[-1]
    return (toks[0], "") if toks else ("", "")


def classify(companies):
    fy24 = fy25 = 0
    for c in companies:
        r = c.get("pay_ratio")
        m = c.get("median_worker_pay")
        if not (r and m):
            continue
        fn, ln = name_parts(c.get("ceo_name", ""))
        if not (fn and ln):
            continue
        tot = {}
        for e in c.get("executives", []):
            nm = e.get("name", "")
            if fn in nm and ln in nm and e.get("year") in (2024, 2025) and e.get("total"):
                tot[e["year"]] = e["total"]
        if 2024 not in tot or 2025 not in tot:
            continue
        target = r * m
        d24 = abs(tot[2024] - target) / tot[2024]
        d25 = abs(tot[2025] - target) / tot[2025]
        if d24 < 0.03 and d25 >= 0.03:
            fy24 += 1
        elif d25 < 0.03 and d24 >= 0.03:
            fy25 += 1
    return fy24, fy25


def main():
    try:
        with open(APP_JS, encoding="utf-8") as f:
            src = f.read()
        with open(COMP_JSON, encoding="utf-8") as f:
            comp = json.load(f)
    except OSError as e:
        print("INFRA: cannot read inputs -", e)
        return 2

    claim = "remain the FY2024 figures from the 2025 proxy season"
    check(
        "S1 bullet carries FY2024-vintage claim",
        claim in src,
        "claim present" if claim in src else "bullet rewritten - update this guard",
    )

    fy24, fy25 = classify(comp.get("companies", []))
    denom = fy24 + fy25
    share = (fy24 / denom) if denom else 0.0
    check(
        "S2 FY2024-vintage majority holds",
        share >= THRESHOLD,
        "FY2024 %d / distinguishable %d = %.1f%% (threshold %.0f%%)"
        % (fy24, denom, 100 * share, 100 * THRESHOLD),
    )

    fails = [n for n, ok, _ in results if not ok]
    return 1 if fails else 0


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        pass  # contract literal; checks are static-only by construction
    sys.exit(main())
