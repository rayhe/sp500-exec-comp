#!/usr/bin/env python3
"""Regression guard: composition aggregate blocks must vintage-match their detail editions.

Background (2026-10-12 06:00 PT run): the composition donut's granular
detail field is year-keyed (s_and_p_500_fy<YYYY>_detail), but the salary and
perks segments in the granular branch read from the TOP-LEVEL s_and_p_500
aggregate block, and the source note labeled the fiscal year from that same
top-level block. When the top-level block was promoted to the FY2025
AP/Equilar 2026 survey while the only detail edition was FY2024 (Harvard Law
School Forum), the donut would have rendered FY2024 granular segments with
FY2025 salary/perks values under an "FY2024" title, and a source note
claiming "Harvard Law School Forum (Dec 2025) -- FY2025". The class:
aggregate-block/detail-block vintage mismatch -- the same stale-year family
as the Composition Mix Detail fixes, but through the top-level aggregate,
not a hard-coded key.

The fix: charts.js resolves the detail year once (compDetailYear), builds
the granular segments' salary/perks from the year-matched
s_and_p_500_fy<YYYY> aggregate block (falling back to the top-level block
only when no year-matched edition exists), and the source note labels the
detail year when a detail edition is active.

Checks (static only):
  S1 every s_and_p_500_fy<YYYY>_detail key in data/trends.json has a
     sibling s_and_p_500_fy<YYYY> aggregate key with fiscal_year == YYYY.
  S2 the top-level s_and_p_500 aggregate's fiscal_year is >= the latest
     detail year (the aggregate edition must never lag the detail edition).
  S3 the granular segment branch of drawCompositionChart() (from
     `if (detail && detail.median_performance_stock_awards)` to its
     `} else {`) contains no bare sp.median_salary / sp.median_perks /
     sp.perks_yoy_change references (it must use the year-matched block).
  S4 the composition source-note line couples the FY label to the detail
     year (compDetailYear takes precedence over sp.fiscal_year).

Usage:
  scripts/check_composition_vintage_match.py              # static checks
  scripts/check_composition_vintage_match.py --static-only # same (pre-commit contract)

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRENDS_JSON = os.path.join(REPO, "data", "trends.json")
CHARTS_JS = os.path.join(REPO, "js", "charts.js")

FAIL = []
PASS = []

def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("PASS" if ok else "FAIL") + ": " + name + (" -- " + detail if detail else ""))

def main():
    if "--static-only" in sys.argv:
        pass

    try:
        trends = json.load(open(TRENDS_JSON))
    except Exception as e:
        print("INFRA: cannot load trends.json: %s" % e)
        return 2
    comp = (trends or {}).get("compensation_composition") or {}

    detail_years = sorted({
        int(m.group(1))
        for k in comp.keys()
        for m in [re.match(r"^s_and_p_500_fy(\d{4})_detail$", k)]
        if m
    })

    # S1: every detail edition has a same-year aggregate sibling
    s1_ok = True
    for y in detail_years:
        key = "s_and_p_500_fy%d" % y
        agg = comp.get(key)
        if not isinstance(agg, dict) or agg.get("fiscal_year") != y:
            s1_ok = False
            check("S1 detail %d has same-year aggregate block" % y, False,
                  "missing or fiscal_year != %d" % y)
    if detail_years and s1_ok:
        check("S1 all detail editions have same-year aggregate blocks", True,
              "years: %s" % ", ".join(str(y) for y in detail_years))
    elif not detail_years:
        check("S1 all detail editions have same-year aggregate blocks", True,
              "no detail editions (vacuous)")

    # S2: top-level aggregate never lags the detail editions
    top = comp.get("s_and_p_500") or {}
    top_fy = top.get("fiscal_year")
    if detail_years:
        check("S2 top-level aggregate fiscal_year >= latest detail year",
              top_fy is not None and top_fy >= max(detail_years),
              "top FY%s vs detail %d" % (top_fy, max(detail_years)))
    else:
        check("S2 top-level aggregate fiscal_year >= latest detail year", True,
              "no detail editions (vacuous)")

    try:
        src = open(CHARTS_JS).read()
    except Exception as e:
        print("INFRA: cannot read js/charts.js: %s" % e)
        return 2

    # S3: granular branch uses the year-matched block, not bare sp.
    m = re.search(
        r"if\s*\(\s*detail\s*&&\s*detail\.median_performance_stock_awards\s*\)\s*\{",
        src)
    if not m:
        check("S3 granular branch uses year-matched aggregate", False,
              "granular branch not found")
    else:
        tail = src[m.end():]
        else_idx = tail.find("} else {")
        branch = tail[:else_idx] if else_idx != -1 else tail
        bare = re.findall(r"\bsp\.(median_salary|median_perks|perks_yoy_change)\b", branch)
        check("S3 granular branch uses year-matched aggregate", not bare,
              ("bare sp references: %s" % bare) if bare else
              "salary/perks read via year-matched block")

    # S4: source-note FY label prefers the detail year
    note_lines = [l for l in src.splitlines()
                  if "composition-source" in l or
                  ("Source: " in l and "compDetailYear" in l)]
    s4 = any("compDetailYear" in l and "sp.fiscal_year" in l
             for l in src.splitlines() if "Source: " in l and "textContent" in l)
    check("S4 source-note FY label prefers detail year", s4,
          "sourceNote couples compDetailYear over sp.fiscal_year" if s4
          else "source-note line does not couple detail year")

    print("ALL 4 CHECKS PASSED" if not FAIL else "%d CHECK(S) FAILED" % len(FAIL))
    return 1 if FAIL else 0

if __name__ == "__main__":
    sys.exit(main())
