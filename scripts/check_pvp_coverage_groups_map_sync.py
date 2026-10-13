#!/usr/bin/env python3
"""Regression guard: the PvP section's coverage-clause groups must stay in
sync with the canonical PVP_EXCLUSIONS map.

New failure-mode class (2026-10-12 22:00 PT run): paired-constant desync,
third representation. js/app.js carries THREE parallel representations of
the PvP exclusion set:

  1. PVP_EXCLUSIONS (canonical map ticker -> filing-grounded reason),
     rendered by company detail panels;
  2. PVP_EXCLUSION_GROUPS (grouped [{label, tickers}] for the Data
     Verification modal), guarded against the map by
     check_pvp_exclusion_groups_sync.py (72nd guard);
  3. PVP_COVERAGE_EXCLUSION_GROUPS (gap classes for the PvP section
     coverage clause), guard-synced to the LIVE gap set by
     check_pvp_coverage_desc.py S4 (union == comp tickers minus
     PvP-covered tickers, exactly).

Representation (3) is synced to the live gaps, but NOT to the canonical
map: a future edit that drops a ticker from PVP_EXCLUSIONS (and, to keep
the 72nd guard green, from PVP_EXCLUSION_GROUPS) without touching
PVP_COVERAGE_EXCLUSION_GROUPS leaves every existing guard green while
the UI lies by omission -- the modal's exclusion list loses the ticker
(and its group count), and the ticker's detail panel renders its missing
PvP section as an unexplained gap instead of the filing-grounded reason.
Negative-tested 2026-10-12: dropping FDXF from the map + modal groups
(label re-vintaged (3)->(2)) trips NO existing guard (72nd 5/5,
coverage-desc 5/5, method-coverage-sync 6/6 all PASS on the broken tree).

The same hole covers the reverse: a coverage-clause ticker the map never
knew, and the same-issuer-duplicate class (currently GOOG, whose 402(v)
disclosure ships once under GOOGL and is therefore NOT a live gap and
correctly absent from the coverage groups). That special case lived only
in a code comment; this guard pins it.

Checks (static, fast, runs in the pre-commit hook):
  S1 every PVP_COVERAGE_EXCLUSION_GROUPS ticker is a key in PVP_EXCLUSIONS
     (no coverage-clause ticker lacks a filing-grounded reason)
  S2 the map-minus-coverage difference equals exactly the
     same-issuer-duplicate class: keys whose reason matches
     "Same issuer as <T>"; every such key is NOT a live gap and its
     named ticker IS PvP-covered (the disclosure ships once, under
     that ticker). A map key dropped from the coverage clause without
     the same-issuer reason trips here.
  S3 no ticker appears in more than one coverage group

Usage:
  scripts/check_pvp_coverage_groups_map_sync.py
  scripts/check_pvp_coverage_groups_map_sync.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")
COMP_JSON = os.path.join(REPO, "data", "compensation.json")
PVP_JSON = os.path.join(REPO, "data", "pay_vs_performance.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def extract_balanced(src, start_idx, open_ch, close_ch):
    """Return the balanced open_ch..close_ch block starting at start_idx."""
    i = src.index(open_ch, start_idx)
    depth = 0
    in_str = None
    esc = False
    for j in range(i, len(src)):
        ch = src[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ("'", '"'):
            in_str = ch
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return src[i : j + 1]
    raise ValueError("unbalanced " + open_ch + close_ch)


def live_gaps():
    comp = json.load(open(COMP_JSON, encoding="utf-8"))
    pvp = json.load(open(PVP_JSON, encoding="utf-8"))
    comp_tickers = {c["ticker"] for c in comp["companies"]}
    pvp_tickers = {t for t, c in pvp["companies"].items()
                   if isinstance(c, dict) and (c.get("years") or [])}
    return comp_tickers, pvp_tickers, sorted(comp_tickers - pvp_tickers)


SAME_ISSUER_RE = re.compile(r"Same issuer as ([A-Z0-9.\-]+)")


def static_checks():
    try:
        src = open(APP_JS, encoding="utf-8").read()
    except OSError as e:
        print("INFRA: cannot read js/app.js: %s" % e)
        return 2

    # --- PVP_EXCLUSIONS map ---
    m = re.search(r"var PVP_EXCLUSIONS = ", src)
    if not m:
        check("S1 coverage tickers all in PVP_EXCLUSIONS", False, "PVP_EXCLUSIONS not found")
        return 1
    try:
        excl_block = extract_balanced(src, m.start(), "{", "}")
    except ValueError as e:
        check("S1 coverage tickers all in PVP_EXCLUSIONS", False, "unbalanced braces: %s" % e)
        return 1
    excl_entries = re.findall(r"^\s*'([A-Z0-9]+)'\s*:\s*'(.*)'\s*,?\s*$", excl_block, re.M)
    excl_keys = [k for k, _ in excl_entries]
    excl_reasons = dict(excl_entries)

    # --- PVP_COVERAGE_EXCLUSION_GROUPS array ---
    g = re.search(r"var PVP_COVERAGE_EXCLUSION_GROUPS = ", src)
    if not g:
        check("S1 coverage tickers all in PVP_EXCLUSIONS", False, "PVP_COVERAGE_EXCLUSION_GROUPS not found")
        return 1
    try:
        groups_block = extract_balanced(src, g.start(), "[", "]")
    except ValueError as e:
        check("S1 coverage tickers all in PVP_EXCLUSIONS", False, "unbalanced brackets: %s" % e)
        return 1
    group_recs = re.findall(r"\['([^']+)', \[(.*?)\]\]", groups_block, re.S)
    if not group_recs:
        check("S1 coverage tickers all in PVP_EXCLUSIONS", False, "no coverage groups parsed")
        return 1
    grouped = []
    for label, tickers_src in group_recs:
        grouped.append((label, re.findall(r"'([A-Z0-9.\-]+)'", tickers_src)))
    cov_tickers = [t for _, ts in grouped for t in ts]
    cov_set = set(cov_tickers)
    map_set = set(excl_keys)

    # S1: coverage union ⊆ map keys
    missing = sorted(cov_set - map_set)
    check(
        "S1 coverage tickers all in PVP_EXCLUSIONS",
        not missing,
        ("no reason for: " + ",".join(missing)) if missing
        else "%d/%d coverage tickers have map reasons" % (len(cov_set), len(cov_set)),
    )

    # S2: map − coverage == same-issuer-duplicate class, pinned three ways
    diff = sorted(map_set - cov_set)
    pattern_keys = {}
    for k in excl_keys:
        pm = SAME_ISSUER_RE.search(excl_reasons.get(k, ""))
        if pm:
            pattern_keys[k] = pm.group(1)
    s2_problems = []
    if set(diff) != set(pattern_keys):
        s2_problems.append(
            "diff=%s pattern-class=%s"
            % (diff, sorted(pattern_keys))
        )
    try:
        _, pvp_tickers, gaps = live_gaps()
        gap_set = set(gaps)
        for k, ref in pattern_keys.items():
            if k in gap_set:
                s2_problems.append("%s is a live gap, not a shipped-once duplicate" % k)
            if ref not in pvp_tickers:
                s2_problems.append("%s names %s but %s is not PvP-covered" % (k, ref, ref))
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print("INFRA: cannot compute live gaps: %s" % e)
        return 2
    check(
        "S2 map-coverage difference == same-issuer-duplicate class",
        not s2_problems,
        ("; ".join(s2_problems)) if s2_problems
        else "diff=%s pinned (%s)" % (diff, ", ".join("%s->%s" % (k, pattern_keys[k]) for k in diff)),
    )

    # S3: no ticker in two coverage groups
    seen = {}
    dupes = set()
    for label, ts in grouped:
        for t in ts:
            if t in seen:
                dupes.add(t)
            seen[t] = label
    check("S3 no ticker in multiple coverage groups", not dupes,
          ("dupes=" + ",".join(sorted(dupes))) if dupes
          else "%d tickers across %d groups" % (len(seen), len(grouped)))

    return 0 if all(ok for _, ok, _ in results) else 1


def main():
    if "--static-only" in sys.argv:
        rc = static_checks()
    else:
        # No render half: the invariant is purely static. Default == static.
        rc = static_checks()
    fails = [n for n, ok, _ in results if not ok]
    print("%d/%d checks passed" % (len(results) - len(fails), len(results)))
    if rc == 2:
        sys.exit(2)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
