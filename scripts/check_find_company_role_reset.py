#!/usr/bin/env python3
"""Guard: findCompanyInTable must reset the role view to CEO before
forcing the search (379th review).

Background (379th review, 2026-11-07): closes the 378th run's
candidate (1). findCompanyInTable's contract is "Clear filters to
ensure company is visible" -- the 376th review extended it to all
25 row-hiding filter dimensions, but it missed the role view.
renderTable filters to companies with _roleExecs[activeRole] when a
non-CEO role is active, so a CFO/COO/CTO view hid any target company
lacking that role's exec (31 lack a CFO, 365 a COO, 476 a CTO of
518), and the setTimeout auto-click silently found no row: no panel,
no announcement, role chips still claiming a live view. The same
failure class as the 376th fix, in the one dimension it missed.

The fix nulls activeRole at the top of findCompanyInTable and resets
the role chips + column header, mirroring insightResetAndSort and
resetAllFilters, so every "show me this company" call site (~20:
Top 10 chart clicks, insight cards, peer navigation) works from any
role view.

Checks (all static - small JS reads, <2s):
 C1 HARD FAIL: findCompanyInTable has no 379th-review role reset
    (an activeRole guard that nulls it).
 C2 HARD FAIL: the reset does not reset the role chips (remove
    'active' from all, add it to the first) or does not refresh the
    role column header -- the chips/header would keep claiming the
    old role view behind a CEO table.
 C3 HARD FAIL: the reset sits AFTER the forced search / renderTable
    -- the search would render under the old role filter and hide
    the target row before the reset could help.
 C4 HARD FAIL: a sibling reset path lost its role null
    (insightResetAndSort or resetAllFilters) -- the contract's other
    paths must keep resetting role too.
 C5 HARD FAIL: node --check fails on js/app.js.

Usage:
  scripts/check_find_company_role_reset.py
  scripts/check_find_company_role_reset.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
import subprocess
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = f"{REPO}/js/app.js"

if "--static-only" in sys.argv:
    pass  # static half is the whole check; flag accepted for the hook runner


def extract_function_body(src, start_marker):
    """Return the brace-matched body starting at start_marker, or None."""
    idx = src.find(start_marker)
    if idx < 0:
        return None
    brace = src.find("{", idx)
    if brace < 0:
        return None
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[brace:i + 1]
    return None


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read js/app.js: {exc}")
        return 2

    failures = []

    body = extract_function_body(app, "window.findCompanyInTable = function(ticker) {")
    if body is None:
        failures.append("C1 findCompanyInTable not found in js/app.js")
        print("FAIL: " + "\nFAIL: ".join(failures))
        return 1

    # --- C1: the 379th-review role reset exists ----------------------
    fix_comment = body.find("// 379th review:")
    if fix_comment < 0:
        failures.append("C1 findCompanyInTable has no 379th-review role "
                        "reset -- a non-CEO role view would hide the "
                        "target company and the auto-click would silently "
                        "find no row")
    else:
        reset_block = body[fix_comment:]
        if "if (activeRole) {" not in reset_block:
            failures.append("C1 the 379th-review block does not guard on "
                            "activeRole -- the reset would run "
                            "unconditionally or not at all")
        if "activeRole = null;" not in reset_block:
            failures.append("C1 the 379th-review block does not null "
                            "activeRole -- the role filter would keep "
                            "hiding the target row")

    # --- C2: chips + column header refresh ---------------------------
    if fix_comment >= 0:
        reset_block = body[fix_comment:]
        # Scope the chip/header checks to the reset block: from the fix
        # comment to the forced search, so a later unrelated
        # querySelectorAll cannot satisfy them.
        search_pos = reset_block.find("searchTerm = ticker;")
        scoped = reset_block[:search_pos] if search_pos >= 0 else reset_block
        if "querySelectorAll('.role-chip')" not in scoped:
            failures.append("C2 the role reset does not touch the role "
                            "chips -- they would keep showing the old "
                            "role as active behind a CEO table")
        if "classList.remove('active')" not in scoped:
            failures.append("C2 the role reset does not remove 'active' "
                            "from the role chips")
        if "classList.add('active')" not in scoped:
            failures.append("C2 the role reset does not re-activate the "
                            "CEO (first) role chip")
        if "updateRoleColumnHeader();" not in scoped:
            failures.append("C2 the role reset does not refresh the role "
                            "column header -- the header would keep "
                            "naming the old role")

    # --- C3: reset precedes the forced search / render ---------------
    if fix_comment >= 0:
        null_pos = body.find("activeRole = null;", fix_comment)
        search_pos = body.find("searchTerm = ticker;")
        render_pos = body.find("renderTable(companies);")
        if null_pos < 0:
            failures.append("C3 the role null is missing -- cannot order "
                            "it before the search")
        if search_pos >= 0 and null_pos >= 0 and null_pos > search_pos:
            failures.append("C3 the role null sits AFTER the forced search "
                            "-- the search would render under the old role "
                            "filter and hide the target row")
        if render_pos >= 0 and null_pos >= 0 and null_pos > render_pos:
            failures.append("C3 the role null sits AFTER renderTable -- "
                            "the table would render under the old role "
                            "filter")

    # --- C4: sibling reset paths still null activeRole ----------------
    insight = extract_function_body(app, "function insightResetAndSort(sortKey, sortDir) {")
    if insight is None:
        failures.append("C4 insightResetAndSort not found in js/app.js")
    elif "activeRole = null;" not in insight:
        failures.append("C4 insightResetAndSort no longer nulls activeRole "
                        "-- the insight-action path would keep the role "
                        "view behind its reset table")
    reset_all = extract_function_body(app, "window.resetAllFilters = function() {")
    if reset_all is None:
        failures.append("C4 resetAllFilters not found in js/app.js")
    elif "activeRole = null;" not in reset_all:
        failures.append("C4 resetAllFilters no longer nulls activeRole -- "
                        "Reset All would keep the role view behind its "
                        "reset table")

    # --- C5: syntax -----------------------------------------------------
    try:
        chk = subprocess.run(["node", "--check", APP_JS],
                             capture_output=True, text=True, timeout=30)
        if chk.returncode != 0:
            failures.append("C5 node --check fails on js/app.js: "
                            + (chk.stderr or chk.stdout).strip()[:200])
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"INFRA: node --check unavailable: {exc}")
        return 2

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: find-company-role-reset: findCompanyInTable nulls "
          "activeRole before the forced search, resets the role chips "
          "and column header, and both sibling reset paths still null "
          "the role -- a role view can no longer hide the target company")
    return 0


if __name__ == "__main__":
    sys.exit(main())
