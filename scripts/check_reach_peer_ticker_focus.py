#!/usr/bin/env python3
"""Regression guard: reach peer tickers show hover affordance on keyboard focus.

The 2026-10-28 03:30 PT run (253rd review) audited the surfaces queued
by the 249th run and took the fourth: the detail panel's Reach Peer
Analysis tickers (.reach-peer-ticker, js/app.js:10482) are
keyboard-operable - _kbdUpgradeRoving() (js/app.js:11802) gives
[data-ticker] tickers a roving tabindex and an Enter/Space path into
the same click-to-find action as a mouse click (js/app.js:11786) -
but their hover affordances appeared only on :hover: the ticker
brightens to #00b4d8 and gains an underline (unscoped, so the same
in both themes). Keyboard focus got only the generic
[data-kbd-upgraded]:focus-visible accent ring, so a keyboard user
tabbing onto a ticker saw neither the color change nor the underline
signalling clickability. css/style.css now mirrors both hover
affordances onto :focus-visible with exactly the hover values.

Checks (all static):
  S1 js/app.js passes .reach-peer-ticker to _kbdUpgradeRoving
     (keyboard surface).
  S2 css/style.css has a :focus-visible rule for the ticker
     carrying the color + underline affordances.
  S3 the focus-visible affordances match the hover affordances
     exactly (no drift).

Usage:
  scripts/check_reach_peer_ticker_focus.py
  scripts/check_reach_peer_ticker_focus.py --static-only

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

    # S1: reach peer tickers are keyboard-operable via the roving surface.
    kbd_lines = [ln for ln in js.splitlines() if "_kbdUpgradeRoving(detailRow," in ln]
    s1 = any(".reach-peer-ticker[data-ticker]" in ln for ln in kbd_lines)
    check("S1 reach peer tickers get the roving-tabindex keyboard surface",
          s1, "" if s1 else "reach-peer-ticker keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    focus = rule_bodies(".reach-peer-ticker:focus-visible")
    hover = rule_bodies(".reach-peer-ticker:hover")

    # S2: focus-visible mirrors every hover affordance.
    s2 = (any("#00b4d8" in b for b in focus)
          and any("underline" in b for b in focus))
    check("S2 :focus-visible mirrors hover affordances (color + underline)",
          s2, "" if s2 else "focus-visible reach-peer-ticker affordance missing in css/style.css")

    # S3: focus affordance == hover affordance (unscoped, both themes).
    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    s3 = (has(hover, "#00b4d8", "underline")
          and has(focus, "#00b4d8", "underline"))
    check("S3 focus affordances match hover affordances",
          s3, "" if s3 else "focus/hover reach-peer-ticker affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
