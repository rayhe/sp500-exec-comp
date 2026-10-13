#!/usr/bin/env python3
"""Regression guard: the README's Pay-vs-Performance prose must match live data.

Background (2026-10-12 23:30 PT): the PvP method-note JS fallback literals
("498"/"2466"/"518"/"38") are sync-guarded against data files by
scripts/check_pvp_method_coverage_sync.py (S1-S4), but the README's
data-file-map prose carries the same four facts in hand-typed form and had
NO guard:
  line 21: "498 companies, 2,466 company-years (as of wave 38, 2026-09-30)"
  line 75: "pay_vs_performance.json  # 402(v): 498 companies, 2,466
           company-years, Inline-XBRL-verified (as of wave 38)"
A wave-39 shipment would re-vintage the data + JS literals (with guards
firing on the JS) and could leave the README's PvP entry stale: prose
"498 companies, 2,466 company-years (as of wave 38, 2026-09-30)" lying next
to live data files that already carry wave 39. This is the hand-typed-copy /
vintage-stale-prose class (same family as the 70th provenance-census and
71st stub-marker guards, and the section-21 intro-clause extension), applied
to the PvP dataset entry in the README data-file map.

This guard:
  S1: the README pay_vs_performance.json data-file entry's
      "<N> companies, <M> company-years" matches pvp metadata.companies /
      metadata.company_years
  S2: its "(as of wave <W>, <date>)" marker matches the latest "wave <W>"
      marker in pvp coverage_note AND that wave's "of <date>" date
  S3: the README tree-map entry "(as of wave <W>)" matches the same live
      wave, and its "<N> companies, <M> company-years" matches live counts
  S4: every "company-years" occurrence in README is one of the two guarded
      lines (no third hand-typed PvP count surface that could drift)

Usage:
  scripts/check_readme_pvp_vintage.py              # static checks
  scripts/check_readme_pvp_vintage.py --static-only # same (pre-commit contract)

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
PVP_JSON = os.path.join(REPO, "data", "pay_vs_performance.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def latest_wave(note):
    """Return (wave_number, wave_date) for the latest 'wave N of YYYY-MM-DD'
    marker in the coverage note, or (None, None)."""
    hits = [(int(m.group(1)), m.group(2), m.start())
            for m in re.finditer(r"[Ww]ave (\d+) of (\d{4}-\d{2}-\d{2})", note or "")]
    if not hits:
        return None, None
    best = max(hits, key=lambda h: h[0])
    return best[0], best[1]


def static_checks():
    readme = open(README, encoding="utf-8").read()
    pvp = json.load(open(PVP_JSON, encoding="utf-8"))
    pvp_md = pvp.get("metadata", {})

    live_companies = pvp_md.get("companies")
    live_years = pvp_md.get("company_years")
    live_wave, live_date = latest_wave(pvp_md.get("coverage_note"))

    # S1: data-file entry counts == live pvp metadata
    m = re.search(
        r"pay_vs_performance\.json[^\n]*?(\d[\d,]*)\s+companies?,\s*"
        r"(\d[\d,]*)\s+company-years\s*\(as of wave (\d+),\s*(\d{4}-\d{2}-\d{2})\)",
        readme,
    )
    ok = False
    detail = "data-file entry not found"
    if m:
        cos = int(m.group(1).replace(",", ""))
        yrs = int(m.group(2).replace(",", ""))
        ok = (cos == live_companies) and (yrs == live_years)
        detail = "readme=%s/%s data=%s/%s" % (cos, yrs, live_companies, live_years)
    check("S1 README PvP entry counts match pvp metadata", ok, detail)

    # S2: "(as of wave W, date)" == latest wave + wave date from coverage_note
    ok = False
    detail = "data-file entry not found"
    if m:
        w = int(m.group(3))
        dt = m.group(4)
        ok = (w == live_wave) and (dt == live_date)
        detail = "readme=wave %s %s data=wave %s %s" % (w, dt, live_wave, live_date)
    check("S2 README PvP entry wave marker + date match coverage_note", ok, detail)

    # S3: tree-map entry counts + wave == live
    m3 = re.search(
        r"pay_vs_performance\.json\s+#\s*402\(v\):\s*(\d[\d,]*)\s+companies?,\s*"
        r"(\d[\d,]*)\s+company-years[^\n]*?\(as of wave (\d+)\)",
        readme,
    )
    ok = False
    detail = "tree-map entry not found"
    if m3:
        cos = int(m3.group(1).replace(",", ""))
        yrs = int(m3.group(2).replace(",", ""))
        w = int(m3.group(3))
        ok = (cos == live_companies) and (yrs == live_years) and (w == live_wave)
        detail = "readme=%s/%s wave %s data=%s/%s wave %s" % (
            cos, yrs, w, live_companies, live_years, live_wave)
    check("S3 README PvP tree-map counts + wave match live", ok, detail)

    # S4: no third hand-typed PvP count surface in README
    lines = readme.split("\n")
    stray = [ln.strip()[:80] for ln in lines
             if "company-years" in ln
             and "pay_vs_performance.json" not in ln
             and "(as of wave" not in ln]
    check("S4 no stray PvP company-year prose in README", not stray,
          "; ".join(stray) if stray else "")


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
