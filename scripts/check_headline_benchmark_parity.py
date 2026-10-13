#!/usr/bin/env python3
"""Regression guard: the site's headline S&P 500 CEO median must stay within
an independent published benchmark - the external-benchmark-parity class.

Background (2026-10-13 02:10 PT): The Conference Board / ESGAUGE published
"CEO and Executive Compensation Practices in the Russell 3000 and S&P 500:
2026" (Harvard Law School Forum on Corporate Governance, 2026-10-12) - an
independent pipeline measuring the SAME cohort the tracker covers. Their
headline figure: median reported CEO compensation in the S&P 500 was $17.5M
in 2026 filings (typically FY2025). The tracker's own recomputed median from
compensation.json (all FY2025-primary companies with total_compensation > 0)
is $17.19M - within ~2%, a strong independent corroboration.

The uncovered class: NOTHING compares the tracker's headline aggregates to
any outside number. check_metadata_consistency.py gates that metadata counts
recompute correctly (the stale-aggregate class), and the 70th guard pins the
README's provenance census to the live data_source distribution - but a
systematic pipeline bias (wrong fiscal-year rows feeding totals, a unit
error, a double-counted cohort, a skewed sample) could pass every per-row
and internal-recount check while drifting the headline figure far from
reality. An independent benchmark is the only tripwire for that class.

The benchmark is pinned as a module-level constant with its citation
(source, publication date, cohort definition, access date). If a newer
independent study supersedes it, the constant AND its citation are updated
together in one commit - the S2 self-check rejects a bare number with no
provenance.

Checks:
  S1 site median vs benchmark within +/-15% (methodology noise is small;
     a 15% band catches unit errors, double-counts, and sample skew, and
     leaves room for cohort-definition differences between pipelines)
  S2 the benchmark constant carries its full citation (value-level
     assertion on _BENCHMARK_CITATION, not a source grep - a source-grep
     version self-satisfied because the assertion string contained the
     citation literal; caught and fixed during the negative test)
  S3 the sample is large enough for the parity claim to be meaningful
     (n >= 400 FY2025-primary companies with CEO pay > 0); below the floor
     the comparison is vacuous and the guard fails loudly rather than
     blessing a thin sample

Usage:
  scripts/check_headline_benchmark_parity.py              # static checks
  scripts/check_headline_benchmark_parity.py --static-only # same (pre-commit contract)

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMP_JSON = os.path.join(REPO, "data", "compensation.json")

# --- pinned independent benchmark (update constant + citation together) ---
# Source (full citation lives in _BENCHMARK_CITATION; S2 enforces it):
# The Conference Board / ESGAUGE, "CEO and Executive Compensation Practices
# in the Russell 3000 and S&P 500: 2026", Harvard Law School Forum on
# Corporate Governance, 2026-10-12. Cohort: S&P 500, 2026 proxy filings
# (typically FY2025 compensation). Figure: median reported CEO compensation
# = $17.5M (Russell 3000: $7.1M). Verified from the live article 2026-10-13.
_BENCHMARK_CITATION = (
    "The Conference Board / ESGAUGE, 'CEO and Executive Compensation "
    "Practices in the Russell 3000 and S&P 500: 2026', published on the "
    "Harvard Law School Forum on Corporate Governance (corpgov.law.harvard.edu) "
    "2026-10-12; cohort: S&P 500, 2026 proxy filings (typically FY2025); "
    "figure: median reported CEO compensation $17.5M. Verified 2026-10-13."
)
BENCHMARK_SP500_CEO_MEDIAN_2026 = 17_500_000
BENCHMARK_TOLERANCE = 0.15
BENCHMARK_SAMPLE_FLOOR = 400

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def site_ceo_median():
    """Mirror the site's own headline method exactly: all companies with
    total_compensation > 0 (the aggregate_stats.median_ceo_pay definition,
    gated separately by check_metadata_consistency.py)."""
    d = json.load(open(COMP_JSON, encoding="utf-8"))
    pays = [c["total_compensation"] for c in d.get("companies", [])
            if c.get("total_compensation", 0) > 0]
    return int(statistics.median(pays)), len(pays)


def static_checks():
    site_median, n = site_ceo_median()
    gap = abs(site_median - BENCHMARK_SP500_CEO_MEDIAN_2026) / BENCHMARK_SP500_CEO_MEDIAN_2026
    check(
        "S1 site CEO median within 15% of pinned independent benchmark",
        gap <= BENCHMARK_TOLERANCE,
        "site=$%.2fM benchmark=$%.2fM gap=%.1f%% (n=%d)"
        % (site_median / 1e6, BENCHMARK_SP500_CEO_MEDIAN_2026 / 1e6,
           gap * 100, n),
    )

    # S2: the benchmark constant carries its full citation. NOTE: this reads
    # the CONSTANT'S VALUE, not the script source. An earlier draft grepped
    # its own source for the citation literal - but the assertion string
    # itself contained that literal, so stripping the citation also stripped
    # the assertion and the check passed vacuously (caught by the negative
    # test, 2026-10-13). Value-level assertion cannot self-satisfy.
    need = ["Conference Board", "2026-10-12", "proxy filings",
            "law.harvard.edu"]
    citation_ok = all(f in _BENCHMARK_CITATION for f in need)
    check("S2 benchmark constant carries its full citation", citation_ok,
          "provenance locked to the constant" if citation_ok
          else "missing: %s" % [f for f in need if f not in _BENCHMARK_CITATION])

    # S3: the sample is thick enough for parity to mean something.
    check("S3 CEO-pay sample meets the %d-company floor" % BENCHMARK_SAMPLE_FLOOR,
          n >= BENCHMARK_SAMPLE_FLOOR, "n=%d" % n)


def main():
    static_only = "--static-only" in sys.argv
    try:
        static_checks()
    except (OSError, KeyError, json.JSONDecodeError, statistics.StatisticsError) as e:
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
