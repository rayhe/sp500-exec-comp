#!/usr/bin/env python3
"""Peer-network batch-3 fingerprint repair (2026-09-30 22:00 PT run).

Replaces 21 sweep-invisible garbage parses (the n=1/n=2/n=3 extractor
false-positive class) with real CD&A compensation peer groups transcribed
verbatim from each company's latest DEF 14A. Old edge sets show the
documented false-positive fingerprints: GIS (15 sources), COF (10), PFG,
BLK, STT, CHTR, NDAQ, PSA, WM, KMI, IP, TGT, FRT as absurd cross-sector
targets (e.g. CLX->BLK/STT, IBM->PSA/COF, ALGN->COF, AMZN->GIS where
'General Mills' appears ZERO times in Amazon's proxy).

Extraction by two subagent workers + parent AMZN check; evidence files in
/tmp/peersweep/batch3/<TICKER>_peer.txt (copied to goal
hidden_files/thinedge-repair-20260930/).

Repairs (17 sources):
  AKAM GIS -> 19 benchmarking peers (DEF 14A 2026-03-31; image-transcribed)
  LUV  GIS -> 5 airlines (DEF 14A 2026-03-27)
  MCHP WM  -> 16 Semler Brossy peers (DEF 14A 2026-07-06)
  PPL  PFG -> 16 utilities (DEF 14A 2026-04-01; image-transcribed)
  EXR  COF -> 18 comparator cos (DEF 14A 2026-04-01; AVB/EQR delisted ->
               merged Vivmark Residential Aug 2026, kept under last ticker)
  PGR  COF -> 15 (16 named incl. self; DEF 14A 2026-03-23)
  ALGN COF/PODD/ZBH -> 19 Performance Peers (DEF 14A 2026-04-07; HOLX, MASI
               delisted -> kept under last ticker)
  ANET BLK/GIS -> 15 FY2025 peers (DEF 14A 2026-04-16)
  AXON CHTR/NDAQ -> 19 (DEF 14A 2026-04-16; ANSS, AZPN delisted -> kept)
  AXP  PEP/FRT/CRM -> 21 (DEF 14A 2026-03-25; BNY per current roster)
  CBRE TGT/IP -> 15 (DEF 14A 2026-04-03; MRSH per roster)
  DVA  TGT/GIS/LH -> 17 (DEF 14A 2026-04-22; HOLX, SEM delisted -> kept)
  ELV  COF/PSA -> 5 Direct Industry Group (DEF 14A 2026-03-27; 48-company
               General Industry Group is secondary, unstored)
  EQIX PRU/PFG -> 21 (DEF 14A 2026-04-02; XYZ per roster; EA taken private
               -> kept under last ticker)
  IBM  PSA/COF -> 22 benchmark group (DEF 14A 2026-03-10)
  LDOS COF/GIS/PFG -> 14 (DEF 14A 2026-03-19)
  MGM  COF/GIS -> 17 (DEF 14A 2026-03-27)

No named comp peer group (TSLA/CTAS precedent: delete edges, isSource off):
  NRG  (DEF 14A 2026-03-18: unnamed survey data only)
  L    (DEF 14A 2026-04-01: only named list is the PvP TSR group)
  CLX  (DEF 14A 2025-10-07: 'peer group of consumer products companies',
        zero named companies anywhere in the filing)
  AMZN (DEF 14A 2026-04-09: illustrative 'such as' survey list only;
        'General Mills' x0 in filing -> AMZN->GIS pure fabrication)

New peer-only nodes (26): ACM, ALK, ALRM, AZPN, BAH, CACI, CUBE, EHC, FLR,
HEI, IOT, JBLU, JLL, KBR, KD, MASI, OTEX, PCOR, PCTY, PENN, SAIC, SEM, SUI,
TFX, THC, XRAY.
"""
import json, shutil

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, [peer tickers in filing order])
NEW = {
    'AKAM': ('DEF 14A 2026-03-31',
             ['ADSK', 'CIEN', 'CRWD', 'DT', 'FFIV', 'FTNT', 'GEN', 'HUBS',
              'PPLI', 'JNPR', 'NTNX', 'OKTA', 'PANW', 'PTC', 'VRSN', 'NET',
              'OTEX', 'TWLO', 'ZS']),
    'LUV': ('DEF 14A 2026-03-27', ['AAL', 'DAL', 'UAL', 'ALK', 'JBLU']),
    'MCHP': ('DEF 14A 2026-07-06',
             ['AMKR', 'GDDY', 'MPWR', 'SWKS', 'ADI', 'KLAC', 'NXPI', 'TER',
              'FSLR', 'MRVL', 'ON', 'TXN', 'GEN', 'MKSI', 'QRVO', 'WDC']),
    'PPL': ('DEF 14A 2026-04-01',
            ['LNT', 'AEE', 'AEP', 'CNP', 'CMS', 'ED', 'D', 'ETR', 'EVRG',
             'ES', 'FE', 'NI', 'PEG', 'SRE', 'WEC', 'XEL']),
    'EXR': ('DEF 14A 2026-04-01',
            ['AVB', 'EQR', 'SBAC', 'BXP', 'ESS', 'SPG', 'CMG', 'HLT', 'SUI',
             'CCI', 'INVH', 'WELL', 'CUBE', 'MAA', 'DLR', 'PSA', 'EQIX',
             'O']),
    'PGR': ('DEF 14A 2026-03-23',
            ['ELV', 'CNC', 'HUM', 'BAC', 'WFC', 'C', 'MET', 'PRU', 'AXP',
             'ALL', 'CB', 'TRV', 'MOH', 'COF', 'AIG']),
    'ALGN': ('DEF 14A 2026-04-07',
             ['A', 'HOLX', 'RVTY', 'AVTR', 'IDXX', 'STE', 'BIO', 'ILMN',
              'TFX', 'XRAY', 'PODD', 'COO', 'DXCM', 'MASI', 'WAT', 'EW',
              'MTD', 'ZBH', 'RMD']),
    'ANET': ('DEF 14A 2026-04-16',
             ['AKAM', 'CRWD', 'ISRG', 'SNPS', 'ADSK', 'DLR', 'NTAP', 'WDAY',
              'CDNS', 'EQIX', 'PANW', 'ZS', 'CIEN', 'FTNT', 'NOW']),
    'AXON': ('DEF 14A 2026-04-16',
             ['ALRM', 'FICO', 'PCOR', 'ANSS', 'HEI', 'PTC', 'AZPN', 'HUBS',
              'IOT', 'CRWD', 'MDB', 'TYL', 'DDOG', 'PLTR', 'ZS', 'DT',
              'PAYC', 'ESTC', 'PCTY']),
    'AXP': ('DEF 14A 2026-03-25',
            ['BAC', 'BNY', 'BLK', 'COF', 'C', 'GS', 'JPM', 'MS', 'USB',
             'WFC', 'NKE', 'PEP', 'SBUX', 'UBER', 'VZ', 'ADBE', 'IBM', 'MA',
             'PYPL', 'CRM', 'V']),
    'CBRE': ('DEF 14A 2026-04-03',
             ['ACN', 'FIS', 'J', 'ACM', 'FISV', 'JLL', 'AON', 'FLR', 'MRSH',
              'ADP', 'HPE', 'BNY', 'CTSH', 'IBM', 'WTW']),
    'DVA': ('DEF 14A 2026-04-22',
            ['AVTR', 'HSIC', 'RVTY', 'BAX', 'HOLX', 'SEM', 'CNC', 'IQV',
             'THC', 'XRAY', 'LH', 'UHS', 'EHC', 'MOH', 'ZBH', 'HCA',
             'DGX']),
    'ELV': ('DEF 14A 2026-03-27', ['CNC', 'CVS', 'HUM', 'CI', 'UNH']),
    'EQIX': ('DEF 14A 2026-04-02',
             ['ADBE', 'AKAM', 'ANET', 'ADSK', 'XYZ', 'CDNS', 'NET', 'EBAY',
              'EA', 'FTNT', 'INTU', 'PANW', 'PYPL', 'CRM', 'NOW', 'SNPS',
              'WDAY', 'AMT', 'CCI', 'DLR', 'PLD']),
    'IBM': ('DEF 14A 2026-03-10',
            ['ACN', 'BA', 'INTC', 'CRM', 'ADBE', 'AVGO', 'MSFT', 'UPS',
             'GOOGL', 'CSCO', 'ORCL', 'VZ', 'AMZN', 'ELV', 'PEP', 'V', 'T',
             'HPE', 'QCOM', 'BAC', 'HON', 'RTX']),
    'LDOS': ('DEF 14A 2026-03-19',
             ['ACM', 'BAH', 'CACI', 'GIB', 'CTSH', 'FLR', 'HII', 'J', 'KBR',
              'KD', 'LHX', 'NOC', 'SAIC', 'TXT']),
    'MGM': ('DEF 14A 2026-03-27',
            ['SBUX', 'MCD', 'DRI', 'CCL', 'HLT', 'RCL', 'MAR', 'CMG', 'LYV',
             'YUM', 'LVS', 'CZR', 'QSR', 'NCLH', 'WYNN', 'PENN', 'DKNG']),
}

EXPECTED_OLD = {
    'AKAM': ['GIS'], 'ALGN': ['COF', 'PODD', 'ZBH'], 'ANET': ['BLK', 'GIS'],
    'AXON': ['CHTR', 'NDAQ'], 'AXP': ['CRM', 'FRT', 'PEP'],
    'CBRE': ['IP', 'TGT'], 'DVA': ['GIS', 'LH', 'TGT'],
    'ELV': ['COF', 'PSA'], 'EQIX': ['PFG', 'PRU'], 'EXR': ['COF'],
    'IBM': ['COF', 'PSA'], 'LDOS': ['COF', 'GIS', 'PFG'], 'LUV': ['GIS'],
    'MCHP': ['WM'], 'MGM': ['COF', 'GIS'], 'PGR': ['COF'], 'PPL': ['PFG'],
    'NRG': ['GIS'], 'L': ['KMI'], 'CLX': ['BLK', 'STT'],
    'AMZN': ['GIS', 'GOOGL'],
}

NO_GROUP = ['NRG', 'L', 'CLX', 'AMZN']  # delete edges, isSource -> False

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'ACM': ('AECOM', 'Industrials'),
    'ALK': ('Alaska Air Group, Inc.', 'Consumer Discretionary'),
    'ALRM': ('Alarm.com Holdings, Inc.', 'Information Technology'),
    'AZPN': ('Aspen Technology, Inc.', 'Information Technology'),
    'BAH': ('Booz Allen Hamilton Holding Corp', 'Industrials'),
    'CACI': ('CACI International Inc', 'Industrials'),
    'CUBE': ('CubeSmart', 'Real Estate'),
    'EHC': ('Encompass Health Corp', 'Health Care'),
    'FLR': ('Fluor Corp', 'Industrials'),
    'HEI': ('HEICO Corp', 'Industrials'),
    'IOT': ('Samsara Inc.', 'Information Technology'),
    'JBLU': ('JetBlue Airways Corp', 'Consumer Discretionary'),
    'JLL': ('Jones Lang LaSalle Inc', 'Industrials'),
    'KBR': ('KBR, Inc.', 'Industrials'),
    'KD': ('Kyndryl Holdings, Inc.', 'Information Technology'),
    'MASI': ('Masimo Corp', 'Health Care'),
    'OTEX': ('Open Text Corp', 'Information Technology'),
    'PCOR': ('Procore Technologies, Inc.', 'Information Technology'),
    'PCTY': ('Paylocity Holding Corp', 'Information Technology'),
    'PENN': ('Penn Entertainment, Inc.', 'Consumer Discretionary'),
    'SAIC': ('Science Applications International Corp', 'Industrials'),
    'SEM': ('Select Medical Holdings Corp', 'Health Care'),
    'SUI': ('Sun Communities Inc', 'Real Estate'),
    'TFX': ('Teleflex Inc', 'Health Care'),
    'THC': ('Tenet Healthcare Corp', 'Health Care'),
    'XRAY': ('Dentsply Sirona Inc.', 'Health Care'),
}


def main():
    bak = SRC.replace('.json', '_backup_20260930_2200_pre_batch3.json')
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

    # 2. assert + replace edges for the 17 repaired sources
    for src, (filing, peers) in NEW.items():
        assert src in by_ticker, f'{src}: not a node'
        for t in peers:
            assert t in by_ticker, f'{src}: unknown target {t}'
        assert src != peers and src not in peers, f'{src}: self-edge'
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

    # 3. no-named-group sources: delete edges, isSource off
    for src in NO_GROUP:
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        assert old_targets == sorted(EXPECTED_OLD[src]), \
            f'{src}: old edge set changed: {old_targets}'
        edges = [e for e in edges if e['source'] != src]
        by_ticker[src]['isSource'] = False
        print(f'{src}: {len(old)} edges deleted, isSource -> False')

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
    # isSource sanity: sources with edges must be isSource, none with
    # isSource False may hold edges
    for x in nodes:
        od = outdeg.get(x['ticker'], 0)
        if od > 0:
            assert x.get('isSource') is True, f"{x['ticker']}: edges but not isSource"
        if x.get('isSource') is False:
            assert od == 0, f"{x['ticker']}: isSource False but has edges"

    # 5. metadata from actuals
    net['edges'] = edges
    nsrc = sum(1 for x in nodes if x.get('isSource') is True)
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-09-30'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'
    print('sources:', nsrc)

    with open(SRC, 'w') as f:
        json.dump(net, f, indent=1)
    print('wrote', SRC, '| nodes:', len(nodes), '| edges:', len(edges))


if __name__ == '__main__':
    main()
