#!/usr/bin/env python3
"""Guard: sort-contextual summary renders alongside the filter stats
when the active filter's dim matches the sort key.

Background (361st review, 2026-11-06): renderSummaryBar only rendered
the sort-contextual summary (mini-histograms with the active-bucket ring
and click-to-clear bars) when unfiltered, so a filtered deep link or
back/forward navigation into a stock-% or asp-delta tier left the
hash-restore highlight calls as no-ops (no bar groups in the DOM: the
359th review flagged those two calls, and the 360th review carried the
gate as the next fix). The fix renders the sort-contextual summary
alongside the filter stats when the active filter's dim matches the
sort key, computed from the filtered set so its stats stay truthful to
the filtered view. Sector is excluded deliberately (a sector-filtered
set has one sector, so the sector distribution degenerates to a single
bar, and the sector-vs-benchmark block already covers it).
The compact YoY / Stock % / Conc stat blocks are suppressed in exactly
the dim-match case, so no number is shown twice.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: renderSummaryBar's filtered branch does not compute
     the sortCtxMatchesFilter predicate with the dim mappings
     (dist / YoY / ratio / stock-% / pctile / conc / SoP / asp-delta).
  C2 HARD FAIL: the filtered branch does not append the
     sort-contextual summary (renderSortContextSummary(filtered))
     gated on sortCtxMatchesFilter.
  C3 HARD FAIL: a compact YoY / Stock % / Conc stat block is not
     suppressed when the full summary renders for the same dim --
     the median would be shown twice in the same bar.
  C4 HARD FAIL: a restore-site comment still claims the stock-% /
     asp-delta highlight calls are no-ops on a filtered deep link --
     the gate has landed, so the stale claim misleads the next reader.

Usage:
  scripts/check_sortctx_filtered_summary.py
  scripts/check_sortctx_filtered_summary.py --static-only

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


# Dim mappings the predicate must carry: (sort key, active-filter state).
DIM_MAPPINGS = [
    ("total_compensation", "_activeDistFilter"),
    ("_ceoYoYSort", "_activeYoYBucket"),
    ("pay_ratio", "_activeRatioBucket"),
    ("_ceoStockPctSort", "_activeStockPctTier"),
    ("_compPercentile", "_activePctileTier"),
    ("_ceoConcPct", "_activeConcTier"),
    ("_sopApproval", "_activeSopFilter"),
    ("_aspDelta", "_activeAspDeltaTier"),
]

# Compact stat blocks suppressed when the full summary renders.
COMPACT_BLOCKS = [
    ("_ceoYoYSort", "YoY"),
    ("_ceoStockPctSort", "Stock %"),
    ("_ceoConcPct", "Conc"),
]

# Stale sentences from the two restore-site comments (pre-gate claims
# that the stock-% / asp-delta highlight calls are no-ops when filtered).
STALE_SENTENCES = [
    "are no-ops on a filtered deep link today",
    "are no-ops when the new hash carries a",
]


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    bar = extract_function_body(
        app, "function renderSummaryBar(filtered, allCompanies) {")
    if bar is None:
        print("FAIL: C1 renderSummaryBar not found in js/app.js")
        return 1

    # --- C1: dim-match predicate present in the filtered branch -------
    pred_anchor = bar.find("var sortCtxMatchesFilter = false;")
    if pred_anchor < 0:
        failures.append("C1 renderSummaryBar does not compute "
                        "sortCtxMatchesFilter -- the filtered branch "
                        "never renders the sort-contextual summary, so "
                        "the stock-% / asp-delta hash-restore highlight "
                        "calls are no-ops again (359th/360th gap)")
    else:
        compute_anchor = bar.find("// Compute statistics",
                                  pred_anchor)
        pred = bar[pred_anchor:compute_anchor if compute_anchor > 0
                   else pred_anchor + 2000]
        for sort_key, state in DIM_MAPPINGS:
            if ("currentSort.key === '%s'" % sort_key) not in pred:
                failures.append("C1 sortCtxMatchesFilter has no branch "
                                "for sort key %s -- a filtered deep link "
                                "sorted by that key renders no "
                                "sort-contextual summary" % sort_key)
            if state not in pred:
                failures.append("C1 sortCtxMatchesFilter does not test "
                                "%s -- the %s summary cannot know its "
                                "filter is active" % (state, sort_key))
        if ("currentSort.key === 'sector'" in pred
                and "sortCtxMatchesFilter = !!activeSector" in pred):
            failures.append("C1 sortCtxMatchesFilter renders the sector "
                            "summary for a sector filter -- a "
                            "sector-filtered set has one sector, so the "
                            "distribution degenerates to a single bar "
                            "and the sector-vs-benchmark block already "
                            "covers it")

    # --- C2: summary appended alongside the filter stats -------------
    append_anchor = bar.find("if (sortCtxMatchesFilter) {")
    if append_anchor < 0:
        failures.append("C2 the filtered branch never appends the "
                        "sort-contextual summary -- sortCtxMatchesFilter "
                        "is computed but unused")
    else:
        append_block = bar[append_anchor:append_anchor + 600]
        if "renderSortContextSummary(filtered)" not in append_block:
            failures.append("C2 the sortCtxMatchesFilter block does not "
                            "call renderSortContextSummary(filtered) -- "
                            "the histogram never renders in the filtered "
                            "bar")

    # --- C3: compact blocks suppressed on dim match ------------------
    for sort_key, label in COMPACT_BLOCKS:
        guarded = ("currentSort.key === '%s' && !sortCtxMatchesFilter"
                   % sort_key)
        if guarded not in bar:
            failures.append("C3 the compact %s stat block is not guarded "
                            "with !sortCtxMatchesFilter -- when the full "
                            "%s sort summary renders, the same median is "
                            "shown twice in the bar"
                            % (label, label))

    # --- C4: stale no-op claims gone from the restore sites ----------
    for sentence in STALE_SENTENCES:
        if sentence in app:
            failures.append("C4 a restore-site comment still says the "
                            "stock-pct / asp-delta highlight calls \""
                            + sentence + "\" -- the sort-summary gate has "
                            "landed, so the stale claim misleads the next "
                            "reader")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: sortctx-filtered-summary: filtered summary bar renders "
          "the sort-contextual summary when the active filter's dim "
          "matches the sort key, suppresses the duplicated compact "
          "blocks, and no restore-site comment still calls the "
          "stock-% / asp-delta highlights no-ops")
    return 0


if __name__ == "__main__":
    sys.exit(main())
