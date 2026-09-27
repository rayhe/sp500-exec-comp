#!/usr/bin/env python3
"""DQ 2026-09-27 10:00 PT: repair PCG + FITB salary-drop column-shift families.

Continuation of the DG 2026-09-27 06:00 PT batch. The generalized guard
section-8 tripwire (1 < tot/ao < 2, $100K-$2.5M absolute gap, salary==0,
bonus>0) flagged 42 candidate rows / 15 tickers; this batch repairs the
PCG (5 rows) and FITB (4 rows) families filing-verbatim.

Filing re-reads (raw HTML table cells, digit-by-digit):
- PCG 2024 rows (Glickman, Singh, Waghray): 2026 DEF 14A SCT
  (acc. 0001004980-26-000020, filed 2026-04-09), table 111. Name->row
  mapping anchored by the (6) pension footnote dollar figures
  (Glickman $20,385; Singh $26,021+$5,875=$31,896; Waghray $32,508) —
  all nine 2024 rows map uniquely.
- PCG 2023 rows (Glickman, Williams): 2025 DEF 14A SCT
  (acc. 0001004980-25-000073, filed 2025-04-10), table 118.
- FITB 2024 row (Preston): 2026 DEF 14A SCT
  (acc. 0001193125-26-098679, filed 2026-03-09), table 282
  (fully named rows; no pension column in FITB SCT).
- FITB 2023 rows (Leonard, Shaffer, Lavender): 2025 DEF 14A SCT
  (acc. 0001193125-25-045653, filed 2025-03-04), table 280;
  2023/2024 values cross-checked identical between the 2025 and 2026
  proxies.

Shift signature confirmed on all 9: parser dropped the Salary cell,
filing.stock->stored.bonus, filing.options->stored.stock (PCG) /
filing.options->stored.stock-awards... (FITB: 6 data columns, so
filing.stock->stored.bonus, filing.options->stored.stock_awards,
filing.neip->stored.option_awards, filing.all_other->stored.non_equity_incentive,
filing.total->stored.all_other), stored.total recomputed at ~2x.

PCG filing totals foot exactly except Glickman 2024 and Singh 2024
($1 filing-side deltas -> stay `verified` per the $1-$2 taxonomy rule;
Williams 2024 $1 delta is not a target row).
FITB rows foot exactly. No Bonus column content anywhere (all em-dash);
all repaired bonus=0. PCG options all 0 (no option grants in either year).

Phantom removed: $20,994,584
  PCG 2024 anchor: 63,543,232 -> 54,976,924 (Glickman -2,539,985;
    Singh -3,754,998; Waghray -2,271,325)
  FITB 2024 anchor: 40,135,176 -> 38,168,200 (Preston -1,966,976)
  2023 rows repaired but not anchor year: Glickman -3,005,429;
    Williams -952,756; Leonard -2,748,644; Shaffer -1,889,976;
    Lavender -1,864,495.
Rows relabeled verified -> def14a_verified_20260927 (9 rows).
Titles verified present and untouched (per DG batch precedent); note:
stored Williams title 'Executive Vice President' disagrees with the
filing's "VP and Controller, PG&E Corporation and VP, CFO and Controller,
Pacific Gas and Electric Company" — logged for a future title workstream.
"""
import json
import sys

PATH = '/home/hatch/repos/sp500-exec-comp/data/compensation.json'
COMP = ['salary', 'bonus', 'stock_awards', 'option_awards',
        'non_equity_incentive', 'pension_nqdc', 'all_other']

# (ticker, name, year, current-stored values for drift assertion, filing-verbatim repair)
ROWS = [
    # PCG 2024 - from 2026 DEF 14A (acc. 0001004980-26-000020), table 111
    ('PCG', 'Jason M. Glickman', 2024,
     dict(salary=0, bonus=1783968, stock_awards=0, option_awards=597924,
          non_equity_incentive=20385, pension_nqdc=137708, all_other=3309513,
          total=5849498),
     dict(salary=769529, bonus=0, stock_awards=1783968, option_awards=0,
          non_equity_incentive=597924, pension_nqdc=20385, all_other=137708,
          total=3309513)),
    ('PCG', 'Sumeet Singh', 2024,
     dict(salary=0, bonus=2650459, stock_awards=0, option_awards=872896,
          non_equity_incentive=31896, pension_nqdc=199747, all_other=4691181,
          total=8446179),
     dict(salary=936182, bonus=0, stock_awards=2650459, option_awards=0,
          non_equity_incentive=872896, pension_nqdc=31896, all_other=199747,
          total=4691181)),
    ('PCG', 'Ajay Waghray', 2024,
     dict(salary=0, bonus=1529106, stock_awards=0, option_awards=560444,
          non_equity_incentive=32508, pension_nqdc=149267, all_other=2995407,
          total=5266732),
     dict(salary=724082, bonus=0, stock_awards=1529106, option_awards=0,
          non_equity_incentive=560444, pension_nqdc=32508, all_other=149267,
          total=2995407)),
    # PCG 2023 - from 2025 DEF 14A (acc. 0001004980-25-000073), table 118
    ('PCG', 'Jason M. Glickman', 2023,
     dict(salary=0, bonus=1912843, stock_awards=0, option_awards=947689,
          non_equity_incentive=24557, pension_nqdc=120340, all_other=3748529,
          total=6753958),
     dict(salary=743100, bonus=0, stock_awards=1912843, option_awards=0,
          non_equity_incentive=947689, pension_nqdc=24557, all_other=120340,
          total=3748529)),
    ('PCG', 'Stephanie N. Williams', 2023,
     dict(salary=0, bonus=491878, stock_awards=0, option_awards=317444,
          non_equity_incentive=97380, pension_nqdc=46054, all_other=1332521,
          total=2285277),
     dict(salary=379765, bonus=0, stock_awards=491878, option_awards=0,
          non_equity_incentive=317444, pension_nqdc=97380, all_other=46054,
          total=1332521)),
    # FITB 2024 - from 2026 DEF 14A (acc. 0001193125-26-098679), table 282
    ('FITB', 'Bryan D. Preston', 2024,
     dict(salary=0, bonus=1028153, stock_awards=187500, option_awards=668750,
          non_equity_incentive=82573, pension_nqdc=0, all_other=2582938,
          total=4549914),
     dict(salary=615962, bonus=0, stock_awards=1028153, option_awards=187500,
          non_equity_incentive=668750, pension_nqdc=0, all_other=82573,
          total=2582938)),
    # FITB 2023 - from 2025 DEF 14A (acc. 0001193125-25-045653), table 280
    ('FITB', 'James C. Leonard', 2023,
     dict(salary=0, bonus=1598835, stock_awards=262502, option_awards=753500,
          non_equity_incentive=133807, pension_nqdc=0, all_other=3428260,
          total=6176904),
     dict(salary=679616, bonus=0, stock_awards=1598835, option_awards=262502,
          non_equity_incentive=753500, pension_nqdc=0, all_other=133807,
          total=3428260)),
    ('FITB', 'Robert P. Shaffer', 2023,
     dict(salary=0, bonus=1004985, stock_awards=164997, option_awards=610000,
          non_equity_incentive=109994, pension_nqdc=0, all_other=2498438,
          total=4388414),
     dict(salary=608462, bonus=0, stock_awards=1004985, option_awards=164997,
          non_equity_incentive=610000, pension_nqdc=0, all_other=109994,
          total=2498438)),
    ('FITB', 'Kevin P. Lavender', 2023,
     dict(salary=0, bonus=1004985, stock_awards=164997, option_awards=582500,
          non_equity_incentive=112013, pension_nqdc=0, all_other=2445842,
          total=4310337),
     dict(salary=581347, bonus=0, stock_awards=1004985, option_awards=164997,
          non_equity_incentive=582500, pension_nqdc=0, all_other=112013,
          total=2445842)),
]

NEW_ANCHORS = {
    'PCG': 54976924,
    'FITB': 38168200,
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
        print(f"{ticker} total_neo_compensation {old:,} -> {new_total:,}")
    json.dump(d, open(PATH, 'w'), indent=1)
    print(f"phantom removed: ${phantom:,}")

if __name__ == '__main__':
    main()
