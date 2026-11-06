#!/usr/bin/env python3
"""Guard: hashchange handler clears the comp-dist and conc-dist chart
highlights when a back/forward navigation drops the dist / conc filter.

Background (360th review, 2026-11-06): the hashchange handler's conc
restore block was if-only -- no else-clear -- mirroring the CEO-CFO
gap the 359th review fixed. The only clear for the conc ring was
incidental: nested inside the ratio block's else branch, so it ran
only when the new hash carried NO ratio bucket. A back/forward
navigation from a conc-filtered view into a hash carrying a ratio
bucket (but no conc filter) nulled the state and removed the chip,
but left the conc-dist ring on the bar with no filter behind it --
the conc chart is NOT in the sector-aware redraw set, so nothing
else wipes it (proven by render_check_360.py R3, which fails on the
pre-fix tree). The dist block had the same if-only shape; its ring
is currently wiped by the sector-aware redraw that setActiveSector
(null) triggers at the top of the handler, so the dist else-clear is
defense-in-depth (the last if-only restore block, and its only other
clear was the same incidental ratio-branch one being removed). The
fix gives each dim its own else-clear, guarded on its own highlight
function, and removes the incidental clears from the ratio else
branch so each dim has exactly one clear site.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the hashchange handler's dist restore block does not
     clear the comp-dist highlight when the new hash drops the dist
     filter (symmetry/defense-in-depth: the ring is currently wiped
     by the sector-aware redraw, but this was the last if-only
     restore block and the ratio-branch incidental clear is gone).
  C2 HARD FAIL: the hashchange handler's conc restore block does not
     clear the conc-dist highlight when the new hash drops the conc
     tier.
  C3 HARD FAIL: the ratio else branch still clears comp-dist / conc
     incidentally -- the dedicated else branches own the clear now, and
     a second clear site (guarded on highlightRatioBucket's existence,
     not the dim's own function) is a stale-site trap.

Usage:
  scripts/check_hashchange_dist_conc_clear.py
  scripts/check_hashchange_dist_conc_clear.py --static-only

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

    handler = extract_function_body(
        app, "window.addEventListener('hashchange', function() {")
    if handler is None:
        failures.append("C1 hashchange handler not found in js/app.js")
        print("FAIL: " + failures[0])
        return 1

    # --- C1: dist restore block clears comp-dist when dropped -------
    dist_anchor = handler.find("if (window._activeDistFilter) {")
    if dist_anchor < 0:
        failures.append("C1 dist restore block not found in the "
                        "hashchange handler")
    else:
        conc_anchor = handler.find("// Restore conc dist bucket highlight",
                                   dist_anchor)
        dist_block = handler[dist_anchor:conc_anchor if conc_anchor > 0
                             else dist_anchor + 1200]
        if "highlightCompDistBucket(null)" not in dist_block:
            failures.append("C1 hashchange handler does not clear the "
                            "comp-dist highlight when the new hash drops "
                            "the dist filter -- the last if-only restore "
                            "block in the handler (every other dim has an "
                            "else-clear since the 359th); the ring is "
                            "currently wiped by the sector-aware redraw, "
                            "so this is defense-in-depth, not a live "
                            "stale ring today")

    # --- C2: conc restore block clears conc-dist when dropped -------
    conc_anchor = handler.find("if (window._activeConcTier && "
                               "window.highlightConcDistBucket) {")
    if conc_anchor < 0:
        failures.append("C2 conc restore block not found in the "
                        "hashchange handler")
    else:
        ceocfo_anchor = handler.find("// Restore CEO/CFO premium bucket "
                                     "highlight", conc_anchor)
        conc_block = handler[conc_anchor:ceocfo_anchor if ceocfo_anchor > 0
                             else conc_anchor + 1200]
        if "highlightConcDistBucket(null, null)" not in conc_block:
            failures.append("C2 hashchange handler does not clear the "
                            "conc-dist highlight when the new hash drops "
                            "the conc tier -- a back/forward navigation "
                            "into a ratio-carrying hash leaves a stale "
                            "ring with its chip already removed (same "
                            "incidental-clear-only class as C1)")

    # --- C3: no incidental comp/conc clear inside ratio else --------
    ratio = extract_function_body(handler, "if (window.highlightRatioBucket) {")
    if ratio is not None:
        if "highlightCompDistBucket(null)" in ratio:
            failures.append("C3 the ratio else branch still clears the "
                            "comp-dist highlight incidentally -- the dist "
                            "else branch owns that clear now; a second "
                            "site guarded on highlightRatioBucket's "
                            "existence is a stale-site trap")
        if "highlightConcDistBucket(null, null)" in ratio:
            failures.append("C3 the ratio else branch still clears the "
                            "conc-dist highlight incidentally -- the conc "
                            "else branch owns that clear now; a second "
                            "site guarded on highlightRatioBucket's "
                            "existence is a stale-site trap")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: hashchange-dist-conc-clear: hashchange handler clears "
          "the comp-dist and conc-dist highlights when the new hash drops "
          "the dist filter / conc tier, and the ratio else branch holds "
          "no incidental second clear site")
    return 0


if __name__ == "__main__":
    sys.exit(main())
