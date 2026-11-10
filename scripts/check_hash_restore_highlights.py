#!/usr/bin/env python3
"""Guard: hash-restored gov/gender/tenure/SoP/asp-delta/stock-%/vol filters
must highlight their chart buckets at init and on back/forward.

Background (359th review, 2026-11-06): the init restore block and the
hashchange handler restored chart highlights for only six dims (sector,
ratio, YoY, comp-dist, conc, CEO-CFO). The other six hash-serialized
dims with highlight functions -- gov, gender, tenure, SoP, asp-delta,
stock-% -- filtered the table and raised their chips on a deep link or
a back/forward navigation, but left their charts un-ringed: the charts
draw before applyHashState at init, and no chart redraw happens on
hashchange, so the draw-time application never saw the restored state.
Vol joined the serialized set in the 412th review (2026-11-10), so its
highlight is restored/cleared with the rest; vol-tenure / board /
pctile, peer-dist and crosstab have no highlight function to call. The
same block also had a missing else-clear for CEO/CFO: a navigation that
dropped cfomin left the ring while the chip was already removed.

Checks (all static - small JS reads, <2s):
  C1-C7 HARD FAIL: the init restore block (after applyHashState, before
     the table-scroll-indicator setup) does not restore the gov /
     gender / tenure / SoP / asp-delta / stock-% / vol highlight from
     the restored state.
  C8-C14 HARD FAIL: the hashchange handler does not restore the gov /
     gender / tenure / SoP / asp-delta / stock-% / vol highlight when
     the new hash carries the filter, or does not clear it when the new
     hash drops the filter (a dropped filter's ring would linger with
     its chip already removed -- the ratio / YoY else-branch class).
  C15 HARD FAIL: the hashchange handler does not clear the CEO/CFO
     highlight when the new hash drops cfomin (same stale-ring class).
  C16 HARD FAIL: applyHashState calls the gov chip indicator bare
     (updateGovFilterIndicator is nested inside the data-load
     callback, invisible to top-level applyHashState) instead of via
     the guarded window accessor -- a gov deep link or a back/forward
     navigation into a gov hash throws ReferenceError and aborts
     applyHashState (and the whole hashchange handler) mid-way, so no
     later dim restores, no renderTable, and no highlight restores run.
  C17 HARD FAIL: applyHashState decodes a hash value a second time
     (parseHash already decoded every key/value once) -- a label
     holding a literal percent sign throws URIError and aborts the
     whole restore; every YoY and stock-% label holds one, so those
     deep links never restored at all.
  C18 HARD FAIL: a comparison restore still maps decodeURIComponent
     over tickers parseHash already decoded -- same double-decode
     class (harmless for tickers today, a trap for the next value
     format).

Usage:
  scripts/check_hash_restore_highlights.py
  scripts/check_hash_restore_highlights.py --static-only

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


# (dim label, restore call, clear call)
DIMS = [
    ("gov", "highlightGovChart(window._activeGovGrade.min, window._activeGovGrade.max)",
     "highlightGovChart(null)"),
    ("gender", "highlightGenderChart(window._activeGenderFilter)",
     "highlightGenderChart(null)"),
    ("tenure", "highlightTenureBucket(window._activeTenureQuartile.min, window._activeTenureQuartile.max)",
     "highlightTenureBucket(null, null)"),
    ("sop", "highlightSopDistBucket(window._activeSopFilter.min, window._activeSopFilter.max)",
     "highlightSopDistBucket(null)"),
    ("asp-delta", "highlightAspDeltaBucket(window._activeAspDeltaTier.min, window._activeAspDeltaTier.max)",
     "highlightAspDeltaBucket(null, null)"),
    ("stock-%", "highlightStockPctBucket(window._activeStockPctTier.min, window._activeStockPctTier.max)",
     "highlightStockPctBucket(null, null)"),
    ("vol", "highlightVolatilityBucket(window._activeVolatilityBucket.min, window._activeVolatilityBucket.max)",
     "highlightVolatilityBucket(null, null)"),
]


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1-C7: init restore block restores all seven highlights -----
    init_start = app.find("applyHashState(companies);\n    _stateInitialized = true;")
    if init_start < 0:
        failures.append("C1 init restore anchor (applyHashState + "
                        "_stateInitialized) not found in js/app.js")
        init_block = ""
    else:
        init_end = app.find("// === Table horizontal scroll indicator ===",
                            init_start)
        if init_end < 0:
            failures.append("C1 init restore end marker (table-scroll "
                            "indicator setup) not found in js/app.js")
            init_block = ""
        else:
            init_block = app[init_start:init_end]
    if init_block:
        for i, (label, restore, _clear) in enumerate(DIMS):
            if restore not in init_block:
                failures.append(f"C{i + 1} init restore block does not "
                                f"restore the {label} chart highlight "
                                f"from hash state -- a deep link carrying "
                                f"the filter filters the table and raises "
                                f"the chip but leaves the chart un-ringed")

    # --- C8-C14: hashchange handler restores and clears ------------
    handler = extract_function_body(
        app, "window.addEventListener('hashchange', function() {")
    if handler is None:
        failures.append("C7 hashchange handler not found in js/app.js")
    else:
        for i, (label, restore, clear) in enumerate(DIMS):
            if restore not in handler:
                failures.append(f"C{i + 8} hashchange handler does not "
                                f"restore the {label} chart highlight "
                                f"from the new hash -- a back/forward "
                                f"navigation into the filter leaves the "
                                f"chart un-ringed (no redraw happens on "
                                f"hashchange)")
            if clear not in handler:
                failures.append(f"C{i + 8} hashchange handler does not "
                                f"clear the {label} chart highlight when "
                                f"the new hash drops the filter -- the "
                                f"ring lingers with its chip already "
                                f"removed")

    # --- C15: hashchange handler clears CEO/CFO when dropped --------
    if handler is not None and "highlightCeoCfoBucket(null, null)" not in handler:
        failures.append("C15 hashchange handler does not clear the "
                        "CEO/CFO highlight when the new hash drops "
                        "cfomin -- a back/forward navigation out of the "
                        "filter leaves a stale ring")

    # --- C16: applyHashState calls the gov indicator via window -----
    import re
    apply = extract_function_body(app, "function applyHashState(companies)")
    if apply is None:
        failures.append("C16 applyHashState function not found in js/app.js")
    else:
        if "window._updateGovFilterIndicator()" not in apply:
            failures.append("C16 applyHashState does not call the gov "
                            "chip indicator via window._updateGovFilterIndicator "
                            "-- the nested declaration is invisible here")
        # A bare call at line start (not inside a comment) throws
        # ReferenceError: the declaration lives inside the data-load
        # callback, not at top level. The legit bare call inside
        # filterByGovGrade is in another function body, not this one.
        if re.search(r"(?m)^\s*updateGovFilterIndicator\(\);", apply):
            failures.append("C16 applyHashState still calls "
                            "updateGovFilterIndicator() bare -- a gov deep "
                            "link or a navigation into a gov hash throws "
                            "ReferenceError and aborts the restore mid-way")

    # --- C17: no second decode of hash values in applyHashState ----
    if apply is not None and "decodeURIComponent(state." in apply:
        failures.append("C17 applyHashState still decodes a hash value a "
                        "second time -- parseHash already decoded it once, "
                        "so a label holding a literal percent sign (every "
                        "YoY and stock-% label) throws URIError and aborts "
                        "the whole restore")

    # --- C18: comparison restores do not double-decode -------------
    if ".map(decodeURIComponent)" in app:
        failures.append("C18 a comparison restore still maps "
                        "decodeURIComponent over tickers parseHash already "
                        "decoded -- same double-decode class (harmless for "
                        "tickers today, a trap for the next value format)")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: hash-restore-highlights: init restore block and "
          "hashchange handler restore gov/gender/tenure/SoP/asp-delta/"
          "stock-%/vol chart highlights from hash state and clear them when "
          "the hash drops the filter; CEO/CFO else-clear present; "
          "applyHashState calls the gov indicator via the guarded "
          "window accessor and never decodes a hash value twice; "
          "comparison restores do not double-decode")
    return 0


if __name__ == "__main__":
    sys.exit(main())
