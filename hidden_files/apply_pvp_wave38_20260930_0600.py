#!/usr/bin/env python3
"""Wave 38 apply script: 3-company PvP batch (2026-09-30 06:00 PT).

Ships Pay vs Performance entries for the three Sep-2026 roster adds
ARES, RDDT, XYZ into data/pay_vs_performance.json, closing the
"PvP extraction pending" class opened 2026-09-30 03:30 PT.

Every value below was verified 2026-09-30 against the printed Item 402(v)
table in the cited 2026 DEF 14A and cross-checked against the filing's
Inline XBRL ecd: facts (PeoTotalCompAmt / PeoActuallyPaidCompAmt /
NonPeoNeoAvgTotalCompAmt / NonPeoNeoAvgCompActuallyPaidAmt /
TotalShareholderRtnAmt / PeerGroupTotalShareholderRtnAmt / NetIncomeLoss /
CoSelectedMeasureAmt), with sign="-" applied for parenthesized negatives
and scale/decimals honored. Year ordering verified via ix:header context
periods (c-1 = 2025 for all three).

Source filings: ~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/pvp_wave38_20260930_0600/
  ares-20260420.htm, rddt-20260423.htm, sq-20260423.htm

Anomaly log (do not "fix" these; they are filed facts):
- ARES: Fee Related Earnings (the CSM) and Net Income are filed "$ in
  thousands"; values kept as filed with unit "$K" (CRWD/TJX precedent).
  Peer TSR = Dow Jones U.S. Asset Managers Index.
- RDDT: only 2 company-years (IPO 2024-03-21; TSR base is that date, same
  for the Dow Jones Internet Composite Index (DJINET) peer series).
  2024 net loss ($484M) printed parenthesized; XBRL fact carries sign="-".
  Revenue is the CSM (filed in millions).
- XYZ (Block): PEO Jack Dorsey's SCT total is $2.75 every year (filed).
  The filer states it has NO Company-Selected Measure under Item 402(v)
  ("we do not have a 'Company-Selected Measure.' We therefore do not
  provide a tabular list of such performance measures"), so csm is null
  (PLTR/CTRA precedent, not the APP 0.0 legacy form). Negative non-PEO
  CAP in 2021 (-$2,467,273) and 2022 (-$10,751,801) verified against
  sign="-" XBRL facts; 2022 net loss (-$540,747K) likewise. Net Income
  filed in thousands; values kept as filed with unit "$K".
- PEO names: ARES Michael J Arougheti (ecd:PeoName fact; SCT row total
  68,279,532 matches the PvP 2025 SCT exactly); RDDT Steven L. Huffman
  (XBRL "Mr. Huffman"; SCT row total 3,101,009 matches); XYZ Jack Dorsey
  (SCT row total 2.75 matches).
"""
import json, os, shutil

REPO = os.path.expanduser('~/repos/sp500-exec-comp')
PATH = os.path.join(REPO, 'data/pay_vs_performance.json')
BACKUP = os.path.join(REPO, 'hidden_files/pay_vs_performance_backup_20260930_0600_pre_wave38.json')

def yr(year, peo, nonpeo_sct, nonpeo_cap, co_tsr, peer_tsr, net_income, csm):
    return {
        'year': year,
        'nonpeo_sct': float(nonpeo_sct),
        'nonpeo_cap': float(nonpeo_cap),
        'co_tsr': float(co_tsr),
        'peer_tsr': float(peer_tsr),
        'net_income': float(net_income),
        'csm': None if csm is None else float(csm),
        'peo': [{'name': n, 'sct': float(s), 'cap': float(c)} for (n, s, c) in peo],
    }

ENTRIES = {}

# ---------------- ARES: Ares Management Corporation ----------------
ENTRIES['ARES'] = {
    'ticker': 'ARES',
    'company_name': 'Ares Management Corporation',
    'cik': '0001176948',
    'filing_date': '2026-04-20',
    'filing_url': 'https://www.sec.gov/Archives/edgar/data/1176948/000162828026026286/ares-20260420.htm',
    'peer_group': 'Dow Jones U.S. Asset Managers Index',
    'peer_labels': None,
    'csm': {'label': 'Fee Related Earnings', 'unit': '$K'},
    'net_income': {'label': 'Net Income', 'unit': '$K'},
    'notes': [
        'PEO 2021-2025: Michael J Arougheti (single PEO every year).',
        'Net Income and Fee Related Earnings filed in thousands; values kept as filed with unit $K.',
        'All SCT/CAP/TSR/peer-TSR/NI/CSM values cross-checked against Inline XBRL ecd: facts; year ordering verified via context periods.',
    ],
    'years': [
        yr(2025, [('Michael J Arougheti', 68279532, 52496782)], 30236619, 26002098, 399, 196, 426113, 1775300),
        yr(2024, [('Michael J Arougheti', 85381842, 191398092)], 27567773, 54638780, 425, 187, 440961, 1361737),
        yr(2023, [('Michael J Arougheti', 30576590, 82658840)], 14837091, 25794195, 278, 135, 474326, 1163741),
        yr(2022, [('Michael J Arougheti', 34601100, 37288439)], 13511355, 13746133, 155, 110, 167541, 994350),
        yr(2021, [('Michael J Arougheti', 70842896, 135601181)], 23162854, 25070250, 178, 141, 386748, 712308),
    ],
}

# ---------------- RDDT: Reddit, Inc. ----------------
ENTRIES['RDDT'] = {
    'ticker': 'RDDT',
    'company_name': 'Reddit, Inc.',
    'cik': '0001713445',
    'filing_date': '2026-04-23',
    'filing_url': 'https://www.sec.gov/Archives/edgar/data/1713445/000171344526000060/rddt-20260423.htm',
    'peer_group': 'Dow Jones Internet Composite Index (DJINET)',
    'peer_labels': None,
    'csm': {'label': 'Revenue', 'unit': '$M'},
    'net_income': {'label': 'Net Income', 'unit': '$M'},
    'notes': [
        'PEO 2024-2025: Steven L. Huffman (single PEO).',
        'Only 2 company-years: IPO was 2024-03-21; TSR base is that date for both the company and DJINET peer series.',
        'Negative 2024 net income ($484M) printed parenthesized; verified against the sign="-" XBRL fact.',
        'All SCT/CAP/TSR/peer-TSR/NI/CSM values cross-checked against Inline XBRL ecd: facts.',
    ],
    'years': [
        yr(2025, [('Steven L. Huffman', 3101009, 307430831)], 2702619, 47610252, 455.73, 130.94, 530, 2203),
        yr(2024, [('Steven L. Huffman', 2613869, 861753126)], 6947158, 155342721, 324.03, 118.17, -484, 1300),
    ],
}

# ---------------- XYZ: Block, Inc. ----------------
ENTRIES['XYZ'] = {
    'ticker': 'XYZ',
    'company_name': 'Block, Inc.',
    'cik': '0001512673',
    'filing_date': '2026-04-23',
    'filing_url': 'https://www.sec.gov/Archives/edgar/data/1512673/000162828026027203/sq-20260423.htm',
    'peer_group': 'S&P North American Technology Index',
    'peer_labels': None,
    'csm': None,
    'net_income': {'label': 'Net Income (Loss)', 'unit': '$K'},
    'notes': [
        'PEO 2021-2025: Jack Dorsey (single PEO every year); SCT total is $2.75 filed every year, CAP also $2.75.',
        'Filer states it has NO Company-Selected Measure under Item 402(v) ("we do not have a \'Company-Selected Measure.\' We therefore do not provide a tabular list of such performance measures"), so csm is null (PLTR/CTRA precedent).',
        'Net Income filed in thousands; values kept as filed with unit $K.',
        'Negative non-PEO CAP in 2021 (-$2,467,273) and 2022 (-$10,751,801) and the 2022 net loss (-$540,747K) verified against sign="-" XBRL facts.',
        'All SCT/CAP/TSR/peer-TSR/NI values cross-checked against Inline XBRL ecd: facts; year ordering verified via context periods.',
    ],
    'years': [
        yr(2025, [('Jack Dorsey', 2.75, 2.75)], 14211140, 10425904, 29.91, 228.99, 1305636, None),
        yr(2024, [('Jack Dorsey', 2.75, 2.75)], 13619601, 15718794, 39.05, 179.15, 2897047, None),
        yr(2023, [('Jack Dorsey', 2.75, 2.75)], 10767701, 11468047, 35.54, 131.65, 9772, None),
        yr(2022, [('Jack Dorsey', 2.75, 2.75)], 11692439, -10751801, 28.87, 81.71, -540747, None),
        yr(2021, [('Jack Dorsey', 2.75, 2.75)], 9560445, -2467273, 74.21, 126.40, 166284, None),
    ],
}

def main():
    shutil.copy2(PATH, BACKUP)
    d = json.load(open(PATH))
    cos = d['companies']
    for t, e in ENTRIES.items():
        assert t not in cos, f'{t} already shipped!'
        cos[t] = e
    n_years = sum(len(e['years']) for e in ENTRIES.values())
    assert n_years == 12, f'expected 12 company-years, got {n_years}'
    md = d['metadata']
    md['companies'] = 498
    md['company_years'] = 2454 + n_years
    md['coverage_note'] += ('; 3-company wave 38 of 2026-09-30: ARES, RDDT, XYZ '
                            '(Sep-2026 roster adds; extraction was deferred at the '
                            '2026-09-30 03:30 PT ticker normalization, now run). '
                            'XYZ has no CSM (filer states none under Item 402(v)); '
                            'RDDT has 2 company-years only (IPO 2024-03-21).')
    json.dump(d, open(PATH, 'w'), indent=1)
    print(f'shipped {len(ENTRIES)} companies, {n_years} company-years; metadata now {md["companies"]} companies / {md["company_years"]} company-years')
    print('backup:', BACKUP)

if __name__ == '__main__':
    main()
