#!/usr/bin/env python3
"""Peer-network batch-8o fingerprint-queue repair (2026-10-02 23:30 PDT run).

Follow-up to the batch-8a..8n runs (2026-10-01/02). After 8n, the Section-19
fingerprint queue held 190 cross-sector fingerprint-target edges pending
across 150 sources (61 verified marks); the heaviest remaining tier is 40
sources with exactly 2 queued edges each. Batch-8o takes the 6 heaviest of
those by total outbound edge count (VRTX 16 / WELL 16 / BSX 15 / SW 15 /
IT 15 / IDXX 15) and re-extracts each source's comp-decisions peer group
VERBATIM from its latest DEF 14A, keeping only edges that match the
verbatim group. TSR/performance comparator groups, index-only groups,
unnamed survey databases, and explicitly-removed companies are documented
but unstored per the batches 3-8n convention.

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run; CIKs verified against
compensation.json - VRTX 0000875320 / WELL 0000766704 / BSX 0000885725 /
SW 0002005951 / IT 0000749251 / IDXX 0000874716), filing HTML fetched
with User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential,
~2s pacing; non-padded CIK in Archive URLs + curl -L per the batch-8d
note; primary document names from each filing's submissions
primaryDocument field). Peer sections transcribed verbatim. Evidence in
goal hidden_files/peer-batch8o-20261002/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8o_filings.json (accession/URL map); filing HTMLs
persisted to the goal dir AT download time (the batch-8h /tmp-peersweep-
wipe lesson).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  VRTX  16 -> 12 (DEF 14A 2026-04-02; 2025 Peer Group, verbatim (12);
        same group since 2022 except Seagen removed 2024 (acquired by
        Pfizer 2023); dropped BLK + COF queued fabrications + BAX +
        DXCM + HCA + HOLX + TMO non-members; added ALNY, JAZZ, BMRN
        (all already nodes); the COO-role life-science supplement
        (Baxter, DexCom, HCA, Hologic, Thermo Fisher, United
        Therapeutics, Jazz*) is role-specific benchmarking, NOT the
        peer group - UNSTORED; no marks)
  WELL  16 -> 17 (DEF 14A 2026-04-10; 2025 Compensation Peer Group,
        verbatim with filing tickers (17); no changes to the 2025 group;
        dropped COF + GIS queued fabrications; added EQR, CG (both
        already nodes); the PvP TSR peer group is
        the FTSE NAREIT Equity Health Care Index - index-only,
        UNSTORED; no marks)
  BSX   15 -> 14 (DEF 14A 2026-03-18; 2025 Peer Companies, verbatim
        (14); dropped GIS + PSA queued fabrications; all 14 filing
        peers already nodes; no marks)
  SW    15 -> 17 (DEF 14A 2026-03-11; 2025 Compensation Peer Group,
        verbatim (17); Berry Global removed following its Amcor
        acquisition (April 2025) - explicitly removed, UNSTORED per
        precedent; dropped COF queued fabrication; GIS (General Mills)
        SURVIVES genuine - filing-verbatim member of the comp peer
        group (SW = Materials, GIS home = Consumer Staples) ->
        verified_cross_sector mark SW->GIS (PYPL->COF / UNH->MSFT /
        FISV->NDAQ / FISV->BLK batch-8k precedent); added MMM, CRH,
        CCK; new node CRH (CRH plc, Materials))
  IT    15 -> 18 (DEF 14A 2026-04-15; 2025 Peer Group, verbatim (18);
        2024 review added Fortinet, Palo Alto Networks, S&P Global,
        TransUnion; removed Adobe (revenue scope), Splunk + VMware
        (acquired); dropped FRT + GIS queued fabrications + ADBE
        non-member; added INTU, MCO, SSNC, TRI, TRU, VRSK; the 100-co
        General Industry Group is unnamed - UNSTORED; no marks)
  IDXX  15 -> 16 (DEF 14A 2026-03-27; 2025 Compensation Peer Group,
        verbatim with filing tickers (16); same group as 2024; dropped
        GIS + IP queued fabrications + KEY non-member; added ILMN,
        BIO, COO, ELAN; new node ELAN (Elanco Animal Health
        Incorporated, Health Care); ISS/Glass Lewis + self-naming
        peers unnamed - UNSTORED; no marks)

Orphan cleanup (queued item "orphan nodes L/FL cleanup"):
  L (Loews Corp): investigated this run - the 2026-04-01 DEF 14A names
        NO compensation peer group (CD&A describes competing with
        subsidiary peers + NYC financial firms, no list; only the PvP
        TSR peer group is named - unstored per convention). The old
        L->KMI edge was a garbage parse of the PvP TSR group, correctly
        dropped in batch-3. L stays an honest orphan: isSource False,
        0 edges - same class as ADM/AMZN/CLX/CTAS/NRG/TSLA per the
        batch-8a precedent. No data change.
  FL (Foot Locker Inc): stale node, 0 edges, NOT in the S&P 500 roster
        (absent from compensation.json), added accidentally in 1f093d0
        with no edges ever. REMOVED this batch.

New nodes: 2 (CRH, ELAN) - registered in PEER_ONLY_NODES and in
mark_verified_cross_sector REPAIR_SCRIPTS BEFORE the repair ran (the
batch-5 / batch-8h lessons held).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'CRH': ('CRH plc', 'Materials'),
    'ELAN': ('Elanco Animal Health Incorporated', 'Health Care'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'VRTX': ('DEF 14A 2026-04-02',
             ['ABBV', 'LLY', 'ALNY', 'GILD', 'AMGN', 'INCY',
              'BIIB', 'JAZZ', 'BMRN', 'MRNA', 'BMY', 'REGN']),
    'WELL': ('DEF 14A 2026-04-10',
             ['PLD', 'HCA', 'APO', 'AMT', 'EQIX', 'SPG', 'DLR',
              'O', 'CBRE', 'PSA', 'VTR', 'AVB', 'EQR', 'CG',
              'HST', 'DOC', 'BXP']),
    'BSX': ('DEF 14A 2026-03-18',
            ['ABT', 'EW', 'DGX', 'A', 'GEHC', 'SYK', 'BAX',
             'HOLX', 'TMO', 'BDX', 'ISRG', 'ZBH', 'DHR', 'MDT']),
    'SW': ('DEF 14A 2026-03-11',
           ['MMM', 'AMCR', 'BALL', 'CRH', 'CCK', 'CMI', 'DE',
            'DOW', 'GIS', 'IP', 'KMB', 'LYB', 'MDLZ', 'PCAR',
            'PKG', 'KHC', 'TSN']),
    'IT': ('DEF 14A 2026-04-15',
           ['AKAM', 'AON', 'ADSK', 'CDNS', 'EFX', 'FTNT', 'INTU',
            'MCO', 'PANW', 'SPGI', 'NOW', 'SSNC', 'SNPS', 'IPG',
            'TRI', 'TRU', 'VRSK', 'WDAY']),
    'IDXX': ('DEF 14A 2026-03-27',
             ['A', 'ILMN', 'ALGN', 'ISRG', 'BIO', 'MTD', 'COO',
              'RVTY', 'DXCM', 'RMD', 'EW', 'STE', 'ELAN', 'WAT',
              'HOLX', 'ZTS']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-02 23:30 PT from peer-network.json (931 nodes / 7,056 edges).
EXPECTED_OLD = {
    'VRTX': ['ABBV', 'AMGN', 'BAX', 'BIIB', 'BLK', 'BMY', 'COF',
             'DXCM', 'GILD', 'HCA', 'HOLX', 'INCY', 'LLY', 'MRNA',
             'REGN', 'TMO'],
    'WELL': ['AMT', 'APO', 'AVB', 'BXP', 'CBRE', 'COF', 'DLR',
             'DOC', 'EQIX', 'GIS', 'HCA', 'HST', 'O', 'PLD',
             'SPG', 'VTR'],
    'BSX': ['A', 'ABT', 'BAX', 'DGX', 'DHR', 'EW', 'GEHC', 'GIS',
            'HOLX', 'ISRG', 'MDT', 'PSA', 'SYK', 'TMO', 'ZBH'],
    'SW': ['AMCR', 'BALL', 'CMI', 'COF', 'DE', 'DOW', 'GIS', 'IP',
           'KHC', 'KMB', 'LYB', 'MDLZ', 'PCAR', 'PKG', 'TSN'],
    'IT': ['ADBE', 'ADSK', 'AKAM', 'AON', 'CDNS', 'EFX', 'FRT',
           'FTNT', 'GIS', 'IPG', 'NOW', 'PANW', 'SNPS', 'SPGI',
           'WDAY'],
    'IDXX': ['A', 'ALGN', 'DXCM', 'EW', 'GIS', 'HOLX', 'IP', 'ISRG',
             'KEY', 'MTD', 'RMD', 'RVTY', 'STE', 'WAT', 'ZTS'],
}

# new verified_cross_sector marks (filing-verbatim cross-sector edges
# surviving repair): SW->GIS (General Mills is a verbatim member of
# Smurfit Westrock's 2025 Compensation Peer Group; SW = Materials,
# GIS home = Consumer Staples).
NEW_MARKS = [
    {'source': 'SW', 'target': 'GIS',
     'filing': 'DEF 14A 2026-03-11',
     'batch': 'peer-batch8o-20261002'},
]


def main():
    bak = SRC.replace('.json', '_backup_20261002_2330_pre_batch8o.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}

    # 0. orphan cleanup: remove stale FL node (0 edges, not in S&P 500
    #    roster, added accidentally in 1f093d0, never cited).
    fl_edges = [e for e in edges
                if e['source'] == 'FL' or e['target'] == 'FL']
    assert not fl_edges, f'FL has edges: {fl_edges}'
    assert 'FL' in by_ticker, 'FL node already gone?'
    nodes = [x for x in nodes if x['ticker'] != 'FL']
    del by_ticker['FL']
    print('removed orphan node FL (Foot Locker Inc)')

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
    net['nodes'] = nodes
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
