#!/usr/bin/env python3
"""Peer-network batch-8l fingerprint-queue repair (2026-10-02 14:00 PDT run).

Follow-up to the batch-8a/8b/8c/8d/8e/8f/8g/8h/8i/8j/8k runs (2026-10-01/02).
After 8k, the Section-19 fingerprint queue holds 226 cross-sector
fingerprint-target edges pending across 174 sources (54 verified marks).
Batch-8l takes the 6 heaviest remaining 2-queue sources by total outbound
edge count (HUM 18 / SBUX 18 / BLDR 17 / CB 17 / CCL 17 / FIS 17) and
re-extracts each source's comp-decisions peer group VERBATIM from its latest
DEF 14A, keeping only edges that match the verbatim group. TSR/performance
comparator groups, 2026-variant groups, index-only groups, and unnamed
survey databases are documented but unstored per the batches 3-8k convention
(FISV 2026 COF-for-DFS, SBUX 2026 group, CCL 2026 LUV-out precedents this
batch; PCG Entergy table-vs-prose, UNH two-column-chart, VTR MPW->MPT
ticker-slot discipline).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run; CIKs verified against
compensation.json - HUM 49071 / SBUX 829224 / BLDR 1316835 / CB 896159 /
CCL 815097 / FIS 1136893), filing HTML fetched with User-Agent
"Kit/1.0 (factoryfactorykit@gmail.com)" (sequential, ~2-3s pacing;
non-padded CIK in Archive URLs + curl -L per the batch-8d note; primary
document names from each filing's submissions primaryDocument field). Peer
sections transcribed verbatim. Evidence in goal
hidden_files/peer-batch8l-20261002/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8l_filings.json (accession/URL map); filing HTML
copied to the goal dir AT download time (the batch-8h /tmp-peersweep-wipe
lesson, re-hit this run - the first download set vanished from /tmp before
transcription, forcing a full re-fetch).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  HUM   18 -> 18 (DEF 14A 2026-03-06; 2025 Peer Group, verbatim, 3-column
        chart (Managed Care / Healthcare Services & Facilities /
        Financial & Insurance); queued CHTR/COF fabrications dropped;
        added LH (Labcorp) + MOH (Molina Healthcare); WBA stored verbatim
        (footnote says removal going forward after Aug-2025 go-private,
        the 2025 group still names it - table-operative convention,
        same class as batch-8k PCG/ETR); rTSR comparator is now the Dow
        Jones U.S. Select Health Care Provider Index - index-only,
        UNSTORED per the index-only precedent; no cross-sector marks)
  SBUX  18 -> 19 (DEF 14A 2026-01-26; FY2025 Executive Compensation Peer
        Group, verbatim (8 Consumer Staples / 6 Consumer Discretionary /
        1 IT-Software & Services / 4 Iconic Global Brand leaders);
        dropped ABNB/ED/JCI/UBER/V; added KO/CL/KMB/EL/TMUS/MCD;
        GIS + PG SURVIVE - genuine verbatim cross-sector edges
        (SBUX = Consumer Discretionary, both targets' home = Consumer
        Staples), marked verified per batch-8h precedent; FY2026 group
        removed GIS/KMB/KHC/EL (lower growth / manufacturing-focused) -
        documented but NOT stored per the 2026-variant precedent chain,
        queued for the FY2026 cycle)
  BLDR  17 -> 19 (DEF 14A 2026-04-02; 2025 primary Peer Group of 19,
        verbatim, no 2024->2025 changes (July-2024 Meridian review);
        queued GIS/IP fabrications dropped; old POOL/WMB edges dropped;
        added BECN/GWW/FBIN/OC/WCC/WHR; Fortune Brands Home & Security
        stored as FBIN (renamed live holder - ticker-slot discipline);
        BECN stored per the delisted-peer precedent (QXO acquisition
        2025, the 2025 group still names it); the same named group feeds
        the PSU TSR modifier - no separate TSR group disclosed;
        Pay-vs-Performance uses the S&P 600 Building Products Index -
        index-only, UNSTORED per the index-only precedent; no marks)
  CB    17 -> 15 (DEF 14A 2026-04-03; 2025 CEO Compensation Benchmarking
        Peer Group, verbatim (15 companies) - the comp-decisions group;
        queued GIS/IP fabrications dropped; old HIG/JPM edges dropped
        (those were Financial-Performance-group blends); added BNY/MS;
        BNY Mellon stored as BNY (BK->BNY 2026-05-21, node exists per
        batch-8c); BLK survives but is same-sector (CB = Financials), so
        NO verified mark; the Financial Performance Peer Group (P&C
        peers: Allstate/AIG/CNA/Hartford/Liberty Mutual/Travelers/Zurich)
        is performance-assessment only - UNSTORED per the TSR/
        performance-group precedent)
  CCL   17 -> 18 (DEF 14A 2026-02-27; FY2025 Peer Group of 18,
        verbatim (July-2024 FW Cook review, no 2025 changes); queued
        IP/WM fabrications dropped; old AWK edge dropped; added AAL/MGM/
        IAG/MCD; LUV stored verbatim (footnote removes it only for the
        2026 group - table-operative convention; 2026 removal documented,
        queued for the FY2026 cycle); new node IAG (International
        Consolidated Airlines Group, S.A., Industrials, LSE/Nasdaq);
        unnamed survey databases unstored per convention; no marks)
  FIS   17 -> 17 (DEF 14A 2026-04-28; peer group selected late-2024 for
        the 2025 program, verbatim (17 companies; table is as-of the
        selection date and "does not reflect any subsequent mergers,
        acquisitions or divestitures"); dropped AXP/ED/PFG/WDC; added
        DFS/FISV/SSNC/TW; DFS stored verbatim per the delisted-peer
        precedent (Capital One acquisition early 2025; the 2025 group
        still names it - table-operative convention, same class as
        PYPL batch-8k); NDAQ SURVIVES - genuine verbatim cross-sector
        edge (FIS = Information Technology, NDAQ home = Financials),
        marked verified per batch-8h precedent)

Three new verified_cross_sector marks this batch (filing-verbatim,
surviving the repair): SBUX->GIS, SBUX->PG, FIS->NDAQ. Queue 226->214
pending (12 queued edges resolved: HUM CHTR/COF, SBUX GIS/PG, BLDR
GIS/IP, CB GIS/IP, CCL IP/WM, FIS NDAQ/PFG); verified 54->57.

New nodes: 1 (IAG, International Consolidated Airlines Group, S.A.,
Industrials) - registered in PEER_ONLY_NODES and in
mark_verified_cross_sector REPAIR_SCRIPTS BEFORE the repair ran (the
batch-5 / batch-8h lessons held, consistency check green on first commit
attempt).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'IAG': ('International Consolidated Airlines Group, S.A.', 'Industrials'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'HUM': ('DEF 14A 2026-03-06',
            ['CNC', 'CVS', 'ELV', 'MOH', 'CI', 'UNH', 'COR', 'CAH',
             'DVA', 'HCA', 'LH', 'MCK', 'WBA', 'AFL', 'ALL', 'MET',
             'PGR', 'PRU']),
    'SBUX': ('DEF 14A 2026-01-26',
             ['KO', 'CL', 'GIS', 'KMB', 'MDLZ', 'PEP', 'KHC', 'PG',
              'CMG', 'KDP', 'MCD', 'NKE', 'TGT', 'EL', 'PYPL',
              'AXP', 'MA', 'TMUS', 'DIS']),
    'BLDR': ('DEF 14A 2026-04-02',
             ['BALL', 'LEN', 'SHW', 'BECN', 'MAS', 'TT', 'CARR',
              'MHK', 'GWW', 'FBIN', 'OC', 'WCC', 'GPC', 'PPG',
              'WHR', 'JCI', 'PHM', 'LKQ', 'SWK']),
    'CB': ('DEF 14A 2026-04-03',
           ['ALL', 'AXP', 'AIG', 'AON', 'BAC', 'BNY', 'BLK', 'CI',
            'C', 'GS', 'MRSH', 'MET', 'MS', 'PRU', 'TRV']),
    'CCL': ('DEF 14A 2026-02-27',
            ['AAL', 'HLT', 'MGM', 'BKNG', 'IAG', 'NCLH', 'CZR',
             'LVS', 'RCL', 'DRI', 'LYV', 'LUV', 'DAL', 'MAR',
             'SBUX', 'EXPE', 'MCD', 'UAL']),
    'FIS': ('DEF 14A 2026-04-28',
            ['ADP', 'XYZ', 'BR', 'DFS', 'FISV', 'GPN', 'ICE', 'MA',
             'MSCI', 'NDAQ', 'PYPL', 'SSNC', 'SPGI', 'SYF', 'BNY',
             'TW', 'V']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-02 14:05 PT from peer-network.json (915 nodes / 7,043 edges).
EXPECTED_OLD = {
    'HUM': ['AFL', 'ALL', 'CAH', 'CHTR', 'CI', 'CNC', 'COF', 'COR',
            'CVS', 'DVA', 'ELV', 'HCA', 'MCK', 'MET', 'PGR', 'PRU',
            'UNH', 'WBA'],
    'SBUX': ['ABNB', 'AXP', 'CMG', 'DIS', 'ED', 'GIS', 'JCI', 'KDP',
             'KHC', 'MA', 'MDLZ', 'NKE', 'PEP', 'PG', 'PYPL', 'TGT',
             'UBER', 'V'],
    'BLDR': ['BALL', 'CARR', 'GIS', 'GPC', 'IP', 'JCI', 'LEN', 'LKQ',
             'MAS', 'MHK', 'PHM', 'POOL', 'PPG', 'SHW', 'SWK', 'TT',
             'WMB'],
    'CB': ['AIG', 'ALL', 'AON', 'AXP', 'BAC', 'BLK', 'C', 'CI',
           'GIS', 'GS', 'HIG', 'IP', 'JPM', 'MET', 'MRSH', 'PRU',
           'TRV'],
    'CCL': ['AWK', 'BKNG', 'CZR', 'DAL', 'DRI', 'EXPE', 'HLT', 'IP',
            'LUV', 'LVS', 'LYV', 'MAR', 'NCLH', 'RCL', 'SBUX', 'UAL',
            'WM'],
    'FIS': ['ADP', 'AXP', 'BNY', 'BR', 'ED', 'GPN', 'ICE', 'MA',
            'MSCI', 'NDAQ', 'PFG', 'PYPL', 'SPGI', 'SYF', 'V',
            'WDC', 'XYZ'],
}

# new verified_cross_sector marks (filing-verbatim surviving edges only)
NEW_MARKS = [
    {'source': 'SBUX', 'target': 'GIS', 'filing': 'DEF 14A 2026-01-26',
     'batch': 'peer-batch8l-20261002'},
    {'source': 'SBUX', 'target': 'PG', 'filing': 'DEF 14A 2026-01-26',
     'batch': 'peer-batch8l-20261002'},
    {'source': 'FIS', 'target': 'NDAQ', 'filing': 'DEF 14A 2026-04-28',
     'batch': 'peer-batch8l-20261002'},
]


def main():
    bak = SRC.replace('.json', '_backup_20261002_1400_pre_batch8l.json')
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

    # 3. append verified_cross_sector marks (dedupe-guarded)
    marks = net['metadata'].setdefault('verified_cross_sector', [])
    seen = {(m['source'], m['target']) for m in marks}
    for m in NEW_MARKS:
        assert (m['source'], m['target']) not in seen, \
            f"duplicate mark {m['source']}->{m['target']}"
        marks.append(m)
        seen.add((m['source'], m['target']))
    print('verified_cross_sector marks:', len(marks))

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
    net['metadata']['last_updated'] = '2026-10-02'
    net['metadata']['last_dq_repair'] = '2026-10-02'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
