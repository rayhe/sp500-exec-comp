#!/usr/bin/env python3
"""Guard: a filter+detail deep link degrades to the filtered table,
never to zero rows (375th review).

Background (375th review, 2026-11-07): closes the 374th run's
candidate (2). The detail-open path in applyHashState forces
searchTerm = detailTicker when the target row is not on the visible
page, so a deep link can re-open a panel for a company on another
page. But the five ticker-list filters (peer-dist, community,
quartile, position, crosstab) AND with the search: when the filter
excludes the target ticker, the forced search yields zero rows, no
panel opens, and the hash keeps detail= for a panel that does not
exist -- a reload repeats the empty table. The fix checks the five
filters before forcing the search; when any of them excludes the
target, it skips the search entirely, nulls the expanded-detail
ticker (and the diff key), pushes the hash so detail= (and diff=)
drops immediately, and announces why no panel opened. The filtered
table -- plus its chip and, for peer-dist, the strip -- stays
visible. A ticker-list filter that INCLUDES the target, or no
ticker-list filter at all, still takes the search path.

Checks (all static - small JS reads, <2s):
 C1 HARD FAIL: the detail-open path does not check all five
    ticker-list filters for exclusion of the target ticker before
    forcing the search.
 C2 HARD FAIL: the exclusion branch does not null the expanded
    detail ticker and the diff key, or does not pushState so the
    URL drops detail= -- the same pair-null invariant as the 371st
    Reset All, 372nd Escape-close, and 374th filter-click fixes.
 C3 HARD FAIL: the exclusion branch does not announce why no panel
    opened (a silent no-op leaves a screen-reader user with no
    explanation for the missing panel).
 C4 HARD FAIL: the search path is gone -- searchTerm = detailTicker
    must still be present in the detail-open block, after the
    exclusion guard, so an in-filter or unfiltered deep link still
    opens its panel.
 C5 HARD FAIL: node --check fails on js/app.js.

Usage:
  scripts/check_detail_open_filtered.py
  scripts/check_detail_open_filtered.py --static-only

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


TICKER_LIST_FILTERS = [
    "window._activePeerDistFilter",
    "window._activeCommunityFilter",
    "window._activeQuartileFilter",
    "window._activePositionFilter",
    "window._activeCrosstabFilter",
]


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read js/app.js: {exc}")
        return 2

    failures = []

    ahs = extract_function_body(app, "function applyHashState(companies)")
    if ahs is None:
        failures.append("C1 applyHashState not found in js/app.js")
        print("FAIL: " + "\nFAIL: ".join(failures))
        return 1

    # The detail-open block: from the detail= comment to the end of the
    # function body. Use rfind-safe anchors: the guard's own comment
    # prose must not confuse the search, so match on code literals.
    open_anchor = ahs.find("// Deep-link: open detail panel for specified ticker")
    if open_anchor < 0:
        failures.append("C1 detail-open block not found in applyHashState")
        print("FAIL: " + "\nFAIL: ".join(failures))
        return 1
    detail_block = ahs[open_anchor:]

    # --- C1: all five ticker-list filters checked for exclusion -------
    missing = [f for f in TICKER_LIST_FILTERS if f not in detail_block]
    if missing:
        failures.append("C1 the detail-open exclusion check does not "
                        "reference every ticker-list filter -- missing: "
                        + ", ".join(missing))
    if "indexOf(detailTicker) < 0" not in detail_block:
        failures.append("C1 the detail-open path has no exclusion test "
                        "against the target ticker -- a filter that "
                        "excludes it would still take the search path "
                        "and yield zero rows")
    search_pos = detail_block.find("searchTerm = detailTicker;")
    guard_pos = detail_block.find("indexOf(detailTicker) < 0")
    if search_pos < 0:
        failures.append("C4 searchTerm = detailTicker is missing from the "
                        "detail-open block -- the in-filter / unfiltered "
                        "deep-link path is gone")
    elif guard_pos >= 0 and guard_pos > search_pos:
        failures.append("C1 the exclusion check sits AFTER the forced "
                        "search -- the search must be skipped before it "
                        "empties the table, not guarded after the fact")

    # --- C2: the exclusion branch nulls the pair and pushes -----------
    excl_anchor = detail_block.find("_excludedByTickerFilter")
    if excl_anchor < 0:
        failures.append("C2 the exclusion branch is not present in the "
                        "detail-open block")
    else:
        branch = detail_block[excl_anchor:excl_anchor + 800]
        if "_expandedDetailTicker = null;" not in branch:
            failures.append("C2 the exclusion branch does not null the "
                            "expanded detail ticker -- the hash would keep "
                            "detail= for a panel that was never opened")
        if "_activeDiffKey = null;" not in branch:
            failures.append("C2 the exclusion branch does not null the "
                            "diff key -- a stale diff= would ride along "
                            "with the dropped detail=")
        if "pushState();" not in branch:
            failures.append("C2 the exclusion branch does not pushState -- "
                            "the URL would keep detail= until the next "
                            "table render, and a reload would repeat the "
                            "empty table")
        # --- C3: the branch announces the no-op -----------------------
        if "announce('Detail panel not opened" not in branch:
            failures.append("C3 the exclusion branch does not announce "
                            "why no panel opened -- a screen-reader user "
                            "gets no explanation for the missing panel")

    # --- C5: syntax -----------------------------------------------------
    try:
        chk = subprocess.run(["node", "--check", APP_JS],
                             capture_output=True, text=True, timeout=30)
        if chk.returncode != 0:
            failures.append("C5 node --check fails on js/app.js: "
                            + (chk.stderr or chk.stdout).strip()[:200])
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"INFRA: node --check unavailable: {exc}")
        return 2

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: detail-open-filtered: the detail-open path checks all "
          "five ticker-list filters for exclusion of the target before "
          "forcing the search; an excluded target skips the search, "
          "nulls the expanded ticker and diff key, pushes the hash so "
          "detail= drops, and announces why no panel opened; the search "
          "path is preserved for in-filter and unfiltered deep links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
