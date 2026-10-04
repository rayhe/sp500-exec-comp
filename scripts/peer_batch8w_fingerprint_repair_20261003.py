#!/usr/bin/env python3
"""Peer-network batch-8w fingerprint-queue repair (2026-10-03 19:30 PDT run).

Batch-8w of the fingerprint-queue drain. The 8 heaviest remaining 2-edge
sources by total outbound edge count (HLT/MAR/PNW/SJM at out=12;
CPAY/DPZ/JBHT/SYF at out=11) re-extracted verbatim from latest DEF 14A
via EDGAR (Kit/1.0 UA; primaryDocument from submissions; sequential
~2-3s pacing; no subagents per the task execution rule). Peer sections
transcribed verbatim. Evidence in goal
hidden_files/peer-batch8w-20261003/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8w_submissions.json (accession/URL map) +
batch8w_docs.json; filing HTMLs persisted to the goal dir AT download
time (the batch-8h /tmp-peersweep-wipe lesson).

NOTE on filing access: SEC Archives www.sec.gov gated curl with the
Undeclared Automated Tool 403 block this run (~19:30 PDT); the block
persisted through a 10-minute cooldown (probe still 403 at 19:43).
data.sec.gov submissions JSON was never blocked. All 8 peer sections
were transcribed verbatim via the live-browser path (the 2026-09-17
14:00 PT precedent); filing HTMLs could not be persisted locally this
run, so the <TICKER>_peer.txt transcriptions carry the section headings,
change notes, and second-group adjudications. PNW's "PNM Resources, Inc.
(PNM)" is stored as TXNM per the batch-8b live-holder / batch-4
"Fiserv is FISV" rule (PNM Resources renamed TXNM Energy Aug 2024;
TXNM already a node).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
# (all SEC company_tickers_exchange.json verified; names filing-verbatim
# where the filing printed them)
NEW_NODES = {
    'BFH': ("Bread Financial Holdings, Inc.", 'Financials'),
    'BLMN': ("Bloomin' Brands, Inc.", 'Consumer Discretionary'),
    'IHG': ("InterContinental Hotels Group PLC", 'Consumer Discretionary'),
    'PZZA': ("Papa John's International, Inc.", 'Consumer Discretionary'),
    'SPB': ("Spectrum Brands Holdings, Inc.", 'Consumer Discretionary'),
    'TXRH': ("Texas Roadhouse, Inc.", 'Consumer Discretionary'),
    'WEN': ("The Wendy's Company", 'Consumer Discretionary'),
    'WH': ("Wyndham Hotels & Resorts, Inc.", 'Consumer Discretionary'),
    'WING': ("Wingstop Inc.", 'Consumer Discretionary'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'HLT': ('DEF 14A 2026-04-02',
            ['H', 'MAR', 'WH', 'BKNG', 'CCL', 'EXPE', 'LVS', 'MGM',
             'RCL', 'UAL', 'WYNN', 'COF', 'MCD', 'NKE', 'SBUX', 'DIS',
             'YUM']),
    'MAR': ('DEF 14A 2026-03-27',
            ['BKNG', 'CCL', 'CZR', 'EXPE', 'HLT', 'H', 'LVS', 'MGM',
             'RCL', 'COF', 'MCD', 'NKE', 'SBUX', 'DIS', 'UBER']),
    'PNW': ('DEF 14A 2026-04-03',
            ['LNT', 'AEE', 'AGR', 'CMS', 'DTE', 'EIX', 'EVRG', 'ES',
             'HE', 'NI', 'OGE', 'TXNM', 'PPL', 'SO', 'WEC', 'XEL']),
    'SJM': ('DEF 14A 2026-06-26',
            ['CPB', 'HRL', 'CHD', 'INGR', 'CLX', 'KDP', 'CL', 'KHC',
             'CAG', 'MKC', 'FLO', 'POST', 'GIS', 'SPB', 'HSY', 'THS']),
    'CPAY': ('DEF 14A 2026-04-10',
             ['ADP', 'GPN', 'BR', 'INTU', 'DAY', 'JKHY', 'EFX', 'MA',
              'EEFT', 'PAYX', 'FICO', 'PAYC', 'FIS', 'SSNC', 'FISV',
              'WEX']),
    'DPZ': ('DEF 14A 2026-03-10',
            ['BBWI', 'PZZA', 'BLMN', 'QSR', 'CMG', 'TXRH', 'DRI', 'WEN',
             'HLT', 'ULTA', 'H', 'WING', 'IHG', 'WH', 'LULU', 'YUMC',
             'MAR', 'YUM']),
    'JBHT': ('DEF 14A 2026-03-11',
             ['CHRW', 'CSX', 'EXPD', 'HUBG', 'KNX', 'NSC', 'ODFL', 'RSG',
              'R', 'SNDR', 'UNP', 'URI', 'WM', 'XPO']),
    'SYF': ('DEF 14A 2026-04-29',
            ['ALLY', 'AXP', 'BFH', 'COF', 'VOYA', 'XYZ', 'FIS', 'FISV',
             'GPN', 'MA', 'PYPL', 'V']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-03 19:30 PT from peer-network.json (971 nodes / 7,395 edges).
EXPECTED_OLD = {
    'HLT': ['BKNG', 'CCL', 'COF', 'DIS', 'EXPE', 'IP', 'LVS', 'MAR',
            'NKE', 'RCL', 'SBUX', 'UAL'],
    'MAR': ['ABNB', 'BKNG', 'CCL', 'COF', 'CZR', 'EXPE', 'HLT', 'HST',
            'IP', 'NCLH', 'RCL', 'TGT'],
    'PNW': ['AEE', 'DTE', 'EVRG', 'GIS', 'LNT', 'NI', 'PPL', 'SO', 'WEC',
            'WM', 'WTW', 'XEL'],
    'SJM': ['BLK', 'CAG', 'CHD', 'CL', 'CLX', 'GIS', 'HRL', 'HSY', 'KDP',
            'KHC', 'MKC', 'STT'],
    'CPAY': ['ADP', 'BR', 'CHTR', 'EFX', 'FICO', 'FIS', 'FISV', 'GIS',
             'INTU', 'JKHY', 'MA'],
    'DPZ': ['CMG', 'COF', 'DRI', 'EXPE', 'HLT', 'ICE', 'IP', 'MAR',
            'NCLH', 'RCL', 'ULTA'],
    'JBHT': ['CHTR', 'CSX', 'EW', 'EXPD', 'GIS', 'NSC', 'ODFL', 'RSG',
             'UNP', 'URI', 'WM'],
    'SYF': ['AXP', 'COF', 'FIS', 'FISV', 'GIS', 'GPN', 'MA', 'PYPL',
            'TGT', 'V', 'XYZ'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261003_1930_pre_batch8w.json')
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
