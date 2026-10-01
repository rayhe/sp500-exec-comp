#!/usr/bin/env python3
"""Peer-network bank garbage-parse repair batch 2026-09-30 19:30 PT run.

Replaces the last three garbage automated-extractor parses in the peer
network with real CD&A peer groups transcribed verbatim from each company's
latest DEF 14A. The 14:16 PT thin-edge run (2026-09-30) repaired the 8 worst
n=1 stubs and documented JPM/BAC/WFC as the remaining bank garbage parses
("Banks were the worst offenders"), but they were never repaired: they carry
3-4 edges (not n=1), and their edge 'filing' strings already match the latest
DEF 14As, so the EDGAR staleness sweep (18:30 PT: 0 stale sources) cannot see
them. They are wrong regardless of filing vintage:
  JPM -> HSY/PFG/CVX/MSFT   (a bank peer group containing Hershey and Chevron)
  BAC -> CVX/MSFT/GIS/COF   (Chevron/Microsoft in a bank peer group)
  WFC -> GIS/BNY/C          (3-edge stub; filing discloses a 10-company group)

Filing evidence (all downloaded to /tmp/peerfix-20260930-1930/ this run,
copied to goal hidden_files/thinedge-repair-20260930/):
- JPM  DEF 14A 2026-04-06 (jpm-20260402.htm): "Evaluating market practices" -
       "the CMDC benchmarks against our primary financial services peer
       group... The following companies comprise our primary financial
       services peer group, which remains unchanged from last year:
       American Express, Bank of America, Citigroup, Goldman Sachs,
       Morgan Stanley, Wells Fargo." The 13-company Allianz..UBS list
       elsewhere in the filing is the Asset & Wealth Management ranking
       group, NOT the NEO comp group (same comp-decisions-group rule as the
       14:00 PT MS "Comparison Group" repair).
- BAC  DEF 14A 2026-03-23 (d43888ddef14a.htm): "2025 Competitor Group" -
       Primary competitors: Citigroup, Goldman Sachs, JPMorgan Chase,
       Morgan Stanley, Wells Fargo. Leading financial institutions:
       Barclays, Deutsche Bank, HSBC, Truist, UBS, U.S. Bancorp, PNC,
       BlackRock, Blackstone, American Express, Capital One.
       Foreign ADRs (Barclays/BCS, Deutsche Bank/DB, HSBC, UBS) skipped per
       the 14:00 PT MS ticker-node precedent (no ticker nodes exist for
       them; cf. batch-2 UL exclusion note).
- WFC  DEF 14A 2026-03-18 (wfc-20260318.htm): two peer groups; the Labor
       Market Peer Group is the comp-decisions group ("an input for setting
       quantum of pay and pay mix... in connection with its annual review
       of NEO compensation") - the Financial Performance Peer Group is the
       separate relative-performance standard (all G-SIBs). Labor Market
       members (table 148, checkmark-parsed): American Express,
       Bank of America, BNY, Citigroup, Goldman Sachs, JPMorgan Chase,
       Morgan Stanley, PNC, State Street, U.S. Bancorp.

Old edges replaced: JPM->HSY/PFG/CVX/MSFT, BAC->CVX/MSFT/GIS/COF,
WFC->GIS/BNY/C (11 garbage edges -> 28 real edges).
"""
import json, shutil

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, filing year, [peer tickers in filing order])
NEW = {
    'JPM': ('DEF 14A 2026-04-06', 2026,
            ['AXP', 'BAC', 'C', 'GS', 'MS', 'WFC']),
    'BAC': ('DEF 14A 2026-03-23', 2026,
            ['C', 'GS', 'JPM', 'MS', 'WFC',
             'PNC', 'TFC', 'USB', 'BLK', 'BX', 'AXP', 'COF']),
    'WFC': ('DEF 14A 2026-03-18', 2026,
            ['AXP', 'BAC', 'BNY', 'C', 'GS', 'JPM', 'MS', 'PNC', 'STT',
             'USB']),
}

# expected garbage edge sets (asserted before replacement)
EXPECTED_OLD = {
    'JPM': ['HSY', 'PFG', 'CVX', 'MSFT'],
    'BAC': ['CVX', 'MSFT', 'GIS', 'COF'],
    'WFC': ['GIS', 'BNY', 'C'],
}

def main():
    bak = SRC.replace('.json', '_backup_20260930_1930_pre_bankgarbage.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}

    for src, (filing, year, peers) in NEW.items():
        assert src in by_ticker, f'{src}: not a node'
        for t in peers:
            assert t in by_ticker, f'{src}: unknown target {t}'

    for src, (filing, year, peers) in NEW.items():
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        assert old_targets == sorted(EXPECTED_OLD[src]), \
            f'{src}: old edge set changed: {old_targets}'
        print(f'{src}: old {len(old)} garbage edges {old_targets}')
        edges = [e for e in edges if e['source'] != src]
        for t in peers:
            edges.append({'source': src, 'target': t, 'year': year,
                          'group_type': 'primary', 'filing': filing})
        new_check = sorted(e['target'] for e in edges if e['source'] == src)
        assert new_check == sorted(peers), f'{src}: new edge set mismatch'
        assert len(set(new_check)) == len(new_check), f'{src}: duplicates'
        assert by_ticker[src].get('isSource') is True, f'{src}: not isSource'
        print(f'{src}: new {len(peers)} edges filing={filing}')

    from collections import Counter
    indeg = Counter(e['target'] for e in edges)
    outdeg = Counter(e['source'] for e in edges)
    mism = 0
    for x in nodes:
        ni, no = indeg.get(x['ticker'], 0), outdeg.get(x['ticker'], 0)
        if x.get('in_degree') != ni or x.get('out_degree') != no:
            mism += 1
        x['in_degree'], x['out_degree'] = ni, no
    print('nodes with changed degrees:', mism)

    net['edges'] = edges
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-09-30'
    # sources string unchanged: JPM/BAC/WFC were already counted sources;
    # no sources added or removed.

    with open(SRC, 'w') as f:
        json.dump(net, f, indent=1)
    print('wrote', SRC, '| nodes:', len(nodes), '| edges:', len(edges))

if __name__ == '__main__':
    main()
