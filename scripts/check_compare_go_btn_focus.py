#!/usr/bin/env python3
"""Regression guard: compare-tray primary "Compare" button shows hover affordance on keyboard focus.

The 2026-10-28 18:00 PT run (260th review) re-scanned all 162 :hover classes
in css/style.css for keyboard-operability (native <button>/<a href>/<input>/
<select> renders, tabindex windows, classList.add near keydown) against
:focus-visible mirrors. The 259th review's scan claimed only .cm-export-btn
remained, but a stricter keyboard-surface triage found the real remaining
gaps; this review fixes the highest-value one: .compare-go-btn, the compare
tray's primary "Compare" action (index.html:1049, native <button>, click
handler at js/app.js:17408 -> keyboard-operable via Tab + Enter/Space), whose
hover affordance (background: var(--accent-hover)) had no focus-visible
mirror - keyboard focus got only the UA default outline. css/style.css now
mirrors exactly the hover value onto :focus-visible; --accent-hover is
theme-aware (#0096c7 dark / #005f96 light), so one rule covers both themes.

Checks (all static):
  S1 index.html renders .compare-go-btn as a native <button> and js/app.js
     wires a click listener (keyboard surface).
  S2 css/style.css has a .compare-go-btn:focus-visible rule carrying
     background.
  S3 the focus-visible background matches the hover background exactly
     (no drift).

Usage:
  scripts/check_compare_go_btn_focus.py
  scripts/check_compare_go_btn_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "index.html")
APP_JS = os.path.join(REPO, "js", "app.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print((("PASS" if ok else "FAIL") + ": " + name
           + ((" - " + detail) if detail else "")))


def extract_background(css, pattern):
    m = re.search(pattern, css)
    if not m:
        return None
    pm = re.search(r"background\s*:\s*([^;]+);", m.group(1))
    return pm.group(1).strip() if pm else None


def static_checks():
    html = open(HTML, encoding="utf-8").read()
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> with a click listener (keyboard-operable surface).
    s1 = ('<button class="compare-go-btn"' in html
          and "getElementById('compare-go-btn')" in js
          and "addEventListener('click'" in js)
    check("S1 compare-go-btn is a native <button> with click wiring",
          s1, "" if s1 else "button render or click wiring missing in index.html/js/app.js")

    # S2: :focus-visible rule carries background.
    focus_bg = extract_background(
        css, r"\.compare-go-btn:focus-visible\s*\{([^}]*)\}")
    s2 = focus_bg is not None
    check("S2 :focus-visible rule carries background",
          s2, "" if s2 else "focus-visible rule missing in css/style.css")

    # S3: focus-visible background == hover background exactly (no drift).
    hover_bg = extract_background(
        css, r"\.compare-go-btn:hover\s*\{([^}]*)\}")
    if focus_bg and hover_bg:
        ok = focus_bg == hover_bg
        check("S3 focus-visible background matches hover exactly", ok,
              "" if ok else "focus=%r hover=%r" % (focus_bg, hover_bg))
    else:
        check("S3 focus-visible background matches hover exactly",
              False, "could not extract both rules")


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
