#!/usr/bin/env python3
"""Regression guard: PvP coverage badge shows hover affordance on keyboard focus.

The 2026-10-28 14:00 PT run (258th review) continued the keyboard-operable
surface audit past the _kbdUpgradeRoving() call sites (all 17 roving surfaces
verified closed by the 251st-255th fixes) into the remaining inline pilot
surfaces. The PvP coverage badge (.pvp-cov-badge, js/app.js:7626) is one:
it is rendered with role="button" tabindex="0" and an inline
onkeydown handler for Enter/Space that calls the same window.openPvpDetail
action as its onclick. Its hover affordance - a deepened cyan background
(rgba(0,180,216,0.3) over the rgba(0,180,216,0.15) base, dark theme) -
appeared only on :hover. Keyboard focus got only the generic accent
outline ring (css/style.css, 2026-10-09 pilot block), so a keyboard user
tabbing onto the badge saw no tint signalling clickability.
css/style.css now mirrors the hover background onto :focus-visible with
exactly the hover value. (There is no light-theme-specific hover rule for
this badge - [data-theme="light"] .pvp-cov-badge's base background
outranks both :hover and :focus-visible in light theme - so the single
mirror is the exact hover parity, no drift.)

Checks (all static):
  S1 js/app.js renders .pvp-cov-badge with role="button" tabindex="0"
     and wires Enter/Space keydown to the same openPvpDetail action as
     the click (keyboard surface).
  S2 css/style.css has a :focus-visible rule for the badge carrying the
     deepened background.
  S3 the focus-visible background matches the hover background exactly
     (no drift).

Usage:
  scripts/check_pvp_cov_badge_focus.py
  scripts/check_pvp_cov_badge_focus.py --static-only

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

    # S1: the badge is a keyboard-operable surface (role + tabindex + keydown).
    s1 = ("pvp-cov-badge" in js
          and 'role="button" tabindex="0"' in js
          and "onkeydown=" in js
          and "openPvpDetail" in js
          and "event.key===\\'Enter\\'" in js
          and "event.key===\\' \\'" in js)
    check("S1 pvp-cov-badge is keyboard-operable (role/tabindex + Enter/Space)",
          s1, "" if s1 else "pvp-cov-badge keyboard surface missing in js/app.js")

    # S2: :focus-visible carries the deepened hover background.
    m_focus = re.search(
        r'\.pvp-cov-badge:focus-visible\s*\{\s*background\s*:\s*([^;]+);', css)
    check("S2 :focus-visible rule deepens the badge background",
          bool(m_focus),
          "" if m_focus else ".pvp-cov-badge:focus-visible missing in css/style.css")

    # S3: focus-visible background == hover background (no drift).
    m_hover = re.search(
        r'\.pvp-cov-badge:hover\s*\{\s*background\s*:\s*([^;]+);', css)
    if m_hover and m_focus:
        hover_bg = m_hover.group(1).strip()
        focus_bg = m_focus.group(1).strip()
        check("S3 focus-visible background matches hover exactly",
              hover_bg == focus_bg,
              "hover=%r focus=%r" % (hover_bg, focus_bg) if hover_bg != focus_bg else "")
    else:
        check("S3 focus-visible background matches hover exactly",
              False, "could not extract both rules")


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
