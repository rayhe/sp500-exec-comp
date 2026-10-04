#!/usr/bin/env python3
"""Peer-network batch-8y fingerprint-queue repair (2026-10-03 23:30 PDT run).

First batch of the one-edge tier drain under the new tier rule decided this
run: sources with total_out >= 20 get the full verbatim DEF 14A re-read +
wholesale edge-set replace (same assert-then-replace convention as batches
8a-8x), because a single fabrication in the richest remaining unreviewed
edge sets has the largest centrality distortion, and a flagged edge can also
signal the thin-extraction issue (wholesale re-read fixes both). The 6
richest pending sources (VICI 29, FCX 26, TMO 26, ADBE 25, HCA 24, WMT 23)
re-extracted verbatim from latest DEF 14A via EDGAR submissions
(primaryDocument from submissions; Kit/1.0 UA; CIKs verified against the
submissions name field, never from memory). SEC Archives curl 403-blocked
this run (transient; was open at 22:05 for batch-8x) - all 6 peer sections
transcribed verbatim via the live-browser path (the batch-8w precedent); no
filing HTMLs persisted locally. Evidence in goal
hidden_files/peer-batch8y-20261003/ (batch8y_submissions.json +
batch8y_ciks.json + company_tickers_exchange.json). 1 new peer-only node
(GLPI, SEC-verified CIK 1575965).

Adjudications:
- VICI (29->18): 2025 Peer Group (18, all REITs/experiential operators).
  IP fabrication dropped. LVS dropped: the filing documents its Q3-2024
  removal for the 2025 group - a 2024-leak (sixth pre-emptive-leakage catch
  after TMUS/NKE, CDW/BBY, DPZ/NCLH, REG/AVB, ADBE/FY2026). Q3-2025 review
  kept the 2025 group for 2026 unchanged. Dropped AMT/BXP/CCI/FRT/HST/
  INVH/IRM/KIM/MAA/PLD/REG/VTR (old-set padding). TSR benchmarking tables
  (Peer Group / Triple Net REITs / S&P 500 REITs / S&P 500) are performance
  measurement, UNSTORED per convention.
- FCX (26->25): "Compensation Reference Groups" = Industrial Reference
  Group (25, STORED) + S&P 250 broad survey (constituents not enumerated,
  UNSTORED). WM ("Waste Management, Inc.") is filing-genuine cross-sector
  (FCX Materials; WM home sector Industrials) - marked verified via
  mark_verified. The PSU Performance Peer Group (8 mining cos, TSR
  modifier) is performance-assessment -> UNSTORED per HAL/KHC/ACGL dual-role
  convention. "SLB N.V." printed (alternate legal name for Schlumberger)
  stored as SLB; "PACCAR Inc" stored as PCAR. PNR (Pioneer Natural
  Resources, acquired by ExxonMobil 2024, delisted) retained under last
  ticker per the PARA/QRVO/COMM/SMAR/SAVE delisted-peer precedent. Dropped
  AWK/IP/SO fabrications.
- TMO (26->19): dual-group pattern (HAL/KHC/ACGL precedents). The
  Compensation Peer Group (19, STORED) is the compensation-decisions group;
  the 2025 TSR Peer Group (the 19 + 10 supplemental: 3M, AstraZeneca, ADP,
  Boston Scientific, CSX, IQVIA, Merck KGaA, Stryker, Boeing, PNC) is
  relative-TSR performance -> UNSTORED. The old set's ADP/BA/BSX/CSX/IQV/
  PNC/SYK were TSR-supplement leaks - a NEW leak class (leakage from a
  second disclosed group, not a year-over-year leak). 3M removed from the
  comp group in July 2024 per filing (divestiture). AstraZeneca + Merck
  KGaA are non-US -> UNSTORED per convention. PG ("The Procter & Gamble
  Co.") is filing-genuine cross-sector (TMO Health Care; PG home sector
  Consumer Staples) - marked verified. Printed variants stored under live
  tickers (Danaher Corp->DHR, Merck & Co, Inc.->MRK, Medtronic, plc->MDT,
  NIKE, Inc.->NKE, Bristol-Myers Squibb->BMY).
- ADBE (25->20): FY2025 Peer Group (20). BLK fabrication dropped. EXPE/
  SNOW/UBER dropped: the filing says they were added August 2025 for the
  FY2026 group - pre-emptive FY2026-leaks (seventh catch of the class;
  sixth was VICI/LVS this same batch). AWK/PEP fabrications dropped. SAP
  SE is a new peer-only node (NYSE-listed ADR; meets the filing's
  U.S.-listed criterion; SEC CIK 0000796343-family verified via
  company_tickers_exchange.json). PSP Relative TSR = Nasdaq 100 Index;
  PvP = S&P 500 Software & Services Index - both UNSTORED.
- HCA (24->24): peer group (24). CHTR fabrication dropped. WTW dropped
  (fabrication/old). MOH (Molina Healthcare) + THC (Tenet Healthcare)
  added - both S&P 500 company nodes. Printed variants ("Centene Corp.",
  "Medtronic Inc.", "UnitedHealth Group Incorporated") stored under live
  tickers. Willis Towers Watson / Radford McLagan survey databases are
  broad-survey -> UNSTORED. PvP = S&P Health Care Index UNSTORED.
- WMT (23->24): Walmart Proxy Peer Group (24). MSFT ("Microsoft
  Corporation") is filing-genuine cross-sector (WMT Consumer Staples; MSFT
  home sector IT) - marked verified. ACI (Albertsons) added - a dropped
  real peer restored (was missing from the old set). Screening
  methodology (>$100B revenue/mkt-cap, US-headquartered, excludes
  founder-CEO and private companies) documented, UNSTORED. Survey data
  UNSTORED per convention.

Tier rule (for future runs): total_out >= 20 -> full verbatim re-read +
wholesale replace (batch series, this run's tier); 10 <= total_out <= 19 ->
single-edge adjudication against the DEF 14A (drop or mark verified, group
otherwise untouched); total_out < 10 -> single-edge adjudication, lowest
priority. Remaining after this run: 104 one-edge sources (7 at total_out
20+ form batch-8z: AME, ES, NUE, SMCI, AIG, LYB, RSG).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
# (all SEC company_tickers_exchange.json verified)
NEW_NODES = {
    'GLPI': ("Gaming & Leisure Properties, Inc.", 'Real Estate'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'VICI': ('DEF 14A 2026-03-16',
             ['ARE', 'EXR', 'O', 'AVB', 'GLPI', 'SBAC', 'CZR', 'DOC',
              'SPG', 'DLR', 'HLT', 'WELL', 'EQIX', 'MGM', 'WPC', 'EQR',
              'PSA', 'WY']),
    'FCX': ('DEF 14A 2026-04-23',
            ['APD', 'BKR', 'CAT', 'CTVA', 'CMI', 'DOW', 'DD', 'ETN',
             'ECL', 'EMR', 'EOG', 'HAL', 'HON', 'ITW', 'JCI', 'NEM',
             'NUE', 'OXY', 'PCAR', 'PH', 'PNR', 'PPG', 'SLB', 'SHW',
             'WM']),
    'TMO': ('DEF 14A 2026-04-07',
            ['ABBV', 'ABT', 'AMGN', 'BDX', 'BMY', 'AVGO', 'CSCO',
             'DHR', 'LLY', 'GILD', 'HON', 'JNJ', 'MDT', 'MRK', 'NKE',
             'PEP', 'PFE', 'TXN', 'PG']),
    'ADBE': ('DEF 14A 2026-02-27',
             ['GOOGL', 'AMZN', 'AMD', 'ABNB', 'AAPL', 'ADSK', 'AVGO',
              'CSCO', 'INTU', 'META', 'MSFT', 'NFLX', 'NVDA', 'ORCL',
              'PANW', 'PYPL', 'CRM', 'SAP', 'NOW', 'WDAY']),
    'HCA': ('DEF 14A 2026-03-13',
            ['ABT', 'ABBV', 'AMGN', 'BMY', 'CAH', 'COR', 'CNC', 'CVS',
             'DHR', 'ELV', 'LLY', 'GILD', 'HUM', 'JNJ', 'MCK', 'MDT',
             'MRK', 'MOH', 'PFE', 'SYK', 'THC', 'CI', 'TMO', 'UNH']),
    'WMT': ('DEF 14A 2026-04-23',
            ['ACI', 'GOOGL', 'AMZN', 'AXP', 'AAPL', 'CMCSA', 'COST',
             'CVS', 'HD', 'JPM', 'KR', 'MCD', 'MCK', 'META', 'MSFT',
             'NKE', 'PEP', 'PG', 'TGT', 'TMUS', 'UPS', 'VZ', 'WBA',
             'DIS']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-03 23:30 PT from peer-network.json (1002 nodes / 7,481 edges).
EXPECTED_OLD = {
    'VICI': ['AMT', 'ARE', 'AVB', 'BXP', 'CCI', 'CZR', 'DLR', 'DOC',
             'EQIX', 'EQR', 'EXR', 'FRT', 'HLT', 'HST', 'INVH', 'IP',
             'IRM', 'KIM', 'LVS', 'MAA', 'O', 'PLD', 'PSA', 'REG',
             'SBAC', 'SPG', 'VTR', 'WELL', 'WY'],
    'FCX': ['APD', 'AWK', 'BKR', 'CAT', 'CMI', 'CTVA', 'DD', 'DOW',
            'ECL', 'EMR', 'EOG', 'ETN', 'HAL', 'HON', 'IP', 'ITW',
            'JCI', 'NEM', 'NUE', 'OXY', 'PCAR', 'PH', 'PPG', 'SHW',
            'SO', 'WM'],
    'TMO': ['ABBV', 'ABT', 'ADP', 'AMGN', 'AVGO', 'BA', 'BDX', 'BMY',
            'BSX', 'CSCO', 'CSX', 'DHR', 'GILD', 'HON', 'IQV', 'JNJ',
            'LLY', 'MDT', 'MRK', 'NKE', 'PEP', 'PFE', 'PG', 'PNC',
            'SYK', 'TXN'],
    'ADBE': ['AAPL', 'ABNB', 'ADSK', 'AMD', 'AMZN', 'AVGO', 'AWK',
             'BLK', 'CRM', 'CSCO', 'EXPE', 'GOOGL', 'INTU', 'META',
             'MSFT', 'NFLX', 'NOW', 'NVDA', 'ORCL', 'PANW', 'PEP',
             'PYPL', 'SNOW', 'UBER', 'WDAY'],
    'HCA': ['ABBV', 'ABT', 'AMGN', 'BMY', 'CAH', 'CHTR', 'CI', 'CNC',
            'COR', 'CVS', 'DHR', 'ELV', 'GILD', 'HUM', 'JNJ', 'LLY',
            'MCK', 'MDT', 'MRK', 'PFE', 'SYK', 'TMO', 'UNH', 'WTW'],
    'WMT': ['AAPL', 'AMZN', 'AXP', 'CMCSA', 'COST', 'CVS', 'DIS',
            'GOOGL', 'HD', 'JPM', 'KR', 'MCD', 'MCK', 'META', 'MSFT',
            'NKE', 'PEP', 'PG', 'TGT', 'TMUS', 'UPS', 'VZ', 'WBA'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261003_2330_pre_batch8y.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}

    # 1. create new peer-only nodes (before edge validation)
    for t, (name, sector) in sorted(NEW_NODES.items()):
        assert t not in by_ticker, f'{t}: node already exists'
        n = {'ticker': t, 'name': name, 'sector': sector,
             'in_degree': 0, 'out_degree': 0, 'market_cap_tier': 'large'}
        nodes.append(n)
        by_ticker[t] = n
    print('new peer-only nodes:', len(NEW_NODES))

    # 2. assert + replace edges for the repaired sources
    for src, (filing, peers) in NEW.items():
        assert src in by_ticker, f'{src}: not a node'
        for t in peers:
            assert t in by_ticker, f'{src}: unknown target {t}'
        assert src not in peers, f'{src}: self-edge'
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        assert old_targets == sorted(EXPECTED_OLD[src]), \
            f'{src}: old edge set changed: {old_targets}'
        edges = [e for e in edges if e['source'] != src]
        year = int(filing.rsplit(' ', 1)[1].split('-')[0])
        for t in peers:
            edges.append({'source': src, 'target': t, 'year': year,
                          'group_type': 'primary', 'filing': filing})
        new_check = sorted(e['target'] for e in edges if e['source'] == src)
        assert new_check == sorted(peers), f'{src}: new edge set mismatch'
        assert len(set(new_check)) == len(new_check), f'{src}: duplicates'
        assert by_ticker[src].get('isSource') is True, f'{src}: not isSource'
        print(f'{src}: {len(old)} old -> {len(peers)} new ({filing})')

    # 3. recompute degrees exactly
    from collections import Counter
    indeg = Counter(e['target'] for e in edges)
    outdeg = Counter(e['source'] for e in edges)
    for e in edges:
        assert e['source'] in by_ticker and e['target'] in by_ticker, \
            f"dangling edge {e['source']}->{e['target']}"
    mism = 0
    for x in nodes:
        ni, no = indeg.get(x['ticker'], 0), outdeg.get(x['ticker'], 0)
        if x.get('in_degree') != ni or x.get('out_degree') != no:
            mism += 1
        x['in_degree'], x['out_degree'] = ni, no
    print('nodes with changed degrees:', mism)
    for x in nodes:
        od = outdeg.get(x['ticker'], 0)
        if od > 0:
            assert x.get('isSource') is True, \
                f"{x['ticker']}: edges but not isSource"
        if x.get('isSource') is False:
            assert od == 0, f"{x['ticker']}: isSource False but has edges"

    # 4. metadata from actuals
    net['nodes'] = nodes
    net['edges'] = edges
    nsrc = sum(1 for x in nodes if x.get('isSource') is True)
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-10-03'
    net['metadata']['last_dq_repair'] = '2026-10-03'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
