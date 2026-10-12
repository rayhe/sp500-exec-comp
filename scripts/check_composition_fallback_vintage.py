#!/usr/bin/env python3
"""Regression guard: composition fallback defaults must not fossilize a superseded study edition.

Background (2026-10-12 07:30 PT run): drawCompositionChart() in js/charts.js
carried a dormant 4-segment fallback branch (renders only when no granular
detail edition exists in trends.json) whose `||` defaults were bare FY2024
Equilar/AP 2025 edition constants (71.6 / 7.6 / 1.7 / $17.1M implied total),
frozen by the 2026-10-12 FY2025 survey promotion. The same branch's source
note defaulted the survey label to 'Equilar/AP 2025' and the FY label to
2024. The class: dormant-stale literals that silently resurrect a superseded
study edition the moment the data drops a field (cf. the MISSING_DATA_REASONS
dormant-string class, 2026-10-11 23:35 PT; the five-year fallback mirrors the
live data's window, 2026-10-11 18:00 PT; and the ratio-vintage S2
data-coupled-claim pattern, 2026-10-12 02:00 PT).

The fix: fallback defaults read the year-keyed s_and_p_500_fy2024 edition
live (vintage-explicit) before falling to comment-labeled raw backstops; the
survey-edition and FY defaults mirror the current edition.

Checks (static only):
  S1 js/charts.js contains no bare 'Equilar/AP 2025' literal (the superseded
     survey edition must not survive as a current-edition default).
  S2 the composition fallback branch contains no direct
     `sp.stock_awards_pct || 71.6` (a default must hop through the
     year-keyed FY2024 edition first).
  S3 the FY-label backstop in the composition source-note line equals the
     live top-level s_and_p_500 fiscal_year from data/trends.json (the
     dormant literal is coupled to the data; an FY2026 promotion trips it).
  S4 every remaining final-backstop literal of the FY2024 constants
     (71.6, 7.6, 1.7, 17100000) in js/charts.js sits on a line carrying an
     FY2024 vintage comment.

Usage:
  scripts/check_composition_fallback_vintage.py
  scripts/check_composition_fallback_vintage.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
TRENDS_JSON = os.path.join(REPO, "data", "trends.json")

FAILURES = []


def fail(msg):
    FAILURES.append(msg)
    print("FAIL: %s" % msg)


def main():
    if "--static-only" in sys.argv:
        pass
    try:
        charts = open(CHARTS_JS, encoding="utf-8").read()
    except OSError as e:
        print("INFRA: cannot read js/charts.js: %s" % e)
        return 2

    # S1: no bare superseded survey-edition default. Comment text is
    # stripped first: historical references to the FY2024 edition in
    # comments (e.g. the VINTAGE NOTE) are vintage honesty, not defaults.
    code = re.sub(r"/\*.*?\*/", "", charts, flags=re.S)
    code = re.sub(r"//[^\n]*", "", code)
    if "Equilar/AP 2025" in code:
        fail("S1: js/charts.js still carries the 'Equilar/AP 2025' literal outside "
             "comments; the survey-edition default must mirror the current edition "
             "(Equilar/AP 2026 as of the 2026-10-12 FY2025 promotion)")

    # S2: no direct bare-constant default for stock_awards_pct
    if re.search(r"sp\.stock_awards_pct\s*\|\|\s*71\.6", charts):
        fail("S2: js/charts.js still has 'sp.stock_awards_pct || 71.6'; the "
             "fallback must hop through the year-keyed s_and_p_500_fy2024 "
             "edition first (vintage-explicit)")

    # S3: FY-label backstop coupled to the live top-level fiscal_year
    try:
        trends = json.load(open(TRENDS_JSON, encoding="utf-8"))
        live_fy = str(trends["compensation_composition"]["s_and_p_500"]["fiscal_year"])
    except (OSError, KeyError, ValueError) as e:
        print("INFRA: cannot read live fiscal_year from trends.json: %s" % e)
        return 2
    m = re.search(r"compDetailYear\s*\|\|\s*sp\.fiscal_year\s*\|\|\s*(\d{4})", charts)
    if not m:
        fail("S3: composition source-note FY expression not found in js/charts.js "
             "(expected 'compDetailYear || sp.fiscal_year || <YYYY>')")
    elif m.group(1) != live_fy:
        fail("S3: composition FY-label backstop is %s but the live top-level "
             "s_and_p_500 fiscal_year in trends.json is %s; update the dormant "
             "literal to mirror the data" % (m.group(1), live_fy))

    # S4: every remaining FY2024 final-backstop literal is vintage-labeled
    for lit in ["71.6", "7.6", "1.7", "17100000"]:
        pat = r"(?<![\d.])" + re.escape(lit) + r"(?![\d])"
        for i, line in enumerate(charts.split("\n"), 1):
            if re.search(pat, line) and "FY2024" not in line:
                fail("S4: js/charts.js:%d carries the FY2024 final-backstop "
                     "literal '%s' without an FY2024 vintage comment on the "
                     "line" % (i, lit))

    if FAILURES:
        print("check_composition_fallback_vintage: %d FAIL" % len(FAILURES))
        return 1
    print("check_composition_fallback_vintage: PASS (S1-S4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
