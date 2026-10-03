#!/usr/bin/env python3
"""Peer-network batch-8p fingerprint-queue repair (2026-10-03 02:00 PDT run).

Follow-up to the batch-8a..8o runs (2026-10-01/02). After 8o, the Section-19
fingerprint queue held 178 cross-sector fingerprint-target edges pending
across 144 sources (62 verified marks); the heaviest remaining tier is 34
sources with exactly 2 queued edges each. Batch-8p takes the 6 heaviest of
those by total outbound edge count (VMC 15 / IEX 15 / KHC 15 / ACGL 14 /
TMUS 14 / TSN 14) and re-extracts each source's comp-decisions peer group
VERBATIM from its latest DEF 14A, keeping only edges that match the
verbatim group. TSR/performance comparator groups, index-only groups,
unnamed survey databases, and explicitly-removed companies are documented
but unstored per the batches 3-8o convention.

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run; CIKs verified against
compensation.json - VMC 0001396009 / IEX 0000832101 / KHC 0001637459 /
ACGL 0000947484 / TMUS 0001283699 / TSN 0000100493), filing HTML fetched
with User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential,
~2s pacing; non-padded CIK in Archive URLs + curl -L per the batch-8d
note; primary document names from each filing's submissions
primaryDocument field). Peer sections transcribed verbatim. Evidence in
goal hidden_files/peer-batch8p-20261003/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8p_filings.json (accession/URL map); filing HTMLs
persisted to the goal dir AT download time (the batch-8h /tmp-peersweep-
wipe lesson).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  VMC   15 -> 24 (DEF 14A 2026-03-24; "Our peer group for 2025 consisted of
        the following 24 companies", verbatim, Materials-heavy; Minerals
        Technologies Inc. explicitly removed for 2025 per revenue/market-
        cap comparability - UNSTORED per the explicit-removal precedent;
        dropped queued COF + CHTR fabrications; added EXP, NEU, ALSN, OC,
        FMC, CBT, FBIN, SUM, CE, TKR, WLK (FBIN = Fortune Brands
        Innovations, filing names the predecessor "Fortune Brands Home &
        Security, Inc."); the PvP Item 201(e) TSR group is this same comp
        group - no separate TSR group to unstore; no marks)
  IEX   15 -> 20 (DEF 14A 2026-03-26; "The following peer group was used to
        evaluate 2025 executive compensation decisions", verbatim;
        2025 review removed Roper Technologies (ROP), added Fortive (FTV)
        - ROP dropped as non-member; dropped queued COF + GIS
        fabrications + WTW non-member; added ITT, LECO, BRKR, CR, DCI,
        FLS, WTS, GGG, WWD (all already nodes); the PvP TSR Peer Group is
        the S&P 400 Midcap Industrials Sector Index - index-only,
        UNSTORED; no marks)
  KHC   15 -> 15 (DEF 14A 2026-04-03; "For 2025, the Compensation Committee
        did not make any changes to the peer groups indicated below" -
        COMPENSATION PEER GROUP verbatim (16 named; Kellanova explicitly
        "removed from the peer group" after the Dec-11-2025 Mars
        acquisition - UNSTORED per the explicit-removal precedent, NOT the
        CTLT delisted-but-table-operative case); dropped queued IP +
        CHTR fabrications; added CPB, MDLZ, SJM (all already nodes); the
        PERFORMANCE PEER GROUP (FMCG/CG subset for PSU relative-TSR) is
        performance-assessment only - UNSTORED; the PvP Item 201(e) group
        is the S&P Consumer Staples Food and Soft Drink Products index -
        UNSTORED; no marks)
  ACGL  14 -> 17 (DEF 14A 2026-03-24; "The Compensation Peer Group approved
        in September 2024 and used for 2025 compensation decisions ...
        comprised of the following 17 companies", verbatim; 2025 review
        added The Allstate Corporation (new 17th member); dropped queued
        IP + GIS fabrications + AWK, AIG, ADP non-members; added AFG, AXS,
        CB, CNA, THG, MKL, ORI, RNR, WRB (all already nodes); the
        20-company PERFORMANCE PEER GROUP for PSU relative-TSR is
        performance-assessment only - UNSTORED; no marks)
  TMUS  14 -> 13 (DEF 14A 2026-04-27; "T-Mobile's peer group of 13
        companies that was used to set executive compensation for 2025"
        (est. Jan-2022, reaffirmed Sept-2024), verbatim; the 2026 variant
        (removed Liberty Global + Lumen, added Amazon + Netflix) is
        documented but NOT stored per the 2026-variant precedent chain
        (NKE batch-8m) - queued for the FY2026 cycle; the old stored
        AMZN/NFLX edges were the 2026 revision leaking into the 2025 set -
        dropped; dropped queued GIS fabrication; MSFT (Microsoft Corp.)
        SURVIVES genuine - filing-verbatim member of the 2025 group
        (TMUS = Communication Services, MSFT home = Information
        Technology) -> verified_cross_sector mark TMUS->MSFT (PYPL->COF /
        UNH->MSFT / FISV->NDAQ / FISV->BLK / SW->GIS batch-8k/8o
        precedent); new nodes LBTYA (Liberty Global Ltd.) and LUMN (Lumen
        Technologies, Inc.) already existed as nodes)
  TSN   14 -> 16 (DEF 14A 2025-12-17; "The companies listed below made up
        the Compensation Peer Group for fiscal year 2025", verbatim (16);
        "In fiscal year 2025, there were no changes"; Kellanova is table-
        operative with NO removal footnote in this Dec-2025 filing ->
        stored verbatim per the delisted-peer (CTLT/FSLR-Avangrid)
        precedent (Mars closed the acquisition Dec-11-2025, 6 days before
        the filing - removal expected in the next filing; FY2026-cycle
        watch item); dropped queued PSA + IP fabrications; added BG,
        PFGC, JBHT, USFD (all already nodes); the PvP Item 201(e) group is
        the S&P 500 Consumer Staples Index - index-only, UNSTORED)

New nodes: 7 (EXP, NEU, ALSN, FMC, CBT, SUM, WLK - all Materials, from
VMC's 2025 peer group) - registered in PEER_ONLY_NODES and in
mark_verified_cross_sector REPAIR_SCRIPTS BEFORE the repair ran (the
batch-5 / batch-8h lessons held).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'EXP': ('Eagle Materials Inc.', 'Materials'),
    'NEU': ('NewMarket Corporation', 'Materials'),
    'ALSN': ('Allison Transmission Holdings, Inc.', 'Industrials'),
    'FMC': ('FMC Corporation', 'Materials'),
    'CBT': ('Cabot Corporation', 'Materials'),
    'SUM': ('Summit Materials, Inc.', 'Materials'),
    'WLK': ('Westlake Chemical Corporation', 'Materials'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'VMC': ('DEF 14A 2026-03-24',
            ['APD', 'EXP', 'NEU', 'ALB', 'EMN', 'NEM', 'ALSN', 'ECL',
             'OC', 'BALL', 'FMC', 'PKG', 'CBT', 'FBIN', 'SUM', 'CE',
             'LII', 'MOS', 'CF', 'MLM', 'TKR', 'DOV', 'MAS', 'WLK']),
    'IEX': ('DEF 14A 2026-03-26',
            ['A', 'ITT', 'AME', 'LECO', 'BRKR', 'MTD', 'CR', 'NDSN',
             'DCI', 'PNR', 'DOV', 'RVTY', 'FLS', 'WAT', 'FTV', 'WTS',
             'GGG', 'WWD', 'IR', 'XYL']),
    'KHC': ('DEF 14A 2026-04-03',
            ['ADM', 'CL', 'KMB', 'PG', 'CPB', 'CAG', 'GIS', 'HRL',
             'KDP', 'MKC', 'MDLZ', 'PEP', 'KO', 'HSY', 'SJM', 'TSN']),
    'ACGL': ('DEF 14A 2026-03-24',
             ['ALL', 'AFG', 'AJG', 'AIZ', 'AXS', 'CB', 'CINF', 'CNA',
              'EG', 'THG', 'HIG', 'MKL', 'ORI', 'RNR', 'TRV', 'WRB',
              'WTW']),
    'TMUS': ('DEF 14A 2026-04-27',
             ['T', 'CHTR', 'CSCO', 'CMCSA', 'INTC', 'IBM', 'LBTYA',
              'LUMN', 'MSFT', 'ORCL', 'QCOM', 'DIS', 'VZ']),
    'TSN': ('DEF 14A 2025-12-17',
            ['ADM', 'KHC', 'BG', 'MDLZ', 'CAT', 'PEP', 'KO', 'PFGC',
             'DE', 'PG', 'JBHT', 'SYY', 'K', 'USFD', 'KMB', 'WMT']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-03 02:00 PT from peer-network.json (932 nodes / 7,058 edges).
EXPECTED_OLD = {
    'VMC': ['EMN', 'MOS', 'COF', 'MLM', 'DOV', 'CF', 'BALL', 'NEM',
            'APD', 'MAS', 'LII', 'ALB', 'ECL', 'CHTR', 'PKG'],
    'IEX': ['RVTY', 'NDSN', 'WAT', 'IR', 'ROP', 'PNR', 'MTD', 'FTV',
            'WTW', 'COF', 'DOV', 'GIS', 'A', 'AME', 'XYL'],
    'KHC': ['IP', 'PG', 'CHTR', 'HRL', 'KDP', 'PEP', 'HSY', 'CL',
            'CAG', 'MKC', 'GIS', 'KMB', 'KO', 'TSN', 'ADM'],
    'ACGL': ['COF', 'EG', 'AJG', 'ALL', 'TRV', 'IP', 'HIG', 'WTW',
             'AWK', 'AIZ', 'GIS', 'ADP', 'CINF', 'AIG'],
    'TMUS': ['CMCSA', 'MSFT', 'IBM', 'AMZN', 'CHTR', 'VZ', 'INTC',
             'T', 'NFLX', 'CSCO', 'ORCL', 'GIS', 'DIS', 'QCOM'],
    'TSN': ['MDLZ', 'PSA', 'WMT', 'PEP', 'IP', 'DE', 'ADM', 'SYY',
            'KO', 'PG', 'KMB', 'K', 'CAT', 'KHC'],
}

# new verified_cross_sector marks (filing-verbatim cross-sector edges
# surviving repair): TMUS->MSFT (Microsoft Corp. is a verbatim member of
# T-Mobile's 2025 Executive Compensation Peer Group; TMUS = Communication
# Services, MSFT home = Information Technology).
NEW_MARKS = [
    {'source': 'TMUS', 'target': 'MSFT',
     'filing': 'DEF 14A 2026-04-27',
     'batch': 'peer-batch8p-20261003'},
]


def main():
    bak = SRC.replace('.json', '_backup_20261003_0200_pre_batch8p.json')
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
    net['metadata']['last_updated'] = '2026-10-03'
    net['metadata']['last_dq_repair'] = '2026-10-03'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
