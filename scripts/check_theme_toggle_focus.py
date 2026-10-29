#!/usr/bin/env python3
"""Regression guard: theme toggle button shows hover affordance on keyboard focus.

The 2026-10-28 22:00 PT run (262nd review) continued the keyboard-operable
surface audit from the 260th/261st reviews (render-site triage of :hover
classes without :focus-visible mirrors; .compare-go-btn closed at the 260th,
.path-finder-go at the 261st). Next highest-value native-button surface:
.theme-toggle, the global theme switcher in the site header (index.html:124,
native <button id="theme-toggle">, click listener at js/app.js:15604 ->
keyboard-operable via Tab + Enter/Space; visible on every page view), whose
hover affordance (border-color: var(--accent); color: var(--accent);
background: var(--bg-elevated)) had no focus-visible mirror - keyboard focus
got only the UA default outline. css/style.css now mirrors exactly the hover
declarations onto .theme-toggle:focus-visible, placed adjacent to the hover
rule; the vars are theme-aware (--accent / --bg-elevated resolve per
data-theme), so one rule covers both themes.

Checks (all static):
  S1 index.html renders .theme-toggle as a native <button> and js/app.js
     wires a click listener (keyboard surface).
  S2 css/style.css has a .theme-toggle:focus-visible rule carrying
     border-color, color, and background.
  S3 each focus-visible declaration matches the hover declaration exactly
     (no drift).

Usage:
  scripts/check_theme_toggle_focus.py
  scripts/check_theme_toggle_focus.py --static-only

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


def extract_rule(css, pattern):
    m = re.search(pattern, css)
    return m.group(1).strip() if m else None


def extract_decl(rule, prop):
    m = re.search(prop + r"\s*:\s*([^;]+);", rule)
    return m.group(1).strip() if m else None


def static_checks():
    html = open(HTML, encoding="utf-8").read()
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> with a click listener (keyboard-operable surface).
    s1 = ('<button class="theme-toggle"' in html
          and "getElementById('theme-toggle')" in js
          and "themeBtn.addEventListener('click'" in js)
    check("S1 theme-toggle is a native <button> with click wiring",
          s1, "" if s1 else "button render or click wiring missing in index.html/js/app.js")

    # S2: :focus-visible rule carries border-color, color, background.
    focus_rule = extract_rule(css, r"\.theme-toggle:focus-visible\s*\{([^}]*)\}")
    s2 = (focus_rule is not None
          and extract_decl(focus_rule, "border-color") is not None
          and extract_decl(focus_rule, "color") is not None
          and extract_decl(focus_rule, "background") is not None)
    check("S2 :focus-visible rule carries border-color/color/background",
          s2, "" if s2 else "focus-visible rule missing in css/style.css (rule=%r)"
          % (focus_rule,))

    # S3: each focus-visible declaration == hover declaration exactly.
    hover_rule = extract_rule(css, r"\.theme-toggle:hover\s*\{([^}]*)\}")
    ok = focus_rule is not None and hover_rule is not None
    if ok:
        for prop in ("border-color", "color", "background"):
            if extract_decl(focus_rule, prop) != extract_decl(hover_rule, prop):
                ok = False
                break
    check("S3 focus-visible declarations match hover exactly",
          ok,
          "" if ok else "focus=%r hover=%r" % (focus_rule, hover_rule))


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
