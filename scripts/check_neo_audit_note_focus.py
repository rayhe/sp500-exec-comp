#!/usr/bin/env python3
"""Regression guard: NEO-panel correction audit note is keyboard-accessible.

The 2026-10-26 15:30 PT run (235th review) closed the last known
keyboard gap the 234th run queued: .neo-audit-note in the NEO detail
panel was a non-focusable <span> whose correction history lived only
in a title tooltip (mouse-only; title tooltips do not surface on
keyboard focus in Chrome). 805 of 7,079 NEO rows carry such a note, so
the gap hid real correction history from keyboard and AT users. The
sibling .neo-footnote-mark has the same title-only shape but its
content is ALSO rendered as full .neo-footnote text below the table,
so the audit note was the one title-only surface with no alternate
rendering.

Fix (js/app.js + css/style.css):
  - the span carries tabindex="0" (keyboard-focusable);
  - its aria-label carries the full escaped note text
    ("Correction audit note: <note>"), not the bare generic label, so
    AT users hear the correction history on focus;
  - css/style.css carries .neo-audit-note:focus-visible { opacity: 1;
    outline: 2px solid var(--accent); outline-offset: 1px; }, matching
    the .neo-filing-link focus pattern from the 234th run.

Checks (all static):
  S1 js/app.js renders .neo-audit-note with tabindex="0".
  S2 the span's aria-label is built from the escaped audit text
     (_auditEsc), not the bare "Correction audit note" label.
  S3 css/style.css has .neo-audit-note:focus-visible with opacity: 1
     and the --accent outline (all matches scanned, not just the
     first: the selector also appears in no light-theme override today,
     but the 234th run's guard-authoring note applies).

Usage:
  scripts/check_neo_audit_note_focus.py
  scripts/check_neo_audit_note_focus.py --static-only

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

    # S1: the audit-note span is keyboard-focusable.
    # js/app.js builds it as: ' <span class="neo-audit-note" tabindex="0" ...'
    s1 = ('<span class="neo-audit-note" tabindex="0"' in js)
    check("S1 .neo-audit-note is rendered with tabindex=\"0\"",
          s1, "" if s1 else "audit-note span lacks tabindex in js/app.js")

    # S2: the aria-label carries the note text, not just the generic label.
    # The markup builds: aria-label="Correction audit note: ' + _auditEsc
    # (plain single-quote before the concatenation, per the file's literal
    # quoting - the 234th run's guard-authoring note).
    s2 = ('aria-label="Correction audit note: \' + _auditEsc' in js)
    check("S2 .neo-audit-note aria-label carries the escaped note text",
          s2, "" if s2 else "aria-label does not build from _auditEsc")

    # S3: focus-visible reveal matching hover, plus the accent ring.
    # Scan ALL matches (234th run's guard-authoring note: a selector can
    # appear in a light-theme single-line rule as well as the base rule).
    matches = re.findall(r"\.neo-audit-note:focus-visible\s*\{([^}]*)\}", css)
    s3 = any("opacity: 1" in body and "var(--accent)" in body for body in matches)
    check("S3 .neo-audit-note:focus-visible reveals at opacity 1 with accent ring",
          s3, "" if s3 else "focus-visible audit-note reveal missing")


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
