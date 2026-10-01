#!/usr/bin/env python3
"""Peer-network batch-7 fingerprint-queue repair (2026-10-01 run).

Follow-up to the 2026-10-01 batch-6 run. The Section-19 fingerprint queue
still lists 488 cross-sector fingerprint-target edges across 261 sources.
Batch-6 drained the <=8-edge thin sources; batch-7 takes the 18 heaviest
offender sources (the remaining batch-6 candidates were all resolved) and
re-extracts each source's comp-decisions peer group VERBATIM from its latest
DEF 14A, keeping only edges that match the verbatim group. TSR/PSU
comparator groups are unstored per the batches 3-6 convention.

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession, filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)", peer sections
transcribed verbatim. Evidence in /tmp/peersweep/batch7/<TICKER>_peer.txt
(copied to goal hidden_files/peer-batch7-20261001/).

Repairs (18 sources; all from latest DEF 14A, comp-decisions groups):

  EXC  32 -> 18 (DEF 14A 2026-03-18; blended 13 energy-services + 5
        general-industry group; 20-co TSR comparator unstored; GENUINE
        KEEPS: IP, WM; dropped: BLK, GIS, PFG, PSA, STT, TGT, AWK, UAL,
        10 TSR-only; added EIX, ES, SRE)
  KVUE 22 -> 17 (DEF 14A 2026-04-08; 17-co branded-consumer group;
        GENUINE KEEPS: GIS, HSY; dropped: CHTR, COF, IP, PG + BF-A,
        MKC, MNST, PEP, STZ, TAP, TSN; added CLX, SJM, MDLZ, PRGO)
  LLY  12 -> 35 (DEF 14A 2026-03-20; UNION of 13-co Pharma Peer Group
        and 22-co General Industry Peer Group - both feed comp decisions
        (FE precedent); Roche RHHBY skipped, OTC-only; dropped all 6
        offenders GIS, IP, PFG, PG, PSA, TGT)
  AEP  29 -> 25 (DEF 14A 2026-03-18; 25-co 2025 Compensation Peer Group;
        25-co TSR group unstored; GENUINE KEEP: WM; dropped: CHTR, COF,
        GIS, IP, DAL, GD, NOC, PNW, WMB)
  CVS  52 -> 19 (DEF 14A 2026-04-03; 19-co diversified 2025 group; WBA
        kept per delisted-peer precedent (private since Aug 2025); rTSR
        PSU comparator unstored; GENUINE KEEPS: MSFT, TGT; dropped:
        CHTR, GIS, IP + 33 extractor fabrications)
  CCI  20 -> 12 (DEF 14A 2026-04-06; 2025 group = prior minus 10 removed
        (AMAT, BKNG, BXP, CHTR, INTU, KLAC, LRCX, LUMN, NTAP, NOW) plus
        8 added (ARE, AVB, EQR, EXR, INVH, IRM, MAA, WY); GIS SURVIVES
        the cut - the filing explicitly retains it, so GIS is a GENUINE
        KEEP along with BLK and STT; dropped: CHTR)
  CHTR 29 -> 32 (DEF 14A 2026-03-12; UNION of 13-co Primary + 19-co
        Secondary peer groups - both feed comp decisions (FE precedent);
        EchoStar -> ECHO (SEC live ticker; SATS is stale); Paramount
        Skydance Corp. -> PSKY (current; the stored PARA node is Banzai
        per SEC); Liberty Global -> LBTYA; GENUINE KEEP: PG; dropped:
        FRT, GIS, IP)
  DOW  26 -> 20 (DEF 14A 2026-02-27; 20-co 2025 Compensation Peer Group;
        relative-TSR group unstored; dropped all 4 offenders CHTR, CVX,
        GIS, PFG + CTVA, EMN, IP, WMB, XOM; added MMM, ADM, MDLZ)
  GM   15 -> 16 (DEF 14A 2026-04-20; 16-co Overall Compensation
        Benchmarking group; OEM Titans-30 PSU group unstored; GENUINE
        KEEPS: MSFT, PG; dropped: CHTR, COF; added MMM, BA, JNJ)
  HON  22 -> 18 (DEF 14A 2026-04-10; 18-co 2025 Compensation Peer Group;
        no changes in 2025; dropped all 4 offenders CHTR, COF, GIS, IP
        + AXON, O; added MMM, PSX)
  HST  17 -> 16 (DEF 14A 2026-04-08; 16-co compensation peer group;
        Welltower removed by company; dropped all 4 offenders BLK,
        CHTR, GIS, STT + DOC, WELL; added H, PK, REG, PEAK, VNO)
  LKQ  10 -> 18 (DEF 14A 2026-03-24; 18-co 2025 group, same as 2024;
        dropped all 4 offenders BLK, COF, GIS, IP; added ADNT, AAP, GT,
        APTV, LEA, ORLY, BECN, BWA, GWW, DAN, WSO, WCC)
  PANW 22 -> 16 (DEF 14A 2025-11-07; 16-co fiscal-2025 group; Gen Digital,
        VMware, Splunk, Juniper out; Adobe, Synopsys in; dropped all 4
        offenders FRT, IP, PFG, PG + AMD, GEN, JNPR; added SSNC)
  RTX  10 -> 21 (DEF 14A 2026-03-09; 21-co Compensation Peer Group;
        2025 adds Ford, Microsoft, Nvidia; removes 3M, L3Harris; Core
        A&D PSU group unstored; GENUINE KEEP: MSFT; dropped: IP, PFG,
        STT, JCI, TXT)
  STE  16 -> 16 (DEF 14A 2026-06-11; 16-co fiscal-2026 group; GEHC added;
        dropped all 4 offenders GIS, IP, PFG, WM + ED; added TFX, BIO,
        COO, MTD, XRAY)
  TGT  28 -> 38 (DEF 14A 2026-04-27; UNION of 25-co Retail + 13-co General
        industry groups - both used for FY2025 comp (FE precedent);
        Nordstrom/Walgreens removed (private); Publix skipped (private,
        no ticker); Gap stored as GAP (SEC ticker; the proxy's "(GPS)"
        label is a typo); GENUINE KEEPS: GIS, PG; dropped: COF, IP,
        UHS, WBA, WTW)
  TT   20 -> 15 (DEF 14A 2026-04-23; 15-co 2025 Compensation Peer Group;
        Fortive removed by company; dropped all 4 offenders CHTR, COF,
        GIS, IP + FTV, LII; added MMM)
  UPS  19 -> 17 (DEF 14A 2026-03-19; 17-co compensation peer group; no
        changes in 2025; GENUINE KEEPS: PG, TGT; dropped: COF, FRT,
        DLR, WM; added MCD, LOW)
"""
import json
import shutil

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, [peer tickers in filing order])
NEW = {
    'EXC': ('DEF 14A 2026-03-18',
            ['AEP', 'ED', 'D', 'DUK', 'EIX', 'ETR', 'ES', 'FE', 'NEE', 'PCG',
             'SRE', 'SO', 'XEL', 'IP', 'ETN', 'OXY', 'UNP', 'WM']),
    'KVUE': ('DEF 14A 2026-04-08',
             ['CPB', 'CHD', 'CLX', 'KO', 'CL', 'CAG', 'EL', 'GIS', 'HSY',
              'HRL', 'SJM', 'K', 'KDP', 'KMB', 'KHC', 'MDLZ', 'PRGO']),
    'LLY': ('DEF 14A 2026-03-20',
            ['ABBV', 'AMGN', 'AZN', 'BMY', 'GILD', 'GSK', 'JNJ', 'MDT',
             'MRK', 'NVS', 'PFE', 'SNY', 'SYK', 'MMM', 'ABT', 'ADBE', 'AMD',
             'AAPL', 'AMAT', 'AVGO', 'CSCO', 'KO', 'CL', 'DHR', 'HON',
             'IBM', 'INTC', 'MCD', 'MU', 'NKE', 'NVDA', 'QCOM', 'CRM',
             'TSLA', 'TMO']),
    'AEP': ('DEF 14A 2026-03-18',
            ['MMM', 'GD', 'CNP', 'NEE', 'ED', 'NOC', 'CEG', 'PCG', 'DAL',
             'PPL', 'D', 'PEG', 'DTE', 'SRE', 'DUK', 'AES', 'EIX', 'SHW',
             'ETR', 'SO', 'ES', 'WM', 'EXC', 'XEL', 'FE']),
    'CVS': ('DEF 14A 2026-04-03',
            ['ABBV', 'HCA', 'MSFT', 'BMY', 'HUM', 'PFE', 'CAH', 'IBM',
             'TGT', 'COR', 'JNJ', 'UNH', 'CNC', 'MCK', 'WBA', 'CI', 'MRK',
             'WMT', 'ELV']),
    'CCI': ('DEF 14A 2026-04-06',
            ['ARE', 'AVB', 'BLK', 'EQR', 'EXR', 'GIS', 'INVH', 'IRM',
             'KEY', 'MAA', 'STT', 'WY']),
    'CHTR': ('DEF 14A 2026-03-12',
             ['T', 'CSCO', 'CMCSA', 'ECHO', 'FOX', 'LBTYA', 'LUMN', 'NFLX',
              'PSKY', 'DIS', 'TMUS', 'VZ', 'WBD', 'MMM', 'AXP', 'BMY',
              'CAT', 'GILD', 'HON', 'IBM', 'JNJ', 'MRK', 'MDLZ', 'NKE',
              'PEP', 'PFE', 'PM', 'PG', 'QCOM', 'RTX', 'KO', 'KHC']),
    'DOW': ('DEF 14A 2026-02-27',
            ['MMM', 'ADM', 'BA', 'BMY', 'CAT', 'KO', 'COP', 'DE', 'ECL',
             'HON', 'JCI', 'KMB', 'LIN', 'LMT', 'LYB', 'MDLZ', 'PFE', 'PPG',
             'RTX', 'SHW']),
    'GM': ('DEF 14A 2026-04-20',
           ['MMM', 'BA', 'CAT', 'CSCO', 'F', 'HON', 'HPQ', 'IBM', 'INTC',
            'JNJ', 'MSFT', 'PEP', 'PFE', 'PG', 'RTX', 'TSLA']),
    'HON': ('DEF 14A 2026-04-10',
            ['BA', 'DE', 'DD', 'GD', 'CAT', 'DOW', 'GE', 'ITW', 'LMT',
             'RTX', 'ETN', 'SLB', 'MMM', 'EMR', 'PSX', 'JCI', 'CSCO',
             'MDT']),
    'HST': ('DEF 14A 2026-04-08',
            ['ARE', 'H', 'AVB', 'KIM', 'BXP', 'MAR', 'EQR', 'PK', 'ESS',
             'REG', 'FRT', 'UDR', 'PEAK', 'VTR', 'HLT', 'VNO']),
    'LKQ': ('DEF 14A 2026-03-24',
            ['ADNT', 'GPC', 'AAP', 'GT', 'APTV', 'LEA', 'AZO', 'ORLY',
             'BECN', 'RSG', 'BWA', 'URI', 'CDW', 'GWW', 'DAN', 'WSO',
             'FAST', 'WCC']),
    'PANW': ('DEF 14A 2025-11-07',
             ['ADBE', 'AKAM', 'ADSK', 'CDNS', 'CRWD', 'FTNT', 'INTU',
              'KEYS', 'NTAP', 'PAYX', 'ROP', 'NOW', 'SNOW', 'SSNC',
              'SNPS', 'WDAY']),
    'RTX': ('DEF 14A 2026-03-09',
            ['BA', 'GE', 'GD', 'LMT', 'NOC', 'CAT', 'DE', 'T', 'CSCO',
             'HPQ', 'IBM', 'INTC', 'MSFT', 'NVDA', 'VZ', 'CVX', 'DOW',
             'HON', 'F', 'GM', 'UPS']),
    'STE': ('DEF 14A 2026-06-11',
            ['A', 'EW', 'RVTY', 'BAX', 'GEHC', 'TFX', 'BIO', 'HOLX', 'WAT',
             'BSX', 'IDXX', 'ZBH', 'COO', 'MTD', 'XRAY', 'RMD']),
    'TGT': ('DEF 14A 2026-04-27',
            ['ACI', 'HD', 'AMZN', 'KSS', 'BBY', 'KR', 'BJ', 'LOW', 'COST',
             'M', 'CVS', 'DG', 'ROST', 'FDX', 'DLTR', 'TJX', 'SBUX', 'GAP',
             'WMT', 'RTX', 'JNJ', 'UPS', 'JCI', 'UNH', 'MAR', 'MMM',
             'MCD', 'ABT', 'MET', 'ADM', 'MDLZ', 'CI', 'NKE', 'KO', 'PEP',
             'ELV', 'PG', 'GIS']),
    'TT': ('DEF 14A 2026-04-23',
           ['MMM', 'DE', 'HON', 'PH', 'CARR', 'DOV', 'ITW', 'ROK', 'CMI',
            'ETN', 'JCI', 'TEL', 'DHR', 'EMR', 'OTIS']),
    'UPS': ('DEF 14A 2026-03-19',
            ['T', 'FDX', 'MCD', 'BA', 'HD', 'PEP', 'CAT', 'INTC', 'PG',
             'CSCO', 'JNJ', 'TGT', 'CMCSA', 'LMT', 'WMT', 'DE', 'LOW']),
}

# expected fabricated old edge sets (assertion guard) -- captured at
# 2026-10-01 10:10 PT from peer-network.json (859 nodes / 7,359 edges)
EXPECTED_OLD = {
    'EXC': ['AEE', 'AEP', 'AWK', 'BLK', 'CMS', 'CNP', 'D', 'DTE', 'DUK',
            'ED', 'ETN', 'ETR', 'EVRG', 'FE', 'GIS', 'IP', 'LNT', 'NEE',
            'NI', 'OXY', 'PCG', 'PEG', 'PFG', 'PPL', 'PSA', 'SO', 'STT',
            'TGT', 'UAL', 'UNP', 'WEC', 'XEL'],
    'KVUE': ['BF-A', 'CAG', 'CHD', 'CHTR', 'CL', 'COF', 'GIS', 'HRL',
             'HSY', 'IP', 'K', 'KDP', 'KHC', 'KMB', 'KO', 'MKC', 'MNST',
             'PEP', 'PG', 'STZ', 'TAP', 'TSN'],
    'LLY': ['ADM', 'AMAT', 'CRM', 'GIS', 'HON', 'IP', 'JCI', 'PFG', 'PG',
            'PSA', 'TGT', 'TMO'],
    'AEP': ['AEE', 'CEG', 'CHTR', 'CMS', 'CNP', 'COF', 'D', 'DAL', 'DTE',
            'DUK', 'ED', 'ETR', 'EVRG', 'EXC', 'FE', 'GD', 'GIS', 'IP',
            'LNT', 'NEE', 'NOC', 'PCG', 'PEG', 'PNW', 'PPL', 'SO', 'WM',
            'WMB', 'XEL'],
    'CVS': ['A', 'ABBV', 'ALGN', 'AMGN', 'BIIB', 'BMY', 'CAH', 'CHTR',
            'CI', 'CNC', 'COR', 'CRL', 'DGX', 'DHR', 'DVA', 'ELV', 'EW',
            'GIS', 'HCA', 'HOLX', 'HSIC', 'HUM', 'IDXX', 'INCY', 'IP',
            'IQV', 'ISRG', 'JNJ', 'LLY', 'MCK', 'MDT', 'MRK', 'MRNA',
            'MSFT', 'PFE', 'PODD', 'REGN', 'RMD', 'RVTY', 'SOLV', 'STE',
            'SYK', 'TECH', 'TGT', 'UHS', 'UNH', 'VTRS', 'WAT', 'WBA',
            'WMT', 'WST', 'ZTS'],
    'CCI': ['AMAT', 'ARE', 'AVB', 'BKNG', 'BLK', 'BXP', 'CHTR', 'EXR',
            'GIS', 'INTU', 'INVH', 'IRM', 'KEY', 'KLAC', 'LRCX', 'MAA',
            'NOW', 'NTAP', 'STT', 'WY'],
    'CHTR': ['AXP', 'BMY', 'CAT', 'CMCSA', 'CSCO', 'DIS', 'FOX', 'FRT',
             'GILD', 'GIS', 'HON', 'IP', 'JNJ', 'KHC', 'KO', 'MDLZ',
             'MRK', 'NFLX', 'NKE', 'PARA', 'PEP', 'PFE', 'PG', 'PM',
             'QCOM', 'T', 'TMUS', 'VZ', 'WBD'],
    'DOW': ['BA', 'BMY', 'CAT', 'CHTR', 'COP', 'CTVA', 'CVX', 'DE', 'ECL',
            'EMN', 'GIS', 'HON', 'IP', 'JCI', 'KMB', 'KO', 'LIN', 'LMT',
            'LYB', 'PFE', 'PFG', 'PPG', 'RTX', 'SHW', 'WMB', 'XOM'],
    'GM': ['CAT', 'CHTR', 'COF', 'CSCO', 'F', 'HON', 'HPQ', 'IBM', 'INTC',
           'MSFT', 'PEP', 'PFE', 'PG', 'RTX', 'TSLA'],
    'HON': ['AXON', 'BA', 'CAT', 'CHTR', 'COF', 'CSCO', 'DD', 'DE', 'DOW',
            'EMR', 'ETN', 'GD', 'GE', 'GIS', 'IP', 'ITW', 'JCI', 'LMT',
            'MDT', 'O', 'RTX', 'SLB'],
    'HST': ['ARE', 'AVB', 'BLK', 'BXP', 'CHTR', 'DOC', 'EQR', 'ESS', 'FRT',
            'GIS', 'HLT', 'KIM', 'MAR', 'STT', 'UDR', 'VTR', 'WELL'],
    'LKQ': ['AZO', 'BLK', 'CDW', 'COF', 'FAST', 'GIS', 'GPC', 'IP', 'RSG',
            'URI'],
    'PANW': ['ADBE', 'ADSK', 'AKAM', 'AMD', 'CDNS', 'CRWD', 'FRT', 'FTNT',
             'GEN', 'INTU', 'IP', 'JNPR', 'KEYS', 'NOW', 'NTAP', 'PAYX',
             'PFG', 'PG', 'ROP', 'SNOW', 'SNPS', 'WDAY'],
    'RTX': ['CAT', 'F', 'HPQ', 'IP', 'JCI', 'MSFT', 'NVDA', 'PFG', 'STT',
            'TXT'],
    'STE': ['A', 'BAX', 'BSX', 'ED', 'EW', 'GEHC', 'GIS', 'HOLX', 'IDXX',
            'IP', 'PFG', 'RMD', 'RVTY', 'WAT', 'WM', 'ZBH'],
    'TGT': ['AMZN', 'BBY', 'CI', 'COF', 'COST', 'CVS', 'DG', 'DLTR', 'ELV',
            'FDX', 'GIS', 'HD', 'IP', 'JCI', 'KR', 'MET', 'NKE', 'PEP',
            'PG', 'ROST', 'RTX', 'SBUX', 'UHS', 'UNH', 'UPS', 'WBA',
            'WMT', 'WTW'],
    'TT': ['CARR', 'CHTR', 'CMI', 'COF', 'DE', 'DHR', 'DOV', 'EMR', 'ETN',
           'FTV', 'GIS', 'HON', 'IP', 'ITW', 'JCI', 'LII', 'OTIS', 'PH',
           'ROK', 'TEL'],
    'UPS': ['BA', 'CAT', 'CMCSA', 'COF', 'CSCO', 'DE', 'DLR', 'FDX', 'FRT',
            'HD', 'INTC', 'JNJ', 'LMT', 'PEP', 'PG', 'T', 'TGT', 'WM',
            'WMT'],
}

# new peer-only nodes: ticker -> (name, sector)
# all SEC-verified 2026-10-01 via company_tickers.json (live file for ECHO);
# ECHO = EchoStar CORP (SEC live ticker; CHTR filing's "EchoStar" SATS is
# stale); GAP note: TGT filing says "The Gap, Inc. (GPS)" but SEC ticker
# is GAP and the node already exists.
NEW_NODES = {
    'BJ': ("BJ's Wholesale Club Holdings, Inc.", 'Consumer Staples'),
    'DAN': ('DANA Inc', 'Consumer Discretionary'),
    'ECHO': ('EchoStar CORP', 'Communication Services'),
    'H': ('Hyatt Hotels Corp', 'Consumer Discretionary'),
    'LUMN': ('Lumen Technologies, Inc.', 'Communication Services'),
    'PK': ('Park Hotels & Resorts Inc.', 'Real Estate'),
    'PRGO': ('PERRIGO Co plc', 'Health Care'),
    'VNO': ('VORNADO REALTY TRUST', 'Real Estate'),
    'WSO': ('WATSCO INC', 'Industrials'),
}


def main():
    bak = SRC.replace('.json', '_backup_20261001_1100_pre_batch7.json')
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
