#!/usr/bin/env python3
"""Guard: the Escape-key clear-all path must clear the CEO/CFO highlight.

Background (346th review, 2026-11-05): the global Escape-key
clear-all branch in js/app.js (document keydown handler,
"// Clear all filters and search") cleared every chart highlight
except the CEO/CFO premium chart's. Enumerating every
window.highlight*/clear*Highlight function against the branch's
highlight-clear list leaves exactly one absentee among the dims
Escape does not deliberately keep: highlightCeoCfoBucket
(charts.js). The other absentees are all 339th-review deliberately
kept dims (tenure / gov / vol / board / community / quartile /
position -- highlightTenureBucket, highlightGovChart,
highlightVolatilityBucket, clearCommunityHighlight,
clearPositionHighlight, clearQuartileHighlight), and
highlightSopBucket is the SoP setter, not a highlight clear
(Escape nulls _activeSopFilter and calls
highlightSopDistBucket(null) for its visual, as the 345th review
established). The premium highlight is highlight-only -- the bar
click never filters the table -- so it is not in the kept list,
yet it was absent from the gate, the nulls, and the trailing
highlight clears:

  * with ONLY a premium bar highlighted, Escape did nothing at
    all -- the gate did not fire, so the branch never ran;
  * with a filter plus a highlight active, Escape announced the
    filters cleared while the premium bars stayed dimmed with a
    white-stroked "active" bar;
  * the stale toggle state (_activeCeoCfoBucket) made the next
    click on that same bar a silent no-op: the toggle reads the
    stale state as active and nulls it instead of highlighting
    (the 345th review's second facet, now on this path, which
    Reset All already closed).

The fix adds the state to the gate (so Escape fires on a
highlight-only state -- it is the only highlight with no
corresponding filter, so it is also the only one Escape could
not otherwise reach), nulls the toggle state, and clears the
visual, mirroring the 345th review's Reset All fix. The scoped
announcement is unchanged: the premium bucket is highlight-only,
not a filtering dim, so it must never join the keptEsc list.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the Escape clear-all branch cannot be located
     (marker "// Clear all filters and search" through
     "// If in search, blur it").
  C2 HARD FAIL: the gate condition does not mention
     window._activeCeoCfoBucket, so Escape is still a no-op with
     only a premium bar highlighted.
  C3 HARD FAIL: the branch does not null _activeCeoCfoBucket
     (visual cleared, toggle state left stale -> next click
     no-ops).
  C4 HARD FAIL: the branch does not call
     highlightCeoCfoBucket(null, null) (state nulled, bars stay
     dimmed until the next chart redraw).
  C5 HARD FAIL: the scoped announcement was changed, or the
     premium bucket joined the keptEsc list (it is highlight-only,
     not a filtering dim -- clearing it needs no announcement
     change, and listing it as "still active" would mislabel a
     highlight as a filter).

Usage:
  scripts/check_escape_clears_ceocfo.py
  scripts/check_escape_clears_ceocfo.py --static-only

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

START = "// Clear all filters and search"
END = "// If in search, blur it"
ANNOUNCE = ("announce(keptEsc.length ? 'Filters cleared; still active: ' "
            "+ keptEsc.join(', ') : 'All filters cleared')")

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
    print("FAIL: escape-clears-ceocfo: C1 Escape clear-all branch "
          "markers not found in js/app.js")
    sys.exit(1)
branch = src[start:end]

# C2: the gate line itself must mention the premium toggle state, or
# Escape stays a no-op with only a premium bar highlighted.
gate_lines = [ln for ln in branch.splitlines()
              if ln.strip().startswith("if (activeSector")]
if not gate_lines:
    fail("C2: Escape gate condition line not found in branch")
elif "window._activeCeoCfoBucket" not in gate_lines[0]:
    fail("C2: Escape gate does not mention _activeCeoCfoBucket "
         "(highlight-only state never fires the branch)")

# C3: toggle state nulled in the branch. (The 346th comment block in
# app.js deliberately never spells the assignment, so a plain
# search cannot false-pass on prose.)
if not re.search(r"window\._activeCeoCfoBucket\s*=\s*null", branch):
    fail("C3: Escape branch does not null _activeCeoCfoBucket "
         "(toggle state survives Escape, so the next click on the "
         "same bar silently un-highlights instead of highlighting)")

# C4: premium-bar highlight cleared in the branch.
if "highlightCeoCfoBucket(null, null)" not in branch:
    fail("C4: Escape branch does not call highlightCeoCfoBucket(null, "
         "null) (premium bars stay dimmed until the next chart redraw)")

# C5: the scoped announcement is unchanged, and the premium bucket
# never joined the kept-filter list. Search only the keptEsc.push
# lines inside the kept block, so comment prose elsewhere in the
# branch cannot collide (343rd-review lesson).
kept_start = branch.find("var keptEsc = [];")
kept_end = branch.find("announce(keptEsc", kept_start) if kept_start >= 0 else -1
if kept_start < 0 or kept_end < 0:
    fail("C5: keptEsc block / announce line not found in Escape branch")
else:
    kept_block = branch[kept_start:kept_end]
    for ln in kept_block.splitlines():
        if "keptEsc.push" in ln and "ceocfo" in ln.lower():
            fail("C5: premium bucket joined the keptEsc list (it is "
                 "highlight-only, not a filtering dim)")
            break
    if ANNOUNCE not in branch:
        fail("C5: Escape announcement no longer reads 'Filters "
             "cleared; still active: ...' / 'All filters cleared' "
             "(the fix clears a highlight, it must not weaken or "
             "reword the announcement)")

if failures:
    for msg in failures:
        print(f"FAIL: {msg}")
    sys.exit(1)
print("PASS: escape-clears-ceocfo: Escape fires on a premium-bar "
      "highlight, nulls _activeCeoCfoBucket, clears the highlight, "
      "and keeps the scoped announcement")
