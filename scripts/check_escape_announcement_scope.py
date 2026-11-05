#!/usr/bin/env python3
"""Guard: the Escape-key clear-all announcement must be scoped to kept filters.

Background (343rd review, 2026-11-04): the global Escape-key clear-all
branch in js/app.js (document keydown handler, "// Clear all filters
and search") deliberately keeps the AF-panel/session dims tenure / gov /
vol / board / community / quartile / position / vol-tenure / pvponly
(339th-review scoping, unchanged), but its announcement was an
unconditional "All filters cleared". With a chart filter plus e.g. a
tenure filter active, Escape announced everything clear while the kept
filter kept filtering with no audible trace -- the same false-announcement
class the 342nd review fixed for the five omitted chart dims, now on the
announcement side. The fix scopes the announcement: "All filters
cleared" only when nothing remains, else "Filters cleared; still
active: <dims>" naming the kept dims still filtering.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the Escape clear-all branch cannot be located
     (marker "// Clear all filters and search" through
     "// If in search, blur it").
  C2 HARD FAIL: the branch does not read one of the 9 deliberately
     kept states before the announcement (each must appear before
     the "still active" announce, so a future edit cannot silently
     drop a kept dim from the announcement).
  C3 HARD FAIL: the branch still contains the bare unconditional
     statement announce('All filters cleared'); -- on the fixed tree
     that string appears only inside the kept-empty ternary.
  C4 HARD FAIL: the branch has no "still active" announce, or the
     "All filters cleared" string is not in a ternary/conditional
     form (": 'All filters cleared'").

Usage:
  scripts/check_escape_announcement_scope.py
  scripts/check_escape_announcement_scope.py --static-only

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

# Deliberately kept dims (339th-review scoping): state var -> announce label.
KEPT_DIMS = [
    ("TenureQuartile", "tenure"),
    ("GovGrade", "governance"),
    ("VolatilityBucket", "volatility"),
    ("VolTenureBracket", "volatility-tenure"),
    ("BoardFilter", "board"),
    ("CommunityFilter", "community"),
    ("QuartileFilter", "quartile"),
    ("PositionFilter", "position"),
    ("PvpOnlyFilter", "PvP-covered"),
]

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

# C2: every kept state read before the scoped announce.
# rfind, not find: the 343rd-review comment block above the kept list
# itself contains the phrase "still active", so the first occurrence
# is prose, not the announce. The announce line is the last one.
still_at = branch.rfind("still active")
if still_at < 0:
    fail("C2: Escape branch has no 'still active' announce to scope against")
else:
    pre = branch[:still_at]
    for dim, label in KEPT_DIMS:
        if f"window._active{dim}" not in pre:
            fail(f"C2: Escape branch never reads kept state _active{dim} before announce")
        if f"'{label}'" not in pre:
            fail(f"C2: Escape branch never labels kept dim '{label}' before announce")

# C3: no bare unconditional announcement remains.
if "announce('All filters cleared');" in branch:
    fail("C3: Escape branch still has unconditional announce('All filters cleared');")

# C4: scoped announce present, with 'All filters cleared' only in ternary form.
if "still active" not in branch:
    fail("C4: Escape branch has no 'still active' announce")
if not re.search(r":\s*'All filters cleared'", branch):
    fail("C4: 'All filters cleared' is not in a conditional (ternary) form in the Escape branch")

if failures:
    for msg in failures:
        print(f"FAIL: {msg}")
    sys.exit(1)
print("PASS: Escape announcement scoped to kept filters (all 9 kept dims named)")
