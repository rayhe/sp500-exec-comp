#!/usr/bin/env python3
"""Peer-network batch-8i fingerprint-queue repair (2026-10-02 run).

Follow-up to the batch-8a/8b/8c/8d/8e/8f/8g/8h runs (2026-10-01/02). After 8h,
the Section-19 fingerprint queue holds 262 cross-sector fingerprint-target
edges across ~186 sources; the 3-edge tier is fully drained and the 2-edge
tier is nearly drained. Batch-8i takes the 6 heaviest remaining 2-queue
sources by total outbound edge count (AMT 22 / JNJ 22 / TEL 22 / WEC 22 /
LMT 21 / SWK 21) and re-extracts each source's comp-decisions peer group
VERBATIM from its latest DEF 14A, keeping only edges that match the verbatim
group. TSR/performance comparator groups, 2026-variant groups, and unnamed
survey databases are documented but unstored per the batches 3-8h convention
(V Block->Uber / HPQ FY2026 / GDDY 2026 / KMB 2026 / CNP 2026 / IFF 2026 /
KDP 2026 / GEV 2026 / DVN Jan-2026 / CRL 2026 / ADM index-only /
CTAS+ETN TSR-only precedents).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run; tickers/CIKs verified against
SEC company_tickers.json - TEL is CIK 1385157), filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential, ~2s pacing;
non-padded CIK in Archive URLs + curl -L per the batch-8d note; the primary
document name comes from each filing's index.json, NOT the accession
filename). Peer sections transcribed verbatim. Evidence in goal
hidden_files/peer-batch8i-20261002/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8i_filings.json (accession/URL map); filing HTML
backups copied to the goal dir immediately after download (the batch-8h
/tmp-peersweep-wipe lesson).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  AMT   22 -> 22 (DEF 14A 2026-04-08; "Peer Group for 2025 Compensation
        Decisions", 22 cos verbatim (BXP stored verbatim per filing "(fka
        Boston Properties, Inc.)"); NVIDIA explicitly REMOVED by the filing
        for 2025; queued AWK/COF/TGT fabrications dropped; added
        BXP/EQR/LHX/PSA)
  JNJ   22 -> 17 (DEF 14A 2026-03-11; 2025 EXECUTIVE peer group, verbatim
        with filing tickers, "No changes to the group were made for 2026";
        MSFT and PG SURVIVE - genuine verbatim cross-sector edges (JNJ
        Health Care -> MSFT IT / PG Staples), marked verified per batch-8h
        precedent; GE explicitly REMOVED for 2025 per the filing ("3M Company
        and General Electric Company were removed from the group for 2025");
        queued BSX/CL/ISRG/JCI/SYK/ZBH fabrications dropped; added ABT/IBM;
        Competitor Composite Peer Group (relative-performance / PSU
        relative-TSR group) documented unstored per TSR precedent)
  TEL   22 -> 21 (DEF 14A 2026-01-15; fiscal-2025 Industry Peer Group, 21
        cos verbatim (MDCC: no changes this year); queued GIS/IP
        fabrications dropped; added MMM; supplemental WTW cross-industry
        sample unnamed - unstored)
  WEC   22 -> 20 (DEF 14A 2026-03-26; FW Cook 2025 comparison group, 20
        utilities verbatim ("same 20 companies as the previous year's
        comparison group"); queued AWK/COF/DUK/IP fabrications dropped;
        added ES/EIX; WTW + Aon Radford surveys unnamed - unstored)
  LMT   21 -> 17 (DEF 14A 2026-03-26; "Lockheed Martin Comparator Group -
        2025 Comparator Group Companies", market-rate group for 2025 comp
        decisions, verbatim; DOW removed 2025 per filing ("no longer
        participates in the Aon Benchmarking Survey"); GE Aerospace
        maintained post-spin-offs; Verizon + Dell Technologies newly added;
        queued AON/GIS/PSA/TDG/TXT fabrications dropped; added MMM/GE;
        2025-2027 A&D Relative TSR Comparators (9 cos, weighted with S&P 500
        Index) documented unstored per TSR precedent)
  SWK   21 -> 16 (DEF 14A 2026-03-06; 2025 Compensation Peer Group, 16 cos
        verbatim ("no changes made to the Compensation Peer Group for
        2025"); queued COF/DOW/IP/IR/KEY/POOL/TT/WMB fabrications dropped;
        added OC/PH/WHR; published compensation surveys unnamed - unstored)

Two new verified_cross_sector marks this batch (all filing-verbatim,
surviving the repair): JNJ->MSFT, JNJ->PG. Queue 262->~244 pending (the
marks + the flagged-source drain); verified 47->49.

No new nodes needed: every verbatim peer ticker already exists as a node
(checked pre-run; AMT's BXP/EQR/LHX/PSA, JNJ's ABT/IBM, TEL/LMT's MMM,
LMT's GE, WEC's ES/EIX, SWK's OC/PH/WHR all present).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# no new peer-only nodes this batch (all targets exist)

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'AMT': ('DEF 14A 2026-04-08',
            ['ADBE', 'BKNG', 'AVGO', 'BXP', 'CCI', 'DLR', 'EQIX', 'EQR',
             'FIS', 'INTU', 'LHX', 'MA', 'MSI', 'NEE', 'PLD', 'PSA',
             'CRM', 'SBAC', 'SPG', 'TXN', 'VTR', 'WELL']),
    'JNJ': ('DEF 14A 2026-03-11',
            ['ABT', 'ABBV', 'AMGN', 'T', 'BA', 'BMY', 'CSCO', 'LLY',
             'GILD', 'INTC', 'IBM', 'MDT', 'MRK', 'MSFT', 'PFE', 'PG',
             'RTX']),
    'TEL': ('DEF 14A 2026-01-15',
            ['MMM', 'ETN', 'NXPI', 'APH', 'EMR', 'PH', 'APTV', 'FTV',
             'ROK', 'CARR', 'GD', 'SWK', 'GLW', 'HON', 'TXN', 'CMI',
             'ITW', 'TXT', 'DOV', 'JCI', 'TT']),
    'WEC': ('DEF 14A 2026-03-26',
            ['LNT', 'ED', 'EVRG', 'PCG', 'AEE', 'D', 'ES', 'PNW', 'AEP',
             'DTE', 'EXC', 'PPL', 'CNP', 'EIX', 'FE', 'SO', 'CMS',
             'ETR', 'NI', 'XEL']),
    'LMT': ('DEF 14A 2026-03-26',
            ['MMM', 'GE', 'NOC', 'CAT', 'GD', 'RTX', 'CSCO', 'HON',
             'BA', 'DE', 'HPQ', 'UPS', 'DELL', 'IBM', 'VZ', 'FDX',
             'INTC']),
    'SWK': ('DEF 14A 2026-03-06',
            ['CARR', 'EMR', 'OC', 'ROK', 'CMI', 'ITW', 'PCAR', 'SHW',
             'DOV', 'JCI', 'PH', 'TXT', 'ETN', 'MAS', 'PPG', 'WHR']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-02 07:30 PT from peer-network.json (914 nodes / 7,061 edges)
EXPECTED_OLD = {
    'AMT': ['ADBE', 'AVGO', 'AWK', 'BKNG', 'CCI', 'COF', 'CRM', 'DLR',
            'EQIX', 'FIS', 'INTU', 'MA', 'MSI', 'NEE', 'NVDA', 'PLD',
            'SBAC', 'SPG', 'TGT', 'TXN', 'VTR', 'WELL'],
    'JNJ': ['ABBV', 'AMGN', 'BA', 'BMY', 'BSX', 'CL', 'CSCO', 'GE',
            'GILD', 'INTC', 'ISRG', 'JCI', 'LLY', 'MDT', 'MRK', 'MSFT',
            'PFE', 'PG', 'RTX', 'SYK', 'T', 'ZBH'],
    'TEL': ['APH', 'APTV', 'CARR', 'CMI', 'DOV', 'EMR', 'ETN', 'FTV',
            'GD', 'GIS', 'GLW', 'HON', 'IP', 'ITW', 'JCI', 'NXPI',
            'PH', 'ROK', 'SWK', 'TT', 'TXN', 'TXT'],
    'WEC': ['AEE', 'AEP', 'AWK', 'CMS', 'CNP', 'COF', 'D', 'DTE', 'DUK',
            'ED', 'ETR', 'EVRG', 'EXC', 'FE', 'IP', 'LNT', 'NI', 'PCG',
            'PNW', 'PPL', 'SO', 'XEL'],
    'LMT': ['AON', 'BA', 'CAT', 'CSCO', 'DE', 'DELL', 'DOW', 'FDX',
            'GD', 'GIS', 'HON', 'HPQ', 'IBM', 'INTC', 'NOC', 'PSA',
            'RTX', 'TDG', 'TXT', 'UPS', 'VZ'],
    'SWK': ['CARR', 'CMI', 'COF', 'DOV', 'DOW', 'EMR', 'ETN', 'IP',
            'IR', 'ITW', 'JCI', 'KEY', 'MAS', 'PCAR', 'POOL', 'PPG',
            'ROK', 'SHW', 'TT', 'TXT', 'WMB'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261002_0730_pre_batch8i.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}

    # 1. assert + replace edges for the repaired sources
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

    # 2. recompute degrees exactly
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

    # 3. metadata from actuals
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
