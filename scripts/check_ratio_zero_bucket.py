#!/usr/bin/env python3
"""Guard: zero-count buckets render at min height, dimmed and clickable,
in the pay-ratio sort-summary histogram when a ratio-bucket filter is
active.

Background (364th review, 2026-11-06): renderRatioSortSummary skipped
every zero-count bucket (bare `if (b.count === 0) return;` in the bar
loop). When filtered by a ratio bucket, the filtered set has zero
companies in every non-overlapping bucket by definition, so the
histogram collapsed to the active bucket only and the bar could not
switch buckets -- the bucket-switching histogram the 361st review had
just made reachable in filtered states was one bar. The fix gates the
skip on the ratio filter being active: zero-count buckets render at
min height (4px, this histogram's minimum), dimmed (the existing 0.3
non-active opacity) and clickable so the filter can be switched; with
no ratio filter active the unfiltered view is unchanged. Same pattern
as the 362nd eq/asp and 363rd SoP fixes; the gate predicate here is
the ratio filter itself (activeRB is an exact bucket match). Closes
queued candidate (2) from the 363rd list.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the ratio bar loop does not gate its zero-count skip on
     activeRB -- a filtered ratio histogram collapses to the active
     bucket only and the bar cannot switch buckets.
  C2 HARD FAIL: a zero-count bar is not rendered at min height
     (b.count === 0 ? 4 : ...) -- a zero-height bar would be invisible
     and unclickable.
  C3 HARD FAIL: a bare zero-count skip remains anywhere in the
     function -- the gated skip above is not the one that runs.
  C4 HARD FAIL: non-active bars are not dimmed when a filter is active
     -- a zero-count bar would render at full opacity and read as a
     populated bucket.

Usage:
  scripts/check_ratio_zero_bucket.py
  scripts/check_ratio_zero_bucket.py --static-only

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

    ratio = extract_function_body(
        app, "function renderRatioSortSummary(companies) {")
    if ratio is None:
        print("FAIL: renderRatioSortSummary not found in js/app.js")
        return 1

    # --- C1: ratio bar loop gates the zero-count skip -----------------
    # The bar loop is the buckets.forEach after the ratio-dist-bars
    # container marker; the earlier buckets.forEach only counts.
    ratio_bars = ratio.split("ratio-dist-bars")[1] \
        if "ratio-dist-bars" in ratio else ""
    if "if (b.count === 0 && !activeRB) return;" not in ratio_bars:
        failures.append("C1 the ratio bar loop does not gate its "
                        "zero-count skip on activeRB -- when filtered "
                        "by a ratio bucket the histogram collapses to "
                        "the active bucket only and the bar cannot "
                        "switch buckets (364th gap)")
    if "if (b.count === 0) return;" in ratio_bars:
        failures.append("C1 the ratio bar loop still carries the bare "
                        "zero-count skip -- the gated skip above is not "
                        "the one that runs")

    # --- C2: zero-count bars render at min height ---------------------
    if "b.count === 0 ? 4 :" not in ratio:
        failures.append("C2 the ratio histogram does not render "
                        "zero-count bars at min height "
                        "(b.count === 0 ? 4 : ...) -- a zero-height bar "
                        "would be invisible and unclickable")

    # --- C3: no bare zero-count skip remains in the function ----------
    if "if (b.count === 0) return;" in ratio:
        failures.append("C3 a bare zero-count skip remains in "
                        "renderRatioSortSummary -- the gated skip is not "
                        "the one that runs")

    # --- C4: non-active bars dim when a filter is active --------------
    if "isDimmed = (activeRB && !isActive)" not in ratio:
        failures.append("C4 the ratio histogram does not dim non-active "
                        "bars when a ratio filter is active -- a "
                        "zero-count bar would render at full opacity and "
                        "read as a populated bucket")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: ratio-zero-bucket: pay-ratio sort-summary histogram "
          "renders zero-count buckets at min height, dimmed and "
          "clickable when a ratio-bucket filter is active, and the "
          "unfiltered view still skips zero-count buckets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
