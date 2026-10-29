#!/usr/bin/env python3
"""Regression guard: methodology info buttons show hover affordance on keyboard focus.

The 2026-10-29 06:00 PT run (266th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; 39 remained
after .methodology-modal-close closed at the 265th). Next highest-value
surface: .methodology-info-btn, the six methodology "i" buttons in section
headers (peer network, governance, GER; index.html, native <button>
elements, click wiring via delegated closest('.methodology-info-btn')
handler in js/app.js -> keyboard-operable via Tab + Enter/Space). Their
hover affordances (tint background + border + text color + scale) had no
:focus-visible mirrors, so keyboard focus got only the UA default outline.

The hover declarations are fixed rgba values (NOT theme vars), so three
separate :focus-visible mirrors are needed, each adjacent to its hover rule:
  (1) .methodology-info-btn:focus-visible mirrors the base dark hover
      (background/border-color/color + transform scale(1.05));
  (2) .methodology-info-btn.ger-method-btn:focus-visible mirrors the GER
      (red) variant hover; the transform comes from the base focus rule,
      exactly as the hover transform comes from the base :hover rule;
  (3) [data-theme="light"] .methodology-info-btn:focus-visible mirrors the
      light-theme hover. There is no light-theme ger :hover rule, so none is
      added for light focus: placed at the same cascade position, the light
      base rule wins over the earlier ger focus-visible rule for
      background/border-color/color, exactly as the light base rule wins
      over the dark ger :hover rule -- so focus matches hover on the
      light-theme GER button too (light values, base transform still
      applying). No mouse-behavior change; the buttons are never disabled,
      so no :not(:disabled) parallel. No pre-existing
      .methodology-info-btn:focus-visible rule, so no first-match-guard
      shadowing issue.

Checks (all static):
  S1 index.html renders .methodology-info-btn as native <button> elements
     (all 6, incl. the ger-method-btn variant) and js/app.js wires clicks
     via closest('.methodology-info-btn') (keyboard surface).
  S2 css/style.css has all three :focus-visible rules carrying background,
     color and border-color (base also transform).
  S3 each focus-visible declaration set matches its hover counterpart
     exactly (no drift): base incl. transform; ger and light without
     transform (their hovers declare none).

Usage:
  scripts/check_methodology_info_btn_focus.py
  scripts/check_methodology_info_btn_focus.py --static-only

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

    # S1: native <button> renders (6 info buttons, one with ger-method-btn)
    # and delegated closest() click wiring in js/app.js (keyboard-operable).
    n_btn = html.count('<button class="methodology-info-btn')
    s1 = (n_btn >= 6
          and '<button class="methodology-info-btn ger-method-btn"' in html
          and "closest('.methodology-info-btn')" in js)
    check("S1 methodology-info-btn native <button> x6 + delegated click wiring",
          s1, "" if s1 else "found %d renders or missing closest() wiring" % n_btn)

    # S2: three :focus-visible rules carry background + color + border-color.
    props = ("background", "color", "border-color")
    base = extract_decls(css, r"\.methodology-info-btn:focus-visible\s*\{([^}]*)\}", props)
    ger = extract_decls(css,
                        r"\.methodology-info-btn\.ger-method-btn:focus-visible\s*\{([^}]*)\}",
                        props)
    light = extract_decls(css,
                          r"\[data-theme=\"light\"\]\s*\.methodology-info-btn:focus-visible\s*\{([^}]*)\}",
                          props)
    s2 = (base is not None and all(p in base for p in props)
          and ger is not None and all(p in ger for p in props)
          and light is not None and all(p in light for p in props))
    check("S2 all three :focus-visible rules carry background + color + border-color",
          s2, "" if s2 else "base=%r ger=%r light=%r" % (base, ger, light))

    # S3: each focus-visible declaration set == its hover counterpart.
    base_props = props + ("transform",)
    base_focus = extract_decls(css, r"\.methodology-info-btn:focus-visible\s*\{([^}]*)\}",
                               base_props)
    base_hover = extract_decls(css, r"\.methodology-info-btn:hover\s*\{([^}]*)\}", base_props)
    ger_focus = ger
    ger_hover = extract_decls(css,
                              r"\.methodology-info-btn\.ger-method-btn:hover\s*\{([^}]*)\}",
                              props)
    light_focus = light
    light_hover = extract_decls(css,
                                r"\[data-theme=\"light\"\]\s*\.methodology-info-btn:hover\s*\{([^}]*)\}",
                                props)
    ok_base = (base_focus is not None and base_hover is not None
               and all(base_focus.get(p) == base_hover.get(p) for p in base_props))
    ok_ger = (ger_focus is not None and ger_hover is not None
              and all(ger_focus.get(p) == ger_hover.get(p) for p in props))
    ok_light = (light_focus is not None and light_hover is not None
                and all(light_focus.get(p) == light_hover.get(p) for p in props))
    ok = ok_base and ok_ger and ok_light
    check("S3 focus-visible declarations match hover exactly (base incl. transform)",
          ok, "" if ok else "base=%r ger=%r light=%r" % (ok_base, ok_ger, ok_light))


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
