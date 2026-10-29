#!/usr/bin/env python3
"""Regression guard: export button cluster shows hover affordance on keyboard focus.

The 2026-10-28 23:30 PT run (263rd review) continued the keyboard-operable
surface audit from the 260th/261st/262nd reviews (render-site triage of :hover
classes without :focus-visible mirrors; .compare-go-btn closed at the 260th,
.path-finder-go at the 261st, .theme-toggle at the 262nd). Next highest-value
native-button surface: the comp-table export action cluster (index.html:378-386,
all native <button>s, click listeners in js/app.js, keyboard-operable via
Tab + Enter/Space), whose hover affordances had no focus-visible mirrors.

Scope: three rules, one per hover-variant, because specificity diverges:
  .export-csv-btn:hover                                   (0,2,0 equivalent base)
  .export-btn-group .export-neo-btn:hover                 (0,3,0, green variant)
  .export-btn-group .reset-all-btn:hover                  (0,3,0, orange variant,
                                                           hover adds color:#fdba74)
The variants carry the .export-csv-btn base class too, so a base-only
:focus-visible rule would render the green/orange buttons with the cyan
tint on keyboard focus - each variant gets its own exact-mirror rule.
The hover declarations are fixed rgba values with no light-theme override,
so each single rule covers both themes (same convention as the 262nd run).

Checks (all static):
  S1 index.html renders export-csv-btn/export-neo-btn/reset-all-btn as
     native <button>s and js/app.js wires a click listener for export-csv-btn
     (keyboard surface).
  S2 css/style.css has all three :focus-visible rules, each carrying the
     declarations of its hover counterpart (background + border-color;
     reset variant also color).
  S3 each focus-visible declaration matches its hover declaration exactly
     (no drift).

Usage:
  scripts/check_export_csv_btn_focus.py
  scripts/check_export_csv_btn_focus.py --static-only

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


def sel_re(sel):
    """Build a regex matching an exact CSS selector rule block."""
    return re.escape(sel) + r"\s*\{([^}]*)\}"


VARIANTS = [
    # (label, hover selector, focus selector, props to mirror)
    ("base", ".export-csv-btn:hover",
     ".export-csv-btn:focus-visible",
     ("background", "border-color")),
    ("neo", ".export-btn-group .export-neo-btn:hover",
     ".export-btn-group .export-neo-btn:focus-visible",
     ("background", "border-color")),
    ("reset", ".export-btn-group .reset-all-btn:hover",
     ".export-btn-group .reset-all-btn:focus-visible",
     ("background", "border-color", "color")),
]


def static_checks():
    html = open(HTML, encoding="utf-8").read()
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button>s with click wiring (keyboard-operable surface).
    s1 = ('<button class="export-csv-btn"' in html
          and '<button class="export-csv-btn export-neo-btn"' in html
          and '<button class="export-csv-btn reset-all-btn"' in html
          and "getElementById('export-csv-btn')" in js
          and "addEventListener('click'" in js)
    check("S1 export cluster renders native <button>s with click wiring",
          s1, "" if s1 else "button render or click wiring missing in index.html/js/app.js")

    # S2 + S3: each :focus-visible rule exists and mirrors its hover rule exactly.
    for label, hover_sel, focus_sel, props in VARIANTS:
        focus_rule = extract_rule(css, sel_re(focus_sel))
        hover_rule = extract_rule(css, sel_re(hover_sel))
        s2 = (focus_rule is not None
              and all(extract_decl(focus_rule, p) is not None for p in props))
        check("S2 %s :focus-visible rule carries %s" % (label, "/".join(props)),
              s2, "" if s2 else "focus-visible rule missing in css/style.css (rule=%r)"
              % (focus_rule,))
        ok = focus_rule is not None and hover_rule is not None
        if ok:
            for prop in props:
                if extract_decl(focus_rule, prop) != extract_decl(hover_rule, prop):
                    ok = False
                    break
        check("S3 %s focus-visible declarations match hover exactly" % label,
              ok, "" if ok else "focus=%r hover=%r" % (focus_rule, hover_rule))


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
