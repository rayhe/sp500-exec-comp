#!/usr/bin/env python3
"""318th review (2026-11-02 14:30 PT): no-pension-column SCT misalignment repair (CBRE + FIS).

The queued variant-F sweep (standalone footnote-marker cells consumed as component
values, Binda/Cole-2025 shape, 312th review) screened the full dataset:
  - strict screen (bonus>0, stock==0, option==0, neip>=1M, total foots): 1 hit,
    CBRE Vikram Kohli FY2025.
  - lowered screen (neip>=300k): +1 hit, WRB Lucille T. Sgaglione FY2025.
  - tiny-stock screen (0<stock<50): 0 hits.

WRB Sgaglione FY2025 adjudicated FALSE POSITIVE against the 2026 DEF 14A SCT
(acc. 0001193125-26-170583, filed 2026-04-22): the (7) footnote marker on the
Bonus cell did NOT corrupt the parse; stored row byte-equals the filing
(742,102 / 1,100,000 / 0 / 366,050 / 101,412 / 2,309,564). All 17 WRB SCT rows
verified byte-equal -- WRB joins the do-not-re-arbitrate list. No variant-F
instances found beyond ARE (312th review, already repaired).

CBRE Kohli FY2025 turned out to be a different corruption family: CBRE's 2026
DEF 14A SCT (acc. 0001193125-26-141285, filed 2026-04-03; raw HTML cached at
goal hidden_files/wtw-residual-20261004/CBRE_def14a.htm) has NO Option Awards
and NO Pension columns (6 data columns). The legacy parser misaligned rows on
such tables. Company-wide arbitration of all 5 FY2025 CBRE rows found 3
corrupted (all total-neutral relabels):

  Robert E. Sulentic 2025: filing 1,350,000 / -- / 19,023,324 / 3,638,824 /
      312,891 / 24,325,039. Stored had filing All Other ($312,891) in
      pension_nqdc with all_other=0. Repair: pension 312,891->0,
      all_other 0->312,891.
  Emma E. Giamartino 2025: filing 775,000 / -- / 5,102,505 / 1,476,347 /
      38,578 / 7,392,430. Stored invented bonus=$1,462,500 (a number appearing
      NOWHERE in the filing -- parser artifact) by splitting filing stock:
      1,462,500 + 3,640,005 = 5,102,505. Repair: bonus 1,462,500->0,
      stock_awards 3,640,005->5,102,505.
  Vikram Kohli 2025: filing 850,000 / 1,450,000 / 5,696,094 / 1,684,019 /
      38,898 / 9,719,011. Stored variant-H shape: stock=0,
      neip=5,696,094 (=filing stock), pension=1,684,019 (=filing NEIP),
      ao=38,898. Repair: stock 0->5,696,094, neip 5,696,094->1,684,019,
      pension 1,684,019->0.
  Hodari 2025, Doellinger 2025: byte-equal, no change.

FIS's 2026 DEF 14A SCT (acc. 0001136893-26-000026, filed 2026-04-28; fetched
this run to goal hidden_files/dq_20261102_1430/fis_2026_def14a.htm) HAS an
Option Awards column but NO Pension column. The legacy parser filed NEIP into
pension_nqdc on every row, option->NEIP on the two rows with real option
grants, and variant-H-shifted Kehoe 2024 (whose filing Option cell is empty,
not even an em-dash). All 12 FIS rows repaired (all total-neutral):

  Ferris 2025: neip 0->2,812,500, pension 2,812,500->0 (filing 1,250,000 / -- /
      18,741,367 / -- / 2,812,500 / 124,545 / 22,928,412)
  Ferris 2024: neip 0->2,301,600, pension 2,301,600->0 (filing 1,200,000 / -- /
      17,571,281 / -- / 2,301,600 / 170,604 / 21,243,485)
  Ferris 2023: option ABSENT->6,479,998, neip 6,479,998->2,856,220,
      pension 2,856,220->0 (filing 1,000,000 / -- / 9,005,347 / 6,479,998 /
      2,856,220 / 92,177 / 19,433,742)
  Kehoe 2025: neip 0->1,462,500, pension 1,462,500->0 (filing 975,000 / -- /
      6,078,310 / -- / 1,462,500 / 10,500 / 8,526,310)
  Kehoe 2024: stock 0->6,312,006, neip 6,312,006->1,402,538,
      pension 1,402,538->0 (filing 975,000 / -- / 6,312,006 / (empty) /
      1,402,538 / 10,350 / 8,699,894)
  Kehoe 2023: MISSING from the dataset -- the 2026 proxy SCT carries Kehoe
      2023 as a continuation row (355,469 / 1,700,000 / 9,999,986 / -- /
      761,056 / 35,586 / 12,852,097). Queued for a missing-row batch
      (needs the 2024 DEF 14A NEO determination); NOT restored here.
  Bhathena 2025: neip 0->980,000, pension 980,000->0 (filing 700,000 / -- /
      4,040,163 / -- / 980,000 / 10,500 / 5,730,663)
  Bhathena 2024: neip 0->872,690, pension 872,690->0 (filing 700,000 / -- /
      3,431,975 / -- / 872,690 / 10,350 / 5,015,015)
  Toohey 2025: neip 0->980,000, pension 980,000->0 (filing 700,000 / 250,000 /
      3,030,157 / -- / 980,000 / 18,251 / 4,978,408)
  Tsai 2025: neip 0->980,000, pension 980,000->0 (filing 700,000 / -- /
      4,040,163 / -- / 980,000 / 10,500 / 5,730,663)
  Tsai 2024: neip 0->863,042, pension 863,042->0 (filing 665,000 / -- /
      5,639,221 / -- / 863,042 / 10,350 / 7,177,613)
  Tsai 2023: option ABSENT->1,755,008, neip 1,755,008->1,169,622,
      pension 1,169,622->0 (filing 630,000 / 250,000 / 2,876,455 / 1,755,008 /
      1,169,622 / 10,817 / 6,691,902)

All 15 repairs are total-neutral: every stored total already footed exactly
and still does; phantom delta asserted $0. Company aggregates, CEO totals,
pay ratios, metadata buckets, and the dataq fallback block are untouched.
Titles and _total_source untouched per the 305th/306th ROL precedent.
The two rows gaining option_awards (Ferris 2023, Tsai 2023) normalize the
missing key on touched rows only (TSLA 2026-09-17 precedent); the
dataset-wide missing-key convention is out of scope for this run.
"""
import json
import shutil
import sys
from datetime import datetime

sys.path.insert(0, "/home/hatch/repos/sp500-exec-comp/hidden_files")
import phantom_record

REPO = "/home/hatch/repos/sp500-exec-comp"
DATA = f"{REPO}/data/compensation.json"
STAMP = datetime.now().strftime("%Y%m%d_%H%M")
BACKUP = f"{REPO}/data/compensation_backup_{STAMP}_pre_nopension_misalign.json"

COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]

ABSENT = object()


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


# (ticker, name, year): {field: (old, new)}; old=ABSENT means key must be missing
REPAIRS = {
    ("CBRE", "Robert E Sulentic", 2025): {
        "pension_nqdc": (312891, 0),
        "all_other": (0, 312891),
    },
    ("CBRE", "Emma E Giamartino", 2025): {
        "bonus": (1462500, 0),
        "stock_awards": (3640005, 5102505),
    },
    ("CBRE", "Vikram Kohli", 2025): {
        "stock_awards": (0, 5696094),
        "non_equity_incentive": (5696094, 1684019),
        "pension_nqdc": (1684019, 0),
    },
    ("FIS", "Stephanie L Ferris", 2025): {
        "non_equity_incentive": (0, 2812500),
        "pension_nqdc": (2812500, 0),
    },
    ("FIS", "Stephanie L Ferris", 2024): {
        "non_equity_incentive": (0, 2301600),
        "pension_nqdc": (2301600, 0),
    },
    ("FIS", "Stephanie L Ferris", 2023): {
        "option_awards": (ABSENT, 6479998),
        "non_equity_incentive": (6479998, 2856220),
        "pension_nqdc": (2856220, 0),
    },
    ("FIS", "James Kehoe", 2025): {
        "non_equity_incentive": (0, 1462500),
        "pension_nqdc": (1462500, 0),
    },
    ("FIS", "James Kehoe", 2024): {
        "stock_awards": (0, 6312006),
        "non_equity_incentive": (6312006, 1402538),
        "pension_nqdc": (1402538, 0),
    },
    ("FIS", "Firdaus Bhathena", 2025): {
        "non_equity_incentive": (0, 980000),
        "pension_nqdc": (980000, 0),
    },
    ("FIS", "Firdaus Bhathena", 2024): {
        "non_equity_incentive": (0, 872690),
        "pension_nqdc": (872690, 0),
    },
    ("FIS", "Robert Toohey", 2025): {
        "non_equity_incentive": (0, 980000),
        "pension_nqdc": (980000, 0),
    },
    ("FIS", "Caroline Tsai", 2025): {
        "non_equity_incentive": (0, 980000),
        "pension_nqdc": (980000, 0),
    },
    ("FIS", "Caroline Tsai", 2024): {
        "non_equity_incentive": (0, 863042),
        "pension_nqdc": (863042, 0),
    },
    ("FIS", "Caroline Tsai", 2023): {
        "option_awards": (ABSENT, 1755008),
        "non_equity_incentive": (1755008, 1169622),
        "pension_nqdc": (1169622, 0),
    },
}


def main():
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    by_ticker = {c["ticker"]: c for c in d["companies"]}

    shutil.copy2(DATA, BACKUP)
    print("backup:", BACKUP)

    n = 0
    for (ticker, name, year), fields in REPAIRS.items():
        c = by_ticker[ticker]
        rows = [e for e in c["executives"]
                if e["name"] == name and e.get("year") == year]
        check(len(rows) == 1, f"expected 1 row for {(ticker, name, year)}, got {len(rows)}")
        row = rows[0]
        for field, (old, new) in fields.items():
            if old is ABSENT:
                check(field not in row, f"{name} {year}: expected {field} absent")
            else:
                check(row.get(field) == old,
                      f"{name} {year}: {field} expected old={old}, found {row.get(field)}")
            row[field] = new
        # exact footing assertion
        s = sum(row.get(k, 0) or 0 for k in COMPS)
        check(s == row["total"],
              f"{name} {year}: footing {s} != total {row['total']}")
        n += 1
    print(f"repaired {n} rows; all foot exactly")

    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")

    delta = phantom_record.record_batch(pre_path=BACKUP)
    print("phantom delta:", delta)
    check(delta == 0, f"expected total-neutral delta 0, got {delta}")
    pr = d["metadata"]["phantom_removed"]
    print("phantom batches now:", pr["batches"], "| gross:", pr["gross_removed"],
          "| restored:", pr["restored"], "| net:", pr["cumulative"])


if __name__ == "__main__":
    main()
