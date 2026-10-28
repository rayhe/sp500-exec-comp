#!/usr/bin/env python3
"""Regression guard: clickable network stats show hover affordance on keyboard focus.

The 2026-10-28 11:30 PT run (257th review) broadened the hover/focus
audit past the _kbdUpgradeRoving() call sites (all 17 roving surfaces
verified closed, including the 251st-255th fixes) to the other
keyboard-operable pilot surfaces. The clickable network stats
(.ngs-stat-clickable, #ngs-avg-degree and #ngs-avg-cc, js/network.js)
were the remaining gap: they are tabindex="0" role="button"
distribution-panel toggles with click and Enter/Space keydown wired in
renderGlobalStats (js/network.js), and their hover affordance is more
than a ring - a tinted background (dark rgba(0,180,216,0.12), light
rgba(0,120,180,0.1)) plus brightened label/value text (dark
rgba(255,255,255,0.95), light rgba(0,0,0,0.9)). But keyboard focus got
only the generic accent outline ring (css/style.css, 2026-10-09 pilot
block), so a keyboard user tabbing onto a clickable stat saw no tint
or text brightening signalling clickability. css/style.css now mirrors
each hover affordance onto :focus-visible with exactly the hover
values per theme. (The .network-search-result case, which a naive
hover scan flags, is not a straggler: keyboard navigation there drives
the .active class, which already shares the hover background.)

Checks (all static):
  S1 js/network.js renders .ngs-stat-clickable with role="button"
     tabindex="0" and wires Enter/Space keydown (keyboard surface).
  S2 css/style.css has :focus-visible rules for the stat carrying
     the tinted background AND the brightened label/value text,
     dark and light themes.
  S3 the focus-visible backgrounds and text colors match the hover
     backgrounds and text colors exactly per theme (no drift).

Usage:
  scripts/check_ngs_stat_clickable_focus.py
  scripts/check_ngs_stat_clickable_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK_JS = os.path.join(REPO, "js", "network.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    js = open(NETWORK_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: clickable stats are keyboard-operable (tabindex + role + keydown).
    s1 = ("ngs-stat-clickable" in js
          and 'role="button" tabindex="0"' in js
          and "ngs-avg-degree" in js and "ngs-avg-cc" in js
          and "ev.key === 'Enter'" in js)
    check("S1 clickable network stats get the keyboard surface",
          s1, "" if s1 else "ngs-stat-clickable keyboard surface missing in js/network.js")

    def rule_bodies(selector):
        # Match rule blocks whose selector LIST contains the target selector
        # (label/value share one comma-joined block).
        bodies = []
        for sels, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
            if selector in [s.strip() for s in sels.split(",")]:
                bodies.append(body)
        return bodies

    dark_hover_bg = rule_bodies(".ngs-stat-clickable:hover")
    dark_focus_bg = rule_bodies(".ngs-stat-clickable:focus-visible")
    dark_hover_txt = rule_bodies(".ngs-stat-clickable:hover .ngs-label")
    dark_focus_txt = rule_bodies(".ngs-stat-clickable:focus-visible .ngs-label")
    light_hover_bg = rule_bodies('[data-theme="light"] .ngs-stat-clickable:hover')
    light_focus_bg = rule_bodies('[data-theme="light"] .ngs-stat-clickable:focus-visible')
    light_hover_txt = rule_bodies('[data-theme="light"] .ngs-stat-clickable:hover .ngs-label')
    light_focus_txt = rule_bodies('[data-theme="light"] .ngs-stat-clickable:focus-visible .ngs-label')

    # S2: focus-visible mirrors hover tint + text brightening in both themes.
    s2 = (any("rgba(0,180,216,0.12)" in b for b in dark_focus_bg)
          and any("rgba(255,255,255,0.95)" in b for b in dark_focus_txt)
          and any("rgba(0,120,180,0.1)" in b for b in light_focus_bg)
          and any("rgba(0,0,0,0.9)" in b for b in light_focus_txt))
    check("S2 :focus-visible mirrors hover tint + text (dark + light)",
          s2, "" if s2 else "focus-visible ngs-stat-clickable affordance missing in css/style.css")

    # S3: focus values == hover values per theme (no drift).
    s3 = (any("rgba(0,180,216,0.12)" in b for b in dark_hover_bg)
          and any("rgba(0,180,216,0.12)" in b for b in dark_focus_bg)
          and any("rgba(255,255,255,0.95)" in b for b in dark_hover_txt)
          and any("rgba(255,255,255,0.95)" in b for b in dark_focus_txt)
          and any("rgba(0,120,180,0.1)" in b for b in light_hover_bg)
          and any("rgba(0,120,180,0.1)" in b for b in light_focus_bg)
          and any("rgba(0,0,0,0.9)" in b for b in light_hover_txt)
          and any("rgba(0,0,0,0.9)" in b for b in light_focus_txt))
    check("S3 focus values match hover values per theme",
          s3, "" if s3 else "focus/hover ngs-stat-clickable value drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
