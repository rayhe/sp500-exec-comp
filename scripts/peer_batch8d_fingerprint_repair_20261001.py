#!/usr/bin/env python3
"""Peer-network batch-8d fingerprint-queue repair (2026-10-01 run).

Follow-up to the 2026-10-01 batch-8a/8b/8c runs. After 8c, the Section-19
fingerprint queue holds 337 cross-sector fingerprint-target edges across
~215 sources; the heaviest remaining tier is 15 sources with exactly 3
queued edges each. Batch-8d takes the next 6 heaviest by total outbound
edge count (KDP/CNP/YUM/TDG/MAS/IFF) and re-extracts each source's
comp-decisions peer group VERBATIM from its latest DEF 14A, keeping only
edges that match the verbatim group. TSR/PSU comparator groups and
2026-variant groups are documented but unstored per the batches 3-8c
convention (V Block->Uber / HPQ FY2026 / GDDY 2026 / KMB 2026 / CNP 2026 /
IFF 2026 / KDP 2026 precedents).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run), filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential, 3s pacing;
note: zero-padded CIK Archive URLs 301-redirect to the non-padded form,
so curl needs -L - the 0-byte downloads earlier this run were the missing
-L, not SEC gating). Peer sections transcribed verbatim. Evidence in
/tmp/peersweep/batch8d/<TICKER>_peer.txt (copied to goal
hidden_files/peer-batch8d-20261001/) with batch8d_filings.json
(accession/URL map).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  KDP  19 -> 16 (DEF 14A 2026-04-24; 2025 Compensation Peer Group, 18 cos;
        Kellanova (K) stored verbatim per delisted-peer precedent (the 2025
        group the filing discloses; the Dec-2025 Mars acquisition removal
        applies to the current/2026 group - documented, queued for the
        FY2026 cycle); Danone (DANOY) and Nestle (NSRGY) skipped OTC-only
        per the RHHBY precedent; Diageo stored as DEO (NYSE ADR, new node,
        same class as BUD/UL); queued FRT/IP/PSA all dropped)
  CNP  19 -> 18 (DEF 14A 2026-03-04; 2025 peer group, 18 utilities verbatim;
        Avangrid removal / OGE addition already reflected; the 2026 variant
        (-Alliant LNT, -OGE, +Dominion D, +FirstEnergy FE) documented but
        NOT stored per the V precedent - queued for the FY2026 cycle; the
        old set's D/FE were the extractor picking up the disclosed 2026
        variant, correctly dropped this run; queued COF/IP/TGT dropped)
  YUM  18 -> 19 (DEF 14A 2026-04-03; 2025 Executive Peer Group, 19 cos,
        Nov-2024 revision for 2025 pay decisions; GENUINE KEEP: GIS
        (Consumer Staples, batch-6 FE/KMB/KR class); K stored verbatim
        per delisted-peer precedent; QSR is NYSE-listed, stored per the
        GIB/STN convention; queued BLK/IP dropped)
  TDG  17 -> 20 (DEF 14A 2026-01-23; the 2024 Peer Group, continued for
        FY2025 per the CD&A ("We continue to use the peer group adopted
        in 2024"); 20 cos verbatim; "Northrup Grumman" is the filing's own
        spelling, mapped to NOC; queued BLK/GIS/PSA all dropped)
  MAS  16 -> 17 (DEF 14A 2026-04-10; current peer group, 17 cos verbatim;
        "Newell Rubbermaid Inc." is the filing's stale name for Newell
        Brands, ticker NWL; queued IP/PFG/PSA all dropped)
  IFF  16 -> 21 (DEF 14A 2026-03-18; 2025 peer group used for 2025 comp
        decisions, 21 cos verbatim; GENUINE KEEPS: GIS and HSY (both
        Consumer Staples home sector, batch-6 class); Catalent (CTLT,
        delisted Dec 2024) stored verbatim per delisted-peer precedent;
        the 2026 variant (-Corteva, -Catalent, -Zoetis, +Agilent A,
        +Biogen BIIB) documented but NOT stored - queued for the FY2026
        cycle; queued COF dropped)

No ticker-slot collisions: DEO (Diageo NYSE ADR), RBC (RBC Bearings NYSE),
RPM (RPM International NYSE), LEG (Leggett & Platt NYSE), BHC (Bausch
Health NYSE) are all live-held by the cited companies; CTLT has no live
holder (Catalent delisted Dec 2024) so the slot is free for the
filing-verbatim mapping.
"""
import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'DEO': ('Diageo plc', 'Consumer Staples'),
    'RBC': ('RBC Bearings Incorporated', 'Industrials'),
    'RPM': ('RPM International Inc.', 'Materials'),
    'LEG': ('Leggett & Platt, Incorporated', 'Consumer Discretionary'),
    'BHC': ('Bausch Health Companies Inc.', 'Health Care'),
    'CTLT': ('Catalent, Inc.', 'Health Care'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'KDP': ('DEF 14A 2026-04-24',
            ['BUD', 'K', 'BF-A', 'KHC', 'CPB', 'MKC', 'KO', 'TAP',
             'STZ', 'MDLZ', 'MNST', 'DEO', 'HSY', 'PEP', 'SJM',
             'SBUX']),
    'CNP': ('DEF 14A 2026-03-04',
            ['LNT', 'EVRG', 'AEE', 'ES', 'AEP', 'NI', 'ATO', 'OGE',
             'CMS', 'PPL', 'ED', 'PEG', 'DTE', 'SRE', 'EIX', 'WEC',
             'ETR', 'XEL']),
    'YUM': ('DEF 14A 2026-04-03',
            ['CMG', 'EL', 'KHC', 'RL', 'KO', 'GIS', 'LULU', 'QSR',
             'CL', 'HLT', 'MAR', 'SBUX', 'DRI', 'K', 'MCD', 'VFC',
             'DPZ', 'KMB', 'MDLZ']),
    'TDG': ('DEF 14A 2026-01-23',
            ['AME', 'APTV', 'DOV', 'ETN', 'EMR', 'FTV', 'GD', 'HEI',
             'HWM', 'ITW', 'IR', 'LHX', 'MSI', 'NOC', 'PH', 'RBC',
             'ROK', 'ROP', 'TDY', 'TXT']),
    'MAS': ('DEF 14A 2026-04-10',
            ['DOV', 'PPG', 'FTV', 'RPM', 'FBIN', 'SNA', 'ITW', 'SWK',
             'LEG', 'SHW', 'MHK', 'TT', 'NWL', 'WHR', 'OC', 'XYL',
             'PNR']),
    'IFF': ('DEF 14A 2026-03-18',
            ['ADM', 'BALL', 'BHC', 'CTLT', 'CE', 'CHD', 'CLX', 'CL',
             'STZ', 'CTVA', 'EMN', 'ECL', 'EL', 'GIS', 'HSY', 'INGR',
             'KDP', 'KMB', 'MKC', 'VTRS', 'ZTS']),
}

EXPECTED_OLD = {
    'KDP': ['BF-A', 'FRT', 'GIS', 'GPN', 'HSY', 'IP', 'JCI', 'JNJ',
            'K', 'KHC', 'KO', 'MKC', 'MNST', 'PEP', 'PG', 'PSA',
            'SBUX', 'STZ', 'TAP'],
    'CNP': ['AEE', 'ATO', 'AWK', 'CMS', 'COF', 'D', 'DTE', 'ED',
            'ETR', 'EVRG', 'FE', 'IP', 'LNT', 'NI', 'PEG', 'PPL',
            'TGT', 'WEC', 'XEL'],
    'YUM': ['BLK', 'CL', 'CMG', 'DPZ', 'DRI', 'EL', 'GIS', 'HLT',
            'IP', 'JPM', 'KHC', 'KMB', 'KO', 'MAR', 'MCD', 'MDLZ',
            'RL', 'SBUX'],
    'TDG': ['AME', 'APTV', 'BLK', 'DOV', 'EMR', 'ETN', 'FTV', 'GIS',
            'HWM', 'IR', 'MSI', 'PH', 'PSA', 'ROK', 'ROP', 'TDY',
            'TXT'],
    'MAS': ['CRL', 'DOV', 'FTV', 'IP', 'ITW', 'MHK', 'PFG', 'PNR',
            'POOL', 'PPG', 'PSA', 'SHW', 'SNA', 'SWK', 'TT', 'XYL'],
    'IFF': ['A', 'AWK', 'BALL', 'CHD', 'CL', 'COF', 'CTVA', 'ECL',
            'GIS', 'HSY', 'IP', 'KDP', 'KMB', 'MKC', 'STZ', 'VTRS'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261001_1900_pre_batch8d.json')
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
