#!/usr/bin/env python3
"""Regression guard: scatter-preset-btn shows hover affordance on keyboard focus.

The 2026-10-31 19:30 PT run (296th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; the
295th closed the scatter-label dismiss family). Next per the audit:
.scatter-preset-btn -- the scatter-axis preset buttons (Pay vs Ratio,
Worker vs Ratio, ...), rendered in index.html as native <button> elements
and wired in js/charts.js (setupScatterPresets) with
addEventListener('click') -> keyboard-operable via Tab + Enter/Space.

The hover affordance (:hover { border-color: var(--accent);
color: var(--accent); }) had no :focus-visible mirror, so keyboard focus
got only the UA default outline. css/style.css now carries the
:focus-visible rule adjacent to its :hover counterpart with byte-identical
declarations (same convention as the 285th-295th runs). The mirrored
values use var(--accent), which is theme-aware, so the one rule covers
both themes; no light-theme override needed.

The audit's sibling class .scatter-metric-select needs no mirror: it
already carries a :focus rule (border-color + box-shadow) covering
keyboard focus on the native <select> elements.

Parity notes for S4: the later .scatter-preset-btn.active rule also sets
border-color/color to var(--accent) at equal specificity (0,2,0), so an
active button keeps the focus affordance exactly; :active is excluded as
a transient press state with the sanctioned hover relation.

Checks (all static):
  S1 index.html renders native <button class="scatter-preset-btn..."> and
     js/charts.js wires addEventListener('click') (keyboard surface).
  S2 css/style.css has the :focus-visible mirror with the expected
     declarations (border-color, color).
  S3 the focus-visible block matches the hover block exactly (no drift).
  S4 the focus rule comes after the hover rule; no later compatible rule
     overrides the mirrored declarations for focus but not for hover
     (:active excluded - transient press state with the sanctioned
     hover relation).

Usage:
  scripts/check_scatter_preset_btn_focus.py
  scripts/check_scatter_preset_btn_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(REPO, "index.html")
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name
          + ((" - " + detail) if detail else ""))


def parse_rules(css):
    """Parse top-level rules into (selector, declarations dict, pos) tuples."""
    rules = []
    for m in re.finditer(r'([^{}]+?)\{([^}]*)\}', css):
        sel = m.group(1).strip()
        if not sel or sel.startswith('@'):
            continue
        decls = {}
        for dm in re.finditer(r'([a-z-]+)\s*:\s*([^;]+);', m.group(2)):
            decls[dm.group(1).strip()] = dm.group(2).strip()
        rules.append((sel, decls, m.start()))
    return rules


def specificity(sel):
    """Rough CSS specificity (a, b, c) for class/attr/pseudo selectors."""
    a = len(re.findall(r'#[A-Za-z0-9_-]+', sel))
    b = len(re.findall(r'\.[A-Za-z0-9_-]+', sel)) + \
        len(re.findall(r'\[[^\]]+\]', sel)) + \
        len(re.findall(r':(?!:)[A-Za-z0-9_-]+(\([^)]*\))?', sel))
    c = len(re.findall(r'(^|[\s>+~])([a-zA-Z][a-zA-Z0-9_-]*)', sel))
    return (a, b, c)


def required_classes(sel):
    """Class names a selector requires (ignores pseudo-classes)."""
    base = re.sub(r':[A-Za-z0-9_-]+(\([^)]*\))?', '', sel)
    return set(re.findall(r'\.([A-Za-z0-9_-]+)', base))


# (focus selector, hover selector, expected props, needle for S4 scope)
RULE_PAIRS = [
    (".scatter-preset-btn:focus-visible",
     ".scatter-preset-btn:hover",
     ("border-color", "color"), "scatter-preset-btn"),
]


def static_checks():
    html = open(INDEX_HTML, encoding="utf-8").read()
    js = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    rules = parse_rules(css)
    by_sel = {}
    for sel, decls, pos in rules:
        by_sel.setdefault(sel, []).append((decls, pos))

    # S1: native <button class="scatter-preset-btn...> render in index.html
    # + click wiring in js/charts.js.
    s1 = (('<button class="scatter-preset-btn' in html)
          and ("querySelectorAll('.scatter-preset-btn')" in js)
          and ("addEventListener('click'" in js))
    check("S1 scatter-preset-btn renders as native <button> with click wiring",
          s1, "" if s1 else "button render missing in index.html or click "
          "wiring missing in js/charts.js")

    # S2: the :focus-visible mirrors exist with the expected declarations.
    s2_ok = True
    s2_detail = ""
    for focus_sel, _, props, _ in RULE_PAIRS:
        decls = by_sel.get(focus_sel, [(None, -1)])[0][0]
        if decls is None or not all(p in decls for p in props):
            s2_ok = False
            s2_detail = "missing/incomplete: %s -> %r" % (focus_sel, decls)
            break
    check("S2 :focus-visible mirrors exist with expected declarations",
          s2_ok, s2_detail)

    # S3: focus-visible block matches the hover block exactly.
    s3_ok = True
    s3_detail = ""
    for focus_sel, hover_sel, _, _ in RULE_PAIRS:
        fdecls = by_sel.get(focus_sel, [(None, -1)])[0][0]
        hdecls = by_sel.get(hover_sel, [(None, -1)])[0][0]
        if fdecls is None or hdecls is None or fdecls != hdecls:
            s3_ok = False
            s3_detail = "drift: %s focus=%r hover=%r" % (focus_sel, fdecls, hdecls)
            break
    check("S3 focus-visible declarations match hover exactly (no drift)",
          s3_ok, s3_detail)

    # S4: focus rule after hover; no later rule overrides the mirrored
    # declarations for focus but not for hover (:active excluded).
    s4_ok = True
    s4_detail = ""
    for focus_sel, hover_sel, props, needle in RULE_PAIRS:
        fentries = by_sel.get(focus_sel)
        hentries = by_sel.get(hover_sel)
        if not fentries or not hentries:
            s4_ok = False
            s4_detail = "rule missing: %s / %s" % (focus_sel, hover_sel)
            break
        _, fpos = fentries[0]
        _, hpos = hentries[0]
        if not (hpos < fpos):
            s4_ok = False
            s4_detail = "focus not after hover: %s" % focus_sel
            break
        fspec = specificity(focus_sel)
        hspec = specificity(hover_sel)
        fclasses = required_classes(focus_sel)
        hclasses = required_classes(hover_sel)
        for sel, decls, pos in rules:
            if pos <= fpos:
                continue
            if needle not in sel:
                continue
            if ":active" in sel:
                continue  # transient press state; hover has the same relation
            lclasses = required_classes(sel)
            if not (lclasses <= fclasses or fclasses <= lclasses):
                continue  # cannot hit the same element
            # Parity: the later rule also overrides the hover counterpart
            # identically -> focus keeps hover's relation; sanctioned.
            if (lclasses <= hclasses or hclasses <= lclasses) and \
                    specificity(sel) >= hspec:
                continue
            if specificity(sel) < fspec:
                continue
            for prop in props:
                if prop in decls:
                    s4_ok = False
                    s4_detail = ("later rule overrides %s on %s without "
                                 "the same override of hover: %r"
                                 % (prop, focus_sel, sel[:80]))
                    break
            if not s4_ok:
                break
        if not s4_ok:
            break
    check("S4 focus rules follow hover; no unsanctioned later override",
          s4_ok, s4_detail)


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
