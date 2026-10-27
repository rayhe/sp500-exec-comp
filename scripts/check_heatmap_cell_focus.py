#!/usr/bin/env python3
"""Regression guard: heatmap cells show hover lift on keyboard focus.

The 2026-10-27 03:30 PT run (241st review) found the next straggler
after the 240th run closed the radar-label case: the sector x component
heatmap (.hm-cell / .hm-sector-label, js/app.js:15177) and the role x
sector heatmap (.rs-cell / .rs-sector-label, js/app.js:15279) are
keyboard-operable - _kbdUpgradeRoving() gives both grids a roving
tabindex and an Enter/Space path into the same filter action as a
mouse click - but their hover affordances appeared only on :hover:
cells lift (scale 1.08 + shadow + z-index) and sector labels tint.
Keyboard focus got only the generic [data-kbd-upgraded]:focus-visible
accent ring. css/style.css now mirrors each hover affordance onto
:focus-visible, with exactly the hover values per theme (hm-cell lift
is theme-independent; rs-cell light shadow is the softer 0.12-alpha
value; sector-label tints differ per theme). Zero/empty cells keep
their hover-none behaviour on focus too.

Checks (all static):
  S1 js/app.js passes both heatmap grids to _kbdUpgradeRoving
     (keyboard surface).
  S2 css/style.css has :focus-visible lift for .hm-cell and .rs-cell
     plus :focus-visible tints for both sector labels, in both themes.
  S3 the focus-visible affordance matches the hover affordance per
     selector per theme (no drift between the two affordances).

Usage:
  scripts/check_heatmap_cell_focus.py
  scripts/check_heatmap_cell_focus.py --static-only

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

    # S1: both heatmap grids are keyboard-operable, not mouse-only grids.
    s1 = ("_kbdUpgradeRoving(container, '.hm-sector-label, .hm-cell:not(.hm-zero)')" in js
          and "_kbdUpgradeRoving(container, '.rs-sector-label, .rs-cell:not(.rs-cell-empty)')" in js)
    check("S1 both heatmap grids get the roving-tabindex keyboard surface",
          s1, "" if s1 else "heatmap keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    hm_focus = rule_bodies(".hm-cell:focus-visible")
    rs_focus = rule_bodies(".rs-cell:focus-visible")
    rs_light_focus = rule_bodies('[data-theme="light"] .rs-cell:focus-visible')
    hm_label_focus = rule_bodies(".sector-comp-heatmap td.hm-sector-label:focus-visible")
    hm_label_light_focus = rule_bodies('[data-theme="light"] .sector-comp-heatmap td.hm-sector-label:focus-visible')
    rs_label_focus = rule_bodies(".rs-sector-label:focus-visible")
    rs_label_light_focus = rule_bodies('[data-theme="light"] .rs-sector-label:focus-visible')

    # S2: focus-visible mirrors the hover lift and label tints, both themes.
    s2 = (any("scale(1.08)" in b and "0 2px 8px rgba(0,0,0,0.25)" in b for b in hm_focus)
          and any("scale(1.08)" in b and "0 4px 16px rgba(0,0,0,0.3)" in b for b in rs_focus)
          and any("0 4px 16px rgba(0,0,0,0.12)" in b for b in rs_light_focus)
          and any("rgba(0,180,216,0.08)" in b for b in hm_label_focus)
          and any("rgba(0,180,216,0.06)" in b for b in hm_label_light_focus)
          and any("rgba(255,255,255,0.06)" in b for b in rs_label_focus)
          and any("rgba(0,0,0,0.04)" in b for b in rs_label_light_focus))
    check("S2 :focus-visible mirrors hover lift and label tints in both themes",
          s2, "" if s2 else "focus-visible heatmap affordance missing in css/style.css")

    # S3: focus affordance == hover affordance per selector per theme.
    hm_hover = rule_bodies(".hm-cell:hover")
    rs_hover = rule_bodies(".rs-cell:hover")
    rs_light_hover = rule_bodies('[data-theme="light"] .rs-cell:hover')
    hm_label_hover = rule_bodies(".sector-comp-heatmap td.hm-sector-label:hover")
    hm_label_light_hover = rule_bodies('[data-theme="light"] .sector-comp-heatmap td.hm-sector-label:hover')
    rs_label_hover = rule_bodies(".rs-sector-label:hover")
    rs_label_light_hover = rule_bodies('[data-theme="light"] .rs-sector-label:hover')

    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    s3 = (has(hm_hover, "scale(1.08)", "0 2px 8px rgba(0,0,0,0.25)")
          and has(hm_focus, "scale(1.08)", "0 2px 8px rgba(0,0,0,0.25)")
          and has(rs_hover, "scale(1.08)", "0 4px 16px rgba(0,0,0,0.3)")
          and has(rs_focus, "scale(1.08)", "0 4px 16px rgba(0,0,0,0.3)")
          and has(rs_light_hover, "0 4px 16px rgba(0,0,0,0.12)")
          and has(rs_light_focus, "0 4px 16px rgba(0,0,0,0.12)")
          and has(hm_label_hover, "rgba(0,180,216,0.08)")
          and has(hm_label_focus, "rgba(0,180,216,0.08)")
          and has(hm_label_light_hover, "rgba(0,180,216,0.06)")
          and has(hm_label_light_focus, "rgba(0,180,216,0.06)")
          and has(rs_label_hover, "rgba(255,255,255,0.06)")
          and has(rs_label_focus, "rgba(255,255,255,0.06)")
          and has(rs_label_light_hover, "rgba(0,0,0,0.04)")
          and has(rs_label_light_focus, "rgba(0,0,0,0.04)"))
    check("S3 focus affordance matches hover affordance per selector per theme",
          s3, "" if s3 else "focus/hover heatmap affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
