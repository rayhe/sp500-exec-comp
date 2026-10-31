#!/usr/bin/env python3
"""Regression guard: neo-smooth-btn / neo-compare-years-btn show hover
affordance on keyboard focus.

The 2026-10-31 11:30 PT run (292nd review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; the
291st closed the network control-btn family). Next per the audit: the
NEO detail-view toggle buttons --

  .neo-smooth-btn ("Smooth equity grants", data-action="toggle-smooth",
  js/app.js:10649) and .neo-compare-years-btn ("Compare FYs",
  data-action="toggle-sbs", js/app.js:10689) --

rendered as native <button> elements wired by click delegation
(querySelectorAll('[data-action="toggle-smooth"/"toggle-sbs"]'),
js/app.js:11630/11649) -> keyboard-operable via Tab + Enter/Space.

Their :hover affordance (color: var(--text); border-color: var(--accent);
border-style: solid -- dashed becomes solid on hover) had no
:focus-visible mirror, so keyboard focus got only the UA default outline.
css/style.css now carries one :focus-visible rule per :hover rule, each
adjacent to its :hover counterpart with byte-identical declarations
(same convention as the 285th-291st runs). All declarations use theme
vars (--text, --accent) with no light-theme override for either class,
so the two rules cover both themes.

Parity notes for S4:
- The later .neo-smooth-btn.active and .neo-compare-years-btn.active
  rules (specificity (0,2,0)) set color, border-color AND border-style --
  all three mirrored props -- and override both the focus and the hover
  rule identically (both are (0,2,0), earlier in the file). Since they
  treat hover and focus identically, focus keeps hover's exact visual
  relation to .active; S4 skips such parity-identical rules.
- No other rule in the stylesheet references either class (grep-verified
  at fix time), so there is nothing else that could drift one of the
  two states.

Checks (all static):
  S1 both buttons render as native <button> elements in js/app.js
     (keyboard surface).
  S2 css/style.css has both :focus-visible mirrors with the expected
     declarations (color, border-color, border-style).
  S3 each focus-visible block matches its hover block exactly (no drift).
  S4 each focus rule comes after its hover rule; no later compatible rule
     overrides the mirrored declarations for focus but not for hover
     (:active excluded - transient press state with the sanctioned
     hover relation; parity-identical .active rules excluded).

Usage:
  scripts/check_neo_btn_focus.py
  scripts/check_neo_btn_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(REPO, "js", "app.js")
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


# (class base, expected mirrored props)
BUTTON_CLASSES = [
    ("neo-smooth-btn", ("color", "border-color", "border-style")),
    ("neo-compare-years-btn", ("color", "border-color", "border-style")),
]


def static_checks():
    js = open(JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    rules = parse_rules(css)
    by_sel = {}
    for sel, decls, pos in rules:
        by_sel.setdefault(sel, []).append((decls, pos))

    # S1: native <button class="neo-smooth-btn"> /
    #     <button class="neo-compare-years-btn"> rendered in js/app.js.
    s1_ok = True
    s1_detail = ""
    for cls, _ in BUTTON_CLASSES:
        n = len(re.findall(r'<button class="%s"' % re.escape(cls), js))
        if n < 1:
            s1_ok = False
            s1_detail = "no native <button> render site for .%s in js/app.js" % cls
            break
    check("S1 both neo toggle buttons render as native <button> elements",
          s1_ok, s1_detail)

    # S2: the :focus-visible mirrors exist with the expected declarations.
    s2_ok = True
    s2_detail = ""
    for cls, props in BUTTON_CLASSES:
        focus_sel = "." + cls + ":focus-visible"
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
    for cls, _ in BUTTON_CLASSES:
        focus_sel = "." + cls + ":focus-visible"
        hover_sel = "." + cls + ":hover"
        fdecls = by_sel.get(focus_sel, [(None, -1)])[0][0]
        hdecls = by_sel.get(hover_sel, [(None, -1)])[0][0]
        if fdecls is None or hdecls is None or fdecls != hdecls:
            s3_ok = False
            s3_detail = "drift: .%s focus=%r hover=%r" % (cls, fdecls, hdecls)
            break
    check("S3 focus-visible declarations match hover exactly (no drift)",
          s3_ok, s3_detail)

    # S4: each focus rule comes after its hover rule; no later compatible
    # rule overrides the mirrored declarations for focus but not for
    # hover (parity-identical .active rules are sanctioned; :active is
    # excluded as transient).
    s4_ok = True
    s4_detail = ""
    for cls, props in BUTTON_CLASSES:
        focus_sel = "." + cls + ":focus-visible"
        hover_sel = "." + cls + ":hover"
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
            if cls not in sel:
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
