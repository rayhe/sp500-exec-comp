#!/usr/bin/env python3
"""Regression guard: the Pay-vs-Performance section's coverage clause must
render live and keep its no-JS static fallback honest.

Background (2026-10-08): the PvP section (SEC Item 402(v)) covered 498 of
518 tracked companies, but the section only showed the live "498 companies"
badge -- the "of 518" context and the 20 documented exclusions (take-private,
delisted, 402(v)-exempt, no DEF 14A, filer-side XBRL errors, no Inline XBRL)
were invisible in the UI, a transparency gap the peer-network section had
already closed (renderNetworkCoverage + section 18 of check_metadata_consistency).
The fix adds #pvp-coverage-desc, rendered live by renderPvpCoverageDesc()
from compData/pvpData with named exclusion groups, textContent-only.

This guard:
  A. Static: #pvp-coverage-desc exists in index.html; renderPvpCoverageDesc
     exists in js/app.js and is textContent-only; renderPvpComparison calls
     it with the comparison rows; the union of PVP_COVERAGE_EXCLUSION_GROUPS
     tickers equals the live gap set (comp tickers minus PvP-covered
     tickers, years>0), exactly -- a newly-filed proxy (e.g. VMRK) or a new
     gap fails here until the groups + fallback are updated;
     the static fallback paragraph equals the text the renderer would
     produce from today's data, character for character.

Usage:
  scripts/check_pvp_coverage_desc.py              # static checks
  scripts/check_pvp_coverage_desc.py --static-only # same (pre-commit contract)

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
INDEX_HTML = os.path.join(REPO, "index.html")
COMP_JSON = os.path.join(REPO, "data", "compensation.json")
PVP_JSON = os.path.join(REPO, "data", "pay_vs_performance.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def live_gaps():
    comp = json.load(open(COMP_JSON, encoding="utf-8"))
    pvp = json.load(open(PVP_JSON, encoding="utf-8"))
    comp_tickers = {c["ticker"] for c in comp["companies"]}
    pvp_tickers = {t for t, c in pvp["companies"].items()
                   if isinstance(c, dict) and (c.get("years") or [])}
    return comp_tickers, pvp_tickers, sorted(comp_tickers - pvp_tickers)


def parse_groups(src):
    """Extract PVP_COVERAGE_EXCLUSION_GROUPS = [ ['label', ['A','B']], ... ]."""
    m = re.search(r"var PVP_COVERAGE_EXCLUSION_GROUPS = \[(.*?)\];",
                  src, re.S)
    if not m:
        return None
    body = m.group(1)
    groups = []
    for gm in re.finditer(r"\['([^']+)', \[(.*?)\]\]", body, re.S):
        label = gm.group(1)
        tickers = re.findall(r"'([A-Z0-9.\-]+)'", gm.group(2))
        groups.append((label, tickers))
    return groups


def expected_text(covered, tracked, groups):
    text = "Covers %d of the %d tracked companies" % (covered, tracked)
    gaps = tracked - covered
    if gaps > 0:
        clauses = ["%s (%s)" % (label, ", ".join(t)) for label, t in groups]
        text += ". %d excluded: %s." % (gaps, " \u00b7 ".join(clauses))
    else:
        text += "."
    return text


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    html = open(INDEX_HTML, encoding="utf-8").read()

    # S1: the element exists in index.html.
    s1 = 'id="pvp-coverage-desc"' in html
    check("S1 #pvp-coverage-desc exists in index.html", s1,
          "" if s1 else "element missing")

    # S2: renderer exists and is textContent-only (no innerHTML).
    fn = re.search(r"function renderPvpCoverageDesc\(rows\)\s*\{(.*?)\n\}",
                   src, re.S)
    s2 = fn is not None and ".textContent = text" in fn.group(1) \
        and "innerHTML" not in fn.group(1)
    check("S2 renderPvpCoverageDesc exists and renders textContent-only",
          s2, "" if s2 else "renderer missing or uses innerHTML")

    # S3: renderPvpComparison calls the renderer with the comparison rows.
    s3 = re.search(r"renderPvpCoverageDesc\(rows\)", src) is not None
    check("S3 renderPvpComparison calls renderPvpCoverageDesc(rows)",
          s3, "" if s3 else "call missing")

    # S4: group tickers == live gaps, exactly.
    groups = parse_groups(src)
    comp_tickers, pvp_tickers, gaps = live_gaps()
    covered, tracked = len(pvp_tickers), len(comp_tickers)
    if groups is None:
        check("S4 PVP_COVERAGE_EXCLUSION_GROUPS parses", False,
              "array literal not found")
    else:
        group_tickers = sorted(t for _, ts in groups for t in ts)
        s4 = group_tickers == gaps
        check("S4 exclusion groups cover every live gap ticker, exactly",
              s4, ("" if s4 else
                   "gaps=%s grouped=%s" % (gaps, group_tickers)))

    # S5: static fallback == renderer output for today's data.
    m = re.search(
        r'<p class="section-desc" id="pvp-coverage-desc">(.*?)</p>',
        html, re.S)
    if groups is None or m is None:
        check("S5 static fallback matches live renderer output", False,
              "element or groups unparseable")
    else:
        expected = expected_text(covered, tracked, groups)
        actual = m.group(1).replace("&middot;", "\u00b7")
        s5 = actual == expected
        check("S5 static fallback matches live renderer output (%d/%d)" %
              (covered, tracked), s5,
              "" if s5 else "fallback=%r expected=%r" % (actual, expected))


def main():
    static_only = "--static-only" in sys.argv
    try:
        static_checks()
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print("INFRA: " + str(e))
        sys.exit(2)
    fails = [n for n, ok, _ in results if not ok]
    print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
    if fails:
        print("FAILED: " + ", ".join(fails))
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
