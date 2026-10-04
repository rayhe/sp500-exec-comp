#!/usr/bin/env python3
"""Peer-network batch-8z fingerprint-queue repair (2026-10-04 02:00 PDT run).

Second batch of the one-edge tier drain under the tier rule decided in
batch-8y: sources with total_out >= 20 get the full verbatim DEF 14A re-read
+ wholesale edge-set replace (assert-then-replace convention from batches
8a-8y). The 7 richest remaining one-edge sources (AME/ES/NUE/SMCI/AIG/LYB/
RSG, total_out 20-22) re-extracted verbatim from latest DEF 14A via EDGAR
submissions (primaryDocument from submissions; Kit/1.0 UA; CIKs verified
against the submissions name field, never from memory; sequential ~3s
pacing; no subagents per the task execution rule). SEC Archives curl was
UNBLOCKED this run - all 7 peer sections extracted directly from downloaded
HTMLs; filing HTMLs persisted to the goal dir at download time (the
batch-8h /tmp-peersweep-wipe lesson). Evidence in goal
hidden_files/peer-batch8z-20261004/ (<TICKER>_peer.txt verbatim
transcriptions + batch8z_submissions.json accession/URL map +
company_tickers_exchange.json; RSG_comparator_group.jpg for the
image-rendered comparator table).

New peer-only nodes (3): CLF (SEC CIK 0000764065), SANM (SEC CIK 0000897723),
X (United States Steel Corporation - delisted after the Nippon Steel
acquisition, retained under last ticker per the PNR/SMAR/SAVE precedent).

Adjudications:
- AME (22->19): the 2025 pay-actions peer group (19). Dropped GIS/WTW
  fabrications. MSI was a pre-emptive FY2026-leak (eighth catch of the
  class; added Aug 2025 for the FY2026 group per filing) - ALB/ADBE/AME
  convention. S&P 500 Industrials TSR table UNSTORED (performance measure).
- ES (21->20): "the 20 peer group companies listed in the table below".
  Dropped AWK/IP fabrications.
- NUE (21->21): the 21 Compensation Peer Companies. Dropped GIS/CARR/LYB
  fabrications; restored MMM/PCAR/NOC (real peers). Steel Comparator Group
  and General Industry Comparator Group are AIP/LTIP performance measure -
  UNSTORED per the HAL/KHC/ACGL dual-role convention. X (U.S. Steel,
  acquired by Nippon Steel) retained under last ticker.
- SMCI (21->22): the FY2025 Peer Group (22 companies). Dropped AON/NDAQ/
  ZBRA fabrications. FY2024 group (18) prior-year - UNSTORED. Nasdaq
  Computer Index (PvP table) - UNSTORED.
- AIG (20->17): the 2025 compensation benchmarking group (17). Dropped
  GIS/DLR fabrications. The old set's AMP/AON/PYPL/V edges were pre-emptive
  2026-leaks (ninth catch of the class) - stored the year in use. MFC
  (Manulife, NYSE-listed Canadian) is filing-genuine cross-border.
  Relative-TSR "Business Competitors" (LTI plan) - UNSTORED.
- LYB (20->18): "Our 2025 Peer Group" (18). Dropped EMN/GIS/KEY/WMB/WTW
  fabrications.
- RSG (20->17): COMPARATOR GROUP 2025 (17; image-transcribed). Dropped
  APD/ETR/FAST (removed in 2025) and GIS/HRL/KO/MCK/SO fabrications.
  Restored CNI/CP/JBHT/WCN (continuing peers). CNI/CP are filing-genuine
  cross-border (Canadian rails).

Tier rule (batch-8y, for future runs): total_out >= 20 -> full verbatim
re-read + wholesale replace (this batch); 10 <= total_out <= 19 ->
single-edge adjudication against the DEF 14A; total_out < 10 -> single-edge
adjudication, lowest priority.
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

NEW_NODES = {
    'CLF': ("Cleveland-Cliffs Inc.", 'Materials'),
    'SANM': ("Sanmina Corporation", 'Information Technology'),
    'X': ("United States Steel Corporation", 'Materials'),
}

NEW = {
    'AME': ('DEF 14A 2026-03-11',
            ['A', 'HUBB', 'MTD', 'TEL', 'DOV', 'IEX', 'OTIS', 'TDY', 'EMR',
             'ITW', 'PH', 'TDG', 'FTV', 'IR', 'ROK', 'XYL', 'HWM', 'KEYS',
             'SNA']),
    'ES': ('DEF 14A 2026-03-27',
           ['LNT', 'DTE', 'PCG', 'AEE', 'EIX', 'PPL', 'AEP', 'ETR', 'PEG',
            'CNP', 'EVRG', 'SRE', 'CMS', 'EXC', 'WEC', 'ED', 'FE', 'XEL',
            'D', 'NI']),
    'NUE': ('DEF 14A 2026-03-27',
            ['MMM', 'EMR', 'PCAR', 'CAT', 'FCX', 'PH', 'CLF', 'GD', 'PPG',
             'CMI', 'HON', 'STLD', 'DHR', 'ITW', 'TXT', 'DE', 'IP', 'TT',
             'ETN', 'NOC', 'X']),
    'SMCI': ('DEF 14A 2026-03-03',
             ['CDW', 'MCHP', 'GLW', 'MU', 'EA', 'NTAP', 'HPE', 'ON', 'HPQ',
              'SANM', 'JBL', 'STX', 'JNPR', 'TEL', 'KEYS', 'TDY', 'KLAC',
              'TOST', 'LRCX', 'WDC', 'MRVL', 'WDAY']),
    'AIG': ('DEF 14A 2026-03-31',
            ['ALL', 'AXP', 'BAC', 'BLK', 'COF', 'CB', 'CI', 'C', 'JPM',
             'MFC', 'MRSH', 'MET', 'PGR', 'PRU', 'TRV', 'USB', 'WFC']),
    'LYB': ('DEF 14A 2026-04-10',
            ['MMM', 'ADM', 'CAT', 'CMI', 'DE', 'DOW', 'DD', 'GD', 'DINO',
             'HON', 'IP', 'JCI', 'LIN', 'MPC', 'PSX', 'PPG', 'SHW', 'VLO']),
    'RSG': ('DEF 14A 2026-03-24',
            ['AEP', 'CNI', 'CP', 'CTAS', 'CSX', 'ECL', 'FDX', 'JBHT', 'NSC',
             'SYY', 'GWW', 'WCN', 'WM', 'DOW', 'LYB', 'NEE', 'UNP']),
}

# expected old edge sets (assertion guard) -- captured at 2026-10-04 02:00
# PDT from peer-network.json (1003 nodes / 7,458 edges).
EXPECTED_OLD = {
    'AME': ['A', 'DOV', 'EMR', 'FTV', 'GIS', 'HUBB', 'HWM', 'IEX', 'IR',
            'ITW', 'KEYS', 'MSI', 'MTD', 'OTIS', 'PH', 'ROK', 'SNA', 'TDG',
            'TDY', 'TEL', 'WTW', 'XYL'],
    'ES': ['AEE', 'AEP', 'AWK', 'CMS', 'CNP', 'D', 'DTE', 'ED', 'EIX',
           'ETR', 'EVRG', 'EXC', 'FE', 'IP', 'LNT', 'NI', 'PCG', 'PEG',
           'PPL', 'WEC', 'XEL'],
    'NUE': ['CARR', 'CAT', 'CMI', 'DE', 'DHR', 'EMR', 'ETN', 'FCX', 'GD',
            'GIS', 'HON', 'IP', 'ITW', 'LYB', 'NOC', 'PCAR', 'PH', 'PPG',
            'STLD', 'TT', 'TXT'],
    'SMCI': ['AON', 'CDW', 'EA', 'GLW', 'HPE', 'HPQ', 'JBL', 'JNPR', 'KLAC',
             'LRCX', 'MCHP', 'MRVL', 'MU', 'NDAQ', 'NTAP', 'ON', 'STX',
             'TDY', 'WDAY', 'WDC', 'ZBRA'],
    'AIG': ['ALL', 'AMP', 'AON', 'AXP', 'BAC', 'BLK', 'C', 'CI', 'COF',
            'DLR', 'GIS', 'JPM', 'MET', 'MRSH', 'PGR', 'PRU', 'PYPL', 'TRV',
            'V', 'WFC'],
    'LYB': ['ADM', 'CAT', 'CMI', 'DD', 'DE', 'DOW', 'EMN', 'GD', 'GIS',
            'HON', 'IP', 'JCI', 'KEY', 'LIN', 'MPC', 'PPG', 'SHW', 'VLO',
            'WMB', 'WTW'],
    'RSG': ['AEP', 'APD', 'CSX', 'CTAS', 'DOW', 'ECL', 'ETR', 'FAST', 'FDX',
            'GIS', 'HRL', 'KO', 'LYB', 'MCK', 'NEE', 'NSC', 'SO', 'SYY',
            'UNP', 'WM'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261004_0200_pre_batch8z.json')
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
    net['metadata']['last_updated'] = '2026-10-04'
    net['metadata']['last_dq_repair'] = '2026-10-04'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
