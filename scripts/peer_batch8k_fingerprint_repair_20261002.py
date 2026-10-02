#!/usr/bin/env python3
"""Peer-network batch-8k fingerprint-queue repair (2026-10-02 run).

Follow-up to the batch-8a/8b/8c/8d/8e/8f/8g/8h/8i/8j runs (2026-10-01/02). After
8j, the Section-19 fingerprint queue holds 238 cross-sector fingerprint-target
edges pending across 174 sources (ECL->WM marked via the batch-8j registration
this run). Batch-8k takes the 6 heaviest remaining 2-queue sources by total
outbound edge count (PCG 19 / PEG 19 / PYPL 19 / UNH 19 / VTR 19 / FISV 18)
and re-extracts each source's comp-decisions peer group VERBATIM from its
latest DEF 14A, keeping only edges that match the verbatim group. TSR/
performance comparator groups, 2026-variant groups, and unnamed survey
databases are documented but unstored per the batches 3-8j convention
(V Block->Uber / HPQ FY2026 / GDDY 2026 / KMB 2026 / CNP 2026 / IFF 2026 /
KDP 2026 / GEV 2026 / DVN Jan-2026 / CRL 2026 / CEG 2026 / XYL 2026 /
FISV 2026 COF-for-DFS precedents; CTAS+ETN TSR-only / ADM index-only).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run; tickers/CIKs verified against SEC
company_tickers.json - PCG 1004980 / PEG 788784 / PYPL 1633917 / UNH 731766 /
VTR 740260 / FISV 798354), filing HTML fetched with User-Agent
"Kit/1.0 (factoryfactorykit@gmail.com)" (sequential, 3s pacing; non-padded
CIK in Archive URLs + curl -L per the batch-8d note; primary document names
from each filing's submissions primaryDocument field). Peer sections
transcribed verbatim. Evidence in goal
hidden_files/peer-batch8k-20261002/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8k_filings.json (accession/URL map); filing HTML
backups copied to the goal dir immediately after download (the batch-8h
/tmp-peersweep-wipe lesson).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  PCG   19 -> 30 (DEF 14A 2026-04-09; 2025 Pay Comparator Group, verbatim
        with filing tickers - the operative table lists 30 companies with
        a Pay checkmark; queued IP/PSA fabrications dropped; added CNP/CEG/
        EIX/EVRG/ES/MOH/NEE/NRG/NUE/OXY/SRE/LUV/UNP; the prose change-note
        claims Entergy was removed from the Pay group but the resulting
        table lists Entergy (ETR) WITH a Pay checkmark - the table is the
        operative disclosure, ETR stored verbatim from it (filing-side
        inconsistency documented in the evidence file); Performance
        Comparator Group (relative-TSR for PSUs) unstored per TSR precedent;
        unnamed survey data unstored)
  PEG   19 -> 18 (DEF 14A 2026-03-12; 2025 peer group "for 2025", verbatim,
        18 similarly-sized utilities; "For 2026, we did not make changes to
        the peer group"; queued IP/TGT fabrications dropped; added EIX/ES/
        SRE; old AWK/WTW edges dropped; the same named group feeds LTIP
        relative-TSR assessment per the filing - no separate TSR group
        disclosed)
  PYPL  19 -> 20 (DEF 14A 2026-04-07; 2025 Compensation Peer Group, verbatim,
        10 tech + 10 financial; ADP removed / Airbnb added per filing;
        queued TGT fabrication dropped; added SHOP/USB/DFS; Block stored as
        XYZ (live NYSE ticker; SQ retired, SEC company_tickers.json
        verified); Discover Financial Services stored as DFS per
        delisted-peer precedent (Capital One merger completed May 2025, the
        2025 group still names it); COF SURVIVES - genuine verbatim
        cross-sector edge (PYPL = Information Technology in dataset sectors,
        COF home = Financials), marked verified per batch-8h precedent)
  UNH   19 -> 20 (DEF 14A 2026-04-21; 20-co compensation peer group verbatim
        with filing-supplied NYSE/Nasdaq tickers (the text-extraction
        flattened the two-column chart to 15 - the raw HTML table holds all
        20; 5 largest managed-care competitors included per the screening
        methodology); queued GIS fabrication dropped; added IBM/JNJ/PFE;
        old TRGP edge dropped; MSFT SURVIVES - genuine verbatim cross-sector
        edge (UNH = Health Care, MSFT home = Information Technology),
        marked verified; pay-vs-performance Peer Group TSR uses the S&P 500
        Health Care Index - documented unstored per index-only precedent)
  VTR   19 -> 20 (DEF 14A 2026-04-01; 2025 Compensation Peer Group, verbatim
        with filing tickers, * = new for 2025 (ARE/KIM/MAA/UDR/INVH); Macerich
        + Vornado removed per filing; queued GIS/IP fabrications dropped;
        old GPN edge dropped; Medical Properties Trust stored as MPT, the
        LIVE NYSE ticker (MPW->MPT effective 2026-02-02 per Business Wire
        2026-01-20; the filing prints the stale (MPW) code - live holder
        wins per ticker-slot discipline, same class as batch-8g VERX->VRTX);
        new node MPT, Real Estate; all 20 same-sector, no verified marks)
  FISV  18 -> 18 (DEF 14A 2026-04-02; 2025 peer group verbatim - the existing
        18-edge set was ALREADY filing-verbatim (assertion confirms byte-set
        equality); Adobe added for 2025 per filing; queued NDAQ + BLK both
        SURVIVE genuine (FISV = Information Technology, both targets' home =
        Financials) -> 2 verified marks per batch-8h precedent; footnote
        (1) "Capital One Financial Corporation replaced Discover Financial
        Services in our peer group for 2026 compensation" documented but NOT
        stored per the 2026-variant precedent chain, queued for the FY2026
        cycle; Block stored as XYZ (live ticker); BNY Mellon stored as BNY
        (BK->BNY 2026-05-21, node exists per batch-8c))

Four new verified_cross_sector marks this batch (filing-verbatim, surviving
the repair): PYPL->COF, UNH->MSFT, FISV->NDAQ, FISV->BLK. Queue 238->226
pending (12 queued edges resolved: PCG PSA/IP, PEG IP/TGT, PYPL COF/TGT,
UNH GIS/MSFT, VTR GIS/IP, FISV NDAQ/BLK); verified 50->54.

New nodes: 1 (MPT, Medical Properties Trust, Real Estate) - added to
PEER_ONLY_NODES with a dated batch-8k comment BEFORE the repair ran (the
batch-5 lesson held, consistency check green on first commit attempt).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'MPT': ('Medical Properties Trust, Inc.', 'Real Estate'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'PCG': ('DEF 14A 2026-04-09',
            ['LNT', 'AEE', 'AEP', 'CNP', 'CMS', 'ED', 'CEG', 'D',
             'DTE', 'DUK', 'EIX', 'ETR', 'EVRG', 'ES', 'EXC', 'FE',
             'MOH', 'NEE', 'NI', 'NRG', 'NUE', 'OXY', 'PNW', 'PPL',
             'SRE', 'LUV', 'SO', 'UNP', 'WEC', 'XEL']),
    'PEG': ('DEF 14A 2026-03-12',
            ['AEE', 'AEP', 'CNP', 'CMS', 'ED', 'D', 'DTE', 'DUK',
             'EIX', 'ETR', 'ES', 'EXC', 'FE', 'PPL', 'SRE', 'SO',
             'WEC', 'XEL']),
    'PYPL': ('DEF 14A 2026-04-07',
             ['ADBE', 'ABNB', 'XYZ', 'INTU', 'NFLX', 'ORCL', 'CRM',
              'NOW', 'SHOP', 'UBER', 'AXP', 'COF', 'DFS', 'FIS',
              'FISV', 'GPN', 'JPM', 'MA', 'USB', 'V']),
    'UNH': ('DEF 14A 2026-04-21',
            ['GOOGL', 'CI', 'JPM', 'AMZN', 'C', 'MCK', 'AAPL', 'CVS',
             'MSFT', 'BAC', 'ELV', 'PFE', 'CAH', 'HUM', 'WMT',
             'COR', 'IBM', 'WFC', 'CNC', 'JNJ']),
    'VTR': ('DEF 14A 2026-04-01',
            ['ARE', 'KIM', 'AMT', 'MPT', 'AVB', 'MAA', 'BXP', 'PLD',
             'CCI', 'PSA', 'DLR', 'O', 'EQIX', 'SPG', 'EQR', 'UDR',
             'DOC', 'WELL', 'INVH', 'WY']),
    'FISV': ('DEF 14A 2026-04-02',
             ['ADBE', 'INTU', 'AXP', 'MA', 'ADP', 'NDAQ', 'BLK',
              'PAYX', 'XYZ', 'PYPL', 'CTSH', 'CRM', 'DFS', 'SPGI',
              'FIS', 'BNY', 'GPN', 'V']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-02 11:30 PT from peer-network.json (914 nodes / 7,030 edges).
EXPECTED_OLD = {
    'PCG': ['AEE', 'AEP', 'CMS', 'D', 'DTE', 'DUK', 'ED', 'ETR',
            'EXC', 'FE', 'IP', 'LNT', 'NI', 'PNW', 'PPL', 'PSA',
            'SO', 'WEC', 'XEL'],
    'PEG': ['AEE', 'AEP', 'AWK', 'CMS', 'CNP', 'D', 'DTE', 'DUK',
            'ED', 'ETR', 'EXC', 'FE', 'IP', 'PPL', 'SO', 'TGT',
            'WEC', 'WTW', 'XEL'],
    'PYPL': ['ABNB', 'ADBE', 'ADP', 'AXP', 'COF', 'CRM', 'FIS',
             'FISV', 'GPN', 'INTU', 'JPM', 'MA', 'NFLX', 'NOW',
             'ORCL', 'TGT', 'UBER', 'V', 'XYZ'],
    'UNH': ['AAPL', 'AMZN', 'BAC', 'C', 'CAH', 'CI', 'CNC', 'COR',
            'CVS', 'ELV', 'GIS', 'GOOGL', 'HUM', 'JPM', 'MCK',
            'MSFT', 'TRGP', 'WFC', 'WMT'],
    'VTR': ['AMT', 'ARE', 'AVB', 'DLR', 'DOC', 'EQIX', 'GIS', 'GPN',
            'INVH', 'IP', 'KIM', 'MAA', 'O', 'PLD', 'PSA', 'SPG',
            'UDR', 'WELL', 'WY'],
    'FISV': ['ADBE', 'ADP', 'AXP', 'BLK', 'BNY', 'CRM', 'CTSH',
             'DFS', 'FIS', 'GPN', 'INTU', 'MA', 'NDAQ', 'PAYX',
             'PYPL', 'SPGI', 'V', 'XYZ'],
}

# new verified_cross_sector marks (filing-verbatim surviving edges only)
NEW_MARKS = [
    {'source': 'PYPL', 'target': 'COF', 'filing': 'DEF 14A 2026-04-07',
     'batch': 'peer-batch8k-20261002'},
    {'source': 'UNH', 'target': 'MSFT', 'filing': 'DEF 14A 2026-04-21',
     'batch': 'peer-batch8k-20261002'},
    {'source': 'FISV', 'target': 'NDAQ', 'filing': 'DEF 14A 2026-04-02',
     'batch': 'peer-batch8k-20261002'},
    {'source': 'FISV', 'target': 'BLK', 'filing': 'DEF 14A 2026-04-02',
     'batch': 'peer-batch8k-20261002'},
]


def main():
    bak = SRC.replace('.json', '_backup_20261002_1130_pre_batch8k.json')
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
