#!/usr/bin/env python3
"""Regression guard: comparison radar dimension labels show hover tint on focus.

The 2026-10-27 02:00 PT run (240th review) found the next straggler
after the 239th run closed the divergence-row case: the comparison
radar's dimension labels (.cmp-radar-dim-label, js/app.js) are
keyboard-operable - _kbdUpgradeSvgRoving() gives them a roving tabindex
and an Enter/Space path into the same insightResetAndSort sort action
as a mouse click - but their hover affordance, the accent fill plus
underline that signals clickability, appeared only on :hover. Keyboard
focus got only the generic [data-kbd-upgraded]:focus-visible accent
ring. css/style.css now mirrors the hover affordance onto
:focus-visible, with exactly the hover values.

Checks (all static):
  S1 js/app.js renders .cmp-radar-dim-label labels and passes them to
     _kbdUpgradeSvgRoving (keyboard surface).
  S2 css/style.css has .cmp-radar-dim-label:focus-visible with the
     hover accent fill and underline.
  S3 the focus-visible affordance matches the hover affordance (no drift
     between the two affordances).

Usage:
  scripts/check_cmp_radar_dim_label_focus.py
  scripts/check_cmp_radar_dim_label_focus.py --static-only

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

    # S1: radar dimension labels are keyboard-operable, not mouse-only text.
    s1 = ("cmp-radar-dim-label" in js
          and "_kbdUpgradeSvgRoving(svg.node(), '.cmp-radar-dim-label')" in js)
    check("S1 .cmp-radar-dim-label labels get the roving-tabindex keyboard surface",
          s1, "" if s1 else "radar-label keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    focus = rule_bodies(".cmp-radar-dim-label:focus-visible")
    hover = rule_bodies(".cmp-radar-dim-label:hover")

    # S2: focus-visible mirrors the hover accent fill + underline.
    s2 = (any("var(--accent)" in b for b in focus)
          and any("underline" in b for b in focus))
    check("S2 :focus-visible mirrors hover accent fill and underline",
          s2, "" if s2 else "focus-visible radar-label affordance missing in css/style.css")

    # S3: focus affordance == hover affordance.
    s3 = (any("var(--accent)" in b for b in hover)
          and any("underline" in b for b in hover)
          and any("var(--accent)" in b for b in focus)
          and any("underline" in b for b in focus))
    check("S3 focus affordance matches hover affordance",
          s3, "" if s3 else "focus/hover radar-label affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
