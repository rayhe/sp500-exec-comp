#!/usr/bin/env python3
"""Peer-network batch-6 thin GIS/COF-fingerprint repair (2026-10-01 run).

Follow-up to the 2026-10-01 batch-5 run. The Section-19 fingerprint queue
still holds 29 thin sources (<=8 edges) containing GIS and/or COF -- the
extractor-fabrication signature. Unlike batches 3-5, batch-6 needs
per-source judgment: several of these edge sets look partially plausible
(e.g. CFG's bank peers, KR's retail set, ESS's REIT set, PPG's materials
set) -- they may be real parses with a GIS/COF appendage rather than pure
fabrications, so each source is repaired verbatim from its latest DEF 14A
and only edges absent from the verbatim group are dropped.

Extraction by three subagents (10+10+9 sources): EDGAR submissions JSON
for the latest DEF 14A accession, filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)", peer sections
transcribed verbatim. Evidence in /tmp/peersweep/batch6/<TICKER>_peer.txt
(copied to goal hidden_files/peer-batch6-20261001/).

Repairs (29 sources; all from latest DEF 14A, comp-decisions groups):

  ABT  7 -> 18 (DEF 14A 2026-03-13; 19-co group; Reckitt Benckiser RKT.L
        skipped, no US ticker, per LULU/TPL convention)
  AEE  5 -> 21 (DEF 14A 2026-03-31; comp peers from Venn graphic,
        transcribed visually; 19-co TSR group unstored)
  AZO  5 -> 14 (DEF 14A 2025-10-28; FY25 group, no changes; petroleum
        distributors excluded per filing)
  CFG  6 ->  9 (DEF 14A 2026-03-09; 2025 group; 2026 variant ZION replaces
        CMA documented, queued per KO decisions-disclosed convention)
  COP  7 -> 22 (DEF 14A 2026-03-30; Comp Reference Group = 11 energy +
        11 general-industry; Performance Peer Group w/ Diamondback unstored)
  CTSH 6 -> 17 (DEF 14A 2026-04-17; chart images transcribed visually;
        "Hewlett Packard" -> HPE (revenue match); "Fiserv" -> FISV
        (current Nasdaq ticker; the FI recommendation was backwards - FI
        was the interim NYSE ticker, FISV restored 2025-11-11, batch-4
        "Fiserv is FISV" stands); "Marsh & McLennan" -> MRSH (batch-4);
        Discover DFS stored verbatim (in group as set late 2024, acquired
        by COF May 2025, per delisted-peer precedent); EPAM dropped -
        TSR-group-only; VMware removed by company)
  EG   6 -> 14 (DEF 14A 2026-04-10; 3 added 2025: ORI, AFG, TRV)
  ESS  8 -> 14 (DEF 14A 2026-03-27; Healthpeak listed as PEAK - DOC is
        the stale ticker, dropped; AMH/CPT/ELS/PEAK/PSA/O/SUI/UDR added)
  FAST 8 -> 10 (DEF 14A 2026-02-25; 2026 group identical; TSR group is an
        index, unstored)
  FE   6 -> 54 (DEF 14A 2026-04-01; UNION of 21-co Utility + 33-co
        General Industry groups - BOTH feed comp decisions via the
        filing's "Blended Median"; GIS (General Mills) is a GENUINE KEEP
        in the general-industry group, the batch's one surviving GIS)
  GDDY 8 -> 17 (DEF 14A 2026-04-24; 2025 group incl. NTNX; 2026 variant
        drops NTNX documented, queued; Zillow stored as Z)
  GL   6 -> 15 (DEF 14A 2026-03-19; Compensation Peer Group; PvP TSR is
        the S&P Life & Health Index, unstored)
  HPQ  7 -> 16 (DEF 14A 2026-02-25; FY2025 group from chart image; ORCL
        kept (FY2026 removes it), AMD/LRCX are FY2026 adds documented
        not stored; GE removed FY2025 by company; DELL new node)
  J    7 -> 13 (DEF 14A 2025-12-18; post-CMS-Separation group; GD/NOC/
        TXT removed by company; WSP skipped (TSX-only); GIB (CGI,
        NYSE-listed) and STN (Stantec, NYSE-listed, verified 2026-10-01)
        stored per foreign-with-US-ticker convention)
  KMB  6 -> 19 (DEF 14A 2026-03-23; 2025 group; GIS is a GENUINE KEEP
        (Consumer Staples home sector); K (Kellanova, Mars-acquired)
        stored verbatim per delisted-peer precedent; 2026 removes
        HON/K documented, queued)
  KR   8 -> 15 (DEF 14A 2026-05-13; TGT is a GENUINE KEEP (retail);
        supplemental Fortune-40 reference data unstored)
  MCK  6 -> 20 (DEF 14A 2026-06-12; disclosed FY2026 group set May 2025;
        chart image transcribed visually; 14-co relative-TSR PSU
        comparator unstored)
  MKTX 7 -> 17 (DEF 14A 2026-04-29; FICO/NDAQ explicitly removed 2025
        for size - DROP confirmed by filing; AssetMark/Envestnet removed
        post-acquisition; "Factset" -> FDS)
  NDSN 7 -> 22 (DEF 14A 2026-01-16; B (Barnes Group, taken private Jan
        2025) stored verbatim per delisted-peer precedent; National
        Instruments removed post-Emerson-acquisition; "Crane Co." -> CR)
  NXPI 6 -> 16 (DEF 14A 2026-04-27; STM/ASML/IFX skipped, no US ticker;
        same group doubles as RTSR PSU comparator per filing)
  PODD 8 -> 14 (DEF 14A 2026-04-06; Seagen/Shockwave removed
        post-acquisition)
  POOL 8 -> 13 (DEF 14A 2026-03-26; Watsco removed 2024 for atypical pay)
  PPG  7 -> 22 (DEF 14A 2026-03-05; comp-decisions comparator group;
        MAS dropped - genuine PPG peer but performance-only PvP group;
        COF fabricated)
  ROL  7 -> 17 (DEF 14A 2026-03-17; Mercer 2025 peer group)
  SLB  6 -> 29 (DEF 14A 2026-02-26; 10-co Core Industry + 19-co General
        Industry main groups, union (IBM added Jul 2024); SGO/ENR (no US
        ticker), SB (Schneider, Euronext), AAL (Anglo American) and BAESY
        (BAE Systems) skipped per RHHBY OTC-only precedent; 47-co CTO-only
        R&D group unstored - SWK stays dropped; "Northrup Grumman" typo)
  SO   6 -> 19 (DEF 14A 2026-04-03; comp-decisions group; 24-co
        relative-TSR group unstored ("Fortis Energy Services" typo for
        FTS, TSR-only anyway))
  TJX  6 -> 17 (DEF 14A 2026-04-30; FY26 = FY25 group; "McDonalds" no
        apostrophe; "Estee Lauder" no accent)
  VST  7 ->  6 (DEF 14A 2026-03-18; 2025 group (UGI); 2026 variant
        (UGI out, NEE+TLN in) documented, queued)
  WSM  6 -> 13 (DEF 14A 2026-05-06; FY2025 = FY2026; "RH (Restoration
        Hardware Holdings)" -> RH)

Extraction by three subagents (10+10+9): EDGAR submissions JSON for the
latest DEF 14A accession, filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)", peer sections
transcribed verbatim (chart images transcribed visually where noted).
Evidence in /tmp/peersweep/batch6/<TICKER>_peer.txt
(copied to goal hidden_files/peer-batch6-20261001/).
"""
import json
import shutil

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, [peer tickers in filing order])
NEW = {
    'ABT': ('DEF 14A 2026-03-13',
            ['MMM', 'BDX', 'BA', 'BSX', 'BMY', 'CSCO', 'KO', 'DHR', 'HON', 'JNJ', 'MDT', 'MRK', 'NKE', 'PEP', 'PFE', 'PG', 'SYK', 'TMO']),
    'AEE': ('DEF 14A 2026-03-31',
            ['EIX', 'NI', 'OGE', 'PCG', 'POR', 'PEG', 'SRE', 'LNT', 'AEP', 'CNP', 'CMS', 'ED', 'D', 'DTE', 'DUK', 'ETR', 'ES', 'FE', 'PNW', 'WEC', 'XEL']),
    'AZO': ('DEF 14A 2025-10-28',
            ['AAP', 'BBWI', 'COST', 'DKS', 'DG', 'DLTR', 'GPC', 'LKQ', 'LOW', 'ORLY', 'SHW', 'TSCO', 'ULTA', 'GWW']),
    'CFG': ('DEF 14A 2026-03-09',
            ['CMA', 'KEY', 'RF', 'FITB', 'MTB', 'TFC', 'HBAN', 'PNC', 'USB']),
    'COP': ('DEF 14A 2026-03-30',
            ['APA', 'CVX', 'DVN', 'EOG', 'XOM', 'HAL', 'MPC', 'OXY', 'PSX', 'SLB', 'VLO', 'MMM', 'BMY', 'CAT', 'CMI', 'GD', 'HON', 'LMT', 'MRK', 'NOC', 'PFE', 'RTX']),
    'CTSH': ('DEF 14A 2026-04-17',
            ['ACN', 'IBM', 'CRM', 'HPE', 'MRSH', 'ADBE', 'FISV', 'ADP', 'LDOS', 'OMC', 'AON', 'DXC', 'DFS', 'EBAY', 'FIS', 'WTW', 'NTAP']),
    'EG': ('DEF 14A 2026-04-10',
            ['AIG', 'CINF', 'ORI', 'AFG', 'CNA', 'RNR', 'ACGL', 'THG', 'TRV', 'AXS', 'HIG', 'WRB', 'CB', 'MKL']),
    'ESS': ('DEF 14A 2026-03-27',
            ['AMH', 'AVB', 'CPT', 'ELS', 'EQR', 'EXR', 'PEAK', 'INVH', 'MAA', 'PSA', 'O', 'REG', 'SUI', 'UDR']),
    'FAST': ('DEF 14A 2026-02-25',
            ['AIT', 'NDSN', 'DCI', 'ORLY', 'GPC', 'TSCO', 'IEX', 'WCC', 'MSM', 'GWW']),
    'FE': ('DEF 14A 2026-04-01',
            ['AEE', 'AEP', 'CNP', 'CMS', 'ED', 'D', 'DTE', 'DUK', 'EIX', 'ETR', 'EVRG', 'ES', 'EXC', 'NEE', 'NI', 'PCG', 'PPL', 'PEG', 'SO', 'WEC', 'XEL', 'APD', 'HBI', 'PVH', 'AA', 'HON', 'ROK', 'ADP', 'HRL', 'SWK', 'BALL', 'IP', 'TXT', 'BWA', 'K', 'CLX', 'CPB', 'KMI', 'EL', 'CAG', 'LHX', 'GT', 'EMN', 'MAS', 'HSY', 'ETN', 'OC', 'SHW', 'FBIN', 'PH', 'VFC', 'GIS', 'PPG', 'WHR']),
    'GDDY': ('DEF 14A 2026-04-24',
            ['AKAM', 'ADSK', 'DOCU', 'EBAY', 'FTNT', 'GEN', 'HUBS', 'NTNX', 'OKTA', 'PINS', 'SHOP', 'TOST', 'TWLO', 'VRSN', 'WIX', 'Z', 'ZM']),
    'GL': ('DEF 14A 2026-03-19',
            ['AFL', 'EQH', 'PRI', 'AIZ', 'FG', 'PFG', 'BHF', 'JXN', 'RGA', 'CINF', 'LNC', 'UNM', 'CNO', 'ORI', 'VOYA']),
    'HPQ': ('DEF 14A 2026-02-25',
            ['DELL', 'PEP', 'AVGO', 'IBM', 'ORCL', 'CSCO', 'INTC', 'NKE', 'QCOM', 'HON', 'MU', 'HPE', 'AMAT', 'MMM', 'TXN', 'WDC']),
    'J': ('DEF 14A 2025-12-18',
            ['ACN', 'CTSH', 'LDOS', 'KD', 'DXC', 'TTEK', 'PSN', 'EPAM', 'FLR', 'KBR', 'FCN', 'GIB', 'STN']),
    'KMB': ('DEF 14A 2026-03-23',
            ['MMM', 'HSY', 'MDLZ', 'CPB', 'HON', 'NWL', 'CLX', 'SJM', 'NKE', 'KO', 'K', 'PEP', 'CL', 'KVUE', 'PG', 'CAG', 'KHC', 'VFC', 'GIS']),
    'KR': ('DEF 14A 2026-05-13',
            ['ACI', 'CVS', 'SYY', 'BBY', 'HD', 'TGT', 'CAH', 'JNJ', 'TJX', 'COR', 'LOW', 'PG', 'WBA', 'WMT', 'COST']),
    'MCK': ('DEF 14A 2026-06-12',
            ['WMT', 'UNH', 'CVS', 'COR', 'COST', 'CI', 'CAH', 'ELV', 'KR', 'HUM', 'TGT', 'JNJ', 'UPS', 'FDX', 'PG', 'SYY', 'HCA', 'MRK', 'PFE', 'ABT']),
    'MKTX': ('DEF 14A 2026-04-29',
            ['ACIW', 'GWRE', 'SEIC', 'BGC', 'HTGC', 'TW', 'CBOE', 'MORN', 'VIRT', 'CWAN', 'MSCI', 'VRTS', 'CNS', 'NCNO', 'WT', 'FDS', 'QTWO']),
    'NDSN': ('DEF 14A 2026-01-16',
            ['AEIS', 'ENTG', 'KEYS', 'TRMB', 'AME', 'GGG', 'LECO', 'VNT', 'B', 'ICUI', 'MMSI', 'WTS', 'GTLS', 'IEX', 'MKSI', 'WWD', 'CR', 'ITGR', 'TFX', 'DCI', 'ITT', 'TER']),
    'NXPI': ('DEF 14A 2026-04-27',
            ['AMD', 'MRVL', 'STX', 'ADI', 'MCHP', 'SWKS', 'AMAT', 'MU', 'ON', 'TEL', 'GLW', 'QRVO', 'TXN', 'QCOM', 'WDC', 'LRCX']),
    'PODD': ('DEF 14A 2026-04-06',
            ['ALGN', 'DXCM', 'GMED', 'HOLX', 'IDXX', 'MASI', 'RMD', 'TFX', 'TECH', 'EXAS', 'NBIX', 'NVCR', 'AZPN', 'GWRE']),
    'POOL': ('DEF 14A 2026-03-26',
            ['AIT', 'BECN', 'BCC', 'CNM', 'FAST', 'GMS', 'HSIC', 'LKQ', 'MSM', 'PDCO', 'REZI', 'SITE', 'UFPI']),
    'PPG': ('DEF 14A 2026-03-05',
            ['MMM', 'APD', 'CE', 'DOW', 'DD', 'EMN', 'ETN', 'ECL', 'EMR', 'HON', 'HWM', 'ITW', 'IP', 'JCI', 'LIN', 'LYB', 'PH', 'ROK', 'SWK', 'TXT', 'SHW', 'TT']),
    'ROL': ('DEF 14A 2026-03-17',
            ['ABM', 'ADT', 'BV', 'BCO', 'CWST', 'CLH', 'FIX', 'FTDR', 'IRM', 'LII', 'MAS', 'SMG', 'SCI', 'TTEK', 'UNF', 'VLTO', 'WCN']),
    'SLB': ('DEF 14A 2026-02-26',
            ['BKR', 'BHP', 'COP', 'ENB', 'EOG', 'HAL', 'NOV', 'OXY', 'SU', 'FTI', 'MMM', 'ABB', 'APD', 'CARR', 'CAT', 'DE', 'DOW', 'ETN', 'EMR', 'FCX', 'GD', 'HON', 'IBM', 'JCI', 'LIN', 'LYB', 'ORCL', 'RIO', 'TT']),
    'SO': ('DEF 14A 2026-04-03',
            ['AEE', 'AEP', 'CNP', 'CMS', 'D', 'DTE', 'DUK', 'EIX', 'ETR', 'ES', 'EXC', 'FE', 'NEE', 'PCG', 'PPL', 'PEG', 'SRE', 'WEC', 'XEL']),
    'TJX': ('DEF 14A 2026-04-30',
            ['BBY', 'HD', 'LOW', 'MDLZ', 'PG', 'TGT', 'KO', 'KMB', 'M', 'NKE', 'ROST', 'WMT', 'EL', 'KSS', 'MCD', 'PEP', 'SBUX']),
    'VST': ('DEF 14A 2026-03-18',
            ['AES', 'CEG', 'ETR', 'NRG', 'PEG', 'UGI']),
    'WSM': ('DEF 14A 2026-05-06',
            ['BBWI', 'LEVI', 'TPR', 'CPRI', 'LULU', 'ULTA', 'EBAY', 'PVH', 'VFC', 'GAP', 'RL', 'W', 'RH']),
}

# expected fabricated old edge sets (assertion guard) -- captured at
# 2026-10-01 07:40 PT from peer-network.json (769 nodes / 7,039 edges)
EXPECTED_OLD = {
    'ABT': ['DHR', 'GIS', 'KO', 'NTRS', 'PEP', 'PFG', 'SYK'],
    'AEE': ['AON', 'CHTR', 'GIS', 'ITW', 'PEG'],
    'AZO': ['GIS', 'GPC', 'LKQ', 'TSCO', 'WMB'],
    'CFG': ['FITB', 'GIS', 'KEY', 'MTB', 'PNC', 'RF'],
    'COP': ['APA', 'BLK', 'COF', 'ED', 'MPC', 'PSX', 'STT'],
    'CTSH': ['ACN', 'CHTR', 'EPAM', 'GE', 'GIS', 'GPN'],
    'EG': ['ACGL', 'AWK', 'ED', 'GIS', 'HIG', 'WMB'],
    'ESS': ['AVB', 'DOC', 'EQR', 'EXR', 'GIS', 'INVH', 'MAA', 'REG'],
    'FAST': ['AMAT', 'COF', 'GPC', 'IEX', 'IP', 'NDSN', 'ORLY', 'TSCO'],
    'FE': ['CMS', 'EL', 'GIS', 'PEG', 'PSA', 'WMB'],
    'GDDY': ['ADSK', 'AKAM', 'CHTR', 'COF', 'FTNT', 'GEN', 'PINS', 'VRSN'],
    'GL': ['AFL', 'AIZ', 'CINF', 'GIS', 'IP', 'PFG'],
    'HPQ': ['AMD', 'AVGO', 'GE', 'GIS', 'LRCX', 'ORCL', 'PEP'],
    'J': ['ACN', 'EPAM', 'GD', 'GIS', 'IP', 'NOC', 'TXT'],
    'KMB': ['ED', 'GIS', 'K', 'KHC', 'PEP', 'PG'],
    'KR': ['COF', 'COR', 'COST', 'CVS', 'JNJ', 'TGT', 'WBA', 'WMT'],
    'MCK': ['BLK', 'CHTR', 'COF', 'KEY', 'UNH', 'WM'],
    'MKTX': ['CBOE', 'COF', 'FDS', 'FICO', 'GIS', 'MSCI', 'NDAQ'],
    'NDSN': ['AMD', 'AME', 'EMR', 'GIS', 'IEX', 'TER', 'TRMB'],
    'NXPI': ['CARR', 'COF', 'GIS', 'KEY', 'LRCX', 'ON'],
    'PODD': ['ALGN', 'CHTR', 'DXCM', 'GIS', 'HOLX', 'IDXX', 'RMD', 'TECH'],
    'POOL': ['AMAT', 'CHTR', 'COF', 'FAST', 'FDS', 'HSIC', 'LKQ', 'TGT'],
    'PPG': ['COF', 'DD', 'DOW', 'EMN', 'IP', 'MAS', 'SHW'],
    'ROL': ['BLK', 'COF', 'IP', 'IRM', 'LII', 'MAS', 'VLTO'],
    'SLB': ['BKR', 'CARR', 'CVX', 'GIS', 'JCI', 'SWK'],
    'SO': ['AWK', 'GIS', 'NEE', 'PSA', 'SWK', 'WEC'],
    'TJX': ['CRL', 'GIS', 'GPN', 'PEP', 'PG', 'WM'],
    'VST': ['CEG', 'ETR', 'GIS', 'NEE', 'NRG', 'PEG', 'PFG'],
    'WSM': ['GIS', 'LULU', 'RL', 'SPGI', 'TPR', 'ULTA'],
}

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'ABB': ('ABB Ltd', 'Industrials'),
    'ABM': ('ABM Industries Incorporated', 'Industrials'),
    'ACI': ('Albertsons Companies, Inc.', 'Consumer Staples'),
    'ADT': ('ADT Inc.', 'Consumer Discretionary'),
    'AFG': ('American Financial Group, Inc.', 'Financials'),
    'AMH': ('American Homes 4 Rent', 'Real Estate'),
    'AXS': ('Axis Capital Holdings Limited', 'Financials'),
    'B': ('Barnes Group Inc.', 'Industrials'),
    'BCC': ('Boise Cascade Company', 'Industrials'),
    'BCO': ('The Brink\'s Company', 'Industrials'),
    'BECN': ('Beacon Roofing Supply, Inc.', 'Industrials'),
    'BGC': ('BGC Group, Inc.', 'Financials'),
    'BHF': ('Brighthouse Financial, Inc.', 'Financials'),
    'BHP': ('BHP Group Limited', 'Materials'),
    'BV': ('BrightView Holdings, Inc.', 'Industrials'),
    'BWA': ('BorgWarner Inc.', 'Consumer Discretionary'),
    'CE': ('Celanese Corporation', 'Materials'),
    'CLH': ('Clean Harbors, Inc.', 'Industrials'),
    'CMA': ('Comerica Incorporated', 'Financials'),
    'CNA': ('CNA Financial Corporation', 'Financials'),
    'CNM': ('Core & Main, Inc.', 'Industrials'),
    'CNO': ('CNO Financial Group, Inc.', 'Financials'),
    'CNS': ('Cohen & Steers, Inc.', 'Financials'),
    'CR': ('Crane Company', 'Industrials'),
    'CWAN': ('Clearwater Analytics Holdings, Inc.', 'Technology'),
    'CWST': ('Casella Waste Systems, Inc.', 'Industrials'),
    'DCI': ('Donaldson Company, Inc.', 'Industrials'),
    'DXC': ('DXC Technology Company', 'Information Technology'),
    'ELS': ('Equity LifeStyle Properties, Inc.', 'Real Estate'),
    'ENB': ('Enbridge Inc.', 'Energy'),
    'EQH': ('Equitable Holdings, Inc.', 'Financials'),
    'FBIN': ('Fortune Brands Innovations, Inc.', 'Industrials'),
    'FCN': ('FTI Consulting, Inc.', 'Industrials'),
    'FG': ('F&G Annuities & Life, Inc.', 'Financials'),
    'FIX': ('Comfort Systems USA, Inc.', 'Industrials'),
    'FTDR': ('Frontdoor, Inc.', 'Consumer Discretionary'),
    'FTI': ('TechnipFMC plc', 'Energy'),
    'GGG': ('Graco Inc.', 'Industrials'),
    'GMED': ('Globus Medical, Inc.', 'Health Care'),
    'GMS': ('GMS Inc.', 'Industrials'),
    'GT': ('The Goodyear Tire & Rubber Company', 'Consumer Discretionary'),
    'GTLS': ('Chart Industries, Inc.', 'Industrials'),
    'HBI': ('Hanesbrands Inc.', 'Consumer Discretionary'),
    'HTGC': ('Hercules Capital, Inc.', 'Financials'),
    'ICUI': ('ICU Medical, Inc.', 'Health Care'),
    'ITGR': ('Integer Holdings Corporation', 'Health Care'),
    'JXN': ('Jackson Financial Inc.', 'Financials'),
    'KSS': ('Kohl\'s Corporation', 'Consumer Discretionary'),
    'LECO': ('Lincoln Electric Holdings, Inc.', 'Industrials'),
    'M': ('Macy\'s, Inc.', 'Consumer Discretionary'),
    'MKL': ('Markel Group Inc.', 'Financials'),
    'MMSI': ('Merit Medical Systems, Inc.', 'Health Care'),
    'MORN': ('Morningstar, Inc.', 'Financials'),
    'NCNO': ('nCino, Inc.', 'Technology'),
    'NOV': ('NOV Inc.', 'Energy'),
    'NVCR': ('NovoCure Limited', 'Health Care'),
    'OC': ('Owens Corning', 'Industrials'),
    'OGE': ('OGE Energy Corp.', 'Utilities'),
    'ORI': ('Old Republic International Corporation', 'Financials'),
    'PDCO': ('Patterson Companies, Inc.', 'Health Care'),
    'PEAK': ('Healthpeak Properties, Inc.', 'Real Estate'),
    'POR': ('Portland General Electric Company', 'Utilities'),
    'PRI': ('Primerica, Inc.', 'Financials'),
    'PSN': ('Parsons Corporation', 'Industrials'),
    'QTWO': ('Q2 Holdings, Inc.', 'Technology'),
    'RGA': ('Reinsurance Group of America, Incorporated', 'Financials'),
    'RIO': ('Rio Tinto plc', 'Materials'),
    'RNR': ('RenaissanceRe Holdings Ltd.', 'Financials'),
    'SCI': ('Service Corporation International', 'Consumer Discretionary'),
    'SEIC': ('SEI Investments Company', 'Financials'),
    'SITE': ('SiteOne Landscape Supply, Inc.', 'Industrials'),
    'SMG': ('The Scotts Miracle-Gro Company', 'Materials'),
    'STN': ('Stantec Inc.', 'Industrials'),
    'SU': ('Suncor Energy Inc.', 'Energy'),
    'THG': ('The Hanover Insurance Group, Inc.', 'Financials'),
    'TTEK': ('Tetra Tech, Inc.', 'Industrials'),
    'TW': ('Tradeweb Markets Inc.', 'Financials'),
    'UFPI': ('UFP Industries, Inc.', 'Industrials'),
    'UGI': ('UGI Corporation', 'Utilities'),
    'UNF': ('UniFirst Corporation', 'Industrials'),
    'UNM': ('Unum Group', 'Financials'),
    'VIRT': ('Virtu Financial, Inc.', 'Financials'),
    'VOYA': ('Voya Financial, Inc.', 'Financials'),
    'VRTS': ('Virtus Investment Partners, Inc.', 'Financials'),
    'WCN': ('Waste Connections, Inc.', 'Industrials'),
    'WHR': ('Whirlpool Corporation', 'Consumer Discretionary'),
    'WIX': ('Wix.com Ltd.', 'Information Technology'),
    'WT': ('WisdomTree, Inc.', 'Financials'),
    'WTS': ('Watts Water Technologies, Inc.', 'Industrials'),
    'WWD': ('Woodward, Inc.', 'Industrials'),
}


def main():
    bak = SRC.replace('.json', '_backup_20261001_0730_pre_batch6.json')
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
