#!/usr/bin/env python3
"""Regression guard: peer pay rows show hover tint on keyboard focus.

The 2026-10-27 06:00 PT run (242nd review) found the next straggler
after the 241st run closed the heatmap case: the detail panel's peer
pay rows (.peer-pay-row, js/app.js:11802) are keyboard-operable -
_kbdUpgradeRoving() gives them a roving tabindex and an Enter/Space
path into the same find-in-table action as a mouse click - but their
hover affordances appeared only on :hover: the row tint (dark
rgba(255,255,255,0.04) / light rgba(0,0,0,0.04)) and the bar opacity
lift (0.35 -> 0.6). Keyboard focus got only the generic
[data-kbd-upgraded]:focus-visible accent ring. css/style.css now
mirrors each hover affordance onto :focus-visible, with exactly the
hover values per theme. Self rows (.peer-pay-self) are unwired and
excluded from the roving selector, so they keep their hover-none
behaviour on focus too (parity with the roving selector).

Checks (all static):
  S1 js/app.js passes the peer pay rows to _kbdUpgradeRoving
     (keyboard surface, self rows excluded).
  S2 css/style.css has :focus-visible row tint and bar opacity lift,
     in both themes.
  S3 the focus-visible affordance matches the hover affordance per
     selector per theme (no drift between the two affordances).

Usage:
  scripts/check_peer_pay_row_focus.py
  scripts/check_peer_pay_row_focus.py --static-only

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

    # S1: peer pay rows are keyboard-operable, self rows excluded (parity).
    s1 = (".peer-pay-row[data-ticker]:not(.peer-pay-self)" in js
          and "_kbdUpgradeRoving(detailRow" in js)
    check("S1 peer pay rows get the roving-tabindex keyboard surface (self excluded)",
          s1, "" if s1 else "peer pay row keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    row_focus = rule_bodies(".peer-pay-row:not(.peer-pay-self):focus-visible")
    row_light_focus = rule_bodies('[data-theme="light"] .peer-pay-row:not(.peer-pay-self):focus-visible')
    bar_focus = rule_bodies(".peer-pay-row:not(.peer-pay-self):focus-visible .peer-pay-bar")

    # S2: focus-visible mirrors the hover tint and bar opacity lift, both themes.
    s2 = (any("rgba(255,255,255,0.04)" in b for b in row_focus)
          and any("rgba(0,0,0,0.04)" in b for b in row_light_focus)
          and any("opacity: 0.6" in b for b in bar_focus))
    check("S2 :focus-visible mirrors hover tint and bar opacity lift in both themes",
          s2, "" if s2 else "focus-visible peer pay affordance missing in css/style.css")

    # S3: focus affordance == hover affordance per selector per theme.
    row_hover = rule_bodies(".peer-pay-row:not(.peer-pay-self):hover")
    row_light_hover = rule_bodies('[data-theme="light"] .peer-pay-row:not(.peer-pay-self):hover')
    bar_hover = rule_bodies(".peer-pay-row:not(.peer-pay-self):hover .peer-pay-bar")

    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    s3 = (has(row_hover, "rgba(255,255,255,0.04)")
          and has(row_focus, "rgba(255,255,255,0.04)")
          and has(row_light_hover, "rgba(0,0,0,0.04)")
          and has(row_light_focus, "rgba(0,0,0,0.04)")
          and has(bar_hover, "opacity: 0.6")
          and has(bar_focus, "opacity: 0.6"))
    check("S3 focus affordance matches hover affordance per selector per theme",
          s3, "" if s3 else "focus/hover peer pay affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
