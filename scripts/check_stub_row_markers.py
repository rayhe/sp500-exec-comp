#!/usr/bin/env python3
"""Regression guard: coverage stubs must not render as zero-pay CEOs.

New failure-mode class (2026-10-12 18:00 PT run): a zero-row roster company
(VMRK today -- added at the Sep 2026 rebalance with no post-merger DEF 14A on
file yet, total_compensation 0 as a roster placeholder) rendered the
main-table comp cell as "$0", which reads as a genuine zero-pay CEO on the
site's most-visited surface. Every aggregate layer already excludes stubs
(computeCompPercentile nulls them, the Zero Pay insight filters on
_hasNeoData); the main-table comp cell is the one surface that still printed
the placeholder as a value. The fix:
  - renderTable computes `var _isStub = !(c.executives && c.executives.length)`
    and renders stubCompCellHtml(c) instead of the "$0" + bar for stub rows
  - stubCompCellHtml reuses the filing-grounded MISSING_DATA_REASONS text with
    the same escaped-content contract as getMissingDataHtml
  - VMRK gets a MISSING_DATA_REASONS entry so its pay-ratio / median-worker
    cells render the warning N/A with a tooltip (and the detail panel's
    Incomplete-data notice picks up the filing-grounded reason instead of the
    generic fallback)

Checks (static, fast, runs in the pre-commit hook):
  S1 every zero-executive-row company in data/compensation.json has a
     MISSING_DATA_REASONS entry in js/app.js (so stub N/A cells carry a
     filing-grounded reason, and the entry stays live per the
     check_missing_data_reasons.py S1 contract)
  S2 the main-table comp-cell stub branch exists: `_isStub` computed from the
     executives array (not ticker-hardcoded) and the branch calls
     stubCompCellHtml(c)
  S3 stubCompCellHtml reuses MISSING_DATA_REASONS text and quote-escapes the
     title attribute
  S4 node-eval of the file-extracted stubCompCellHtml: a stub ticker renders
     N/A with its reason text (quote-escaped); an unknown ticker gets the
     generic fallback
  S5 the _isStub branch never emits formatCurrency (guards against the "$0"
     value creeping back in beside the marker)

Usage:
  scripts/check_stub_row_markers.py
  scripts/check_stub_row_markers.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")
COMP_JSON = os.path.join(REPO, "data", "compensation.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def extract_braced(src, start_idx):
    """Return the {...} block starting at the first '{' at/after start_idx."""
    i = src.index("{", start_idx)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i : j + 1]
    raise ValueError("unbalanced braces")


def static_checks():
    try:
        src = open(APP_JS, encoding="utf-8").read()
    except OSError as e:
        print("INFRA: cannot read js/app.js: %s" % e)
        return 2
    try:
        comp = json.load(open(COMP_JSON, encoding="utf-8"))
    except OSError as e:
        print("INFRA: cannot read data/compensation.json: %s" % e)
        return 2

    # S1: every zero-row company has a MISSING_DATA_REASONS entry.
    stubs = [
        c["ticker"]
        for c in comp["companies"]
        if not c.get("executives")
    ]
    dict_m = re.search(
        r"var MISSING_DATA_REASONS = (\{.*?\n\});", src, re.S
    )
    reason_keys = set()
    if dict_m:
        reason_keys = set(re.findall(r"^\s*'([A-Z]+)'\s*:", dict_m.group(1), re.M))
    missing = [t for t in stubs if t not in reason_keys]
    check(
        "S1 every zero-row stub company has a MISSING_DATA_REASONS entry",
        len(missing) == 0 and len(stubs) > 0,
        ("stubs=%s" % stubs) if not missing else ("no reason for: %s" % missing),
    )

    # S2: the comp-cell stub branch exists and is data-driven (executives
    # array), calling the marker helper.
    is_stub_decl = re.search(
        r"var _isStub = !\(c\.executives && c\.executives\.length\);", src
    )
    branch = re.search(
        r"if\s*\(\s*_isStub\s*\)\s*\{\s*compHtml\s*\+=\s*stubCompCellHtml\(c\);",
        src,
    )
    check(
        "S2 comp-cell stub branch: data-driven _isStub from executives array, "
        "calls stubCompCellHtml(c)",
        is_stub_decl is not None and branch is not None,
        "decl+branch found" if (is_stub_decl and branch) else "missing or ticker-hardcoded",
    )

    # S3: the helper reuses MISSING_DATA_REASONS and escapes the title.
    helper_m = re.search(r"function stubCompCellHtml\(c\)", src)
    helper_body = ""
    if helper_m:
        try:
            helper_body = (
                "function stubCompCellHtml(c) " + extract_braced(src, helper_m.end() - 3)
            )
        except ValueError:
            helper_body = ""
    reuses_reasons = "MISSING_DATA_REASONS" in helper_body
    escapes = ".replace(/\"/g, '&quot;')" in helper_body
    check(
        "S3 stubCompCellHtml reuses MISSING_DATA_REASONS and quote-escapes title",
        reuses_reasons and escapes,
        "reuses+escapes" if (reuses_reasons and escapes) else "contract broken",
    )

    # S4: node-eval the FILE-EXTRACTED helper (never hand-composed): VMRK
    # renders N/A + reason + quote escaping; unknown ticker gets the fallback.
    if not helper_body:
        check("S4 node-eval of extracted stubCompCellHtml", False, "extraction failed")
    else:
        probe = (
            "var MISSING_DATA_REASONS = {'VMRK': 'stub reason with \"quotes\"'};\n"
            + helper_body
            + "\nconsole.log(stubCompCellHtml({ticker:'VMRK'}));\n"
            + "console.log(stubCompCellHtml({ticker:'ZZZZ'}));\n"
        )
        try:
            out = subprocess.run(
                ["node", "-e", probe],
                capture_output=True,
                text=True,
                timeout=30,
            )
            lines = out.stdout.strip().split("\n")
            vmrk_ok = (
                len(lines) >= 2
                and "N/A" in lines[0]
                and "stub reason with &quot;quotes&quot;" in lines[0]
                and out.returncode == 0
            )
            fall_ok = len(lines) >= 2 and "No NEO compensation data on file yet" in lines[1]
            check(
                "S4 node-eval extracted helper: stub ticker renders N/A + "
                "escaped reason, unknown ticker gets fallback",
                vmrk_ok and fall_ok,
                "vmrk=%s fallback=%s" % (vmrk_ok, fall_ok),
            )
        except (OSError, subprocess.SubprocessError) as e:
            check("S4 node-eval of extracted stubCompCellHtml", False, "infra: %s" % e)

    # S5: the _isStub branch never emits formatCurrency (no "$0" beside or
    # instead of the marker).
    stub_branch_block = re.search(
        r"if\s*\(\s*_isStub\s*\)\s*\{([^}]*)\}", src
    )
    leaks_value = (
        stub_branch_block is not None
        and "formatCurrency" in stub_branch_block.group(1)
    )
    check(
        "S5 _isStub branch never calls formatCurrency (no $0 placeholder value)",
        stub_branch_block is not None and not leaks_value,
        "branch emits value" if leaks_value else "clean",
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
