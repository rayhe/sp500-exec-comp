#!/usr/bin/env python3
"""Guard: detail= for a ticker that is not in the roster at all must
drop detail= from the hash instead of leaving a stale deep link
(378th review).

Background (378th review, 2026-11-07): closes the 377th run's
candidate (1). The detail-open block in applyHashState sets
_expandedDetailTicker = detailTicker before checking whether the
ticker exists in companies. When it does not exist (typo, delisted
name, stale link), no branch ever nulled the variable, so the hash
kept detail= for a panel that can never open -- a reload repeats
the stale deep link forever. The 375th/377th fixes only cover
tickers that exist but are hidden by a filter; this is the
nonexistent-ticker class.

The fix adds an else branch on companyExists: it nulls the
expanded-detail ticker and the diff key synchronously (so no later
serializeState can re-emit detail= or diff=), then defers the
pushState + announce on a short setTimeout -- pushState is a no-op
until _stateInitialized flips true right after applyHashState
returns at boot, so the push must wait past init, the same deferred
pattern the existing-ticker setTimeout(50) path uses. On a
hashchange restore _stateInitialized is already true, so the same
delay is harmless there.

Checks (all static - small JS reads, <2s):
 C1 HARD FAIL: the detail-open block has no else branch on
    companyExists carrying the 378th-review fix.
 C2 HARD FAIL: the else branch does not null the expanded detail
    ticker and the diff key, or does not null them BEFORE the
    deferred push (a deferred null would let a pushState between
    applyHashState's return and the timer re-emit detail=).
 C3 HARD FAIL: the else branch does not defer pushState on a
    setTimeout, or does not announce why no panel opened.
 C4 HARD FAIL: the existing-ticker path is gone -- the companyExists
    check, the forced search, the row click, or the diff-viewer open
    must still be present, so a real deep link still opens its panel.
 C5 HARD FAIL: node --check fails on js/app.js.

Usage:
  scripts/check_detail_unknown_ticker.py
  scripts/check_detail_unknown_ticker.py --static-only

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

    ahs = extract_function_body(app, "function applyHashState(companies)")
    if ahs is None:
        failures.append("C1 applyHashState not found in js/app.js")
        print("FAIL: " + "\nFAIL: ".join(failures))
        return 1

    open_anchor = ahs.find("// Deep-link: open detail panel for specified ticker")
    if open_anchor < 0:
        failures.append("C1 detail-open block not found in applyHashState")
        print("FAIL: " + "\nFAIL: ".join(failures))
        return 1
    detail_block = ahs[open_anchor:]

    # --- C1: the else branch on companyExists exists ----------------
    exists_pos = detail_block.find("if (companyExists) {")
    if exists_pos < 0:
        failures.append("C4 the companyExists check is missing from the "
                        "detail-open block")
    fix_comment = detail_block.find("// 378th review:")
    if fix_comment < 0:
        failures.append("C1 the detail-open block has no else branch on "
                        "companyExists for a nonexistent ticker -- detail= "
                        "for a ticker outside the roster would keep the "
                        "stale hash forever")
        fix_comment = None

    branch = None
    if fix_comment is not None and exists_pos >= 0:
        # The branch opens at the last "} else {" before the fix comment;
        # it must sit after the companyExists check (not inside the
        # targetRow else-if chain, which precedes the setTimeout close).
        else_pos = detail_block.rfind("} else {", 0, fix_comment)
        if else_pos < 0 or else_pos < exists_pos:
            failures.append("C1 the 378th-review fix is not inside an else "
                            "branch on companyExists")
        else:
            # Brace-match from the "{" of that else (the first call in the
            # 377th guard's helper searches from the first marker
            # occurrence, which is wrong here -- the detail block's
            # targetRow else-if chain precedes this branch).
            brace = detail_block.find("{", else_pos)
            depth = 0
            end = None
            for i in range(brace, len(detail_block)):
                if detail_block[i] == "{":
                    depth += 1
                elif detail_block[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            branch = detail_block[brace:end] if end else None
            if branch is None:
                failures.append("C1 the nonexistent-ticker else branch "
                                "body cannot be brace-matched -- the branch "
                                "may be malformed")

    # --- C2: the branch nulls the pair, synchronously ----------------
    if branch is not None:
        null_ticker = branch.find("_expandedDetailTicker = null;")
        null_diff = branch.find("_activeDiffKey = null;")
        timer_pos = branch.find("setTimeout(function() {")
        if null_ticker < 0:
            failures.append("C2 the nonexistent-ticker branch does not null "
                            "the expanded detail ticker -- the hash would "
                            "keep detail= for a panel that can never open")
        if null_diff < 0:
            failures.append("C2 the nonexistent-ticker branch does not null "
                            "the diff key -- a stale diff= would ride along "
                            "with the dropped detail=")
        if null_ticker >= 0 and timer_pos >= 0 and null_ticker > timer_pos:
            failures.append("C2 the ticker null sits AFTER the deferred "
                            "push -- a pushState between applyHashState's "
                            "return and the timer would re-emit detail=")
        if null_diff >= 0 and timer_pos >= 0 and null_diff > timer_pos:
            failures.append("C2 the diff-key null sits AFTER the deferred "
                            "push -- same re-emit hazard as the ticker null")

    # --- C3: the branch defers pushState and announces ---------------
    if branch is not None:
        timer_pos = branch.find("setTimeout(function() {")
        if timer_pos < 0:
            failures.append("C3 the nonexistent-ticker branch does not defer "
                            "on a setTimeout -- pushState is a no-op until "
                            "_stateInitialized flips true after "
                            "applyHashState returns at boot, so an immediate "
                            "push would never drop detail= from the URL")
        else:
            deferred = branch[timer_pos:]
            if "pushState();" not in deferred:
                failures.append("C3 the deferred branch does not pushState "
                                "-- the URL would keep detail= until the "
                                "next table render, and a reload would "
                                "repeat the stale deep link")
            if "announce('Detail panel not opened:" not in deferred:
                failures.append("C3 the deferred branch does not announce "
                                "why no panel opened -- a screen-reader "
                                "user gets no explanation for the missing "
                                "panel")

    # --- C4: the existing-ticker path is intact -----------------------
    if "searchTerm = detailTicker;" not in detail_block:
        failures.append("C4 searchTerm = detailTicker is missing from the "
                        "detail-open block -- the in-filter / unfiltered "
                        "deep-link path is gone")
    if "r.click();" not in detail_block:
        failures.append("C4 the found path no longer clicks the target row "
                        "-- a real deep link would not open its panel")
    if "_openDiffFromHash(detailTicker, state.diff);" not in detail_block:
        failures.append("C4 the found path no longer opens the diff viewer "
                        "from the hash -- a diff deep link would open the "
                        "panel without its repair diff")

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
    print("PASS: detail-unknown-ticker: the detail-open path has an else "
          "branch on companyExists that nulls the expanded ticker and diff "
          "key synchronously, then defers pushState and the announce past "
          "init so detail= drops from the URL for a ticker outside the "
          "roster; the existing-ticker path still forces the search, clicks "
          "the target row, and opens the diff viewer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
