#!/usr/bin/env python3
"""Peer-network batch-4 GIS-fingerprint repair (2026-10-01 run).

Follow-up to the 2026-09-30 22:00 PT batch-3 run. During this run's
verification of batch-3's "GIS appears as a target 0 times among sources"
claim, the full-universe count showed 173 sources citing GIS (and 91 citing
COF) -- the batch-3 scan only covered thin sources, so the claim was false
and is corrected in the iteration log. This batch repairs the 15 worst
remaining offenders: mega-caps and thin sources whose stored edge sets are
entirely extractor-fabricated (e.g. AAPL's VZ/MA/ABBV/UNH/SBUX/GIS, QCOM's
GIS/CHTR/COF/IBM, LIN's GIS/IP/COF), replaced with verbatim CD&A peer groups
transcribed from each company's latest DEF 14A.

Extraction by two subagent workers; evidence files in
/tmp/peersweep/batch4/<TICKER>_peer.txt (copied to goal
hidden_files/peer-batch4-20261001/).

Repairs (15 sources):
  AAPL 6 -> 19 (DEF 14A 2026-01-08; "2025 Primary Peer Group")
  META 2 -> 15 (DEF 14A 2026-04-16; Peer Group, Q2-2024 approved)
  MSFT 5 -> 13 (DEF 14A 2025-10-21; Primary Technology group; 11-company
        Secondary General Industry group unstored per ELV precedent)
  CVX  5 -> 8  (DEF 14A 2026-04-07; Oil Industry Peer Group, image-transcribed;
        14-company Non-Oil group unstored per ELV precedent; Hess removed
        post-acquisition, Occidental added)
  VZ   5 -> 26 (DEF 14A 2026-04-06; comp peer group)
  QCOM 4 -> 20 (DEF 14A 2026-01-22; Figure 12, market-cap order)
  MU   3 -> 16 (DEF 14A 2025-11-25; image-transcribed)
  LIN  3 -> 25 (DEF 14A 2026-04-29; image-transcribed; Roche/RHHBY skipped,
        OTC only, no US ticker, per LULU/TPL convention)
  TRV  2 -> 13 (DEF 14A 2026-04-07; "Compensation Comparison Group")
  BLK  3 -> 17 (DEF 14A 2026-04-10; disclosed peer group stored as the named
        comp group; filing notes no formal benchmarking, documented)
  KEYS 2 -> 27 (DEF 14A 2026-01-26; "Compensation Benchmarking Peer Group")
  INCY 2 -> 14 (DEF 14A 2026-04-28; revenue-sorted comparison table)
  APO  1 -> 10 (DEF 14A 2026-04-24; verbatim inline sentence)
  KO   4 -> 16 (DEF 14A 2026-03-16; 2025 Compensation Comparator Group per
        decisions-disclosed convention; 2026 variant documented, queued;
        Danone/Nestle skipped, no US ticker; Unilever PLC node created)
  MPC  4 -> 23 (DEF 14A 2026-03-16; "2025 Compensation Reference Group";
        named Performance Peer Group is TSR/FCF-only, unstored)

New peer-only nodes (17): ARES, ARGX, BAM, BP, BUD, CG, EXEL, GMAB, LNC,
NTRA, OWL, PTCT, SHEL, ST, TPG, UL, UTHR. Foreign-with-US-ticker convention:
peer-only node created (SAP/OTEX/GIB/LYB/BG line); foreign without a US
ticker skipped (LULU/TPL line: RHHBY, Danone, Nestle). The MS/BAC bank-ADR
skips are noted as the minority deviation.
"""
import json
import shutil

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, [peer tickers in filing order])
NEW = {
    'AAPL': ('DEF 14A 2026-01-08',
             ['GOOGL', 'CSCO', 'MA', 'NVDA', 'VZ', 'AMZN', 'CMCSA', 'META',
              'ORCL', 'V', 'T', 'DIS', 'MSFT', 'QCOM', 'WBD', 'AVGO', 'INTC',
              'NFLX', 'CRM']),
    'META': ('DEF 14A 2026-04-16',
             ['GOOGL', 'NVDA', 'AMZN', 'ORCL', 'AAPL', 'CRM', 'T', 'DIS',
              'CSCO', 'UBER', 'CMCSA', 'VZ', 'MSFT', 'V', 'NFLX']),
    'MSFT': ('DEF 14A 2025-10-21',
             ['ADBE', 'GOOGL', 'AMZN', 'AAPL', 'AVGO', 'CSCO', 'IBM', 'INTC',
              'META', 'NVDA', 'ORCL', 'QCOM', 'CRM']),
    'CVX': ('DEF 14A 2026-04-07',
            ['XOM', 'SHEL', 'COP', 'BP', 'PSX', 'VLO', 'MPC', 'OXY']),
    'VZ': ('DEF 14A 2026-04-06',
           ['GOOGL', 'CSCO', 'MSFT', 'AMZN', 'CMCSA', 'NFLX', 'AXP', 'GS',
            'NVDA', 'AAPL', 'HD', 'PG', 'T', 'IBM', 'TMUS', 'BA', 'JNJ',
            'UNH', 'CAT', 'JPM', 'WMT', 'CHTR', 'MRK', 'DIS', 'CVX', 'META']),
    'QCOM': ('DEF 14A 2026-01-22',
             ['NVDA', 'AVGO', 'V', 'ORCL', 'AMD', 'NFLX', 'ADBE', 'ACN',
              'CSCO', 'TMUS', 'INTC', 'INTU', 'IBM', 'AMAT', 'TXN', 'MU',
              'LRCX', 'ADI', 'PYPL', 'NXPI']),
    'MU': ('DEF 14A 2025-11-25',
           ['ADBE', 'ADI', 'AVGO', 'HPE', 'INTC', 'NVDA', 'CRM', 'TXN', 'AMD',
            'AMAT', 'CSCO', 'IBM', 'LRCX', 'QCOM', 'STX', 'WDC']),
    'LIN': ('DEF 14A 2026-04-29',
            ['MMM', 'CAT', 'DE', 'HON', 'MDT', 'PPG', 'SHW', 'BUD', 'KO',
             'ETN', 'JCI', 'MRK', 'TMO', 'ABBV', 'CMI', 'GILD', 'KHC', 'MU',
             'RTX', 'ABT', 'DHR', 'HAL', 'LYB', 'MDLZ', 'SAP']),
    'TRV': ('DEF 14A 2026-04-07',
            ['AIG', 'ALL', 'CB', 'HIG', 'PGR', 'AFL', 'AXP', 'BNY', 'HUM',
             'LNC', 'MRSH', 'MET', 'PRU']),
    'BLK': ('DEF 14A 2026-04-10',
            ['AMP', 'BNY', 'SCHW', 'BEN', 'GS', 'MS', 'NTRS', 'STT', 'TROW',
             'APO', 'BX', 'KKR', 'AXP', 'FISV', 'MA', 'PYPL', 'RJF']),
    'KEYS': ('DEF 14A 2026-01-26',
             ['A', 'FFIV', 'JNPR', 'ROP', 'TRMB', 'AME', 'FTNT', 'KLAC', 'ST',
              'WDAY', 'ANET', 'FTV', 'MSI', 'SSNC', 'ZBRA', 'ADSK', 'GEN',
              'NTAP', 'SNPS', 'CDNS', 'HUBB', 'PANW', 'TDY', 'CIEN', 'INTU',
              'ROK', 'TER']),
    'INCY': ('DEF 14A 2026-04-28',
             ['BIIB', 'ONC', 'ILMN', 'JAZZ', 'ARGX', 'GMAB', 'ALNY', 'BMRN',
              'UTHR', 'NBIX', 'EXEL', 'NTRA', 'MRNA', 'PTCT']),
    'APO': ('DEF 14A 2026-04-24',
            ['ARES', 'BLK', 'BX', 'OWL', 'BAM', 'CG', 'GS', 'KKR', 'MS',
             'TPG']),
    'KO': ('DEF 14A 2026-03-16',
           ['ABT', 'ADM', 'CL', 'INTC', 'JNJ', 'KMB', 'KHC', 'MCD', 'MDLZ',
            'NKE', 'PEP', 'PFE', 'PM', 'PG', 'SBUX', 'UL']),
    'MPC': ('DEF 14A 2026-03-16',
            ['MMM', 'ADM', 'BG', 'CAT', 'COR', 'COP', 'CMI', 'DOW', 'DD',
             'EOG', 'FDX', 'F', 'GD', 'GM', 'HON', 'LMT', 'LYB', 'MCK',
             'PSX', 'PPG', 'RTX', 'UPS', 'VLO']),
}

EXPECTED_OLD = {
    'AAPL': ['ABBV', 'GIS', 'MA', 'SBUX', 'UNH', 'VZ'],
    'META': ['DIS', 'VZ'],
    'MSFT': ['ACN', 'BLK', 'CRM', 'NDAQ', 'T'],
    'CVX': ['BLK', 'BRK-B', 'HES', 'RSG', 'STT'],
    'VZ': ['CHTR', 'DIS', 'JPM', 'MSFT', 'UNH'],
    'QCOM': ['CHTR', 'COF', 'GIS', 'IBM'],
    'MU': ['CHTR', 'GIS', 'RTX'],
    'LIN': ['COF', 'GIS', 'IP'],
    'TRV': ['COF', 'GIS'],
    'BLK': ['BX', 'KKR', 'STT'],
    'KEYS': ['COF', 'TDY'],
    'INCY': ['CHTR', 'GPN'],
    'APO': ['PFG'],
    'KO': ['CHTR', 'ED', 'GIS', 'MS'],
    'MPC': ['CVX', 'TGT', 'VLO', 'XOM'],
}

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'ARES': ('Ares Management Corp', 'Financials'),
    'ARGX': ('ARGENX SE', 'Health Care'),
    'BAM': ('Brookfield Asset Management Ltd.', 'Financials'),
    'BP': ('BP PLC', 'Energy'),
    'BUD': ('Anheuser-Busch InBev SA/NV', 'Consumer Staples'),
    'CG': ('Carlyle Group Inc.', 'Financials'),
    'EXEL': ('EXELIXIS, INC.', 'Health Care'),
    'GMAB': ('GENMAB A/S', 'Health Care'),
    'LNC': ('LINCOLN NATIONAL CORP', 'Financials'),
    'NTRA': ('Natera, Inc.', 'Health Care'),
    'OWL': ('BLUE OWL CAPITAL INC.', 'Financials'),
    'PTCT': ('PTC THERAPEUTICS, INC.', 'Health Care'),
    'SHEL': ('Shell plc', 'Energy'),
    'ST': ('Sensata Technologies Holding plc', 'Industrials'),
    'TPG': ('TPG Inc.', 'Financials'),
    'UL': ('UNILEVER PLC', 'Consumer Staples'),
    'UTHR': ('UNITED THERAPEUTICS Corp', 'Health Care'),
}


def main():
    bak = SRC.replace('.json', '_backup_20261001_0330_pre_batch4.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}

    # 1. create new peer-only nodes (before edge validation so targets exist)
    for t, (name, sector) in sorted(NEW_NODES.items()):
        assert t not in by_ticker, f'{t}: node already exists'
        n = {'ticker': t, 'name': name, 'sector': sector,
             'in_degree': 0, 'out_degree': 0, 'market_cap_tier': 'large'}
        nodes.append(n)
        by_ticker[t] = n
    print('new peer-only nodes:', len(NEW_NODES))

    # 2. assert + replace edges for the 15 repaired sources
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
    # isSource sanity: sources with edges must be isSource, none with
    # isSource False may hold edges
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
    print('sources:', nsrc)

    with open(SRC, 'w') as f:
        json.dump(net, f, indent=1)
    print('wrote', SRC, '| nodes:', len(nodes), '| edges:', len(edges))


if __name__ == '__main__':
    main()
