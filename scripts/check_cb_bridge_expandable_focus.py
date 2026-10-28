#!/usr/bin/env python3
"""Regression guard: community bridge expandable rows show hover affordance on keyboard focus.

The 2026-10-28 05:00 PT run (254th review) audited the keyboard
surfaces after the 249th run's queue was exhausted (trajectory,
tc-missing-link, peer-dist-col, reach-peer-ticker all closed) and
took the next uncovered one: the detail panel's community bridge
expandable rows (.cb-bridge-expandable, js/app.js:11283) are
keyboard-operable - _kbdUpgradeRoving() (js/app.js:11837) gives
them a roving tabindex and an Enter/Space path into the same
expand/collapse toggle as a mouse click (js/app.js:11805) - but
their hover affordance appeared only on :hover: a tinted
background (dark rgba(167,139,250,0.08), light
rgba(124,58,237,0.06)). Keyboard focus got only the generic
[data-kbd-upgraded]:focus-visible accent ring, so a keyboard user
tabbing onto a bridge row saw no tint signalling clickability.
css/style.css now mirrors the hover background onto
:focus-visible with exactly the hover values per theme.

Checks (all static):
  S1 js/app.js passes .cb-bridge-expandable to _kbdUpgradeRoving
     (keyboard surface).
  S2 css/style.css has a :focus-visible rule for the row carrying
     the tinted background, dark and light themes.
  S3 the focus-visible backgrounds match the hover backgrounds
     exactly per theme (no drift).

Usage:
  scripts/check_cb_bridge_expandable_focus.py
  scripts/check_cb_bridge_expandable_focus.py --static-only

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

    # S1: bridge expandable rows are keyboard-operable via the roving surface.
    kbd_lines = [ln for ln in js.splitlines() if "_kbdUpgradeRoving(detailRow," in ln]
    s1 = any("'.cb-bridge-expandable'" in ln for ln in kbd_lines)
    check("S1 bridge expandable rows get the roving-tabindex keyboard surface",
          s1, "" if s1 else "cb-bridge-expandable keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    dark_hover = rule_bodies(".cb-bridge-expandable:hover")
    dark_focus = rule_bodies(".cb-bridge-expandable:focus-visible")
    light_hover = rule_bodies('[data-theme="light"] .cb-bridge-expandable:hover')
    light_focus = rule_bodies('[data-theme="light"] .cb-bridge-expandable:focus-visible')

    # S2: focus-visible mirrors the hover tint in both themes.
    s2 = (any("rgba(167,139,250,0.08)" in b for b in dark_focus)
          and any("rgba(124,58,237,0.06)" in b for b in light_focus))
    check("S2 :focus-visible mirrors hover tint (dark + light)",
          s2, "" if s2 else "focus-visible cb-bridge-expandable tint missing in css/style.css")

    # S3: focus tint == hover tint per theme (no drift).
    s3 = (any("rgba(167,139,250,0.08)" in b for b in dark_hover)
          and any("rgba(167,139,250,0.08)" in b for b in dark_focus)
          and any("rgba(124,58,237,0.06)" in b for b in light_hover)
          and any("rgba(124,58,237,0.06)" in b for b in light_focus))
    check("S3 focus tints match hover tints per theme",
          s3, "" if s3 else "focus/hover cb-bridge-expandable tint drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
