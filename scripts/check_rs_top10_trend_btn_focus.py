#!/usr/bin/env python3
"""Regression guard: rs-mode-btn / top10-mode-btn / trend-overlay-btn show
hover affordance on keyboard focus.

The 2026-10-31 14:00 PT run (293rd review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; the 292nd
closed the NEO detail-view toggle family). Next per the audit: the chart
mode/series toggle families --

  .rs-mode-btn (role-sector "$ Absolute" / "+-% vs Index", index.html:1010-1011,
  wired via inline onclick="setRoleSectorMode(...)" -> window.setRoleSectorMode,
  js/app.js:15461),
  .top10-mode-btn (top-10 chart modes, index.html:643-648, wired via
  addEventListener('click') in js/charts.js:228), and
  .trend-overlay-btn (trend series toggles, index.html:595-599, wired via
  addEventListener('click') in js/charts.js:247 / 1116) --

rendered as native <button> elements, so click handlers fire on Enter/Space:
keyboard-operable via Tab + Enter/Space.

Their :hover affordances (background/color/border-color shifts, each in a
dark-theme and a light-theme variant) had no :focus-visible mirrors, so
keyboard focus got only the UA default outline. css/style.css now carries
one :focus-visible rule per :hover rule (six total, covering both themes),
each adjacent to its :hover counterpart with byte-identical declarations
(same convention as the 285th-292nd runs).

Parity notes for S4:
- The later .rs-mode-btn.active, .top10-mode-btn.active and
  .trend-overlay-btn.active[data-series="..."] rules (specificity (0,2,0) or
  (0,3,0)) set the same mirrored props and override both the hover and the
  focus rule identically -> focus keeps hover's exact visual relation to
  .active; S4 skips such parity-identical rules (same mechanism as the
  292nd run's S4).
- :active is excluded as a transient press state (hover has the same
  relation).
- Mobile @media rules only touch padding/font-size for these classes, not
  the mirrored props (grep-verified at fix time); the static parser skips
  @media-inner rules anyway.
- No other rule in the stylesheet references these classes with
  background/color/border-color declarations (grep-verified at fix time).

Checks (all static):
  S1 all three classes render as native <button> elements in index.html
     (keyboard surface).
  S2 css/style.css has all six :focus-visible mirrors with the expected
     declarations.
  S3 each focus-visible block matches its hover block exactly (no drift).
  S4 each focus rule comes after its hover rule; no later compatible rule
     overrides the mirrored declarations for focus but not for hover
     (parity-identical .active rules sanctioned; :active excluded).

Usage:
  scripts/check_rs_top10_trend_btn_focus.py
  scripts/check_rs_top10_trend_btn_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "index.html")
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


# (hover selector, focus selector, mirrored props) pairs
PAIRS = [
    (".rs-mode-btn:hover", ".rs-mode-btn:focus-visible",
     ("background", "color")),
    ("[data-theme=\"light\"] .rs-mode-btn:hover",
     "[data-theme=\"light\"] .rs-mode-btn:focus-visible",
     ("background",)),
    (".top10-mode-btn:hover", ".top10-mode-btn:focus-visible",
     ("background", "border-color", "color")),
    ("[data-theme=\"light\"] .top10-mode-btn:hover",
     "[data-theme=\"light\"] .top10-mode-btn:focus-visible",
     ("background", "border-color", "color")),
    (".trend-overlay-btn:hover", ".trend-overlay-btn:focus-visible",
     ("background", "border-color", "color")),
    ("[data-theme=\"light\"] .trend-overlay-btn:hover",
     "[data-theme=\"light\"] .trend-overlay-btn:focus-visible",
     ("background", "border-color", "color")),
]

CLASSES = ("rs-mode-btn", "top10-mode-btn", "trend-overlay-btn")


def static_checks():
    html = open(HTML, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    rules = parse_rules(css)
    by_sel = {}
    for sel, decls, pos in rules:
        by_sel.setdefault(sel, []).append((decls, pos))

    # S1: native <button class="..."> render sites in index.html.
    s1_ok = True
    s1_detail = ""
    for cls in CLASSES:
        n = len(re.findall(r'<button class="%s' % re.escape(cls), html))
        if n < 1:
            s1_ok = False
            s1_detail = "no native <button> render site for .%s in index.html" % cls
            break
    check("S1 chart toggle buttons render as native <button> elements",
          s1_ok, s1_detail)

    # S2: the six :focus-visible mirrors exist with the expected declarations.
    s2_ok = True
    s2_detail = ""
    for hover_sel, focus_sel, props in PAIRS:
        decls = by_sel.get(focus_sel, [(None, -1)])[0][0]
        if decls is None or not all(p in decls for p in props):
            s2_ok = False
            s2_detail = "missing/incomplete: %s -> %r" % (focus_sel, decls)
            break
    check("S2 :focus-visible mirrors exist with expected declarations",
          s2_ok, s2_detail)

    # S3: each focus-visible block matches its hover block exactly.
    s3_ok = True
    s3_detail = ""
    for hover_sel, focus_sel, _ in PAIRS:
        fdecls = by_sel.get(focus_sel, [(None, -1)])[0][0]
        hdecls = by_sel.get(hover_sel, [(None, -1)])[0][0]
        if fdecls is None or hdecls is None or fdecls != hdecls:
            s3_ok = False
            s3_detail = "drift: %s focus=%r hover=%r" % (
                focus_sel, fdecls, hdecls)
            break
    check("S3 focus-visible declarations match hover exactly (no drift)",
          s3_ok, s3_detail)

    # S4: each focus rule comes after its hover rule; no later compatible
    # rule overrides the mirrored declarations for focus but not for
    # hover (parity-identical .active rules are sanctioned; :active is
    # excluded as transient).
    s4_ok = True
    s4_detail = ""
    for hover_sel, focus_sel, props in PAIRS:
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
            if not any(cls in sel for cls in CLASSES):
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
