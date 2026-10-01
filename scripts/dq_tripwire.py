#!/usr/bin/env python3
"""DQ tripwire scan 2026-09-30 ~18:30 PT: footing gaps, mismatch notes,
name-year collisions on data/compensation.json."""
import json
from collections import defaultdict

REPO = '/home/hatch/repos/sp500-exec-comp'
d = json.load(open(REPO + '/data/compensation.json'))
cos = d['companies']

COMPS = ['salary', 'bonus', 'stock_awards', 'option_awards',
         'non_equity_incentive', 'pension_nqdc', 'all_other']

foot_gaps = []       # verified rows with |footing gap| >= 5000
unnoted_mm = []      # rows with big gap but no mismatch annotation
collisions = defaultdict(list)

for c in cos:
    t = c['ticker']
    for e in c.get('executives', []):
        key = (e['name'], e['year'], t)
        collisions[key].append(e)
        total = e.get('total')
        src = e.get('_total_source')
        if total is None:
            continue
        parts = [e.get(k) for k in COMPS]
        if any(v is None for v in parts):
            continue
        gap = total - sum(parts)
        if src == 'verified' and abs(gap) >= 5000:
            foot_gaps.append((t, e['name'], e['year'], total, sum(parts), gap))
        if abs(gap) >= 20000 and not (e.get('_index_note') or e.get('_note')):
            unnoted_mm.append((t, e['name'], e['year'], gap))

dup = {k: v for k, v in collisions.items() if len(v) > 1}

print('=== footing gaps >= $5K in verified rows:', len(foot_gaps))
for r in foot_gaps[:30]:
    print(' ', r)
print('=== gaps >= $20K without any note:', len(unnoted_mm))
for r in unnoted_mm[:30]:
    print(' ', r)
print('=== name-ticker-year collisions:', len(dup))
for k, v in list(dup.items())[:20]:
    print(' ', k, '->', [(x.get('title'), x.get('_total_source')) for x in v])

total_rows = sum(len(c.get('executives', [])) for c in cos)
print('companies:', len(cos), 'neo rows:', total_rows)
