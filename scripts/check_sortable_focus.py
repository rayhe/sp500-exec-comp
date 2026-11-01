#!/usr/bin/env python3
"""Regression guard: sortable table headers show hover affordance on keyboard focus.

The 2026-11-01 02:00 PT run (299th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; the
298th closed the .kbd-hint family). Next per the audit: the .sortable
class -- the main data-table column headers, rendered in index.html as
native <th class="sortable" tabindex="0"> and wired in js/app.js with
click + keydown (Enter/Space) -> keyboard-operable via Tab + Enter/Space.

The hover affordance (thead th.sortable:hover { color: var(--text-primary); })
had no :focus-visible mirror, so keyboard focus got only the UA default
outline. css/style.css now carries the :focus-visible rule adjacent to its
:hover counterpart with byte-identical declarations (same convention as
the 285th-298th runs). The mirrored value uses the theme-aware
var(--text-primary), so one rule covers both themes.

Parity notes for S4: no :active rule exists for thead th.sortable; no
light-theme override touches th.sortable's color; the later
thead th.sorted-asc/desc::after rules target the sort-indicator pseudo
element (different class), not the mirrored color prop. .neo-sortable /
.sa-sortable / .sector-corr-sortable are distinct classes and filtered out
of the S4 scan by exact class membership (neo-sortable headers are
click-only surfaces with no tabindex/keydown wiring, so they were not in
the 260th audit's flagged keyboard-operable set).

Checks (all static):
  S1 index.html renders <th class="sortable" ... tabindex="0"> and js/app.js
     wires click + keydown (Enter/Space) on th.sortable (keyboard surface).
  S2 css/style.css has the :focus-visible mirror with the expected
     declarations (color).
  S3 the focus-visible block matches the hover block exactly (no drift).
  S4 the focus rule comes after the hover rule; no later compatible rule
     overrides the mirrored declarations for focus but not for hover
     (:active excluded - transient press state with the sanctioned
     hover relation).

Usage:
  scripts/check_sortable_focus.py
  scripts/check_sortable_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(REPO, "index.html")
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
    ("thead th.sortable:focus-visible",
     "thead th.sortable:hover",
     ("color",)),
]


def static_checks():
    html = open(INDEX_HTML, encoding="utf-8").read()
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    rules = parse_rules(css)
    by_sel = {}
    for sel, decls, pos in rules:
        by_sel.setdefault(sel, []).append((decls, pos))

    # S1: <th class="sortable" ... tabindex="0"> in index.html + click/keydown
    # wiring on th.sortable in js/app.js.
    s1 = (('<th class="sortable"' in html)
          and ('tabindex="0"' in html)
          and ("querySelectorAll('th.sortable')" in js)
          and ("addEventListener('click'" in js)
          and ("addEventListener('keydown'" in js)
          and ("e.key === 'Enter'" in js))
    check("S1 th.sortable renders with tabindex=0 and click+keydown wiring",
          s1, "" if s1 else "th render or click/keydown wiring missing (index.html/js/app.js)")

    # S2: the :focus-visible mirror exists with the expected declarations.
    s2_ok = True
    s2_detail = ""
    for focus_sel, _, props in RULE_PAIRS:
        decls = by_sel.get(focus_sel, [(None, -1)])[0][0]
        if decls is None or not all(p in decls for p in props):
            s2_ok = False
            s2_detail = "missing/incomplete: %s -> %r" % (focus_sel, decls)
            break
    check("S2 :focus-visible mirror exists with expected declarations",
          s2_ok, s2_detail)

    # S3: focus-visible block matches the hover block exactly.
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

    # S4: focus rule after hover; no later rule overrides the mirrored
    # declarations for focus but not for hover (:active excluded).
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
            # Exact class membership: distinct classes like .sa-sortable /
            # .neo-sortable / .sector-corr-sortable do not hit the same
            # element as .sortable.
            lclasses = required_classes(sel)
            if "sortable" not in lclasses:
                continue
            if ":active" in sel:
                continue  # transient press state; hover has the same relation
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
    check("S4 focus rule follows hover; no unsanctioned later override",
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
