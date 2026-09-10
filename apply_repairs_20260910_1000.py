"""DEF 14A rounding-bucket re-verification 2026-09-10 10:00 PT.

Re-verified the 6 largest-delta 'rounding' rows against their primary DEF 14A
SCTs (filings fetched fresh 2026-09-10). All 6 match the filing verbatim:
the components and the printed total are identical to the SCT, but the
filing's own arithmetic does not foot. Per the 2026-09-10 06:00 PT precedent
(SBUX Kelly, FDS Shan), these are genuine filing-side arithmetic
inconsistencies -> relabeled 'component_mismatch', filing totals retained.
"""
import json

COMP_KEYS = ('salary', 'bonus', 'stock_awards', 'option_awards',
             'non_equity_incentive', 'pension_nqdc', 'all_other')

# (ticker, name, year, expected_component_sum, filing_filename, extra_note)
TARGETS = [
    ('CDNS', 'Paul Cunningham', 2024, 5343116, 'd932644ddef14a.htm', ''),
    ('CDNS', 'Paul Cunningham', 2023, 4905300, 'd932644ddef14a.htm', ''),
    ('TSCO', 'Harry A. Lawton III', 2024, 11777463, 'd16327ddef14a.htm', ''),
    ('TSCO', 'Robert D. Mills', 2024, 2459417, 'd16327ddef14a.htm', ''),
    ('RF', 'John M. Turner, Jr', 2023, 9222778, 'rf-20260323.htm',
     ' The SCT "Total Without" column ($9,192,557 = total minus $25,161 pension) foots consistently.'),
    ('RF', 'David R. Keenan', 2023, 2702752, 'rf-20260323.htm', ''),
]

path = '/home/hatch/repos/sp500-exec-comp/data/compensation.json'
d = json.load(open(path))
fixed = []
for ticker, name, year, expect_sum, filing, extra in TARGETS:
    co = next(c for c in d['companies'] if c['ticker'] == ticker)
    rows = [e for e in co['executives']
            if e['name'] == name and e['year'] == year]
    assert len(rows) == 1, (ticker, name, year, len(rows))
    e = rows[0]
    assert e['_total_source'] == 'rounding', (ticker, name, year, e['_total_source'])
    comp_sum = sum(v for k, v in e.items()
                   if k in COMP_KEYS and isinstance(v, (int, float)))
    assert comp_sum == expect_sum, (ticker, name, year, comp_sum)
    total = e['total']
    gap = comp_sum - total
    e['_total_source'] = 'component_mismatch'
    e['_note'] = (
        f'Filing-printed components sum to ${comp_sum:,} vs filing-printed '
        f'total ${total:,} (gap ${gap:+,}); identical in the latest DEF 14A '
        f'SCT ({filing}) with no explanatory footnote - filing-side '
        f'arithmetic inconsistency, not a parse error.{extra}'
    )
    e['_reverify_20260910_1000'] = 'components+total match primary DEF 14A SCT verbatim; relabeled per component_mismatch taxonomy'
    fixed.append((ticker, name, year, gap))

# Rebuild quality buckets by recount
from collections import Counter
c = Counter()
for co in d['companies']:
    for e in co['executives']:
        c[e.get('_total_source', 'verified')] += 1
c['verified_total'] = (c['verified'] + c.get('def14a_verified_20260907', 0)
                       + c.get('def14a_verified_20260908', 0)
                       + c.get('def14a_verified_20260909', 0)
                       + c.get('def14a_verified_20260910', 0))
c['last_audit'] = '2026-09-10'
for sec in ('data_quality', 'data_quality_detailed'):
    d['metadata'][sec] = dict(c)
assert sum(1 for co in d['companies'] for e in co['executives']) == 6778

d['metadata']['notes'].append(
    'Rounding-bucket re-verification 2026-09-10 10:00 PT: the 6 largest-delta '
    'rounding rows (CDNS Cunningham 2024 +$20,000 / 2023 -$25,000, TSCO Lawton '
    '2024 +$4,000, TSCO Mills 2024 -$500, RF Turner 2023 +$5,060, RF Keenan '
    '2023 +$1,180) were re-verified against fresh primary DEF 14A SCTs; all '
    'components and totals match the filings verbatim, so the gaps are genuine '
    'filing-side arithmetic inconsistencies - relabeled component_mismatch '
    '(precedent: SBUX Kelly / FDS Shan). Filing totals retained verbatim. '
    'Buckets now: rounding 50, component_mismatch 10; verified_total unchanged '
    '6682/6778 (98.58%).'
)

json.dump(d, open(path, 'w'), indent=2)
print('fixed:', len(fixed))
for f in fixed:
    print(' ', f)
print('buckets:', dict(c))
