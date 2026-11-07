#!/usr/bin/env python3
"""Guard: Escape's detail-close branch must null the expanded-detail
state (and drop the hash params) like the other close paths.

Background (372nd review, 2026-11-07): closes the 371st run's candidate
(1). The 371st review fixed Reset All: it nulled _expandedDetailTicker
and _activeDiffKey before pushState so a reload after a reset cannot
re-expand the old panel. Escape's detail-close branch had the same
stale-state bug in milder form: it removed the .detail-row and cleared
.selected but never nulled _expandedDetailTicker (or _activeDiffKey),
never called pushState, left aria-expanded="true" on the trigger row,
and only nulled _detailTriggerRow inside the isConnected focus check.
The hash kept detail= (and diff=) until the next pushState, so a reload
after an Escape close re-expanded the panel. The fix mirrors the
close-button path: remove aria-expanded, null the trigger row
unconditionally, null the ticker/diff pair, pushState. The same run
also closes the dangling-trigger-row secondary: resetAllFilters and the
hashchange-clear path destroy the detail row via a tbody wipe without
nulling _detailTriggerRow (latent -- every reader guards with
isConnected), and the close-button path never nulled _activeDiffKey
(hash-safe since the ticker was nulled, but out of step with the
pair-null invariant the toggle-off and reset paths already keep).

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: Escape's detail-close branch does not null
     _expandedDetailTicker.
  C2 HARD FAIL: Escape's detail-close branch does not null
     _activeDiffKey (the diff viewer lives inside the detail panel,
     so its key dies with it).
  C3 HARD FAIL: either null comes AFTER the pushState() call inside
     the Escape branch -- pushState serializes detail= from the
     variable, so a late null leaves the stale ticker in the hash.
  C4 HARD FAIL: the Escape branch does not remove aria-expanded from
     the trigger row -- it would keep claiming expanded with no
     panel open.
  C5 HARD FAIL: the Escape branch nulls _detailTriggerRow only inside
     the isConnected focus check (or not at all) -- a detached trigger
     row would leave the reference dangling.
  C6 HARD FAIL: the close-button handler does not null _activeDiffKey
     -- all three close paths must keep the pair-null invariant.
  C7 HARD FAIL: resetAllFilters does not null _detailTriggerRow -- the
     renderTable tbody wipe below detaches the row it points at.
  C8 HARD FAIL: the hashchange-clear path does not null
     _detailTriggerRow -- the .detail-row removal there detaches the
     trigger row too.

Usage:
  scripts/check_escape_detail_close.py
  scripts/check_escape_detail_close.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
import re
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


def extract_block_after(src, anchor, open_marker):
    """Return the brace-matched block opened by open_marker at/after anchor.

    Returns (body, start_index, end_index) or (None, -1, -1).
    """
    a = src.find(anchor)
    if a < 0:
        return None, -1, -1
    m = src.find(open_marker, a)
    if m < 0:
        return None, -1, -1
    brace = src.find("{", m)
    if brace < 0:
        return None, -1, -1
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[brace:i + 1], brace, i + 1
    return None, -1, -1


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- Escape detail-close branch ----------------------------------
    # The search is over js/app.js only, so marker phrases quoted here
    # as string literals cannot false-positive on this guard's own
    # source (same convention as the 371st reset-ticker guard's C4).
    esc, esc_start, esc_end = extract_block_after(
        app, "var detailRow = document.querySelector('.detail-row');",
        "if (detailRow)")
    if esc is None:
        failures.append("C1 Escape detail-close branch not found in "
                        "js/app.js (no 'if (detailRow)' after the "
                        ".detail-row query)")
    else:
        ticker_null = re.search(r"_expandedDetailTicker\s*=\s*null\b", esc)
        if ticker_null is None:
            failures.append("C1 Escape detail-close does not null "
                            "_expandedDetailTicker -- the hash keeps "
                            "detail=<ticker> until the next pushState and "
                            "a reload re-expands the panel")
        diff_null = re.search(r"_activeDiffKey\s*=\s*null\b", esc)
        if diff_null is None:
            failures.append("C2 Escape detail-close does not null "
                            "_activeDiffKey -- the repair-diff viewer lives "
                            "inside the detail panel, so its key must die "
                            "with it")
        push_idx = esc.find("pushState()")
        if push_idx < 0:
            failures.append("C3 Escape detail-close has no pushState() call "
                            "-- cannot verify the null-before-push ordering")
        else:
            if ticker_null is not None and ticker_null.start() > push_idx:
                failures.append("C3 _expandedDetailTicker is nulled AFTER "
                                "pushState() in the Escape branch -- the "
                                "stale ticker is already in the hash")
            if diff_null is not None and diff_null.start() > push_idx:
                failures.append("C3 _activeDiffKey is nulled AFTER "
                                "pushState() in the Escape branch -- the "
                                "stale diff key is already serialized")
        if "tr[aria-expanded]" not in esc:
            failures.append("C4 Escape detail-close does not remove "
                            "aria-expanded -- the trigger row keeps claiming "
                            "expanded with no panel open")
        # C5: the trigger null must sit OUTSIDE the isConnected focus-if.
        focus_blk, fb_start, fb_end = extract_block_after(
            esc, "// Return focus to the row that opened the detail panel",
            "if (_detailTriggerRow")
        # fb_* are offsets into esc: extract_block_after returns the
        # block's span within the string it was given.
        if focus_blk is None:
            failures.append("C5 Escape focus-return if-block not found -- "
                            "cannot verify the unconditional trigger null")
        else:
            null_idx = esc.find("_detailTriggerRow = null;")
            if null_idx < 0:
                failures.append("C5 Escape detail-close never nulls "
                                "_detailTriggerRow -- the reset/destroy "
                                "paths leave a dangling reference")
            elif fb_start <= null_idx < fb_end:
                failures.append("C5 _detailTriggerRow is nulled only INSIDE "
                                "the isConnected focus check in the Escape "
                                "branch -- a detached trigger row leaves "
                                "the reference dangling; null it "
                                "unconditionally like the close-button path")

    # --- C6: close-button handler keeps the pair-null invariant -------
    close_fn = extract_function_body(
        app, "_closeBtn.addEventListener('click', function(e)")
    if close_fn is None:
        failures.append("C6 detail close-button handler not found in "
                        "js/app.js")
    elif "_activeDiffKey = null" not in close_fn:
        failures.append("C6 close-button handler does not null "
                        "_activeDiffKey -- the toggle-off and reset paths "
                        "already null the pair, so the button must too")

    # --- C7: resetAllFilters nulls the trigger row --------------------
    reset_fn = extract_function_body(app, "window.resetAllFilters = function")
    if reset_fn is None:
        failures.append("C7 resetAllFilters function not found in js/app.js")
    elif "_detailTriggerRow = null" not in reset_fn:
        failures.append("C7 resetAllFilters does not null _detailTriggerRow "
                        "-- the renderTable tbody wipe detaches the row it "
                        "points at")

    # --- C8: hashchange-clear path nulls the trigger row --------------
    hash_fn = extract_function_body(
        app, "window.addEventListener('hashchange', function()")
    if hash_fn is None:
        failures.append("C8 hashchange handler not found in js/app.js")
    elif "_detailTriggerRow = null" not in hash_fn:
        failures.append("C8 hashchange-clear path does not null "
                        "_detailTriggerRow -- the .detail-row removal there "
                        "detaches the trigger row too")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: escape-detail-close: Escape nulls _expandedDetailTicker, "
          "_activeDiffKey and _detailTriggerRow before pushState and clears "
          "aria-expanded; close-button nulls the diff key; resetAllFilters "
          "and hashchange null the trigger row")
    return 0


if __name__ == "__main__":
    sys.exit(main())
