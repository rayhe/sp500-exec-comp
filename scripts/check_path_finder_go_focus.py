#!/usr/bin/env python3
"""Regression guard: path finder "Find" button shows hover affordance on keyboard focus.

The 2026-10-28 19:30 PT run (261st review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; .compare-go-btn
closed at the 260th). Next highest-value native-button surface: .path-finder-go,
the network tab's path-finder "Find" action (index.html:245, native <button>,
click listener at js/network.js:7832 -> keyboard-operable via Tab + Enter/Space;
enabled only when both endpoints are chosen, network.js:7102), whose hover
affordance (dark: rgba(168,85,247,0.25); light: rgba(126,34,206,0.15)) had no
focus-visible mirror - keyboard focus got only the UA default outline.
css/style.css now mirrors exactly the hover value onto
.path-finder-go:focus-visible:not(:disabled) (dark) and
[data-theme="light"] .path-finder-go:focus-visible:not(:disabled) (light),
placed adjacent to each theme's hover rule; :not(:disabled) parallels the
hover selector exactly (a disabled button cannot take focus anyway).

Checks (all static):
  S1 index.html renders .path-finder-go as a native <button> and js/network.js
     wires a click listener (keyboard surface).
  S2 css/style.css has :focus-visible rules carrying background for both
     themes.
  S3 each focus-visible background matches its theme's hover background
     exactly (no drift).

Usage:
  scripts/check_path_finder_go_focus.py
  scripts/check_path_finder_go_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "index.html")
NETWORK_JS = os.path.join(REPO, "js", "network.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name
          + ((" - " + detail) if detail else ""))


def extract_background(css, pattern):
    m = re.search(pattern, css)
    if not m:
        return None
    pm = re.search(r"background\s*:\s*([^;]+);", m.group(1))
    return pm.group(1).strip() if pm else None


def static_checks():
    html = open(HTML, encoding="utf-8").read()
    js = open(NETWORK_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> with a click listener (keyboard-operable surface).
    s1 = ('<button class="path-finder-go"' in html
          and "getElementById('path-finder-go')" in js
          and "pfGoBtn.addEventListener('click'" in js)
    check("S1 path-finder-go is a native <button> with click wiring",
          s1, "" if s1 else "button render or click wiring missing in index.html/js/network.js")

    # S2: :focus-visible rules carry background in both themes.
    dark_focus = extract_background(
        css, r"\.path-finder-go:focus-visible:not\(:disabled\)\s*\{([^}]*)\}")
    light_focus = extract_background(
        css, r'\[data-theme="light"\]\s*\.path-finder-go:focus-visible:not\(:disabled\)\s*\{([^}]*)\}')
    s2 = dark_focus is not None and light_focus is not None
    check("S2 :focus-visible rules carry background (both themes)",
          s2, "" if s2 else "focus-visible rule missing in css/style.css (dark=%r light=%r)"
          % (dark_focus, light_focus))

    # S3: each focus-visible background == its theme's hover background exactly.
    dark_hover = extract_background(
        css, r"\.path-finder-go:hover:not\(:disabled\)\s*\{([^}]*)\}")
    light_hover = extract_background(
        css, r'\[data-theme="light"\]\s*\.path-finder-go:hover:not\(:disabled\)\s*\{([^}]*)\}')
    ok = (dark_focus is not None and dark_hover is not None
          and light_focus is not None and light_hover is not None
          and dark_focus == dark_hover and light_focus == light_hover)
    check("S3 focus-visible backgrounds match hover exactly (both themes)",
          ok,
          "" if ok else "dark focus=%r dark hover=%r light focus=%r light hover=%r"
          % (dark_focus, dark_hover, light_focus, light_hover))


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
