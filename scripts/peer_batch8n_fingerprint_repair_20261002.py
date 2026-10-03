#!/usr/bin/env python3
"""Peer-network batch-8n fingerprint-queue repair (2026-10-02 22:00 PDT run).

Follow-up to the batch-8a..8m runs (2026-10-01/02). After 8m, the Section-19
fingerprint queue held 202 cross-sector fingerprint-target edges pending
across 156 sources (61 verified marks); the heaviest remaining tier is 46
sources with exactly 2 queued edges each. Batch-8n takes the 6 heaviest of
those by total outbound edge count (ZBRA 17 / DOC 16 / FSLR 16 / GD 16 /
RMD 16 / TDY 16) and re-extracts each source's comp-decisions peer group
VERBATIM from its latest DEF 14A, keeping only edges that match the
verbatim group. TSR/performance comparator groups, index-only groups,
2026-variant groups, and unnamed survey databases are documented but
unstored per the batches 3-8m convention (RMD ASX-peer precedent this
batch; SunPower-removed + Nextracker-renamed footnotes in FSLR).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run; CIKs verified against
compensation.json - ZBRA 0000877212 / DOC 0000765880 / FSLR 0001274494 /
GD 0000040533 / RMD 0000943819 / TDY 0001094285), filing HTML fetched
with User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential,
~2s pacing; non-padded CIK in Archive URLs + curl -L per the batch-8d
note; primary document names from each filing's submissions
primaryDocument field). Peer sections transcribed verbatim. Evidence in
goal hidden_files/peer-batch8n-20261002/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8n_filings.json (accession/URL map); filing HTMLs
persisted to the goal dir AT download time (the batch-8h /tmp-peersweep-
wipe lesson).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  ZBRA  17 -> 17 (DEF 14A 2026-04-03; 2025 compensation peer group,
        verbatim table (17 companies, revenues as of Sep 30 2024);
        approved July/August 2024 after FW Cook review; dropped COF +
        GIS queued fabrications + KLAC + NOW non-members; added CIEN,
        FFIV, NSIT, VNT; new nodes CIEN (Ciena Corp., IT), NSIT
        (Insight Enterprises, IT), VNT (Vontier Corp., IT); FFIV/MS
        exist; TDY cites Zebra back (TDY->ZBRA edge added in TDY
        repair this batch); no cross-sector marks)
  DOC   16 -> 14 (DEF 14A 2026-03-12; "2025 executive compensation peer
        group" (14 S&P 500 equity REITs, verbatim bullet list); dropped
        AWK + COF + GIS + KEY + SPGI fabrications; added HR, OHI, WPC;
        new nodes HR (Healthcare Realty Trust, Real Estate), OHI
        (Omega Healthcare Investors, Real Estate), WPC (W.P. Carey,
        Real Estate); the 2023 LTIP relative-TSR peer groups (footnote:
        companies weighted by asset-mix comparability incl. Healthcare
        Realty) are performance-assessment only - UNSTORED; no marks)
  FSLR  16 -> 27 (DEF 14A 2026-04-02; 2025 peer group, verbatim (28
        named, 27 stored); dropped BLK + COF queued fabrications;
        SunPower REMOVED (Chapter 11 Aug 2024, footnote 2) - UNSTORED
        per explicit removal; added AMRC, AMKR, ARRY, AGR, CRUS, DIOD,
        ENS, ENTG, MKSI, NXT, QRVO, RUN, AES; new nodes AMRC
        (Ameresco, Industrials), ARRY (Array Technologies,
        Industrials), AGR (Avangrid, Utilities - delisted Dec 2024,
        stored verbatim per the CTLT delisted-peer precedent), ENS
        (EnerSys, Industrials); footnote (1): Nextracker rebranded to
        Nextpower Inc. Nov 2025 - stored as NXT (same ticker lineage);
        no marks)
  GD    16 -> 14 (DEF 14A 2026-03-27; "Peer Group Companies" table with
        filing-supplied tickers (14 + GD self); dropped AON + COF + IP
        fabrications; added MMM; the dagger-marked peers disclose GD
        as a peer back - directed GD->X edges only per convention;
        the rTSR PSU measure is performance-only, no separate group
        disclosed - nothing to store; no marks)
  RMD   16 -> 19 (DEF 14A 2026-10-01; US peer group for fiscal 2026
        comp decisions, verbatim (19); Feb-2025 refresh: removed
        Dentsply Sirona (smaller), added IQVIA; dropped ABBV + GIS +
        IP fabrications; added BIO, BSX, COO, ILMN, IQV, TFX; PSU
        relative-TSR benchmark is the S&P 500 index - index-only,
        UNSTORED; ASX peer group given less weight, unnamed companies
        - UNSTORED; no marks (all Health Care))
  TDY   16 -> 16 (DEF 14A 2026-03-12; "peer group ... for 2025 pay
        decisions", verbatim (16), last reviewed July 2025; dropped
        GIS + IP queued fabrications; added BRKR + ZBRA; ZBRA<->TDY
        now mutually cited (ZBRA lists TDY; TDY lists Zebra
        Technology Corporation); the pay-vs-performance group is the
        S&P 1500 Industrials index - UNSTORED; the broader general-
        industry survey group is unnamed - UNSTORED; no marks)

No new verified_cross_sector marks this batch: all 12 queued
fingerprint edges were dropped as fabrications; no cross-sector
fingerprint-target edge survived any repair.

New nodes: 8 (NSIT, HR, OHI, WPC, AMRC, ARRY, AGR, ENS) - registered in
PEER_ONLY_NODES and in mark_verified_cross_sector REPAIR_SCRIPTS BEFORE
the repair ran (the batch-5 / batch-8h lessons held).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'NSIT': ('Insight Enterprises, Inc.', 'Information Technology'),
    'HR': ('Healthcare Realty Trust Incorporated', 'Real Estate'),
    'OHI': ('Omega Healthcare Investors, Inc.', 'Real Estate'),
    'WPC': ('W.P. Carey Inc.', 'Real Estate'),
    'AMRC': ('Ameresco, Inc.', 'Industrials'),
    'ARRY': ('Array Technologies, Inc.', 'Industrials'),
    'AGR': ('Avangrid, Inc.', 'Utilities'),
    'ENS': ('EnerSys', 'Industrials'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'ZBRA': ('DEF 14A 2026-04-03',
             ['MSI', 'NSIT', 'ROK', 'A', 'NTAP', 'ANET', 'ADSK', 'TDY',
              'JNPR', 'KEYS', 'CDNS', 'CIEN', 'AKAM', 'TRMB', 'VNT',
              'FFIV', 'TER']),
    'DOC': ('DEF 14A 2026-03-12',
            ['ARE', 'AVB', 'BXP', 'EQR', 'HR', 'HST', 'KIM', 'OHI', 'O',
             'REG', 'UDR', 'VTR', 'WELL', 'WPC']),
    'FSLR': ('DEF 14A 2026-04-02',
             ['AMRC', 'AMKR', 'ADI', 'ARRY', 'AGR', 'CRUS', 'DIOD', 'ENS',
              'ENPH', 'ENTG', 'GNRC', 'KLAC', 'LRCX', 'MRVL', 'MCHP',
              'MKSI', 'MPWR', 'NEE', 'NXT', 'ON', 'PNW', 'QRVO', 'SWKS',
              'RUN', 'TER', 'AES', 'XEL']),
    'GD': ('DEF 14A 2026-03-27',
           ['MMM', 'ACN', 'BA', 'CAT', 'CSCO', 'DE', 'ETN', 'EMR', 'HON',
            'JCI', 'LMT', 'NOC', 'RTX', 'TXT']),
    'RMD': ('DEF 14A 2026-10-01',
            ['A', 'IDXX', 'ALGN', 'ILMN', 'BAX', 'ISRG', 'BIO', 'IQV',
             'BSX', 'MTD', 'CRL', 'RVTY', 'COO', 'STE', 'DXCM', 'TFX',
             'EW', 'WAT', 'HOLX']),
    'TDY': ('DEF 14A 2026-03-12',
            ['A', 'AME', 'BRKR', 'FTV', 'GRMN', 'HWM', 'IEX', 'KEYS',
             'MTD', 'RVTY', 'TER', 'TDG', 'TRMB', 'WAT', 'XYL', 'ZBRA']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-02 22:05 PT from peer-network.json (923 nodes / 7,046 edges).
EXPECTED_OLD = {
    'ZBRA': ['A', 'ADSK', 'AKAM', 'ANET', 'CDNS', 'COF', 'GIS', 'JNPR',
             'KEYS', 'KLAC', 'MSI', 'NOW', 'NTAP', 'ROK', 'TDY', 'TER',
             'TRMB'],
    'DOC': ['ARE', 'AVB', 'AWK', 'BXP', 'COF', 'EQR', 'GIS', 'HST', 'KEY',
            'KIM', 'O', 'REG', 'SPGI', 'UDR', 'VTR', 'WELL'],
    'FSLR': ['ADI', 'BLK', 'COF', 'ENPH', 'GNRC', 'KLAC', 'LRCX', 'MCHP',
             'MPWR', 'MRVL', 'NEE', 'ON', 'PNW', 'SWKS', 'TER', 'XEL'],
    'GD': ['ACN', 'AON', 'BA', 'CAT', 'COF', 'CSCO', 'DE', 'EMR', 'ETN',
           'HON', 'IP', 'JCI', 'LMT', 'NOC', 'RTX', 'TXT'],
    'RMD': ['A', 'ABBV', 'ALGN', 'BAX', 'CRL', 'DXCM', 'EW', 'GIS',
            'HOLX', 'IDXX', 'IP', 'ISRG', 'MTD', 'RVTY', 'STE', 'WAT'],
    'TDY': ['A', 'AME', 'FTV', 'GIS', 'GRMN', 'HWM', 'IEX', 'IP', 'KEYS',
            'MTD', 'RVTY', 'TDG', 'TER', 'TRMB', 'WAT', 'XYL'],
}

# No new verified_cross_sector marks: all 12 queued fingerprint edges
# were dropped as fabrications; no cross-sector fingerprint-target edge
# survived any of the six repairs.
NEW_MARKS = []


def main():
    bak = SRC.replace('.json', '_backup_20261002_2200_pre_batch8n.json')
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
