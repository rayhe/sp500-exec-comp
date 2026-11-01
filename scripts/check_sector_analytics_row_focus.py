#!/usr/bin/env python3
"""Regression guard: sector-analytics rows show hover affordance on keyboard focus.

The 2026-11-01 02:30 PT run (300th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; the
299th closed the .sortable family). Next per the audit: the
.sector-analytics-row class -- the sector-analytics table rows, rendered
in js/app.js as <tr class="sector-analytics-row" ... tabindex="0"> and
wired with a tbody click listener plus a keydown listener
(Enter/Space -> row.click()) -> keyboard-operable via Tab + Enter/Space.

The hover affordance has TWO declarations (fixed rgba, not theme vars):
  dark:  .sector-analytics-row:hover { background: rgba(0,180,216,0.06); }
  light: [data-theme="light"] .sector-analytics-row:hover { background: rgba(0,0,0,0.03); }
Neither had a :focus-visible mirror, so keyboard focus got only the UA
default outline. css/style.css now carries both :focus-visible rules,
each placed adjacent to its :hover counterpart with byte-identical
declarations (the 261st-review path-finder-go convention: when the hover
decls are fixed values with a light-theme override, mirror each theme;
a single rule would tint one theme wrong). No mouse-behavior change.

Parity notes for S4: .sa-active (dark, (0,2,0)) sits after the dark
:hover rule (0,2,0) and overrides its background identically, so focus
keeps hover's relation -- sanctioned via the parity rule, same as the
.chip.active / scatter-preset-btn / sortable precedents. The light
.sa-active (0,3,0) sits after the light :hover rule (0,3,0) -- same
sanction. No :active rule exists for this class. The later
@media .sector-analytics-row td rule touches only padding, not the
mirrored background prop. .sa-sortable/.neo-sortable are distinct classes
and filtered out of the S4 scan by exact class membership (they have
their own focus rules, separate runs). The generic
[data-kbd-upgraded]:focus-visible ring rule does not apply here: the
row render sets tabindex="0", so js/app.js's kbd-upgrade helpers skip
these rows (continue on hasAttribute('tabindex')).

Checks (all static):
  S1 js/app.js renders <tr class="sector-analytics-row" ... tabindex="0">
     and wires tbody click + keydown (Enter/Space -> row.click()).
  S2 both :focus-visible mirrors exist with the expected declarations
     (dark + light).
  S3 each focus-visible block matches its hover block exactly (no drift).
  S4 each focus rule comes after its hover rule; no later compatible rule
     overrides the mirrored declarations for focus but not for hover
     (:active excluded; .sa-active sanctioned via parity).

Usage:
  scripts/check_sector_analytics_row_focus.py
  scripts/check_sector_analytics_row_focus.py --static-only

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
    (".sector-analytics-row:focus-visible",
     ".sector-analytics-row:hover",
     ("background",)),
    ('[data-theme="light"] .sector-analytics-row:focus-visible',
     '[data-theme="light"] .sector-analytics-row:hover',
     ("background",)),
]


def static_checks():
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    rules = parse_rules(css)
    by_sel = {}
    for sel, decls, pos in rules:
        by_sel.setdefault(sel, []).append((decls, pos))

    # S1: <tr class="sector-analytics-row" ... tabindex="0"> in js/app.js
    # (render string uses plain double quotes inside the JS single-quoted
    # literal; no backslash escapes -- 294th-run lesson: verify with raw
    # bytes, not tool-output rendering) + tbody click/keydown wiring.
    s1 = (('<tr class="sector-analytics-row' in js)
          and ('tabindex="0"' in js)
          and ("tbody.addEventListener('click'" in js)
          and ("tbody.addEventListener('keydown'" in js)
          and ("ev.key === 'Enter'" in js)
          and ("closest('.sector-analytics-row')" in js)
          and ("row.click()" in js))
    check("S1 tr.sector-analytics-row renders tabindex=0 with click+keydown wiring",
          s1, "" if s1 else "tr render or click/keydown wiring missing (js/app.js)")

    # S2: both :focus-visible mirrors exist with the expected declarations.
    s2_ok = True
    s2_detail = ""
    for focus_sel, _, props in RULE_PAIRS:
        decls = by_sel.get(focus_sel, [(None, -1)])[0][0]
        if decls is None or not all(p in decls for p in props):
            s2_ok = False
            s2_detail = "missing/incomplete: %s -> %r" % (focus_sel, decls)
            break
    check("S2 :focus-visible mirrors exist with expected declarations (dark+light)",
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

    # S4: focus rule after hover; no later rule overrides the mirrored
    # declarations for focus but not for hover (:active excluded;
    # .sa-active sanctioned via parity).
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
            # .neo-sortable do not hit the same element as
            # .sector-analytics-row.
            lclasses = required_classes(sel)
            if "sector-analytics-row" not in lclasses:
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
