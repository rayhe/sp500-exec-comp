#!/usr/bin/env python3
"""Regression guard: advanced-filters family shows hover affordance on keyboard focus.

The 2026-10-31 03:00 PT run (288th review) continued the keyboard-operable
surface audit from the 260th review's render-site triage (46 flagged
keyboard-operable :hover classes without :focus-visible mirrors;
.compare-clear-btn closed at the 287th). Next per the 260th-review priority
order: the advanced-filters family -- the primary disclosure toggle that
unlocks the whole advanced-filtering surface, its category accordions, and
its clear action.

Keyboard surfaces (all natively focusable; Tab + Enter/Space operable):
  .advanced-filters-toggle -- index.html:392 native <button
     id="advanced-filters-toggle"> with addEventListener('click') wiring at
     js/advanced-filters.js:183 (toggles the panel, aria-expanded).
  .af-cat-summary -- <summary> inside <details> (index.html:410/453/494);
     native summary is focusable and toggles on Enter/Space.
  .af-clear-btn -- index.html:523 native <button id="af-clear-btn"> with
     addEventListener('click') wiring at js/advanced-filters.js:422
     (clearAdvancedFilters).

Their :hover affordances had no :focus-visible mirrors, so keyboard focus got
only the UA default outline. css/style.css now carries five mirrors, each
adjacent to its :hover counterpart with byte-identical declarations:
  .advanced-filters-toggle:focus-visible (dark: border-color/color/background)
  [data-theme="light"] .advanced-filters-toggle:focus-visible (light)
  .af-cat-summary:focus-visible .af-cat-name (dark)
  [data-theme="light"] .af-cat-summary:focus-visible .af-cat-name (light)
  .af-clear-btn:focus-visible (fixed values, no light override -> one rule
     covers both themes)
No mouse-behavior change; the [aria-expanded="true"] state rules keep their
precedence over focus exactly as they do over hover (equal specificity,
later rule wins); none of the buttons is ever disabled, so no
:not(:disabled) parallels are needed.

Checks (all static):
  S1 the three classes render on natively keyboard-operable elements with
     click/activation wiring (keyboard surface).
  S2 all five :focus-visible mirrors exist with the expected declarations.
  S3 each focus-visible declaration block matches its hover counterpart
     exactly (no drift).
  S4 cascade order: each focus rule follows its hover rule with no later
     rule overriding the mirrored declarations (the aria-expanded state
     rules intentionally keep winning over both hover and focus).

Usage:
  scripts/check_af_btn_focus.py
  scripts/check_af_btn_focus.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, "index.html")
AF_JS = os.path.join(REPO, "js", "advanced-filters.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name
          + ((" - " + detail) if detail else ""))


def extract_decls(css, pattern):
    m = re.search(pattern, css)
    if not m:
        return None
    decls = {}
    for dm in re.finditer(r"([a-z-]+)\s*:\s*([^;]+);", m.group(1)):
        decls[dm.group(1).strip()] = dm.group(2).strip()
    return decls


# (name, hover selector pattern, focus selector pattern, mirrored decls)
MIRRORS = [
    ("advanced-filters-toggle",
     r"\.advanced-filters-toggle:hover\s*\{([^}]*)\}",
     r"\.advanced-filters-toggle:focus-visible\s*\{([^}]*)\}",
     {"border-color": "var(--accent)",
      "color": "var(--text-primary)",
      "background": "rgba(0,180,216,0.06)"}),
    ("advanced-filters-toggle-light",
     r"\[data-theme=\"light\"\] \.advanced-filters-toggle:hover\s*\{([^}]*)\}",
     r"\[data-theme=\"light\"\] \.advanced-filters-toggle:focus-visible\s*\{([^}]*)\}",
     {"border-color": "#0077b6",
      "background": "rgba(0,119,182,0.06)"}),
    ("af-cat-summary",
     r"\.af-cat-summary:hover \.af-cat-name\s*\{([^}]*)\}",
     r"\.af-cat-summary:focus-visible \.af-cat-name\s*\{([^}]*)\}",
     {"color": "var(--accent)"}),
    ("af-cat-summary-light",
     r"\[data-theme=\"light\"\] \.af-cat-summary:hover \.af-cat-name\s*\{([^}]*)\}",
     r"\[data-theme=\"light\"\] \.af-cat-summary:focus-visible \.af-cat-name\s*\{([^}]*)\}",
     {"color": "#0077b6"}),
    ("af-clear-btn",
     r"\.af-clear-btn:hover\s*\{([^}]*)\}",
     r"\.af-clear-btn:focus-visible\s*\{([^}]*)\}",
     {"border-color": "#fb923c",
      "color": "#fb923c",
      "background": "rgba(251,146,60,0.08)"}),
]


def static_checks():
    html = open(INDEX, encoding="utf-8").read()
    js = open(AF_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: native keyboard surfaces with click/activation wiring.
    s1a = ('<button class="advanced-filters-toggle" id="advanced-filters-toggle"'
           in html
           and "document.getElementById('advanced-filters-toggle')" in js
           and "addEventListener('click'" in js)
    s1b = (html.count('<summary class="af-cat-summary"') >= 1
           and '<details class="af-cat"' in html)
    s1c = ('<button class="af-clear-btn" id="af-clear-btn">' in html
           and "document.getElementById('af-clear-btn')" in js)
    s1 = s1a and s1b and s1c
    check("S1 AF family is keyboard-operable (native button/summary + wiring)",
          s1,
          "" if s1 else "missing surface: toggle=%s summary=%s clear=%s"
          % (s1a, s1b, s1c))

    # S2 + S3: mirrors exist and match hover exactly.
    all_s2 = True
    all_s3 = True
    s2_detail = []
    s3_detail = []
    for name, hpat, fpat, expected in MIRRORS:
        hover = extract_decls(css, hpat)
        focus = extract_decls(css, fpat)
        if focus is None or any(focus.get(k) != v for k, v in expected.items()):
            all_s2 = False
            s2_detail.append(name)
        if focus is None or hover is None or focus != hover:
            all_s3 = False
            s3_detail.append(name)
    check("S2 five :focus-visible mirrors carry expected declarations",
          all_s2, "" if all_s2 else "missing/incomplete: %s" % s2_detail)
    check("S3 focus-visible declarations match hover exactly",
          all_s3, "" if all_s3 else "drift on: %s" % s3_detail)

    # S4: each focus rule follows its hover rule; no same-theme rule targeting
    # the same element later in the file may override a mirrored declaration.
    # Sanctioned exceptions (focus/hover parity preserved):
    #  - [aria-expanded="true"] state rules: equal specificity, later than
    #    BOTH hover and focus, so they win over both equally (the 280th S4
    #    convention).
    #  - cross-theme rules ([data-theme="light"] when checking a dark
    #    mirror and vice versa) do not apply in the mirror's theme.
    # Descendant rules (e.g. .advanced-filters-toggle .af-count-badge) target
    # a different element and are never overrides.
    s4 = True
    s4_detail = ""
    for name, hpat, fpat, expected in MIRRORS:
        hover_m = re.search(hpat, css)
        focus_m = re.search(fpat, css)
        if not hover_m or not focus_m or focus_m.start() < hover_m.start():
            s4 = False
            s4_detail = "order violation on %s" % name
            break
        light = name.endswith("-light")
        cls = name.split("-light")[0]
        subject = ".af-cat-name" if cls == "af-cat-summary" else "." + cls
        focus_end = css.find("}", focus_m.start()) + 1
        later = css[focus_end:]
        for rm in re.finditer(r"([^{}]+)\{([^}]*)\}", later):
            decls = rm.group(2)
            selectors = [sel.strip() for sel in rm.group(1).split(",")]
            for sel in selectors:
                rule_light = sel.startswith('[data-theme="light"]')
                if rule_light != light:
                    continue
                sel_body = sel[len('[data-theme="light"]'):].strip()
                # the element the rule targets = last compound selector
                target = re.split(r"\s+|[>+~]", sel_body)[-1].strip()
                # same element only if target is exactly the subject plus
                # optional attribute/pseudo-class chains (no descendant)
                if not re.fullmatch(
                        re.escape(subject)
                        + r"(\[[^\]]*\]|::?[a-zA-Z-]+(\([^)]*\))?)*",
                        target):
                    continue
                if '[aria-expanded="true"]' in target:
                    continue  # sanctioned: wins over hover and focus equally
                if any(re.search(r"(^|;)\s*%s\s*:" % re.escape(d), decls)
                       for d in expected):
                    s4 = False
                    s4_detail = "later override on %s: %s" % (name, sel[:80])
                    break
            if not s4:
                break
        if not s4:
            break
    check("S4 focus rules follow hover; no unsanctioned later override",
          s4, s4_detail)


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
