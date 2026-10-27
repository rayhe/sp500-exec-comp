#!/usr/bin/env python3
"""Regression guard: NEW CEO badge shows hover affordance on keyboard focus.

The 2026-10-27 07:30 PT run (243rd review) found the next straggler
after the 242nd run closed the peer pay rows: the main table's NEW CEO
badge (.new-ceo-badge-clickable, js/app.js:7614) is keyboard-operable -
_kbdUpgradeRoving() (js/app.js:7780) gives it a roving tabindex and an
Enter/Space path into the same filter-by-CEO-transition action as a
mouse click - but its hover affordances appeared only on :hover:
dark theme the orange tint plus scale-up plus shadow, light theme the
tint plus shadow with NO scale change. Keyboard focus got only the
generic [data-kbd-upgraded]:focus-visible accent ring. css/style.css
now mirrors each hover affordance onto :focus-visible, with exactly
the hover values per theme. The non-clickable .new-ceo-badge (detail
panel, js/app.js:17281) has no hover rule and is not in the roving
set, so it is out of scope here.

Checks (all static):
  S1 js/app.js passes .new-ceo-badge-clickable to _kbdUpgradeRoving
     (keyboard surface).
  S2 css/style.css has :focus-visible affordance mirroring hover,
     in both themes.
  S3 the focus-visible affordance matches the hover affordance per
     theme (no drift between the two affordances; light theme keeps
     its no-scale parity).

Usage:
  scripts/check_new_ceo_badge_focus.py
  scripts/check_new_ceo_badge_focus.py --static-only

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

    # S1: NEW CEO badge is keyboard-operable via the roving surface.
    s1 = (".new-ceo-badge-clickable" in js
          and "_kbdUpgradeRoving(tbody" in js
          and ".new-ceo-badge-clickable" in
          js[js.find("_kbdUpgradeRoving(tbody"):js.find("_kbdUpgradeRoving(tbody") + 300])
    check("S1 NEW CEO badge gets the roving-tabindex keyboard surface",
          s1, "" if s1 else "NEW CEO badge keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    badge_focus = rule_bodies(".new-ceo-badge-clickable:focus-visible")
    badge_light_focus = rule_bodies('[data-theme="light"] .new-ceo-badge-clickable:focus-visible')

    # S2: focus-visible mirrors the hover affordance, both themes.
    s2 = (any("rgba(251,146,60,0.35)" in b and "scale(1.12)" in b
              and "0 1px 6px rgba(251,146,60,0.3)" in b for b in badge_focus)
          and any("rgba(234,88,12,0.25)" in b
                  and "0 1px 6px rgba(234,88,12,0.2)" in b for b in badge_light_focus))
    check("S2 :focus-visible mirrors hover affordance in both themes",
          s2, "" if s2 else "focus-visible NEW CEO badge affordance missing in css/style.css")

    # S3: focus affordance == hover affordance per theme (no drift).
    badge_hover = rule_bodies(".new-ceo-badge-clickable:hover")
    badge_light_hover = rule_bodies('[data-theme="light"] .new-ceo-badge-clickable:hover')

    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    s3 = (has(badge_hover, "rgba(251,146,60,0.35)", "scale(1.12)",
               "0 1px 6px rgba(251,146,60,0.3)")
          and has(badge_focus, "rgba(251,146,60,0.35)", "scale(1.12)",
                  "0 1px 6px rgba(251,146,60,0.3)")
          and has(badge_light_hover, "rgba(234,88,12,0.25)",
                  "0 1px 6px rgba(234,88,12,0.2)")
          and has(badge_light_focus, "rgba(234,88,12,0.25)",
                  "0 1px 6px rgba(234,88,12,0.2)")
          # Light theme parity: neither hover nor focus scales the badge.
          and not any("scale(" in b for b in badge_light_hover)
          and not any("scale(" in b for b in badge_light_focus))
    check("S3 focus affordance matches hover affordance per theme",
          s3, "" if s3 else "focus/hover NEW CEO badge affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
