#!/usr/bin/env python3
"""Regression guard: detail-panel action buttons show hover affordance on keyboard focus.

The 2026-10-30 14:00 PT run (281st review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors;
.cf-normalize-btn/.cf-transpose-btn closed at the 280th). Next highest-value
native-button surface: .detail-network-btn and .detail-table-btn -- the
company-detail and comparison-tray "Show in Network" / "Find in Table" action
buttons, rendered by js/app.js as native <button> elements
(with onclick attributes in the detail panel and addEventListener('click')
wiring in the comparison tray cards) -> keyboard-operable via Tab +
Enter/Space.

The hover affordances (.detail-network-btn:hover: background
rgba(0,180,216,0.25), color #fff, border-color var(--accent-hover);
.detail-table-btn:hover: background rgba(161,161,170,0.25), color #fff,
border-color #d4d4d8) had no :focus-visible mirrors, so keyboard focus got
only the UA default outline. css/style.css now carries one :focus-visible
rule per button, placed adjacent to its :hover rule with byte-identical
declarations.

Checks (all static):
  S1 js/app.js renders both as native <button> elements with click wiring
     (keyboard surface).
  S2 css/style.css has both :focus-visible mirrors carrying
     background + border-color.
  S3 each focus-visible declaration block matches its hover counterpart
     exactly (no drift).
  S4 the focus rules come after their hover rules and no later rule
     overrides the mirrored declarations, so the mirror is actually
     visible on keyboard focus.

Usage:
  scripts/check_detail_btns_focus.py
  scripts/check_detail_btns_focus.py --static-only

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


def find_rule(css, selector):
    """Find a standalone rule by selector. Returns (declarations dict, pos)
    or (None, -1)."""
    for m in re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", css):
        decls = {}
        for dm in re.finditer(r"([a-z-]+)\s*:\s*([^;]+);", m.group(1)):
            decls[dm.group(1).strip()] = dm.group(2).strip()
        return decls, m.start()
    return None, -1


PAIRS = [
    (".detail-network-btn:hover", ".detail-network-btn:focus-visible"),
    (".detail-table-btn:hover", ".detail-table-btn:focus-visible"),
]


def static_checks():
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native <button> renders with click wiring (keyboard surface).
    s1 = ("'<button class=\"detail-network-btn\"" in js
          and "'<button class=\"detail-table-btn\"" in js
          and "netBtn.addEventListener('click'" in js
          and "tableBtn.addEventListener('click'" in js
          and 'onclick="if(window.focusNetworkNode)' in js)
    check("S1 detail action buttons are native <button> with click wiring",
          s1, "" if s1 else "button render or click wiring missing in js/app.js")

    # S2: both :focus-visible mirrors exist carrying background + border-color.
    s2_ok = True
    s2_detail = ""
    for _, focus_sel in PAIRS:
        decls, _ = find_rule(css, focus_sel)
        if decls is None or "background" not in decls or "border-color" not in decls:
            s2_ok = False
            s2_detail = "missing/incomplete: %s -> %r" % (focus_sel, decls)
    check("S2 both :focus-visible mirrors carry background/border-color",
          s2_ok, s2_detail)

    # S3: each focus-visible block matches its hover counterpart exactly.
    s3_ok = True
    s3_detail = ""
    for hover_sel, focus_sel in PAIRS:
        hover_decls, _ = find_rule(css, hover_sel)
        focus_decls, _ = find_rule(css, focus_sel)
        if hover_decls is None or focus_decls is None or focus_decls != hover_decls:
            s3_ok = False
            s3_detail = "drift %s: focus=%r hover=%r" % (focus_sel, focus_decls, hover_decls)
    check("S3 focus-visible declarations match hover exactly (no drift)",
          s3_ok, s3_detail)

    # S4: focus rules come right after hover rules; no later rule overrides
    # the mirrored declarations.
    s4_ok = True
    s4_detail = ""
    for hover_sel, focus_sel in PAIRS:
        _, hover_pos = find_rule(css, hover_sel)
        _, focus_pos = find_rule(css, focus_sel)
        base = hover_sel.replace(":hover", "")
        if hover_pos == -1 or focus_pos == -1 or not (hover_pos < focus_pos):
            s4_ok = False
            s4_detail = "focus rule not after hover for %s (hover=%d focus=%d)" % (
                focus_sel, hover_pos, focus_pos)
            continue
        # Any later rule whose selector mentions the class and sets one of the
        # mirrored declarations would clobber the mirror.
        for m in re.finditer(r'([^{}]+?)\{([^}]*)\}', css):
            sel = m.group(1)
            if base.lstrip(".") not in sel or m.start() <= focus_pos:
                continue
            body = m.group(2)
            for prop in ("background", "border-color", "color"):
                if re.search(r"(?<![a-z-])" + prop + r"\s*:", body):
                    s4_ok = False
                    s4_detail = "later rule overrides %s on %s: %r" % (
                        prop, base, sel.strip()[:80])
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
