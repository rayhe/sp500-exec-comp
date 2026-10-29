#!/usr/bin/env python3
"""Regression guard: methodology modal close button shows hover affordance on keyboard focus.

The 2026-10-29 03:30 PT run (265th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; 40 remained
after .path-finder-clear closed at the 264th). Next highest-value
native-button surface: .methodology-modal-close, the methodology modal's
dismiss control (index.html, native <button>, id="methodology-modal-close",
close wiring at js/app.js via e.target.id check -> closeMethodologyModal(),
plus Escape-key handling). It is ALSO programmatically focused on modal open
(js/app.js openMethodologyModal -> closeBtn.focus()), so the primary keyboard
flow (Enter on a .methodology-info-btn -> focus lands on the close button)
matches :focus-visible -- and keyboard focus previously got only the UA
default outline while mouse hover showed the elevated background/color/border.
css/style.css now mirrors exactly the hover declarations onto
.methodology-modal-close:focus-visible, placed adjacent to the hover rule;
because the declarations use theme-aware vars, ONE rule covers both themes
(same convention as the 262nd/264th runs). No mouse-behavior change; the
button is never disabled, so no :not(:disabled) parallel.

Checks (all static):
  S1 index.html renders .methodology-modal-close as a native <button> and
     js/app.js wires the close action by element id, focuses the button on
     modal open, and closes on Escape (keyboard surface).
  S2 css/style.css has a :focus-visible rule carrying background, color and
     border-color.
  S3 the focus-visible declarations match the hover declarations exactly
     (no drift).

Usage:
  scripts/check_methodology_modal_close_focus.py
  scripts/check_methodology_modal_close_focus.py --static-only

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
    print(("PASS" if ok else "FAIL") + ": " + name
          + ((" - " + detail) if detail else ""))


def extract_decls(css, pattern, props):
    m = re.search(pattern, css)
    if not m:
        return None
    body = m.group(1)
    out = {}
    for prop in props:
        pm = re.search(r"%s\s*:\s*([^;]+);" % prop, body)
        if pm:
            out[prop] = pm.group(1).strip()
    return out


def static_checks():
    html = open(HTML, encoding="utf-8").read()
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> with id-based close wiring, programmatic focus on
    # open, and Escape-to-close (keyboard-operable surface).
    s1 = ('<button class="methodology-modal-close" id="methodology-modal-close"' in html
          and "e.target.id === 'methodology-modal-close'" in js
          and "getElementById('methodology-modal-close')" in js
          and "closeBtn.focus()" in js
          and "e.key === 'Escape'" in js
          and "closeMethodologyModal" in js)
    check("S1 methodology-modal-close is a native <button> with id close wiring + focus-on-open + Escape",
          s1, "" if s1 else "button render or keyboard wiring missing in index.html/js/app.js")

    # S2: :focus-visible rule carries background, color and border-color.
    props = ("background", "color", "border-color")
    focus = extract_decls(css, r"\.methodology-modal-close:focus-visible\s*\{([^}]*)\}", props)
    s2 = focus is not None and all(p in focus for p in props)
    check("S2 :focus-visible rule carries background + color + border-color",
          s2, "" if s2 else "focus-visible rule missing or incomplete in css/style.css")

    # S3: focus-visible declarations == hover declarations exactly.
    hover = extract_decls(css, r"\.methodology-modal-close:hover\s*\{([^}]*)\}", props)
    ok = (focus is not None and hover is not None
          and all(focus.get(p) == hover.get(p) for p in props))
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
