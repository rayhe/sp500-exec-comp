#!/usr/bin/env python3
"""Peer-network batch-20 fragmentary-source sweep, tranche 2 (2026-10-05 02:15 PDT run).

Closes the batch-19 observation class "fragmentary stored groups invisible to
the fingerprint queue" for the 10 remaining deg<=4 sources (the batch-19
tranche-1 entry listed ~21 n<=5 candidates; the deg-5 set AVB/CINF/ELV/HAS/
LUV/MS/UHS/ULTA is tranche 3). 10 sources re-read filing-verbatim against
the stored edges' own DEF 14As (all also the latest; pinned=False for all 10)
and replaced wholesale (assert-then-replace, EXPECTED_OLD captured 2026-10-05
02:15 PDT). No drop-all this run: all 10 disclose a peer list.

Adjudications (all against the stored edges' own filings):

- CZR 3->11 (DEF 14A 2026-04-23, acc. 0001193125-26-174058): 2025 peer group
  verbatim 11 (gaming/hospitality/hotel/leisure). Stored CCL/HLT/NCLH all
  genuine but fragmentary.
- UBER 3->19 (DEF 14A 2026-03-23, acc. 0001308179-26-000125): 2025 peer group
  verbatim 19. Stored BKNG/DASH/EXPE genuine but fragmentary. "Block"
  stored as XYZ per the network's Block convention (XYZ is a company node;
  SQ absent).
- VRSN 3->18 (DEF 14A 2026-04-10, acc. 0001014473-26-000013): the operative
  group is the 18-co 2025 peer group ("in making 2025 compensation
  decisions"). The Oct-2025-approved 2026 group (remove SNPS/ANSS, add
  DLR/IRDM) is forward-looking and UNSTORED per the operative-group
  convention (BA/A batch-19 precedent). Stored GPN/SNPS genuine; DLR
  dropped (2026-forward member). ANSS stored as last ticker (delisted Jul
  2025 on the completed Synopsys acquisition, per the ENIA precedent).
- TER 3->18 (DEF 14A 2026-03-27, acc. 0001193125-26-127504): 2025 peer group
  verbatim 18. Stored ON genuine. KLAC dropped: the filing's 2025 revision
  explicitly EXCLUDES KLA-Tencor (disproportionate size) -- stale member,
  not a 2025 peer. LRCX dropped: Lam Research is not a peer-group member;
  it appears only in director bios (former employers -- batch-19
  director-bio pickup vector) and in the separate "VC Comparison Group"
  (variable-cash program, dual-role UNSTORED per HAL/KHC/ACGL convention).
  "Trimble Navigation" stored as TRMB.
- WM 3->20 (DEF 14A 2026-03-31, acc. 0001104659-26-037381): the operative
  group is the 20-co 2025 comparison group, printed as a chart image
  (bc_peercompany-pn.jpg, transcribed visually -- the STT batch-18 image
  blind spot, second instance). The text-printed 25-co list is the
  2026-forward peer group (FW Cook 2025 refresh) and UNSTORED per the
  operative-group convention. Stored UNP genuine; CARR/JCI dropped (both
  2026-forward members, filing-named but not operative for this proxy).
- COIN 4->20 (DEF 14A 2026-04-24, acc. 0001679788-26-000045): 2025 peer group
  verbatim 20 (Dropbox/Splunk removed, EBAY/NFLX/PYPL/CRM/UBER added).
  Stored CRM/NFLX/PYPL/UBER genuine but fragmentary. "Block" -> XYZ.
- DUK 4->20 (DEF 14A 2026-03-20, acc. 0001104659-26-032443): compensation peer
  group verbatim 20. Stored DE/ETN/RTX/SO genuine but fragmentary.
- OMC 4->7 (DEF 14A 2026-03-26, acc. 0001213900-26-034811): peer group
  verbatim 7 (unchanged from last year "other than the removal of IPG due
  to the Merger"). Stored ACN/ADP/CTSH/PARA genuine but fragmentary. The
  pay-vs-performance "Peer Group TSR" (WPP + Publicis) is dual-role
  UNSTORED.
- RL 4->16 (DEF 14A 2026-06-18, acc. 0001140361-26-025788): Fiscal 2026 peer
  group verbatim 16 (RL FY ends March; this proxy is the FY2026 proxy, so
  the Fiscal 2026 group is operative). Stored NKE/TPR/WSM genuine; AWK
  FABRICATED (zero "American Water" full-text mentions; new vector
  instance: partial-name match -- "American Eagle Outfitters" -> AWK
  (American Water), same class as MPWR->UHS batch-19).
- VLTO 4->16 (DEF 14A 2026-03-27, acc. 0001967680-26-000016): the operative
  group is the FORMER 16-co peer group (market data reviewed Nov 2024 /
  Feb 2025 "in connection with its named executive officer compensation
  decisions"). The July-2025 update (remove A/CLH, add EMR/IR) and the
  December-2025 16-co list are forward-looking and UNSTORED per the
  operative-group convention. Stored ECL/ROP genuine; DHR dropped
  (director-bio/spinoff-parent pickup -- 59 Danaher mentions, none as a
  peer; batch-19 vector); IR dropped (2026-forward addition).

New peer-only nodes (5), registered in guard PEER_ONLY_NODES + mark_verified
REPAIR_SCRIPTS BEFORE the repair (batch-5/8h/8z/17/19 ordering held):
  CGNX (Cognex Corporation, Information Technology),
  CAR (Avis Budget Group, Inc., Industrials),
  GIII (G-III Apparel Group, Ltd., Consumer Discretionary),
  GPS (The Gap, Inc., Consumer Discretionary),
  FL (Foot Locker, Inc., Consumer Discretionary).

New contamination vectors documented: partial-name match "American" -> AWK
(instance of the batch-19 class); director-bio + spinoff-parent pickup for
VLTO->DHR (instance of the batch-19 director-bio class).

Evidence: goal hidden_files/peer-batch20-20261005/ (<T>_def14a.htm +
<T>_def14a.txt x10, WM_peerchart.jpg + bc_peercompany-pn.jpg source,
batch20_submissions.json, fetch_def14a.py).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

NEW_NODES = {
    'CGNX': ("Cognex Corporation", 'Information Technology'),
    'CAR': ("Avis Budget Group, Inc.", 'Industrials'),
    'GIII': ("G-III Apparel Group, Ltd.", 'Consumer Discretionary'),
    'GPS': ("The Gap, Inc.", 'Consumer Discretionary'),
    'FL': ("Foot Locker, Inc.", 'Consumer Discretionary'),
}

NEW = {
    'CZR': ('DEF 14A 2026-04-23',
            ['BYD', 'CCL', 'HLT', 'H', 'LVS', 'MAR', 'MGM', 'NCLH',
             'PENN', 'RCL', 'WYNN']),
    'UBER': ('DEF 14A 2026-03-23',
             ['ADBE', 'EBAY', 'PYPL', 'ABNB', 'EXPE', 'CRM', 'GOOGL',
              'INTU', 'SPOT', 'AMZN', 'LYFT', 'TSLA', 'XYZ', 'META', 'V',
              'BKNG', 'NFLX', 'DASH', 'ORCL']),
    'VRSN': ('DEF 14A 2026-04-10',
             ['AKAM', 'EQIX', 'JKHY', 'ANSS', 'FFIV', 'PAYX', 'ADSK',
              'FDS', 'ROP', 'BR', 'FTNT', 'SNPS', 'CDNS', 'GDDY', 'TDC',
              'CPAY', 'GPN', 'VRSK']),
    'TER': ('DEF 14A 2026-03-27',
            ['CDNS', 'MPWR', 'CRUS', 'ON', 'CGNX', 'PTC', 'ENTG', 'QRVO',
             'FTV', 'ROK', 'KEYS', 'SWKS', 'MRVL', 'TDY', 'MCHP', 'TRMB',
             'MKSI', 'ZBRA']),
    'WM': ('DEF 14A 2026-03-31',
           ['AEP', 'CAR', 'CHRW', 'CSX', 'ETR', 'FDX', 'GWW', 'HAL',
            'JBHT', 'NEE', 'NSC', 'RSG', 'R', 'SLB', 'SO', 'LUV', 'SYY',
            'UNP', 'UPS', 'WCN']),
    'COIN': ('DEF 14A 2026-04-24',
             ['ABNB', 'PANW', 'SNOW', 'XYZ', 'PYPL', 'TTD', 'DOCU',
              'PINS', 'TWLO', 'DASH', 'HOOD', 'UBER', 'EBAY', 'CRM',
              'WDAY', 'INTU', 'SHOP', 'ZM', 'NFLX', 'SNAP']),
    'DUK': ('DEF 14A 2026-03-20',
            ['MMM', 'EIX', 'NEE', 'SO', 'AEP', 'EXC', 'NOC', 'UNP', 'DE',
             'GD', 'PCG', 'UPS', 'D', 'HON', 'RTX', 'WM', 'ETN', 'LMT',
             'TXN', 'XEL']),
    'OMC': ('DEF 14A 2026-03-26',
            ['ACN', 'DXC', 'WPP', 'ADP', 'PARA', 'CTSH', 'TRI']),
    'RL': ('DEF 14A 2026-06-18',
           ['ANF', 'GIII', 'NKE', 'URBN', 'AEO', 'GPS', 'PVH', 'VFC',
            'CPRI', 'HBI', 'LEVI', 'TPR', 'WSM', 'FL', 'LULU', 'UAA']),
    'VLTO': ('DEF 14A 2026-03-27',
             ['AME', 'FTV', 'PNR', 'DCI', 'IEX', 'ROK', 'DOV', 'ROP',
              'ECL', 'KEYS', 'XYL', 'MTD', 'ZBRA', 'FLS', 'A', 'CLH']),
}

# expected old edge sets (assertion guard) -- captured at 2026-10-05 02:15
# PDT from peer-network.json (1019 nodes / 7,509 edges).
EXPECTED_OLD = {
    'CZR': ['CCL', 'HLT', 'NCLH'],
    'UBER': ['BKNG', 'DASH', 'EXPE'],
    'VRSN': ['DLR', 'GPN', 'SNPS'],
    'TER': ['KLAC', 'LRCX', 'ON'],
    'WM': ['CARR', 'JCI', 'UNP'],
    'COIN': ['CRM', 'NFLX', 'PYPL', 'UBER'],
    'DUK': ['DE', 'ETN', 'RTX', 'SO'],
    'OMC': ['ACN', 'ADP', 'CTSH', 'PARA'],
    'RL': ['AWK', 'NKE', 'TPR', 'WSM'],
    'VLTO': ['DHR', 'ECL', 'IR', 'ROP'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261005_0200_pre_batch20.json')
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
