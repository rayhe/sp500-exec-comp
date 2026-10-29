#!/usr/bin/env python3
"""Regression guard: path finder "Clear" button shows hover affordance on keyboard focus.

The 2026-10-29 02:00 PT run (264th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; 41 remained
after .export-csv-btn cluster closed at the 263rd). Next highest-value
native-button surface: .path-finder-clear, the network tab's path-finder
"Clear" action (index.html:246, native <button>, click listener at
js/network.js:7836 -> keyboard-operable via Tab + Enter/Space), whose hover
affordance (border-color: var(--accent); color: var(--text-primary)) had no
focus-visible mirror - keyboard focus got only the UA default outline.
css/style.css now mirrors exactly the hover declarations onto
.path-finder-clear:focus-visible, placed adjacent to the hover rule; because
the declarations use theme-aware vars (--accent / --text-primary resolve per
data-theme), ONE rule covers both themes (same convention as the 262nd
theme-toggle run). No mouse-behavior change.

Checks (all static):
  S1 index.html renders .path-finder-clear as a native <button> and
     js/network.js wires a click listener (keyboard surface).
  S2 css/style.css has a :focus-visible rule carrying border-color and color.
  S3 the focus-visible declarations match the hover declarations exactly
     (no drift).

Usage:
  scripts/check_path_finder_clear_focus.py
  scripts/check_path_finder_clear_focus.py --static-only

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


def extract_decls(css, pattern):
    m = re.search(pattern, css)
    if not m:
        return None
    body = m.group(1)
    out = {}
    for prop in ("border-color", "color"):
        pm = re.search(r"%s\s*:\s*([^;]+);" % prop, body)
        if pm:
            out[prop] = pm.group(1).strip()
    return out


def static_checks():
    html = open(HTML, encoding="utf-8").read()
    js = open(NETWORK_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> with a click listener (keyboard-operable surface).
    s1 = ('<button class="path-finder-clear"' in html
          and "getElementById('path-finder-clear')" in js
          and "pfClearBtn.addEventListener('click'" in js)
    check("S1 path-finder-clear is a native <button> with click wiring",
          s1, "" if s1 else "button render or click wiring missing in index.html/js/network.js")

    # S2: :focus-visible rule carries border-color and color.
    focus = extract_decls(css, r"\.path-finder-clear:focus-visible\s*\{([^}]*)\}")
    s2 = focus is not None and "border-color" in focus and "color" in focus
    check("S2 :focus-visible rule carries border-color + color",
          s2, "" if s2 else "focus-visible rule missing or incomplete in css/style.css")

    # S3: focus-visible declarations == hover declarations exactly.
    hover = extract_decls(css, r"\.path-finder-clear:hover\s*\{([^}]*)\}")
    ok = (focus is not None and hover is not None
          and focus.get("border-color") == hover.get("border-color")
          and focus.get("color") == hover.get("color"))
    check("S3 focus-visible declarations match hover exactly",
          ok,
          "" if ok else "focus=%r hover=%r" % (focus, hover))


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
