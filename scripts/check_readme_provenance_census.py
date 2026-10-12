#!/usr/bin/env python3
"""Regression guard: the README's provenance census must match the live
data_source distribution in data/compensation.json.

Background (2026-10-12): the README's census clause ("Per-company
`data_source` labels are canonical: `SEC EDGAR DEF 14A + AFL-CIO` (438),
`SEC EDGAR DEF 14A` (73), ...") went stale the moment the VMRK roster add
assigned the `SEC EDGAR DEF 14A` label to a zero-row stub (pending its
post-merger proxy). DEF 14A-only moved 73 -> 74 while every prose sentence
built from enriched-row math (517 enriched, 511 from DEF 14A SCTs, 6
verified exceptions) stayed true - the census counts label assignments,
not enriched rows. This is the label-census drift class: a roster add that
assigns a label without rows moves the census without moving any enriched
count, so the README silently understates the roster (517 labels claimed,
518 assigned).

The fix syncs the census literal to 74 and documents the stub distinction
(zero-row VMRK stub pending its post-merger proxy).

This guard:
  S1: every `LABEL` (N[, ...]) census literal in the README's
      "Per-company `data_source` labels are canonical" clause matches the
      live data_source distribution exactly
  S2: the census literals sum to the total roster size
  S3: any zero-row company is named in the census clause (stub distinction)
  S4: the "511 from DEF 14A" figure == enriched (>=1 row) companies sourced
      from DEF 14A labels
  S5: the "517 enriched" figure == companies with >=1 executive row
  S6: the "6 verified exceptions" figure == enriched companies with
      non-DEF-14A data_source labels

Usage:
  scripts/check_readme_provenance_census.py              # static checks
  scripts/check_readme_provenance_census.py --static-only # same (pre-commit contract)

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(REPO, "README.md")
COMP_JSON = os.path.join(REPO, "data", "compensation.json")

DEF14A_LABELS = {"SEC EDGAR DEF 14A", "SEC EDGAR DEF 14A + AFL-CIO"}

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    try:
        readme = open(README, encoding="utf-8").read()
    except OSError as e:
        print("INFRA: cannot read README.md: %s" % e)
        return 2
    try:
        comp = json.load(open(COMP_JSON, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("INFRA: cannot read data/compensation.json: %s" % e)
        return 2

    companies = comp.get("companies", [])
    live = {}
    for c in companies:
        live[c.get("data_source", "?")] = live.get(c.get("data_source", "?"), 0) + 1
    enriched = [c for c in companies if c.get("executives")]
    zero_row = [c["ticker"] for c in companies if not c.get("executives")]

    m = re.search(r"Per-company `data_source` labels are canonical:(.*?)(?:—|\n\n)", readme, re.S)
    if not m:
        check("S1 census clause present", False, "clause not found in README")
        return 1
    clause = m.group(1)
    claimed = {}
    for label, num in re.findall(r"`(SEC EDGAR [^`]+)`\s*\((\d+)", clause):
        claimed[label] = int(num)

    # S1: each census literal matches the live distribution exactly.
    s1_ok = claimed == live
    detail = ""
    if not s1_ok:
        diffs = []
        for k in sorted(set(claimed) | set(live)):
            if claimed.get(k) != live.get(k):
                diffs.append("%s: README %s vs live %s" % (k, claimed.get(k), live.get(k)))
        detail = "; ".join(diffs)
    check("S1 census literals match live data_source distribution", s1_ok, detail or "7 labels in sync")

    # S2: census literals sum to the roster size.
    check(
        "S2 census sum == roster size (%d)" % len(companies),
        sum(claimed.values()) == len(companies),
        "sum=%d" % sum(claimed.values()),
    )

    # S3: any zero-row company is named in the census clause.
    unnamed = [t for t in zero_row if t not in clause]
    check(
        "S3 zero-row stubs named in census clause",
        not unnamed,
        "unnamed: %s" % ",".join(unnamed) if unnamed else "zero-row: %s" % ",".join(zero_row or ["none"]),
    )

    # S4: "511 from DEF 14A" == enriched DEF 14A-sourced companies.
    m4 = re.search(r"(\d+) from DEF 14A summary compensation tables", readme)
    def14a_enriched = sum(1 for c in enriched if c.get("data_source") in DEF14A_LABELS)
    check(
        "S4 DEF 14A-enriched figure matches live (%d)" % def14a_enriched,
        m4 is not None and int(m4.group(1)) == def14a_enriched,
        "README says %s" % (m4.group(1) if m4 else "nothing"),
    )

    # S5: "517 enriched" == companies with >=1 executive row.
    m5 = re.search(r"(\d+) enriched with full NEO breakdowns", readme)
    check(
        "S5 enriched figure matches live (%d)" % len(enriched),
        m5 is not None and int(m5.group(1)) == len(enriched),
        "README says %s" % (m5.group(1) if m5 else "nothing"),
    )

    # S6: "6 verified exceptions" == enriched non-DEF-14A-sourced companies.
    m6 = re.search(r"(\d+) verified exceptions", readme)
    exceptions = sum(1 for c in enriched if c.get("data_source") not in DEF14A_LABELS)
    check(
        "S6 verified-exceptions figure matches live (%d)" % exceptions,
        m6 is not None and int(m6.group(1)) == exceptions,
        "README says %s" % (m6.group(1) if m6 else "nothing"),
    )

    return 0 if all(ok for _, ok, _ in results) else 1


def main():
    # Pre-commit auto-discovery CONTRACT: --static-only means run the static
    # checks (same as the default path here).
    _ = "--static-only" in sys.argv
    rc = static_checks()
    fails = [n for n, ok, _ in results if not ok]
    if fails:
        print("FAIL: %d/%d checks failed" % (len(fails), len(results)))
    else:
        print("OK: %d/%d checks passed" % (len(results), len(results)))
    return rc


if __name__ == "__main__":
    sys.exit(main())
