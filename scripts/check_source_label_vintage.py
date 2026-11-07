#!/usr/bin/env python3
"""Guard: company `source` (CEO-anchor provenance) labels stay vintage- and
form-consistent with the anchor filing.

Background (368th review, 2026-11-06): 13 companies carried stale `source`
labels after their CEO anchors were promoted. 10 of them (BR, CAG, CAH,
CTAS, DRI, FDX, GIS, PH, TPR, PG) still said FY2025 while the anchor
total, filing_date, filing_url and proxy_fiscal_year all pointed at the
FY2026 proxy; 3 (EA, TECH, K) said DEF 14A while their anchors came from
10-K/As. The label is not decorative: three UI spots derive the
filing-form link label from it (table row link, NEO panel link, Board
Independence source link - js/app.js ~7894, ~10043, ~11013, via a /10-K/
test on `source`), so EA/TECH/K showed "SEC Filing / View DEF 14A proxy
statement" and "DEF 14A" links for 10-K/A filings. The fix set the labels
to the anchor filing's true form + year + FY; this guard keeps the
invariant so the next anchor promotion cannot repeat the drift.

Checks (all static - small JSON read, <2s):
  C1 HARD FAIL: a parseable FY year in `source` disagrees with the
     company's proxy_fiscal_year (the anchor filing's fiscal year).
  C2 HARD FAIL: a parseable proxy year/date in `source` disagrees with
     the filing_date year (the anchor filing's filing year). Yearless
     forms ("SEC EDGAR DEF 14A - FY2025 CEO") skip this check.
  C3 HARD FAIL: data_source is SEC EDGAR 10-K/A but `source` does not
     name 10-K/A (form disagreement - the EA/TECH/K class).
  C4 HARD FAIL: data_source is a DEF 14A-family source but `source`
     names a 10-K form (the reverse form disagreement).

Skips: empty `source` (VMRK stub - no anchor filing yet) and companies
with no proxy_fiscal_year. TSLA is intentionally NOT covered by a
URL-vs-source check: its rows are 10-K/A-sourced (2026-04-30) while its
filing_url points at the 2026-10-19 DEF 14A, which also carries the
FY2025 SCT; deciding between repointing the URL and relabeling the
source needs SCT verification against the Oct-19 DEF 14A (queued in the
368th review notes), so no URL-form assertion is made here.

Usage:
  scripts/check_source_label_vintage.py
  scripts/check_source_label_vintage.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JSON unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import json
import os
import re
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
JSON_PATH = os.path.join(REPO, "data", "compensation.json")

if "--static-only" in sys.argv:
    pass  # static half is the whole check; flag accepted for the hook runner

FY_RE = re.compile(r"FY(\d{4})\b")
# A proxy year/date must sit BEFORE the FY token (the form part of the
# label). Yearless forms ("SEC EDGAR DEF 14A - FY2025 CEO") carry no
# proxy year, so the first year in the whole string would be the FY year
# itself - searching the pre-FY prefix avoids that false positive.
YEAR_RE = re.compile(r"(\d{4})-\d{2}-\d{2}|(\d{4})")


def check(data):
    failures = []
    for c in data["companies"]:
        ticker = c.get("ticker", "?")
        src = c.get("source") or ""
        if not src:
            continue  # VMRK stub: no anchor filing yet
        pfy = c.get("proxy_fiscal_year")
        filing_date = c.get("filing_date") or ""
        ds = c.get("data_source") or ""

        # C1: FY year in the label must equal the anchor filing's fiscal year.
        m = FY_RE.search(src)
        if m and pfy is not None and int(m.group(1)) != pfy:
            failures.append(
                f"C1 {ticker}: source FY{m.group(1)} != proxy_fiscal_year "
                f"{pfy} ({src!r})")
        # C2: proxy year/date in the label must equal the filing year.
        # Only the pre-FY prefix counts (see YEAR_RE note above).
        prefix = src.split("FY", 1)[0]
        ym = YEAR_RE.search(prefix)
        if ym and filing_date:
            label_year = int(ym.group(1) or ym.group(2))
            if label_year != int(filing_date[:4]):
                failures.append(
                    f"C2 {ticker}: source year {label_year} != filing year "
                    f"{filing_date[:4]} ({src!r}, filed {filing_date})")
        # C3: 10-K/A data_source requires a 10-K/A label.
        if ds == "SEC EDGAR 10-K/A" and "10-K/A" not in src:
            failures.append(
                f"C3 {ticker}: data_source is 10-K/A but source names no "
                f"10-K/A ({src!r})")
        # C4: DEF 14A-family data_source must not be labeled a 10-K form.
        if ds.startswith("SEC EDGAR DEF 14A") and "10-K" in src:
            failures.append(
                f"C4 {ticker}: data_source is DEF 14A but source names a "
                f"10-K form ({src!r})")
    return failures


def main():
    try:
        with open(JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print(f"INFRA: cannot read {JSON_PATH}: {e}")
        return 2
    failures = check(data)
    if failures:
        print(f"FAIL: {len(failures)} source-label drift(s):")
        for fl in failures:
            print("  " + fl)
        return 1
    print("OK: all company source labels match anchor filing vintage + form")
    return 0


if __name__ == "__main__":
    sys.exit(main())
