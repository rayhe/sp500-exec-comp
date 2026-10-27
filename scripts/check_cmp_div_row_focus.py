#!/usr/bin/env python3
"""Regression guard: comparison divergence rows show hover tint on focus.

The 2026-10-26 23:30 PT run (239th review) found the next straggler
after the 238th run closed the hover-only reveal audit: the comparison
radar's divergence rows (.cmp-div-row-clickable, js/app.js) are
keyboard-operable - _kbdUpgradeRoving() gives them roving tabindex,
role=button, an aria-label, and an Enter/Space path into the same
insightResetAndSort sort action as a mouse click - but their hover
affordance, the row background tint that signals clickability, appeared
only on :hover. Keyboard focus got only the generic
[data-kbd-upgraded]:focus-visible accent ring. css/style.css now mirrors
the hover tint onto :focus-visible, in both themes: dark
rgba(255,255,255,0.06), light rgba(0,0,0,0.04), exactly the hover values.

Checks (all static):
  S1 js/app.js renders .cmp-div-row-clickable rows and passes them to
     _kbdUpgradeRoving (keyboard surface).
  S2 css/style.css has .cmp-div-row-clickable:focus-visible with the
     hover row tint, in both themes.
  S3 the focus-visible tint matches the hover tint per theme (no drift
     between the two affordances).

Usage:
  scripts/check_cmp_div_row_focus.py
  scripts/check_cmp_div_row_focus.py --static-only

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

    # S1: divergence rows are keyboard-operable, not mouse-only divs.
    s1 = ("cmp-div-row-clickable" in js
          and "_kbdUpgradeRoving(divEl, '.cmp-div-row-clickable')" in js)
    check("S1 .cmp-div-row-clickable rows get the roving-tabindex keyboard surface",
          s1, "" if s1 else "divergence-row keyboard surface missing in js/app.js")

    # S2: focus-visible mirrors the hover tint, both themes.
    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    dark_focus = rule_bodies(".cmp-div-row-clickable:focus-visible")
    light_focus = rule_bodies('[data-theme="light"] .cmp-div-row-clickable:focus-visible')
    s2 = (any("rgba(255,255,255,0.06)" in b for b in dark_focus)
          and any("rgba(0,0,0,0.04)" in b for b in light_focus))
    check("S2 :focus-visible mirrors hover tint in both themes",
          s2, "" if s2 else "focus-visible divergence-row tint missing in css/style.css")

    # S3: focus tint == hover tint per theme.
    dark_hover = rule_bodies(".cmp-div-row-clickable:hover")
    light_hover = rule_bodies('[data-theme="light"] .cmp-div-row-clickable:hover')
    s3 = (any("rgba(255,255,255,0.06)" in b for b in dark_hover)
          and any("rgba(255,255,255,0.06)" in b for b in dark_focus)
          and any("rgba(0,0,0,0.04)" in b for b in light_hover)
          and any("rgba(0,0,0,0.04)" in b for b in light_focus))
    check("S3 focus tint matches hover tint per theme",
          s3, "" if s3 else "focus/hover divergence-row tint drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
