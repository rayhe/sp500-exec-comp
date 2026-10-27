#!/usr/bin/env python3
"""Regression guard: aspirational-pay badge shows hover affordance on keyboard focus.

The 2026-10-27 15:30 PT run (247th review) re-ran the :hover vs
:focus-visible scan instead of assuming the hover/focus family was
closed (the 244th run found the governance badge and the 245th found
the equity badge after closure had been declared, and the 246th found
the concentration badge the same way). The last roving-set straggler:
the main table's aspirational-pay badge (.asp-tbl-badge-clickable,
js/app.js:7703) is keyboard-operable - _kbdUpgradeRoving()
(js/app.js:7780) gives it a roving tabindex and an Enter/Space path
into the same filter-by-aspirational-delta-tier action as a mouse
click - but its hover affordance appeared only on :hover: scale(1.08)
plus a ring shadow (dark rgba(255,255,255,0.15), light
rgba(0,0,0,0.12)). Keyboard focus got only the generic
[data-kbd-upgraded]:focus-visible accent ring. css/style.css now
mirrors each hover affordance onto :focus-visible with exactly the
hover values per theme. Light-theme parity is inherited, not
repeated: the light hover rule overrides only the shadow (scale
comes from the base hover rule), so the light focus rule likewise
overrides only the shadow (scale comes from the base focus rule).
The non-clickable .asp-tbl-badge spans (no -clickable suffix) have no
hover rule and are not in the roving set, so they are out of scope
here.

Checks (all static):
  S1 js/app.js passes .asp-tbl-badge-clickable to _kbdUpgradeRoving
     (keyboard surface).
  S2 css/style.css has a :focus-visible affordance for the badge,
     dark and light themes.
  S3 the focus-visible affordance matches the hover affordance
     exactly per theme (no drift between the two affordances).

Usage:
  scripts/check_asp_badge_focus.py
  scripts/check_asp_badge_focus.py --static-only

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

    # S1: aspirational-pay badge is keyboard-operable via the roving surface.
    roving_start = js.find("_kbdUpgradeRoving(tbody")
    s1 = (".asp-tbl-badge-clickable" in js
          and roving_start != -1
          and ".asp-tbl-badge-clickable" in js[roving_start:roving_start + 300])
    check("S1 aspirational-pay badge gets the roving-tabindex keyboard surface",
          s1, "" if s1 else "aspirational-pay badge keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    dark_focus = rule_bodies(".asp-tbl-badge-clickable:focus-visible")
    light_focus = rule_bodies('[data-theme="light"] .asp-tbl-badge-clickable:focus-visible')

    # S2: focus-visible mirrors the hover affordance, both themes.
    s2 = (any("scale(1.08)" in b and "rgba(255,255,255,0.15)" in b for b in dark_focus)
          and any("rgba(0,0,0,0.12)" in b for b in light_focus))
    check("S2 :focus-visible mirrors hover affordance (dark + light)",
          s2, "" if s2 else "focus-visible aspirational-pay badge affordance missing in css/style.css")

    # S3: focus affordance == hover affordance per theme (no drift).
    dark_hover = rule_bodies(".asp-tbl-badge-clickable:hover")
    light_hover = rule_bodies('[data-theme="light"] .asp-tbl-badge-clickable:hover')

    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    s3 = (has(dark_hover, "scale(1.08)", "rgba(255,255,255,0.15)")
          and has(dark_focus, "scale(1.08)", "rgba(255,255,255,0.15)")
          and has(light_hover, "rgba(0,0,0,0.12)")
          and has(light_focus, "rgba(0,0,0,0.12)")
          and has(dark_focus, "scale(1.08)"))
    check("S3 focus affordance matches hover affordance per theme",
          s3, "" if s3 else "focus/hover aspirational-pay badge affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
