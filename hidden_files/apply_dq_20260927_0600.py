#!/usr/bin/env python3
"""DQ 2026-09-27 06:00 PT: repair DG (Dollar General) salary-drop column-shift family.

Discovery: the guard section-8 tripwire (|total - 2*all_other| <= 10% of total)
systematically misses the shift variant where the dropped salary is a LARGER
fraction of the filing total. Dollar General's SCT has no Bonus and no
Change-in-Pension column (7 data columns); the parser dropped the Salary cell,
shifting filing.stock->stored.bonus, filing.options->stored.stock,
filing.neip->stored.options, filing.all_other->stored.neip,
filing.total->stored.all_other, and recomputed stored.total at ~1.7x the
filing total. For Dilts 2024 the gap |tot - 2*ao| = 762,529 = the filing salary
to the dollar (bullseye), but 762,529 > 10% x 4,920,833, so the tripwire was
silent. Same family exists at GNRC/GWW/PCG/FITB/INVH/AEE/KDP/KMB/WEC/XEL/CHD/
JCI/LW/WRB/CTSH (48-row generalized-signature candidate set) - queued for
filing-by-filing verification in later batches; each repair needs its own
DEF 14A SCT re-read (arithmetic inference is not filing-verbatim).

This batch: all 11 DG rows (2023 x5, 2024 x6) repaired filing-verbatim.
- 2024 rows: 2026 DEF 14A SCT (acc. 0001104659-26-040394, filed 2026-04-07)
  re-read digit-by-digit from raw HTML table cells (table 115).
- 2023 rows: 2024 DEF 14A SCT (acc. 0001104659-24-044304, filed 2024-04-05)
  re-read digit-by-digit (table 28); 2025/2026 proxy reprints agree.
All 11 components foot to the printed filing total with $0 delta.
Titles verified clean (no parser artifacts) and untouched.

Phantom removed: $26,832,235 (2024: 28,805,112 -> 16,967,220;
2023: 33,543,237 -> 18,548,894). Company total_neo_compensation re-anchored
to the filing-verbatim FY2024 sum 16,967,220.
Rows relabeled verified -> def14a_verified_20260927 (11 rows).
"""
import json
import sys

PATH = '/home/hatch/repos/sp500-exec-comp/data/compensation.json'
COMP = ['salary', 'bonus', 'stock_awards', 'option_awards',
        'non_equity_incentive', 'pension_nqdc', 'all_other']

# (name, year, current-stored values for drift assertion, filing-verbatim repair)
ROWS = [
    # 2024 - from 2026 DEF 14A (acc. 0001104659-26-040394)
    ('Todd J. Vasos', 2024,
     dict(salary=0, bonus=0, stock_awards=0, option_awards=214849,
          non_equity_incentive=537454, pension_nqdc=0, all_other=2152357,
          total=2904660),
     dict(salary=1400054, bonus=0, stock_awards=0, option_awards=0,
          non_equity_incentive=214849, pension_nqdc=0, all_other=537454,
          total=2152357)),
    ('Kelly M. Dilts', 2024,
     dict(salary=0, bonus=965509, stock_awards=992754, option_awards=58700,
          non_equity_incentive=62189, pension_nqdc=0, all_other=2841681,
          total=4920833),
     dict(salary=762529, bonus=0, stock_awards=965509, option_awards=992754,
          non_equity_incentive=58700, pension_nqdc=0, all_other=62189,
          total=2841681)),
    ('Emily C. Taylor', 2024,
     dict(salary=0, bonus=1103527, stock_awards=1134570, option_awards=63227,
          non_equity_incentive=104437, pension_nqdc=0, all_other=3225790,
          total=5631551),
     dict(salary=820029, bonus=0, stock_awards=1103527, option_awards=1134570,
          non_equity_incentive=63227, pension_nqdc=0, all_other=104437,
          total=3225790)),
    ('Rhonda M. Taylor', 2024,
     dict(salary=0, bonus=1103527, stock_awards=1134570, option_awards=57299,
          non_equity_incentive=107737, pension_nqdc=0, all_other=3146287,
          total=5549420),
     dict(salary=743154, bonus=0, stock_awards=1103527, option_awards=1134570,
          non_equity_incentive=57299, pension_nqdc=0, all_other=107737,
          total=3146287)),
    ('Carman R. Wenkoff', 2024,
     dict(salary=0, bonus=965509, stock_awards=992754, option_awards=54479,
          non_equity_incentive=60526, pension_nqdc=0, all_other=2780970,
          total=4854238),
     dict(salary=707702, bonus=0, stock_awards=965509, option_awards=992754,
          non_equity_incentive=54479, pension_nqdc=0, all_other=60526,
          total=2780970)),
    ('Steven R. Deckard', 2024,
     dict(salary=0, bonus=965509, stock_awards=992754, option_awards=53712,
          non_equity_incentive=112300, pension_nqdc=0, all_other=2820135,
          total=4944410),
     dict(salary=695860, bonus=0, stock_awards=965509, option_awards=992754,
          non_equity_incentive=53712, pension_nqdc=0, all_other=112300,
          total=2820135)),
    # 2023 - from 2024 DEF 14A (acc. 0001104659-24-044304)
    ('Todd J. Vasos', 2023,
     dict(salary=0, bonus=0, stock_awards=7952550, option_awards=0,
          non_equity_incentive=375106, pension_nqdc=0, all_other=8980117,
          total=17307773),
     dict(salary=652461, bonus=0, stock_awards=0, option_awards=7952550,
          non_equity_incentive=0, pension_nqdc=0, all_other=375106,
          total=8980117)),
    ('Kelly M. Dilts', 2023,
     dict(salary=0, bonus=275980, stock_awards=898569, option_awards=0,
          non_equity_incentive=63390, pension_nqdc=0, all_other=1965200,
          total=3203139),
     dict(salary=727261, bonus=0, stock_awards=275980, option_awards=898569,
          non_equity_incentive=0, pension_nqdc=0, all_other=63390,
          total=1965200)),
    ('Emily C. Taylor', 2023,
     dict(salary=0, bonus=919726, stock_awards=867222, option_awards=0,
          non_equity_incentive=139007, pension_nqdc=0, all_other=2695492,
          total=4621447),
     dict(salary=769537, bonus=0, stock_awards=919726, option_awards=867222,
          non_equity_incentive=0, pension_nqdc=0, all_other=139007,
          total=2695492)),
    ('Rhonda M. Taylor', 2023,
     dict(salary=0, bonus=919726, stock_awards=867222, option_awards=0,
          non_equity_incentive=134203, pension_nqdc=0, all_other=2633855,
          total=4555006),
     dict(salary=712704, bonus=0, stock_awards=919726, option_awards=867222,
          non_equity_incentive=0, pension_nqdc=0, all_other=134203,
          total=2633855)),
    ('Carman R. Wenkoff', 2023,
     dict(salary=0, bonus=781736, stock_awards=737157, option_awards=0,
          non_equity_incentive=62749, pension_nqdc=0, all_other=2274230,
          total=3855872),
     dict(salary=692588, bonus=0, stock_awards=781736, option_awards=737157,
          non_equity_incentive=0, pension_nqdc=0, all_other=62749,
          total=2274230)),
]

NOTE_2024 = (
    "DQ 2026-09-27 06:00 PT: salary-drop column-shift repair (wide-gap "
    "sub-variant). Dollar General's SCT has no Bonus and no Change-in-Pension "
    "column; the parser dropped the Salary cell, shifting filing.stock->"
    "stored.bonus, filing.options->stored.stock, filing.neip->stored.options, "
    "filing.all_other->stored.neip, filing.total->stored.all_other, and "
    "recomputed stored.total at ~1.7x the filing total. The guard section-8 "
    "tripwire was silent because the dropped salary exceeds 10% of the "
    "stored total (Dilts 2024: gap 762,529 = filing salary to the dollar). "
    "Repaired filing-verbatim from the 2026 DEF 14A SCT (acc. "
    "0001104659-26-040394, filed 2026-04-07), values read digit-by-digit from "
    "raw HTML table cells; components foot to the printed total with $0 "
    "delta. Title verified clean, untouched. "
    "https://www.sec.gov/Archives/edgar/data/29534/000110465926040394/tm261322-1_def14a.htm"
)
NOTE_2023 = (
    "DQ 2026-09-27 06:00 PT: salary-drop column-shift repair (wide-gap "
    "sub-variant). Same corruption class as the 2024 rows (Dollar General "
    "SCT has no Bonus/Change-in-Pension column; parser dropped Salary, "
    "shifted every component one column left, printed total landed in "
    "all_other, stored total recomputed ~1.7x phantom). Repaired "
    "filing-verbatim from the 2024 DEF 14A SCT (acc. 0001104659-24-044304, "
    "filed 2024-04-05), values read digit-by-digit from raw HTML table "
    "cells; components foot to the printed total with $0 delta. Title "
    "verified clean, untouched. "
    "https://www.sec.gov/Archives/edgar/data/29534/000110465924044304/tm2332854d3_def14a.htm"
)


def main():
    d = json.load(open(PATH))
    comp = next(c for c in d['companies'] if c.get('ticker') == 'DG')
    idx = {(e.get('name'), e.get('year')): e for e in comp['executives']}

    # Pre-write drift assertions on exact stored values.
    for name, year, stored, _ in ROWS:
        e = idx.get((name, year))
        assert e is not None, f'MISSING ROW {name} {year}'
        for k, v in stored.items():
            assert e.get(k) == v, \
                f'DRIFT {name} {year} {k}: expected {v}, found {e.get(k)}'

    # Apply repairs.
    for name, year, _, fixed in ROWS:
        e = idx[(name, year)]
        for k, v in fixed.items():
            e[k] = v
        e['_total_source'] = 'def14a_verified_20260927'
        e['_repair_note_20260927'] = NOTE_2024 if year == 2024 else NOTE_2023

    # Post-repair footing assertions ($0 delta vs printed filing total).
    for name, year, _, fixed in ROWS:
        e = idx[(name, year)]
        s = sum(e.get(k) or 0 for k in COMP)
        assert s == e['total'], \
            f'NOT-FOOT {name} {year}: components sum {s} != total {e["total"]}'
        assert e['salary'] > 0, f'SALARY STILL 0 {name} {year}'

    # Re-anchor company FY2024 aggregate to the filing-verbatim sum.
    fy2024_sum = sum(e['total'] for e in comp['executives']
                     if e.get('year') == 2024)
    old_agg = comp.get('total_neo_compensation')
    assert old_agg == 28805112, f'AGG DRIFT: {old_agg}'
    assert fy2024_sum == 16967220, f'FY2024 sum {fy2024_sum}'
    comp['total_neo_compensation'] = fy2024_sum

    fy2023_sum = sum(e['total'] for e in comp['executives']
                     if e.get('year') == 2023)
    assert fy2023_sum == 18548894, f'FY2023 sum {fy2023_sum}'

    # Phantom accounting.
    old_2024 = sum(v['total'] for _, y, v, _ in ROWS if y == 2024)
    old_2023 = sum(v['total'] for _, y, v, _ in ROWS if y == 2023)
    phantom = (old_2024 - 16967220) + (old_2023 - 18548894)
    assert phantom == 26832235, f'phantom {phantom}'

    # Metadata truthfulness: both date fields advance with the batch.
    d['last_updated'] = '2026-09-27'
    d['metadata']['last_dq_repair'] = '2026-09-27'

    with open(PATH, 'w') as f:
        json.dump(d, f, indent=1, ensure_ascii=True)
        f.write('\n')

    print(f'OK: 11 DG rows repaired filing-verbatim, '
          f'phantom removed ${phantom:,}, '
          f'FY2024 aggregate {old_agg:,} -> {fy2024_sum:,}')


if __name__ == '__main__':
    main()
