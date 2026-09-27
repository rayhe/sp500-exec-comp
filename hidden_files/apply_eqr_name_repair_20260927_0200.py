"""DQ 2026-09-27 02:00 PT repair batch.

1. EQR company_name: "Residential" -> "Equity Residential". Truncation artifact
   found by a short-name audit; verified 100 occurrences of "Equity Residential"
   in the primary 2026 DEF 14A (eqr-20260410.htm, d939028 filing eqr-20260410 /
   accession 0001193125-26-155007). EQR/AVB are retained with historical NEO
   coverage post-VMRK merger (2026-08-17).
2. BKR 2024 negative Non-Equity Incentive Plan Comp values are filing-verbatim:
   Simonelli 2024 ($-171,000) and Borras 2024 ($-5,732) print parenthetical in the
   2026 DEF 14A SCT (d939028ddef14a.htm); components foot exactly to printed
   totals. Re-verification note stamped on the two rows; no value changes.
3. VMRK stub: EDGAR submissions re-checked 2026-09-27 — CIK 906107 has no
   Vivmark post-merger DEF 14A (only insider Forms 3/4, 144s, 8-Ks); latest DEF
   14A on the CIK remains the EQR 2026 pre-merger proxy (2026-04-14). _index_note
   refreshed to the new check date; stub remains.
"""
import json

PATH = 'data/compensation.json'
d = json.load(open(PATH))
comps = d['companies']
n = 0

for c in comps:
    if c['ticker'] == 'EQR':
        assert c['company_name'] == 'Residential', c['company_name']
        c['company_name'] = 'Equity Residential'
        c['_name_note_20260927_0200'] = (
            '2026-09-27 02:00 PT: company_name repaired Residential -> Equity '
            'Residential (truncation artifact found by short-name audit). Verified '
            'against primary 2026 DEF 14A eqr-20260410.htm (filed 2026-04-14, '
            'accession 0001193125-26-155007): 100 occurrences of "Equity '
            'Residential"; EQR was the pre-merger issuer. Retained with historical '
            'NEO coverage per VMRK merger note (2026-08-17).')
        n += 1
    if c['ticker'] == 'VMRK':
        c['_index_note'] = (
            'Added 2026-09-21 (Sept quarterly rebalance; merger of equals of '
            'AvalonBay Communities and Equity Residential closed 2026-08-17). '
            'Re-checked EDGAR submissions for CIK 906107 on 2026-09-27: no '
            'post-merger Vivmark DEF 14A yet (latest DEF 14A on the CIK is the '
            'EQR 2026 pre-merger proxy, filed 2026-04-14, accession '
            '0001193125-26-155007). Queued for enrichment when first proxy files.')

for c in comps:
    if c['ticker'] == 'BKR':
        for e in c.get('executives', []):
            if (e.get('name'), e.get('year')) in (
                    ('Lorenzo Simonelli', 2024), ('Maria Claudia Borras', 2024)):
                e['_reverify_20260927_0200'] = (
                    'Re-verified 2026-09-27 02:00 PT against primary 2026 DEF 14A '
                    'SCT (d939028ddef14a.htm): negative Non-Equity Incentive Plan '
                    'Compensation values are filing-verbatim (parenthetical: '
                    '$(171,000) Simonelli 2024, $(5,732) Borras 2024); all '
                    'components foot exactly to printed totals. Genuine '
                    'filing-side value, not a parse artifact; no correction '
                    'invented.')

json.dump(d, open(PATH, 'w'), indent=2)
print('repairs applied:', n)
