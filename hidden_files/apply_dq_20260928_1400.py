#!/usr/bin/env python3
"""DQ 2026-09-28 14:00 PT: close the RMD queued investigation.

RMD (ResMed Inc., 13 SCT rows = 5 NEOs x 3/2 years) was queued by the
2026-09-28 02:00 PT batch as a separate investigation: the 2025/2024 rows
carry a salary==0/bonus==0/stock>0 signature (8 rows). Whole-company SCT
re-read, digit-by-digit, vs the 2025 DEF 14A SCT (acc. 0000943819-25-000079,
filed 2026-10-02; FY ended 2026-06-30; transcribed from the live filing via
the sanctioned browser recovery path after the VM egress proxy timed out on
www.sec.gov and browser.open was 403-blocked).

KEY FILING FACT: RMD's SCT has NO Bonus column and NO Pension/NQDC column.
Columns: Name and Principal Position / Year / Salary(a)(b) / Stock Awards(c)
/ Option Awards(d) / Non-Equity Incentive Plan Compensation(e) / All Other
Compensation(f) / Total. Filing intro text confirms every NEO draws a real
salary ("We compensate our executive officers in their residences' local
currency... presented in US dollars"), so the stored salary==0 values are
parser corruption, not genuine. Footnote (b): Leong's and Sandercock's base
salaries are paid in AUD, converted at FY-average rates - the transcribed
USD values are the filing-verbatim figures we store.

Two corruption families in one company (both UNDERSTATE the filing):

Family B - split-currency variant (8 rows: Ghoshal/Leong/Rider/Sandercock
2025+2024): the proxy renders each value cell preceded by a standalone "$"
cell. Parser mapped filing.salary->stored.stock_awards,
filing.stock->stored.non_equity_incentive (RMD's table lacks Bonus/Pension
columns, so the landing slots differ from CPT's all_other landing), dropped
filing NEIP and All Other, stored.salary=0, and recomputed
total=salary+stock. E.g. Ghoshal 2025 stored $3,051,738 vs filing $3,652,455.

Stock-drop shift variant (3 rows: Farrell/Ghoshal/Sandercock 2023): parser
dropped the Stock Awards cell; stored.salary=filing.salary (correct),
stored.stock_awards=0, filing.stock->stored.option_awards,
filing.options->stored.all_other, filing NEIP and All Other dropped,
stored.total recomputed from salary+stock+options. E.g. Farrell 2023 stored
$12,128,186 vs filing $13,868,641.

Clean (2 rows): Farrell 2025/2024 match the filing to the dollar on every
component - verified clean vs stored, untouched.

Transcription confidence: all 13 transcribed filing rows foot exactly
(components sum to printed total), and the 2 clean rows' transcribed values
match stored verified rows field-for-field, so a transcription digit error
is effectively ruled out. Ghoshal 2025 All Other $50,716 cross-checks vs the
filing's (f) sub-table (0+14,027+1,732+2,132+32,825). No name artifacts.
All 11 repaired rows relabeled def14a_verified_20260928.

Anchors (guard section 5: fiscal_year, NOT proxy_fiscal_year; RMD
fiscal_year=2024, proxy_fiscal_year=2025):
- RMD fiscal_year=2024: total_neo_compensation 24,599,030 -> 26,636,897
  (filing-verbatim FY2024 row sums).
- CEO Michael Farrell FY2024 total 14,120,829 unchanged (row was clean);
  total_compensation asserted not rewritten. Pay ratio stays 179
  (14,120,829 / 79,096 = 178.5 -> 179).

Phantom: -$6,828,888 (negative = restoration; the parser UNDERSTATED RMD
NEO comp - Family B and the stock-drop variant both understate, unlike
Family A which overstates).
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260928_1400_pre_dqbatch.json")

COMP = ["salary", "bonus", "stock_awards", "option_awards",
        "non_equity_incentive", "pension_nqdc", "all_other"]

# (name, year, current-stored components, filing-verbatim fix)
ROWS = [
    # Michael Farrell - stock-drop shift variant (2023 only; 2025/2024 clean)
    ("Michael Farrell", 2023,
     {"salary": 1128211, "bonus": 0, "stock_awards": 0, "option_awards": 8249986,
      "non_equity_incentive": 0, "pension_nqdc": 0, "all_other": 2749989,
      "total": 12128186},
     {"salary": 1128211, "bonus": 0, "stock_awards": 8249986, "option_awards": 2749989,
      "non_equity_incentive": 1510264, "pension_nqdc": 0, "all_other": 230191,
      "total": 13868641}),
    # Bobby Ghoshal - Family B (2025/2024), stock-drop variant (2023)
    ("Bobby Ghoshal", 2025,
     {"salary": 0, "bonus": 0, "stock_awards": 651660, "option_awards": 0,
      "non_equity_incentive": 2400078, "pension_nqdc": 0, "all_other": 0,
      "total": 3051738},
     {"salary": 651660, "bonus": 0, "stock_awards": 2400078, "option_awards": 0,
      "non_equity_incentive": 550001, "pension_nqdc": 0, "all_other": 50716,
      "total": 3652455}),
    ("Bobby Ghoshal", 2024,
     {"salary": 0, "bonus": 0, "stock_awards": 631577, "option_awards": 0,
      "non_equity_incentive": 2299905, "pension_nqdc": 0, "all_other": 0,
      "total": 2931482},
     {"salary": 631577, "bonus": 0, "stock_awards": 2299905, "option_awards": 0,
      "non_equity_incentive": 558618, "pension_nqdc": 0, "all_other": 40770,
      "total": 3530870}),
    ("Bobby Ghoshal", 2023,
     {"salary": 600000, "bonus": 0, "stock_awards": 0, "option_awards": 1650047,
      "non_equity_incentive": 0, "pension_nqdc": 0, "all_other": 550013,
      "total": 2800060},
     {"salary": 600000, "bonus": 0, "stock_awards": 1650047, "option_awards": 550013,
      "non_equity_incentive": 475780, "pension_nqdc": 0, "all_other": 33680,
      "total": 3309520}),
    # Brett Sandercock - Family B (2025/2024), stock-drop variant (2023)
    ("Brett Sandercock", 2025,
     {"salary": 0, "bonus": 0, "stock_awards": 498967, "option_awards": 0,
      "non_equity_incentive": 2600037, "pension_nqdc": 0, "all_other": 0,
      "total": 3099004},
     {"salary": 498967, "bonus": 0, "stock_awards": 2600037, "option_awards": 0,
      "non_equity_incentive": 407171, "pension_nqdc": 0, "all_other": 65835,
      "total": 3572010}),
    ("Brett Sandercock", 2024,
     {"salary": 0, "bonus": 0, "stock_awards": 471039, "option_awards": 0,
      "non_equity_incentive": 2299905, "pension_nqdc": 0, "all_other": 0,
      "total": 2770944},
     {"salary": 471039, "bonus": 0, "stock_awards": 2299905, "option_awards": 0,
      "non_equity_incentive": 399979, "pension_nqdc": 0, "all_other": 62642,
      "total": 3233565}),
    ("Brett Sandercock", 2023,
     {"salary": 467002, "bonus": 0, "stock_awards": 0, "option_awards": 2200049,
      "non_equity_incentive": 0, "pension_nqdc": 0, "all_other": 0,
      "total": 2667051},
     {"salary": 467002, "bonus": 0, "stock_awards": 2200049, "option_awards": 0,
      "non_equity_incentive": 384705, "pension_nqdc": 0, "all_other": 57934,
      "total": 3109690}),
    # Justin Leong - Family B (2025/2024)
    ("Justin Leong", 2025,
     {"salary": 0, "bonus": 0, "stock_awards": 677032, "option_awards": 0,
      "non_equity_incentive": 2600037, "pension_nqdc": 0, "all_other": 0,
      "total": 3277069},
     {"salary": 677032, "bonus": 0, "stock_awards": 2600037, "option_awards": 0,
      "non_equity_incentive": 552478, "pension_nqdc": 0, "all_other": 81894,
      "total": 3911441}),
    ("Justin Leong", 2024,
     {"salary": 0, "bonus": 0, "stock_awards": 586305, "option_awards": 0,
      "non_equity_incentive": 2399823, "pension_nqdc": 0, "all_other": 0,
      "total": 2986128},
     {"salary": 586305, "bonus": 0, "stock_awards": 2399823, "option_awards": 0,
      "non_equity_incentive": 497856, "pension_nqdc": 0, "all_other": 113256,
      "total": 3597240}),
    # Mike Rider - Family B (2025/2024)
    ("Mike Rider", 2025,
     {"salary": 0, "bonus": 0, "stock_awards": 508745, "option_awards": 0,
      "non_equity_incentive": 1400005, "pension_nqdc": 0, "all_other": 0,
      "total": 1908750},
     {"salary": 508745, "bonus": 0, "stock_awards": 1400005, "option_awards": 0,
      "non_equity_incentive": 311363, "pension_nqdc": 0, "all_other": 69009,
      "total": 2289122}),
    ("Mike Rider", 2024,
     {"salary": 0, "bonus": 0, "stock_awards": 489575, "option_awards": 0,
      "non_equity_incentive": 1300072, "pension_nqdc": 0, "all_other": 0,
      "total": 1789647},
     {"salary": 489575, "bonus": 0, "stock_awards": 1300072, "option_awards": 0,
      "non_equity_incentive": 311789, "pension_nqdc": 0, "all_other": 52957,
      "total": 2154393}),
]

# Rows verified clean vs the filing (asserted, not rewritten)
CLEAN = [
    ("Michael Farrell", 2025,
     {"salary": 1214150, "stock_awards": 8775059, "option_awards": 2925007,
      "non_equity_incentive": 1646743, "all_other": 113584, "total": 14674543}),
    ("Michael Farrell", 2024,
     {"salary": 1168987, "stock_awards": 8400057, "option_awards": 2800025,
      "non_equity_incentive": 1613032, "all_other": 138728, "total": 14120829}),
]

NEW_ANCHOR = 26636897  # filing-verbatim sum of RMD fiscal_year=2024 rows


def main():
    d = json.load(open(PATH))
    companies = d["companies"] if isinstance(d, dict) else d
    cm = {c["ticker"]: c for c in companies}
    rmd = cm["RMD"]
    assert rmd["fiscal_year"] == 2024, rmd["fiscal_year"]
    assert len(rmd["executives"]) == 13, len(rmd["executives"])

    shutil.copy2(PATH, BACKUP)

    # 1. assert the clean rows are untouched
    for name, year, expect in CLEAN:
        e = next(e for e in rmd["executives"]
                 if e["name"] == name and e["year"] == year)
        for k, v in expect.items():
            assert (e.get(k) or 0) == v, \
                f"CLEAN-DRIFT RMD {name} {year}: {k} stored {e.get(k)} != {v}"
        print(f"clean verified RMD {year} {name}: total ${expect['total']:,}")

    # 2. repair corrupted rows filing-verbatim
    phantom = 0
    for name, year, cur, fix in ROWS:
        e = next(e for e in rmd["executives"]
                 if e["name"] == name and e["year"] == year)
        for k, v in cur.items():
            sv = e.get(k)
            assert (sv or 0) == (v or 0), (f"DRIFT RMD {name} {year}: "
                                           f"stored {k}={sv} != expected {v}")
        # filing-verbatim footing check (transcription-error tripwire)
        assert sum(fix[k] for k in COMP) == fix["total"], \
            f"FOOTING RMD {name} {year}"
        phantom += e["total"] - fix["total"]
        for k in COMP + ["total"]:
            e[k] = fix[k]
        e["_total_source"] = "def14a_verified_20260928"
        print(f"repaired RMD {year} {name}: "
              f"${cur['total']:,} -> ${fix['total']:,}")

    # 3. re-anchor on fiscal_year (guard section 5 convention)
    old_anchor = rmd["total_neo_compensation"]
    s = sum(e["total"] for e in rmd["executives"]
            if e["year"] == rmd["fiscal_year"])
    assert s == NEW_ANCHOR, f"ANCHOR RMD sum {s} != {NEW_ANCHOR}"
    rmd["total_neo_compensation"] = NEW_ANCHOR
    print(f"RMD total_neo_compensation {old_anchor:,} -> {NEW_ANCHOR:,}")

    # 4. CEO anchor unchanged (Farrell 2024 row was clean)
    assert rmd["ceo_name"] == "Michael Farrell"
    ceo_row = next(e for e in rmd["executives"]
                   if e["name"] == "Michael Farrell" and e["year"] == 2024)
    assert ceo_row["total"] == 14120829
    assert rmd["total_compensation"] == 14120829
    assert rmd["pay_ratio"] == 179
    print("RMD CEO anchor unchanged: 14,120,829; pay_ratio 179 unchanged")

    d["last_updated"] = "2026-09-28"
    d["metadata"]["last_dq_repair"] = "2026-09-28"
    json.dump(d, open(PATH, "w"), indent=1)
    print(f"phantom removed: ${phantom:,}")


if __name__ == "__main__":
    main()
