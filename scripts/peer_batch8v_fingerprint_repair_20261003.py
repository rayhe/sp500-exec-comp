#!/usr/bin/env python3
"""Peer-network batch-8v fingerprint-queue repair (2026-10-03 18:00 PDT run).

Batch-8v of the fingerprint-queue drain. The 6 heaviest remaining 2-edge
sources by total outbound edge count (AFL/BMY/CDW/CMG/HAL/HIG, all out=12)
re-extracted verbatim from latest DEF 14A via EDGAR (Kit/1.0 UA; curl -L,
non-padded CIK; primaryDocument from submissions; sequential ~2-3s pacing;
no subagents per the task execution rule). Peer sections transcribed
verbatim. Evidence in goal hidden_files/peer-batch8v-20261003/
<TICKER>_peer.txt (verbatim transcriptions) + batch8v_submissions.json
(accession/URL map) + batch8v_docs.json; filing HTMLs persisted to the goal
dir AT download time (the batch-8h /tmp-peersweep-wipe lesson).

Repairs (6 sources; latest DEF 14A each):

  AFL   12 -> 16 (DEF 14A 2026-03-19; "2025 Peer Group", verbatim, 16;
        no changes 2024->2025. Dropped stored GIS + WM + COF fabrications;
        added BHF, CB, CRBG, EQH, LNC, MFC, UNM (all already nodes except
        CRBG/MFC). No marks.)
  BMY   12 -> 8  (DEF 14A 2026-03-25; "2025 Primary Peer Group", verbatim, 8;
        2025 changes: removed Biogen, added Regeneron. Dropped stored BIIB +
        GIS + TGT + ADP fabrications (BIIB was the pre-2025 member; the old
        extractor carried both). The Extended Peer Group (primary 8 +
        AZN/GSK/NVS/ROG/SNY) is a selective reference + PSU/MSU relative-TSR
        input -> UNSTORED per the KHC/ACGL performance-group convention; the
        PHRA Survey Group (incl. Takeda) is survey data -> UNSTORED. No marks.)
  CDW   12 -> 16 (DEF 14A 2026-04-10; "2025 compensation peer group",
        verbatim, 16 (PvP footnote TSR group = the comp group). 2024->2025:
        removed DXC + BBY, added IBM. Dropped stored BBY (2024-group leak) +
        EA + IP + TGT fabrications; added ARW, AVT, GIB, FLEX, NSIT, SNX,
        GWW, WCC (all already nodes except SNX). No marks.)
  CMG   12 -> 16 (DEF 14A 2026-04-28; "2025 Peer Group", verbatim, 16;
        Sept-2025 review: no changes for 2026 comp. Dropped stored CHTR + IP
        fabrications; added DPZ, EBAY, LULU, MCD, QSR, YUM (all already
        nodes). No marks.)
  HAL   12 -> 16 (DEF 14A 2026-03-31; "2025 Comparator Peer Group" — the
        group "used to determine market levels of total compensation for the
        2025 plan year", verbatim, 16; unchanged from 2024. Dropped stored
        ELV + GIS + IP fabrications; added MMM, DE, NOV, SLB, RIG, FLR, WFRD
        (already nodes except RIG/WFRD). The 2025 Performance Peer Group
        (17 cos, PUP ROCE/TSR) is performance-assessment only -> UNSTORED
        per convention; OSX index-only -> UNSTORED. No marks.)
  HIG   12 -> 14 (DEF 14A 2026-04-09; "2025 Corporate Peer Group",
        verbatim, 14 public cos; no 2025 changes. Dropped stored AWK + EG +
        GIS + IP fabrications; added WRB, CNA, THG, LNC, UNM, VOYA (all
        already nodes). The 4 non-public survey-only members (Liberty
        Mutual, MassMutual, Nationwide, State Farm) -> UNSTORED. No marks.)

New nodes: 5 (CRBG - Corebridge Financial, Financials; MFC - Manulife
Financial Corp, Financials; SNX - TD SYNNEX Corp, Information Technology;
RIG - Transocean Ltd., Energy; WFRD - Weatherford International plc,
Energy) - registered in PEER_ONLY_NODES and in mark_verified REPAIR_SCRIPTS
BEFORE the repair ran (the batch-5 / batch-8h lessons held).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'CRBG': ('Corebridge Financial, Inc.', 'Financials'),
    'MFC': ('Manulife Financial Corp', 'Financials'),
    'SNX': ('TD SYNNEX Corp', 'Information Technology'),
    'RIG': ('Transocean Ltd.', 'Energy'),
    'WFRD': ('Weatherford International plc', 'Energy'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'AFL': ('DEF 14A 2026-03-19',
            ['ALL', 'AIZ', 'BHF', 'CB', 'CRBG', 'EQH', 'HIG', 'HUM',
             'LNC', 'MFC', 'MET', 'PFG', 'PGR', 'PRU', 'TRV', 'UNM']),
    'BMY': ('DEF 14A 2026-03-25',
            ['ABBV', 'AMGN', 'LLY', 'GILD', 'JNJ', 'MRK', 'PFE', 'REGN']),
    'CDW': ('DEF 14A 2026-04-10',
            ['ACN', 'ARW', 'AVT', 'GIB', 'CTSH', 'FLEX', 'GPC', 'HSIC',
             'HPE', 'NSIT', 'IBM', 'JBL', 'LKQ', 'SNX', 'GWW', 'WCC']),
    'CMG': ('DEF 14A 2026-04-28',
            ['ABNB', 'BKNG', 'DRI', 'DPZ', 'DASH', 'EBAY', 'EXPE', 'HLT',
             'LULU', 'MAR', 'MCD', 'QSR', 'SBUX', 'UBER', 'ULTA', 'YUM']),
    'HAL': ('DEF 14A 2026-03-31',
            ['MMM', 'HES', 'APA', 'HON', 'BKR', 'JCI', 'CAT', 'NOV',
             'COP', 'OXY', 'DE', 'SLB', 'EMR', 'RIG', 'FLR', 'WFRD']),
    'HIG': ('DEF 14A 2026-04-09',
            ['ALL', 'AIG', 'WRB', 'CB', 'CINF', 'CNA', 'THG', 'LNC',
             'MET', 'PFG', 'PGR', 'TRV', 'UNM', 'VOYA']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-03 18:00 PT from peer-network.json (966 nodes / 7,381 edges).
EXPECTED_OLD = {
    'AFL': ['AIZ', 'ALL', 'COF', 'GIS', 'HIG', 'HUM', 'MET', 'PFG',
            'PGR', 'PRU', 'TRV', 'WM'],
    'BMY': ['ABBV', 'ADP', 'AMGN', 'BIIB', 'GILD', 'GIS', 'JNJ', 'LLY',
            'MRK', 'PFE', 'REGN', 'TGT'],
    'CDW': ['ACN', 'BBY', 'CTSH', 'EA', 'GPC', 'HPE', 'HSIC', 'IBM',
            'IP', 'JBL', 'LKQ', 'TGT'],
    'CMG': ['ABNB', 'BKNG', 'CHTR', 'DASH', 'DRI', 'EXPE', 'HLT', 'IP',
            'MAR', 'SBUX', 'UBER', 'ULTA'],
    'HAL': ['APA', 'BKR', 'CAT', 'COP', 'ELV', 'EMR', 'GIS', 'HES',
            'HON', 'IP', 'JCI', 'OXY'],
    'HIG': ['AIG', 'ALL', 'AWK', 'CB', 'CINF', 'EG', 'GIS', 'IP',
            'MET', 'PFG', 'PGR', 'TRV'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261003_1800_pre_batch8v.json')
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
