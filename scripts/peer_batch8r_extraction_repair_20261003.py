#!/usr/bin/env python3
"""Peer-network batch-8r peer-orphan extraction repair (2026-10-03 10:00 PDT run).

Follow-up to the batch-8a..8q fingerprint runs (2026-10-01/02/03) and the
2026-10-03 07:38 orphan-affordance Improve run, which found the network's
largest remaining structural gap: 31 tracked S&P 500 companies with
out_degree 0 whose own peer groups were NEVER extracted from their DEF
14As (heaviest inbound hubs: HOLX 22 / MA 21 / SYK 19 / C 17 / FDX 16 /
GS 15). Batch-8r extracts the 6 heaviest of those VERBATIM from their
latest DEF 14As. TSR/performance comparator groups, index-only groups,
unnamed survey databases, and explicitly-removed companies are
documented but unstored per the batches 3-8r convention.

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (CIKs verified against
compensation.json - HOLX 0000859737 / MA 0001141391 / SYK 0000310764 /
C 0000831001 / FDX 0001048911 / GS 0000886982), filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential, ~2s
pacing; non-padded CIK in Archive URLs; primaryDocument from each
filing's submissions primaryDocument field). Peer sections transcribed
verbatim. Evidence in goal hidden_files/peer-batch8r-20261003/
<TICKER>_peer.txt (verbatim transcriptions) + batch8r_filings.json
(accession/URL map); filing HTMLs persisted to the goal dir AT download
time (the batch-8h /tmp-peersweep-wipe lesson).

Repairs (6 sources; latest DEF 14A each):

  HOLX  0 -> 15 (DEF 14A 2025-01-16; 2024 Primary Peer Group verbatim,
        15 Health Care cos; no changes approved for fiscal 2025 per the
        filing; Hologic's 15-12G filed 2026-04-17 means this is its last
        authoritative comp peer group before going private. Supplemental
        Practices Peer Group explicitly "not used to set compensation"
        -> UNSTORED. No marks.)
  MA    0 -> 16 (DEF 14A 2026-04-27; 2025 compensation decision-making
        peer group verbatim (16, with filing tickers); DFS stored
        verbatim (2025 operative) - the COF-for-DFS swap is effective
        for 2026 decisions -> documented, UNSTORED per the TMUS batch-8p
        2026-variant precedent; filing "Fiserv (FI)" maps to network node
        FISV (same company, network canonical ticker). MSFT SURVIVES
        genuine (fingerprint target, MA home Financials vs MSFT home IT)
        -> new verified_cross_sector mark 63->64. BKNG cross-sector but
        not a fingerprint target -> no mark per ORLY batch-8q.)
  SYK   0 -> 17 (DEF 14A 2026-03-23; Semler Brossy 2024 benchmarking
        comparison group verbatim (17), committee-approved and used for
        2025 comp decisions; the mid-2025 study used the same group -
        this is the comp-decisions benchmarking group, stored. No marks.)
  C     0 -> 13 (DEF 14A 2026-04-02; 2025 COMPENSATION PEER GROUP verbatim
        (13, with filing tickers); the 5-bank "core peer group" is a
        subset of the stored 13, not a separate stored group; the
        9-bank relative-performance narrower group + PvP index group
        UNSTORED; filing "BNY Mellon (BK)" maps to network node BNY
        (same company, network canonical ticker); COF is a fingerprint
        target but home-sector Financials matches C -> no mark. No marks.)
  GS    0 -> 9  (DEF 14A 2026-03-20; "Our Peers" comp benchmarking peer
        set verbatim - 6 U.S. + 3 European peers; filing "BNY Mellon
        (BK)" maps to network node BNY; new nodes BCS (Barclays PLC),
        DB (Deutsche Bank AG), UBS (UBS Group AG) - Financials ADRs.
        "Other Companies Considered" (unnamed asset managers / S&P 100)
        + SVC Awards relative-threshold peer group (performance-only) +
        PvP S&P 500 Financials index UNSTORED. No marks.)
  FDX   (DEF 14A 2026-08-17; NO named compensation peer group - comp
        benchmarking uses unnamed general-industry survey data (124
        companies fiscal 2026); only named group is the Dow Jones
        Transportation Average PvP TSR -> index-only, UNSTORED. FDX
        joins the verified-absent set: isSource None -> False, per the
        ADM batch-8a precedent.)

New nodes: 3 (BCS, DB, UBS - Financials ADRs from GS) - registered in
PEER_ONLY_NODES and in mark_verified_cross_sector REPAIR_SCRIPTS BEFORE
the repair ran (the batch-5 / batch-8h lessons held).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'BCS': ('Barclays PLC', 'Financials'),
    'DB': ('Deutsche Bank AG', 'Financials'),
    'UBS': ('UBS Group AG', 'Financials'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'HOLX': ('DEF 14A 2025-01-16',
             ['A', 'IDXX', 'STE', 'BAX', 'ILMN', 'TFX', 'BSX', 'ISRG',
              'COO', 'XRAY', 'RMD', 'WAT', 'EW', 'RVTY', 'ZBH']),
    'MA': ('DEF 14A 2026-04-27',
           ['ACN', 'ADBE', 'AXP', 'XYZ', 'BKNG', 'AVGO', 'DFS', 'FISV',
            'IBM', 'INTU', 'MSFT', 'ORCL', 'PYPL', 'CRM', 'SPGI', 'V']),
    'SYK': ('DEF 14A 2026-03-23',
            ['ABT', 'DHR', 'DGX', 'AMGN', 'LLY', 'REGN', 'BAX', 'GEHC',
             'TMO', 'BDX', 'GILD', 'VTRS', 'BIIB', 'LH', 'ZBH', 'BSX',
             'MDT']),
    'C': ('DEF 14A 2026-04-02',
          ['AIG', 'GS', 'PRU', 'AXP', 'JPM', 'USB', 'BAC', 'MET', 'WFC',
           'BNY', 'MS', 'COF', 'PNC']),
    'GS': ('DEF 14A 2026-03-20',
           ['BAC', 'C', 'JPM', 'MS', 'BNY', 'WFC', 'BCS', 'DB', 'UBS']),
}

# never-extracted sources: expected old edge set is EMPTY (assertion guard)
EXPECTED_OLD = {
    'HOLX': [],
    'MA': [],
    'SYK': [],
    'C': [],
    'GS': [],
}


def main():
    bak = SRC.replace('.json', '_backup_20261003_1000_pre_batch8r.json')
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

    # 2. FDX: no named comp group -> verified-absent, flip isSource
    old_fdx = [e for e in edges if e['source'] == 'FDX']
    assert old_fdx == [], f'FDX: unexpected stored edges: {old_fdx}'
    assert by_ticker['FDX'].get('isSource') is None, 'FDX: already classified'
    by_ticker['FDX']['isSource'] = False
    print('FDX: 0 old -> 0 new (no named comp peer group, DEF 14A 2026-08-17; '
          'isSource None -> False)')

    # 3. assert (empty) old edge sets + add verbatim edges for the sources
    for src, (filing, peers) in NEW.items():
        assert src in by_ticker, f'{src}: not a node'
        for t in peers:
            assert t in by_ticker, f'{src}: unknown target {t}'
        assert src not in peers, f'{src}: self-edge'
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        assert old_targets == sorted(EXPECTED_OLD[src]), \
            f'{src}: old edge set changed: {old_targets}'
        year = int(filing.rsplit(' ', 1)[1].split('-')[0])
        for t in peers:
            edges.append({'source': src, 'target': t, 'year': year,
                          'group_type': 'primary', 'filing': filing})
        new_check = sorted(e['target'] for e in edges if e['source'] == src)
        assert new_check == sorted(peers), f'{src}: new edge set mismatch'
        assert len(set(new_check)) == len(new_check), f'{src}: duplicates'
        by_ticker[src]['isSource'] = True
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
