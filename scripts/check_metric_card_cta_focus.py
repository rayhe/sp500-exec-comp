#!/usr/bin/env python3
"""Regression guard: metric-card CTA text reveals on keyboard focus.

The 2026-10-26 11:30 PT run (233rd review) completed the touch/keyboard
CTA-reveal audit started by the 223rd (metric touch), 225th (insight
touch), and 229th (trend touch/focus) runs. Insight and trend cards
already revealed their CTA hints on :focus-visible, but the metric
cards -- full keyboard surfaces since the interactive-metric-cards work
(tabindex="0", role="button", Enter/Space keydown, :focus-visible ring
in js/app.js) -- revealed .metric-card-cta only on :hover (and on
touch via the (hover: none) media query). A keyboard user tabbing to a
metric card saw the focus ring but not the action label ("Sort by
compensation ->" etc.), so the card's purpose was invisible exactly
when it had focus. css/style.css now carries a
.metric-card:focus-visible .metric-card-cta rule (opacity 1, accent
color, with the light-theme #0077b6 override matching the hover rule).

Checks (all static):
  S1 metric cards are keyboard surfaces in js/app.js: tabindex="0",
     role="button", and an Enter/Space keydown handler on the card.
  S2 css/style.css has .metric-card:focus-visible .metric-card-cta
     with opacity: 1, in both the base rule and the light-theme rule.

Usage:
  scripts/check_metric_card_cta_focus.py              # static checks
  scripts/check_metric_card_cta_focus.py --static-only

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

    # S1: metric-card keyboard wiring in the interactive-metric-cards block.
    s1 = ("card.setAttribute('tabindex', '0')" in js
          and "card.setAttribute('role', 'button')" in js
          and "ctaEl.className = 'metric-card-cta'" in js
          and "card.addEventListener('keydown'" in js
          and "e.key === 'Enter' || e.key === ' '" in js)
    check("S1 metric cards are tabindex=0 buttons with Enter/Space keydown",
          s1, "" if s1 else "metric-card keyboard wiring missing or altered")

    # S2: focus-visible CTA reveal, base + light-theme, matching hover.
    # (search all matches: the light-theme single-line rule precedes the
    # base rule in file order and matches the same selector tail.)
    matches = re.findall(r"\.metric-card:focus-visible \.metric-card-cta\s*\{([^}]*)\}", css)
    s2 = any("opacity: 1" in body and "var(--accent)" in body for body in matches)
    check("S2 .metric-card:focus-visible .metric-card-cta reveals at opacity 1",
          s2, "" if s2 else "focus-visible CTA reveal missing")
    s2b = ('[data-theme="light"] .metric-card:focus-visible .metric-card-cta { color: #0077b6; }' in css)
    check("S2b light-theme focus-visible CTA color matches hover (#0077b6)",
          s2b, "" if s2b else "light-theme focus-visible CTA color missing")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
