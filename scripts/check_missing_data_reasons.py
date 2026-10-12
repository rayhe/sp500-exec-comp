#!/usr/bin/env python3
"""Regression guard: MISSING_DATA_REASONS entries must describe the CURRENT
anchor-year data state.

New failure-mode class (2026-10-11 23:30 PT run): static reason strings keyed
to data that has since arrived. getMissingDataHtml() (js/app.js:1366) and
the detail-panel "Incomplete data" notice (js/app.js:10940) render the
MISSING_DATA_REASONS[ticker] note only when the company's ANCHOR pay_ratio /
median_worker_pay is missing. An entry whose company now HAS both fields is
a dormant stale claim: invisible today, misleading the moment the note would
render (e.g. SOLV/GEV/SW each carried an FY2024-era reason - "spun off ...
no full-year proxy data available for FY2024", "no FY2024 pay ratio
disclosed" - while the live anchor rows already carried FY2025 pay ratios
245:1, 282:1, 271:1 from the 2026 DEF 14A). The 2026-09-17 run set the
precedent: TSLA's stale "Pay ratio not computed" note was removed, not
rewritten, when the 10-K/A ratio shipped.

Checks (static, fast, runs in the pre-commit hook):
  S1 for every ticker in MISSING_DATA_REASONS, the company's anchor record
     in data/compensation.json must be genuinely missing at least one of
     pay_ratio (null or <= 0) / median_worker_pay (null or falsy). If the
     company has both, the entry is dormant and its reason string is a
     stale claim - remove the entry or rewrite the reason.
  S2 every MISSING_DATA_REASONS ticker must exist in compensation.json;
     an entry for a ticker absent from the dataset can never render.
  S3 the exact stale FY2024-era reason strings are absent (regression trip
     for this bug).

Usage:
  scripts/check_missing_data_reasons.py
  scripts/check_missing_data_reasons.py --static-only

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

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def extract_reasons(src):
    """Return dict of ticker -> reason from the MISSING_DATA_REASONS literal."""
    m = re.search(r"var MISSING_DATA_REASONS = \{(.*?)\};", src, re.S)
    if not m:
        return None
    pairs = re.findall(r"['\"]([A-Z.\-]{1,8})['\"]\s*:\s*['\"](.*?)['\"]\s*,?\s*$",
                       m.group(1), re.M)
    return dict(pairs)


def main():
    static_only = "--static-only" in sys.argv
    try:
        with open(APP_JS, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print("INFRA: cannot read js/app.js: %s" % e)
        return 2
    reasons = extract_reasons(src)
    if reasons is None:
        check("S1/S2: MISSING_DATA_REASONS literal parse", False,
              "could not locate 'var MISSING_DATA_REASONS = {...};' in js/app.js")
        ok = False
    else:
        ok = True
        try:
            with open(COMP_JSON, "r", encoding="utf-8") as f:
                comp = json.load(f)
        except OSError as e:
            print("INFRA: cannot read data/compensation.json: %s" % e)
            return 2
        idx = {c.get("ticker"): c for c in comp.get("companies", [])}
        stale = []
        missing_ticker = []
        for t, reason in reasons.items():
            c = idx.get(t)
            if c is None:
                missing_ticker.append(t)
                continue
            pr = c.get("pay_ratio")
            mwp = c.get("median_worker_pay")
            if (pr is not None and pr > 0) and mwp:
                stale.append("%s (anchor pay_ratio=%s, median_worker_pay=%s)"
                             % (t, pr, mwp))
        check("S1: every entry's company genuinely lacks anchor data",
              not stale, "; ".join(stale) if stale else
              "%d entr%s verified dormant-free" %
              (len(reasons), "y" if len(reasons) == 1 else "ies"))
        check("S2: every entry's ticker exists in compensation.json",
              not missing_ticker, "; ".join(missing_ticker) if missing_ticker
              else "all present")
        ok = not stale and not missing_ticker
    for bad in ("no full-year proxy data available for FY2024",
                "no FY2024 pay ratio disclosed"):
        found = bad in src
        check("S3: stale FY2024-era reason string absent: %r" % bad, not found,
              "still present in js/app.js" if found else "")
        ok = ok and not found
    return 0 if ok and all(r[1] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
