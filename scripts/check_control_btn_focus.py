#!/usr/bin/env python3
"""Regression guard: control-btn family shows hover affordance on keyboard focus.

The 2026-10-31 10:00 PT run (291st review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; the
290th closed section-nav-link). Next per the audit: the control-btn
family -- the network section's twelve interactive controls (path-finder
toggle, all/primary/secondary filters, network-overflow menu toggle,
comp/PageRank/clustering/GER/verification/community heatmap toggles,
pvp-ring toggle), rendered in index.html as native
<button class="control-btn ..."> elements -> keyboard-operable via
Tab + Enter/Space.

The hover affordance (:hover { border-color: var(--accent);
color: var(--text-primary); }) had no :focus-visible mirror, so keyboard
focus got only the UA default outline. css/style.css now carries the
:focus-visible rule adjacent to its :hover counterpart with byte-identical
declarations (same convention as the 285th-290th runs). Both declarations
use theme vars (--accent, --text-primary) with no light-theme override for
this class, so the one rule covers both themes.

Parity notes for S4:
- The later `.control-btn.active` rule (specificity (0,2,0)) sets
  border-color: var(--accent) and color: var(--accent) and overrides both
  the focus and the hover rule identically (both are (0,2,0), earlier in
  the file). Since it treats hover and focus identically, focus keeps
  hover's exact visual relation to .active; S4 skips such
  parity-identical rules.
- The later `.control-btn.control-btn-disabled` rule (0,2,0) sets only
  opacity/cursor/text-decoration/border-style -- none of the mirrored
  props -- so no conflict.
- The later `.control-btn.control-btn-disabled:hover` rule (0,3,0) is
  hover-scoped: it neutralizes the hover affordance for disabled buttons
  but never touches the focus state. The disabled class is dormant (never
  rendered in index.html or applied in js/app.js), so no live element can
  sit in the focused-but-not-hovered disabled state; S4's genuine-drift
  criterion (a later rule overriding the focus declarations WITHOUT the
  same override of hover) is not triggered.

Checks (all static):
  S1 index.html renders native <button class="control-btn ..."> elements
     (keyboard surface).
  S2 css/style.css has the :focus-visible mirror with the expected
     declarations (border-color, color).
  S3 the focus-visible block matches the hover block exactly (no drift).
  S4 the focus rule comes after the hover rule; no later compatible rule
     overrides the mirrored declarations for focus but not for hover
     (:active excluded - transient press state with the sanctioned
     hover relation; parity-identical rules like .active excluded).

Usage:
  scripts/check_control_btn_focus.py
  scripts/check_control_btn_focus.py --static-only

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


# (focus selector, hover selector, expected props)
RULE_PAIRS = [
    (".control-btn:focus-visible",
     ".control-btn:hover",
     ("border-color", "color")),
]


def static_checks():
    html = open(HTML, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    rules = parse_rules(css)
    by_sel = {}
    for sel, decls, pos in rules:
        by_sel.setdefault(sel, []).append((decls, pos))

    # S1: native <button class="control-btn ..."> elements (keyboard surface).
    n_btns = len(re.findall(r'<button class="control-btn', html))
    s1 = n_btns >= 12
    check("S1 control-btn family renders as native <button> elements",
          s1, "" if s1 else "found %d buttons, expected >= 12" % n_btns)

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
    # declarations for focus but not for hover (parity-identical rules
    # such as .active are sanctioned; :active is excluded; the dormant
    # .control-btn-disabled:hover state guard is hover-scoped only).
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
            if "control-btn" not in sel:
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
