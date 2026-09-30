#!/usr/bin/env python3
"""Peer-network stale-source refresh batch 2 - 2026-09-30 ~16:00 PT run.

Replaces stale peer edges for the 20 sources the 2026-09-30 14:30 PT EDGAR
sweep flagged as having a newer DEF 14A than any edge filing. Each source's
edges are replaced with the compensation peer group transcribed verbatim from
that source's latest DEF 14A CD&A (evidence files:
goal hidden_files/thinedge-repair-20260930/*_peer.txt, batch-2 set).

Per-source result:
- XYZ  DEF 14A 2026-04-24: 17 peers (count matches old; FISV not FI - SEC
         company_tickers.json lists FISERV INC under FISV; the BR/PAYX "FI"
         mappings from their evidence files are corrected here). The 1-day
         gap was filename-vs-filing-date, not an amendment; the same-day
         DEFA14A is additional materials, not a proxy amendment.
- DRI  DEF 14A 2026-08-10: 11 -> 18 ("FY 2026 Peer Group", unchanged from FY2025)
- CAG  DEF 14A 2026-08-11: 13 -> 17 (FY2026 group; Lamb Weston added). Kellanova
         (K) kept as a cited peer: delisted Dec 2025 via Mars acquisition, retained
         per the DFS/IPG delisted-peer precedent.
- GIS  DEF 14A 2026-08-13: 13 -> 14 ("OUR INDUSTRY PEER GROUP" used for FY2026
         decisions). Nestle/Reckitt/Danone skipped (OTC ADR only, no US listing).
         Unilever UL excluded: the filing's own footnote excludes it (and the
         other three) from compensation comparisons (non-U.S. pay model).
- MDT  DEF 14A 2026-08-17: 6 -> 22 ("22-Company Compensation Comparison Group",
         used for FY2026 decisions; Biogen/UnitedHealth removed). FY2027 adds
         (ISRG, VRTX) queued, not applied.
- PAYX DEF 14A 2026-09-04: 11 -> 16 (FY2026 group, unchanged from prior year)
- STX  DEF 14A 2026-09-08: 15 -> 16 ("FY2026 Executive Peer Group"; tickers
         inline in filing). FY2027 removals (P/Everpure, SWKS) queued, not applied.
- CTAS DEF 14A 2026-09-15: NO named compensation peer group (CD&A describes an
         unnamed peer group + survey data; the 4 named companies are the TSR
         group for the Pay-vs-Performance table). Old ROL/WM edges deleted,
         isSource flipped off (TSLA 14:00 PT precedent).
- FOX  DEF 14A 2026-09-17: 9 -> 13 (ONE shared group for the whole company;
         no class-specific groups - the old 9-vs-12 split was a parse artifact).
         Versant added; Paramount Global -> Paramount Skydance post-merger.
- FOXA DEF 14A 2026-09-17: 12 -> 13 (same shared 13-member group as FOX)
- PH   DEF 14A 2026-09-18: 19 -> 19 (FY2026 = FY2025 group). MOG-A is Moog's
         SEC-listed primary class.
- KLAC DEF 14A 2026-09-22: 15 -> 17 ("industry peer group" for FY2026; NXP and
         Qualcomm added, Broadcom/NVIDIA/Teradyne removed)
- NWSA DEF 14A 2026-09-23: 10 -> 14 (Fiscal 2026 group; CoStar/RELX/SPGI added;
         TEGNA/Netflix/Paramount Global/WBD removed). FY2027 group (IPG out,
         Gartner in) queued, not applied.
- ADP  DEF 14A 2026-09-24: 14 -> 17 ("Fiscal Year 2026 Compensation Peer Group",
         tickers printed in filing). DFS kept: delisted May 2025 via Capital One
         acquisition, retained per delisted-peer precedent. FY2027 group
         (DFS removed) queued, not applied.
- LRCX DEF 14A 2026-09-24: 19 -> 17 ("Peer Group Companies for Calendar Year
         2026", no changes from Aug 2025 review)
- ORCL DEF 14A 2026-09-25: 14 -> 14 (FY2026 group; HPE removed, Intuit added)
- TPR  DEF 14A 2026-09-25: 6 -> 14 ("peer group used during fiscal year 2026";
         Richemont skipped - Swiss listing only, no US ticker; TPR self excluded;
         the secondary foreign/private reference set and the PRSU TSR group are
         not compensation peers, not transcribed)
- AMCR DEF 14A 2026-09-29: 24 -> 20 ("COMPENSATION PEER GROUP", unchanged for
         FY2026; the separate 30-company TSR Peer Group not transcribed)
- BR   DEF 14A 2026-09-29: 13 -> 14 ("Peer Group" for FY2026; Nasdaq added).
         Fiserv mapped to FISV (see XYZ note).
- EL   DEF 14A 2026-09-30: 5 -> 20 ("peer group of companies used for
         compensation in fiscal 2026"; same group approved for fiscal 2027)

Foreign-peer convention applied (coordinator decision, flagged by extraction
agents): every peer with a verifiable NYSE/Nasdaq ticker is mapped (literal
convention #5), including foreign-domiciled NYSE listings (GIB, SAP, RELX, TRI,
QSR, NXPI) per the MRNA/ONC and STX/NXPI precedents. Skipped only where there
is no US listing (Richemont, Nestle, Reckitt, Danone) or where the filing
itself excludes the peer from compensation comparisons (Unilever UL - GIS
footnote). The batch-1 MS exception (foreign money-center banks BCS/DB/UBS)
is not relitigated.

New peer-only nodes (26, all SEC company_tickers.json-verified except VSXY,
whose VSCO->VSXY NYSE ticker change effective 2026-06-02 is per the company's
own 8-K/press release): AA, AAP, AEO, ARMK, BBWI, BURL, CCK, COTY, EEFT, FLEX,
GFS, GIB, GPK, ITT, MOG-A, NWL, QSR, RELX, SAP, SSNC, TRI, VSXY, VSNT, WEX,
WU, Z (Zillow Class C; ZG Class A already a node, sector matched).
"""
import json, shutil

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, edge year, [peer tickers in filing order])
NEW = {
    'XYZ':  ('DEF 14A 2026-04-24', 2026,
             ['ADBE','DASH','INTU','SHOP','AFRM','EBAY','PANW','TOST','ABNB',
              'FISV','PYPL','UBER','TEAM','GPN','NOW','WDAY','COIN']),
    'DRI':  ('DEF 14A 2026-08-10', 2026,
             ['AAP','HLT','ARMK','MAR','AZO','ORLY','BBWI','QSR','BURL','ROST',
              'CCL','RCL','CMG','TSCO','DKS','ULTA','DPZ','YUM']),
    'CAG':  ('DEF 14A 2026-08-11', 2026,
             ['CPB','KDP','CHD','KMB','CLX','KHC','CL','LW','GIS','MKC','HSY',
              'MDLZ','HRL','NWL','SJM','POST','K']),
    'GIS':  ('DEF 14A 2026-08-13', 2026,
             ['CPB','HSY','CLX','SJM','PEP','KO','KMB','PG','CL','KHC','CAG',
              'KDP','MDLZ']),
    'MDT':  ('DEF 14A 2026-08-17', 2026,
             ['MMM','GEHC','ABT','GILD','ABBV','HON','AMGN','IBM','BAX','INTC',
              'BDX','JNJ','BSX','MRK','BMY','PFE','CSCO','QCOM','DHR','SYK',
              'LLY','TMO']),
    'PAYX': ('DEF 14A 2026-09-04', 2026,
             ['ADP','GPN','BR','INTU','CPAY','JKHY','EFX','MCO','EEFT','SSNC',
              'FICO','TRU','FISV','VRSK','IT','WEX']),
    'STX':  ('DEF 14A 2026-09-08', 2026,
             ['ADI','KLAC','MSI','P','GLW','LRCX','NTAP','SWKS','FLEX','MCHP',
              'NXPI','WDC','KEYS','MU','ON','ZBRA']),
    'FOX':  ('DEF 14A 2026-09-17', 2026,
             ['AMCX','CHTR','CMCSA','DIS','LBTYA','LYV','NFLX','NXST','PSKY',
              'SBGI','SIRI','WBD','VSNT']),
    'FOXA': ('DEF 14A 2026-09-17', 2026,
             ['AMCX','CHTR','CMCSA','DIS','LBTYA','LYV','NFLX','NXST','PSKY',
              'SBGI','SIRI','WBD','VSNT']),
    'PH':   ('DEF 14A 2026-09-18', 2026,
             ['MMM','CAT','CMI','DE','DOV','ETN','EMR','FLS','FTV','HON','ITW',
              'IR','ITT','JCI','MOG-A','RTX','ROK','TXT','TT']),
    'KLAC': ('DEF 14A 2026-09-22', 2026,
             ['AMD','KEYS','MKSI','SWKS','ADI','LRCX','NXPI','TXN','AMAT',
              'MRVL','ON','GLW','MCHP','QRVO','GFS','MU','QCOM']),
    'NWSA': ('DEF 14A 2026-09-23', 2026,
             ['BKNG','OMC','CSGP','PPLI','FDS','RELX','FOXA','SPGI','IPG',
              'SIRI','LBTYA','TRI','NXST','Z']),
    'ADP':  ('DEF 14A 2026-09-24', 2026,
             ['ACN','EBAY','MA','ADBE','FIS','PYPL','AON','FISV','CRM','GIB',
              'INTU','TEL','CTSH','LDOS','V','DFS','MRSH']),
    'LRCX': ('DEF 14A 2026-09-24', 2026,
             ['AMD','CSCO','MCHP','QCOM','A','GLW','MU','TXN','ADI','INTC',
              'NVDA','AMAT','KLAC','NXPI','AVGO','MRVL','ON']),
    'ORCL': ('DEF 14A 2026-09-25', 2026,
             ['ACN','CSCO','MSFT','ADBE','INTC','QCOM','GOOGL','IBM','CRM',
              'AMZN','INTU','SAP','AAPL','META']),
    'TPR':  ('DEF 14A 2026-09-25', 2026,
             ['GAP','EL','LULU','VFC','PVH','RL','WSM','VSXY','LEVI','URBN',
              'COTY','AEO','UAA','CPRI']),
    'AMCR': ('DEF 14A 2026-09-29', 2026,
             ['MMM','EMR','AA','GPK','AVY','IFF','BALL','IP','CARR','JCI','CL',
              'KMB','GLW','NUE','CCK','PPG','EMN','SW','ETN','SHW']),
    'BR':   ('DEF 14A 2026-09-29', 2026,
             ['EFX','EEFT','FDS','FIS','FISV','IT','GPN','ICE','JKHY','NDAQ',
              'PAYX','SSNC','VRSK','WU']),
    'EL':   ('DEF 14A 2026-09-30', 2026,
             ['BBWI','CPRI','KO','CL','COTY','GAP','IFF','KVUE','KDP','KMB',
              'KHC','LULU','MDLZ','NKE','PVH','RL','SBUX','TPR','ULTA','VFC']),
}

# ticker -> (name, sector) for peer-only nodes that do not exist yet.
# All SEC company_tickers.json-verified 2026-09-30, except VSXY (company 8-K).
NEW_NODES = {
    'AA':   ('Alcoa Corporation', 'Materials'),
    'AAP':  ('Advance Auto Parts, Inc.', 'Consumer Discretionary'),
    'AEO':  ('American Eagle Outfitters, Inc.', 'Consumer Discretionary'),
    'ARMK': ('Aramark', 'Industrials'),
    'BBWI': ('Bath & Body Works, Inc.', 'Consumer Discretionary'),
    'BURL': ('Burlington Stores, Inc.', 'Consumer Discretionary'),
    'CCK':  ('Crown Holdings, Inc.', 'Materials'),
    'COTY': ('Coty Inc.', 'Consumer Staples'),
    'EEFT': ('Euronet Worldwide, Inc.', 'Financials'),
    'FLEX': ('Flex Ltd.', 'Information Technology'),
    'GFS':  ('GLOBALFOUNDRIES Inc.', 'Information Technology'),
    'GIB':  ('CGI Inc.', 'Information Technology'),
    'GPK':  ('Graphic Packaging Holding Company', 'Materials'),
    'ITT':  ('ITT Inc.', 'Industrials'),
    'MOG-A':('Moog Inc.', 'Industrials'),
    'NWL':  ('Newell Brands Inc.', 'Consumer Discretionary'),
    'QSR':  ('Restaurant Brands International Inc.', 'Consumer Discretionary'),
    'RELX': ('RELX PLC', 'Industrials'),
    'SAP':  ('SAP SE', 'Information Technology'),
    'SSNC': ('SS&C Technologies Holdings, Inc.', 'Information Technology'),
    'TRI':  ('Thomson Reuters Corporation', 'Industrials'),
    'VSXY': ("Victoria's Secret & Co.", 'Consumer Discretionary'),
    'VSNT': ('Versant Media Group, Inc.', 'Communication Services'),
    'WEX':  ('WEX Inc.', 'Industrials'),
    'WU':   ('The Western Union Company', 'Financials'),
    'Z':    ('Zillow Group, Inc.', 'Real Estate'),
}

def main():
    bak = SRC.replace('.json', '_backup_20260930_1530_pre_batch2.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}

    # sanity: every new target is either an existing node or in NEW_NODES
    for src, (filing, year, peers) in NEW.items():
        assert src in by_ticker, f'{src}: not a node'
        for t in peers:
            assert t in by_ticker or t in NEW_NODES, f'{src}: unknown target {t}'
    print('target mapping OK:', sum(len(p) for _, _, p in NEW.values()), 'targets')

    # add missing peer-only nodes (peer-only nodes omit isSource, per convention)
    added = 0
    for t, (name, sector) in NEW_NODES.items():
        if t in by_ticker:
            continue
        node = {'ticker': t, 'name': name, 'sector': sector,
                'in_degree': 0, 'out_degree': 0, 'market_cap_tier': 'large'}
        nodes.append(node)
        by_ticker[t] = node
        added += 1
    print('new peer-only nodes added:', added)
    assert added == len(NEW_NODES), f'expected {len(NEW_NODES)} new nodes, got {added}'

    # CTAS: assert and delete both stale edges, flip isSource off (no named
    # compensation peer group in the 2026-09-15 DEF 14A - TSLA precedent)
    ctas_edges = [e for e in edges if e['source'] == 'CTAS']
    assert sorted(e['target'] for e in ctas_edges) == ['ROL', 'WM'], \
        f'CTAS edge set unexpected: {ctas_edges}'
    print(f"CTAS: deleting stale edges {[e['target'] for e in ctas_edges]} "
          f"filing={[e['filing'] for e in ctas_edges]}")
    edges = [e for e in edges if e['source'] != 'CTAS']
    by_ticker['CTAS']['isSource'] = False
    print('CTAS: isSource -> False')

    # replace edges per source, asserting before/after sets
    total_new = 0
    for src, (filing, year, peers) in NEW.items():
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        old_filings = sorted(set(e['filing'] for e in old))
        print(f'{src}: old {len(old)} edges filings={old_filings}')
        edges = [e for e in edges if e['source'] != src]
        for t in peers:
            edges.append({'source': src, 'target': t, 'year': year,
                          'group_type': 'primary', 'filing': filing})
        new_check = sorted(e['target'] for e in edges if e['source'] == src)
        assert new_check == sorted(peers), f'{src}: new edge set mismatch'
        assert len(set(new_check)) == len(new_check), f'{src}: duplicate targets'
        total_new += len(peers)
        print(f'{src}: new {len(peers)} edges filing={filing} year={year}')

    # recompute degrees for all nodes (stored degrees must stay exact)
    from collections import Counter
    indeg = Counter(e['target'] for e in edges)
    outdeg = Counter(e['source'] for e in edges)
    for x in nodes:
        x['in_degree'] = indeg.get(x['ticker'], 0)
        x['out_degree'] = outdeg.get(x['ticker'], 0)

    net['edges'] = edges
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-09-30'
    # regenerate the stale metadata 'sources' string from actuals (queued since
    # the 14:00 PT batch; previously "472 DEF 14A proxy statements..." while
    # 484 sources had edges). Machine-computed, never hand-edited.
    n_sources = len(set(e['source'] for e in edges))
    net['metadata']['sources'] = [
        f'{n_sources} DEF 14A proxy statements from S&P 500 companies']
    print('sources string regenerated:', net['metadata']['sources'][0])

    with open(SRC, 'w') as f:
        json.dump(net, f, indent=1)
    print('wrote', SRC, '| nodes:', len(nodes), '| edges:', len(edges))

if __name__ == '__main__':
    main()
