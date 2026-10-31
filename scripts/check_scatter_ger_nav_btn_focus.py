#!/usr/bin/env python3
"""Regression guard: scatter GER nav buttons show hover affordance on keyboard focus.

The 2026-10-30 22:00 PT run (285th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors;
25 remained after .ger-scatter-nav closed at the 282nd). Next per the
260th-review priority order: .scatter-ger-nav-btn -- the scatter chart's
"Dive into GER chart" nav strip buttons (top-5 GER tickers + "View all"),
rendered by _renderScatterGERNav in js/charts.js as native <button>
elements with addEventListener('click') wiring -> keyboard-operable via
Tab + Enter/Space.

The hover affordances had no :focus-visible mirrors, so keyboard focus got
only the UA default outline:
  base                                    : transform translateY(-1px)
  .ger-risk-critical / -high / -elevated /
  -moderate / .scatter-ger-nav-all        : background + border-color
css/style.css now carries one :focus-visible rule per hover rule, placed
adjacent to its :hover counterpart with byte-identical declarations. The
declarations are fixed rgba/transform values with no light-theme override,
so the six rules cover both themes (same convention as the
262nd/280th/281st/282nd runs).

Checks (all static):
  S1 js/charts.js renders native <button class="scatter-ger-nav-btn">
     elements (plus the scatter-ger-nav-all "View all" variant) with
     click wiring (keyboard surface).
  S2 css/style.css has all six :focus-visible mirrors carrying the
     expected declarations (base: transform; variants: background +
     border-color).
  S3 each focus-visible declaration block matches its hover counterpart
     exactly (no drift).
  S4 each focus rule comes after its hover rule and no later compatible
     rule overrides the mirrored declarations (:active press-state rules
     are excluded - the hover affordance has the same relationship with
     :active for mouse users).

Usage:
  scripts/check_scatter_ger_nav_btn_focus.py
  scripts/check_scatter_ger_nav_btn_focus.py --static-only

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


# (focus selector, hover selector, expected props)
RULE_PAIRS = [
    (".scatter-ger-nav-btn:focus-visible",
     ".scatter-ger-nav-btn:hover",
     ("transform",)),
    (".scatter-ger-nav-btn.ger-risk-critical:focus-visible",
     ".scatter-ger-nav-btn.ger-risk-critical:hover",
     ("background", "border-color")),
    (".scatter-ger-nav-btn.ger-risk-high:focus-visible",
     ".scatter-ger-nav-btn.ger-risk-high:hover",
     ("background", "border-color")),
    (".scatter-ger-nav-btn.ger-risk-elevated:focus-visible",
     ".scatter-ger-nav-btn.ger-risk-elevated:hover",
     ("background", "border-color")),
    (".scatter-ger-nav-btn.ger-risk-moderate:focus-visible",
     ".scatter-ger-nav-btn.ger-risk-moderate:hover",
     ("background", "border-color")),
    (".scatter-ger-nav-btn.scatter-ger-nav-all:focus-visible",
     ".scatter-ger-nav-btn.scatter-ger-nav-all:hover",
     ("background", "border-color")),
]


def static_checks():
    js = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    rules = parse_rules(css)
    by_sel = {}
    for sel, decls, pos in rules:
        by_sel.setdefault(sel, []).append((decls, pos))

    # S1: native <button> render with click wiring (keyboard surface).
    s1 = (("btn.className = 'scatter-ger-nav-btn';" in js)
          and ("viewAllBtn.className = 'scatter-ger-nav-btn scatter-ger-nav-all';" in js)
          and ("btn.addEventListener('click'" in js)
          and ("viewAllBtn.addEventListener('click'" in js)
          and ("_renderScatterGERNav" in js))
    check("S1 scatter-ger-nav-btn buttons are native <button> with click wiring",
          s1, "" if s1 else "button render or click wiring missing in js/charts.js")

    # S2: all six :focus-visible mirrors exist with expected declarations.
    s2_ok = True
    s2_detail = ""
    for focus_sel, _, props in RULE_PAIRS:
        decls = by_sel.get(focus_sel, [(None, -1)])[0][0]
        if decls is None or not all(p in decls for p in props):
            s2_ok = False
            s2_detail = "missing/incomplete: %s -> %r" % (focus_sel, decls)
            break
    check("S2 six :focus-visible mirrors exist with expected declarations",
          s2_ok, s2_detail)

    # S3: each focus-visible block matches its hover counterpart exactly.
    s3_ok = True
    s3_detail = ""
    for focus_sel, hover_sel, _ in RULE_PAIRS:
        fdecls = by_sel.get(focus_sel, [(None, -1)])[0][0]
        hdecls = by_sel.get(hover_sel, [(None, -1)])[0][0]
        if fdecls is None or hdecls is None or fdecls != hdecls:
            s3_ok = False
            s3_detail = "drift: %s focus=%r hover=%r" % (focus_sel, fdecls, hdecls)
            break
    check("S3 focus-visible declarations match hover exactly (no drift)",
          s3_ok, s3_detail)

    # S4: each focus rule comes after its hover rule; no later compatible
    # rule overrides the mirrored declarations (:active excluded).
    s4_ok = True
    s4_detail = ""
    for focus_sel, hover_sel, props in RULE_PAIRS:
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
        fclasses = required_classes(focus_sel)
        for sel, decls, pos in rules:
            if pos <= fpos:
                continue
            if "scatter-ger-nav-btn" not in sel:
                continue
            if ":active" in sel:
                continue  # transient press state; hover has the same relation
            # Only rules that can hit the same element (compatible class sets).
            lclasses = required_classes(sel)
            if not (lclasses <= fclasses or fclasses <= lclasses):
                continue
            if specificity(sel) < fspec:
                continue
            for prop in props:
                if prop in decls:
                    s4_ok = False
                    s4_detail = ("later rule overrides %s on %s: %r"
                                 % (prop, focus_sel, sel[:80]))
                    break
            if not s4_ok:
                break
        if not s4_ok:
            break
    check("S4 focus rules follow hover; no later override of mirrored decls",
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
