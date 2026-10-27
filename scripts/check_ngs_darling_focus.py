#!/usr/bin/env python3
"""Regression guard: Benchmark Darling rows show hover affordance on focus.

The 2026-10-26 22:00 PT run (238th review) finished the hover-only
reveal audit that the 223rd/225th/229th/233rd/234th/235th runs ran over
the card CTAs, the NEO filing link, and the NEO audit note. The last
straggler was .ngs-ddp-darling in the network panel: a role=button,
tabindex=0 row (js/network.js wires Enter/Space to focusNetworkNode),
so fully keyboard-operable, but its hover affordance - row tint plus
the ticker turning accent + underline, the signal that the row is
clickable and which ticker it names - appeared only on :hover. The
:focus-visible rule carried only the outline ring. css/style.css now
mirrors the hover affordance onto :focus-visible, in both themes:
dark uses the rgba(255,255,255,0.06) tint + #00b4d8 ticker, light uses
the rgba(0,0,0,0.05) tint + #0077b6 ticker.

Checks (all static):
  S1 js/network.js renders .ngs-ddp-darling as role=button tabindex=0
     with an Enter/Space keydown path (keyboard surface).
  S2 css/style.css has .ngs-ddp-darling:focus-visible with the hover
     row tint, and .ngs-ddp-darling:focus-visible .ngs-ddp-darling-
     ticker with the accent color + underline, in both themes.
  S3 the focus-visible ticker color matches the hover ticker color
     per theme (no drift between the two affordances).

Usage:
  scripts/check_ngs_darling_focus.py
  scripts/check_ngs_darling_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET_JS = os.path.join(REPO, "js", "network.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    js = open(NET_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: darling rows are keyboard-operable buttons, not mouse-only divs.
    s1 = ('class="ngs-ddp-darling" role="button" tabindex="0"' in js
          and "ngs-ddp-darling" in js and "Enter" in js)
    check("S1 .ngs-ddp-darling is a keyboard-operable button (role + tabindex + Enter path)",
          s1, "" if s1 else "darling row keyboard surface missing in js/network.js")

    # S2: focus-visible mirrors the hover affordance, both themes.
    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    dark_row = rule_bodies(".ngs-ddp-darling:focus-visible")
    dark_tick = rule_bodies(".ngs-ddp-darling:focus-visible .ngs-ddp-darling-ticker")
    light_row = rule_bodies('[data-theme="light"] .ngs-ddp-darling:focus-visible')
    light_tick = rule_bodies('[data-theme="light"] .ngs-ddp-darling:focus-visible .ngs-ddp-darling-ticker')
    s2 = (any("rgba(255,255,255,0.06)" in b for b in dark_row)
          and any("#00b4d8" in b and "underline" in b for b in dark_tick)
          and any("rgba(0,0,0,0.05)" in b for b in light_row)
          and any("#0077b6" in b and "underline" in b for b in light_tick))
    check("S2 :focus-visible mirrors hover tint + ticker accent/underline in both themes",
          s2, "" if s2 else "focus-visible darling affordance missing in css/style.css")

    # S3: focus ticker color == hover ticker color per theme.
    hover_dark = rule_bodies(".ngs-ddp-darling:hover .ngs-ddp-darling-ticker")
    hover_light = rule_bodies('[data-theme="light"] .ngs-ddp-darling:hover .ngs-ddp-darling-ticker')
    s3 = (any("#00b4d8" in b for b in hover_dark)
          and any("#00b4d8" in b for b in dark_tick)
          and any("#0077b6" in b for b in hover_light)
          and any("#0077b6" in b for b in light_tick))
    check("S3 focus ticker color matches hover ticker color per theme",
          s3, "" if s3 else "focus/hover ticker color drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
