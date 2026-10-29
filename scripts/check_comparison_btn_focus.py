#!/usr/bin/env python3
"""Regression guard: comparison buttons show hover affordance on keyboard focus.

The 2026-10-29 07:30 PT run (267th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; 38 remained
after .methodology-info-btn closed at the 266th). Next highest-value surface:
the comparison button cluster -- .comparison-close-btn, .comparison-export-btn
(copy + CSV buttons), .comparison-path-btn -- native <button> elements in
index.html (comparison section header), click-wired in js/app.js via
getElementById('comparison-*-btn').addEventListener('click', ...) ->
keyboard-operable via Tab + Enter/Space. Their hover affordances (accent /
negative border+text; path variant adds tint, glow, lift) had no
:focus-visible mirrors, so keyboard focus got only the UA default outline.

Five :focus-visible mirrors, each adjacent to its hover rule:
  (1) .comparison-close-btn:focus-visible mirrors the close hover
      (border-color/color = var(--negative));
  (2) .comparison-export-btn:focus-visible mirrors the base dark export hover
      (border-color/color = var(--accent));
  (3) .comparison-path-btn:focus-visible mirrors the path hover (tint
      background, glow box-shadow, lift transform), placed after (2) exactly
      as the path :hover rule sits after the export :hover rule -- the path
      button carries BOTH classes, so the later rule wins for both
      :hover and :focus-visible;
  (4) [data-theme="light"] .comparison-export-btn:focus-visible mirrors the
      light-theme export hover (#0077b6 border+text);
  (5) [data-theme="light"] .comparison-path-btn:focus-visible mirrors the
      light-theme path hover (border+text #0077b6, light tint background);
      the base (3) focus rule still supplies box-shadow/transform on light,
      exactly as the base path :hover rule supplies them on light hover.

The .copied state (green, line after the export hover/focus pair in both
themes) keeps winning over both hover and focus: no mouse-behavior change.
No pre-existing :focus-visible rules on these classes, so no first-match-guard
shadowing issue. None of these buttons are ever disabled, so no
:not(:disabled) parallel is needed.

Checks (all static):
  S1 index.html renders the 4 comparison buttons as native <button>
     elements (close, copy, csv, path incl. the dual-class path button)
     and js/app.js wires each by id with addEventListener('click')
     (keyboard surface).
  S2 all five :focus-visible rules exist and carry the needed declarations
     (close/export + light export: border-color, color; path: + background,
     box-shadow, transform; light path: + background).
  S3 each focus-visible declaration set matches its hover counterpart
     exactly (no drift).
  S4 cascade order: .comparison-export-btn:focus-visible comes before
     .comparison-path-btn:focus-visible (so the later path rule wins for the
     dual-class path button, exactly as the path :hover rule wins over the
     export :hover rule), and the .copied rule still comes after the export
     focus rule (copied state still wins over focus, as over hover).

Usage:
  scripts/check_comparison_btn_focus.py
  scripts/check_comparison_btn_focus.py --static-only

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

    # S1: native <button> renders x4 and per-id click wiring in js/app.js.
    s1 = ('<button class="comparison-close-btn"' in html
          and 'id="comparison-copy-btn"' in html
          and 'id="comparison-csv-btn"' in html
          and '<button class="comparison-export-btn comparison-path-btn"' in html
          and "getElementById('comparison-path-btn').addEventListener('click'" in js
          and "getElementById('comparison-close-btn').addEventListener('click'" in js
          and "getElementById('comparison-copy-btn').addEventListener('click'" in js
          and "getElementById('comparison-csv-btn').addEventListener('click'" in js)
    check("S1 4 comparison native <button> renders + per-id click wiring",
          s1, "" if s1 else "missing a render or wiring in index.html/js/app.js")

    # S2: five :focus-visible rules carry their declarations.
    bc = ("border-color", "color")
    path_props = bc + ("background", "box-shadow", "transform")
    light_path_props = bc + ("background",)
    close = extract_decls(css, r"\.comparison-close-btn:focus-visible\s*\{([^}]*)\}", bc)
    export = extract_decls(css, r"\.comparison-export-btn:focus-visible\s*\{([^}]*)\}", bc)
    path = extract_decls(css, r"\.comparison-path-btn:focus-visible\s*\{([^}]*)\}",
                         path_props)
    light_export = extract_decls(
        css, r"\[data-theme=\"light\"\]\s*\.comparison-export-btn:focus-visible\s*\{([^}]*)\}",
        bc)
    light_path = extract_decls(
        css, r"\[data-theme=\"light\"\]\s*\.comparison-path-btn:focus-visible\s*\{([^}]*)\}",
        light_path_props)
    s2 = (close is not None and all(p in close for p in bc)
          and export is not None and all(p in export for p in bc)
          and path is not None and all(p in path for p in path_props)
          and light_export is not None and all(p in light_export for p in bc)
          and light_path is not None and all(p in light_path for p in light_path_props))
    check("S2 all five :focus-visible rules carry needed declarations",
          s2, "" if s2 else "close=%r export=%r path=%r light_export=%r light_path=%r"
          % (close, export, path, light_export, light_path))

    # S3: each focus-visible declaration set == its hover counterpart.
    pairs = [
        (close, r"\.comparison-close-btn:hover\s*\{([^}]*)\}", bc, "close"),
        (export, r"\.comparison-export-btn:hover\s*\{([^}]*)\}", bc, "export"),
        (path, r"\.comparison-path-btn:hover\s*\{([^}]*)\}", path_props, "path"),
        (light_export,
         r"\[data-theme=\"light\"\]\s*\.comparison-export-btn:hover\s*\{([^}]*)\}",
         bc, "light_export"),
        (light_path,
         r"\[data-theme=\"light\"\]\s*\.comparison-path-btn:hover\s*\{([^}]*)\}",
         light_path_props, "light_path"),
    ]
    bad = []
    for focus_decls, hover_pat, props, label in pairs:
        hover_decls = extract_decls(css, hover_pat, props)
        if (focus_decls is None or hover_decls is None
                or any(focus_decls.get(p) != hover_decls.get(p) for p in props)):
            bad.append(label)
    check("S3 focus-visible declarations match hover exactly (no drift)",
          not bad, "" if not bad else "drift in: " + ",".join(bad))

    # S4: cascade order -- path focus after export focus (dual-class button),
    # and each .copied rule still after its focus rule.
    # NOTE: [data-theme="light"] rules sit earlier in the file than the dark
    # comparison rules, so bare find() would match the light occurrence first;
    # find_dark() skips occurrences preceded by '[data-theme="light"] '.
    def find_dark(sel):
        idx = css.find(sel)
        while idx != -1 and css[max(0, idx - 21):idx] == '[data-theme="light"] ':
            idx = css.find(sel, idx + 1)
        return idx

    i_exp = find_dark(".comparison-export-btn:focus-visible")
    i_path = find_dark(".comparison-path-btn:focus-visible")
    i_copied = find_dark(".comparison-export-btn.copied {")
    i_light_focus = css.find('[data-theme="light"] .comparison-export-btn:focus-visible')
    i_light_copied = css.find('[data-theme="light"] .comparison-export-btn.copied')
    s4 = (i_exp != -1 and i_path != -1 and i_copied != -1
          and i_exp < i_path and i_exp < i_copied
          and i_light_focus != -1 and i_light_copied != -1
          and i_light_focus < i_light_copied)
    check("S4 path focus after export focus; .copied after each focus rule",
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
