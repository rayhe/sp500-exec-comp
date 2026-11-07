#!/usr/bin/env python3
"""Guard: a filter+detail deep link whose target is outside a
non-ticker-list filter restores the filtered table instead of
leaving zero rows (377th review).

Background (377th review, 2026-11-07): closes the 376th run's
candidate (1). The 375th fix guards the detail-open path against
the five ticker-list filters (peer-dist, community, quartile,
position, crosstab) by checking their tickers lists before forcing
the search. But the other filters in renderTable -- sector, ratio
bucket, dist, conc tier, CEO/CFO bucket, volatility, role,
gov/gender/tenure/SoP, YoY, stock-pct, asp-delta, team
completeness, CEO transition, PvP-only -- carry no tickers list,
so no pre-search test can tell whether they exclude the target.
When one of them does, the forced search (searchTerm = detail
ticker) ANDs with the filter, yields zero rows, opens no panel,
and leaves the hash carrying detail= for a panel that does not
exist -- a reload repeats the empty table.

The fix saves the pre-search state (searchTerm and currentPage)
before forcing the search, and the re-query after the forced
render tracks whether the target row was found. When it still is
not found, the branch reverts the forced search (restores the
pre-search term, input value, and page), re-renders the filtered
table the user actually asked for, nulls the expanded-detail
ticker (and the diff key), pushes the hash so detail= (and diff=)
drops immediately, and announces why no panel opened -- the same
pair-null invariant as the 371st Reset All, 372nd Escape-close,
374th filter-click, and 375th ticker-list fixes. A target that IS
found still takes the click-and-scroll path.

Checks (all static - small JS reads, <2s):
 C1 HARD FAIL: the detail-open path does not save the pre-search
    state (search term and page) before forcing the search.
 C2 HARD FAIL: the re-query after the forced search does not track
    whether the target row was found, or has no not-found branch.
 C3 HARD FAIL: the not-found branch does not restore the pre-search
    term, input, and page, re-render, null the expanded detail
    ticker and the diff key, pushState so the URL drops detail=, or
    announce why no panel opened.
 C4 HARD FAIL: the search path is gone -- searchTerm = detailTicker
    must still be present in the detail-open block, and the found
    path must still click the target row, so an in-filter or
    unfiltered deep link still opens its panel.
 C5 HARD FAIL: node --check fails on js/app.js.

Usage:
  scripts/check_detail_zero_row_restore.py
  scripts/check_detail_zero_row_restore.py --static-only

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

    # The detail-open block: from the detail= comment to the end of the
    # function body. Match on code literals, not prose: the guard's own
    # docstring and the app's comments both mention the marker phrases.
    open_anchor = ahs.find("// Deep-link: open detail panel for specified ticker")
    if open_anchor < 0:
        failures.append("C1 detail-open block not found in applyHashState")
        print("FAIL: " + "\nFAIL: ".join(failures))
        return 1
    detail_block = ahs[open_anchor:]

    search_pos = detail_block.find("searchTerm = detailTicker;")
    if search_pos < 0:
        failures.append("C4 searchTerm = detailTicker is missing from the "
                        "detail-open block -- the in-filter / unfiltered "
                        "deep-link path is gone")

    # --- C1: pre-search state saved before the forced search --------
    save_term = detail_block.find("var _prevSearchTerm = searchTerm;")
    save_page = detail_block.find("var _prevPage = currentPage;")
    if save_term < 0:
        failures.append("C1 the detail-open path does not save the "
                        "pre-search term before forcing the search -- "
                        "there is nothing to restore when a non-ticker-"
                        "list filter excludes the target")
    elif search_pos >= 0 and save_term > search_pos:
        failures.append("C1 the pre-search term is saved AFTER the forced "
                        "search -- it would capture the ticker itself, "
                        "not the state to restore")
    if save_page < 0:
        failures.append("C1 the detail-open path does not save the "
                        "pre-search page before forcing the search")
    elif detail_block.find("currentPage = 1;") >= 0 and \
            save_page > detail_block.find("currentPage = 1;"):
        failures.append("C1 the pre-search page is saved AFTER currentPage "
                        "= 1 -- the restore would keep page 1 instead of "
                        "the page the user was on")

    # --- C2: the re-query tracks found-ness and has a not-found -----
    # branch after the forced search
    found_flag = detail_block.find("var _foundTarget = false;")
    not_found = detail_block.find("if (!_foundTarget)")
    if found_flag < 0:
        failures.append("C2 the re-query after the forced search does not "
                        "track whether the target row was found -- a "
                        "zero-row result would go undetected")
    if not_found < 0:
        failures.append("C2 the detail-open path has no not-found branch "
                        "-- when a non-ticker-list filter excludes the "
                        "target, the forced search would leave zero rows "
                        "with no restore")
    elif search_pos >= 0 and not_found < search_pos:
        failures.append("C2 the not-found branch sits BEFORE the forced "
                        "search -- it must run on the re-query after the "
                        "forced render, not before it")

    # --- C3: the not-found branch restores, nulls, pushes, announces
    # Brace-match the branch (a fixed window is brittle: the branch
    # carries a long comment, and the 375th guard's window already
    # proved too short for prose-heavy branches).
    if not_found >= 0:
        branch = extract_function_body(detail_block, "if (!_foundTarget)")
        if branch is None:
            failures.append("C3 the not-found branch body cannot be "
                            "brace-matched -- the branch may be malformed")
            branch = ""
        need = [
            ("searchTerm = _prevSearchTerm;",
             "does not restore the pre-search term"),
            ("value = _prevSearchTerm",
             "does not restore the search input value"),
            ("currentPage = _prevPage;",
             "does not restore the pre-search page"),
            ("renderTable(companies);",
             "does not re-render the filtered table after restoring"),
            ("_expandedDetailTicker = null;",
             "does not null the expanded detail ticker -- the hash "
             "would keep detail= for a panel that was never opened"),
            ("_activeDiffKey = null;",
             "does not null the diff key -- a stale diff= would ride "
             "along with the dropped detail="),
            ("pushState();",
             "does not pushState -- the URL would keep detail= until "
             "the next table render, and a reload would repeat the "
             "empty table"),
            ("announce('Detail panel not opened",
             "does not announce why no panel opened -- a screen-reader "
             "user gets no explanation for the missing panel"),
        ]
        for lit, why in need:
            if lit not in branch:
                failures.append("C3 the not-found branch " + why)

    # --- C4: the found path still clicks the target row -------------
    if "r.click();" not in detail_block:
        failures.append("C4 the found path no longer clicks the target "
                        "row -- an in-filter deep link would not open "
                        "its panel")
    if "_openDiffFromHash(detailTicker, state.diff);" not in detail_block:
        failures.append("C4 the found path no longer opens the diff "
                        "viewer from the hash -- a diff deep link would "
                        "open the panel without its repair diff")

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
    print("PASS: detail-zero-row-restore: the detail-open path saves the "
          "pre-search term and page before forcing the search; the "
          "re-query tracks whether the target was found; when it still "
          "is not found, the branch restores the pre-search term, input "
          "and page, re-renders the filtered table, nulls the expanded "
          "ticker and diff key, pushes the hash so detail= drops, and "
          "announces why no panel opened; the found path still clicks "
          "the target row and opens the diff viewer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
