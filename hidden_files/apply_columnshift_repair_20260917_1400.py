#!/usr/bin/env python3
"""DQ batch 2026-09-17 14:00 PT: column-shift EDGAR repair, INTU + BKR.

Class: salary-cell-drop column shift (INTU 2024/2023 rows, BKR all rows) plus
last-column all_other/total conflation (INTU 2025 footnote cells, BKR 2025 rows).
All values re-parsed filing-verbatim from the current DEF 14A SCTs:
  - INTU: intu-20251126.htm (FY2025 proxy, filed 2025-11-26), SCT covers FY2025/2024/2023
  - BKR:  d939028ddef14a.htm (FY2025 proxy, filed 2026-03-30), SCT covers FY2025/2024/2023
Also deletes 2 bogus BKR rows (Ramaswamy 2025, Buese 2025) absent from the filing's SCT,
and propagates the 2026-09-06 10-Year LTIP audit note to the other 4 WELL 2025 NEO rows.
Company aggregates recomputed on the anchor-year (proxy_fy - 1) convention.
"""
import json, shutil, os

REPO = os.path.expanduser('~/repos/sp500-exec-comp')
DATA = os.path.join(REPO, 'data/compensation.json')
NOTE_KEY = '_repair_note_20260917_1400'
LABEL = 'def14a_verified_20260917'

shutil.copy2(DATA, os.path.join(REPO, 'hidden_files',
    'compensation_backup_20260917_1400_pre_columnshift5.json'))

d = json.load(open(DATA))
comps = {c['ticker']: c for c in d['companies']}

def note_intu():
    return ('2026-09-17: salary-cell-drop column-shift repair from FY2025 DEF 14A SCT '
            '(intu-20251126.htm). Values filing-verbatim; totals foot exactly.')

def note_bkr(gap=False):
    n = ('2026-09-17: column-shift rebuild from FY2025 DEF 14A SCT '
         '(d939028ddef14a.htm). Values filing-verbatim.')
    if gap:
        n += ' Components sum $1 off printed total (filing-side rounding gap, kept verbatim).'
    return n

# ---------------- INTU ----------------
# filing: Salary | Stock | Option | Non-Equity | All Other | Total
INTU_ROWS = [
    # (name, year, salary, stock, option, neip, all_other, total)
    ('Sasan K. Goodarzi', 2025, 1300000, 24285384, 8650168, 2600000, 10000, 36845552),
    ('Sasan K. Goodarzi', 2024, 1200000, 24247389, 8650027, 2280000, 194944, 36572360),
    ('Sasan K. Goodarzi', 2023, 1100000, 17840333, 6375096, 1980000, 10000, 27305429),
    ('Sandeep S. Aujla', 2025, 800000, 11007870, 3625099, 960000, 11300, 16404269),
    ('Sandeep S. Aujla', 2024, 770000, 10560586, 3500057, 877800, 11300, 15719743),
    ('Mark Notarainni', 2024, 725000, 10125439, 3375055, 688750, 11300, 14925544),
    ('Marianna Tessel', 2025, 800000, 11007870, 3625099, 960000, 10000, 16402969),
    ('Marianna Tessel', 2024, 770000, 12500970, 4125067, 877800, 12600, 18286437),
    ('Marianna Tessel', 2023, 770000, 10980607, 3625026, 831600, 10992, 16218225),
]

intu = comps['INTU']
intu_fixed = 0
for (name, year, sal, stk, opt, neip, oth, tot) in INTU_ROWS:
    rows = [e for e in intu['executives'] if e['name'] == name and e['year'] == year]
    assert len(rows) == 1, (name, year, len(rows))
    e = rows[0]
    e['salary'] = sal
    e['bonus'] = e.get('bonus', 0)
    e['stock_awards'] = stk
    e['option_awards'] = opt
    e['non_equity_incentive'] = neip
    e['pension_nqdc'] = e.get('pension_nqdc', 0)
    e['all_other'] = oth
    e['total'] = tot
    e['_total_source'] = LABEL
    e[NOTE_KEY] = note_intu()
    # sanity: components foot
    s = sal + stk + opt + neip + (e.get('pension_nqdc') or 0) + oth
    assert s == tot, (name, year, s, tot)
    intu_fixed += 1

# INTU aggregates on anchor year 2024 (proxy_fy 2025 - 1)
anchor = intu['proxy_fiscal_year'] - 1
intu_2024 = [e for e in intu['executives'] if e['year'] == anchor]
ceo_2024 = [e for e in intu_2024 if e['name'] == intu['ceo_name']][0]
intu['total_neo_compensation'] = sum(e['total'] for e in intu_2024)
intu['total_compensation'] = ceo_2024['total']
intu['neo_count'] = len(intu_2024)
print('INTU rows fixed:', intu_fixed)
print('INTU neo_agg:', intu['total_neo_compensation'], 'ceo_total:', intu['total_compensation'])

# ---------------- BKR ----------------
# filing: Salary | Bonus | Stock | Non-Equity | Pension | All Other | Total
BKR_ROWS = [
    # (name, year, title, salary, bonus, stock, neip, pension, all_other, total, gap)
    ('Lorenzo Simonelli', 2025, 'Chairman, President and CEO', 1710000, 13310819, 3557706, 911327, 1873973, 0, 21363825, False),
    ('Lorenzo Simonelli', 2024, 'Chairman, President and CEO', 1645000, 12425422, 4583200, -171000, 1414598, 0, 19897221, True),
    ('Lorenzo Simonelli', 2023, 'Chairman, President and CEO', 1589230, 12588972, 6328847, 992907, 686207, 0, 22186164, True),
    ('Ahmed Moghal', 2025, 'Chief Financial Officer', 743036, 3128458, 951008, 173400, 245663, 0, 5241565, False),
    ('Maria Claudia Borras', 2025, 'Chief Growth & Experience Officer & EVP–IET (Interim)', 970000, 3109951, 1124812, 31257, 772593, 0, 6008613, False),
    ('Maria Claudia Borras', 2024, 'Chief Growth & Experience Officer & EVP–IET (Interim)', 957692, 3088599, 1261000, -5732, 426556, 0, 5728116, True),
    ('Maria Claudia Borras', 2023, 'Chief Growth & Experience Officer & EVP–IET (Interim)', 950000, 3236726, 2566623, 38128, 252000, 0, 7043477, False),
    ('Amerino Gatti', 2025, 'Executive Vice President–OFSE', 900000, 2591564, 971010, 23474, 166798, 0, 4652846, False),
    ('Georgia Magno', 2025, 'Chief Legal Officer', 669231, 1554976, 821926, 0, 313608, 0, 3359741, False),
    ('Georgia Magno', 2024, 'Chief Legal Officer', 555959, 1235452, 910000, 0, 215678, 0, 2917089, False),
    ('Nancy Buese', 2024, 'Former Executive Vice President and Chief Financial Officer', 969231, 3603366, 1400000, 7250, 342440, 0, 6322286, True),
    ('Nancy Buese', 2023, 'Former Executive Vice President and Chief Financial Officer', 919230, 3776191, 1330000, 2721, 142274, 0, 6170415, True),
    ('Ganesh Ramaswamy', 2024, 'Former Executive Vice President–IET', 896154, 2573833, 1395000, 539, 216933, 0, 5082458, True),
    ('Ganesh Ramaswamy', 2023, 'Former Executive Vice President–IET', 824519, 2500000, 4697231, 1174658, 0, 102979, 9299386, True),
]

bkr = comps['BKR']
# drop the 2 bogus rows absent from the filing SCT
before = len(bkr['executives'])
bkr['executives'] = [e for e in bkr['executives']
                     if not (e['name'] == 'Ganesh Ramaswamy' and e['year'] == 2025)
                     and not (e['name'] == 'Nancy Buese' and e['year'] == 2025)]
dropped = before - len(bkr['executives'])
assert dropped == 2, dropped

bkr_fixed = 0
for (name, year, title, sal, bon, stk, neip, pen, oth, tot, gap) in BKR_ROWS:
    rows = [e for e in bkr['executives'] if e['name'] == name and e['year'] == year]
    assert len(rows) == 1, (name, year, len(rows))
    e = rows[0]
    e['title'] = title
    e['salary'] = sal
    e['bonus'] = bon
    e['stock_awards'] = stk
    e['option_awards'] = 0
    e['non_equity_incentive'] = neip
    e['pension_nqdc'] = pen
    e['all_other'] = oth
    e['total'] = tot
    e['_total_source'] = LABEL
    e[NOTE_KEY] = note_bkr(gap)
    s = sal + bon + stk + neip + pen + oth
    assert abs(s - tot) <= 2, (name, year, s, tot)
    bkr_fixed += 1

anchor = bkr['proxy_fiscal_year'] - 1
bkr_anchor = [e for e in bkr['executives'] if e['year'] == anchor]
ceo_bkr = [e for e in bkr_anchor if e['name'] == bkr['ceo_name']][0]
bkr['total_neo_compensation'] = sum(e['total'] for e in bkr_anchor)
bkr['total_compensation'] = ceo_bkr['total']
bkr['neo_count'] = len(bkr_anchor)
print('BKR rows fixed:', bkr_fixed, '| bogus rows dropped:', dropped)
print('BKR neo_agg:', bkr['total_neo_compensation'], 'ceo_total:', bkr['total_compensation'])
# pay ratio cross-check: 19897221/74104 = 268.5 -> 269 (stored ratio unchanged)
print('BKR ratio check:', round(bkr['total_compensation'] / bkr['median_worker_pay']))
# INTU ratio check: 36572360/200562 = 182.3 -> 182 (stored ratio unchanged)
print('INTU ratio check:', round(intu['total_compensation'] / intu['median_worker_pay']))

# ---------------- WELL: propagate 10-Year LTIP note ----------------
WELL_NOTE = ('audit 2026-09-17: FY2025 stock awards include the one-time 10-Year LTIP award '
             '(${amt:,} grant-date fair value, Welltower OP LLC LTIP Units); per 2026 DEF 14A, '
             'NEOs agreed to no additional compensation 2026-01-01..2035-12-31 beyond the LTIP '
             'awards and a $110,000 annual base salary.')
well = comps['WELL']
well_noted = 0
for e in well['executives']:
    if e['year'] == 2025 and '_note' not in e:
        e['_note'] = WELL_NOTE.format(amt=e['stock_awards'])
        well_noted += 1
print('WELL 2025 rows noted:', well_noted)

json.dump(d, open(DATA, 'w'), indent=2)
print('saved', DATA)
