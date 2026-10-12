#!/usr/bin/env python3
"""Regression guard: the main table's headline cells must carry the
realized-comp marker for note-carrying tickers.

Background (2026-10-12): the REALIZED_COMP_NOTES contract (TSLA's 10-K/A
realized-comp caveat, added 2026-09-18) was applied to the insight cards,
the company detail panel, the Highest Paid metric card, and the role-comp
tables - but NOT to the main comp table itself, the site's most-visited
surface. The TSLA row rendered "$158.4B" in the CEO comp cell (with a #1
top-comp badge) and "2,522,203:1" in the pay-ratio cell (with the extreme
ratio badge) with no grant-date marker, while every other surface annotated
both figures. This is the surface-incompleteness class for contract notes:
any cell rendering a note-carrying ticker's headline figure must emit the
"· grant-date figure" marker.

The fix adds the marker (span.role-top-grantdate, title = filing-verbatim
note, quote-escaped) to both cells in the main-table row renderer:
  - comp cell: gated on !isRolePivot, since the note is CEO-specific and
    role-pivot cells render other roles' comp
  - pay-ratio cell: inside the pay_ratio > 0 branch, alongside the outlier
    badges
Non-note tickers render byte-identical.

This guard:
  S1: the comp-cell render block gates the marker on
      !isRolePivot && REALIZED_COMP_NOTES[c.ticker]
  S2: the pay-ratio cell render block (ratioHtml, pay_ratio > 0 branch)
      gates the marker on REALIZED_COMP_NOTES[c.ticker]
  S3: both new marker sites quote-escape the title attribute
      (.replace(/"/g, '&quot;') adjacent to the span)
  S4: the .role-top-grantdate class exists in css/style.css
  S5: every role-top-grantdate emission in js/app.js carries a title=
      attribute in the same statement (no bare marker without the note)

Usage:
  scripts/check_table_realized_marker.py              # static checks
  scripts/check_table_realized_marker.py --static-only # same (pre-commit contract)

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem.

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
    try:
        src = open(APP_JS, encoding="utf-8").read()
    except OSError as e:
        print("INFRA: cannot read js/app.js: %s" % e)
        return 2

    # Locate the main-table row renderer's comp-cell and ratio-cell regions.
    comp_gate = re.search(
        r"if\s*\(\s*!isRolePivot\s*&&\s*REALIZED_COMP_NOTES\[c\.ticker\]\s*\)\s*\{"
        r"\s*compHtml\s*\+=\s*' <span class=\"role-top-grantdate\"",
        src,
    )
    check(
        "S1 comp cell gated on !isRolePivot && REALIZED_COMP_NOTES[c.ticker]",
        comp_gate is not None,
        "marker emission site found" if comp_gate else "missing or mis-gated",
    )

    ratio_block = re.search(
        r"if\s*\(\s*c\.pay_ratio\s*!=\s*null\s*&&\s*c\.pay_ratio\s*>\s*0\s*\)\s*\{(.*?)\n\s*\}\s*else\s*\{",
        src,
        re.S,
    )
    ratio_gate = None
    if ratio_block:
        ratio_gate = re.search(
            r"if\s*\(\s*REALIZED_COMP_NOTES\[c\.ticker\]\s*\)\s*\{"
            r"\s*ratioHtml\s*\+=\s*' <span class=\"role-top-grantdate\"",
            ratio_block.group(1),
        )
    check(
        "S2 ratio cell gates marker on REALIZED_COMP_NOTES[c.ticker] "
        "(pay_ratio > 0 branch)",
        ratio_gate is not None,
        "marker emission site found in ratio branch" if ratio_gate
        else "missing from ratio branch",
    )

    # S3: both new sites quote-escape the title. Anchor each emission to its
    # variable (compHtml / ratioHtml) so the pre-existing role-table site
    # cannot satisfy either check.
    comp_esc = re.search(
        r"compHtml\s*\+=\s*' <span class=\"role-top-grantdate\" "
        r"title=\"' \+ REALIZED_COMP_NOTES\[c\.ticker\]\.replace\(/\"/g, '&quot;'\)",
        src,
    )
    ratio_esc = re.search(
        r"ratioHtml\s*\+=\s*' <span class=\"role-top-grantdate\" "
        r"title=\"' \+ REALIZED_COMP_NOTES\[c\.ticker\]\.replace\(/\"/g, '&quot;'\)",
        src,
    )
    check(
        "S3 comp-cell marker title is quote-escaped",
        comp_esc is not None,
        "replace(/\"/g) adjacent" if comp_esc else "escape missing",
    )
    check(
        "S3 ratio-cell marker title is quote-escaped",
        ratio_esc is not None,
        "replace(/\"/g) adjacent" if ratio_esc else "escape missing",
    )

    # S4: CSS class exists.
    try:
        css = open(CSS, encoding="utf-8").read()
        check(
            "S4 .role-top-grantdate class defined in css/style.css",
            ".role-top-grantdate" in css,
            "",
        )
    except OSError as e:
        print("INFRA: cannot read css/style.css: %s" % e)
        return 2

    # S5: every role-top-grantdate emission carries a title attribute in the
    # same statement (semicolon-terminated segment containing the span).
    segments = [s for s in src.split(";") if "role-top-grantdate" in s]
    bare = [s for s in segments if "title=" not in s]
    check(
        "S5 every role-top-grantdate emission carries a title attribute",
        len(bare) == 0,
        "%d/%d emissions titled" % (len(segments) - len(bare), len(segments)),
    )

    return 0 if all(ok for _, ok, _ in results) else 1


def main():
    if "--static-only" in sys.argv:
        rc = static_checks()
    else:
        rc = static_checks()
    sys.exit(rc)


if __name__ == "__main__":
    main()
