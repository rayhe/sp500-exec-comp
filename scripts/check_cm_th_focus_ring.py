#!/usr/bin/env python3
"""Regression guard: community-comparison sort headers show a keyboard focus ring.

The Community Compensation Comparison table's column headers (.cm-th) are
tabindex="0" role="columnheader" sort controls with click and Enter/Space
keydown wired in _renderCommunityMetrics (js/network.js) -- a 2026-10-09
5-critic panel (Interactivity dimension) found they were the last
keyboard-operable surface without a :focus-visible ring, so keyboard users
could not see which header had focus. css/style.css now carries a
.cm-th:focus-visible rule using the site's --accent outline convention
(matching #sector-chart rect.bar:focus-visible etc.).

Checks (all static; the wiring itself predates this guard and is asserted
here only for co-change safety):
  S1 .cm-th headers are rendered with tabindex="0", role="columnheader",
     and both click and Enter/Space keydown handlers in _renderCommunityMetrics.
  S2 css/style.css has a .cm-th:focus-visible rule with the --accent
     outline convention (2px solid var(--accent), 2px offset).

Usage:
  scripts/check_cm_th_focus_ring.py              # static checks
  scripts/check_cm_th_focus_ring.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK_JS = os.path.join(REPO, "js", "network.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    js = open(NETWORK_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: the header render wires tabindex, role, click and Enter/Space.
    # (The header HTML is built inside a single-quoted JS string, so its
    # attributes appear backslash-escaped in the file source.)
    s1 = ("data-cm-sort" in js
          and 'tabindex=\"0\"' in js
          and 'role=\"columnheader\"' in js
          and "th.addEventListener('click'" in js
          and "th.addEventListener('keydown'" in js
          and "ev.key === 'Enter' || ev.key === ' '" in js)
    check("S1 .cm-th headers are tabindex=0 columnheaders with click + Enter/Space keydown",
          s1, "" if s1 else "sort-header keyboard wiring missing or altered")

    # S2: the --accent focus-visible rule exists on .cm-th.
    m = re.search(r"\.cm-th:focus-visible\s*\{([^}]*)\}", css)
    s2 = (m is not None
          and "outline: 2px solid var(--accent)" in m.group(1)
          and "outline-offset: 2px" in m.group(1))
    check("S2 .cm-th:focus-visible ring uses --accent convention",
          s2, "" if s2 else "focus ring missing or off-convention")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    # Pure CSS addition: full mode is the static checks.
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
