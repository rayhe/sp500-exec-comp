#!/usr/bin/env python3
"""Regression guard: detail-panel nav and compare buttons show hover affordance on keyboard focus.

The 2026-10-27 19:30 PT run (249th review) closed the pair the 248th
run queued: the detail panel's prev/next buttons (.detail-nav-btn,
js/app.js:8945/9033) and its add-to-comparison button
(.detail-compare-btn, js/app.js:9036) are native <button> elements -
inherently keyboard-focusable, with aria-labels (nav) and aria-pressed
(compare) - but their hover affordances appeared only on :hover, in
both themes. Keyboard focus got only the generic focus ring.
css/style.css now mirrors each hover affordance onto
:focus-visible:not(:disabled) with exactly the hover values per theme:
nav dark var(--accent) background/border with white text, nav light
#0077b6 background/border with white text; compare dark
rgba(0,180,216,0.10) background with var(--accent) border/text,
compare light rgba(0,119,182,0.08) background with #0077b6
border/text. The :not(:disabled) qualifier matches the hover rules
exactly (disabled buttons are not focusable targets for the
affordance).

Checks (all static):
  S1 js/app.js renders .detail-nav-btn (prev + next) and
     .detail-compare-btn as native <button> elements with their
     accessible names (aria-label / aria-pressed).
  S2 css/style.css has a :focus-visible affordance for both buttons,
     dark and light themes.
  S3 the focus-visible affordance matches the hover affordance
     exactly per theme per button (no drift between the two
     affordances).

Usage:
  scripts/check_detail_nav_compare_btn_focus.py
  scripts/check_detail_nav_compare_btn_focus.py --static-only

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

    # S1: both buttons are native <button> elements with accessible names.
    s1_nav = ('<button class="detail-nav-btn detail-nav-prev"' in js
              and 'aria-label="Previous company"' in js
              and '<button class="detail-nav-btn detail-nav-next"' in js
              and 'aria-label="Next company"' in js)
    s1_cmp = ('<button class="detail-compare-btn' in js
              and 'aria-pressed="' in js)
    s1 = s1_nav and s1_cmp
    check("S1 detail nav + compare buttons are native buttons with accessible names",
          s1, "" if s1 else "detail nav/compare button keyboard surface missing in js/app.js")

    def rule_bodies(selector):
        return re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)

    def has(bodies, *needles):
        return any(all(n in b for n in needles) for b in bodies)

    # Per-button, per-theme expected affordance values (hover == focus).
    cases = [
        ("nav dark", ".detail-nav-btn", None,
         ("var(--accent)", "#fff")),
        ("nav light", ".detail-nav-btn", '[data-theme="light"] ',
         ("#0077b6", "#fff")),
        ("compare dark", ".detail-compare-btn", None,
         ("rgba(0,180,216,0.10)", "var(--accent)")),
        ("compare light", ".detail-compare-btn", '[data-theme="light"] ',
         ("rgba(0,119,182,0.08)", "#0077b6")),
    ]

    # S2: focus-visible affordance exists for both buttons, both themes.
    s2 = True
    for label, cls, prefix, needles in cases:
        focus_sel = (prefix or "") + cls + ":focus-visible:not(:disabled)"
        if not has(rule_bodies(focus_sel), *needles):
            s2 = False
    check("S2 :focus-visible mirrors hover affordance (nav + compare, dark + light)",
          s2, "" if s2 else "focus-visible detail nav/compare affordance missing in css/style.css")

    # S3: focus affordance == hover affordance per theme per button.
    s3 = True
    for label, cls, prefix, needles in cases:
        hover_sel = (prefix or "") + cls + ":hover:not(:disabled)"
        focus_sel = (prefix or "") + cls + ":focus-visible:not(:disabled)"
        if not (has(rule_bodies(hover_sel), *needles)
                and has(rule_bodies(focus_sel), *needles)):
            s3 = False
    check("S3 focus affordance matches hover affordance per theme per button",
          s3, "" if s3 else "focus/hover detail nav/compare affordance drift in css/style.css")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
