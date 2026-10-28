#!/usr/bin/env python3
"""Regression guard: scatter brush-result rows show hover affordance on keyboard focus.

The 2026-10-28 07:30 PT run (255th review) re-scanned every
_kbdUpgradeRoving() call site against the :hover / :focus-visible
rules in css/style.css (268 hover rules, 142 focus-visible rules).
The scatter brush-results rows (.sbr-row, js/charts.js:4855) were
the sole remaining roving surface with a hover affordance but no
focus-visible mirror: they are keyboard-operable -
_kbdUpgradeRoving() (js/app.js:52, exposed on window) gives them a
roving tabindex and an Enter/Space path into the same
findCompanyInTable action as a mouse click (js/charts.js:4828) -
but their hover affordance appeared only on :hover: a tinted
background (dark rgba(0,180,216,0.06), light
rgba(0,180,216,0.05)). Keyboard focus got only the generic
[data-kbd-upgraded]:focus-visible accent ring, so a keyboard user
tabbing onto a brush-result row saw no tint signalling
clickability. css/style.css now mirrors the hover background onto
:focus-visible with exactly the hover values per theme. (The
peer-pay-row case, which a naive substring scan flags, already has
:focus-visible rules qualified with :not(.peer-pay-self); it is not
a straggler.)

Checks (all static):
  S1 js/charts.js passes .sbr-row to _kbdUpgradeRoving
     (keyboard surface).
  S2 css/style.css has a :focus-visible rule for the row carrying
     the tinted background, dark and light themes.
  S3 the focus-visible backgrounds match the hover backgrounds
     exactly per theme (no drift).

Usage:
  scripts/check_sbr_row_focus.py
  scripts/check_sbr_row_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    js = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: brush-result rows are keyboard-operable via the roving surface.
    kbd_lines = [ln for ln in js.splitlines() if "_kbdUpgradeRoving(" in ln]
    s1 = any("'.sbr-row'" in ln for ln in kbd_lines)
    check("S1 brush-result rows get the roving-tabindex keyboard surface",
          s1, "" if s1 else "sbr-row keyboard surface missing in js/charts.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    dark_hover = rule_bodies(".sbr-row:hover")
    dark_focus = rule_bodies(".sbr-row:focus-visible")
    light_hover = rule_bodies('[data-theme="light"] .sbr-row:hover')
    light_focus = rule_bodies('[data-theme="light"] .sbr-row:focus-visible')

    # S2: focus-visible mirrors the hover tint in both themes.
    s2 = (any("rgba(0,180,216,0.06)" in b for b in dark_focus)
          and any("rgba(0,180,216,0.05)" in b for b in light_focus))
    check("S2 :focus-visible mirrors hover tint (dark + light)",
          s2, "" if s2 else "focus-visible sbr-row tint missing in css/style.css")

    # S3: focus tint == hover tint per theme (no drift).
    s3 = (any("rgba(0,180,216,0.06)" in b for b in dark_hover)
          and any("rgba(0,180,216,0.06)" in b for b in dark_focus)
          and any("rgba(0,180,216,0.05)" in b for b in light_hover)
          and any("rgba(0,180,216,0.05)" in b for b in light_focus))
    check("S3 focus tints match hover tints per theme",
          s3, "" if s3 else "focus/hover sbr-row tint drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
