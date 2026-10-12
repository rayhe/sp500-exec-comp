#!/usr/bin/env python3
"""Regression guard: the Pay-vs-Performance method note's coverage clause must
render live counts and keep its fallback literals + wave label synced to data.

Background (2026-10-12): the method sentence hard-coded "498 of 518 roster
companies (2,466 company-years; 2026-09-30 wave 38 ...)" - true the day wave 38
shipped, but the same stale-count class as the sector-comp and role-comp
descriptions (each fixed 2026-10-07 by rendering live from metadata with a
static fallback). A wave-39 shipment would silently stale the method note.
The fix adds _pvpMethodCoverageClause() in js/app.js: covered/roster/
company-years and the wave number render live from pvp metadata.companies,
metadata.company_years, the latest "Wave N" marker in metadata.coverage_note,
and comp metadata.total_companies; fallback literals on vintage-commented
lines are kept only for degraded loads.

This guard:
  S1: the covered-companies fallback literal equals pvp metadata.companies
  S2: the company-years fallback literal equals pvp metadata.company_years
  S3: the roster fallback literal equals comp metadata.total_companies
  S4: the wave fallback literal equals the latest "Wave N" marker parsed
      from pvp coverage_note
  S5: no hard-coded 'Coverage: <n> of <m> roster companies' sentence with
      bare digit literals remains outside _pvpMethodCoverageClause (the
      builder is the single source of the clause)
  S6: the builder parses the wave number from pvp coverage_note (not from
      a bare literal), and the builder is wired into the method innerHTML

Usage:
  scripts/check_pvp_method_coverage_sync.py              # static checks
  scripts/check_pvp_method_coverage_sync.py --static-only # same (pre-commit contract)

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
PVP_JSON = os.path.join(REPO, "data", "pay_vs_performance.json")
COMP_JSON = os.path.join(REPO, "data", "compensation.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def fallback_literal(src, varname):
    """Extract `var <varname> = ... : <digits>;` fallback literal (after the
    `? ... : ` data-first ternary) from the builder. Returns int or None."""
    m = re.search(
        r"var " + re.escape(varname) + r"\s*=\s*\([^;]*\)\s*\?\s*[^:;]+:\s*(\d+)\s*;",
        src,
    )
    if m:
        return int(m.group(1))
    # wave fallback uses a separate `if (wave == null ...) wave = N;` form
    m2 = re.search(r"wave == null.*?\)\s*wave\s*=\s*(\d+)\s*;", src, re.S)
    if varname == "wave" and m2:
        return int(m2.group(1))
    return None


def latest_wave(note):
    waves = [int(w) for w in re.findall(r"[Ww]ave (\d+)", note or "")]
    return max(waves) if waves else None


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    pvp = json.load(open(PVP_JSON, encoding="utf-8"))
    comp = json.load(open(COMP_JSON, encoding="utf-8"))
    pvp_md = pvp.get("metadata", {})
    comp_md = comp.get("metadata", {})

    # S1: covered fallback == pvp metadata.companies
    live_covered = pvp_md.get("companies")
    lit_covered = fallback_literal(src, "covered")
    check("S1 covered-companies fallback literal matches pvp metadata.companies",
          lit_covered == live_covered,
          "literal=%s data=%s" % (lit_covered, live_covered))

    # S2: company-years fallback == pvp metadata.company_years
    live_years = pvp_md.get("company_years")
    lit_years = fallback_literal(src, "companyYears")
    check("S2 company-years fallback literal matches pvp metadata.company_years",
          lit_years == live_years,
          "literal=%s data=%s" % (lit_years, live_years))

    # S3: roster fallback == comp metadata.total_companies
    live_roster = comp_md.get("total_companies")
    lit_roster = fallback_literal(src, "roster")
    check("S3 roster fallback literal matches comp metadata.total_companies",
          lit_roster == live_roster,
          "literal=%s data=%s" % (lit_roster, live_roster))

    # S4: wave fallback == latest Wave marker in coverage_note
    live_wave = latest_wave(pvp_md.get("coverage_note"))
    lit_wave = fallback_literal(src, "wave")
    check("S4 wave fallback literal matches latest Wave marker in coverage_note",
          lit_wave == live_wave,
          "literal=%s data=%s" % (lit_wave, live_wave))

    # S5: no hard-coded 'Coverage: <n> of <m> roster companies' with bare
    # digits remains outside the builder. The builder itself concatenates,
    # so any literal digits in that phrase are a stale-sentence regression.
    builder_start = src.find("function _pvpMethodCoverageClause()")
    builder_end = src.find("function renderPvpComparison()", builder_start)
    outside = src[:builder_start] + src[builder_end:]
    s5 = not re.search(r"Coverage:\s*\d+\s+of\s+\d+\s+roster companies", outside)
    check("S5 no hard-coded Coverage sentence outside the builder",
          s5, "bare-digit coverage sentence found outside builder" if not s5 else "")

    # S6: builder parses wave from coverage_note and is wired into the method
    builder = src[builder_start:builder_end] if builder_start >= 0 else ""
    parses_note = "coverage_note" in builder and re.search(
        r"\[Ww\]ave \(\\d\+\)", builder) is not None
    wired = "_pvpMethodCoverageClause()" in outside
    check("S6 builder parses wave from coverage_note and is wired into the method note",
          bool(parses_note) and wired,
          "parses_note=%s wired=%s" % (bool(parses_note), wired))


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
