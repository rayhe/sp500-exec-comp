#!/usr/bin/env python3
"""Peer-network batch-8f fingerprint-queue repair (2026-10-02 run).

Follow-up to the 2026-10-01 batch-8a/8b/8c/8d/8e runs. After 8e, the Section-19
fingerprint queue holds 301 cross-sector fingerprint-target edges across 204
sources; the heaviest remaining tier is the 3 sources with 3 queued edges
each (UNP/WYNN/ALLE). Batch-8f takes those 3 plus the next 3 heaviest by
total outbound edge count among the 2-queue tier (DE/CI/BF-A: 45/36/31
outbound) and re-extracts each source's comp-decisions peer group VERBATIM
from its latest DEF 14A, keeping only edges that match the verbatim group.
TSR/performance comparator groups, index peer groups, S&P 150 general-
industry groups, and 2026-variant groups are documented but unstored per the
batches 3-8e convention (V Block->Uber / HPQ FY2026 / GDDY 2026 / KMB 2026 /
CNP 2026 / IFF 2026 / KDP 2026 / GEV 2026 / DVN Jan-2026 precedents).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run), filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential, 3s pacing;
non-padded CIK in Archive URLs + curl -L per the batch-8d note). Peer
sections transcribed verbatim. Evidence in /tmp/peersweep/batch8f/
<TICKER>_peer.txt (copied to goal hidden_files/peer-batch8f-20261002/) with
batch8f_filings.json (accession/URL map).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  UNP   11 -> 15 (DEF 14A 2026-03-25; 2025 comp-decisions group used for the
        SCT-disclosed pay, 15 cos verbatim; Canadian National stored as CNI,
        Canadian Pacific Kansas City as CP (both NYSE-listed); the May-2025
        2026-variant group (+CAT/+GE Aerospace/+UAL, -NOC/-LUV) documented
        but NOT stored per the 2026-variant precedent; the PvP DJ
        Transportation Index group documented but unstored; queued BLK/GIS/
        PSA + AMCR/CAH fabrications all dropped)
  WYNN  11 -> 15 (DEF 14A 2026-03-25; 2025 Executive Compensation Peer Group,
        unchanged for 2025, 15 cos verbatim; Boyd Gaming stored as BYD (new
        node); queued GIS/IP/PFG fabrications all dropped)
  ALLE   9 -> 22 (DEF 14A 2026-04-17; Compensation Benchmarking Peer Group
        for NEO target total direct compensation, 22 cos verbatim incl. new
        2025 peer Generac (GNRC); Acuity (AYI), A.O. Smith (AOS), Belden
        (BDC), SPX Technologies (SPXC) new nodes; the LTI Performance Peer
        Group (TSR comparator) documented but unstored; queued CHTR/COF/IP
        + FSLR fabrications all dropped)
  DE    45 -> 16 (DEF 14A 2026-01-14; FY2025 compensation peer group, 16 cos
        verbatim; -Emerson (divestitures), +General Electric disclosed; the
        43-company Performance Peer Group (TSR/revenue, S&P 500 Industrials
        subset) documented but unstored; queued GIS/IP + 27 other
        fabrications all dropped - the old 45-edge set was the heaviest
        fabricated set remaining)
  CI    36 -> 24 (DEF 14A 2026-03-13; 2025 compensation peer group, 24 cos
        verbatim (consistent with 2024); WBA (acquired Aug 2025) stored
        verbatim per the delisted-peer precedent; Target (TGT) IS in the
        filing's group - the queued CI->TGT edge is genuine and gets a
        verified_cross_sector mark this batch via the mark-script regen;
        queued GIS dropped; the 2026 compensation peer group (24 cos,
        ACN/AXP/BMY/COF/CRM/IBM/JNJ/MRK/ORCL/PFE new) documented but NOT
        stored per the 2026-variant precedent - the old set had picked up
        the 2026 variant early, exactly the GEV-batch pattern; the S&P 150
        general-industry group and the 2025 TSR Peer Group documented but
        unstored)
  BF-A  31 -> 19 (DEF 14A 2026-06-18; Compensation Comparator Group for
        decisions made in FISCAL 2026, 20 cos - this IS the decisions group
        for the disclosed FY2026 SCT pay, so it is stored (fiscal-year
        proxy, not a next-year variant); Pernod Ricard skipped OTC-only
        per the RHHBY/DANOY/NSRGY precedent (PDRDY); Diageo stored as DEO
        (NYSE ADR); Boston Beer (SAM), Edgewell (EPC), Energizer (ENR),
        Harley-Davidson (HOG), YETI (YETI) new nodes; the custom distilled-
        spirits PBRSU performance group and the S&P Consumer Staples
        benchmarking footnote documented but unstored; queued IP/PSA
        fabrications all dropped)

No ticker-slot collisions: BYD/AYI/AOS/BDC/SPXC/SAM/EPC/ENR/HOG/YETI are all
free; CNI/CP/LUV/DAL/EXC/NEE/MGM/PENN/H/CPRI/VFC/PVH/GNRC/GGG/NVT/OC/WTS/
CSL/KEYS/REZI/LII/FBIN/LFUS/ST/MMM/LOW/CPB/CLX/DEO/HAIN/SJM/POST exist as
peer-only or source nodes with the cited companies holding the slots. The
single surviving filing-verbatim cross-sector fingerprint edge is CI->TGT
(Health Care -> Consumer Staples/Discretionary, Target Corp in Cigna's 2025
comp group), which the mark_verified_cross_sector_20261001.py regen marks
verified this batch; all other 15 queued edges in the six sources were
fabrications and are dropped.
"""
import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'BYD': ('Boyd Gaming Corporation', 'Consumer Discretionary'),
    'AYI': ('Acuity Brands, Inc.', 'Industrials'),
    'AOS': ('A. O. Smith Corporation', 'Industrials'),
    'BDC': ('Belden Inc.', 'Information Technology'),
    'SPXC': ('SPX Technologies, Inc.', 'Industrials'),
    'SAM': ('The Boston Beer Company, Inc.', 'Consumer Staples'),
    'EPC': ('Edgewell Personal Care Company', 'Consumer Staples'),
    'ENR': ('Energizer Holdings, Inc.', 'Consumer Staples'),
    'HOG': ('Harley-Davidson, Inc.', 'Consumer Discretionary'),
    'YETI': ('YETI Holdings, Inc.', 'Consumer Discretionary'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'UNP': ('DEF 14A 2026-03-25',
            ['CNI', 'CP', 'CSX', 'DE', 'DAL', 'EXC', 'FDX', 'HON',
             'NEE', 'NSC', 'NOC', 'RTX', 'SO', 'LUV', 'UPS']),
    'WYNN': ('DEF 14A 2026-03-25',
             ['BYD', 'CZR', 'LVS', 'MGM', 'PENN', 'HLT', 'H',
              'MAR', 'NCLH', 'RCL', 'CPRI', 'PVH', 'RL', 'TPR',
              'VFC']),
    'ALLE': ('DEF 14A 2026-04-17',
             ['AYI', 'GNRC', 'MAS', 'SPXC', 'AOS', 'GGG', 'NVT',
              'TRMB', 'BDC', 'HUBB', 'OC', 'WTS', 'CSL', 'KEYS',
              'REZI', 'ZBRA', 'FTV', 'LII', 'ROK', 'FBIN', 'LFUS',
              'ST']),
    'DE': ('DEF 14A 2026-01-14',
           ['MMM', 'ADM', 'BA', 'CARR', 'CAT', 'CSCO', 'CMI',
            'ETN', 'GE', 'GD', 'HON', 'INTC', 'JCI', 'LMT',
            'PCAR', 'RTX']),
    'CI': ('DEF 14A 2026-03-13',
           ['T', 'FDX', 'SYY', 'CAH', 'HCA', 'TGT', 'COR', 'HUM',
            'TMUS', 'CNC', 'KR', 'UNH', 'C', 'LOW', 'UPS', 'COST',
            'MCK', 'VZ', 'CVS', 'MET', 'WBA', 'ELV', 'PRU',
            'WFC']),
    'BF-A': ('DEF 14A 2026-06-18',
             ['SAM', 'CPB', 'CHD', 'CLX', 'CAG', 'STZ', 'DEO',
              'EPC', 'ENR', 'HAIN', 'HOG', 'HSY', 'SJM', 'KDP',
              'MKC', 'TAP', 'MNST', 'POST', 'YETI']),
}

EXPECTED_OLD = {
    'UNP': ['AMCR', 'BLK', 'CAH', 'DE', 'FDX', 'GIS', 'NOC', 'NSC',
            'PSA', 'RTX', 'SO'],
    'WYNN': ['CZR', 'GIS', 'HLT', 'IP', 'LVS', 'MAR', 'NCLH',
             'PFG', 'RCL', 'RL', 'TPR'],
    'ALLE': ['CHTR', 'COF', 'FSLR', 'FTV', 'HUBB', 'IP', 'MAS',
             'TRMB', 'ZBRA'],
    'DE': ['ADM', 'ALLE', 'AME', 'BA', 'CARR', 'CAT', 'CMI',
           'CSCO', 'CSX', 'DOV', 'EMR', 'ETN', 'FTV', 'GD', 'GE',
           'GIS', 'GNRC', 'HON', 'HWM', 'INTC', 'IP', 'IR', 'ITW',
           'J', 'JCI', 'LMT', 'MAS', 'NDSN', 'NSC', 'ODFL',
           'PCAR', 'PH', 'PNC', 'PNR', 'PWR', 'ROK', 'ROP', 'RTX',
           'SNA', 'SO', 'TDG', 'TT', 'TXT', 'UNP', 'XYL'],
    'CI': ['ACN', 'AXON', 'AXP', 'BMY', 'CAH', 'CNC', 'COR',
           'COST', 'CRM', 'CVS', 'DGX', 'DVA', 'ELV', 'FDX',
           'GIS', 'HCA', 'HSIC', 'HUM', 'IBM', 'KR', 'MCK', 'MET',
           'MOH', 'MRK', 'ORCL', 'PFE', 'SYY', 'T', 'TGT', 'TMUS',
           'UHS', 'UNH', 'UPS', 'VZ', 'WBA', 'WFC'],
    'BF-A': ['ADM', 'BG', 'CAG', 'CHD', 'CL', 'COST', 'DG',
             'DLTR', 'GIS', 'HRL', 'HSY', 'IP', 'KDP', 'KHC',
             'KMB', 'KO', 'KR', 'KVUE', 'MKC', 'MNST', 'MO',
             'PEP', 'PG', 'PM', 'PSA', 'STZ', 'SYY', 'TAP', 'TGT',
             'TSN', 'WMT'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261002_0200_pre_batch8f.json')
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
