#!/usr/bin/env python3
"""DQ 2026-09-28 18:00 PT: close the MRNA + HUM queued investigations.

Two queued investigations closed in one batch (both triaged by the
2026-09-28 02:00 PT batch as separate investigations with distinct
signatures). Whole-company SCT re-reads, cell-by-cell, from the primary
2026 DEF 14A HTML filings (fetched from EDGAR via the VM egress proxy;
www.sec.gov reachable this run, no browser recovery path needed).

MRNA (Moderna Inc., 12 SCT rows = 4 NEOs x 3 years). 2026 DEF 14A
(acc. 0001308179-26-000081, filed 2026-03-16). KEY FILING FACT: MRNA's SCT
has NO Pension/NQDC column. Columns: Name and Principal Position / Year /
Salary / Non-Equity Plan Incentive Compensation / Bonus / Stock Awards(1) /
Option Awards(1) / All Other Compensation / Total. 2024/2023 columns
cross-checked identical vs the 2025 DEF 14A SCT (acc. 0001308179-25-000082,
filed 2025-03-11) - no restatements.

Two corruption families in one company:
(A) salary-drop column shift (8 rows: all 2023/2024 rows for Bancel, Mock,
Hoge, Klinger): parser dropped the Salary cell; filing.salary->dropped,
filing.NEIP->stored.salary, filing.stock->stored.bonus,
filing.options->stored.stock_awards, filing.all_other->stored.option_awards,
filing.total->stored.all_other, stored.total recomputed ~1.9-2x phantom.
E.g. Bancel 2024 stored $38,126,475 vs filing $19,876,180.
(B) split-currency Family B on the Bancel 2025 row ONLY (the latest-year
row renders each value preceded by a standalone "$" cell; the other 2025
rows render normally and parsed clean): parser mapped
filing.salary->stored.non_equity_incentive,
filing.NEIP->stored.stock_awards, dropped stock/options/all_other, stored
salary=0, recomputed total=salary+NEIP - UNDERSTATES the filing
($5,980,099 vs $19,932,217).

Clean (3 rows): Mock 2025, Hoge 2025, Klinger 2025 match the filing to the
dollar on every component - asserted, not rewritten, not relabeled.

HUM (Humana Inc., 11 SCT rows = 5 NEOs: 6x2025 + 3x2024 + 2x2023). 2026 DEF
14A (acc. 0001104659-26-024393, filed 2026-03-06). Columns: Name and
Principal Position / Year / Salary ($) / Bonus ($) / Stock Awards ($)(1) /
Option Awards ($)(2) / Non-Equity Incentive Plan Compensation ($)(3) /
Change in Pension Value and Nonqualified Deferred Compensation Earnings ($)
/ All Other Compensation ($)(4) / Total ($). Shetty 2024/2023 columns
cross-checked identical vs the 2025 DEF 14A SCT (acc. 0001193125-25-048976,
filed 2025-03-07) - no restatements. The 2025-proxy SCT confirms Diamond
2024/2023 and Rechtin 2024 match the 2026 proxy too.

One corruption family at HUM: "bonus-only" parse (6 rows: Mellet, Mehta,
O'Hara, Shetty 2025; Shetty 2024/2023): the parser kept ONLY the Bonus
cell, landing it in stored.option_awards for the 2025 rows and in
stored.stock_awards for the Shetty continuation rows, and recomputed
stored.total = bonus alone - every row UNDERSTATES the filing. All 6
corrupted NEOs carry footnote markers (5)/(6)/(7)/(8) in the name cell;
the 5 clean rows (Rechtin x2, Diamond x3) parsed fine. E.g. Mellet 2025
stored $6,000,000 vs filing $18,922,704; Shetty 2023 stored $1,400,000 vs
filing $4,581,941.

Transcription confidence: every transcribed filing row foots exactly
(components sum to printed total), and the 8 clean rows' transcribed values
match the stored 'verified' rows field-for-field, so a transcription digit
error is effectively ruled out. All 15 repaired rows relabeled
def14a_verified_20260928 (moving inside the verified class, so
verified_total stays 7,044).

Anchors (guard section 5: fiscal_year, NOT proxy_fiscal_year):
- MRNA fiscal_year=2024: total_neo_compensation 122,912,406 -> 63,638,941
  (filing-verbatim FY2024 row sums); CEO total_compensation 38,126,475 ->
  19,876,180 (Bancel FY2024 filing-verbatim); pay ratio stays 93
  (19,876,180 / 213,200 = 93.2 -> 93). This moves MRNA from the pay-ratio
  near-2x cluster into the within-tolerance band.
- HUM fiscal_year=2025: total_neo_compensation 34,190,005 -> 65,725,589;
  CEO total_compensation unchanged 18,757,075 (Rechtin 2025 was clean);
  pay ratio stays 226 (18,757,075 / 82,935 = 226.2 -> 226).

Phantom: -$88,128,132 removed (all MRNA Family A) / +$54,554,906 restored
(MRNA Bancel 2025 +$13,952,118; HUM +$40,602,788). Net batch phantom
-$33,573,226.
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260928_1800_pre_dqbatch.json")

COMP = ["salary", "bonus", "stock_awards", "option_awards",
        "non_equity_incentive", "pension_nqdc", "all_other"]


def rows(ticker, entries):
    return [(ticker,) + e for e in entries]


# (name, year, current-stored components, filing-verbatim fix)
MRNA_ROWS = rows("MRNA", [
    # Stephane Bancel - Family B split-currency (2025), Family A (2024/2023)
    ("Stéphane Bancel", 2025,
     {"salary": 0, "bonus": 0, "stock_awards": 4302360, "option_awards": 0,
      "non_equity_incentive": 1677739, "pension_nqdc": 0, "all_other": 0,
      "total": 5980099},
     {"salary": 1677739, "bonus": 0, "stock_awards": 6897455,
      "option_awards": 6897425, "non_equity_incentive": 4302360,
      "pension_nqdc": 0, "all_other": 157238, "total": 19932217}),
    ("Stéphane Bancel", 2024,
     {"salary": 1965600, "bonus": 7654730, "stock_awards": 7654752,
      "option_awards": 975213, "non_equity_incentive": 0, "pension_nqdc": 0,
      "all_other": 19876180, "total": 38126475},
     {"salary": 1625885, "bonus": 0, "stock_awards": 7654730,
      "option_awards": 7654752, "non_equity_incentive": 1965600,
      "pension_nqdc": 0, "all_other": 975213, "total": 19876180}),
    ("Stéphane Bancel", 2023,
     {"salary": 1913625, "bonus": 3129194, "stock_awards": 9387713,
      "option_awards": 1074520, "non_equity_incentive": 0, "pension_nqdc": 0,
      "all_other": 17068514, "total": 32573566},
     {"salary": 1563462, "bonus": 0, "stock_awards": 3129194,
      "option_awards": 9387713, "non_equity_incentive": 1913625,
      "pension_nqdc": 0, "all_other": 1074520, "total": 17068514}),
    # James Mock - Family A (2024/2023)
    ("James Mock", 2024,
     {"salary": 611021, "bonus": 11507221, "stock_awards": 4252615,
      "option_awards": 15525, "non_equity_incentive": 0, "pension_nqdc": 0,
      "all_other": 17212582, "total": 33598964},
     {"salary": 826200, "bonus": 0, "stock_awards": 11507221,
      "option_awards": 4252615, "non_equity_incentive": 611021,
      "pension_nqdc": 0, "all_other": 15525, "total": 17212582}),
    ("James Mock", 2023,
     {"salary": 583200, "bonus": 1460282, "stock_awards": 1460295,
      "option_awards": 21100, "non_equity_incentive": 0, "pension_nqdc": 0,
      "all_other": 4317185, "total": 7842062},
     {"salary": 792308, "bonus": 0, "stock_awards": 1460282,
      "option_awards": 1460295, "non_equity_incentive": 583200,
      "pension_nqdc": 0, "all_other": 21100, "total": 4317185}),
    # Stephen Hoge - Family A (2024/2023)
    ("Stephen Hoge, M.D", 2024,
     {"salary": 1447992, "bonus": 4422698, "stock_awards": 2211340,
      "option_awards": 15525, "non_equity_incentive": 0, "pension_nqdc": 0,
      "all_other": 9181478, "total": 17279033},
     {"salary": 1083923, "bonus": 0, "stock_awards": 4422698,
      "option_awards": 2211340, "non_equity_incentive": 1447992,
      "pension_nqdc": 0, "all_other": 15525, "total": 9181478}),
    ("Stephen Hoge, M.D", 2023,
     {"salary": 850500, "bonus": 2711792, "stock_awards": 2711966,
      "option_awards": 22600, "non_equity_incentive": 0, "pension_nqdc": 0,
      "all_other": 7339166, "total": 13636024},
     {"salary": 1042308, "bonus": 0, "stock_awards": 2711792,
      "option_awards": 2711966, "non_equity_incentive": 850500,
      "pension_nqdc": 0, "all_other": 22600, "total": 7339166}),
    # Shannon Thyme Klinger - Family A (2024/2023)
    ("Shannon Thyme Klinger", 2024,
     {"salary": 763776, "bonus": 11507317, "stock_awards": 4252615,
      "option_awards": 15525, "non_equity_incentive": 0, "pension_nqdc": 0,
      "all_other": 17368701, "total": 33907934},
     {"salary": 829468, "bonus": 0, "stock_awards": 11507317,
      "option_awards": 4252615, "non_equity_incentive": 763776,
      "pension_nqdc": 0, "all_other": 15525, "total": 17368701}),
    ("Shannon Thyme Klinger", 2023,
     {"salary": 583200, "bonus": 1460282, "stock_awards": 1460295,
      "option_awards": 24103, "non_equity_incentive": 0, "pension_nqdc": 0,
      "all_other": 4312496, "total": 7840376},
     {"salary": 784616, "bonus": 0, "stock_awards": 1460282,
      "option_awards": 1460295, "non_equity_incentive": 583200,
      "pension_nqdc": 0, "all_other": 24103, "total": 4312496}),
])

HUM_ROWS = rows("HUM", [
    # Celeste M. Mellet - bonus-only (2025)
    ("Celeste M. Mellet", 2025,
     {"salary": 0, "bonus": 0, "stock_awards": 0, "option_awards": 6000000,
      "non_equity_incentive": 0, "pension_nqdc": 0, "all_other": 0,
      "total": 6000000},
     {"salary": 900000, "bonus": 6000000, "stock_awards": 10651166,
      "option_awards": 0, "non_equity_incentive": 1327603,
      "pension_nqdc": 43935, "all_other": 0, "total": 18922704}),
    # Japan A. Mehta - bonus-only (2025)
    ("Japan A. Mehta", 2025,
     {"salary": 0, "bonus": 0, "stock_awards": 0, "option_awards": 4300000,
      "non_equity_incentive": 0, "pension_nqdc": 0, "all_other": 0,
      "total": 4300000},
     {"salary": 618750, "bonus": 4300000, "stock_awards": 3908903,
      "option_awards": 0, "non_equity_incentive": 732787,
      "pension_nqdc": 0, "all_other": 4123, "total": 9564563}),
    # Michelle A. O'Hara - bonus-only (2025)
    ("Michelle A. O’Hara", 2025,
     {"salary": 0, "bonus": 0, "stock_awards": 0, "option_awards": 2500000,
      "non_equity_incentive": 0, "pension_nqdc": 0, "all_other": 0,
      "total": 2500000},
     {"salary": 715385, "bonus": 2500000, "stock_awards": 4863176,
      "option_awards": 0, "non_equity_incentive": 840000,
      "pension_nqdc": 0, "all_other": 24077, "total": 8942638}),
    # Sanjay K. Shetty - bonus-only (2025 lands in options; 2024/2023 in stock)
    ("Sanjay K. Shetty, M.D.", 2025,
     {"salary": 0, "bonus": 0, "stock_awards": 0, "option_awards": 250000,
      "non_equity_incentive": 0, "pension_nqdc": 0, "all_other": 0,
      "total": 250000},
     {"salary": 715769, "bonus": 250000, "stock_awards": 5063055,
      "option_awards": 0, "non_equity_incentive": 963335,
      "pension_nqdc": 0, "all_other": 163520, "total": 7155679}),
    ("Sanjay K. Shetty, M.D.", 2024,
     {"salary": 0, "bonus": 0, "stock_awards": 550000, "option_awards": 0,
      "non_equity_incentive": 0, "pension_nqdc": 0, "all_other": 0,
      "total": 550000},
     {"salary": 694808, "bonus": 550000, "stock_awards": 3798420,
      "option_awards": 623769, "non_equity_incentive": 661107,
      "pension_nqdc": 0, "all_other": 107159, "total": 6435263}),
    ("Sanjay K. Shetty, M.D.", 2023,
     {"salary": 0, "bonus": 0, "stock_awards": 1400000, "option_awards": 0,
      "non_equity_incentive": 0, "pension_nqdc": 0, "all_other": 0,
      "total": 1400000},
     {"salary": 493269, "bonus": 1400000, "stock_awards": 1401072,
      "option_awards": 449844, "non_equity_incentive": 0,
      "pension_nqdc": 0, "all_other": 837756, "total": 4581941}),
])

# Rows verified clean vs the filing (asserted, not rewritten, not relabeled)
CLEAN = [
    ("MRNA", "James Mock", 2025,
     {"salary": 852192, "bonus": 0, "stock_awards": 2452404,
      "option_awards": 1226205, "non_equity_incentive": 1311210,
      "pension_nqdc": 0, "all_other": 15750, "total": 5857761}),
    ("MRNA", "Stephen Hoge, M.D", 2025,
     {"salary": 1260000, "bonus": 0, "stock_awards": 9196606,
      "option_awards": 4598277, "non_equity_incentive": 2983500,
      "pension_nqdc": 0, "all_other": 15750, "total": 18054133}),
    ("MRNA", "Shannon Thyme Klinger", 2025,
     {"salary": 852192, "bonus": 0, "stock_awards": 2145838,
      "option_awards": 1072924, "non_equity_incentive": 1311210,
      "pension_nqdc": 0, "all_other": 15750, "total": 5397914}),
    ("HUM", "James A. Rechtin", 2025,
     {"salary": 1348558, "bonus": 0, "stock_awards": 13868141,
      "option_awards": 0, "non_equity_incentive": 3034740,
      "pension_nqdc": 0, "all_other": 505636, "total": 18757075}),
    ("HUM", "Susan M. Diamond", 2025,
     {"salary": 961075, "bonus": 0, "stock_awards": 0, "option_awards": 0,
      "non_equity_incentive": 1225000, "pension_nqdc": 0,
      "all_other": 196855, "total": 2382930}),
    ("HUM", "James A. Rechtin", 2024,
     {"salary": 1105769, "bonus": 0, "stock_awards": 7317483,
      "option_awards": 4495979, "non_equity_incentive": 1943477,
      "pension_nqdc": 0, "all_other": 716768, "total": 15579476}),
    ("HUM", "Susan M. Diamond", 2024,
     {"salary": 846192, "bonus": 0, "stock_awards": 6733897,
      "option_awards": 948087, "non_equity_incentive": 911377,
      "pension_nqdc": 0, "all_other": 177961, "total": 9617514}),
    ("HUM", "Susan M. Diamond", 2023,
     {"salary": 790000, "bonus": 0, "stock_awards": 2802776,
      "option_awards": 898145, "non_equity_incentive": 0,
      "pension_nqdc": 0, "all_other": 239812, "total": 4730733}),
]

NEW_ANCHORS = {
    "MRNA": {"fiscal_year": 2024, "neo": 63638941,
             "ceo_name": "Stéphane Bancel", "ceo_total": 19876180,
             "pay_ratio": 93, "median": 213200},
    "HUM": {"fiscal_year": 2025, "neo": 65725589,
            "ceo_name": "James A. Rechtin", "ceo_total": 18757075,
            "pay_ratio": 226, "median": 82935},
}


def main():
    d = json.load(open(PATH))
    cm = {c["ticker"]: c for c in d["companies"]}

    mrna = cm["MRNA"]
    hum = cm["HUM"]
    assert mrna["fiscal_year"] == 2024, mrna["fiscal_year"]
    assert hum["fiscal_year"] == 2025, hum["fiscal_year"]
    assert len(mrna["executives"]) == 12, len(mrna["executives"])
    assert len(hum["executives"]) == 11, len(hum["executives"])

    shutil.copy2(PATH, BACKUP)

    # 1. assert the clean rows are untouched
    for ticker, name, year, expect in CLEAN:
        e = next(e for e in cm[ticker]["executives"]
                 if e["name"] == name and e["year"] == year)
        for k, v in expect.items():
            assert (e.get(k) or 0) == v, \
                f"CLEAN-DRIFT {ticker} {name} {year}: {k} stored {e.get(k)} != {v}"
        print(f"clean verified {ticker} {year} {name}: total ${expect['total']:,}")

    # 2. repair corrupted rows filing-verbatim
    phantom_removed = 0
    restored = 0
    n = 0
    for ticker, name, year, cur, fix in MRNA_ROWS + HUM_ROWS:
        e = next(e for e in cm[ticker]["executives"]
                 if e["name"] == name and e["year"] == year)
        for k, v in cur.items():
            sv = e.get(k)
            assert (sv or 0) == (v or 0), (f"DRIFT {ticker} {name} {year}: "
                                           f"stored {k}={sv} != expected {v}")
        # filing-verbatim footing check (transcription-error tripwire)
        assert sum(fix[k] for k in COMP) == fix["total"], \
            f"FOOTING {ticker} {name} {year}"
        delta = e["total"] - fix["total"]
        if delta > 0:
            phantom_removed += delta
        else:
            restored += -delta
        for k in COMP + ["total"]:
            e[k] = fix[k]
        e["_total_source"] = "def14a_verified_20260928"
        n += 1
        print(f"repaired {ticker} {year} {name}: "
              f"${cur['total']:,} -> ${fix['total']:,}")

    # 3. re-anchor on fiscal_year (guard section 5 convention)
    for ticker, a in NEW_ANCHORS.items():
        c = cm[ticker]
        old = c["total_neo_compensation"]
        s = sum(e["total"] for e in c["executives"]
                if e["year"] == a["fiscal_year"])
        assert s == a["neo"], f"ANCHOR {ticker} sum {s} != {a['neo']}"
        c["total_neo_compensation"] = a["neo"]
        assert c["ceo_name"] == a["ceo_name"], c["ceo_name"]
        c["total_compensation"] = a["ceo_total"]
        assert c["pay_ratio"] == a["pay_ratio"], c["pay_ratio"]
        assert c["median_worker_pay"] == a["median"], c["median_worker_pay"]
        print(f"{ticker} total_neo_compensation {old:,} -> {a['neo']:,} / "
              f"CEO total_compensation -> {a['ceo_total']:,}")

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    print(f"repaired {n} rows; phantom removed ${phantom_removed:,}; "
          f"restored ${restored:,}; net ${phantom_removed - restored:,}")


if __name__ == "__main__":
    main()
