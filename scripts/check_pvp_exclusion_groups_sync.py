#!/usr/bin/env python3
"""Regression guard: the Data Verification modal's PvP exclusion groups must
stay in sync with the canonical PVP_EXCLUSIONS map.

New failure-mode class (2026-10-12 19:30 PT run): paired-constant desync.
js/app.js carries THREE parallel representations of the PvP exclusion set:

  1. PVP_EXCLUSIONS (canonical map ticker -> filing-grounded reason), rendered
     by company detail panels;
  2. PVP_EXCLUSION_GROUPS (grouped [{label, tickers}] for the Data
     Verification modal's exclusion list), whose own comment says
     "Union of tickers must equal Object.keys(PVP_EXCLUSIONS) ... Keep in
     sync with PVP_EXCLUSIONS";
  3. PVP_COVERAGE_EXCLUSION_GROUPS (gap classes for the PvP section coverage
     clause), guard-synced to the LIVE gap set by check_pvp_coverage_desc.py.

Representation (2) had only its code comment as the sync mechanism: a future
edit that adds/removes a ticker in PVP_EXCLUSIONS (e.g. a VMRK deferral
resolving, a new 402(v) exclusion) without touching PVP_EXCLUSION_GROUPS
would silently stale the modal -- the "N tickers are principled exclusions"
count, the group lists, and the group labels' parenthetical counts would all
lie while every existing guard stayed green (negative-tested 2026-10-12:
dropping VMRK from the Deferred group trips no existing guard).

Checks (static, fast, runs in the pre-commit hook):
  S1 union of PVP_EXCLUSION_GROUPS tickers == set(PVP_EXCLUSIONS keys),
     exactly (no missing, no extras)
  S2 no ticker appears in more than one group
  S3 each group label's parenthetical count equals its ticker-list length
     (e.g. 'Delisted / taken private (8)' really holds 8 tickers)
  S4 every grouped ticker has a non-empty PVP_EXCLUSIONS reason string, so
     the modal never renders the 'No stated reason.' fallback
  S5 the Data Verification modal renderer (_dataqPvpHtml) reads
     PVP_EXCLUSION_GROUPS (the constant is wired, not dead)

Usage:
  scripts/check_pvp_exclusion_groups_sync.py
  scripts/check_pvp_exclusion_groups_sync.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")

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


def static_checks():
    try:
        src = open(APP_JS, encoding="utf-8").read()
    except OSError as e:
        print("INFRA: cannot read js/app.js: %s" % e)
        return 2

    # --- Extract PVP_EXCLUSIONS map ---
    m = re.search(r"var PVP_EXCLUSIONS = ", src)
    if not m:
        check("S1 groups union == PVP_EXCLUSIONS keys", False, "PVP_EXCLUSIONS not found")
        return 1
    try:
        excl_block = extract_balanced(src, m.start(), "{", "}")
    except ValueError as e:
        check("S1 groups union == PVP_EXCLUSIONS keys", False, "unbalanced braces: %s" % e)
        return 1
    excl_entries = re.findall(r"^\s*'([A-Z0-9]+)'\s*:\s*'(.*)'\s*,?\s*$", excl_block, re.M)
    excl_keys = [k for k, _ in excl_entries]
    excl_reasons = dict(excl_entries)

    # --- Extract PVP_EXCLUSION_GROUPS array ---
    g = re.search(r"var PVP_EXCLUSION_GROUPS = ", src)
    if not g:
        check("S1 groups union == PVP_EXCLUSIONS keys", False, "PVP_EXCLUSION_GROUPS not found")
        return 1
    try:
        groups_block = extract_balanced(src, g.start(), "[", "]")
    except ValueError as e:
        check("S1 groups union == PVP_EXCLUSIONS keys", False, "unbalanced brackets: %s" % e)
        return 1
    group_recs = re.findall(
        r"\{\s*label:\s*'([^']+)'\s*,\s*tickers:\s*\[([^\]]*)\]\s*\}", groups_block, re.S
    )
    if not group_recs:
        check("S1 groups union == PVP_EXCLUSIONS keys", False, "no groups parsed")
        return 1

    grouped = []  # (label, [tickers])
    for label, tickers_src in group_recs:
        grouped.append((label, re.findall(r"'([A-Z0-9]+)'", tickers_src)))

    # S1: exact set equality
    union = [t for _, ts in grouped for t in ts]
    missing = sorted(set(excl_keys) - set(union))
    extra = sorted(set(union) - set(excl_keys))
    check(
        "S1 groups union == PVP_EXCLUSIONS keys",
        not missing and not extra,
        "groups=%d map=%d%s%s"
        % (
            len(set(union)),
            len(set(excl_keys)),
            (" missing=" + ",".join(missing)) if missing else "",
            (" extra=" + ",".join(extra)) if extra else "",
        ),
    )

    # S2: no ticker in two groups
    seen = {}
    dupes = set()
    for label, ts in grouped:
        for t in ts:
            if t in seen:
                dupes.add(t)
            seen[t] = label
    check("S2 no ticker in multiple groups", not dupes,
          ("dupes=" + ",".join(sorted(dupes))) if dupes else "%d tickers across %d groups" % (len(seen), len(grouped)))

    # S3: parenthetical label counts match list lengths
    bad_counts = []
    for label, ts in grouped:
        pm = re.search(r"\((\d+)\)\s*$", label)
        if not pm:
            bad_counts.append("%r (no trailing count)" % label)
        elif int(pm.group(1)) != len(ts):
            bad_counts.append("%r claims %s, holds %d" % (label, pm.group(1), len(ts)))
    check("S3 label parenthetical counts match ticker lists", not bad_counts,
          ("; ".join(bad_counts)) if bad_counts else "all %d groups" % len(grouped))

    # S4: every grouped ticker has a non-empty reason (no 'No stated reason.' fallback)
    no_reason = [t for t in set(union) if not (excl_reasons.get(t) or "").strip()]
    check("S4 every grouped ticker has a PVP_EXCLUSIONS reason", not no_reason,
          ("missing=" + ",".join(sorted(no_reason))) if no_reason else "%d/%d with reasons" % (len(set(union)) - len(no_reason), len(set(union))))

    # S5: the modal renderer is wired to the groups constant
    wired = ("_dataqPvpHtml" in src) and ("PVP_EXCLUSION_GROUPS" in src.split("_dataqPvpHtml", 1)[1].split("function openMethodologyModal", 1)[0] if "_dataqPvpHtml" in src else "")
    check("S5 _dataqPvpHtml renders from PVP_EXCLUSION_GROUPS", bool(wired),
          "modal exclusion list reads the guarded constant" if wired else "renderer not wired")

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
