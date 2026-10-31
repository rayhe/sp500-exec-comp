#!/usr/bin/env python3
"""Regression guard: compare-clear-btn shows hover affordance on keyboard focus.

The 2026-10-31 02:00 PT run (287th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; .anomaly- and
.vol-scatter-nav-btn closed at the 286th). Next highest-value native-button
surface: .compare-clear-btn -- the compare tray's "Clear" action (index.html
native <button id="compare-clear-btn">, click listener at js/app.js:17409 ->
clearCompare, keyboard-operable via Tab + Enter/Space), sibling of the
260th review's .compare-go-btn.

The hover affordance (.compare-clear-btn:hover: border-color var(--negative),
color var(--negative)) had no :focus-visible mirror, so keyboard focus got
only the UA default outline. css/style.css now carries
.compare-clear-btn:focus-visible with the exact same two declarations, placed
adjacent to the :hover rule. The hover uses the theme CSS var --negative, so
one rule covers both themes; the button is never disabled, so no
:not(:disabled) parallel (unlike path-finder-go).

Checks (all static):
  S1 index.html renders .compare-clear-btn as a native <button> with a
     getElementById click wiring in js/app.js (keyboard surface).
  S2 css/style.css has the :focus-visible mirror carrying border-color, color.
  S3 each focus-visible declaration matches the hover counterpart exactly
     (no drift).
  S4 cascade order: the focus rule follows the hover rule with no later rule
     overriding the mirrored declarations (print media query only hides via
     display, which does not override border-color/color).

Usage:
  scripts/check_compare_clear_btn_focus.py
  scripts/check_compare_clear_btn_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, "index.html")
APP_JS = os.path.join(REPO, "js", "app.js")
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
    decls = {}
    for dm in re.finditer(r"([a-z-]+)\s*:\s*([^;]+);", m.group(1)):
        decls[dm.group(1).strip()] = dm.group(2).strip()
    return decls


def static_checks():
    html = open(INDEX, encoding="utf-8").read()
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> with click wiring (keyboard surface).
    s1 = ('<button class="compare-clear-btn" id="compare-clear-btn">' in html
          and "document.getElementById('compare-clear-btn').addEventListener('click'" in js)
    check("S1 compare-clear-btn is a native <button> with click wiring",
          s1, "" if s1 else "button or click wiring missing (index.html/js/app.js)")

    # S2: :focus-visible mirror exists with the two declarations.
    focus = extract_decls(
        css,
        r"\.compare-clear-btn:focus-visible\s*\{([^}]*)\}")
    s2 = (focus is not None
          and focus.get("border-color") == "var(--negative)"
          and focus.get("color") == "var(--negative)")
    check("S2 :focus-visible mirror carries border-color/color",
          s2, "" if s2 else "focus-visible rule missing or incomplete in css/style.css: %r" % (focus,))

    # S3: focus-visible declarations match the hover counterparts exactly.
    hover = extract_decls(
        css,
        r"\.compare-clear-btn:hover\s*\{([^}]*)\}")
    ok = (focus is not None and hover is not None and focus == hover)
    check("S3 focus-visible declarations match hover exactly",
          ok,
          "" if ok else "focus=%r hover=%r" % (focus, hover))

    # S4: focus rule follows hover with no later override of the mirrored decls.
    hover_pos = css.find(".compare-clear-btn:hover {")
    focus_pos = css.find(".compare-clear-btn:focus-visible {")
    s4 = hover_pos != -1 and focus_pos > hover_pos
    later = ""
    if s4:
        focus_end = css.find("}", focus_pos) + 1
        later = css[focus_end:]
    # later rules touching the class must not redeclare border-color or color
    for m in re.finditer(r"\.compare-clear-btn\b[^{]*\{([^}]*)\}", later):
        if "border-color" in m.group(1) or "color" in m.group(1):
            s4 = False
    # tolerate print-hide only if it doesn't touch these decls (display only)
    check("S4 focus rule follows hover; no later override of mirrored decls",
          s4,
          "" if s4 else "cascade conflict detected (positions hover=%d focus=%d)" % (hover_pos, focus_pos))


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
