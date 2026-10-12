#!/usr/bin/env python3
"""Regression guard: dataq pay-ratio "Fiscal-year roll" bullet names a
self-consistent proxy season.

The data-quality modal's pay-ratio methodology block explains why disclosed
ratios deviate from total_compensation / median_worker_pay. Its
"Fiscal-year roll" bullet says the anchor reflects FY<anchor> SCT totals
while the disclosed ratio and median worker pay "remain the FY{Y} figures
from the {P} proxy season".

2026-10-11 19:30 PT run: the bullet read "the FY2024 figures from the 2026
proxy season" - self-contradictory. A 2026 proxy discloses FY2025 figures;
the stored pay_ratio / median_worker_pay fields are FY2024 figures from the
2025 proxy season (spot-verified: CMG 1148:1 / $16,666 = ~$19.1M matches
CMG's 2025 DEF 14A year-end-CEO figure cited in the same modal; MO 169:1
is the 2025 DEF 14A figure, not the 2026 DEF 14A's 147:1; TSLA is the
documented FY2025 exception). The bullet now reads "from the 2025 proxy
season".

Checks (static, fast, runs in the pre-commit hook):
  S1 the Fiscal-year-roll bullet exists in js/app.js.
  S2 the bullet's vintage claim is self-consistent: it names a ratio/median
     fiscal year Y ("remain the FY{Y} figures") and a proxy season P
     ("from the {P} proxy season"), and P == Y + 1, because FY{Y} figures
     are disclosed in proxies filed in calendar Y+1 (the Y+1 proxy season).
     This holds across future anchor rolls: if the ratios are ever
     re-extracted to FY2025, the copy must read "FY2025 figures from the
     2026 proxy season" and P == Y+1 still holds.
  S3 the exact stale string "FY2024 figures from the 2026 proxy season"
     is absent from js/app.js (regression trip for this bug).

Usage:
  scripts/check_payratio_proxyseason_copy.py
  scripts/check_payratio_proxyseason_copy.py --static-only

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


def main():
    static_only = "--static-only" in sys.argv
    try:
        with open(APP_JS, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print("INFRA: cannot read js/app.js: %s" % e)
        return 2

    # S1: the Fiscal-year-roll bullet exists.
    m = re.search(r"Fiscal-year roll</strong>:(.*?)</li>", src, re.DOTALL)
    check("S1 fiscal-year-roll bullet present", m is not None)
    if not m:
        print("RESULT: %d/%d static checks passed" % (sum(1 for _, ok, _ in results if ok), len(results)))
        return 1

    bullet = m.group(1)

    # S2: vintage claim self-consistency - P == Y + 1.
    ym = re.search(r"remain the FY(\d{4}) figures", bullet)
    pm = re.search(r"from the (\d{4}) proxy season", bullet)
    if ym and pm:
        y, p = int(ym.group(1)), int(pm.group(1))
        check("S2 proxy season == ratio FY + 1", p == y + 1,
              "FY%d figures from the %d proxy season" % (y, p))
    else:
        check("S2 proxy season == ratio FY + 1", False,
              "could not parse FY/proxy-season years from bullet")

    # S3: the exact stale string is gone.
    check("S3 stale 'FY2024 figures from the 2026 proxy season' absent",
          "FY2024 figures from the 2026 proxy season" not in src)

    if not static_only:
        print("NOTE: render half not implemented for this copy guard (static-only contract).")

    passed = sum(1 for _, ok, _ in results if ok)
    print("RESULT: %d/%d static checks passed" % (passed, len(results)))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
