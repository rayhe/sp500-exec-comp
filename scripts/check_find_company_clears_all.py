#!/usr/bin/env python3
"""Guard: findCompanyInTable clears every row-hiding filter before
forcing the search (376th review).

Background (376th review, 2026-11-07): findCompanyInTable is the
"show me this company" path for Top 10 chart clicks, insight-card
actions, and peer navigation (~20 call sites). Its contract comment
says "Clear filters to ensure company is visible", but it cleared
only 12 of the 25 row-hiding dimensions. Every dimension below ANDs
with the forced searchTerm = ticker in renderTable, so any of them
could hide the target row and the setTimeout auto-click below
silently found nothing: no panel, no announcement, stale chips still
claiming a live filter. Same failure class as the 375th review's hash
deep-link fix, in the other "show me this company" path. The fix
mirrors insightResetAndSort, the canonical clear-all path: null the
state, remove the chip, clear the chart highlight or call the
indicator that owns the chip. Board is the one dimension renderTable
does not apply (it filters only via the AF _refreshTable /
_sp500RenderTable paths), so it cannot hide the target row here --
but its chip and the AF badge would keep claiming a live filter
while the table shows unfiltered rows, the inverse of the 330th
review's stale-badge class, so it is nulled with the rest. The 338th
review's "intentionally kept" tenure/gov/vol/board carve-out is
reversed: state and selects are now cleared together, which is what
keeps the AF panel truthful.

Checks (all static - small JS reads, <2s):
 C1 HARD FAIL: findCompanyInTable does not null every row-hiding
    filter dimension (stock-pct, tenure, gov, volatility,
    volatility-tenure, peer-dist, community, quartile, position,
    crosstab, CEO-transition, PvP-only, board).
 C2 HARD FAIL: a nulled dimension is missing its chip removal,
    highlight clear, or indicator call -- state without its visual
    leaves a stale chip / ring / strip behind.
 C3 HARD FAIL: the _clearAfSelects call does not list all eight
    AF selects (af-pay-band, af-sop-tier, af-tenure, af-gov,
    af-gender, af-conc, af-vol, af-board) -- a kept select would
    keep showing an old value and the badge counting a filter that
    no longer filters.
 C4 HARD FAIL: the asp-delta highlight is not cleared -- the tier
    was nulled for years without its highlight clear (354th class).
 C5 HARD FAIL: the search + auto-click path is gone -- searchTerm =
    ticker and the setTimeout row click must still be present, so
    an unfiltered click still opens its panel.
 C6 HARD FAIL: node --check fails on js/app.js.

Usage:
  scripts/check_find_company_clears_all.py
  scripts/check_find_company_clears_all.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
import subprocess
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = f"{REPO}/js/app.js"

if "--static-only" in sys.argv:
    pass  # static half is the whole check; flag accepted for the hook runner


def extract_function_body(src, start_marker):
    """Return the brace-matched body starting at start_marker, or None."""
    idx = src.find(start_marker)
    if idx < 0:
        return None
    brace = src.find("{", idx)
    if brace < 0:
        return None
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[brace:i + 1]
    return None


# Each entry: (state token, companion tokens that must also appear in
# the function body -- chip removal, highlight clear, or indicator).
DIMENSIONS = [
    ("window._activeStockPctTier = null;",
     ["stockpct-filter-chip", "highlightStockPctBucket(null"]),
    ("window._activeTenureQuartile = null;",
     ["tenure-filter-chip", "highlightTenureBucket(null"]),
    ("window._activeGovGrade = null;",
     ["gov-filter-chip", "highlightGovChart(null)"]),
    ("window._activeVolatilityBucket = null;",
     ["updateVolatilityFilterIndicator()", "highlightVolatilityBucket(null)"]),
    ("window._activeVolTenureBracket = null;",
     ["updateVolTenureFilterIndicator()"]),
    ("window._activePeerDistFilter = null;",
     ["updatePeerDistFilterIndicator()"]),
    ("window._activeCommunityFilter = null;",
     ["clearCommunityHighlight()"]),
    ("window._activeQuartileFilter = null;",
     ["quartile-filter-chip"]),
    ("window._activePositionFilter = null;",
     ["position-filter-chip"]),
    ("window._activeCrosstabFilter = null;",
     ["crosstab-filter-chip"]),
    ("window._activeCeoTransitionFilter = false;",
     ["transition-filter-chip"]),
    ("window._activePvpOnlyFilter = false;",
     ["_updatePvpOnlyToggle()"]),
    ("window._activeBoardFilter = null;",
     ["board-filter-chip", "'af-board'"]),
]

AF_SELECTS = [
    "af-pay-band", "af-sop-tier", "af-tenure", "af-gov",
    "af-gender", "af-conc", "af-vol", "af-board",
]


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read js/app.js: {exc}")
        return 2

    failures = []

    body = extract_function_body(app, "window.findCompanyInTable = function(ticker)")
    if body is None:
        failures.append("C1 findCompanyInTable not found in js/app.js")
        print("FAIL: " + "\nFAIL: ".join(failures))
        return 1

    # --- C1/C2: every dimension nulled with its visual -----------------
    for state, companions in DIMENSIONS:
        if state not in body:
            failures.append("C1 findCompanyInTable does not clear "
                            + state.split(" = ")[0]
                            + " -- an uncleared dimension either ANDs "
                            "with the forced search and hides the target "
                            "row (the auto-click finds nothing, no panel "
                            "opens) or, for board, leaves its chip and "
                            "the AF badge claiming a live filter while "
                            "the table shows unfiltered rows")
        for comp in companions:
            if comp not in body:
                failures.append("C2 the " + state.split(" = ")[0]
                                + " clear is missing its companion "
                                + comp + " -- state without its visual "
                                "leaves a stale chip, ring, or strip "
                                "claiming a filter that no longer filters")

    # --- C3: all eight AF selects cleared with the state ---------------
    af_anchor = body.find("_clearAfSelects(")
    if af_anchor < 0:
        failures.append("C3 findCompanyInTable never calls "
                        "_clearAfSelects -- the AF panel would keep "
                        "showing old values for filters that no longer "
                        "filter")
    else:
        call = body[af_anchor:af_anchor + 300]
        missing = [s for s in AF_SELECTS if "'" + s + "'" not in call]
        if missing:
            failures.append("C3 the _clearAfSelects call is missing "
                            "selects: " + ", ".join(missing)
                            + " -- a kept select keeps showing an old "
                            "value and the badge counting a filter that "
                            "no longer filters")

    # --- C4: asp-delta highlight ---------------------------------------
    if "highlightAspDeltaBucket(null" not in body:
        failures.append("C4 findCompanyInTable nulls the asp-delta tier "
                        "but never clears its histogram highlight -- "
                        "the bars would stay ringed behind the "
                        "unfiltered table (354th class)")

    # --- C5: the search + auto-click path survives ---------------------
    if "searchTerm = ticker;" not in body:
        failures.append("C5 searchTerm = ticker is missing from "
                        "findCompanyInTable -- the click-to-show path "
                        "is gone")
    if "setTimeout(function()" not in body:
        failures.append("C5 the setTimeout auto-click is missing from "
                        "findCompanyInTable -- the row would be found "
                        "but its detail panel never opened")

    # --- C6: syntax -----------------------------------------------------
    try:
        chk = subprocess.run(["node", "--check", APP_JS],
                             capture_output=True, text=True, timeout=30)
        if chk.returncode != 0:
            failures.append("C6 node --check fails on js/app.js: "
                            + (chk.stderr or chk.stdout).strip()[:200])
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"INFRA: node --check unavailable: {exc}")
        return 2

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: find-company-clears-all: findCompanyInTable nulls all "
          "13 row-hiding dimensions with their chips / highlights / "
          "indicators, clears all eight AF selects, clears the "
          "asp-delta highlight, and keeps the search + auto-click path "
          "that opens the target panel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
