#!/usr/bin/env python3
"""Regression guard: peer distribution histogram columns show hover affordance on keyboard focus.

The 2026-10-28 02:00 PT run (252nd review) audited the surfaces queued
by the 249th run and took the third: the detail panel's peer
distribution histogram columns (.peer-dist-col,
js/app.js:10583) are keyboard-operable - _kbdUpgradeRoving()
(js/app.js:11802) gives non-empty-ticker columns a roving tabindex
and an Enter/Space path into the same click-to-filter action as a
mouse click (js/app.js:11751) - but their hover affordances appeared
only on :hover: the bar brightens (dark #475569, light #64748b),
the self-bucket bar shifts to #0096c7 (unscoped, both themes), and
a column with tickers lifts with transform scaleY(1.08). Keyboard
focus got only the generic [data-kbd-upgraded]:focus-visible accent
ring, so a keyboard user tabbing onto a column saw neither the bar
brightening nor the lift signalling clickability.
css/style.css now mirrors each hover affordance onto :focus-visible
with exactly the hover values per theme.

Checks (all static):
  S1 js/app.js passes .peer-dist-col to _kbdUpgradeRoving
     (keyboard surface).
  S2 css/style.css has :focus-visible affordances for the column:
     bar brightening dark + light, self-bucket shift, column lift.
  S3 the focus-visible affordances match the hover affordances
     exactly per theme (no drift).

Usage:
  scripts/check_peer_dist_col_focus.py
  scripts/check_peer_dist_col_focus.py --static-only

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

    # S1: histogram columns are keyboard-operable via the roving surface.
    kbd_lines = [ln for ln in js.splitlines() if "_kbdUpgradeRoving(detailRow," in ln]
    s1 = any(".peer-dist-col" in ln for ln in kbd_lines)
    check("S1 peer-dist columns get the roving-tabindex keyboard surface",
          s1, "" if s1 else "peer-dist-col keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    dark_focus = rule_bodies(".peer-dist-col:focus-visible .peer-dist-bar")
    light_focus = rule_bodies('[data-theme="light"] .peer-dist-col:focus-visible .peer-dist-bar')
    self_focus = rule_bodies(".peer-dist-self-bucket:focus-visible .peer-dist-bar")
    lift_focus = rule_bodies(".peer-dist-col[data-peer-tickers]:focus-visible")

    # S2: focus-visible mirrors every hover affordance.
    s2 = (any("#475569" in b for b in dark_focus)
          and any("#64748b" in b for b in light_focus)
          and any("#0096c7" in b for b in self_focus)
          and any("scaleY(1.08)" in b for b in lift_focus))
    check("S2 :focus-visible mirrors hover affordances (bar dark+light, self-bucket, lift)",
          s2, "" if s2 else "focus-visible peer-dist-col affordance missing in css/style.css")

    # S3: focus affordance == hover affordance per theme.
    dark_hover = rule_bodies(".peer-dist-col:hover .peer-dist-bar")
    light_hover = rule_bodies('[data-theme="light"] .peer-dist-col:hover .peer-dist-bar')
    self_hover = rule_bodies(".peer-dist-self-bucket:hover .peer-dist-bar")
    lift_hover = rule_bodies(".peer-dist-col[data-peer-tickers]:hover")

    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    s3 = (has(dark_hover, "#475569")
          and has(dark_focus, "#475569")
          and has(light_hover, "#64748b")
          and has(light_focus, "#64748b")
          and has(self_hover, "#0096c7")
          and has(self_focus, "#0096c7")
          and has(lift_hover, "scaleY(1.08)")
          and has(lift_focus, "scaleY(1.08)"))
    check("S3 focus affordances match hover affordances per theme",
          s3, "" if s3 else "focus/hover peer-dist-col affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
