#!/usr/bin/env python3
"""Peer-network batch-8j fingerprint-queue repair (2026-10-02 run).

Follow-up to the batch-8a/8b/8c/8d/8e/8f/8g/8h/8i runs (2026-10-01/02). After
8i, the Section-19 fingerprint queue holds 250 cross-sector fingerprint-target
edges across 180 sources (70 sources x2, 110 sources x1); verified_cross_sector
marks at 49. Batch-8j takes the 6 heaviest remaining 2-queue sources by total
outbound edge count (ECL 20 / ETR 20 / XYL 20 / APTV 19 / CHD 19 / MKC 19 -
alphabetical tie-break among the eight 19-outdeg sources) and re-extracts each
source's comp-decisions peer group VERBATIM from its latest DEF 14A, keeping
only edges that match the verbatim group. TSR/performance comparator groups,
2026-variant groups, and unnamed survey databases are documented but unstored
per the batches 3-8i convention (V Block->Uber / HPQ FY2026 / GDDY 2026 /
KMB 2026 / CNP 2026 / IFF 2026 / KDP 2026 / GEV 2026 / DVN Jan-2026 / CRL
2026 / ADM index-only / CTAS+ETN TSR-only precedents).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run; tickers/CIKs verified against SEC
company_tickers.json - ECL 31462 / ETR 65984 / XYL 1524472 / APTV 1521332 /
CHD 313927 / MKC 63754), filing HTML fetched with User-Agent
"Kit/1.0 (factoryfactorykit@gmail.com)" (sequential, ~2s pacing; non-padded
CIK in Archive URLs + curl -L per the batch-8d note; primary document names
from each filing's index.json). Peer sections transcribed verbatim. Evidence in
goal hidden_files/peer-batch8j-20261002/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8j_filings.json (accession/URL map); filing HTML backups
copied to the goal dir immediately after download (the batch-8h
/tmp-peersweep-wipe lesson).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  ECL   20 -> 21 (DEF 14A 2026-03-20; 21-company peer group for 2025, verbatim
        with filing tickers, "no changes to the 21-company peer group for
        2025"; queued GIS fabrication dropped; added CE/MMM; WM SURVIVES -
        genuine verbatim cross-sector edge (ECL Materials -> WM Industrials),
        marked verified per batch-8h precedent; WTW + FW Cook general-industry
        surveys unnamed - unstored)
  ETR   20 -> 20 (DEF 14A 2026-03-27; Compensation Peer Group = Philadelphia
        Utility Index companies as of 2026-10-31, verbatim; queued GIS/FDX/IP
        fabrications dropped; added AES/EIX/ES; unnamed survey data - unstored)
  XYL   20 -> 19 (DEF 14A 2026-03-30; 2025 Peer Group, verbatim, used for
        benchmarking 2025 NEO compensation; queued FRT/GIS fabrications
        dropped; added LECO/FLS; the filing's 2026 Peer Group (A/ROP out,
        OSK/SWK in) documented but NOT stored per the 2026-variant precedent;
        Aon Hewitt + WTW surveys unnamed - unstored)
  APTV  19 -> 18 (DEF 14A 2026-03-16; Aptiv's 2025 peer group for 2025 target
        compensation decisions, verbatim; queued IP/PSA fabrications dropped;
        added LEA)
  CHD   19 -> 17 (DEF 14A 2026-03-19; Compensation Peer Group column of the
        three-column peer-group table, verbatim; the old set was almost
        entirely fabricated (CAG/CL/COF/KHC/KMB/MDLZ/PEP/PFG/PG/TGT/WTW plus
        GIS/KDP/HAS/HSY/KVUE/MKC/MNST/CLX only partly right); queued COF/PFG
        fabrications dropped; added COTY/CPB/ENR/EPC/FLO/NWL/PRGO/POST/SMG/SJM;
        Performance Peer Group (relative TSR for 2025 PSU grants) and CIP
        Rating Peer Group documented unstored per TSR precedent; "The
        Performance Peer Group did not change in 2025 from the prior year")
  MKC   19 ->  8 (DEF 14A 2026-02-18; Market Group = Market-Group-Only +
        Market-and-Peer-Groups columns of the three-column table, verbatim,
        8 companies; the old 19-edge set blended genuine Market Group members
        (BF-A/STZ/TAP/CAG/CHD/CLX/CPB) with Peer-Group-Only performance-
        comparator members (HRL/HSY/IFF/K/KDP/KHC/LW/MNST/TSN, documented
        unstored per the TSR precedent) plus CHTR/COF/GIS fabrications;
        queued COF/CHTR fabrications dropped; added FLO; the filing names
        "Brown-Forman Corporation" with no share class - stored as BF-A, the
        dataset's canonical dual-class ticker (GOOGL/BF-A/LEN precedent);
        CHCC removed Monster Beverage from both groups per the filing; Peer
        Group Only column (financial-performance insights + LTPP relative-TSR
        modifier) documented unstored per TSR precedent)

One new verified_cross_sector mark this batch (filing-verbatim, surviving the
repair): ECL->WM. Queue 250->238 pending (12 queued edges resolved: ECL GIS/WM,
ETR GIS/IP, XYL FRT/GIS, APTV PSA/IP, CHD COF/PFG, MKC COF/CHTR); verified
49->50.

No new nodes needed: every verbatim peer ticker already exists as a node
(checked pre-run; Brown-Forman stored as existing BF-A per the dataset's
single-class dual-listing convention).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# no new peer-only nodes this batch (all targets exist; Brown-Forman stored
# as the existing BF-A node per the dataset's single-class dual-listing
# convention - GOOGL / BF-A / LEN)

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'ECL': ('DEF 14A 2026-03-20',
            ['MMM', 'DOV', 'ITW', 'A', 'DOW', 'LIN', 'APD', 'DD',
             'PPG', 'CE', 'EMN', 'RSG', 'CTAS', 'ETN', 'SHW', 'CLX',
             'EMR', 'TMO', 'DHR', 'HON', 'WM']),
    'ETR': ('DEF 14A 2026-03-27',
            ['AES', 'EIX', 'AEE', 'ES', 'AEP', 'EXC', 'AWK', 'FE',
             'CNP', 'NEE', 'ED', 'PNW', 'CEG', 'PEG', 'D', 'SO',
             'DTE', 'WEC', 'DUK', 'XEL']),
    'XYL': ('DEF 14A 2026-03-30',
            ['A', 'LECO', 'AME', 'PH', 'DOV', 'PNR', 'ECL', 'ROK',
             'EMR', 'ROP', 'FLS', 'SNA', 'FTV', 'TEL', 'IEX', 'TT',
             'ITW', 'VLTO', 'IR']),
    'APTV': ('DEF 14A 2026-03-16',
             ['ADBE', 'JCI', 'APH', 'LEA', 'GLW', 'PYPL', 'CMI', 'ROK',
              'ETN', 'CRM', 'EMR', 'TEL', 'FTV', 'TXT', 'HON', 'TT',
              'ITW', 'UBER']),
    'CHD': ('DEF 14A 2026-03-19',
            ['CLX', 'COTY', 'CPB', 'ENR', 'EPC', 'FLO', 'HAS', 'HSY',
             'KVUE', 'KDP', 'MKC', 'MNST', 'NWL', 'PRGO', 'POST',
             'SMG', 'SJM']),
    'MKC': ('DEF 14A 2026-02-18',
            ['BF-A', 'STZ', 'TAP', 'CAG', 'CPB', 'CHD', 'CLX', 'FLO']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-02 10:00 PT from peer-network.json (914 nodes / 7,044 edges).
# NOTE: the pre-run plan recorded a fully-fabricated 19-edge MKC set, but the
# live file shows the actual old MKC set below (a blend of genuine Market
# Group members, Peer-Group-Only performance comparators, and CHTR/COF/GIS
# fabrications); the assertion guard caught the drift and the EXPECTED_OLD
# entry was corrected to the live set before any write.
EXPECTED_OLD = {
    'ECL': ['ITW', 'GIS', 'CLX', 'TMO', 'ETN', 'DOV', 'DD', 'DOW', 'WM',
            'PPG', 'APD', 'EMR', 'RSG', 'CTAS', 'EMN', 'LIN', 'DHR',
            'HON', 'A', 'SHW'],
    'ETR': ['DTE', 'AWK', 'WEC', 'EXC', 'XEL', 'AEE', 'GIS', 'FDX',
            'AEP', 'PEG', 'FE', 'IP', 'CEG', 'DUK', 'PNW', 'NEE',
            'D', 'SO', 'ED', 'CNP'],
    'XYL': ['A', 'AME', 'DOV', 'ECL', 'EMR', 'FRT', 'FTV', 'GIS',
            'IEX', 'IR', 'ITW', 'PH', 'PNR', 'ROK', 'ROP', 'SNA',
            'SWK', 'TEL', 'TT', 'VLTO'],
    'APTV': ['ADBE', 'APH', 'CMI', 'CRM', 'EMR', 'ETN', 'FTV', 'GLW',
             'HON', 'IP', 'ITW', 'JCI', 'PSA', 'PYPL', 'ROK', 'TEL',
             'TT', 'TXT', 'UBER'],
    'CHD': ['CAG', 'CL', 'CLX', 'COF', 'GIS', 'HAS', 'HSY', 'KDP',
            'KHC', 'KMB', 'KVUE', 'MDLZ', 'MKC', 'MNST', 'PEP', 'PFG',
            'PG', 'TGT', 'WTW'],
    'MKC': ['BF-A', 'CAG', 'CHD', 'CHTR', 'CLX', 'COF', 'CPB', 'GIS',
            'HRL', 'HSY', 'IFF', 'K', 'KDP', 'KHC', 'LW', 'MNST', 'STZ',
            'TAP', 'TSN'],
}

# new verified_cross_sector marks (filing-verbatim surviving edges only)
NEW_MARKS = [
    {'source': 'ECL', 'target': 'WM', 'filing': 'DEF 14A 2026-03-20',
     'batch': 'peer-batch8j-20261002'},
]


def main():
    bak = SRC.replace('.json', '_backup_20261002_1000_pre_batch8j.json')
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

    # 2. append verified_cross_sector marks (dedupe-guarded)
    marks = net['metadata'].setdefault('verified_cross_sector', [])
    seen = {(m['source'], m['target']) for m in marks}
    for m in NEW_MARKS:
        assert (m['source'], m['target']) not in seen, \
            f"duplicate mark {m['source']}->{m['target']}"
        marks.append(m)
        seen.add((m['source'], m['target']))
    print('verified_cross_sector marks:', len(marks))

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
