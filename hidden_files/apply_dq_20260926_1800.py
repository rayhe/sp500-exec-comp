"""apply_dq_20260926_1800.py
Drains the 2026-09-09 component_mismatch re-verification queue.

On 2026-09-26 18:00 PT the 9 still-queued rows (CDNS x3, TSCO x2, DRI, NI,
TAP x2) were re-read digit-by-digit against the primary DEF 14A SCTs
(d932644ddef14a.htm, d16327ddef14a.htm, dri-20250804.htm,
ny20055306x771_def14a.htm, tap-20260506xdef14a.htm). Every stored component
and total matches the filing verbatim; all residuals are genuine filing-side
arithmetic inconsistencies ($-177,535 .. $+500). Totals retained verbatim,
no correction invented -- no value changes.

Also strips the stale '; queued for filing re-verification.' clause from
GEN/K/UNP/GPN/RF rows already re-verified on 2026-09-10/11/25.

Idempotent: re-running adds nothing (guards on '2026-09-26 DQ re-verified'
marker and on the absence of the stale clause).
"""
import json, shutil, sys

P = 'data/compensation.json'
VERIFIED_20260926 = {
    ('CDNS', 'Paul Scannell', 2024):
        "2026-09-26 DQ re-verified against primary DEF 14A SCT (d932644ddef14a.htm): all components and total match filing verbatim; -$177,535: components sum 4,994,992 vs printed 5,172,527 -- genuine filing-side arithmetic inconsistency; total retained verbatim, no correction invented.",
    ('CDNS', 'Paul Cunningham', 2023):
        "2026-09-26 DQ re-verified against primary DEF 14A SCT (d932644ddef14a.htm): all components and total match filing verbatim; -$25,000: components sum 4,905,300 vs printed 4,930,300 -- genuine filing-side arithmetic inconsistency; total retained verbatim, no correction invented.",
    ('CDNS', 'Paul Cunningham', 2024):
        "2026-09-26 DQ re-verified against primary DEF 14A SCT (d932644ddef14a.htm): all components and total match filing verbatim; -$20,000: components sum 5,343,116 vs printed 5,323,116 -- genuine filing-side arithmetic inconsistency; total retained verbatim, no correction invented.",
    ('TSCO', 'Harry A. Lawton III', 2024):
        "2026-09-26 DQ re-verified against primary DEF 14A SCT (d16327ddef14a.htm): all components and total match filing verbatim; -$4,000: components sum 11,777,463 vs printed 11,773,463 -- genuine filing-side arithmetic inconsistency; total retained verbatim, no correction invented.",
    ('TSCO', 'Robert D. Mills', 2024):
        "2026-09-26 DQ re-verified against primary DEF 14A SCT (d16327ddef14a.htm): all components and total match filing verbatim; +$500: components sum 2,459,417 vs printed 2,459,917 -- genuine filing-side arithmetic inconsistency; total retained verbatim, no correction invented.",
    ('DRI', 'Rajesh Vennam', 2023):
        "2026-09-26 DQ re-verified against primary DEF 14A SCT (dri-20250804.htm): all components and total match filing verbatim; +$10: components sum 3,355,319 vs printed 3,355,329 -- genuine filing-side arithmetic inconsistency; total retained verbatim, no correction invented.",
    ('NI', 'Melody Birmingham', 2024):
        "2026-09-26 DQ re-verified against primary DEF 14A SCT (ny20055306x771_def14a.htm): all components and total match filing verbatim; -$49: components sum 3,301,465 vs printed 3,301,416 -- genuine filing-side arithmetic inconsistency; total retained verbatim, no correction invented.",
    ('TAP', 'Michelle St. Jacques', 2024):
        "2026-09-26 DQ re-verified against primary DEF 14A SCT (tap-20260506xdef14a.htm): all components and total match filing verbatim; +$22: components sum 3,060,368 vs printed 3,060,390 -- genuine filing-side arithmetic inconsistency; total retained verbatim, no correction invented.",
    ('TAP', 'Natalie Maciolek', 2024):
        "2026-09-26 DQ re-verified against primary DEF 14A SCT (tap-20260506xdef14a.htm): all components and total match filing verbatim; -$30: components sum 2,402,186 vs printed 2,402,156 -- genuine filing-side arithmetic inconsistency; total retained verbatim, no correction invented.",
}
# rows already re-verified 2026-09-10/11/25 carrying stale queue wording
STALE_QUEUE_CLEANUP = [
    ('GEN', 'Vincent Pilette', 2026), ('GEN', 'Natalie M. Derse', 2026),
    ('GEN', 'Bryan S. Ko', 2026), ('K', 'David Lawlor', 2022),
    ('K', 'Gary Pilnick', 2022), ('UNP', 'V. James Vena', 2025),
    ('UNP', 'V. James Vena', 2024), ('UNP', 'Jennifer L. Hamann', 2024),
    ('UNP', 'Kenny G. Rocker', 2024), ('UNP', 'Rahul Jalali', 2024),
    ('UNP', 'Elizabeth F. Whited', 2024), ('GPN', 'Cameron M. Bready', 2025),
    ('RF', 'John M. Turner, Jr', 2023), ('RF', 'David R. Keenan', 2023),
]

def clean_stale(note):
    return note.replace('; queued for filing re-verification.', '') \
               .replace('; queued for filing re-verification', '') \
               .replace('  ', ' ').strip()

def main():
    d = json.load(open(P))
    cos = {c['ticker']: c for c in d['companies']}
    changed = 0

    def row_for(t, name, yr):
        for ex in cos[t].get('executives') or []:
            if ex['name'] == name and ex.get('year') == yr:
                return ex
        return None

    for key, note in VERIFIED_20260926.items():
        ex = row_for(*key)
        if ex is None:
            print('MISSING', key); continue
        prev = clean_stale(ex.get('_parse_note') or '')
        if '2026-09-26 DQ re-verified' not in prev:
            ex['_parse_note'] = (prev + ' | ' + note).strip(' |')
            changed += 1
    for key in STALE_QUEUE_CLEANUP:
        ex = row_for(*key)
        if ex is None:
            print('MISSING', key); continue
        new = clean_stale(ex.get('_parse_note') or '')
        if new != (ex.get('_parse_note') or ''):
            ex['_parse_note'] = new
            changed += 1
    d['metadata']['last_dq_repair'] = (
        '2026-09-26 18:00 PT: drained the 2026-09-09 component_mismatch '
        're-verification queue -- CDNS x3, TSCO x2, DRI, NI, TAP x2 all '
        're-read digit-by-digit vs primary DEF 14A SCTs; stored values match '
        'filings verbatim; all deltas are genuine filing-side arithmetic '
        'inconsistencies, totals retained verbatim; GEN/K/UNP/GPN/RF stale '
        'queue wording cleaned (already re-verified 2026-09-10/11/25)')
    d['metadata']['last_updated'] = '2026-09-26 18:00 PT'
    json.dump(d, open(P, 'w'), indent=1)
    print('changed rows:', changed)

if __name__ == '__main__':
    main()
