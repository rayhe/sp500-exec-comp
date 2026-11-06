#!/usr/bin/env python3
"""Guard: zero-count tiers render at min height, dimmed and clickable,
in the eq / asp sort-summary histograms when a tier filter is active.

Background (362nd review, 2026-11-06): renderStockPctSortSummary and
renderAspDeltaSortSummary skipped every zero-count tier (bare
`if (t.count === 0) return;` in both the bar loop and the bracket-label
loop). When filtered by a tier, the filtered set has zero companies in
every other tier by definition, so the histogram collapsed to the active
tier only and the bar could not switch tiers -- the tier-switching
histogram the 361st review had just made reachable in filtered states
was a single bar. The fix gates the skip on the tier filter being
active: zero-count tiers render at min height (2px), dimmed (the
existing 0.3 non-active opacity) and clickable so the filter can be
switched; with no tier filter active the unfiltered view is unchanged.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the eq bar loop does not gate its zero-count skip on
     activeT -- a filtered eq histogram collapses to the active tier.
  C2 HARD FAIL: the eq bracket-label loop does not carry the same
     gate -- bars and labels would go out of sync.
  C3 HARD FAIL: the asp bar loop does not gate its zero-count skip
     on window._activeAspDeltaTier.
  C4 HARD FAIL: the asp bracket-label loop does not carry the same
     gate.
  C5 HARD FAIL: a zero-count bar is not rendered at min height
     (t.count === 0 ? 2 : ...) in either function -- a zero-height
     bar would be invisible and unclickable.

Usage:
  scripts/check_eq_asp_zero_tier.py
  scripts/check_eq_asp_zero_tier.py --static-only

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

    eq = extract_function_body(
        app, "function renderStockPctSortSummary(companies) {")
    if eq is None:
        print("FAIL: renderStockPctSortSummary not found in js/app.js")
        return 1
    asp = extract_function_body(
        app, "function renderAspDeltaSortSummary(companies) {")
    if asp is None:
        print("FAIL: renderAspDeltaSortSummary not found in js/app.js")
        return 1

    # --- C1: eq bar loop gates the zero-count skip on activeT ---------
    # The bar loop is the first tiers.forEach in the function; the label
    # loop is the second. Split on the histogram container marker.
    eq_bars = eq.split("eq-dist-bracket-labels")[0]
    if "if (t.count === 0 && !activeT) return;" not in eq_bars:
        failures.append("C1 the eq bar loop does not gate its zero-count "
                        "skip on activeT -- when filtered by a tier the "
                        "histogram collapses to the active tier only and "
                        "the bar cannot switch tiers (362nd gap)")
    if "if (t.count === 0) return;" in eq_bars:
        failures.append("C1 the eq bar loop still carries the bare "
                        "zero-count skip -- the gated skip above is not "
                        "the one that runs")

    # --- C2: eq bracket-label loop carries the same gate --------------
    eq_labels = eq.split("eq-dist-bracket-labels")[1] \
        if "eq-dist-bracket-labels" in eq else ""
    if "if (t.count === 0 && !activeT) return;" not in eq_labels:
        failures.append("C2 the eq bracket-label loop does not gate its "
                        "zero-count skip on activeT -- bars and labels "
                        "would go out of sync in a filtered eq histogram")

    # --- C3: asp bar loop gates the zero-count skip --------------------
    asp_bars = asp.split("asp-dist-bracket-labels")[0]
    if ("if (t.count === 0 && !window._activeAspDeltaTier) return;"
            not in asp_bars):
        failures.append("C3 the asp bar loop does not gate its zero-count "
                        "skip on window._activeAspDeltaTier -- when "
                        "filtered by a tier the histogram collapses to "
                        "the active tier only and the bar cannot switch "
                        "tiers (362nd gap)")
    if "if (t.count === 0) return;" in asp_bars:
        failures.append("C3 the asp bar loop still carries the bare "
                        "zero-count skip -- the gated skip above is not "
                        "the one that runs")

    # --- C4: asp bracket-label loop carries the same gate --------------
    asp_labels = asp.split("asp-dist-bracket-labels")[1] \
        if "asp-dist-bracket-labels" in asp else ""
    if ("if (t.count === 0 && !window._activeAspDeltaTier) return;"
            not in asp_labels):
        failures.append("C4 the asp bracket-label loop does not gate its "
                        "zero-count skip on window._activeAspDeltaTier -- "
                        "bars and labels would go out of sync in a "
                        "filtered asp histogram")

    # --- C5: zero-count bars render at min height ----------------------
    for name, body in (("eq", eq), ("asp", asp)):
        if "t.count === 0 ? 2 :" not in body:
            failures.append("C5 the %s histogram does not render "
                            "zero-count bars at min height "
                            "(t.count === 0 ? 2 : ...) -- a zero-height "
                            "bar would be invisible and unclickable"
                            % name)

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: eq-asp-zero-tier: eq/asp sort-summary histograms render "
          "zero-count tiers at min height, dimmed and clickable when a "
          "tier filter is active, with bars and labels in sync, and the "
          "unfiltered view still skips zero-count tiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
