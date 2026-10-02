#!/usr/bin/env python3
"""Peer-network batch-8e fingerprint-queue repair (2026-10-01 run).

Follow-up to the 2026-10-01 batch-8a/8b/8c/8d runs. After 8d, the Section-19
fingerprint queue holds 319 cross-sector fingerprint-target edges across 210
sources; the heaviest remaining tier is 9 sources with exactly 3 queued edges
each. Batch-8e takes the next 6 heaviest by total outbound edge count
(LVS/DVN/FANG/FFIV/GEV/TRGP) and re-extracts each source's comp-decisions
peer group VERBATIM from its latest DEF 14A, keeping only edges that match
the verbatim group. TSR/PSU comparator groups, index peer groups (XOP, DJ
U.S. Gambling), and 2026-variant groups are documented but unstored per the
batches 3-8d convention (V Block->Uber / HPQ FY2026 / GDDY 2026 / KMB 2026 /
CNP 2026 / IFF 2026 / KDP 2026 / GEV 2026 / DVN Jan-2026 precedents).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run), filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential, 3s pacing;
non-padded CIK in Archive URLs + curl -L per the batch-8d note). Peer
sections transcribed verbatim. Evidence in /tmp/peersweep/batch8e/
<TICKER>_peer.txt (copied to goal hidden_files/peer-batch8e-20261001/) with
batch8e_filings.json (accession/URL map).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  LVS  16 -> 15 (DEF 14A 2026-04-01; 2025 peer group unchanged from the 2025
        proxy, 15 cos verbatim; Yum China Holdings stored as YUMC (NYSE,
        new node) per the QSR NYSE-precedent; the PvP DJ U.S. Gambling Index
        group documented but unstored; queued GIS/IP/PFG all dropped)
  DVN   15 -> 9 (DEF 14A 2026-05-28; 2025 comp-decisions group = the "For
        Decisions Made January 2025" column of the CD&A peer table, 9 cos;
        Hess (HES, acquired by Chevron Jul 2025) and Marathon Oil (MRO,
        acquired by ConocoPhillips Nov 2024) stored verbatim per the
        delisted-peer precedent (Kellanova/Catalent; MRO new node, HES node
        already existed); EQT/Expand Energy/Permian Resources were added
        Sept 2025 for JAN-2026 decisions - documented, NOT stored per the
        2026-variant precedent; the announced Devon/Coterra merger (8-K
        2026-02-01) discloses no peer change; the PvP XOP-ETF group
        documented but unstored; queued CHTR/COF/GIS + CVX/MPC/PSX
        fabrications all dropped)
  FANG  15 -> 13 (DEF 14A 2026-04-09; 2025 Benchmarking Compensation Peer
        Group, 13 cos verbatim; Cheniere stored as LNG (NYSE, new node);
        the TSR performance peer group (S&P 500 + XOP index, weighted 2x)
        documented but unstored; queued COF/GIS/TGT + AWK/HES/MPC
        fabrications all dropped)
  FFIV  15 -> 21 (DEF 14A 2026-01-26; FY2025 peer group, 21 cos verbatim;
        Check Point stored as CHKP (Nasdaq, new node); Informatica (INFA),
        Pure Storage (PSTG), Teradata (TDC) new nodes; the filing's stated
        removals (Arista/ANET, AutoDesk/ADSK, Cadence/CDNS, Juniper/JNPR,
        Palo Alto/PANW, Splunk, Synopsys, VMware, Workday) explain the old
        set's ADSK/ANET/CDNS/JNPR/PANW; queued CHTR/NDAQ/PSA all dropped)
  GEV   15 -> 11 (DEF 14A 2026-04-03; 2025 Peer Group approved by the CHCC
        in 2024, 15 cos listed; ABB (ABBNY), Schneider Electric (SBGSY),
        Siemens Energy (SMEGF), Vestas (VWDRY) skipped OTC-only per the
        RHHBY/DANOY/NSRGY precedent; the 2026 variant (-Halliburton,
        -Honeywell, -Vestas; +RTX, +IBM, +Cisco, +NextEra) documented but
        NOT stored per the 2026-variant precedent - the old set's RTX/IBM
        were the extractor picking up the 2026 variant early; SLB
        (Schlumberger Limited, the filing's name) re-added - the extractor
        had dropped it; queued CHTR/COF/TGT all dropped)
  TRGP  13 -> 15 (DEF 14A 2026-03-26; 2025 compensation peer group, "a mix
        of 15 midstream and E&P companies", 15 cos verbatim; Energy
        Transfer stored as ET, Enterprise Products as EPD, Plains All
        American as PAA (Nasdaq) - all new nodes; Cheniere as LNG; 2025
        changes disclosed: removed Equitrans/EnLink/Marathon Oil/NuStar
        (acquisitions), added DT Midstream/Kinetik/Western Midstream; the
        LTIP TSR comparator group documented but unstored; queued BLK/COF/
        STT + AWK/MPC/WDC fabrications all dropped)

No ticker-slot collisions: YUMC/MRO/LNG/CHKP/INFA/PSTG/TDC/ET/EPD/PAA are all
free; HES/LNG-slot peers exist as peer-only or source nodes with the cited
companies holding the slots. No filing-verbatim cross-sector fingerprint
edges survive in any of the six repairs (all six groups are single-sector),
so no new verified_cross_sector marks are required this batch.
"""
import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'YUMC': ('Yum China Holdings, Inc.', 'Consumer Discretionary'),
    'MRO': ('Marathon Oil Corporation', 'Energy'),
    'LNG': ('Cheniere Energy, Inc.', 'Energy'),
    'CHKP': ('Check Point Software Technologies Ltd.', 'Information Technology'),
    'INFA': ('Informatica Inc.', 'Information Technology'),
    'PSTG': ('Pure Storage, Inc.', 'Information Technology'),
    'TDC': ('Teradata Corporation', 'Information Technology'),
    'ET': ('Energy Transfer LP', 'Energy'),
    'EPD': ('Enterprise Products Partners L.P.', 'Energy'),
    'PAA': ('Plains All American Pipeline, L.P.', 'Energy'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'LVS': ('DEF 14A 2026-04-01',
            ['MGM', 'VICI', 'CZR', 'SBUX', 'WYNN', 'MCD', 'MAR',
             'YUMC', 'HLT', 'BKNG', 'CCL', 'EXPE', 'RCL', 'LYV',
             'SPG']),
    'DVN': ('DEF 14A 2026-05-28',
            ['APA', 'COP', 'CTRA', 'FANG', 'EOG', 'HES', 'MRO',
             'OXY', 'OVV']),
    'FANG': ('DEF 14A 2026-04-09',
             ['APA', 'EXE', 'LNG', 'OXY', 'COP', 'OVV', 'CTRA',
              'PSX', 'DVN', 'SLB', 'EOG', 'WMB', 'EQT']),
    'FFIV': ('DEF 14A 2026-01-26',
             ['AKAM', 'CHKP', 'CIEN', 'NET', 'DDOG', 'DOCU', 'DBX',
              'DT', 'FTNT', 'GEN', 'INFA', 'NTAP', 'NTNX', 'OKTA',
              'PSTG', 'TDC', 'TRMB', 'TWLO', 'U', 'VRSN', 'ZS']),
    'GEV': ('DEF 14A 2026-04-03',
            ['BKR', 'CAT', 'CMI', 'DE', 'ETN', 'EMR', 'HAL',
             'HON', 'PH', 'PWR', 'SLB']),
    'TRGP': ('DEF 14A 2026-03-26',
             ['APA', 'ET', 'OKE', 'LNG', 'EPD', 'OVV', 'DVN',
              'EQT', 'PAA', 'FANG', 'KMI', 'WMB', 'DTM', 'KNTK',
              'WES']),
}

EXPECTED_OLD = {
    'LVS': ['BKNG', 'CCL', 'CZR', 'EXPE', 'GIS', 'HLT', 'IP', 'LYV',
            'MAR', 'MCD', 'PFG', 'RCL', 'SBUX', 'SPG', 'VICI',
            'WYNN'],
    'DVN': ['APA', 'CHTR', 'COF', 'COP', 'CTRA', 'CVX', 'EOG', 'EQT',
            'EXE', 'FANG', 'GIS', 'HES', 'MPC', 'OXY', 'PSX'],
    'FANG': ['APA', 'AWK', 'COF', 'COP', 'CTRA', 'DVN', 'EOG', 'EQT',
             'EXE', 'GIS', 'HES', 'MPC', 'OXY', 'TGT', 'WMB'],
    'FFIV': ['ADSK', 'AKAM', 'ANET', 'CDNS', 'CHTR', 'DDOG', 'FTNT',
             'GEN', 'JNPR', 'NDAQ', 'NTAP', 'PANW', 'PSA', 'TRMB',
             'VRSN'],
    'GEV': ['BKR', 'CAT', 'CHTR', 'CMI', 'COF', 'DE', 'EMR', 'ETN',
            'HAL', 'HON', 'IBM', 'PH', 'PWR', 'RTX', 'TGT'],
    'TRGP': ['APA', 'AWK', 'BLK', 'COF', 'DVN', 'EQT', 'FANG', 'KMI',
             'MPC', 'OKE', 'STT', 'WDC', 'WMB'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261001_2200_pre_batch8e.json')
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
    net['metadata']['last_updated'] = '2026-10-01'
    net['metadata']['last_dq_repair'] = '2026-10-01'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
