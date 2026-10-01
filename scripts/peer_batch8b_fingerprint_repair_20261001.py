#!/usr/bin/env python3
"""Peer-network batch-8b fingerprint-queue repair (2026-10-01 run).

Follow-up to the 2026-10-01 batch-8a run. The Section-19 fingerprint queue
listed 373 cross-sector fingerprint-target edges across 228 sources; the
heaviest remaining tier is 27 sources with exactly 3 queued edges each.
Batch-8b takes the 6 heaviest by total outbound edge count (CMS/NEE/NEM/
PFE/V/IQV) and re-extracts each source's comp-decisions peer group VERBATIM
from its latest DEF 14A, keeping only edges that match the verbatim group.
TSR/PSU comparator groups and explicitly-excluded reference groups are
unstored per the batches 3-7 convention.

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession, filing HTML fetched
with User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)", peer sections
transcribed verbatim. Evidence in /tmp/peersweep/batch8b/<TICKER>_peer.txt
(copied to goal hidden_files/peer-batch8b-20261001/).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  CMS  34 -> 19 (DEF 14A 2026-03-26; 2025 Compensation Peer Group, 19
        cos, Evergy added vs 2024; Performance Peer Group is the TSR/EPS
        comparator -> unstored per convention; queued COF/IP/PSA all
        dropped)
  NEE  33 -> 33 (DEF 14A 2026-04-01; UNION of 13-co Energy Services and
        20-co General Industry groups - BOTH feed 2025 target-TDC
        decisions (FE precedent); queued GIS/IP/PSA all dropped;
        added EIX/MMM/SLB/SRE)
  NEM  30 -> 25 (DEF 14A 2026-03-26; 2025 Compensation Peer Group, 2026
        group unchanged per filing; TSR Peer Group (GDX + S&P 500)
        unstored; queued CHTR/PSA/WM all dropped; added CE/COP/DD/OVV/B.
        B = Barrick Gold Corporation per the filing's own "(B)" - see
        the ticker-slot adjudication below.)
  PFE  28 -> 31 (DEF 14A 2026-03-12; UNION of 12-co Pharmaceutical Peer
        Group and 20-co General Industry Comparators - both feed the
        annual benchmarking (FE precedent); Roche skipped (OTC RHHBY,
        per RHHBY precedent); AZN/GSK/NVS/SNY kept (NYSE/Nasdaq ADRs,
        peer-only nodes already exist); XOM/UNH removed and DHR/MDT/TMO
        added per the filing's own 2026 update note; GENUINE KEEPS:
        CVX, PG (filing-verbatim cross-sector))
  V    25 -> 21 (DEF 14A 2025-12-08; 2025 peer group, 21 cos; the 2026
        Block->Uber variant is documented but NOT stored (HPQ/GDDY
        precedent - queued for the FY2026 cycle); GENUINE KEEP: MSFT;
        dropped GIS/PSA + EA/MSCI/UBER fabrications; added MS)
  IQV  25 -> 22 (DEF 14A 2026-02-27; 2025 Compensation Peer Group, 22
        cos, no 2025 changes; cross-checked against the pay-vs-
        performance footnote list; queued CHTR/COF/PSA all dropped;
        added LH/AVTR/ICLR/BMY)

TICKER-SLOT ADJUDICATION (first of its kind): batch-6 created node B as
"Barnes Group Inc." (Industrials, delisted Jan 2025) from NDSN's name-only
"Barnes Group Inc" filing mention - the B mapping was inference, not
verbatim. NYSE:B has been live-held by Barrick Mining Corporation
(formerly Barrick Gold Corporation) since 2025-05-09 (verified this run
via web search: name/symbol/CUSIP change effective May 9, 2025), and
NEM's 2026-03-26 DEF 14A lists "Barrick Gold Corporation (B)"
filing-verbatim. Rule established: on ticker-slot collision the LIVE
holder wins. Node B is renamed to Barrick Mining Corporation (Materials);
NDSN's inferred Barnes edge is dropped (NDSN 22 -> 21) with the verbatim
evidence retained in goal hidden_files/peer-batch6-20261001/NDSN_peer.txt.
"""
import json
import shutil

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, [peer tickers in filing order])
NEW = {
    'CMS': ('DEF 14A 2026-03-26',
            ['LNT', 'ETR', 'PPL', 'AEE', 'EVRG', 'PEG', 'ATO', 'ES',
             'SRE', 'CNP', 'HE', 'WEC', 'ED', 'NI', 'XEL', 'DTE',
             'OGE', 'EIX', 'PNW']),
    'NEE': ('DEF 14A 2026-04-01',
            ['AEP', 'ED', 'D', 'DUK', 'EIX', 'ETR', 'EXC', 'FE', 'PPL',
             'PEG', 'SRE', 'SO', 'XEL', 'MMM', 'GD', 'APD', 'HAL',
             'CAT', 'HON', 'CI', 'ITW', 'DHR', 'MRSH', 'DE', 'NOC',
             'DVN', 'SLB', 'DD', 'TXN', 'ETN', 'TMO', 'EMR', 'UNP']),
    'NEM': ('DEF 14A 2026-03-26',
            ['APD', 'EOG', 'AME', 'FTV', 'BKR', 'FCX', 'B', 'HAL',
             'CARR', 'ITW', 'CE', 'IR', 'COP', 'JCI', 'CTVA', 'OVV',
             'CMI', 'PH', 'DD', 'PPG', 'ETN', 'ROK', 'ECL', 'WAB',
             'EMR']),
    'PFE': ('DEF 14A 2026-03-12',
            ['ABBV', 'AMGN', 'AZN', 'BMY', 'LLY', 'GILD', 'GSK', 'JNJ',
             'MRK', 'NVS', 'SNY', 'MMM', 'ABT', 'BA', 'CAT', 'CVX',
             'KO', 'CMCSA', 'COP', 'DHR', 'HON', 'IBM', 'LMT', 'MDT',
             'MDLZ', 'PEP', 'PG', 'RTX', 'TMO', 'UPS', 'VZ']),
    'V': ('DEF 14A 2025-12-08',
          ['AXP', 'COF', 'MA', 'PYPL', 'BAC', 'BLK', 'C', 'JPM', 'MS',
           'GS', 'WFC', 'ACN', 'ADBE', 'GOOGL', 'XYZ', 'IBM', 'INTU',
           'META', 'MSFT', 'ORCL', 'CRM']),
    'IQV': ('DEF 14A 2026-02-27',
            ['ABBV', 'AMGN', 'BIIB', 'GILD', 'MRNA', 'REGN', 'VRTX',
             'LH', 'ACN', 'CTSH', 'IT', 'IBM', 'A', 'AVTR', 'DHR',
             'ICLR', 'TMO', 'BMY', 'LLY', 'MRK', 'PFE', 'ZTS']),
}

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'HE': ('Hawaiian Electric Industries Inc', 'Utilities'),
    'ICLR': ('ICON plc', 'Health Care'),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-01 15:30 PT from peer-network.json (868 nodes / 7,196 edges)
EXPECTED_OLD = {
    'CMS': ['AEE', 'AEP', 'ATO', 'AWK', 'CEG', 'CNP', 'COF', 'D',
            'DTE', 'DUK', 'ED', 'EIX', 'ES', 'ETR', 'EVRG', 'EXC',
            'FE', 'GE', 'IP', 'LNT', 'LUV', 'NEE', 'NI', 'PCG',
            'PEG', 'PNW', 'PPL', 'PSA', 'SO', 'UHS', 'VST', 'WDC',
            'WEC', 'XEL'],
    'NEE': ['AEP', 'APD', 'AWK', 'CAT', 'CI', 'D', 'DD', 'DE', 'DHR',
            'DUK', 'DVN', 'ED', 'EMR', 'ETN', 'ETR', 'EXC', 'FE',
            'GD', 'GIS', 'HAL', 'HON', 'IP', 'ITW', 'MRSH', 'NOC',
            'PEG', 'PPL', 'PSA', 'SO', 'TMO', 'TXN', 'UNP', 'XEL'],
    'NEM': ['AME', 'APD', 'AWK', 'BKR', 'CARR', 'CHTR', 'CMI',
            'CTVA', 'DE', 'ECL', 'EMR', 'EOG', 'ETN', 'FCX', 'FTV',
            'HAL', 'HES', 'IP', 'IR', 'ITW', 'JCI', 'NTRS', 'PH',
            'PPG', 'PSA', 'ROK', 'RSG', 'VMC', 'WAB', 'WM'],
    'PFE': ['ABBV', 'ABT', 'AMGN', 'BMY', 'CAT', 'CMCSA', 'COP',
            'CVX', 'DHR', 'GILD', 'GIS', 'HON', 'IBM', 'JNJ', 'KO',
            'LLY', 'LMT', 'MDLZ', 'MDT', 'MRK', 'PEP', 'PG', 'RTX',
            'TMO', 'UNH', 'UPS', 'VZ', 'XOM'],
    'V': ['ACN', 'ADBE', 'AXP', 'BAC', 'BLK', 'C', 'COF', 'CRM',
          'EA', 'GIS', 'GOOGL', 'GS', 'IBM', 'INTU', 'JPM', 'MA',
          'META', 'MSCI', 'MSFT', 'ORCL', 'PSA', 'PYPL', 'UBER',
          'WFC', 'XYZ'],
    'IQV': ['A', 'ABBV', 'ACN', 'AMGN', 'BBY', 'BIIB', 'CARR',
            'CHTR', 'COF', 'CTSH', 'DHR', 'GILD', 'HD', 'IBM', 'IT',
            'KEY', 'LLY', 'MRK', 'MRNA', 'PFE', 'PSA', 'REGN',
            'TMO', 'VRTX', 'ZTS'],
}

# ticker-slot adjudication: NDSN's inferred Barnes edge is dropped
# (B reclaimed by the live holder, Barrick). Expected NDSN old set
# from batch-6 (22 edges).
NDSN_EXPECTED_OLD = ['AEIS', 'AME', 'B', 'CR', 'DCI', 'ENTG', 'GGG',
                     'GTLS', 'ICUI', 'IEX', 'ITGR', 'ITT', 'KEYS',
                     'LECO', 'MKSI', 'MMSI', 'TER', 'TFX', 'TRMB',
                     'VNT', 'WTS', 'WWD']


def main():
    bak = SRC.replace('.json', '_backup_20261001_1530_pre_batch8b.json')
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

    # 2. ticker-slot adjudication: B -> Barrick Mining Corporation
    b = by_ticker['B']
    assert b['name'] == 'Barnes Group Inc.', f"B node changed: {b['name']}"
    assert b['sector'] == 'Industrials'
    b['name'] = 'Barrick Mining Corporation'
    b['sector'] = 'Materials'
    print('B node renamed: Barnes Group Inc. -> Barrick Mining Corporation '
          '(Industrials -> Materials)')

    # 3. drop NDSN's inferred Barnes edge
    assert 'NDSN' in by_ticker, 'NDSN: not a node'
    ndsn_old = sorted(e['target'] for e in edges if e['source'] == 'NDSN')
    assert ndsn_old == sorted(NDSN_EXPECTED_OLD), \
        f'NDSN: old edge set changed: {ndsn_old}'
    edges = [e for e in edges
             if not (e['source'] == 'NDSN' and e['target'] == 'B')]
    print('NDSN: Barnes edge dropped (22 -> 21)')

    # 4. assert + replace edges for the repaired sources
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

    # 5. recompute degrees exactly
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

    # 6. metadata from actuals
    net['edges'] = edges
    nsrc = sum(1 for x in nodes if x.get('isSource') is True)
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-10-01'
    net['metadata']['last_dq_repair'] = '2026-10-01'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'
    print('sources:', nsrc)

    with open(SRC, 'w') as f:
        json.dump(net, f, indent=1)
    print('wrote', SRC, '| nodes:', len(nodes), '| edges:', len(edges))


if __name__ == '__main__':
    main()
