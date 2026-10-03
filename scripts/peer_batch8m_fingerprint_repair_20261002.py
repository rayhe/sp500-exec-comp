#!/usr/bin/env python3
"""Peer-network batch-8m fingerprint-queue repair (2026-10-02 18:00 PDT run).

Follow-up to the batch-8a/8b/8c/8d/8e/8f/8g/8h/8i/8j/8k/8l runs
(2026-10-01/02). After 8l, the Section-19 fingerprint queue holds 214
cross-sector fingerprint-target edges pending across ~162 sources (57
verified marks). Batch-8m takes the 6 heaviest remaining 2-queue sources
by total outbound edge count (LHX 17 / NKE 17 / PEP 17 / PLD 17 / PWR 17
/ RVTY 17) and re-extracts each source's comp-decisions peer group
VERBATIM from its latest DEF 14A, keeping only edges that match the
verbatim group. TSR/performance comparator groups, 2026/2027-variant
groups, index-only groups, and unnamed survey databases are documented
but unstored per the batches 3-8l convention (LHX Howmet 2026-planning
add, NKE MSFT FY2027 removal precedents this batch; KDP/8d DANOY/NSRGY
OTC-skip precedent re-applied for PEP).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run; CIKs verified against
compensation.json - LHX 0000202058 / NKE 0000320187 / PEP 0000077476 /
PLD 0001045609 / PWR 0001050915 / RVTY 0000031791), filing HTML fetched
with User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential,
~2-3s pacing; non-padded CIK in Archive URLs + curl -L per the
batch-8d note; primary document names from each filing's submissions
primaryDocument field). Peer sections transcribed verbatim. Evidence in
goal hidden_files/peer-batch8m-20261002/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8m_filings.json (accession/URL map) + sub_<TICKER>
.json + <TICKER>_text.txt; filing HTMLs persisted to the goal dir AT
download time (the batch-8h /tmp-peersweep-wipe lesson).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  LHX   17 -> 14 (DEF 14A 2026-04-01; compensation comparison peer group,
        verbatim table (14 companies); Oct-2024 FW Cook review for 2025
        comp decisions; queued IP/PSA fabrications dropped; HII dropped
        (it came from the TSR performance peer group blend); HWM dropped
        (added only for 2026 planning per the filing - documented, queued
        for the FY2026 cycle); the TSR Performance Peer Group (BAE, HII,
        NOC, Booz Allen, Leidos, SAIC, CACI et al., Feb-2025 approval for
        the 2025-2027 PSU cycle) is performance-assessment only -
        UNSTORED per the TSR precedent; no cross-sector marks)
  NKE   17 -> 17 (DEF 14A 2026-07-15; peer group for setting fiscal 2026
        executive compensation, verbatim (17); dropped ED (queued
        fabrication); added TJX; MSFT + PG SURVIVE - genuine verbatim
        cross-sector edges (NKE = Consumer Discretionary, MSFT home =
        Information Technology, PG home = Consumer Staples), marked
        verified per batch-8h precedent; TGT survives but same-sector
        (TGT home includes Consumer Discretionary) so no mark; Nov-2025
        FY2027 refinement removes Microsoft - documented but NOT stored
        per the 2026-variant precedent chain, queued for the FY2027
        cycle)
  PEP   17 -> 19 (DEF 14A 2026-03-27; "PepsiCo 2025 Compensation Peer
        Group", verbatim (21 named, 19 stored); Danone (DANOY) + Nestle
        (NSRGY) SKIPPED OTC-only per the RHHBY/batch-8d KDP precedent;
        AB InBev stored as BUD, Unilever as UL (NYSE ADRs, existing
        nodes); queued CHTR/GPN/IP fabrications dropped; added MMM, BUD,
        MCD, MDLZ, UL; the same proxy peer group feeds the relative-TSR
        PSU multiplier - no separate TSR group disclosed; no marks
        (PG/GIS home = Consumer Staples = PEP sector))
  PLD   17 -> 20 (DEF 14A 2026-03-19; "Peer Group for 2025", verbatim
        (20 companies: 5 REITs / 8 Financial Services & Asset Management
        / 7 B2B Technology; the filing's own count confirms the 3-column
        extraction); queued AWK dropped; added CG/EVR/JEF/LAZ (filing:
        replaced Ventas with Digital Realty in 2025); BLK + STT SURVIVE
        - genuine verbatim cross-sector edges (PLD = Real Estate, both
        home = Financials), marked verified per batch-8h precedent;
        new nodes EVR (Evercore Inc.), JEF (Jefferies Financial Group),
        LAZ (Lazard, Inc.) - all Financials; CG already a node)
  PWR   17 -> 18 (DEF 14A 2026-04-10; 2025 peer group, verbatim (18
        companies, filing-supplied NYSE/Nasdaq tickers); dropped DOV +
        WAB (replaced per filing: "Dover Corporation, KBR, Inc. and
        Westinghouse Air Brake ... replaced with Builders FirstSource,
        GE Vernova and Illinois Tool Works"); queued IP/TGT fabrications
        dropped; added ACM/EME/FLR/LHX/MTZ; new nodes EME (EMCOR Group,
        Inc., Industrials) and MTZ (MasTec, Inc., Industrials) - ACM/FLR
        already nodes; the Item 201(e) Reg S-K TSR peer group (AECOM,
        Dycom, EMCOR, Fluor, Jacobs, KBR, MasTec, MYR, Primoris) is
        pay-vs-performance only - UNSTORED per TSR precedent; no marks
        (all 18 Industrials))
  RVTY  15 -> 15 (DEF 14A 2026-03-16; "2025 Peer Group", verbatim (15);
        queued BAC/BLK/GIS/GS/WFC fabrications dropped; old CRL/DGX/IQV/
        MTD/ROP/TDY dropped; added AVTR/BIO/BRKR/COO/EXAS/ILMN/QDEL/QGEN;
        CTLT stored verbatim per the delisted-peer precedent (Catalent
        acquired; the filing's "14 ... remained public reporting
        companies" note confirms the 15-count including CTLT - table-
        operative, same class as BECN/DFS/K); new nodes QGEN (QIAGEN N.V.,
        Health Care, NYSE-listed) and QDEL (QuidelOrtho Corporation,
        Health Care, Nasdaq-listed); relative TSR is a modifier vs an
        industry index - index-only, UNSTORED per the index-only
        precedent; no marks (all Health Care))

Four new verified_cross_sector marks this batch (filing-verbatim,
surviving the repair): NKE->MSFT, NKE->PG, PLD->BLK, PLD->STT.

New nodes: 7 (EVR, JEF, LAZ, EME, MTZ, QGEN, QDEL) - registered in
PEER_ONLY_NODES and in mark_verified_cross_sector REPAIR_SCRIPTS BEFORE
the repair ran (the batch-5 / batch-8h lessons held).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'EVR': ('Evercore Inc.', 'Financials'),
    'JEF': ('Jefferies Financial Group Inc.', 'Financials'),
    'LAZ': ('Lazard, Inc.', 'Financials'),
    'EME': ('EMCOR Group, Inc.', 'Industrials'),
    'MTZ': ('MasTec, Inc.', 'Industrials'),
    'QGEN': ('QIAGEN N.V.', 'Health Care'),
    'QDEL': ('QuidelOrtho Corporation', 'Health Care'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'LHX': ('DEF 14A 2026-04-01',
            ['ETN', 'J', 'PH', 'EMR', 'LDOS', 'RTX', 'GD', 'LMT',
             'ROK', 'HON', 'MSI', 'TXT', 'ITW', 'NOC']),
    'NKE': ('DEF 14A 2026-07-15',
            ['BBY', 'MSFT', 'SBUX', 'CSCO', 'MDLZ', 'TGT', 'KO',
             'NFLX', 'TJX', 'KMB', 'PEP', 'WMT', 'LOW', 'PG', 'DIS',
             'MCD', 'CRM']),
    'PEP': ('DEF 14A 2026-03-27',
            ['MMM', 'BUD', 'KO', 'CL', 'FDX', 'GIS', 'JNJ', 'KHC',
             'MCD', 'MDLZ', 'NKE', 'PFE', 'PG', 'SBUX', 'UL', 'UPS',
             'VZ', 'WMT', 'DIS']),
    'PLD': ('DEF 14A 2026-03-19',
            ['AMT', 'CCI', 'DLR', 'EQIX', 'WELL', 'BLK', 'CG', 'EVR',
             'JEF', 'LAZ', 'NTRS', 'SPGI', 'STT', 'ADBE', 'ADP',
             'GPN', 'INTU', 'PAYX', 'NOW', 'WDAY']),
    'PWR': ('DEF 14A 2026-04-10',
            ['ACM', 'EME', 'J', 'PCAR', 'BLDR', 'EMR', 'JCI', 'PH',
             'GLW', 'FLR', 'LDOS', 'TXT', 'CMI', 'GEV', 'LHX',
             'ETN', 'ITW', 'MTZ']),
    'RVTY': ('DEF 14A 2026-03-16',
             ['A', 'BRKR', 'HOLX', 'COO', 'AVTR', 'CTLT', 'ILMN',
              'TMO', 'BIO', 'DHR', 'QGEN', 'WAT', 'TECH', 'EXAS',
              'QDEL']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-02 18:05 PT from peer-network.json (916 nodes / 7,045 edges).
EXPECTED_OLD = {
    'LHX': ['EMR', 'ETN', 'GD', 'HII', 'HON', 'HWM', 'IP', 'ITW', 'J',
            'LDOS', 'LMT', 'MSI', 'NOC', 'PSA', 'ROK', 'RTX', 'TXT'],
    'NKE': ['BBY', 'CRM', 'CSCO', 'DIS', 'ED', 'KMB', 'KO', 'LOW',
            'MCD', 'MDLZ', 'MSFT', 'NFLX', 'PEP', 'PG', 'SBUX', 'TGT',
            'WMT'],
    'PEP': ['CHTR', 'CL', 'DIS', 'FDX', 'GIS', 'GPN', 'IP', 'JNJ',
            'KHC', 'KO', 'NKE', 'PFE', 'PG', 'SBUX', 'UPS', 'VZ',
            'WMT'],
    'PLD': ['ADBE', 'ADP', 'AMT', 'AWK', 'BLK', 'CCI', 'DLR', 'EQIX',
            'GPN', 'INTU', 'NOW', 'NTRS', 'PAYX', 'SPGI', 'STT',
            'WDAY', 'WELL'],
    'PWR': ['BLDR', 'CMI', 'DOV', 'EMR', 'ETN', 'GEV', 'GLW', 'IP',
            'ITW', 'J', 'JCI', 'LDOS', 'PCAR', 'PH', 'TGT', 'TXT',
            'WAB'],
    'RVTY': ['A', 'BAC', 'BLK', 'CRL', 'DGX', 'DHR', 'GIS', 'GS',
             'HOLX', 'IQV', 'MTD', 'ROP', 'TDY', 'TECH', 'TMO', 'WAT',
             'WFC'],
}

# new verified_cross_sector marks (filing-verbatim surviving edges only)
NEW_MARKS = [
    {'source': 'NKE', 'target': 'MSFT', 'filing': 'DEF 14A 2026-07-15',
     'batch': 'peer-batch8m-20261002'},
    {'source': 'NKE', 'target': 'PG', 'filing': 'DEF 14A 2026-07-15',
     'batch': 'peer-batch8m-20261002'},
    {'source': 'PLD', 'target': 'BLK', 'filing': 'DEF 14A 2026-03-19',
     'batch': 'peer-batch8m-20261002'},
    {'source': 'PLD', 'target': 'STT', 'filing': 'DEF 14A 2026-03-19',
     'batch': 'peer-batch8m-20261002'},
]


def main():
    bak = SRC.replace('.json', '_backup_20261002_1800_pre_batch8m.json')
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
