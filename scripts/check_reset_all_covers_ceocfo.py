#!/usr/bin/env python3
"""Guard: resetAllFilters must actually reset the CEO/CFO highlight.

Background (345th review, 2026-11-04): window.resetAllFilters in
js/app.js (the Reset All button) cleared every chart highlight
except the CEO/CFO premium chart's. highlightCeoCfoBucket (charts.js)
was the only window.highlight*/clear*Highlight function absent from
Reset's highlight-clear list, and its toggle state
(_activeCeoCfoBucket) was never nulled either. Reset does not redraw
charts (it calls renderTable + _refreshInsights, which repopulates
insight cards only), so a clicked premium bar kept its dimmed-others /
white-stroked-active look behind the unconditional 'All filters
reset' announcement -- the same false-announcement class the 343rd /
344th reviews fixed for Escape and for the board filter, now on a
highlight-only dimension. Worse, the stale toggle state made the
next click on that same bar a silent no-op: the toggle reads the
stale state as active and nulls it instead of highlighting.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: resetAllFilters cannot be located in js/app.js.
  C2 HARD FAIL: resetAllFilters does not null _activeCeoCfoBucket
     (visual cleared, toggle state left stale -> next click no-ops).
  C3 HARD FAIL: resetAllFilters does not call
     highlightCeoCfoBucket(null, null) (state nulled, bars stay
     dimmed until the next chart redraw).
  C4 HARD FAIL: resetAllFilters no longer announces
     'All filters reset' -- the fix makes the announcement true
     (the highlight is now cleared), it must not be weakened instead.

Usage:
  scripts/check_reset_all_covers_ceocfo.py
  scripts/check_reset_all_covers_ceocfo.py --static-only

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


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    reset_body = extract_function_body(app, "window.resetAllFilters = function")
    if reset_body is None:
        print("FAIL: reset-all-covers-ceocfo: C1 resetAllFilters function "
              "not found in js/app.js")
        return 1
    if not re.search(r"window\._activeCeoCfoBucket\s*=\s*null", reset_body):
        failures.append("C2 resetAllFilters does not null "
                        "_activeCeoCfoBucket (toggle state survives a "
                        "Reset All, so the next click on the same bar "
                        "silently un-highlights instead of highlighting)")
    if not re.search(r"highlightCeoCfoBucket\(null,\s*null\)", reset_body):
        failures.append("C3 resetAllFilters does not call "
                        "highlightCeoCfoBucket(null, null) (premium bars "
                        "stay dimmed until the next chart redraw)")
    if "announce('All filters reset')" not in reset_body:
        failures.append("C4 resetAllFilters no longer announces "
                        "'All filters reset' (the fix makes it true; "
                        "do not weaken the announcement instead)")

    if failures:
        for f in failures:
            print("FAIL: reset-all-covers-ceocfo: " + f)
        return 1
    print("PASS: reset-all-covers-ceocfo: resetAllFilters nulls "
          "_activeCeoCfoBucket, clears the premium-bar highlight, and "
          "keeps the (now true) announcement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
