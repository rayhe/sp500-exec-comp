#!/usr/bin/env python3
"""Regression guard: NEO-panel filing link reveals on keyboard focus.

The 2026-10-26 14:00 PT run (234th review) completed the hover-only
reveal audit that the 223rd/225th/229th/233rd runs ran over the card
CTAs. The audit's last straggler was .neo-filing-link in the NEO
detail panel: a real <a> to the company's DEF 14A/10-K on EDGAR, so
keyboard-focusable, but it brightened (opacity 0.8 -> 1, underline)
only on :hover. Its sibling .row-filing-link in the main table already
carried a :focus-visible rule (opacity 1 + --accent ring), so the
detail-panel link was the inconsistent one. css/style.css now carries
.neo-filing-link:focus-visible { opacity: 1; text-decoration: underline;
outline: 2px solid var(--accent); outline-offset: 1px; }, matching the
hover affordance plus the site's focus ring.

Checks (all static):
  S1 js/app.js renders .neo-filing-link as an <a href> (keyboard
     surface), not a span/div.
  S2 css/style.css has .neo-filing-link:focus-visible with opacity: 1
     and the --accent outline, matching the hover underline.

Usage:
  scripts/check_neo_filing_link_focus.py
  scripts/check_neo_filing_link_focus.py --static-only

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
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    js = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: the NEO filing link is a real anchor (keyboard-focusable).
    # js/app.js builds it as: html += ' <a class="neo-filing-link" href="...'
    s1 = ('<a class="neo-filing-link" href="' in js)
    check("S1 .neo-filing-link is rendered as a keyboard-focusable <a>",
          s1, "" if s1 else "NEO filing link anchor markup missing in js/app.js")

    # S2: focus-visible reveal matching hover, plus the accent ring.
    matches = re.findall(r"\.neo-filing-link:focus-visible\s*\{([^}]*)\}", css)
    s2 = any("opacity: 1" in body and "text-decoration: underline" in body
             and "var(--accent)" in body for body in matches)
    check("S2 .neo-filing-link:focus-visible reveals at opacity 1 with accent ring",
          s2, "" if s2 else "focus-visible filing-link reveal missing")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
