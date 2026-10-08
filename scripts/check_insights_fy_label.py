#!/usr/bin/env python3
"""Regression guard: the "Early Filers" insights card must derive its year
from metadata.primary_fiscal_year, not a hard-coded FY2025.

Background (2026-10-08): the early-filers insight (insights grid #25) was
hard-coded to fiscal_year === 2025 / 2026-proxy-season copy, which (a) would
go stale at the next anchor promotion and (b) excluded the 22 FY2026
non-calendar filers even today. The fix derives primaryFY from
compData.metadata.primary_fiscal_year, filters c.fiscal_year >= primaryFY,
matches YoY baselines per-company (c.fiscal_year - 1), and labels the card
'FY<primaryFY> Early Filers' with 'prior fiscal year' YoY copy.

This guard covers two live-year insights:
  S1-S6: the early-filers card (see above).
  S7: the Security Perks card derives its years from the year-keyed
      trends.json fields, so new study editions update the card with no
      code change.

Usage:
  scripts/check_insights_fy_label.py              # static checks
  scripts/check_insights_fy_label.py --static-only # same (pre-commit contract)

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    # Scope the block search to the early-filers IIFE.
    m = re.search(r"// 25\. Latest-proxy-season early filers.*?label: 'FY' \+ primaryFY \+ ' Early Filers'",
                  src, re.S)
    block = m.group(0) if m else ""

    # S1: primaryFY derived from metadata.
    s1 = ("var primaryFY = (typeof compData !== 'undefined' && compData && "
          "compData.metadata && compData.metadata.primary_fiscal_year) || 2025;") in src
    check("S1 primaryFY derives from compData.metadata.primary_fiscal_year",
          s1, "" if s1 else "derivation missing or changed")

    # S2: no hard-coded fiscal_year === 2025 anywhere in app.js.
    hard = re.findall(r"fiscal_year\s*===\s*2025", src)
    s2 = len(hard) == 0
    check("S2 no hard-coded 'fiscal_year === 2025' remains in js/app.js",
          s2, ("found %d" % len(hard)) if not s2 else "")

    # S3: no hard-coded 'FY2025 Early Filers' label.
    s3 = "'FY2025 Early Filers'" not in src
    check("S3 no hard-coded 'FY2025 Early Filers' label remains",
          s3, "" if s3 else "hard-coded label found")

    # S4: filter uses c.fiscal_year >= primaryFY.
    s4 = "c.fiscal_year >= primaryFY" in src
    check("S4 early-filers filter uses 'c.fiscal_year >= primaryFY'",
          s4, "" if s4 else "filter missing")

    # S5: per-company prior-year YoY baseline.
    s5 = ("e.year === prevYear" in src
          and "var prevYear = (c.fiscal_year || primaryFY) - 1;" in src)
    check("S5 YoY baseline uses per-company prior year (c.fiscal_year - 1)",
          s5, "" if s5 else "per-company baseline missing")

    # S6: stub-scale current-year rows excluded (SMCI 2025 $442 class would
    # otherwise render a -100% artifact "decline").
    s6 = "if ((rCur.total || 0) < 10000) return;" in src
    check("S6 stub-scale current-year rows (<$10K) excluded from YoY pairs",
          s6, "" if s6 else "stub filter missing")

    # S7: Security Perks insight derives its years from the year-keyed
    # trends.json fields (no hard-coded _2025/_2024 field access).
    s7 = ("s_and_p_500_ceos_with_security_2025" not in src
          and "s_and_p_500_ceos_with_security_2024" not in src
          and "/^s_and_p_500_ceos_with_security_(\\d{4})$/" in src)
    check("S7 Security Perks years derived from year-keyed fields, not hard-coded",
          s7, "" if s7 else "hard-coded security-perks year field remains")

    # S8: Historic Peak card derives its year from the year-keyed
    # historical_context fields; no hard-coded FY2025 label/field access.
    # Also asserts the card's click-through uses its own top ticker
    # (previously hard-coded to the FY2024 NYT top).
    s8 = ("'Historic Peak (FY2025)'" not in src
          and "highest_paid_ceo_fy2025_equilar_ap" not in src
          and "five_ceos_over_100m_fy2025" not in src
          and "/^highest_paid_ceo_fy(\\d{4})_/" in src
          and "_historicTopTicker" in src
          and "card._historicTopTicker" in src)
    check("S8 Historic Peak year derived from year-keyed fields; click-through uses card's own top ticker",
          s8, "" if s8 else "hard-coded historic-peak year remains")


def main():
    static_only = "--static-only" in sys.argv
    try:
        static_checks()
    except OSError as e:
        print("INFRA: " + str(e))
        sys.exit(2)
    fails = [n for n, ok, _ in results if not ok]
    print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
    if fails:
        print("FAILED: " + ", ".join(fails))
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
