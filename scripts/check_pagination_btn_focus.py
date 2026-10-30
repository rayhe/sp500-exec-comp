#!/usr/bin/env python3
"""Regression guard: table pagination buttons show hover affordance on keyboard focus.

The 2026-10-30 10:00 PT run (279th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; .cm-path-btn
closed at the 269th). Next highest-value native-button surface: .pagination-btn
-- the main company-table pagination controls (Prev / page numbers / Next)
rendered by js/app.js renderTable footer (document.createElement('button'),
addEventListener('click') -> keyboard-operable via Tab + Enter/Space; the
prev/next buttons are disabled at the ends via the disabled attribute).

The hover affordance (.pagination-btn:hover:not(.disabled):not(.active):
border-color var(--accent), color var(--text-primary), background
var(--bg-surface)) had no :focus-visible mirror, so keyboard focus got only
the UA default outline. css/style.css now carries
.pagination-btn:focus-visible:not(.disabled):not(.active) with the exact same
three declarations, placed adjacent to the :hover rule. The hover uses theme
CSS vars, so one rule covers both themes. The :not(.disabled):not(.active)
qualifier parallels the hover selector exactly (a disabled button cannot take
focus anyway; the active page keeps its selected styling over focus).

Checks (all static):
  S1 js/app.js renders .pagination-btn as native <button> elements with click
     listeners (keyboard surface).
  S2 css/style.css has the :focus-visible mirror carrying border-color, color,
     background.
  S3 each focus-visible declaration matches the hover counterpart exactly
     (no drift).
  S4 cascade order: the .pagination-btn.active and .pagination-btn.disabled
     rules still come after the focus rule, so selected/disabled styling still
     wins over focus, exactly as it wins over hover.

Usage:
  scripts/check_pagination_btn_focus.py
  scripts/check_pagination_btn_focus.py --static-only

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
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> elements with click listeners (keyboard surface).
    s1 = ("document.createElement('button')" in js
          and "className = 'pagination-btn'" in js
          and "prevBtn.addEventListener('click'" in js
          and "pageBtn.addEventListener('click'" in js
          and "nextBtn.addEventListener('click'" in js)
    check("S1 pagination controls are native <button> with click wiring",
          s1, "" if s1 else "button render or click wiring missing in js/app.js")

    # S2: :focus-visible mirror exists with the three declarations.
    focus = extract_decls(
        css,
        r"\.pagination-btn:focus-visible:not\(\.disabled\):not\(\.active\)\s*\{([^}]*)\}")
    s2 = (focus is not None
          and focus.get("border-color") == "var(--accent)"
          and focus.get("color") == "var(--text-primary)"
          and focus.get("background") == "var(--bg-surface)")
    check("S2 :focus-visible mirror carries border-color/color/background",
          s2, "" if s2 else "focus-visible rule missing or incomplete in css/style.css: %r" % (focus,))

    # S3: focus-visible declarations match the hover counterparts exactly.
    hover = extract_decls(
        css,
        r"\.pagination-btn:hover:not\(\.disabled\):not\(\.active\)\s*\{([^}]*)\}")
    ok = (focus is not None and hover is not None and focus == hover)
    check("S3 focus-visible declarations match hover exactly",
          ok,
          "" if ok else "focus=%r hover=%r" % (focus, hover))

    # S4: .active and .disabled rules still come after the focus rule.
    focus_pos = css.find(".pagination-btn:focus-visible")
    active_pos = css.find(".pagination-btn.active {")
    disabled_pos = css.find(".pagination-btn.disabled {")
    s4 = (focus_pos != -1 and active_pos > focus_pos and disabled_pos > focus_pos)
    check("S4 .active/.disabled rules still win over focus in cascade",
          s4,
          "" if s4 else "positions focus=%d active=%d disabled=%d" % (focus_pos, active_pos, disabled_pos))


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
