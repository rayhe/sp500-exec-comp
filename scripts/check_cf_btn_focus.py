#!/usr/bin/env python3
"""Regression guard: community-flow normalize/transpose buttons show hover affordance on keyboard focus.

The 2026-10-30 11:30 PT run (280th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors; .pagination-btn
closed at the 279th). Next highest-value native-button surface:
.cf-normalize-btn and .cf-transpose-btn -- the community-flow matrix controls
on the network tab ("# Raw / % Row / % Col / +/- Diff" cycle toggle and the
transpose toggle), rendered by js/network.js _renderCommunityFlowMatrix
(native <button> elements, addEventListener('click') -> keyboard-operable via
Tab + Enter/Space).

The hover affordances (dark: background rgba(168,85,247,0.18),
border-color rgba(168,85,247,0.5); light: background rgba(124,58,237,0.12),
border-color rgba(124,58,237,0.4)) had no :focus-visible mirrors, so keyboard
focus got only the UA default outline. css/style.css now carries four
:focus-visible rules (dark + light for each button) mirroring the hover
declarations exactly, placed adjacent to each :hover rule and BEFORE the
state rules (.cf-norm-active / .cf-norm-col / .cf-norm-diff /
.cf-transpose-active), so active-state styling still wins over focus exactly
as it wins over hover (equal specificity, later rule wins).

Checks (all static):
  S1 js/network.js renders both as native <button> elements with click
     listeners (keyboard surface).
  S2 css/style.css has all four :focus-visible mirrors carrying
     background + border-color.
  S3 each focus-visible declaration block matches its hover counterpart
     exactly (no drift), dark and light themes.
  S4 cascade order: the state rules (.cf-norm-active, .cf-transpose-active)
     still come after the focus rules, so active styling still wins over
     focus, exactly as it wins over hover.

Usage:
  scripts/check_cf_btn_focus.py
  scripts/check_cf_btn_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK_JS = os.path.join(REPO, "js", "network.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name
          + ((" - " + detail) if detail else ""))


def find_rule(css, selector, skip_light_prefix=True):
    """Find a standalone rule by selector. Looks at the ~80 chars before the
    match; when skip_light_prefix is True, skips matches whose selector is
    prefixed with [data-theme="light"] (the light variant), so dark rules are
    found even when a comment block sits between the previous rule's close and
    this selector (the dark :focus-visible rules carry such a comment)."""
    for m in re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", css):
        tail = css[max(0, m.start() - 80):m.start()]
        if skip_light_prefix and '[data-theme="light"]' in tail:
            continue
        decls = {}
        for dm in re.finditer(r"([a-z-]+)\s*:\s*([^;]+);", m.group(1)):
            decls[dm.group(1).strip()] = dm.group(2).strip()
        return decls, m.start()
    return None, -1


PAIRS = [
    # (dark hover selector, dark focus selector, light hover selector, light focus selector)
    (".cf-normalize-btn:hover", ".cf-normalize-btn:focus-visible",
     '[data-theme="light"] .cf-normalize-btn:hover',
     '[data-theme="light"] .cf-normalize-btn:focus-visible'),
    (".cf-transpose-btn:hover", ".cf-transpose-btn:focus-visible",
     '[data-theme="light"] .cf-transpose-btn:hover',
     '[data-theme="light"] .cf-transpose-btn:focus-visible'),
]


def static_checks():
    js = open(NETWORK_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> elements with click wiring (keyboard surface).
    s1 = ("'<button class=\"cf-normalize-btn" in js
          and "'<button class=\"cf-transpose-btn" in js
          and "normBtn.addEventListener('click'" in js
          and "transposeBtn.addEventListener('click'" in js)
    check("S1 cf-normalize-btn/cf-transpose-btn are native <button> with click wiring",
          s1, "" if s1 else "button render or click wiring missing in js/network.js")

    # S2: all four :focus-visible mirrors exist carrying background + border-color.
    s2_ok = True
    s2_detail = ""
    for _, focus_sel, _, light_focus_sel in PAIRS:
        dark_focus, _ = find_rule(css, focus_sel)
        light_focus, _ = find_rule(css, light_focus_sel, skip_light_prefix=False)
        for sel, decls in ((focus_sel, dark_focus), (light_focus_sel, light_focus)):
            if decls is None or "background" not in decls or "border-color" not in decls:
                s2_ok = False
                s2_detail = "missing/incomplete: %s -> %r" % (sel, decls)
    check("S2 four :focus-visible mirrors carry background/border-color",
          s2_ok, s2_detail)

    # S3: each focus-visible block matches its hover counterpart exactly.
    s3_ok = True
    s3_detail = ""
    for hover_sel, focus_sel, light_hover_sel, light_focus_sel in PAIRS:
        dark_hover, _ = find_rule(css, hover_sel)
        dark_focus, _ = find_rule(css, focus_sel)
        light_hover, _ = find_rule(css, light_hover_sel, skip_light_prefix=False)
        light_focus, _ = find_rule(css, light_focus_sel, skip_light_prefix=False)
        if dark_hover is None or dark_focus is None or dark_focus != dark_hover:
            s3_ok = False
            s3_detail = "dark drift %s: focus=%r hover=%r" % (focus_sel, dark_focus, dark_hover)
        if light_hover is None or light_focus is None or light_focus != light_hover:
            s3_ok = False
            s3_detail = "light drift %s: focus=%r hover=%r" % (light_focus_sel, light_focus, light_hover)
    check("S3 focus-visible declarations match hover exactly (dark + light)",
          s3_ok, s3_detail)

    # S4: state rules still come after the focus rules (active wins over focus).
    s4_ok = True
    s4_detail = ""
    for _, focus_sel, _, light_focus_sel in PAIRS:
        base = focus_sel.replace(":focus-visible", "")
        _, dark_focus_pos = find_rule(css, focus_sel)
        # First state rule for this button, e.g. ".cf-normalize-btn.cf-norm-active".
        m_state = re.search(re.escape(base) + r"\.cf-[a-z-]+\s*\{", css)
        dark_state_pos = m_state.start() if m_state else -1
        _, light_focus_pos = find_rule(css, light_focus_sel, skip_light_prefix=False)
        m_lstate = re.search(re.escape('[data-theme="light"] ' + base) + r"\.cf-[a-z-]+\s*\{", css)
        light_state_pos = m_lstate.start() if m_lstate else -1
        if dark_state_pos == -1 or dark_focus_pos == -1 or not (dark_focus_pos < dark_state_pos):
            s4_ok = False
            s4_detail = "dark state rule not after focus for %s (focus=%d state=%d)" % (
                focus_sel, dark_focus_pos, dark_state_pos)
        if light_state_pos == -1 or light_focus_pos == -1 or not (light_focus_pos < light_state_pos):
            s4_ok = False
            s4_detail = "light state rule not after focus for %s (focus=%d state=%d)" % (
                light_focus_sel, light_focus_pos, light_state_pos)
    check("S4 state rules still win over focus in cascade",
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
