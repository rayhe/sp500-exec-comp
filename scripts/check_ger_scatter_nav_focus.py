#!/usr/bin/env python3
"""Regression guard: GER scatter-nav buttons show hover affordance on keyboard focus.

The 2026-10-30 15:30 PT run (282nd review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors;
26 remained after .detail-network-btn/.detail-table-btn closed at the
281st). Next per the 260th-review priority order: .ger-scatter-nav -- the
GER risk narrative's "Explore in scatter" ticker buttons, rendered by
js/charts.js as native <button> elements with addEventListener('click')
wiring -> keyboard-operable via Tab + Enter/Space.

The hover affordance (.ger-scatter-nav:hover: background
rgba(239, 71, 111, 0.15), border-color rgba(239, 71, 111, 0.4)) had no
:focus-visible mirror, so keyboard focus got only the UA default outline.
css/style.css now carries one :focus-visible rule, placed adjacent to the
:hover rule with byte-identical declarations. The declarations are fixed
rgba values with no light-theme override, so one rule covers both themes
(same convention as the 262nd/280th/281st runs).

Checks (all static):
  S1 js/charts.js renders native <button class="ger-scatter-nav"> elements
     with click wiring (keyboard surface).
  S2 css/style.css has the :focus-visible mirror carrying background +
     border-color.
  S3 the focus-visible declaration block matches its hover counterpart
     exactly (no drift).
  S4 the focus rule comes after the hover rule and no later rule
     overrides the mirrored declarations, so the mirror is actually
     visible on keyboard focus.

Usage:
  scripts/check_ger_scatter_nav_focus.py
  scripts/check_ger_scatter_nav_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name
          + ((" - " + detail) if detail else ""))


def find_rule(css, selector):
    """Find a standalone rule by selector. Returns (declarations dict, pos)
    or (None, -1)."""
    for m in re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", css):
        decls = {}
        for dm in re.finditer(r"([a-z-]+)\s*:\s*([^;]+);", m.group(1)):
            decls[dm.group(1).strip()] = dm.group(2).strip()
        return decls, m.start()
    return None, -1


HOVER_SEL = ".ger-scatter-nav:hover"
FOCUS_SEL = ".ger-scatter-nav:focus-visible"


def static_checks():
    js = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> render with click wiring (keyboard surface).
    # The buttons are built in a single-quoted JS string, so the HTML
    # carries plain double quotes (no backslash escaping).
    s1 = (("'<button class=\"ger-scatter-nav\"") in js
          and "querySelectorAll('.ger-scatter-nav')" in js
          and "addEventListener('click'" in js
          and "window.navigateToScatter" in js)
    check("S1 ger-scatter-nav buttons are native <button> with click wiring",
          s1, "" if s1 else "button render or click wiring missing in js/charts.js")

    # S2: the :focus-visible mirror exists carrying background + border-color.
    focus_decls, _ = find_rule(css, FOCUS_SEL)
    s2 = (focus_decls is not None
          and "background" in focus_decls
          and "border-color" in focus_decls)
    check("S2 :focus-visible mirror carries background/border-color",
          s2, "" if s2 else "missing/incomplete: %r" % (focus_decls,))

    # S3: focus-visible block matches the hover counterpart exactly.
    hover_decls, _ = find_rule(css, HOVER_SEL)
    s3 = (hover_decls is not None and focus_decls is not None
          and focus_decls == hover_decls)
    check("S3 focus-visible declarations match hover exactly (no drift)",
          s3, "" if s3 else "drift: focus=%r hover=%r" % (focus_decls, hover_decls))

    # S4: focus rule comes after the hover rule; no later rule overrides
    # the mirrored declarations.
    _, hover_pos = find_rule(css, HOVER_SEL)
    _, focus_pos = find_rule(css, FOCUS_SEL)
    s4 = (hover_pos != -1 and focus_pos != -1 and hover_pos < focus_pos)
    s4_detail = ""
    if not s4:
        s4_detail = "focus rule not after hover (hover=%d focus=%d)" % (hover_pos, focus_pos)
    else:
        for m in re.finditer(r'([^{}]+?)\{([^}]*)\}', css):
            sel = m.group(1)
            if "ger-scatter-nav" not in sel or m.start() <= focus_pos:
                continue
            body = m.group(2)
            for prop in ("background", "border-color", "color"):
                if re.search(r"(?<![a-z-])" + prop + r"\s*:", body):
                    s4 = False
                    s4_detail = "later rule overrides %s: %r" % (prop, sel.strip()[:80])
    check("S4 focus rule follows hover; no later override of mirrored decls",
          s4, s4_detail)


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
