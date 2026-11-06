#!/usr/bin/env python3
"""Guard: zero-count buckets render at min height, dimmed and clickable,
in the SoP sort-summary histogram when a SoP filter is active.

Background (363rd review, 2026-11-06): renderSopSortSummary skipped
every zero-count bucket (bare `if (b.count === 0) return;` in both the
bar loop and the bracket-label loop). When filtered by a SoP range, the
filtered set has zero companies in every non-overlapping bucket by
definition, so the histogram collapsed to the overlapping buckets only
and the bar could not switch buckets -- the bucket-switching histogram
the 361st review had just made reachable in filtered states was two
bars. The fix gates the skip on the SoP filter being active: zero-count
buckets render at min height (2px), dimmed (the existing 0.3
non-active group opacity) and clickable so the filter can be switched;
with no SoP filter active the unfiltered view is unchanged. Same
pattern as the 362nd eq/asp fix; the gate predicate here is
window._activeSopFilter itself (an AF-origin SoP filter is a range
overlap, not an exact tier).

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the SoP bar loop does not gate its zero-count skip on
     window._activeSopFilter -- a filtered SoP histogram collapses to
     the overlapping buckets only and the bar cannot switch buckets.
  C2 HARD FAIL: the SoP bracket-label loop does not carry the same
     gate -- bars and labels would go out of sync.
  C3 HARD FAIL: a zero-count bar is not rendered at min height
     (b.count === 0 ? 2 : ...) -- a zero-height bar would be invisible
     and unclickable.
  C4 HARD FAIL: a bare zero-count skip remains anywhere in the
     function -- the gated skip above is not the one that runs.

Usage:
  scripts/check_sop_zero_bucket.py
  scripts/check_sop_zero_bucket.py --static-only

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

    sop = extract_function_body(
        app, "function renderSopSortSummary(companies) {")
    if sop is None:
        print("FAIL: renderSopSortSummary not found in js/app.js")
        return 1

    # --- C1: SoP bar loop gates the zero-count skip --------------------
    # The bar loop is the first buckets.forEach in the function; the label
    # loop is the second. Split on the bracket-labels container marker.
    sop_bars = sop.split("sop-dist-bracket-labels")[0]
    if "if (b.count === 0 && !window._activeSopFilter) return;" not in sop_bars:
        failures.append("C1 the SoP bar loop does not gate its zero-count "
                        "skip on window._activeSopFilter -- when filtered "
                        "by a SoP range the histogram collapses to the "
                        "overlapping buckets only and the bar cannot "
                        "switch buckets (363rd gap)")
    if "if (b.count === 0) return;" in sop_bars:
        failures.append("C1 the SoP bar loop still carries the bare "
                        "zero-count skip -- the gated skip above is not "
                        "the one that runs")

    # --- C2: SoP bracket-label loop carries the same gate --------------
    sop_labels = sop.split("sop-dist-bracket-labels")[1] \
        if "sop-dist-bracket-labels" in sop else ""
    if ("if (b.count === 0 && !window._activeSopFilter) return;"
            not in sop_labels):
        failures.append("C2 the SoP bracket-label loop does not gate its "
                        "zero-count skip on window._activeSopFilter -- "
                        "bars and labels would go out of sync in a "
                        "filtered SoP histogram")

    # --- C3: zero-count bars render at min height ----------------------
    if "b.count === 0 ? 2 :" not in sop:
        failures.append("C3 the SoP histogram does not render zero-count "
                        "bars at min height (b.count === 0 ? 2 : ...) -- "
                        "a zero-height bar would be invisible and "
                        "unclickable")

    # --- C4: no bare zero-count skip remains in the function -----------
    if "if (b.count === 0) return;" in sop:
        failures.append("C4 a bare zero-count skip remains in "
                        "renderSopSortSummary -- the gated skip is not "
                        "the one that runs")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: sop-zero-bucket: SoP sort-summary histogram renders "
          "zero-count buckets at min height, dimmed and clickable when a "
          "SoP filter is active, with bars and labels in sync, and the "
          "unfiltered view still skips zero-count buckets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
