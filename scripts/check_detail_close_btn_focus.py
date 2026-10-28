#!/usr/bin/env python3
"""Regression guard: detail-panel close button shows hover affordance on keyboard focus.

The 2026-10-27 18:00 PT run (248th review) re-ran the :hover vs
:focus-visible scan instead of assuming the hover/focus family was
closed (the 244th-247th runs each found another straggler after
closure had been declared). The next straggler: the detail panel's
close button (.detail-close-btn, js/app.js:9040) is a native
<button> - inherently keyboard-focusable, with an aria-label and an
Esc path - but its hover affordance appeared only on :hover: dark
theme background/border var(--negative) with white text, light theme
background/border #ef476f with white text. Keyboard focus got only
the generic focus ring. css/style.css now mirrors each hover
affordance onto :focus-visible with exactly the hover values per
theme. The sibling .detail-nav-btn and .detail-compare-btn buttons
still lack :focus-visible mirrors and are the next candidates, not
in scope here.

Checks (all static):
  S1 js/app.js renders .detail-close-btn as a native <button> with
     an aria-label (keyboard surface).
  S2 css/style.css has a :focus-visible affordance for the button,
     dark and light themes.
  S3 the focus-visible affordance matches the hover affordance
     exactly per theme (no drift between the two affordances).

Usage:
  scripts/check_detail_close_btn_focus.py
  scripts/check_detail_close_btn_focus.py --static-only

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

    # S1: detail close button is a native <button> with an aria-label.
    s1 = ('<button class="detail-close-btn"' in js
          and 'aria-label="Close detail panel"' in js)
    check("S1 detail close button is a native button with aria-label",
          s1, "" if s1 else "detail close button keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    dark_focus = rule_bodies(".detail-close-btn:focus-visible")
    light_focus = rule_bodies('[data-theme="light"] .detail-close-btn:focus-visible')

    # S2: focus-visible mirrors the hover affordance, both themes.
    s2 = (any("var(--negative)" in b and "#fff" in b for b in dark_focus)
          and any("#ef476f" in b and "#fff" in b for b in light_focus))
    check("S2 :focus-visible mirrors hover affordance (dark + light)",
          s2, "" if s2 else "focus-visible detail close button affordance missing in css/style.css")

    # S3: focus affordance == hover affordance per theme (no drift).
    dark_hover = rule_bodies(".detail-close-btn:hover")
    light_hover = rule_bodies('[data-theme="light"] .detail-close-btn:hover')

    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    s3 = (has(dark_hover, "var(--negative)", "#fff")
          and has(dark_focus, "var(--negative)", "#fff")
          and has(light_hover, "#ef476f", "#fff")
          and has(light_focus, "#ef476f", "#fff"))
    check("S3 focus affordance matches hover affordance per theme",
          s3, "" if s3 else "focus/hover detail close button affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
