#!/usr/bin/env python3
"""Regression guard: community CSV export button shows hover affordance on keyboard focus.

The 2026-10-28 15:30 PT run (259th review) ran a fresh scan of all
162 :hover classes in css/style.css against :focus-visible mirrors. The one
remaining keyboard-operable gap was .cm-export-btn: the community-comparison
panel's "CSV" export control (js/network.js:4862) is a native <button> with
a click listener wired to the CSV export action, so it is keyboard-operable
(Tab focus, Enter/Space activation), but keyboard focus got only the UA
default outline - the hover affordance (deepened background + brightened
border, distinct values per theme) appeared only on :hover. css/style.css
now mirrors the hover background and border-color onto :focus-visible with
exactly the hover values in both themes.

Checks (all static):
  S1 js/network.js renders .cm-export-btn as a native <button> and wires a
     click listener (keyboard surface).
  S2 css/style.css has :focus-visible rules for the button carrying the
     deepened background and border-color, in both themes.
  S3 the focus-visible background/border-color match the hover values
     exactly per theme (no drift).

Usage:
  scripts/check_cm_export_btn_focus.py
  scripts/check_cm_export_btn_focus.py --static-only

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
    print((("PASS" if ok else "FAIL") + ": " + name
           + ((" - " + detail) if detail else "")))


def extract_props(css, pattern):
    m = re.search(pattern, css)
    if not m:
        return None
    body = m.group(1)
    props = {}
    for pm in re.finditer(r"(background|border-color)\s*:\s*([^;]+);", body):
        props[pm.group(1)] = pm.group(2).strip()
    return props


def static_checks():
    js = open(NETWORK_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> with a click listener (keyboard-operable surface).
    s1 = ('<button class="cm-export-btn"' in js
          and "querySelector('.cm-export-btn')" in js
          and "addEventListener('click'" in js)
    check("S1 cm-export-btn is a native <button> with click wiring",
          s1, "" if s1 else "button render or click wiring missing in js/network.js")

    # S2: :focus-visible rules carry background + border-color, both themes.
    dark_focus = extract_props(
        css, r"\.cm-export-btn:focus-visible\s*\{([^}]*)\}")
    light_focus = extract_props(
        css, r"\[data-theme=\"light\"\]\s*\.cm-export-btn:focus-visible\s*\{([^}]*)\}")
    s2 = (dark_focus is not None and "background" in dark_focus
          and "border-color" in dark_focus
          and light_focus is not None and "background" in light_focus
          and "border-color" in light_focus)
    check("S2 :focus-visible rules deepen background + border (dark + light)",
          s2, "" if s2 else "focus-visible rule missing or incomplete in css/style.css")

    # S3: focus values == hover values exactly, per theme (no drift).
    dark_hover = extract_props(css, r"\.cm-export-btn:hover\s*\{([^}]*)\}")
    light_hover = extract_props(
        css, r"\[data-theme=\"light\"\]\s*\.cm-export-btn:hover\s*\{([^}]*)\}")
    if dark_hover and dark_focus and light_hover and light_focus:
        ok = (dark_focus == dark_hover and light_focus == light_hover)
        detail = ("" if ok else
                  "dark focus=%r hover=%r | light focus=%r hover=%r"
                  % (dark_focus, dark_hover, light_focus, light_hover))
        check("S3 focus-visible values match hover exactly per theme", ok, detail)
    else:
        check("S3 focus-visible values match hover exactly per theme",
              False, "could not extract all four rules")


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
