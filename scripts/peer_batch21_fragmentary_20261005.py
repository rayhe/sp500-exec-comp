#!/usr/bin/env python3
"""Peer-network batch-21 fragmentary-source sweep, tranche 3 (2026-10-05 03:55 PDT run).

Closes the batch-20 observation class "fragmentary stored groups invisible to
the fingerprint queue" for the 8 remaining deg-5 sources (AVB/CINF/ELV/HAS/
LUV/MS/UHS/ULTA, all confirmed exactly out_degree 5). Triage first per the
batch-20 note: MS/LUV/ELV/CINF/AVB looked plausibly complete; HAS/UHS/ULTA
looked likely fragmentary. Triage verdict: ELV is genuinely complete
(Direct Industry Group == stored 5; General Industry Group dual-role
UNSTORED, Fortune-50 revenue screen) and is LEFT UNCHANGED. The other 7
are repaired wholesale (assert-then-replace, EXPECTED_OLD captured
2026-10-05 03:55 PDT).

Adjudications (all against the stored edges' own DEF 14As; all also the
latest, pinned=False for all 8):

- AVB 5->14 (DEF 14A 2026-04-06, acc. 0001104659-26-039943): the operative
  group is the 14-co 2025 peer group (plus self AVB) printed ONLY as a
  chart image (avb-20250520xdef14a_a173.jpg, transcribed visually -- third
  STT/WM-class image blind spot). Stored EQR/ESS/MAA/UDR genuine but
  fragmentary. SPGI FABRICATED (zero peer naming; the sole "S&P Global"
  full-text mention is the chart's "Source: S&P Global" line -- new
  vector: chart-source pickup).
- CINF 5->9 (DEF 14A 2026-03-18, acc. 0000020286-26-000015): 2025 peer
  group verbatim 9 (ALL, CNA, THG, HIG, MKL, SIGI, TRV, UFCS, WRB). Stored
  ALL/HIG/TRV genuine but fragmentary. BLK/STT dropped: both appear only
  as institutional shareholders in the 13G beneficial-ownership table,
  never as peer-group members -- new vector: shareholder-pickup (13G
  table pickup).
- HAS 5->12 (DEF 14A 2026-04-17, acc. 0001193125-26-160426): operative
  group is the 12-co 2025 compensation peer group; the 10-co 2026 group
  (remove HSY/SJM) is forward-looking and UNSTORED per the operative-
  group convention. All 5 stored genuine (incl. HAS->HSY, the batch-16
  metadata-verified asymmetry edge, re-marked via this batch's repair
  map).
- LUV 5->8 (DEF 14A 2026-03-27, acc. 0001193125-26-127237): operative
  group is the 8-co LTIP "Peer Group" (ALK/ALGT/AAL/DAL/ULCC/JBLU/SAVE/
  UAL); the filing's only other named reference is the PvP S&P 500
  Retailing index, UNSTORED. Stored 5 genuine but fragmentary.
- MS 5->8 (DEF 14A 2026-04-02, acc. 0001140361-26-012975): operative group
  is the 8-co ROTCE Comparison Group (BAC, BCS, C, DB, GS, JPM, UBS,
  WFC), used for the 2025 PSU awards (Relative ROTCE, 2026-2028 period).
  Stored 5 genuine but fragmentary. BCS/DB/UBS stored as US ADR tickers
  per the ALIZY precedent.
- UHS 5->12 (DEF 14A 2026-04-09, acc. 0001193125-26-148814): operative
  group is the 12-co Compensation Peer Group; the PvP "TSR peer group"
  (10-K industry-line group: ACHC/CYH/HCA/THC + self) is a disclosure
  group, dual-role UNSTORED. Stored 5 genuine but fragmentary.
- ULTA 5->13 (DEF 14A 2026-04-22, acc. 0001104659-26-046308): 2025
  Compensation Peer Group verbatim 13 (UAA removed, GPS added vs 2024).
  Stored 5 genuine but fragmentary.
- ELV left unchanged (DEF 14A 2026-03-27, acc. 0001156039-26-000031):
  stored CI/CNC/CVS/HUM/UNH == the filing's 2025 Direct Industry Group
  exactly; the General Industry Group (Fortune 50 revenue screen) is
  dual-role UNSTORED per the HAL/KHC/ACGL convention. Triage evidence
  recorded, no repair.

New peer-only nodes (10), registered in guard PEER_ONLY_NODES + mark_verified
REPAIR_SCRIPTS BEFORE the repair (batch-5/8h/8z/17/19/20 ordering held):
  SIGI (Selective Insurance Group, Inc., Financials),
  UFCS (United Fire Group, Inc., Financials),
  IHRT (iHeartMedia, Inc., Communication Services),
  TOY (Spin Master Corp., Consumer Discretionary),
  MODG (Topgolf Callaway Brands Corp., Consumer Discretionary),
  ALGT (Allegiant Travel Company, Industrials),
  ULCC (Frontier Group Holdings, Inc., Industrials),
  ACHC (Acadia Healthcare Company, Inc., Health Care),
  BKD (Brookdale Senior Living Inc., Health Care),
  CYH (Community Health Systems, Inc., Health Care).

New contamination vectors documented: chart-source pickup (AVB->SPGI from
the peer-chart's "Source: S&P Global" line -- instance of the source-line
class); shareholder-pickup (CINF->BLK/STT from the 13G ownership table).

Evidence: goal hidden_files/peer-batch21-20261005/ (<T>_def14a.htm +
<T>_def14a.txt x8, AVB_peerchart.jpg, batch21_submissions.json,
fetch_def14a.py).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

NEW_NODES = {
    'SIGI': ("Selective Insurance Group, Inc.", 'Financials'),
    'UFCS': ("United Fire Group, Inc.", 'Financials'),
    'IHRT': ("iHeartMedia, Inc.", 'Communication Services'),
    'TOY': ("Spin Master Corp.", 'Consumer Discretionary'),
    'MODG': ("Topgolf Callaway Brands Corp.", 'Consumer Discretionary'),
    'ALGT': ("Allegiant Travel Company", 'Industrials'),
    'ULCC': ("Frontier Group Holdings, Inc.", 'Industrials'),
    'ACHC': ("Acadia Healthcare Company, Inc.", 'Health Care'),
    'BKD': ("Brookdale Senior Living Inc.", 'Health Care'),
    'CYH': ("Community Health Systems, Inc.", 'Health Care'),
}

NEW = {
    'AVB': ('DEF 14A 2026-04-06',
            ['WELL', 'SPG', 'DLR', 'PSA', 'VTR', 'EXR', 'EQR', 'BXP',
             'INVH', 'ESS', 'SUI', 'MAA', 'UDR', 'AMH']),
    'CINF': ('DEF 14A 2026-03-18',
             ['ALL', 'CNA', 'THG', 'HIG', 'MKL', 'SIGI', 'TRV', 'UFCS',
              'WRB']),
    'HAS': ('DEF 14A 2026-04-17',
            ['CROX', 'MAT', 'HSY', 'EA', 'RBLX', 'SJM', 'IHRT', 'TOY',
             'MODG', 'LYV', 'TTWO', 'UAA']),
    'LUV': ('DEF 14A 2026-03-27',
            ['ALK', 'ALGT', 'AAL', 'DAL', 'ULCC', 'JBLU', 'SAVE',
             'UAL']),
    'MS': ('DEF 14A 2026-04-02',
           ['BAC', 'BCS', 'C', 'DB', 'GS', 'JPM', 'UBS', 'WFC']),
    'UHS': ('DEF 14A 2026-04-09',
            ['ACHC', 'HSIC', 'BKD', 'LH', 'CYH', 'MOH', 'DVA', 'DGX',
             'EHC', 'SEM', 'HCA', 'THC']),
    'ULTA': ('DEF 14A 2026-04-22',
             ['AZO', 'GPS', 'ROST', 'BBWI', 'LULU', 'TSCO', 'BURL',
              'ORLY', 'VFC', 'DKS', 'PVH', 'WSM', 'FL']),
}

# expected old edge sets (assertion guard) -- captured at 2026-10-05 03:55
# PDT from peer-network.json (1024 nodes / 7,639 edges).
EXPECTED_OLD = {
    'AVB': ['EQR', 'ESS', 'MAA', 'SPGI', 'UDR'],
    'CINF': ['ALL', 'BLK', 'HIG', 'STT', 'TRV'],
    'HAS': ['EA', 'HSY', 'LYV', 'RBLX', 'TTWO'],
    'LUV': ['AAL', 'ALK', 'DAL', 'JBLU', 'UAL'],
    'MS': ['BAC', 'C', 'GS', 'JPM', 'WFC'],
    'UHS': ['DGX', 'DVA', 'HCA', 'HSIC', 'MOH'],
    'ULTA': ['AZO', 'LULU', 'ROST', 'TSCO', 'WSM'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261005_0330_pre_batch21.json')
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
