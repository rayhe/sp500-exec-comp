#!/usr/bin/env python3
"""Peer-network batch-17 wholesale re-read (2026-10-04 19:30 PDT run).

Closes the batch-9 observation class "stored group diverges from latest
filing beyond the flagged edge": ROK and IP both had exactly one queued
cross-sector fingerprint edge each (ROK->GIS, IP->GIS - both dropped
filing-verbatim in batch-9), but their stored edge sets diverge from the
same DEF 14A's printed peer group beyond the flagged edge. Full verbatim
re-read + wholesale edge-set replace, assert-then-replace convention from
batches 8a-8z.

- ROK (18->18): 2025 Compensation Peer Group verbatim 18 (DEF 14A
  2025-12-22, acc. 0001308179-25-000665): AMETEK/Amphenol/Autodesk/
  Corning/Dover/Eaton/Emerson/Fortive/Intuit/Keysight/NetApp/PANW/
  Parker-Hannifin/Seagate/Synopsys/TE Connectivity/Trimble/Zebra.
  Dropped AMAT + WTW fabrications (WTW is the filing's named consultant -
  "led by Willis Towers Watson, the Committee removed VMware from the
  peer group" - the extraction vector; AMAT similarly absent full-text).
  Restored GLW + TEL genuine peers. Old WTW edge removal clears the
  compensation-consultant contamination vector documented here.
- IP (17->18): 2025 Compensation Comparator Group (CCG) verbatim 18
  (DEF 14A 2026-03-27, acc. 0001628280-26-021729): Ball/Berry Global/
  Bunge/Carrier/Crown Holdings/Cummins/Eaton/Emerson/General Dynamics/
  Johnson Controls/LyondellBasell/Northrop Grumman/Nucor/Packaging Corp/
  Parker-Hannifin/PPG/Schlumberger/Smurfit WestRock. Dropped AVY/DD/DOW/
  ECL/EMN fabrications (zero full-text mentions, confirmed in the
  batch-9 filing read). Restored BERY/BG/CCK/NOC/SLB/SW genuine peers.
  Filing misspells "Northrup Grumman" (sic; NOC unambiguous). The CCG's
  bold/italic TSR Peer Group overlap (footnote 1) is UNSTORED per the
  HAL/KHC/ACGL dual-role convention. BERY footnote (2): acquired by
  Amcor Plc on April 30, 2025 - retained under last ticker per the
  PNR/SMAR/SAVE/X delisted-peer precedent.

New peer-only nodes (1): BERY (Berry Global Group, Inc., Materials;
acquired by Amcor Plc 2025-04-30). Registered in guard PEER_ONLY_NODES
+ mark_verified REPAIR_SCRIPTS BEFORE the repair (batch-5/8h/8z
lessons held).

Evidence: goal hidden_files/peer-batch9-20261004/ (ROK_def14a.htm,
IP_def14a.htm, batch9_submissions.json accession/URL map) + this run's
goal hidden_files/peer-batch17-20261004/ (render_check.py + d3.min.js).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

NEW_NODES = {
    'BERY': ("Berry Global Group, Inc.", 'Materials'),
}

NEW = {
    'ROK': ('DEF 14A 2025-12-22',
            ['ADSK', 'AME', 'APH', 'DOV', 'EMR', 'ETN', 'FTV', 'GLW',
             'INTU', 'KEYS', 'NTAP', 'PANW', 'PH', 'SNPS', 'STX', 'TEL',
             'TRMB', 'ZBRA']),
    'IP': ('DEF 14A 2026-03-27',
           ['BALL', 'BERY', 'BG', 'CARR', 'CCK', 'CMI', 'EMR', 'ETN',
            'GD', 'JCI', 'LYB', 'NOC', 'NUE', 'PH', 'PKG', 'PPG',
            'SLB', 'SW']),
}

# expected old edge sets (assertion guard) -- captured at 2026-10-04 19:30
# PDT from peer-network.json (1006 nodes / 7,354 edges).
EXPECTED_OLD = {
    'ROK': ['ADSK', 'AMAT', 'AME', 'APH', 'DOV', 'EMR', 'ETN', 'FTV',
            'INTU', 'KEYS', 'NTAP', 'PANW', 'PH', 'SNPS', 'STX', 'TRMB',
            'WTW', 'ZBRA'],
    'IP': ['AVY', 'BALL', 'CARR', 'CMI', 'DD', 'DOW', 'ECL', 'EMN',
           'EMR', 'ETN', 'GD', 'JCI', 'LYB', 'NUE', 'PH', 'PKG', 'PPG'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261004_1930_pre_batch17.json')
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
    net['metadata']['last_updated'] = '2026-10-04'
    net['metadata']['last_dq_repair'] = '2026-10-04'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
