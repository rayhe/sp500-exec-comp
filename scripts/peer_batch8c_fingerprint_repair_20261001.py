#!/usr/bin/env python3
"""Peer-network batch-8c fingerprint-queue repair (2026-10-01 run).

Follow-up to the 2026-10-01 batch-8a/8b runs. After 8b, the Section-19
fingerprint queue holds 355 cross-sector fingerprint-target edges across
222 sources; the heaviest remaining tier is 21 sources with exactly 3
queued edges each. Batch-8c takes the next 6 heaviest by total outbound
edge count (BG/CSX/TXN/NTRS/GLW/WAB) and re-extracts each source's
comp-decisions peer group VERBATIM from its latest DEF 14A, keeping only
edges that match the verbatim group. TSR/PSU comparator groups and
explicitly-excluded reference groups are unstored per the batches 3-8b
convention.

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession, filing HTML fetched
with User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential,
2s pacing; parallel fetch got SEC rate-limited), peer sections
transcribed verbatim. Evidence in /tmp/peersweep/batch8c/<TICKER>_peer.txt
(copied to goal hidden_files/peer-batch8c-20261001/).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  BG   23 -> 18 (DEF 14A 2026-04-10; 2025 Peer Group, 18 cos; post-Viterra
        merger value-chain methodology, Mosaic/Ingredion removals already
        reflected; queued CHTR/IP/PFG all dropped; added CNH/NTR)
  CSX  21 -> 20 (DEF 14A 2026-03-30; 2025 Comparator Group, 20 cos;
        FDX/FTV/UPS removed and DOV/JBHT added per the filing; 2026
        group unchanged per filing; queued CHTR/GIS/TGT all dropped;
        added CNI/CP/JBHT/SLB/WAB)
  TXN  20 -> 18 (DEF 14A 2026-03-03; 2025 Comparator Group, 18 cos, set
        July 2024; July 2025 review made no changes (same group for the
        Jan 2026 bonus decisions); queued COF/GIS/IP all dropped;
        added MMM)
  NTRS 20 -> 12 (DEF 14A 2026-03-11; 2025 Compensation Peer Group, 12
        cos, same as 2024; separate ROE performance peer group (PSU
        comparator) unstored per convention; queued GIS/PSA/TGT all
        dropped; added BK/FITB/TROW/USB)
  GLW  19 -> 26 (DEF 14A 2026-03-20; 2025 Compensation Peer Group, 26
        cos; JNPR replaced by HPE after the mid-2025 acquisition per the
        filing; queued GIS/IP/TGT all dropped; added
        MMM/HON/PPG/IQV/DD/LHX/TEL/TXN/BWA/BSX/NTAP)
  WAB  19 -> 19 (DEF 14A 2026-03-30; 2025 Peer Group = 2024 group, 19
        cos incl. AGCO; the July 2025 AGCO removal applied to 2026
        target-TDC decisions only - documented but NOT stored (V
        precedent: 2026 variant queued for the FY2026 cycle); queued
        CHTR/COF/GIS all dropped; added AGCO/OSK/PH/TKR)

TICKER-SLOT NOTE (corrected during this run): the batch-8b-style
adjudication was first drafted as BNY -> BK, but a live-source check
killed it: BNY Mellon changed its NYSE ticker from BK to BNY effective
2026-05-21 (announced 2026-05-11; trading under BNY since). The node
ticker BNY is therefore CORRECT and is kept as-is; NTRS's filing-verbatim
"The Bank of New York Mellon Corporation" maps to BNY. Rule reaffirmed:
on ticker-slot questions the LIVE holder wins - which here means no
rename at all.

No new edges in this batch match the Section-19 cross-sector
fingerprint pattern, so no verified_cross_sector marks are needed.
"""
import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'CNH': ('CNH Industrial N.V.', 'Industrials'),
    'NTR': ('Nutrien Ltd.', 'Materials'),
    'CNI': ('Canadian National Railway Company', 'Industrials'),
    'TKR': ('Timken Company', 'Industrials'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'BG': ('DEF 14A 2026-04-10',
           ['ADM', 'CAT', 'CNH', 'CTVA', 'DE', 'DOW', 'FDX', 'KHC',
            'LYB', 'MPC', 'MDLZ', 'NUE', 'NTR', 'PSX', 'SYY', 'TSN',
            'UPS', 'VLO']),
    'CSX': ('DEF 14A 2026-03-30',
            ['APD', 'CNI', 'CP', 'DOV', 'ETN', 'ECL', 'EMR', 'ITW',
             'JBHT', 'NSC', 'OTIS', 'PH', 'PPG', 'RSG', 'SLB', 'WMB',
             'TT', 'UNP', 'WAB', 'WM']),
    'TXN': ('DEF 14A 2026-03-03',
            ['MMM', 'INTC', 'AMD', 'LRCX', 'ADI', 'MDT', 'AMAT', 'MU',
             'AVGO', 'MSI', 'CSCO', 'NXPI', 'GLW', 'QCOM', 'EMR', 'TEL',
             'HON', 'TMO']),
    'NTRS': ('DEF 14A 2026-03-11',
             ['BLK', 'FITB', 'BEN', 'KEY', 'MTB', 'STT', 'TFC', 'TROW',
              'BNY', 'SCHW', 'PNC', 'USB']),
    'GLW': ('DEF 14A 2026-03-20',
            ['MMM', 'CMI', 'HON', 'PPG', 'AMD', 'DHR', 'ITW', 'QCOM',
             'A', 'DOV', 'IQV', 'ROK', 'APH', 'DD', 'LHX', 'TEL',
             'AMAT', 'ETN', 'MDT', 'TXN', 'BWA', 'EMR', 'MSI', 'BSX',
             'HPE', 'NTAP']),
    'WAB': ('DEF 14A 2026-03-30',
            ['AGCO', 'AME', 'CSX', 'DOV', 'ETN', 'EMR', 'ITW', 'IR',
             'J', 'NSC', 'OSK', 'PH', 'ROK', 'SNA', 'SWK', 'TXT',
             'TKR', 'TDG', 'XYL']),
}

EXPECTED_OLD = {
    'BG': ['ADM', 'CAG', 'CAT', 'CHTR', 'CTVA', 'DE', 'DOW', 'FDX',
           'GIS', 'IP', 'K', 'KHC', 'LYB', 'MDLZ', 'MOS', 'MPC',
           'NUE', 'PFG', 'PPG', 'SYY', 'TSN', 'UPS', 'VLO'],
    'CSX': ['APD', 'CHTR', 'DOV', 'ECL', 'EMR', 'ETN', 'FDX', 'FTV',
            'GIS', 'ITW', 'NSC', 'OTIS', 'PH', 'PPG', 'RSG', 'TGT',
            'TT', 'UNP', 'UPS', 'WM', 'WMB'],
    'TXN': ['ADI', 'AMAT', 'AMD', 'AVGO', 'COF', 'CSCO', 'EMR', 'GIS',
            'GLW', 'HON', 'INTC', 'IP', 'LRCX', 'MDT', 'MSI', 'MU',
            'NXPI', 'QCOM', 'TEL', 'TMO'],
    'NTRS': ['BAC', 'BEN', 'BLK', 'BNY', 'C', 'COF', 'GIS', 'GS',
             'JPM', 'KEY', 'MS', 'MTB', 'PNC', 'PRU', 'PSA', 'SCHW',
             'STT', 'TFC', 'TGT', 'WFC'],
    'GLW': ['A', 'AMAT', 'AMD', 'APH', 'CMI', 'DHR', 'DOV', 'EMR',
            'ETN', 'GIS', 'HPE', 'IP', 'ITW', 'JNPR', 'MDT', 'MSI',
            'QCOM', 'ROK', 'TGT'],
    'WAB': ['AME', 'CHTR', 'COF', 'CSX', 'DOV', 'EMR', 'ETN', 'GIS',
            'IR', 'ITW', 'J', 'NSC', 'ROK', 'SNA', 'SO', 'SWK',
            'TDG', 'TXT', 'XYL'],
}

# (BNY/BK ticker-slot note: BNY is the live ticker since 2026-05-21;
# no rename performed. The BNY_EXPECTED_* blocks below are retained only
# as documentation of the abandoned adjudication.)


def main():
    bak = SRC.replace('.json', '_backup_20261001_1700_pre_batch8c.json')
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

    # 2. ticker-slot note: BNY is the live ticker (BK -> BNY effective
    #    2026-05-21, verified via company press release this run); the
    #    node is kept as BNY. No rename performed.

    # 3. assert + replace edges for the repaired sources
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

    # 4. recompute degrees exactly
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

    # 5. metadata from actuals
    net['edges'] = edges
    nsrc = sum(1 for x in nodes if x.get('isSource') is True)
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-10-01'
    net['metadata']['last_dq_repair'] = '2026-10-01'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'
    print('sources:', nsrc)

    with open(SRC, 'w') as f:
        json.dump(net, f, indent=1)
    print('wrote', SRC, '| nodes:', len(nodes), '| edges:', len(edges))


if __name__ == '__main__':
    main()
