#!/usr/bin/env python3
"""Regression guard: path-finder buttons show hover affordance on keyboard focus.

The 2026-10-29 10:00 PT run (268th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; 35 remained
after the comparison button cluster closed at the 267th). Next highest-value
surface: the path-finder button cluster -- .pf-epc-compare-btn,
.pf-epc-compare-all-btn, .pf-export-btn, .pf-export-csv-btn,
.pf-show-scatter-btn -- native <button> elements rendered by js/network.js
into the path-finder result panel, each click-wired via
pfResult.querySelector(...).addEventListener('click', ...) ->
keyboard-operable via Tab + Enter/Space. Their hover affordances (tinted
backgrounds, stronger borders, lift transform; scatter adds a glow
box-shadow) had no :focus-visible mirrors, so keyboard focus got only the UA
default outline.

Ten :focus-visible mirrors (5 buttons x 2 themes), each adjacent to its
:hover rule, mirroring the hover declarations exactly. The hover decls are
fixed rgba values (not theme-aware vars), so dark and light each need their
own mirror:
  (1) .pf-epc-compare-btn:focus-visible mirrors the dark hover (background,
      border-color, transform);
  (2) [data-theme="light"] .pf-epc-compare-btn:focus-visible mirrors the
      light hover (background, border-color only -- the base (1) rule still
      supplies transform on light, exactly as the dark :hover transform
      applies on light hover);
  (3)/(4) same pattern for .pf-epc-compare-all-btn (green);
  (5)/(6) same pattern for .pf-export-btn (purple); the .pf-export-copied
      rules sit after the focus rules in both themes, so the copied state
      still wins over both hover and focus -- no mouse-behavior change;
  (7)/(8) same pattern for .pf-export-csv-btn (cyan), copied state likewise
      still winning;
  (9)/(10) same pattern for .pf-show-scatter-btn (green + glow box-shadow).

No pre-existing :focus-visible rules on these classes, so no
first-match-guard shadowing issue. None of these buttons are ever disabled,
so no :not(:disabled) parallel is needed.

Checks (all static):
  S1 js/network.js renders the 5 buttons as native <button> elements and
     wires each with querySelector + addEventListener('click') (keyboard
     surface).
  S2 all ten :focus-visible rules exist and carry the needed declarations.
  S3 each focus-visible declaration set matches its hover counterpart
     exactly (no drift).
  S4 cascade order: each .pf-export-copied rule still comes after its
     button's focus rule (dark and light), so the copied state still wins
     over focus, exactly as it wins over hover.

Usage:
  scripts/check_pathfinder_btn_focus.py
  scripts/check_pathfinder_btn_focus.py --static-only

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

    # S1: five native <button> renders + click wiring in js/network.js.
    renders = [
        '<button class="pf-epc-compare-btn"',
        '<button class="pf-epc-compare-all-btn"',
        '<button class="pf-export-btn" id="pf-export-btn"',
        '<button class="pf-export-csv-btn" id="pf-export-csv-btn"',
        '<button class="pf-show-scatter-btn" id="pf-show-scatter-btn"',
    ]
    wirings = [
        "querySelector('.pf-epc-compare-btn')",
        "querySelector('.pf-epc-compare-all-btn')",
        "querySelector('#pf-export-btn')",
        "querySelector('#pf-export-csv-btn')",
        "querySelector('#pf-show-scatter-btn')",
    ]
    s1 = (all(r in js for r in renders)
          and all(w in js for w in wirings)
          and js.count("addEventListener('click'") >= 5)
    check("S1 5 path-finder native <button> renders + click wiring",
          s1, "" if s1 else "missing a render or wiring in js/network.js")

    # S2: ten :focus-visible rules carry their declarations.
    std_props = ("background", "border-color", "transform")
    scatter_props = std_props + ("box-shadow",)
    light_props = ("background", "border-color")
    light_scatter_props = light_props + ("box-shadow",)
    btns = ["pf-epc-compare-btn", "pf-epc-compare-all-btn",
            "pf-export-btn", "pf-export-csv-btn", "pf-show-scatter-btn"]
    focus = {}
    ok = True
    for b in btns:
        dark_props = scatter_props if b == "pf-show-scatter-btn" else std_props
        light_needed = light_scatter_props if b == "pf-show-scatter-btn" else light_props
        f = extract_decls(css, r"\.%s:focus-visible\s*\{([^}]*)\}" % b,
                          dark_props)
        lf = extract_decls(
            css,
            r"\[data-theme=\"light\"\]\s*\.%s:focus-visible\s*\{([^}]*)\}" % b,
            light_needed)
        focus[b] = (f, lf)
        if (f is None or not all(p in f for p in dark_props)
                or lf is None or not all(p in lf for p in light_needed)):
            ok = False
    check("S2 all ten :focus-visible rules carry needed declarations",
          ok, "" if ok else "focus=%r" % (focus,))

    # S3: each focus-visible declaration set == its hover counterpart.
    bad = []
    for b in btns:
        dark_props = scatter_props if b == "pf-show-scatter-btn" else std_props
        light_needed = light_scatter_props if b == "pf-show-scatter-btn" else light_props
        f, lf = focus[b]
        h = extract_decls(css, r"\.%s:hover\s*\{([^}]*)\}" % b, dark_props)
        lh = extract_decls(
            css,
            r"\[data-theme=\"light\"\]\s*\.%s:hover\s*\{([^}]*)\}" % b,
            light_needed)
        if (f is None or h is None
                or any(f.get(p) != h.get(p) for p in dark_props)):
            bad.append(b)
        if (lf is None or lh is None
                or any(lf.get(p) != lh.get(p) for p in light_needed)):
            bad.append("light_" + b)
    check("S3 focus-visible declarations match hover exactly (no drift)",
          not bad, "" if not bad else "drift in: " + ",".join(bad))

    # S4: each .pf-export-copied rule still after its button's focus rule.
    s4_parts = []
    for b in ["pf-export-btn", "pf-export-csv-btn"]:
        i_focus = find_dark(css, "." + b + ":focus-visible {")
        i_copied = find_dark(css, "." + b + ".pf-export-copied {")
        i_light_focus = css.find('[data-theme="light"] .' + b + ":focus-visible")
        i_light_copied = css.find('[data-theme="light"] .' + b + ".pf-export-copied")
        s4_parts.append(i_focus != -1 and i_copied != -1 and i_focus < i_copied)
        s4_parts.append(i_light_focus != -1 and i_light_copied != -1
                        and i_light_focus < i_light_copied)
    check("S4 .pf-export-copied still after each focus rule (dark+light)",
          all(s4_parts), "" if all(s4_parts) else "cascade order broken")


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
