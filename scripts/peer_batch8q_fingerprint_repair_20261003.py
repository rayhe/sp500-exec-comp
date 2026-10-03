#!/usr/bin/env python3
"""Peer-network batch-8q fingerprint-queue repair (2026-10-03 06:00 PDT run).

Follow-up to the batch-8a..8p runs (2026-10-01/02/03). After 8p, the Section-19
fingerprint queue held 166 cross-sector fingerprint-target edges pending
across 138 sources (63 verified marks); the heaviest remaining tier is 28
sources with exactly 2 queued edges each. Batch-8q takes the 6 heaviest of
those by total outbound edge count (AVY 14 / BAX 14 / GEHC 14 / ORLY 14 /
PNR 14 / HRL 13) and re-extracts each source's comp-decisions peer group
VERBATIM from its latest DEF 14A, keeping only edges that match the
verbatim group. TSR/performance comparator groups, index-only groups,
unnamed survey databases, and explicitly-removed companies are documented
but unstored per the batches 3-8q convention.

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run; CIKs verified against
compensation.json - AVY 0000008818 / BAX 0000010456 / GEHC 0001932393 /
ORLY 0000898173 / PNR 0000077360 / HRL 0000048465), filing HTML fetched
with User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential,
~2s pacing; non-padded CIK in Archive URLs; primary document names from
each filing's submissions primaryDocument field). Peer sections transcribed
verbatim. Evidence in goal hidden_files/peer-batch8q-20261003/
<TICKER>_peer.txt (verbatim transcriptions) + batch8q_filings.json
(accession/URL map); filing HTMLs persisted to the goal dir AT download
time (the batch-8h /tmp-peersweep-wipe lesson).

Repairs (6 sources; latest DEF 14A each):

  AVY   14 -> 0  (DEF 14A 2026-03-12; discloses NO named compensation peer
        group - the only named group is the RELATIVE TSR PEER GROUP used
        solely to measure relative TSR for the 2023-2025 / 2025-2027 PU
        awards (performance-assessment, documented but UNSTORED per the
        batches 3-8q convention); compensation benchmarking uses WTW survey
        data, not a named company group. All 14 stored edges were the old
        extractor's TSR-group mapping (AMCR/BALL/DD/ECL/EMN/IFF/IP/PKG/
        PPG/SHW + SW/WMB artifacts) plus CHTR/GIS fingerprint fabrications.
        TSR-only -> isSource False, per the ADM batch-8a precedent.)
  BAX   14 -> 16 (DEF 14A 2026-03-23; "For 2025, the compensation peer group
        is as follows", verbatim, 16 Health Care cos; dropped stored BIIB +
        CHTR + GIS fabrications; added XRAY, DGX, BDX, GEHC, LH (all already
        nodes); no marks)
  GEHC  14 -> 15 (DEF 14A 2026-03-19; "Our 2025 Compensation Peer Group",
        verbatim 15; the filing also uses this same group for the PSU
        +/-20% relative-TSR modifier - it IS the comp-decisions group, not
        a separate TSR-only group, so the full group is stored; dropped
        stored CHTR + COF fabrications; added PHG (Koninklijke Philips N.V.
        ADR), SMNEY (Siemens Healthineers AG ADR) as new nodes + BDX, DGX
        (already nodes); no marks)
  ORLY  14 -> 17 (DEF 14A 2026-03-27; "The following table identifies the
        Company's 2025 peer group members", verbatim 17 with tickers in
        the table; dropped stored COF + ELV + GIS + WMB fabrications; added
        AAP, AN, BJ, DKS, LOW, SHW, GWW (all already nodes); BJ (Consumer
        Staples), GWW (Industrials), SHW (Materials) are cross-sector but
        NOT fingerprint targets -> no marks, no queue interaction)
  PNR   14 -> 23 (DEF 14A 2026-03-20; Comparator Group, verbatim with filing
        tickers (23); 2025 review ADDED Graco (GGG), ITT, Middleby (MIDD),
        Nordson (NDSN) and REMOVED Enovis (ENOV - was not stored);
        dropped stored AON + GIS + PFG + POOL fabrications; added AYI, AOS,
        CR, DCI, FLS, FBIN (already node from VMC batch-8p), GGG, ITT,
        LECO, OC, TKR (already nodes) + MIDD, VMI new nodes; the PvP
        Item 201(e) group is the S&P 500 Industrials Index - index-only,
        UNSTORED; no marks)
  HRL   13 -> 17 (DEF 14A 2025-12-17; "The Compensation Peer Group used for
        Fiscal 2025 compensation decisions was comprised of the following
        companies", verbatim 17 (approved July 2024, same as FY2024);
        dropped stored IP + PSA fingerprint fabrications + KO + PEP
        (TSR-group leak - those two belong to the separate 2025-2027 LTIP
        relative-TSR peer group, which is performance-assessment only -
        UNSTORED); added PPC, SJM, POST, FLO, SEB, FDP, THS, HAIN (GIS =
        General Mills survives as a genuine same-sector member); new nodes
        PPC, SEB, FDP, POST, FLO, THS, HAIN; no marks)

New nodes: 7 (PHG, SMNEY - Health Care ADRs, from GEHC; MIDD, VMI -
Industrials, from PNR; PPC, SEB, FDP - Consumer Staples, from HRL) -
registered in PEER_ONLY_NODES and in mark_verified_cross_sector
REPAIR_SCRIPTS BEFORE the repair ran (the batch-5 / batch-8h lessons held).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'PHG': ('Koninklijke Philips N.V.', 'Health Care'),
    'SMNEY': ('Siemens Healthineers AG', 'Health Care'),
    'MIDD': ('The Middleby Corporation', 'Industrials'),
    'VMI': ('Valmont Industries, Inc.', 'Industrials'),
    'PPC': ("Pilgrim's Pride Corporation", 'Consumer Staples'),
    'SEB': ('Seaboard Corporation', 'Consumer Staples'),
    'FDP': ('Fresh Del Monte Produce Inc.', 'Consumer Staples'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'BAX': ('DEF 14A 2026-03-23',
            ['ABT', 'XRAY', 'MDT', 'A', 'EW', 'DGX', 'BDX', 'GEHC',
             'SYK', 'BSX', 'HOLX', 'ZBH', 'DHR', 'ISRG', 'DVA', 'LH']),
    'GEHC': ('DEF 14A 2026-03-19',
             ['ABT', 'DHR', 'PHG', 'A', 'EW', 'SMNEY', 'BAX', 'HOLX',
              'SYK', 'BDX', 'ISRG', 'TMO', 'BSX', 'MDT', 'DGX']),
    'ORLY': ('DEF 14A 2026-03-27',
             ['AAP', 'AN', 'AZO', 'BJ', 'KMX', 'DKS', 'DG', 'DLTR',
              'FAST', 'GPC', 'GWW', 'LKQ', 'LOW', 'ROST', 'SHW',
              'TSCO', 'ULTA']),
    'PNR': ('DEF 14A 2026-03-20',
            ['AYI', 'AOS', 'CR', 'DCI', 'DOV', 'FLS', 'FTV', 'FBIN',
             'GGG', 'IEX', 'IR', 'ITT', 'LII', 'LECO', 'MAS', 'MIDD',
             'NDSN', 'OC', 'ROK', 'SNA', 'TKR', 'VMI', 'XYL']),
    'HRL': ('DEF 14A 2025-12-17',
            ['CPB', 'HSY', 'PPC', 'CAG', 'SJM', 'POST', 'FLO', 'K',
             'SEB', 'FDP', 'KHC', 'THS', 'GIS', 'MKC', 'TSN', 'HAIN',
             'MDLZ']),
}

# TSR-only sources: remove all edges, flip isSource True -> False
# (precedent: AMZN, CLX, CTAS, L, NRG, TSLA, ADM batch-8a)
INDEX_ONLY = {
    'AVY': 'DEF 14A 2026-03-12',
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-03 06:00 PT from peer-network.json (939 nodes / 7,077 edges).
EXPECTED_OLD = {
    'BAX': ['A', 'ABT', 'BIIB', 'BSX', 'CHTR', 'DHR', 'DVA', 'EW',
            'GIS', 'HOLX', 'ISRG', 'MDT', 'SYK', 'ZBH'],
    'GEHC': ['A', 'ABT', 'BAX', 'BSX', 'CHTR', 'COF', 'DGX', 'DHR',
             'EW', 'HOLX', 'ISRG', 'MDT', 'SYK', 'TMO'],
    'ORLY': ['AZO', 'COF', 'DG', 'DLTR', 'ELV', 'FAST', 'GIS', 'GPC',
             'KMX', 'LKQ', 'ROST', 'TSCO', 'ULTA', 'WMB'],
    'PNR': ['AON', 'DOV', 'FTV', 'GIS', 'IEX', 'IR', 'LII', 'MAS',
            'NDSN', 'PFG', 'POOL', 'ROK', 'SNA', 'XYL'],
    'HRL': ['CAG', 'CPB', 'GIS', 'HSY', 'IP', 'K', 'KHC', 'KO',
            'MDLZ', 'MKC', 'PEP', 'PSA', 'TSN'],
}
EXPECTED_OLD_COUNT = {'AVY': 14}


def main():
    bak = SRC.replace('.json', '_backup_20261003_0600_pre_batch8q.json')
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

    # 2. TSR-only sources: drop all edges, flip isSource
    for src, filing in INDEX_ONLY.items():
        assert src in by_ticker, f'{src}: not a node'
        old = [e for e in edges if e['source'] == src]
        assert len(old) == EXPECTED_OLD_COUNT[src], \
            f'{src}: old edge count changed: {len(old)}'
        old_targets = sorted(e['target'] for e in old)
        print(f'{src}: old edge set was {old_targets}')
        assert by_ticker[src].get('isSource') is True, f'{src}: not isSource'
        edges = [e for e in edges if e['source'] != src]
        by_ticker[src]['isSource'] = False
        print(f'{src}: {len(old)} old -> 0 new (TSR-only, {filing})')

    # 3. assert + replace edges for the repaired sources
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
