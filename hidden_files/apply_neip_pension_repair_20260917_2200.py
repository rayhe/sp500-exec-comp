#!/usr/bin/env python3
"""DQ batch 2026-09-17 22:00 PT: NEO-component column misallocation repair, EG.

Class: non_equity_incentive -> pension_nqdc column confusion. Everest Group's
2026 DEF 14A SCT (eg-20260406.htm, filed 2026-04-06, acc. 000162828026024596)
has NO pension column at all (8 data cells: Year, Salary, Bonus, Restricted
Stock, PSU, Non-Equity Incentive, All Other, Total). The 2026-09-08 re-parse
mapped Jill Beggs 2025's $51,650 Non-Equity Incentive Plan Compensation value
into `pension_nqdc`, leaving `non_equity_incentive` at 0. Invisible to every
component-sum screen because the 8-component total still foots exactly.

Verified filing-verbatim from the primary DEF 14A: every other EG row already
matches the filing on all components (Andrade bonus==restricted-stock is
genuine filer disclosure, not a parse error; the full EG x filing diff was
run 2026-09-17 22:00 PT - only Beggs 2025 neip differed).

Repair: pension_nqdc 51650 -> 0, non_equity_incentive 0 -> 51650. Total
unchanged ($3,696,473); 8-component sum re-asserted.
"""
import json, shutil, os

REPO = os.path.expanduser('~/repos/sp500-exec-comp')
DATA = os.path.join(REPO, 'data/compensation.json')
NOTE_KEY = '_repair_note_20260917_2200'
LABEL = 'def14a_verified_20260917'
OLD_LABEL = 'def14a_verified_20260908'

shutil.copy2(DATA, os.path.join(REPO, 'hidden_files',
    'compensation_backup_20260917_2200_pre_neippension.json'))

d = json.load(open(DATA))
comps = {c['ticker']: c for c in d['companies']}

eg = comps['EG']
rows = [e for e in eg['executives'] if e['name'] == 'Jill Beggs' and e['year'] == 2025]
assert len(rows) == 1, len(rows)
e = rows[0]
assert e['pension_nqdc'] == 51650 and (e.get('non_equity_incentive') or 0) == 0, e

e['non_equity_incentive'] = 51650
e['pension_nqdc'] = 0
e['_total_source'] = LABEL
e[NOTE_KEY] = ('2026-09-17: moved $51,650 from pension_nqdc to non_equity_incentive; '
    'Everest 2026 DEF 14A SCT (eg-20260406.htm) has no pension column - the value '
    'is Non-Equity Incentive Plan Compensation. Filing-verbatim, total unchanged.')

# 8-component foot check
COMP8 = ['salary', 'bonus', 'stock_awards', 'option_awards', 'non_equity_incentive',
         'pension_nqdc', 'pension_change', 'all_other']
s = sum((e.get(k) or 0) for k in COMP8)
assert s == e['total'], (s, e['total'])
print('Beggs 2025 repaired: neip=51650, pension_nqdc=0, total still', e['total'])

# apply ONLY the row-level repair; company aggregates are total-neutral
# (repair moves $51,650 between component columns, total unchanged), and the
# section-5 aggregate convention is fiscal_year (EG fiscal_year=2025), so
# aggregates are left untouched.

json.dump(d, open(DATA, 'w'), indent=2)
print('saved', DATA)
