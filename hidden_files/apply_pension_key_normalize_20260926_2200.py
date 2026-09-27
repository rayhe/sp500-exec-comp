#!/usr/bin/env python3
"""DQ 2026-09-26 22:00 PT - pension key normalization.

Root cause: two repair passes (2026-09-10 relabel, 2026-09-25 APH) wrote the
"Change in Pension Value and NQDC Earnings" SCT column into a non-canonical
`pension_change` key instead of `pension_nqdc`. Result: 24 NEO rows across
7 tickers (SO x13, TFC x3, AME x3, RF x2, PPL x1, PM x1, APH x1) whose
components did not foot to their filing totals (32 component mismatches
in the DB-wide audit).

Verification (this run, digit-by-digit vs primary DEF 14A SCTs):
- SO (so-20260402.htm, filed 2026-04-03): all 13 pension values match the
  "Change in Pension Value and Nonqualified Deferred Compensation" column
  exactly; stored totals match; components+column foot exactly.
- TFC (2026 proxy): Rogers 2023 1,107,866 / Cummins 2024 480,156 /
  Cummins 2023 701,917 all verbatim.
- PPL: Sorgi 2024 1,483,614 verbatim.
- PM: Kennedy 2023 1,752,402 verbatim.
- RF (rf_def14a.htm): Turner 2023 25,161 / Keenan 2023 179,336 verbatim.
  Filing SCT misprints all_other for both rows (330,753/110,803); the true
  values (325,693/109,623) are confirmed by the filing's own
  "Total Without Change in Pension Value" column and were already stored
  verbatim (09-12 re-verification). Components foot exactly post-migration.
- AME: values footed exactly on 2026-09-10 re-verification (Zapico 2024
  212,725 / Zapico 2023 335,760 / Hardin 2024 81,548); key rename only.
- APH: Lampo 2023 2,600 kept; the $63,000 filing-side arithmetic quirk
  (components sum 3,778,717 vs printed total 3,715,717) is documented in
  _parse_note and untouched.

Repair: migrate pension_change -> pension_nqdc (additive merge if both set),
delete the pension_change key. UI (app.js) already tolerates both keys;
charts.js only reads pension_nqdc, so the canonical key fixes chart totals.

Post-repair audit: 32 -> 9 component mismatches; remaining 9 are all tagged
component_mismatch (adjudicated genuine filing-side issues: APH, CDNS x3,
FDS, NEE, SBUX, WAB, BE). 10 negative-value rows (pension decreases, BKR
NEIP clawbacks) all foot exactly to totals - filing-verbatim, no change.
"""
import json

PATH = 'data/compensation.json'

def main():
    d = json.load(open(PATH))
    moved = []
    for c in d['companies']:
        for e in c.get('executives', []):
            pc = e.get('pension_change')
            if pc not in (None, 0):
                cur = e.get('pension_nqdc')
                e['pension_nqdc'] = (cur or 0) + pc if cur not in (None, 0) else pc
                del e['pension_change']
                moved.append((c['ticker'], e['name'], e['year'], pc))
    d['last_updated'] = '2026-09-26'
    json.dump(d, open(PATH, 'w'), indent=1)
    print('migrated rows:', len(moved))
    for m in moved:
        print(m)

if __name__ == '__main__':
    main()
