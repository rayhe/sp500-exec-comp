#!/usr/bin/env python3
"""Regression guard: team-completeness missing-roles link shows hover affordance on keyboard focus.

The 2026-10-27 23:30 PT run (251st review) audited the surfaces queued
by the 249th run and took the second: the detail panel's
team-completeness missing-roles link (.tc-missing-link,
js/app.js:9469) is keyboard-operable - _kbdUpgradeRoving()
(js/app.js:11721) gives it a roving tabindex and an Enter/Space path
into the same filterByTeamCompleteness('missing') action as a mouse
click - but its hover affordances appeared only on :hover: dark theme
color #fb7185 with a solid underline (base: #f472b6, dotted), light
theme color #be185d (base: #db2777, dotted underline unchanged).
Keyboard focus got only the generic [data-kbd-upgraded]:focus-visible
accent ring, so a keyboard user tabbing onto the link saw neither the
color change nor the solid underline signalling clickability.
css/style.css now mirrors each hover affordance onto :focus-visible
with exactly the hover values per theme.

Checks (all static):
  S1 js/app.js passes .tc-missing-link to _kbdUpgradeRoving
     (keyboard surface).
  S2 css/style.css has a :focus-visible affordance for the link,
     dark and light themes.
  S3 the focus-visible affordance matches the hover affordance
     exactly per theme (no drift).

Usage:
  scripts/check_tc_missing_link_focus.py
  scripts/check_tc_missing_link_focus.py --static-only

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

    # S1: missing-roles link is keyboard-operable via the roving surface.
    kbd_lines = [ln for ln in js.splitlines() if "_kbdUpgradeRoving(detailRow," in ln]
    s1 = any(".tc-missing-link" in ln for ln in kbd_lines)
    check("S1 missing-roles link gets the roving-tabindex keyboard surface",
          s1, "" if s1 else "tc-missing-link keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    dark_focus = rule_bodies(".tc-missing-link:focus-visible")
    light_focus = rule_bodies(':root[data-theme="light"] .tc-missing-link:focus-visible')

    # S2: focus-visible mirrors the hover affordance, both themes.
    s2 = (any("#fb7185" in b and "solid" in b for b in dark_focus)
          and any("#be185d" in b for b in light_focus))
    check("S2 :focus-visible mirrors hover affordance (dark + light)",
          s2, "" if s2 else "focus-visible tc-missing-link affordance missing in css/style.css")

    # S3: focus affordance == hover affordance per theme.
    dark_hover = rule_bodies(".tc-missing-link:hover")
    light_hover = rule_bodies(':root[data-theme="light"] .tc-missing-link:hover')

    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    s3 = (has(dark_hover, "#fb7185", "solid")
          and has(dark_focus, "#fb7185", "solid")
          and has(light_hover, "#be185d")
          and has(light_focus, "#be185d")
          # Light hover does not change underline style, so neither may focus.
          and not any("text-decoration-style" in b for b in light_focus))
    check("S3 focus affordance matches hover affordance per theme",
          s3, "" if s3 else "focus/hover tc-missing-link affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
