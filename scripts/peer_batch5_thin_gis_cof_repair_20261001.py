#!/usr/bin/env python3
"""Peer-network batch-5 thin GIS/COF-fingerprint repair (2026-10-01 run).

Follow-up to the 2026-10-01 batch-4 run. A full-universe scan found 41
sources whose thin edge sets (<=8 edges) contain GIS and/or COF -- the
extractor-fabrication signature (e.g. WAT [GIS, CRL], DG [SBUX, GIS],
GPC [GIS, FAST, COF, AMAT]). This batch repairs 12 of them (all "large"
tier), replacing the fabricated edge sets with verbatim CD&A peer groups
transcribed from each company's latest DEF 14A (filing dates match the
stored edge metadata, confirming the targets were fabricated from these
exact filings).

Extraction done directly (no subagents): EDGAR submissions JSON for the
latest DEF 14A accession, filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)", peer sections
transcribed verbatim. Evidence in /tmp/peersweep/batch5/<TICKER>_* (copied
to goal hidden_files/peer-batch5-20261001/).

Repairs (12 sources):
  WAT  2 -> 16 (DEF 14A 2026-04-09; FY2025 "Peer Companies"; Catalent
        removed by the company post-acquisition, not stored)
  DG   2 -> 14 (DEF 14A 2026-04-07; 2025 peer group; May-2025 modification
        for 2026 decisions removes WBA+SBUX, adds Albertsons+BJ's --
        documented, queued per KO/decisions-disclosed convention)
  PHM  3 ->  9 (DEF 14A 2026-03-13; comp peer group = Performance Peer
        Group verbatim, filing states they are the same homebuilder set)
  SWKS 3 -> 18 (DEF 14A 2026-04-03; FY25 Peer Group; GlobalFoundries added)
  LEN  4 ->  8 (DEF 14A 2026-02-26; comp Peer Group; Beazer is performance-
        only, not stored)
  MRK  4 -> 11 (DEF 14A 2026-04-08; Primary Peer Group; Roche/RHHBY skipped,
        OTC only, no US ticker, per LULU/TPL convention; supplemental DJIA
        group unstored per ELV precedent)
  EIX  4 -> 20 (DEF 14A 2026-03-13; 2025 Peer Group = PHLX Utility Sector
        Index, all 20 ex-EIX constituents stored)
  TYL  4 -> 13 (DEF 14A 2026-03-23; 2025 Peer Group; ENV (Envestnet, taken
        private Nov 2024) stored verbatim as disclosed)
  GPC  4 -> 24 (DEF 14A 2026-02-27; 2025 Comparison Group; filing prints
        "Avent, Inc." -- no such listed company; presumed typo for Avnet,
        Inc. (AVT), stored as AVT with this note)
  TRMB 5 -> 18 (DEF 14A 2026-04-09; resulting 2025 comp peer group;
        Juniper+Splunk removed post-acquisition, FICO+FTNT+VNT added)
  ODFL 5 -> 15 (DEF 14A 2026-04-20; 2025 Peer Group)
  PCAR 5 ->  7 (DEF 14A 2026-03-18; CD&A "eleven Peer Companies" revenue
        table; Daimler Truck/Iveco/TRATON/Volvo skipped, no US listing,
        per LULU/TPL convention)

New peer-only nodes (34): ACIW, ADNT, AGCO, AIT, AN, ARW, AVT, AZN, BLKB,
BSY, CP, ENV, GSK, HUBG, KBH, LEA, MANH, MHO, MSM, MTH, NVS, OSK, PAG,
PEGA, PFGC, SNY, TEX, TMHC, TOL, TPH, UHAL, USFD, VNT, WCC.
"""
import json
import shutil

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, [peer tickers in filing order])
NEW = {
    'WAT': ('DEF 14A 2026-04-09',
            ['A', 'AVTR', 'BIO', 'TECH', 'CRL', 'COO', 'EW', 'HOLX',
             'IDXX', 'ILMN', 'MTD', 'RMD', 'RVTY', 'STE', 'TFX', 'WST']),
    'DG': ('DEF 14A 2026-04-07',
           ['AZO', 'DLTR', 'ORLY', 'SYY', 'TSCO', 'BBY', 'KR', 'ROST',
            'TGT', 'WBA', 'KMX', 'LOW', 'SBUX', 'TJX']),
    'PHM': ('DEF 14A 2026-03-13',
            ['DHI', 'KBH', 'LEN', 'MTH', 'MHO', 'NVR', 'TMHC', 'TOL',
             'TPH']),
    'SWKS': ('DEF 14A 2026-04-03',
             ['AMD', 'LRCX', 'NXPI', 'TER', 'ADI', 'MRVL', 'ON', 'TXN',
              'ENTG', 'MCHP', 'QRVO', 'WDC', 'GFS', 'MU', 'QCOM',
              'KLAC', 'MPWR', 'STX']),
    'LEN': ('DEF 14A 2026-02-26',
            ['DHI', 'PHM', 'KBH', 'TMHC', 'MTH', 'TOL', 'NVR', 'TPH']),
    'MRK': ('DEF 14A 2026-04-08',
            ['ABBV', 'AMGN', 'AZN', 'BMY', 'LLY', 'GILD', 'GSK', 'JNJ',
             'NVS', 'PFE', 'SNY']),
    'EIX': ('DEF 14A 2026-03-13',
            ['AES', 'AEE', 'AEP', 'AWK', 'CNP', 'ED', 'CEG', 'D', 'DTE',
             'DUK', 'ETR', 'ES', 'EXC', 'FE', 'NEE', 'PNW', 'PEG', 'SO',
             'WEC', 'XEL']),
    'TYL': ('DEF 14A 2026-03-23',
            ['ACIW', 'FICO', 'PEGA', 'AZPN', 'GWRE', 'PTC', 'BSY',
             'HUBS', 'VEEV', 'BLKB', 'JKHY', 'ENV', 'MANH']),
    'GPC': ('DEF 14A 2026-02-27',
            ['ADNT', 'FAST', 'AAP', 'HSIC', 'AIT', 'LEA', 'ARW', 'LKQ',
             'AN', 'MSM', 'AZO', 'ORLY', 'AVT', 'PH', 'KMX', 'PFGC',
             'CDW', 'PAG', 'CMI', 'USFD', 'DG', 'WCC', 'DLTR', 'GWW']),
    'TRMB': ('DEF 14A 2026-04-09',
             ['ANSS', 'FICO', 'ROP', 'AZPN', 'FTNT', 'IOT', 'ADSK',
              'FTV', 'SSNC', 'BSY', 'KEYS', 'SNPS', 'CDNS', 'PTC',
              'VNT', 'FFIV', 'ROK', 'ZBRA']),
    'ODFL': ('DEF 14A 2026-04-20',
             ['CHRW', 'CP', 'CSX', 'EXPD', 'HUBG', 'JBHT', 'KNX',
              'LSTR', 'NSC', 'R', 'SAIA', 'SNDR', 'UHAL', 'UNP',
              'XPO']),
    'PCAR': ('DEF 14A 2026-03-18',
             ['AGCO', 'CAT', 'CMI', 'DE', 'ETN', 'OSK', 'TEX']),
}

# expected fabricated old edge sets (assertion guard)
EXPECTED_OLD = {
    'WAT': ['CRL', 'GIS'],
    'DG': ['GIS', 'SBUX'],
    'PHM': ['GIS', 'LEN', 'NVR'],
    'SWKS': ['GIS', 'KLAC', 'QCOM'],
    'LEN': ['COF', 'GIS', 'NVR', 'PHM'],
    'MRK': ['COF', 'CRM', 'CSCO', 'JNJ'],
    'EIX': ['GIS', 'PEG', 'SO', 'WEC'],
    'TYL': ['FICO', 'GIS', 'JKHY', 'PTC'],
    'GPC': ['AMAT', 'COF', 'FAST', 'GIS'],
    'TRMB': ['FICO', 'FTNT', 'GIS', 'SNPS', 'ZBRA'],
    'ODFL': ['CSX', 'EXPD', 'GIS', 'NSC', 'UNP'],
    'PCAR': ['CAT', 'CMI', 'COF', 'DE', 'ETN'],
}

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'ACIW': ('ACI Worldwide, Inc.', 'Technology'),
    'ADNT': ('Adient plc', 'Consumer Discretionary'),
    'AGCO': ('AGCO Corporation', 'Industrials'),
    'AIT': ('Applied Industrial Technologies, Inc.', 'Industrials'),
    'AN': ('AutoNation, Inc.', 'Consumer Discretionary'),
    'ARW': ('Arrow Electronics, Inc.', 'Technology'),
    'AVT': ('Avnet, Inc.', 'Technology'),
    'AZN': ('AstraZeneca PLC', 'Health Care'),
    'BLKB': ('Blackbaud, Inc.', 'Technology'),
    'BSY': ('Bentley Systems, Incorporated', 'Technology'),
    'CP': ('Canadian Pacific Kansas City Limited', 'Industrials'),
    'ENV': ('Envestnet, Inc.', 'Technology'),
    'GSK': ('GSK plc', 'Health Care'),
    'HUBG': ('Hub Group, Inc.', 'Industrials'),
    'KBH': ('KB Home', 'Consumer Discretionary'),
    'LEA': ('Lear Corporation', 'Consumer Discretionary'),
    'MANH': ('Manhattan Associates, Inc.', 'Technology'),
    'MHO': ('M/I Homes, Inc.', 'Consumer Discretionary'),
    'MSM': ('MSC Industrial Direct Co., Inc.', 'Industrials'),
    'MTH': ('Meritage Homes Corporation', 'Consumer Discretionary'),
    'NVS': ('Novartis AG', 'Health Care'),
    'OSK': ('Oshkosh Corporation', 'Industrials'),
    'PAG': ('Penske Automotive Group, Inc.', 'Consumer Discretionary'),
    'PEGA': ('Pegasystems Inc.', 'Technology'),
    'PFGC': ('Performance Food Group Company', 'Consumer Staples'),
    'SNY': ('Sanofi', 'Health Care'),
    'TEX': ('Terex Corporation', 'Industrials'),
    'TMHC': ('Taylor Morrison Home Corporation', 'Consumer Discretionary'),
    'TOL': ('Toll Brothers, Inc.', 'Consumer Discretionary'),
    'TPH': ('TRI Pointe Homes, Inc.', 'Consumer Discretionary'),
    'UHAL': ('U-Haul Holding Company', 'Industrials'),
    'USFD': ('US Foods Holding Corp.', 'Consumer Staples'),
    'VNT': ('Vontier Corporation', 'Industrials'),
    'WCC': ('WESCO International, Inc.', 'Industrials'),
}


def main():
    bak = SRC.replace('.json', '_backup_20261001_0600_pre_batch5.json')
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

    # 2. assert + replace edges for the 12 repaired sources
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
