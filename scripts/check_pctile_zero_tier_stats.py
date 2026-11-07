#!/usr/bin/env python3
"""Guard: zero-count tiers stay visible (dimmed, bare "0") in the
percentile sort-summary tier stats when a pctile tier filter is active.

Background (367th review, 2026-11-06): renderPercentileSortSummary
skipped every zero-count tier in its tier-stats loop (bare
`if (t.count === 0) return;`). When filtered by a pctile tier, the
filtered set has zero companies in every other tier by definition, so
the stats collapsed to the active tier only while the histogram above
kept all four tiers visible at 0 -- the two sections of the same
summary disagreed about which tiers exist. The fix gates the skip on
the tier filter being active: zero-count tiers render dimmed (0.3
opacity, matching the histogram's non-active dim) with a bare "0" and
no comp range (the tier has no companies, so Math.min/max over an
empty list would be Infinity); with no tier filter active the
unfiltered view is unchanged.

Checks (all static - small JS read, <2s):
  C1 HARD FAIL: the pctile tier-stats loop does not gate its
     zero-count skip on activeTier -- a filtered pctile summary
     collapses its stats to the active tier only.
  C2 HARD FAIL: the bare zero-count skip still runs anywhere in
     renderPercentileSortSummary -- the gated skip above is not the
     one that runs.
  C3 HARD FAIL: a zero-count tier is not rendered with a bare "0"
     (no comp range) -- Math.min/max over the empty comps list
     would render Infinity.
  C4 HARD FAIL: a zero-count tier is not dimmed -- the stats would
     read as live data for tiers that hold no companies in the
     filtered set.

Usage:
  scripts/check_pctile_zero_tier_stats.py
  scripts/check_pctile_zero_tier_stats.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
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


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    pct = extract_function_body(
        app, "function renderPercentileSortSummary(companies) {")
    if pct is None:
        print("FAIL: renderPercentileSortSummary not found in js/app.js")
        return 1

    # The tier-stats loop is the last tiers.forEach in the function,
    # after the "Tier-specific stats" comment.
    stats = pct.split("Tier-specific stats")[1] \
        if "Tier-specific stats" in pct else ""
    if not stats:
        print("FAIL: Tier-specific stats section not found in "
              "renderPercentileSortSummary")
        return 1

    # --- C1: stats loop gates the zero-count skip on activeTier -------
    if "if (t.count === 0 && !activeTier) return;" not in stats:
        failures.append("C1 the pctile tier-stats loop does not gate its "
                        "zero-count skip on activeTier -- when filtered "
                        "by a tier the stats collapse to the active tier "
                        "only while the histogram keeps all four tiers "
                        "visible (367th gap)")
    if "if (t.count === 0) return;" in stats:
        failures.append("C1 the pctile tier-stats loop still carries the "
                        "bare zero-count skip -- the gated skip above is "
                        "not the one that runs")

    # --- C2: no bare skip anywhere else in the function ---------------
    if "if (t.count === 0) return;" in pct:
        failures.append("C2 renderPercentileSortSummary still carries a "
                        "bare zero-count skip -- a filtered pctile view "
                        "loses tiers somewhere in the summary")

    # --- C3: zero-count tier renders a bare "0" (no comp range) -------
    if "t.count === 0 ? '' :" not in stats:
        failures.append("C3 the pctile tier-stats loop does not render a "
                        "bare '0' for zero-count tiers -- Math.min/max "
                        "over the empty comps list would render Infinity")

    # --- C4: zero-count tiers are dimmed -------------------------------
    if "opacity:0.3" not in stats:
        failures.append("C4 the pctile tier-stats loop does not dim "
                        "zero-count tiers -- empty tiers would read as "
                        "live data in a filtered summary")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: pctile-zero-tier-stats: percentile sort-summary tier "
          "stats keep zero-count tiers visible (dimmed, bare 0) when a "
          "tier filter is active, and the unfiltered view still skips "
          "zero-count tiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
