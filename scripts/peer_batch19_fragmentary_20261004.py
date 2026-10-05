#!/usr/bin/env python3
"""Peer-network batch-19 fragmentary-source sweep, tranche 1 (2026-10-04 23:30 PDT run).

Closes the batch-18 observation class "fragmentary stored groups invisible to
the fingerprint queue": 10 sources with out_degree <= 5 whose stored edge sets
are fragments of (or fabrications absent from) the peer group printed in the
stored edge's own DEF 14A. Full verbatim re-read + wholesale edge-set replace,
assert-then-replace convention from batches 8a-8z/17/18. One additional source
(FICO) had both stored edges fabricated and discloses no peer list at all --
drop-all, isSource -> False.

Adjudications (all against the stored edges' own filings; no JKHY-class pin
needed -- every stored filing is also the latest DEF 14A):

- FTNT 1->19 (DEF 14A 2026-04-29, acc. 0001193125-26-096787): 2025 compensation
  peer group printed verbatim = 19 tech cos (batch-16 evidence). Filing HTML
  reused from peer-batch16-20261004 (no EDGAR refetch).
- A 1->32 (DEF 14A 2026-02-06, acc. 0001193125-26-040286): FY2025 executive
  compensation peer group verbatim 32 (28 S&P 500 Health Care + TMO/DHR/WAT/
  RVTY). The LTPP ~92-co TSR peer group is UNSTORED per the HAL/KHC/ACGL
  dual-role convention. FY2026 removals (Catalent, Illumina) postdate the
  stored filing; single-filing invariant keeps the 32.
- ABNB 1->13 (DEF 14A 2026-04-24, acc. 0001193125-26-175062): "Primary Peer
  Group for 2025 Pay Decisions" verbatim 13. The 8-co secondary reference
  group (Alphabet/Amazon/Apple/Disney/Meta/Microsoft/Nike/Tesla) was
  explicitly "not included in the primary peer group" -- UNSTORED.
- AES 1->7 (DEF 14A 2026-03-20, acc. 0000874761-26-000070): the only
  company-level peer group in the filing is the 9-co Clean Energy Peer Group
  (LTC relative-TSR, 20% weight). Filing-verbatim tickers: BEP (Brookfield
  Renewable Partners), IBDRY (Iberdrola ADR), CWEN (Clearway Energy),
  NEE, DNNGY (Orsted ADR), ENIA (Enel Americas, delisted 2024 -- last ticker
  per the PNR/SMAR/SAVE/X precedent), ENLT (Enlight Renewable). EDP
  Renewables (Lisbon-only listing) and RWE Clean Energy LLC (non-listed
  subsidiary) are filing-named but unmappable to a tradeable ticker --
  documented here, not stored.
- AMP 1->14 (DEF 14A 2026-03-20, acc. 0001104659-26-032725): external Peer
  Group verbatim 14 across the three business columns. "Bank of NY Mellon"
  stored as BNY per the BK->BNY 2026-05-21 live-holder rule (batch-8c).
- BA 1->19 (DEF 14A 2026-03-06, acc. 0001193125-26-096787): "2025 COMPENSATION
  PEERS" verbatim 19. The stored JNJ edge was genuine but fragmentary. The
  filing's 2026 update (remove MMM, add GE Aerospace) postdates the stored
  filing; single-filing invariant keeps the 2025 nineteen. The S&P 500
  Aerospace & Defense TSR index is UNSTORED (index, not a company group).
- GWW 1->20 (DEF 14A 2026-03-10, acc. 0001104659-26-025575): 2025 Compensation
  Study comparator group verbatim 20. Stored GWW->WM edge is FABRICATED:
  zero "Waste Management" full-text mentions (new contamination vector:
  "W.W." initialism -> WM ticker confusion). The FY2026 update (remove Watsco,
  add Ferguson) postdates the stored filing; invariant keeps the 20.
- IVZ 1->11 (DEF 14A 2026-04-02, acc. 0001193125-26-140019): compensation
  benchmarking peer group verbatim 11 (retained since 2021). The separate TSR
  peer group is UNSTORED per the dual-role convention. "Bank of NY Mellon"
  stored as BNY per the live-holder rule.
- MPWR 2->21 (DEF 14A 2026-04-30, acc. 0001437749-26-014084): 2025 peer group
  verbatim 21. Stored MPWR->UHS edge is FABRICATED: zero "Universal Health"
  mentions (new contamination vector: partial-name match -- the filing says
  "removed Universal Display Corporation from the peer group", extractor
  mapped "Universal" -> UHS). MKS stored as MKSI ("MKS (formerly MKS
  Instruments)").
- MET 3->4 (DEF 14A 2026-04-29, acc. 0001099219-26-000026): Compensation
  Comparator Group verbatim 4: AFL, HIG, ALV (filing prints "ALV" Xetra;
  stored as ALIZY, the US ADR, to avoid collision with Autoliv NYSE:ALV --
  SMNEY/PUBGY ADR precedent), PFG. Stored MET->AMAT is FABRICATED (zero
  "Applied Materials" mentions). Stored MET->PRU and MET->GL came from the
  Performance Share TSR Peers list, not the comparator group -- dropped per
  the dual-role convention (TSR group UNSTORED).
- FICO 2->0 (DEF 14A 2026-01-27, acc. 0001193125-26-024403): both stored edges
  FABRICATED. FICO->AMZN: Amazon appears only as an AWS business partner and
  as a director's former employer (new vectors: business-partner pickup,
  director-bio pickup). FICO->UNH: UnitedHealth appears only as a director's
  former employer. The filing describes a peer group ("companies of similar
  size and from relevant industries") but never prints the member list (the
  lone "Compensation Peer Group" mention is a dangling cross-reference) --
  per the no-fabrication rule (guard 10), FICO keeps no edges and flips
  isSource -> False. First source-to-nonsource flip in the network.

New peer-only nodes (12), registered in guard PEER_ONLY_NODES + this script's
NEW_NODES BEFORE the repair (batch-5/8h/8z/17 ordering held):
  AB (AllianceBernstein Holding L.P., Financials), JHG (Janus Henderson Group
  plc, Financials), LSCC (Lattice Semiconductor Corp, Information Technology),
  POWI (Power Integrations Inc, Information Technology), SLAB (Silicon
  Laboratories Inc, Information Technology), BEP (Brookfield Renewable
  Partners L.P., Utilities), CWEN (Clearway Energy Inc, Utilities), ENLT
  (Enlight Renewable Energy Ltd, Utilities), IBDRY (Iberdrola S.A., Utilities),
  DNNGY (Orsted A/S, Utilities), ENIA (Enel Americas S.A., Utilities --
  delisted 2024, last ticker), ALIZY (Allianz SE, Financials).

Evidence: goal hidden_files/peer-batch19-20261004/ (<T>_def14a.htm +
<T>_def14a.txt x10, FTNT pair reused from peer-batch16-20261004/,
batch19_submissions.json, fetch_def14a.py).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

NEW_NODES = {
    'AB': ("AllianceBernstein Holding L.P.", 'Financials'),
    'JHG': ("Janus Henderson Group plc", 'Financials'),
    'LSCC': ("Lattice Semiconductor Corporation", 'Information Technology'),
    'POWI': ("Power Integrations, Inc.", 'Information Technology'),
    'SLAB': ("Silicon Laboratories Inc.", 'Information Technology'),
    'BEP': ("Brookfield Renewable Partners L.P.", 'Utilities'),
    'CWEN': ("Clearway Energy, Inc.", 'Utilities'),
    'ENLT': ("Enlight Renewable Energy Ltd.", 'Utilities'),
    'IBDRY': ("Iberdrola, S.A.", 'Utilities'),
    'DNNGY': ("Orsted A/S", 'Utilities'),
    'ENIA': ("Enel Americas S.A.", 'Utilities'),
    'ALIZY': ("Allianz SE", 'Financials'),
}

NEW = {
    'FTNT': ('DEF 14A 2026-04-29',
             ['AKAM', 'MRVL', 'ANET', 'NTAP', 'ADSK', 'PANW', 'CDNS',
              'NOW', 'CHKP', 'SNOW', 'NET', 'SNPS', 'CRWD', 'WDAY',
              'DDOG', 'ZM', 'DLR', 'ZS', 'EQIX']),
    'A': ('DEF 14A 2026-02-06',
          ['ALGN', 'DXCM', 'MTD', 'VRTX', 'BAX', 'EW', 'MRNA', 'VTRS',
           'BIIB', 'HOLX', 'DGX', 'WAT', 'BSX', 'IDXX', 'REGN', 'ZBH',
           'CTLT', 'ILMN', 'RMD', 'ZTS', 'CRL', 'INCY', 'RVTY', 'COO',
           'ISRG', 'SOLV', 'DHR', 'IQV', 'STE', 'DVA', 'LH', 'TMO']),
    'ABNB': ('DEF 14A 2026-04-24',
             ['ADBE', 'CRM', 'XYZ', 'NOW', 'BKNG', 'SHOP', 'DASH',
              'SPOT', 'INTU', 'UBER', 'NFLX', 'ZM', 'PINS']),
    'AES': ('DEF 14A 2026-03-20',
            ['BEP', 'IBDRY', 'CWEN', 'NEE', 'DNNGY', 'ENIA', 'ENLT']),
    'AMP': ('DEF 14A 2026-03-20',
            ['BLK', 'CG', 'JEF', 'IVZ', 'TROW', 'BNY', 'SCHW', 'MS',
             'RJF', 'STT', 'USB', 'AFL', 'PFG', 'PRU']),
    'BA': ('DEF 14A 2026-03-06',
           ['MMM', 'F', 'MSFT', 'T', 'GD', 'NOC', 'CAT', 'HON', 'PG',
            'CVX', 'IBM', 'RTX', 'CSCO', 'INTC', 'UPS', 'XOM', 'JNJ',
            'VZ', 'LMT']),
    'GWW': ('DEF 14A 2026-03-10',
            ['AZO', 'FAST', 'PH', 'CDW', 'GPC', 'SWK', 'CTAS', 'HSIC',
             'TSCO', 'CMI', 'ITW', 'URI', 'ETN', 'JCI', 'WSO', 'EBAY',
             'LKQ', 'WCC', 'EXPD', 'PCAR']),
    'IVZ': ('DEF 14A 2026-04-02',
            ['AB', 'GS', 'NTRS', 'BNY', 'JHG', 'STT', 'BLK', 'LAZ',
             'TROW', 'BEN', 'MS']),
    'MPWR': ('DEF 14A 2026-04-30',
             ['ADI', 'MCHP', 'SMTC', 'CRUS', 'MU', 'SLAB', 'COHR',
              'MKSI', 'SWKS', 'DIOD', 'ON', 'SYNA', 'ENTG', 'POWI',
              'TER', 'LSCC', 'QRVO', 'TXN', 'MRVL', 'RMBS', 'WOLF']),
    'MET': ('DEF 14A 2026-04-29',
            ['AFL', 'HIG', 'ALIZY', 'PFG']),
}

# expected old edge sets (assertion guard) -- captured at 2026-10-04 23:30
# PDT from peer-network.json (1007 nodes / 7,364 edges).
EXPECTED_OLD = {
    'FTNT': ['WDAY'],
    'A': ['RVTY'],
    'ABNB': ['NFLX'],
    'AES': ['NEE'],
    'AMP': ['BLK'],
    'BA': ['JNJ'],
    'GWW': ['WM'],
    'IVZ': ['BEN'],
    'FICO': ['AMZN', 'UNH'],
    'MPWR': ['MU', 'UHS'],
    'MET': ['AMAT', 'GL', 'PRU'],
}

# FICO: drop-all (both edges fabricated, no peer list disclosed); not in NEW
# so the single-filing invariant (mark_verified) stays vacuous for it.
DROP_ALL = {'FICO'}


def main():
    bak = SRC.replace('.json', '_backup_20261004_2330_pre_batch19.json')
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

    # 3. drop-all sources (FICO): remove edges, flip isSource
    for src in sorted(DROP_ALL):
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        assert old_targets == sorted(EXPECTED_OLD[src]), \
            f'{src}: old edge set changed: {old_targets}'
        edges = [e for e in edges if e['source'] != src]
        by_ticker[src]['isSource'] = False
        print(f'{src}: {len(old)} old -> 0 new (isSource=False, no peer '
              f'list disclosed in filing)')

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
