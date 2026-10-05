#!/usr/bin/env python3
"""Peer-network batch-22 fragmentary-source sweep, tranche 4 (2026-10-05 06:00 PDT run).

Closes the batch-21 observation class "fragmentary stored groups invisible to
the fingerprint queue" for the 9 remaining deg-6 sources (ENPH/HBAN/JPM/KEY/
MTD/O/ROST/STLD/VST, all confirmed exactly out_degree 6). Triage first per the
batch-21 note: JPM looked plausibly complete (classic money-center group);
VST plausible. Triage verdict: JPM is genuinely complete (stored 6 == the
filing's primary financial services peer group verbatim) and VST is genuinely
complete (stored 6 == the filing's 2025 compensation peer group verbatim;
the 2026 NEE/Talen additions and UGI removal are forward-looking and
UNSTORED per the operative-group convention). Both are LEFT UNCHANGED.
The other 7 are repaired wholesale (assert-then-replace, EXPECTED_OLD captured
2026-10-05 06:00 PDT).

Adjudications (all against the stored edges' own DEF 14As; all also the
latest, pinned=False for all 9):

- ENPH 6->16 (DEF 14A 2026-04-01, acc. 0001463101-26-000026): operative
  group is the filing's 2025 peer group verbatim (Bloom Energy, Nextpower
  (fka Nextracker), SolarEdge, Entegris, Qorvo, Sunrun, Everpure (fka Pure
  Storage), Resideo, Teradyne, First Solar, Rivian, Wolfspeed, Generac,
  Skyworks, Zebra, Monolithic Power). Stored 6 genuine but fragmentary.
- HBAN 6->11 (DEF 14A 2026-03-12, acc. 0001193125-26-103196): operative
  group is the 2025 peer-bank list (CFG/CMA/FITB/FHN/KEY/MTB/PNC/RF/TFC/USB/
  ZION; First Horizon added for 2025, growing 10->11). Stored 6 genuine but
  fragmentary.
- KEY 6->10 (DEF 14A 2026-03-27, acc. 0001193125-26-127600): operative
  group is the 2025 Peer Group verbatim (CFG/CMA/FITB/HBAN/MTB/PNC/RF/TFC/
  USB/ZION); the First Citizens BancShares add for 2026 is forward-looking
  and UNSTORED. Stored 6 genuine but fragmentary.
- MTD 6->16 (DEF 14A 2026-03-18, acc. 0001174947-26-000389): operative
  group is the filing's 16-co "peer companies" list (PM&P survey group:
  A/AME/BIO/BRKR/FTV/HOLX/IEX/ISRG/NDSN/RVTY/RMD/ROK/TDY/TFX/WAT/XYL); the
  WTW Swiss/non-US survey data is NOT a company peer group (dual-role
  UNSTORED). Stored 6 genuine but fragmentary.
- O 6->18 (DEF 14A 2026-03-25, acc. 0000726728-26-000021): operative group
  is the 2025 Peer Group verbatim 18 (expanded beyond REITs: includes
  CBRE/JLL/KW/MET/NTRS/HIG financial-services peers; ESS/DOC/WPC removed).
  Stored MET is filing-verbatim genuine (cross-sector by design), not
  contamination. Stored 6 genuine but fragmentary.
- ROST 6->17 (DEF 14A 2026-04-07, acc. 0000745732-26-000013): FY2025 peer
  group verbatim 17 (BBWI/BBY/BURL/DKS/DG/DLTR/FL/GPS/KSS/M/M/JWN/PVH/TJX/
  TSCO/ULTA/VFC/WSM); PvP TSR peer is the Dow Jones Apparel Retailers index
  (dual-role UNSTORED). Stored 6 genuine but fragmentary.
- STLD 6->13 (DEF 14A 2026-03-27, acc. 0001104659-26-035826): 2025
  compensation peer group verbatim 13 (AGCO/NEM/AA/NUE/CLF/PCAR/CMC/PH/CMI/
  RS/FCX/X/ITW); no changes for 2025. Stored 6 genuine but fragmentary.
- JPM left unchanged (DEF 14A 2026-04-06, acc. 0000019617-26-000096):
  stored AXP/BAC/C/GS/MS/WFC == the filing's primary financial services
  peer group exactly ("remains unchanged from last year"); the
  "other financial services companies" reference is narrative-only,
  UNSTORED. Triage evidence recorded, no repair.
- VST left unchanged (DEF 14A 2026-03-18, acc. 0001628280-26-019029):
  stored AES/CEG/ETR/NRG/PEG/UGI == the filing's 2025 compensation peer
  group exactly ("Consistent with 2024"); 2026 changes (UGI removed; NEE
  and Talen Energy added) are forward-looking and UNSTORED. Triage evidence
  recorded, no repair.

New peer-only nodes (6), registered in guard PEER_ONLY_NODES + mark_verified
REPAIR_SCRIPTS BEFORE the repair (batch-5/8z/17/19/20/21 ordering held):
  SEDG (SolarEdge Technologies, Inc., Information Technology),
  KW (Kennedy-Wilson Holdings, Inc., Real Estate),
  CMC (Commercial Metals Company, Materials),
  RS (Reliance, Inc., Materials),
  FHN (First Horizon Corporation, Financials),
  ZION (Zions Bancorporation, National Association, Financials).

Evidence: goal hidden_files/peer-batch22-20261005/ (<T>_def14a.htm +
<T>_def14a.txt x9, batch22_submissions.json, ctx.py, fetch_def14a.py).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

NEW_NODES = {
    'SEDG': ("SolarEdge Technologies, Inc.", 'Information Technology'),
    'KW': ("Kennedy-Wilson Holdings, Inc.", 'Real Estate'),
    'CMC': ("Commercial Metals Company", 'Materials'),
    'RS': ("Reliance, Inc.", 'Materials'),
    'FHN': ("First Horizon Corporation", 'Financials'),
    'ZION': ("Zions Bancorporation, National Association", 'Financials'),
}

NEW = {
    'ENPH': ('DEF 14A 2026-04-01',
             ['BE', 'NXT', 'SEDG', 'ENTG', 'QRVO', 'RUN', 'PSTG', 'REZI',
              'TER', 'FSLR', 'RIVN', 'WOLF', 'GNRC', 'SWKS', 'ZBRA',
              'MPWR']),
    'HBAN': ('DEF 14A 2026-03-12',
             ['CFG', 'CMA', 'FITB', 'FHN', 'KEY', 'MTB', 'PNC', 'RF',
              'TFC', 'USB', 'ZION']),
    'KEY': ('DEF 14A 2026-03-27',
            ['CFG', 'CMA', 'FITB', 'HBAN', 'MTB', 'PNC', 'RF', 'TFC',
             'USB', 'ZION']),
    'MTD': ('DEF 14A 2026-03-18',
            ['A', 'AME', 'BIO', 'BRKR', 'FTV', 'HOLX', 'IEX', 'ISRG',
             'NDSN', 'RVTY', 'RMD', 'ROK', 'TDY', 'TFX', 'WAT', 'XYL']),
    'O': ('DEF 14A 2026-03-25',
          ['ARE', 'EQIX', 'PLD', 'AVB', 'EQR', 'PSA', 'BXP', 'JLL',
           'SPG', 'CBRE', 'KW', 'HIG', 'CCI', 'MET', 'VTR', 'DLR',
           'NTRS', 'WELL']),
    'ROST': ('DEF 14A 2026-04-07',
             ['BBWI', 'BBY', 'BURL', 'DKS', 'DG', 'DLTR', 'FL', 'GPS',
              'KSS', 'M', 'JWN', 'PVH', 'TJX', 'TSCO', 'ULTA', 'VFC',
              'WSM']),
    'STLD': ('DEF 14A 2026-03-27',
             ['AGCO', 'NEM', 'AA', 'NUE', 'CLF', 'PCAR', 'CMC', 'PH',
              'CMI', 'RS', 'FCX', 'X', 'ITW']),
}

# expected old edge sets (assertion guard) -- captured at 2026-10-05 06:00
# PDT from peer-network.json (1034 nodes / 7,680 edges).
EXPECTED_OLD = {
    'ENPH': ['FSLR', 'GNRC', 'MPWR', 'SWKS', 'TER', 'ZBRA'],
    'HBAN': ['CFG', 'KEY', 'MTB', 'PNC', 'RF', 'TFC'],
    'KEY': ['CFG', 'HBAN', 'MTB', 'PNC', 'RF', 'TFC'],
    'MTD': ['FTV', 'HOLX', 'IEX', 'ISRG', 'NDSN', 'WAT'],
    'O': ['ARE', 'BXP', 'DLR', 'EQIX', 'MET', 'VTR'],
    'ROST': ['BBY', 'DG', 'DLTR', 'TSCO', 'ULTA', 'WSM'],
    'STLD': ['CMI', 'FCX', 'ITW', 'NEM', 'NUE', 'PCAR'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261005_0600_pre_batch22.json')
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
        assert len(set(old_targets)) == len(old_targets), \
            f'{src}: duplicate old edges'
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
    net['metadata']['last_updated'] = '2026-10-05'
    net['metadata']['last_dq_repair'] = '2026-10-05'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
