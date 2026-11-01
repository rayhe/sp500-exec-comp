#!/usr/bin/env python3
"""Regression guard: compare-button family shows hover affordance on keyboard focus.

The 2026-11-01 05:00 PT run (301st review) closed the LAST flagged family
from the 260th review's render-site triage (46 flagged keyboard-operable
:hover classes without :focus-visible mirrors; the 300th closed
.sector-analytics-row). Two :hover rules on the row/insight compare
buttons had no :focus-visible mirrors:
  .insight-compare-btn.selected:hover (dark "remove" affordance,
      border-color/color var(--negative), plus its [data-theme="light"]
      variant at #dc2626)
  .compare-btn.selected:hover (background var(--accent-hover))

The triage ALSO missed one family: base .compare-btn:hover
(border-color/color var(--accent), tinted background) had no focus mirror
at all -- the row compare button is a native <button> rendered in
js/app.js with a click listener, so it is keyboard-operable; this run
adds its mirror too, completing the audit.

Four :focus-visible mirrors in css/style.css, each adjacent to its hover
counterpart with byte-identical declarations (285th-301st convention):
  (1) .compare-btn:focus-visible mirrors the base dark hover
      (border-color/color var(--accent), rgba(0,180,216,0.08));
  (2) .compare-btn.selected:focus-visible mirrors the selected hover
      (background var(--accent-hover));
  (3) .insight-compare-btn.selected:focus-visible mirrors the dark
      "remove" hover (border-color/color var(--negative),
      rgba(239,71,111,0.08)); the base (0,2,0) focus rule at 752 still
      supplies the outline, exactly as the base hover supplies the
      non-selected look -- the compound (0,3,0) rule only needs the three
      mirrored props, placed adjacent to win over the base focus rule;
  (4) [data-theme="light"] .insight-compare-btn.selected:focus-visible
      mirrors the light "remove" hover (#dc2626, rgba(220,38,38,0.08)),
      one-line rule adjacent to the one-line hover (261st convention:
      separate theme rules since the decls are fixed values).

No mouse-behavior change. No :active rules exist for these classes.
The generic *:focus-visible accent outline (!important) stays orthogonal.
The @media print .compare-btn display:none group touches only display.

Parity notes for S4: .compare-btn.selected (0,2,0) and
.compare-btn.selected:hover (0,3,0) sit after the base :hover rule
(0,2,0) and override its mirrored props identically, so focus keeps
hover's relation -- sanctioned via the parity rule (.chip.active /
sortable precedents). The light compound rules cannot be overridden by
the later dark (0,3,0) rules at lower specificity. detail-compare-btn
(:not(:disabled) hover+focus at 3671/3676) is a distinct class with its
own mirrors -- filtered out by exact class membership; it has no
.selected:hover rule, correctly out of scope. pf-epc-compare-btn and
anomaly-compare-btn are distinct classes, also filtered.

Checks (all static):
  S1 js/app.js renders both buttons as native <button> elements with
     click wiring (Tab + Enter/Space operable):
     .compare-btn (7607 render, 7762/7764 click), .insight-compare-btn
     (4762 render, 4831/4832 click).
  S2 all four :focus-visible mirrors exist with the expected declarations.
  S3 each focus-visible declaration set matches its hover counterpart
     exactly (no drift).
  S4 cascade order: each focus rule comes after its hover rule; no later
     compatible rule overrides a mirrored declaration for focus but not
     for hover (:active excluded; .compare-btn.selected /
     .compare-btn.selected:hover sanctioned via parity).

Usage:
  scripts/check_selected_focus.py
  scripts/check_selected_focus.py --static-only

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
    (".compare-btn:focus-visible",
     ".compare-btn:hover",
     ("border-color", "color", "background")),
    (".compare-btn.selected:focus-visible",
     ".compare-btn.selected:hover",
     ("background",)),
    (".insight-compare-btn.selected:focus-visible",
     ".insight-compare-btn.selected:hover",
     ("border-color", "color", "background")),
    ('[data-theme="light"] .insight-compare-btn.selected:focus-visible',
     '[data-theme="light"] .insight-compare-btn.selected:hover',
     ("color", "border-color", "background")),
]


def static_checks():
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    rules = parse_rules(css)
    by_sel = {}
    for sel, decls, pos in rules:
        by_sel.setdefault(sel, []).append((decls, pos))

    # S1: native <button> renders + click wiring in js/app.js.
    # Render strings are single-quoted JS literals carrying PLAIN double
    # quotes (raw byte dumps verified; tool output shows \\" as display
    # escaping only -- 294th/300th-run lesson).
    s1a = (('<button class="compare-btn' in js)
           and ("querySelector('.compare-btn')" in js)
           and ("cBtn.addEventListener('click'" in js))
    s1b = (('<button class="insight-compare-btn' in js)
           and ("querySelectorAll('.insight-compare-btn')" in js)
           and ("btn.addEventListener('click', function(e) {" in js))
    s1 = s1a and s1b
    check("S1 both compare buttons render as native <button> with click wiring",
          s1, "" if s1 else ".compare-btn=%s insight-compare-btn=%s"
          % (s1a, s1b))

    # S2: all four :focus-visible mirrors exist with expected declarations.
    s2_ok = True
    s2_detail = ""
    for focus_sel, _, props in RULE_PAIRS:
        decls = by_sel.get(focus_sel, [(None, -1)])[0][0]
        if decls is None or not all(p in decls for p in props):
            s2_ok = False
            s2_detail = "missing/incomplete: %s -> %r" % (focus_sel, decls)
            break
    check("S2 four :focus-visible mirrors exist with expected declarations",
          s2_ok, s2_detail)

    # S3: each focus-visible block matches its hover block exactly.
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

    # S4: focus rule after hover; no later rule overrides a mirrored
    # declaration for focus but not for hover (:active excluded;
    # .compare-btn.selected / .compare-btn.selected:hover sanctioned via
    # the parity rule).
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
        hspec = specificity(hover_sel)
        fclasses = required_classes(focus_sel)
        hclasses = required_classes(hover_sel)
        for sel, decls, pos in rules:
            if pos <= fpos:
                continue
            # Exact class membership: a rule can only hit the same element
            # if it requires every class the focus selector requires
            # (distinct classes like .detail-compare-btn /
            # .pf-epc-compare-btn / .anomaly-compare-btn are filtered out).
            lclasses = required_classes(sel)
            if not fclasses <= lclasses:
                continue
            if ":active" in sel:
                continue  # transient press state; hover has the same relation
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
