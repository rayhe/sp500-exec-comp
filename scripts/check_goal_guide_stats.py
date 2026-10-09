#!/usr/bin/env python3
"""Guard: hand-typed prose stats in the goal guide must match the data files.

Failure class retired (2026-10-09): prose-stat drift. The 2026-10-01
peer-network batch-3 left "718 peer network nodes, 6,700 edges" in the goal
guide; batches 8w-22 (Oct 4-5) grew the network to 1040 nodes / 7739 edges,
and the prose was still stale eight days later (found by the 06:00 iteration
run's new-failure-mode audit). The repo's own site copy was clean - every
user-visible count on the site is derived from data at render time - but the
goal guide (Goals tab, user-facing) carried the stale numbers.

This guard fails the commit loudly when any machine-verifiable stat claimed
in GOAL.md disagrees with the live data files, naming the exact fix (update
GOAL.md in the same commit - whoever grows a dataset updates the prose).
A stat with no claim found in GOAL.md is SKIPped, not failed: the goal may
intentionally drop a volatile number, and the metadata gate
(check_metadata_consistency.py) already guards the data files themselves.

Paths: data files resolve from the repo root (this script's parent dir);
GOAL.md is an absolute path on this VM (documented assumption). A
--goal-md PATH override exists for negative-testing only.

Contract: honors "--static-only" (pre-commit hook + drift canary
auto-discovery). rc 0 = pass, rc 1 = fail (blocks commit), rc 2 = infra
(unreadable file).
"""

import json
import os
import re
import sys

static_only = "--static-only" in sys.argv  # noqa: F841 (contract literal)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOAL_MD = os.path.expanduser(
    "~/workspace/goals/s-p-500-executive-compensation-tracker/GOAL.md"
)

# Optional test-only override: --goal-md /tmp/goal-copy.md
_goal_override = None
for i, a in enumerate(sys.argv):
    if a == "--goal-md" and i + 1 < len(sys.argv):
        _goal_override = sys.argv[i + 1]
if _goal_override:
    GOAL_MD = _goal_override


def _num(s):
    return int(s.replace(",", ""))


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        print("CHECK goal-guide-stats: INFRA cannot read %s: %s" % (path, e))
        sys.exit(2)


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print("CHECK goal-guide-stats: INFRA cannot parse %s: %s" % (path, e))
        sys.exit(2)


def main():
    comp = _load_json(os.path.join(REPO_ROOT, "data", "compensation.json"))
    pn = _load_json(os.path.join(REPO_ROOT, "data", "peer-network.json"))
    pvp = _load_json(os.path.join(REPO_ROOT, "data", "pay_vs_performance.json"))

    cos = comp.get("companies", comp)
    if isinstance(cos, dict):
        cos = list(cos.values())
    n_companies = len(cos)
    n_neo_rows = sum(len(c.get("executives") or []) for c in cos
                     if isinstance(c, dict))
    n_nodes = len(pn.get("nodes", []))
    n_edges = len(pn.get("edges", []))

    pc = pvp.get("companies", [])
    pvals = pc.values() if isinstance(pc, dict) else pc
    n_pvp_cos = len(pvals) if not isinstance(pc, dict) else len(pc)
    n_pvp_years = 0
    for c in pvals:
        if isinstance(c, dict):
            yrs = c.get("years") or c.get("company_years") or []
            if isinstance(yrs, list):
                n_pvp_years += len(yrs)

    prose = _load(GOAL_MD)

    # (label, regex with capture groups, expected tuple, fix hint)
    checks = [
        ("tracked companies",
         r"(\d[\d,]*)\s+companies\b",
         (n_companies,),
         "update the 'N companies' figure"),
        ("NEO rows",
         r"([\d,]+)\s+NEO rows",
         (n_neo_rows,),
         "update the 'N NEO rows' figure"),
        ("peer network nodes/edges",
         r"([\d,]+)\s+peer network nodes,\s+([\d,]+)\s+edges",
         (n_nodes, n_edges),
         "update the 'N peer network nodes, M edges' figure"),
        ("pay-vs-performance panel",
         r"([\d,]+)-company\s*/\s*([\d,]+)\s+company-year pay-vs-performance",
         (n_pvp_cos, n_pvp_years),
         "update the 'N-company / M company-year pay-vs-performance' figure"),
    ]

    failures = []
    for label, pattern, expected, hint in checks:
        m = re.search(pattern, prose)
        if not m:
            print("CHECK goal-guide-stats: SKIP %s - no claim found in GOAL.md"
                  % label)
            continue
        claimed = tuple(_num(g) for g in m.groups())
        if claimed == expected:
            print("CHECK goal-guide-stats: PASS %s = %s"
                  % (label, "/".join(str(x) for x in claimed)))
        else:
            failures.append(
                "FAIL %s: GOAL.md claims %s but data files have %s - %s "
                "(GOAL.md: %s)" % (
                    label,
                    "/".join(str(x) for x in claimed),
                    "/".join(str(x) for x in expected),
                    hint, GOAL_MD))

    if failures:
        for f in failures:
            print("CHECK goal-guide-stats: " + f)
        sys.exit(1)
    print("CHECK goal-guide-stats: all prose stats match data files")
    sys.exit(0)


if __name__ == "__main__":
    main()
