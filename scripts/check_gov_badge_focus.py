#!/usr/bin/env python3
"""Regression guard: governance-score badge shows hover affordance on keyboard focus.

The 2026-10-27 10:00 PT run (244th review) found the next straggler
after the 243rd run closed the NEW CEO badge: the main table's
governance-score badge (.gov-badge-clickable, js/app.js:7731) is
keyboard-operable - _kbdUpgradeRoving() (js/app.js:7780) gives it a
roving tabindex and an Enter/Space path into the same
filter-by-governance-grade action as a mouse click - but its hover
affordance appeared only on :hover: filter brightness(1.2) plus
scale(1.05). Keyboard focus got only the generic
[data-kbd-upgraded]:focus-visible accent ring. css/style.css now
mirrors the hover affordance onto :focus-visible with exactly the
hover values. The non-clickable .gov-badge (detail panel) has no
hover rule and is not in the roving set, so it is out of scope here.
Unlike the NEW CEO badge, the governance badge has no light-theme
hover override, so there is no per-theme split to mirror.

Checks (all static):
  S1 js/app.js passes .gov-badge-clickable to _kbdUpgradeRoving
     (keyboard surface).
  S2 css/style.css has a :focus-visible affordance for the badge.
  S3 the focus-visible affordance matches the hover affordance
     exactly (no drift between the two affordances).

Usage:
  scripts/check_gov_badge_focus.py
  scripts/check_gov_badge_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: governance badge is keyboard-operable via the roving surface.
    roving_start = js.find("_kbdUpgradeRoving(tbody")
    s1 = (".gov-badge-clickable" in js
          and roving_start != -1
          and ".gov-badge-clickable" in js[roving_start:roving_start + 300])
    check("S1 governance badge gets the roving-tabindex keyboard surface",
          s1, "" if s1 else "governance badge keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    badge_focus = rule_bodies(".gov-badge-clickable:focus-visible")

    # S2: focus-visible mirrors the hover affordance.
    s2 = any("brightness(1.2)" in b and "scale(1.05)" in b for b in badge_focus)
    check("S2 :focus-visible mirrors hover affordance",
          s2, "" if s2 else "focus-visible governance badge affordance missing in css/style.css")

    # S3: focus affordance == hover affordance (no drift).
    badge_hover = rule_bodies(".gov-badge-clickable:hover")

    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    s3 = (has(badge_hover, "brightness(1.2)", "scale(1.05)")
          and has(badge_focus, "brightness(1.2)", "scale(1.05)"))
    check("S3 focus affordance matches hover affordance",
          s3, "" if s3 else "focus/hover governance badge affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
