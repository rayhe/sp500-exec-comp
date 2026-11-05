#!/usr/bin/env python3
"""Guard: the Sector Tenure / Sector SoP insight-card actions must filter
through the real sector state, not a one-shot table subset.

Background (348th review, 2026-11-05): the two insight cards promise
"Filter to <sector>" but implemented it as a one-shot
renderTable(companies.filter(sector)) plus a write to
window._activeSectorFilter -- state nothing ever read (two writes, zero
reads across js/). Consequences, all verified against renderTable /
renderSummaryBar / serializeState / setActiveSector:

  * No visible indicator: the sector chip stayed on 'All'
    (insightResetAndSort marks the first chip active), the summary bar
    showed no sector part, the URL carried no sector= param, and the
    live-region announcement said nothing about the sector -- every one
    of those reads `activeSector`, which stayed null.
  * The restriction evaporated on the next renderTable(companies) from
    any other interaction (chart click, chip dismiss, sort, search),
    because the sector filter was never state -- a "Filter to X" action
    whose effect silently vanished with no way to dismiss or re-derive
    it, and no chip to tell the user the table was restricted at all.

The fix routes both actions through the site's own sector-filter
convention (same as the sector chip and the sector-analytics row click):
insightResetAndSort, setActiveSector(name), currentPage = 1,
renderTable(companies), sync the .chip active class to the sector,
highlightSectorBar(name). renderTable's own pushState then carries the
sector into the hash, and the summary bar / announcement pick it up
from activeSector. The dead _activeSectorFilter writes are removed;
no code anywhere reads that name.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: either insight card (label 'Sector Tenure' / 'Sector
     SoP') cannot be located in js/app.js.
  C2 HARD FAIL: either action still renders a one-shot subset
     (renderTable(companies.filter) or a _activeSectorFilter write.
  C3 HARD FAIL: either action does not call setActiveSector with its
     sector variable's .name (longestSec / lowestSec) followed by
     renderTable(companies).
  C4 HARD FAIL: either action does not sync the .chip active class to
     its sector name or does not call highlightSectorBar with it.
  C5 HARD FAIL: any _activeSectorFilter reference remains anywhere in
     js/*.js (the dead state must be fully gone, not just moved).

Usage:
  scripts/check_insight_sector_filter.py
  scripts/check_insight_sector_filter.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import glob
import os
import re
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = f"{REPO}/js/app.js"

if "--static-only" in sys.argv:
    pass  # static half is the whole check; flag accepted for the hook runner

# label -> sector variable used by that card's action.
CARDS = [
    ("Sector Tenure", "longestSec"),
    ("Sector SoP", "lowestSec"),
]

failures = []


def fail(msg):
    failures.append(msg)
    print(f"FAIL: {msg}")


def strip_comment_lines(text):
    """Drop full-line // comments: the 348th-review comments name the
    removed state for the record, and a name inside a comment is not
    live state. Code occurrences (assignments, reads) survive."""
    return "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith("//")
    )


def main():
    try:
        with open(APP_JS, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"INFRA: cannot read {APP_JS}: {e}")
        return 2

    for label, var in CARDS:
        start = src.find("label: '" + label + "'")
        if start == -1:
            fail(f"C1: insight card '{label}' not found in js/app.js")
            continue
        # The action block runs from the card label to its actionHint line.
        hint = src.find("actionHint:", start)
        if hint == -1:
            fail(f"C1: actionHint not found after '{label}' card")
            continue
        block = strip_comment_lines(src[start:hint])

        if "renderTable(companies.filter" in block:
            fail(f"C2: '{label}' action still renders a one-shot "
                 f"renderTable(companies.filter(...)) subset")
        if "_activeSectorFilter" in block:
            fail(f"C2: '{label}' action still writes dead "
                 f"window._activeSectorFilter")

        set_idx = block.find(f"setActiveSector({var}.name)")
        if set_idx == -1:
            fail(f"C3: '{label}' action does not call "
                 f"setActiveSector({var}.name)")
        else:
            render_idx = block.find("renderTable(companies)", set_idx)
            if render_idx == -1:
                fail(f"C3: '{label}' action does not call "
                     f"renderTable(companies) after setActiveSector")

        if f"chip.textContent === {var}.name" not in block:
            fail(f"C4: '{label}' action does not sync the .chip active "
                 f"class to {var}.name")
        if f"highlightSectorBar({var}.name)" not in block:
            fail(f"C4: '{label}' action does not call "
                 f"highlightSectorBar({var}.name)")

    # C5: dead state must be gone from the whole JS tree, not just the
    # two actions (comment mentions of the removed name do not count).
    for path in sorted(glob.glob(f"{REPO}/js/*.js")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                js = strip_comment_lines(f.read())
        except OSError as e:
            print(f"INFRA: cannot read {path}: {e}")
            return 2
        if "_activeSectorFilter" in js:
            fail(f"C5: dead _activeSectorFilter reference remains in "
                 f"{os.path.basename(path)}")

    if failures:
        return 1
    print("OK: insight sector actions filter through setActiveSector; "
          "no one-shot subset, no dead _activeSectorFilter")
    return 0


if __name__ == "__main__":
    sys.exit(main())
