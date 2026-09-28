#!/usr/bin/env python3
"""DQ 2026-09-27 18:00 PT: repair GWW (6) + KDP (5) = 11 rows.

Continuation of the DG/PCG/FITB/GNRC/CTSH/INVH salary-drop column-shift
campaign. The generalized guard section-8 tripwire (salary==0, 1 < tot/ao < 2,
$100K-$2.5M absolute gap) flagged GWW (5) and KDP (4); filing re-reads caught
2 sibling rows the tripwire missed because the shift variant leaves a NONZERO
salary cell (filing.bonus->stored.salary):
- GWW Berardinelli-Krantz 2023: stored salary=900,000 is the filing Bonus.
- KDP Timothy Cofer 2023: stored salary=8,000,000 is the filing Bonus
  (Cofer's 2023 sign-on/transition bonus row: filing Salary 176,923).

Filing re-reads (raw HTML table cells, digit-by-digit):
- GWW: 2026 DEF 14A SCT (acc. 0001104659-26-025575, filed 2026-03-10),
  "Name and Principal Position | Year | Salary | Bonus | Stock Awards |
  Non-Equity Incentive Plan Comp. | All Other Comp. | Total" - NO options
  and NO pension columns. All 6 target rows foot exactly ($0 deltas).
  2023 columns cross-checked identical vs the 2025 DEF 14A SCT
  (acc. 0001104659-25-021496, filed 2025-03-07); no restatements.
  Shift signature (salary-drop): parser dropped the Salary cell,
  filing.stock->stored.bonus, filing.neip->stored.stock_awards,
  filing.all_other->stored.non_equity_incentive, filing.total->stored.all_other,
  stored.total recomputed ~1.8-2x. Berardinelli 2023 (bonus-content variant):
  filing.bonus->stored.salary, filing.stock->stored.bonus,
  filing.neip->stored.stock_awards, filing.all_other->stored.non_equity_incentive,
  filing.total->stored.all_other.
  GWW 2025 rows (Macpherson/Merriwether/Robbins/Berardinelli-Krantz/Tinto)
  verified clean against the filing - untouched.
- KDP: 2026 DEF 14A SCT (acc. 0001193125-26-177266, filed 2026-04-24),
  "Name and Principal Position | Year | Salary | Bonus | Stock Awards |
  Non-Equity Incentive Plan Comp. | All Other Comp. | Total" - NO options
  and NO pension columns. All 5 target rows foot exactly.
  2023 columns cross-checked identical vs the 2025 DEF 14A SCT
  (acc. 0001193125-25-096767, filed 2025-04-25); no restatements.
  Same salary-drop shift signature. Cofer 2023 is the bonus-content variant
  (filing Bonus $8,000,000 landed in stored.salary).
  All other KDP rows (Cofer 2024/2025, Johnson 2025, Gamgort 2024/2025,
  Priyadarshi 2024/2025, DiSilvestro/Gorli/Shoemaker 2025) verified clean
  against the filing - untouched.

No Bonus column content in any target row's filing except Berardinelli 2023
($900,000) and Cofer 2023 ($8,000,000) - both restored filing-verbatim.
All option_awards stay 0 (neither SCT has an options column); pension_nqdc 0.

Phantom removed: $57,402,705
  GWW anchor FY2024: 29,274,137 -> 21,117,346
    (Merriwether 2024 -3,028,192; Robbins 2024 -2,927,551;
     Berardinelli-Krantz 2024 -2,201,048)
    2023 rows (non-anchor): Merriwether -2,985,581; Robbins -2,985,581;
     Berardinelli-Krantz -4,228,773
  KDP anchor FY2024: 25,739,390 -> 23,310,189
    (Johnson 2024 -2,429,201)
    2023 rows (non-anchor): Johnson -2,179,347; Gamgort -6,120,095;
     Priyadarshi -2,577,558; Cofer -25,739,778
Rows relabeled verified/def14a_verified_20260917 -> def14a_verified_20260927 (11).
"""
import json
import sys

PATH = '/home/hatch/repos/sp500-exec-comp/data/compensation.json'
COMP = ['salary', 'bonus', 'stock_awards', 'option_awards',
        'non_equity_incentive', 'pension_nqdc', 'all_other']

# (ticker, name, year, current-stored values for drift assertion, filing-verbatim repair)
ROWS = [
    # GWW 2024 - from 2026 DEF 14A (acc. 0001104659-26-025575)
    ('GWW', 'Deidra C. Merriwether', 2024,
     dict(salary=0, bonus=2224167, stock_awards=703250, option_awards=0,
          non_equity_incentive=100775, pension_nqdc=0, all_other=3746976,
          total=6775168),
     dict(salary=718784, bonus=0, stock_awards=2224167, option_awards=0,
          non_equity_incentive=703250, pension_nqdc=0, all_other=100775,
          total=3746976)),
    # GWW 2023 - same filing (2023 columns identical in 2025 proxy)
    ('GWW', 'Deidra C. Merriwether', 2023,
     dict(salary=0, bonus=2000793, stock_awards=873905, option_awards=0,
          non_equity_incentive=110883, pension_nqdc=0, all_other=3679417,
          total=6664998),
     dict(salary=693836, bonus=0, stock_awards=2000793, option_awards=0,
          non_equity_incentive=873905, pension_nqdc=0, all_other=110883,
          total=3679417)),
    ('GWW', 'Paige K. Robbins', 2024,
     dict(salary=0, bonus=2123526, stock_awards=703250, option_awards=0,
          non_equity_incentive=100775, pension_nqdc=0, all_other=3646335,
          total=6573886),
     dict(salary=718784, bonus=0, stock_awards=2123526, option_awards=0,
          non_equity_incentive=703250, pension_nqdc=0, all_other=100775,
          total=3646335)),
    ('GWW', 'Paige K. Robbins', 2023,
     dict(salary=0, bonus=2000793, stock_awards=873905, option_awards=0,
          non_equity_incentive=110883, pension_nqdc=0, all_other=3679417,
          total=6664998),
     dict(salary=693836, bonus=0, stock_awards=2000793, option_awards=0,
          non_equity_incentive=873905, pension_nqdc=0, all_other=110883,
          total=3679417)),
    ('GWW', 'Nancy L. Berardinelli-Krantz', 2024,
     dict(salary=0, bonus=1618307, stock_awards=504400, option_awards=0,
          non_equity_incentive=78341, pension_nqdc=0, all_other=2842346,
          total=5043394),
     dict(salary=641298, bonus=0, stock_awards=1618307, option_awards=0,
          non_equity_incentive=504400, pension_nqdc=0, all_other=78341,
          total=2842346)),
    # GWW Berardinelli-Krantz 2023 - bonus-content shift variant (filing.bonus->stored.salary)
    ('GWW', 'Nancy L. Berardinelli-Krantz', 2023,
     dict(salary=900000, bonus=2400939, stock_awards=576293, option_awards=0,
          non_equity_incentive=351541, pension_nqdc=0, all_other=4794910,
          total=9023683),
     dict(salary=566137, bonus=900000, stock_awards=2400939, option_awards=0,
          non_equity_incentive=576293, pension_nqdc=0, all_other=351541,
          total=4794910)),
    # KDP 2024 - from 2026 DEF 14A (acc. 0001193125-26-177266)
    ('KDP', 'Roger Johnson', 2024,
     dict(salary=0, bonus=1082498, stock_awards=519209, option_awards=0,
          non_equity_incentive=827494, pension_nqdc=0, all_other=3119586,
          total=5548787),
     dict(salary=690385, bonus=0, stock_awards=1082498, option_awards=0,
          non_equity_incentive=519209, pension_nqdc=0, all_other=827494,
          total=3119586)),
    ('KDP', 'Roger Johnson', 2023,
     dict(salary=0, bonus=1106991, stock_awards=374400, option_awards=0,
          non_equity_incentive=697956, pension_nqdc=0, all_other=2779347,
          total=4958694),
     dict(salary=600000, bonus=0, stock_awards=1106991, option_awards=0,
          non_equity_incentive=374400, pension_nqdc=0, all_other=697956,
          total=2779347)),
    ('KDP', 'Robert Gamgort', 2023,
     dict(salary=0, bonus=4335741, stock_awards=1755000, option_awards=0,
          non_equity_incentive=29354, pension_nqdc=0, all_other=7620095,
          total=13740190),
     dict(salary=1500000, bonus=0, stock_awards=4335741, option_awards=0,
          non_equity_incentive=1755000, pension_nqdc=0, all_other=29354,
          total=7620095)),
    ('KDP', 'Sudhanshu Priyadarshi', 2023,
     dict(salary=0, bonus=2029504, stock_awards=530400, option_awards=0,
          non_equity_incentive=17654, pension_nqdc=0, all_other=3427558,
          total=6005116),
     dict(salary=850000, bonus=0, stock_awards=2029504, option_awards=0,
          non_equity_incentive=530400, pension_nqdc=0, all_other=17654,
          total=3427558)),
    # KDP Cofer 2023 - bonus-content shift variant (filing Bonus $8M -> stored.salary)
    ('KDP', 'Timothy Cofer', 2023,
     dict(salary=8000000, bonus=17463228, stock_awards=172027, option_awards=0,
          non_equity_incentive=104523, pension_nqdc=0, all_other=25916701,
          total=51656479),
     dict(salary=176923, bonus=8000000, stock_awards=17463228, option_awards=0,
          non_equity_incentive=172027, pension_nqdc=0, all_other=104523,
          total=25916701)),
]

NEW_ANCHORS = {
    'GWW': 21117346,
    'KDP': 23310189,
}

def main():
    d = json.load(open(PATH))
    companies = d['companies'] if isinstance(d, dict) else d
    cm = {c['ticker']: c for c in companies}
    phantom = 0
    for ticker, name, year, cur, fix in ROWS:
        c = cm[ticker]
        e = next(e for e in c['executives']
                 if e['name'] == name and e['year'] == year)
        for k, v in cur.items():
            assert e.get(k) == v, (f"DRIFT {ticker} {name} {year}: "
                                   f"stored {k}={e.get(k)} != expected {v}")
        # filing-verbatim footing check
        assert sum(fix[k] for k in COMP) == fix['total'], \
            (f"FOOTING {ticker} {name} {year}")
        phantom += e['total'] - fix['total']
        for k in COMP + ['total']:
            e[k] = fix[k]
        e['_total_source'] = 'def14a_verified_20260927'
        print(f"repaired {ticker} {year} {name}: "
              f"${cur['total']:,} -> ${fix['total']:,}")
    for ticker, new_total in NEW_ANCHORS.items():
        c = cm[ticker]
        old = c['total_neo_compensation']
        c['total_neo_compensation'] = new_total
        assert sum(e['total'] for e in c['executives']
                   if e['year'] == 2024) == new_total, \
            (f"ANCHOR {ticker} 2024 sum mismatch")
        print(f"{ticker} total_neo_compensation {old:,} -> {new_total:,}")
    json.dump(d, open(PATH, 'w'), indent=1)
    print(f"phantom removed: ${phantom:,}")

if __name__ == '__main__':
    main()
