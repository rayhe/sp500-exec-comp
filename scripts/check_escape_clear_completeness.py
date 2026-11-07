#!/usr/bin/env python3
"""Guard: the Escape-key clear-all path must cover every chart-origin filter.

Background (342nd review, 2026-11-04): the global Escape-key clear-all
branch in js/app.js (document keydown handler, "// Clear all filters
and search") predates the pctile / stockpct / aspdelta / peerdist /
crosstab chart filters and was never extended to them. It gated and
nulled only sector/search/role + ratio/dist/conc/transition/team/yoy/
sop/gender, so:

  * with ONLY a pctile (or stockpct / aspdelta / peerdist / crosstab)
    filter active, Escape did nothing at all -- the gate did not fire;
  * with a covered filter plus one of the five active, Escape announced
    "All filters cleared" while the omitted filter kept filtering;
  * the branch never called pushState, so a refresh (or back/forward
    through the 341st-review hashchange reset) resurrected the
    pre-Escape filters from the URL, which still serialized them;
  * the branch nulled _activeGenderFilter but never cleared the gender
    chart highlight (resetAllFilters does), leaving a stale highlight;
  * the branch never refreshed Reset All button visibility, so the
    button stayed shown after Escape cleared everything.

  346th review (2026-11-05): the CEO/CFO premium highlight was the
  one remaining highlight this branch never cleared -- highlight-only
  (the click never filters the table), not in the 339th deliberately
  kept list, but absent from the gate, the nulls, and the trailing
  highlight clears. With only a premium bar highlighted Escape did
  nothing at all; with a filter plus a highlight active it announced
  the filters cleared while the bars stayed dimmed; and the stale
  toggle state made the next click on that same bar a silent no-op.
  The gate therefore covers 14 dims now (13 + CeoCfoBucket) and the
  highlight-clear list gains highlightCeoCfoBucket(null, null).

  347th review (2026-11-05): the bar click now filters the table,
  so CeoCfoBucket is a real filter dim with a dismissible chip; the
  gate and highlight-clear entries above are unchanged, and the chip
  removal in this branch is pinned by check_ceocfo_filter_table.py.

Deliberately NOT required here (339th-review scoping, unchanged):
tenure / gov / vol / board / community / quartile / position /
vol-tenure / pvponly are AF-panel or section dims this path does not
clear, so their selects and chips stay truthful. The AF-select list in
this branch must therefore stay exactly the 4 selects for the dims it
does null (af-pay-band, af-sop-tier, af-gender, af-conc) -- C6 pins
that, so a future edit cannot silently widen or narrow it.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the Escape clear-all branch cannot be located
     (marker "// Clear all filters and search" through
     "// If in search, blur it").
  C2 HARD FAIL: the gate condition does not mention one of the 14
     chart/core dims (8 pre-existing + pctile/stockpct/aspdelta/
     peerdist/crosstab + CeoCfoBucket, the 346th review's
     highlight-only state). The gate line itself is checked, not the
     whole branch, or the null blocks below would mask a gate gap.
  C3 HARD FAIL: one of the 5 newly covered dims is not nulled in the
     branch or its chip id is not removed there.
  C4 HARD FAIL: a highlight clear is missing for a nulled dim that
     has one (gender, stockpct, aspdelta, CeoCfoBucket).
     Pctile/crosstab/peerdist have no highlight-clear function (their
     visuals live in the detail row, destroyed by renderTable's tbody
     wipe -- the 370th review deletes the dead peerdist clear call
     this branch used to carry, as in resetAllFilters, which clears
     none of the three either).
  C5 HARD FAIL: the branch does not call pushState() or does not
     refresh Reset All button visibility.
  C6 HARD FAIL: the branch's _clearAfSelects call does not list
     exactly af-pay-band, af-sop-tier, af-gender, af-conc.

Usage:
  scripts/check_escape_clear_completeness.py
  scripts/check_escape_clear_completeness.py --static-only

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

# Chart/core dims the Escape gate must cover (state var suffix -> chip id).
GATE_DIMS = [
    "RatioBucket", "DistFilter", "ConcTier", "CeoTransitionFilter",
    "TeamCompletenessFilter", "YoYBucket", "SopFilter", "GenderFilter",
    "PctileTier", "StockPctTier", "AspDeltaTier", "PeerDistFilter",
    "CrosstabFilter", "CeoCfoBucket",
]
# The 5 dims added by the 342nd review (state suffix -> chip id).
NEW_DIMS = [
    ("PctileTier", "pctile-filter-chip"),
    ("StockPctTier", "stockpct-filter-chip"),
    ("AspDeltaTier", "aspdelta-filter-chip"),
    ("PeerDistFilter", "peer-dist-chip"),
    ("CrosstabFilter", "crosstab-filter-chip"),
]
# Highlight clears for nulled dims that have one (call snippet as written).
# Peer-dist is deliberately absent: its histogram lives in the detail row,
# destroyed by renderTable's tbody wipe (370th review) -- there is no
# highlight to clear, same class as pctile/crosstab.
HIGHLIGHT_CLEARS = [
    "highlightGenderChart(null)",
    "highlightStockPctBucket(null)",
    "highlightAspDeltaBucket(null)",
    "highlightCeoCfoBucket(null, null)",
]
AF_SELECTS = ["af-pay-band", "af-sop-tier", "af-gender", "af-conc"]

START = "// Clear all filters and search"
END = "// If in search, blur it"

failures = []


def fail(msg):
    failures.append(msg)


try:
    with open(APP_JS, "r", encoding="utf-8", errors="strict") as f:
        src = f.read()
except (OSError, UnicodeDecodeError) as exc:
    print(f"SKIP: cannot read {APP_JS}: {exc}")
    sys.exit(2)

start = src.find(START)
end = src.find(END, start + 1) if start >= 0 else -1
if start < 0 or end < 0:
    print("FAIL: Escape clear-all branch markers not found in js/app.js")
    sys.exit(1)
branch = src[start:end]

# C2: the gate line itself must mention every chart/core dim.
gate_lines = [ln for ln in branch.splitlines()
              if ln.strip().startswith("if (activeSector")]
if not gate_lines:
    fail("C2: Escape gate condition line not found in branch")
else:
    gate = gate_lines[0]
    for dim in GATE_DIMS:
        if f"window._active{dim}" not in gate:
            fail(f"C2: Escape gate does not mention _active{dim}")

# C3: each newly covered dim nulled + chip removed in the branch.
for dim, chip in NEW_DIMS:
    if f"window._active{dim} = null;" not in branch:
        fail(f"C3: Escape branch never nulls _active{dim}")
    if f"'{chip}'" not in branch and f'"{chip}"' not in branch:
        fail(f"C3: Escape branch never removes chip {chip}")

# C4: highlight clears for nulled dims that have one.
for snippet in HIGHLIGHT_CLEARS:
    if snippet not in branch:
        fail(f"C4: Escape branch missing highlight clear {snippet}")

# C5: cleared state persisted + Reset All button visibility refreshed.
if "pushState();" not in branch:
    fail("C5: Escape branch does not call pushState()")
if "_updateResetAllButtonVisibility()" not in branch:
    fail("C5: Escape branch does not refresh Reset All button visibility")

# C6: AF-select list exactly the 4 selects for dims this path nulls.
m = re.search(r"_clearAfSelects\(\s*\[(.*?)\]\)", branch, re.DOTALL)
if not m:
    fail("C6: Escape branch has no _clearAfSelects call")
else:
    found = sorted(set(re.findall(r"af-[a-z-]+", m.group(1))))
    if found != sorted(AF_SELECTS):
        fail(f"C6: Escape _clearAfSelects lists {found}, expected {sorted(AF_SELECTS)}")

if failures:
    for msg in failures:
        print(f"FAIL: {msg}")
    sys.exit(1)
print("PASS: Escape clear-all covers all chart-origin filters + persists + refreshes")
