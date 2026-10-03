#!/usr/bin/env python3
"""Peer-network batch-8s acquisition-triage orphan extraction repair (2026-10-03 11:30 PDT run).

Follow-up to batch-8r (2026-10-03 10:00), which extracted the 6 heaviest tracked
orphans and queued this run: the acquisition-triage cohort of the 25 remaining
tracked S&P 500 companies with out_degree 0 (25 pending after batch-8r:
T 13 / K 12 / WBA 12 / CAH 10 / ANSS 8 / JNPR 8 / XOM 7 / CTRA 6 / DELL 6 /
HES 6 / APH 5 / ...).

Deal-status verification (this run, web search):
  K    - Mars acquisition closed Dec 11, 2025 (taken private)
  WBA  - Sycamore Partners take-private closed Aug 28, 2025 (delisted)
  JNPR - HPE acquisition closed Jul 2, 2025 (delisted)
  ANSS - Synopsys acquisition closed Jul 17, 2025 (delisted)
  HES  - Chevron acquisition closed Jul 18, 2025 (delisted)
  CTRA - still publicly traded

Convention: for taken-private sources, store the LAST AUTHORITATIVE comp peer
group pre-go-private (HOLX batch-8r precedent: 15-12G on file, no later DEF
14A); for CTRA, the latest DEF 14A. Performance-only comparator groups, TSR
index groups, unnamed survey databases, and explicitly-removed prior-group
companies are documented but unstored per the batches 3-8r convention.

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (CIKs verified against the
submissions name field; WBA CIK is 0001618921, not 0001612862), filing HTML
fetched with User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential,
~2-3s pacing; non-padded CIK in Archive URLs; primaryDocument from each
filing's submissions primaryDocument field). Peer sections transcribed
verbatim. Evidence in goal hidden_files/peer-batch8s-20261003/ <TICKER>_peer.txt
(verbatim transcriptions) + batch8s_filings.json (accession/URL/status map);
filing HTMLs persisted to the goal dir AT download time (the batch-8h
/tmp-peersweep-wipe lesson).

Repairs (6 sources):

  K     0 -> 17 (DEF 14A 2024-03-04; 2024 Compensation Peer Group verbatim -
        17 Consumer Staples cos; no 2025 proxy was filed (merger-pending), so
        this is the last authoritative group pre-go-private. 2024 Performance
        Peer Group = food-company subset, performance-only -> UNSTORED.
        GIS/HSY are fingerprint targets but same home sector -> no marks.)
  WBA   0 -> 20 (DEF 14A 2024-12-13; fiscal 2024 peer group verbatim (same as
        fiscal 2023); S&P 500 Health Care Index TSR group is index-only ->
        UNSTORED. No cross-sector marks: WBA home Consumer Staples lies inside
        TGT's fingerprint home set ({Consumer Staples, Consumer
        Discretionary}) per the Section-19 queued_edges convention, so WBA ->
        TGT is not queued; no other fingerprint targets in the group.)
  JNPR  0 -> 19 (DEF 14A 2025-04-16; FY24 Peer Group verbatim (19, with the
        filing's own add/remove note: Citrix + Xilinx removed; Cadence,
        Marvell, Pure Storage, Qorvo added). Filing "NCR Corporation" maps to
        network node VYX (same company, network canonical ticker). VMWare was
        acquired by Broadcom Nov 2023 but is NAMED in the FY24 group -> stored
        verbatim (new peer-only node VMW). No marks.)
  ANSS  0 -> 15 (DEF 14A 2025-04-29; 2024 Peer Group verbatim (15); Splunk and
        VMware REMOVED from the 2023 group per Compensia -> documented,
        unstored (no edges existed). 7-company TSR industry peer group (PvP)
        performance-only -> UNSTORED. No marks.)
  HES   0 -> 8  (DEF 14A 2025-04-04; 2024 Peer Group verbatim (8); Pioneer
        Natural Resources + Marathon Oil removed after 2024 acquisitions ->
        documented, unstored (no edges existed). The PVP "Proxy Peer Group" is
        the same list (performance context only, no separate storage). New
        peer-only node MUR (Murphy Oil). No marks.)
  CTRA  0 -> 10 (DEF 14A 2025-03-20; peer group for 2024 comp decisions verbatim
        (10); filing's CD&A comp-decisions table names Marathon Oil while the
        PVP footnote's as-of-2025-03-06 version names Hess -> comp-decisions
        version stored verbatim per convention, nuance documented in
        CTRA_peer.txt. MRO was acquired by ConocoPhillips Nov 2024 but is
        NAMED -> stored verbatim. Performance TSR comparators (SPDR S&P Oil &
        Gas E&P ETF + S&P 500 Industrials indices) index-only -> UNSTORED. New
        peer-only node AR (Antero Resources). No marks.)

New nodes: 3 (VMW - VMware, Inc., IT; MUR - Murphy Oil Corp, Energy; AR -
Antero Resources Corp, Energy) - registered in PEER_ONLY_NODES and in
mark_verified_cross_sector REPAIR_SCRIPTS BEFORE the repair ran (the batch-5 /
batch-8h lessons held).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'AR': ('Antero Resources Corporation', 'Energy'),
    'MUR': ('Murphy Oil Corporation', 'Energy'),
    'VMW': ('VMware, Inc.', 'Information Technology'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'K': ('DEF 14A 2024-03-04',
          ['CHD', 'CLX', 'CL', 'HRL', 'KVUE', 'KDP', 'KMB', 'MNST',
           'CPB', 'CAG', 'GIS', 'HSY', 'SJM', 'KHC', 'MKC', 'MDLZ',
           'PEP']),
    'WBA': ('DEF 14A 2024-12-13',
            ['ABT', 'CAH', 'CI', 'KO', 'COST', 'CVS', 'ELV', 'HUM',
             'JNJ', 'KR', 'MCD', 'MCK', 'MDT', 'MDLZ', 'PEP', 'PFE',
             'PG', 'TGT', 'UNH', 'WMT']),
    'JNPR': ('DEF 14A 2025-04-16',
             ['AKAM', 'ADI', 'ANET', 'CDNS', 'CIEN', 'COMM', 'FFIV',
              'FTNT', 'GEN', 'KEYS', 'MRVL', 'MSI', 'VYX', 'NTAP',
              'PANW', 'PSTG', 'QRVO', 'TRMB', 'VMW']),
    'ANSS': ('DEF 14A 2025-04-29',
             ['AKAM', 'ADSK', 'CDNS', 'DDOG', 'DOCU', 'HUBS', 'PAYC',
              'PTC', 'SNPS', 'TTD', 'TWLO', 'TYL', 'VEEV', 'VRSN',
              'WDAY']),
    'HES': ('DEF 14A 2025-04-04',
            ['APA', 'DVN', 'EOG', 'EQT', 'MUR', 'OXY', 'COP', 'CTRA']),
    'CTRA': ('DEF 14A 2025-03-20',
             ['AR', 'APA', 'EXE', 'MRO', 'DVN', 'FANG', 'EOG', 'EQT',
              'OXY', 'OVV']),
}

# never-extracted sources: expected old edge set is EMPTY (assertion guard)
EXPECTED_OLD = {src: [] for src in NEW}


def main():
    bak = SRC.replace('.json', '_backup_20261003_1130_pre_batch8s.json')
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

    # 2. assert (empty) old edge sets + add verbatim edges for the sources
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
