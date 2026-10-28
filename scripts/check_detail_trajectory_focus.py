#!/usr/bin/env python3
"""Regression guard: detail pay-trajectory wrap shows hover affordance on keyboard focus.

The 2026-10-27 22:00 PT run (250th review) audited the non-roving
surfaces queued by the 249th run and took the first: the detail
panel's CEO pay-trajectory wrap (.detail-trajectory-clickable,
js/app.js:9026) is keyboard-operable - _kbdUpgradeRoving()
(js/app.js:11721) gives it a roving tabindex and an Enter/Space path
into the same navigateToPayAnomaly action as a mouse click - but its
hover affordances appeared only on :hover: a tinted background plus
a ring shadow (dark rgba(0,180,216,0.1) / 0 0 0 1px
rgba(0,180,216,0.3); light rgba(0,119,182,0.08) / 0 0 0 1px
rgba(0,119,182,0.25)), and the hover rule additionally reveals the
"-> Pay Anomaly" hint (.detail-trajectory-hint, display:none by
default). Keyboard focus got only the generic
[data-kbd-upgraded]:focus-visible accent ring, so a keyboard user
tabbing onto the trajectory saw neither the affordance nor the hint
explaining what activating it does. css/style.css now mirrors each
hover affordance onto :focus-visible with exactly the hover values
per theme, and reveals the hint on :focus-visible as well as :hover.

Checks (all static):
  S1 js/app.js passes .detail-trajectory-clickable to _kbdUpgradeRoving
     (keyboard surface).
  S2 css/style.css has a :focus-visible affordance for the wrap,
     dark and light themes, and a :focus-visible hint reveal.
  S3 the focus-visible affordance matches the hover affordance
     exactly per theme, and the hint reveal matches (no drift).

Usage:
  scripts/check_detail_trajectory_focus.py
  scripts/check_detail_trajectory_focus.py --static-only

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

    # S1: trajectory wrap is keyboard-operable via the roving surface.
    s1 = (".detail-trajectory-clickable" in js
          and "_kbdUpgradeRoving(detailRow, '.detail-trajectory-clickable" in js)
    check("S1 trajectory wrap gets the roving-tabindex keyboard surface",
          s1, "" if s1 else "trajectory wrap keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    dark_focus = rule_bodies(".detail-trajectory-clickable:focus-visible")
    light_focus = rule_bodies('[data-theme="light"] .detail-trajectory-clickable:focus-visible')
    hint_focus = rule_bodies(".detail-trajectory-clickable:focus-visible .detail-trajectory-hint")

    # S2: focus-visible mirrors the hover affordance, both themes, plus hint.
    s2 = (any("rgba(0, 180, 216, 0.1)" in b and "rgba(0, 180, 216, 0.3)" in b
              for b in dark_focus)
          and any("rgba(0, 119, 182, 0.08)" in b and "rgba(0, 119, 182, 0.25)" in b
                  for b in light_focus)
          and any("display: block" in b for b in hint_focus))
    check("S2 :focus-visible mirrors hover affordance (dark + light) and reveals hint",
          s2, "" if s2 else "focus-visible trajectory affordance or hint reveal missing in css/style.css")

    # S3: focus affordance == hover affordance per theme, hint reveal matches.
    dark_hover = rule_bodies(".detail-trajectory-clickable:hover")
    light_hover = rule_bodies('[data-theme="light"] .detail-trajectory-clickable:hover')
    hint_hover = rule_bodies(".detail-trajectory-clickable:hover .detail-trajectory-hint")

    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    s3 = (has(dark_hover, "rgba(0, 180, 216, 0.1)", "rgba(0, 180, 216, 0.3)")
          and has(dark_focus, "rgba(0, 180, 216, 0.1)", "rgba(0, 180, 216, 0.3)")
          and has(light_hover, "rgba(0, 119, 182, 0.08)", "rgba(0, 119, 182, 0.25)")
          and has(light_focus, "rgba(0, 119, 182, 0.08)", "rgba(0, 119, 182, 0.25)")
          and has(hint_hover, "display: block")
          and has(hint_focus, "display: block"))
    check("S3 focus affordance matches hover affordance per theme (incl. hint)",
          s3, "" if s3 else "focus/hover trajectory affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
