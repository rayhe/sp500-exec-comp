#!/usr/bin/env python3
"""Regression guard: community path-finder bridge button shows hover affordance on keyboard focus.

The 2026-10-29 11:30 PT run (269th review) continued the keyboard-operable
surface audit (30 flagged classes remained after the path-finder cluster
closed at the 268th). Next highest-value surface: .cm-path-btn -- the
two-click path-finder bridge button rendered by js/network.js into each
community table row's name cell (a native <button>, keyboard-operable via
Tab + Enter/Space). Its hover affordances (tinted background, stronger
border, scale(1.1) lift on dark; tinted background + stronger border on
light) had no :focus-visible mirrors, so keyboard focus got only the UA
default outline. This matters for keyboard users in particular: pressing
Enter on a path button adds .cm-path-selecting to the container, which
makes ALL path buttons visible (display: inline-block), so keyboard flow
continues by Tabbing across them -- exactly where the focus tint is needed.

Two :focus-visible mirrors, each adjacent to its :hover rule, mirroring the
hover declarations exactly:
  (1) .cm-path-btn:focus-visible mirrors the dark hover (background,
      border-color, transform: scale(1.1));
  (2) [data-theme="light"] .cm-path-btn:focus-visible mirrors the light
      hover (background, border-color only -- the base (1) rule still
      supplies transform on light, exactly as the dark :hover transform
      applies on light hover).

The .cm-path-btn.cm-path-from rules sit after the focus rules in both
themes, so the selected-source styling still wins over both hover and focus
-- no mouse-behavior change. No pre-existing :focus rules on this class, so
no first-match-guard shadowing issue. The button is never disabled, so no
:not(:disabled) parallel is needed.

Checks (all static):
  S1 js/network.js renders the button as a native <button> element with an
     aria-label, and wires it with querySelectorAll + addEventListener('click')
     (keyboard surface).
  S2 both :focus-visible rules exist and carry the needed declarations.
  S3 each focus-visible declaration set matches its hover counterpart
     exactly (no drift).
  S4 cascade order: each .cm-path-from rule still comes after its button's
     focus rule (dark and light), so the selected-source state still wins
     over focus, exactly as it wins over hover.

Usage:
  scripts/check_cm_path_btn_focus.py
  scripts/check_cm_path_btn_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET_JS = os.path.join(REPO, "js", "network.js")
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


def find_dark(css, sel):
    """Find the dark-theme occurrence of a selector, skipping any
    [data-theme="light"] -prefixed occurrences that sit earlier in the file."""
    idx = css.find(sel)
    while idx != -1 and css[max(0, idx - 21):idx] == '[data-theme="light"] ':
        idx = css.find(sel, idx + 1)
    return idx


def static_checks():
    js = open(NET_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> render + click wiring in js/network.js.
    s1 = ('<button class="cm-path-btn"' in js
          and 'aria-label="Find path from ' in js
          and "querySelectorAll('.cm-path-btn')" in js
          and "addEventListener('click'" in js)
    check("S1 cm-path-btn native <button> render + click wiring",
          s1, "" if s1 else "missing render or wiring in js/network.js")

    # S2: both :focus-visible rules carry their declarations.
    dark_props = ("background", "border-color", "transform")
    light_props = ("background", "border-color")
    f = extract_decls(css, r"\.cm-path-btn:focus-visible\s*\{([^}]*)\}",
                      dark_props)
    lf = extract_decls(
        css,
        r"\[data-theme=\"light\"\]\s*\.cm-path-btn:focus-visible\s*\{([^}]*)\}",
        light_props)
    ok = (f is not None and all(p in f for p in dark_props)
          and lf is not None and all(p in lf for p in light_props))
    check("S2 both :focus-visible rules carry needed declarations",
          ok, "" if ok else "focus=%r light_focus=%r" % (f, lf))

    # S3: each focus-visible declaration set == its hover counterpart.
    h = extract_decls(css, r"\.cm-path-btn:hover\s*\{([^}]*)\}", dark_props)
    lh = extract_decls(
        css,
        r"\[data-theme=\"light\"\]\s*\.cm-path-btn:hover\s*\{([^}]*)\}",
        light_props)
    drift = []
    if (f is None or h is None
            or any(f.get(p) != h.get(p) for p in dark_props)):
        drift.append("dark")
    if (lf is None or lh is None
            or any(lf.get(p) != lh.get(p) for p in light_props)):
        drift.append("light")
    check("S3 focus-visible declarations match hover exactly (no drift)",
          not drift, "" if not drift else "drift in: " + ",".join(drift))

    # S4: each .cm-path-from rule still after its focus rule (dark + light).
    # NOTE: the string ".cm-path-btn.cm-path-from {" also appears as a
    # line-initial CONTINUATION of the earlier selector group
    # ".cm-row.cm-data:hover .cm-path-btn,\n.cm-path-btn.cm-path-from {"
    # (the display: inline-block rule). We care about the STANDALONE rule
    # block -- the one whose line is preceded by the previous block's
    # closing "}" -- because that is the rule whose background/border
    # declarations compete with the focus tint.
    i_focus = find_dark(css, ".cm-path-btn:focus-visible {")
    m_from = re.search(r"\}\n\.cm-path-btn\.cm-path-from\s*\{", css)
    m_light_focus = re.search(
        r'(?m)^\[data-theme="light"\]\s*\.cm-path-btn:focus-visible\s*\{',
        css)
    m_light_from = re.search(
        r'(?m)^\[data-theme="light"\]\s*\.cm-path-btn\.cm-path-from\s*\{',
        css)
    s4 = (i_focus != -1 and m_from is not None and i_focus < m_from.start()
          and m_light_focus is not None and m_light_from is not None
          and m_light_focus.start() < m_light_from.start())
    check("S4 .cm-path-from still after each focus rule (dark+light)",
          s4, "" if s4 else "cascade order broken")


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
