#!/usr/bin/env python3
"""Peer-network refresh batch 2026-09-30: replace peer edges for 8 companies
whose peer groups were refreshed in newer DEF 14As (DECK, GEN, LULU, LW, NTAP, PG, TPL, TTWO).

Peer lists transcribed verbatim from the filings listed below (see /tmp/peerrefresh/
extraction files and the iteration log). Foreign-listed peers with no US ticker
(Adidas, Puma, Freehold Royalties, PrairieSky, L'Oreal, Unilever, Reckitt,
Henkel, Beiersdorf, Kao, Essity, Haleon, Unicharm) are skipped per network
convention (ticker-identified nodes only). Acquired/go-private names that appear
in the DISCLOSED group are kept under their last ticker (FL, JWN, SKX, STR,
ARIS, ENLC).
"""
import json, shutil, datetime

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, [peer tickers in filing order])
NEW = {
    'DECK': ('DEF 14A 2026-07-24', ['ANF','CPRI','COLM','CROX','DKS','EL','LEVI','LULU','PVH','RL','RH','SHOO','TPR','ULTA','UAA','URBN','VFC','WSM','SKX']),
    'GEN':  ('DEF 14A 2026-07-28', ['ADSK','EFX','PINS','AKAM','EXPE','PANW','CRWD','FTNT','RKT','DOCU','GDDY','SOFI','DBX','MTCH','TRU','EBAY','NTAP','ZM','EA']),
    'LULU': ('DEFC14A 2026-05-18', ['CMG','DKS','EL','GAP','LEVI','NKE','JWN','PVH','RL','ROST','SKX','SBUX','TPR','ULTA','UAA','VFC','WSM']),
    'LW':   ('DEF 14A 2026-07-30', ['BRBR','CAG','FLO','HRL','INGR','MKC','TAP','POST','CPB','HAIN','HSY','SJM','MZTI','THS','KLG']),
    'NTAP': ('DEF 14A 2026-07-28', ['ADBE','AKAM','ANET','CDNS','P','FFIV','FTNT','HPE','INTU','JNPR','KEYS','NTNX','PANW','CRM','STX','NOW','WDC','WDAY']),
    'PG':   ('DEF 14A 2026-08-28', ['ABT','BA','CVX','KO','CL','LLY','XOM','HPQ','HD','INTC','JNJ','KMB','MCD','MRK','MSFT','NKE','PEP','PFE','TMO','VZ','WMT']),
    'TPL':  ('DEF 14A 2026-09-25', ['BSM','KRP','NOG','CIVI','MTDR','OVV','PR','RRC','SM','DTM','KNTK','WES','ARIS','ENLC','STR','WTTR']),
    'TTWO': ('DEF 14A 2026-07-27', ['EA','DKNG','BKNG','EBAY','EXPE','MTCH','PLTK','RBLX','ROKU','FOX','HAS','LYV','MAT','PARA','SIRI','TKO','WBD','WMG']),
}

# ticker -> (name, sector) for peer-only nodes that do not exist yet
NEW_NODES = {
    'DKNG': ('DraftKings Inc', 'Consumer Discretionary'),
    'PLTK': ('Playtika Ltd', 'Communication Services'),
    'MAT': ('Mattel Inc', 'Consumer Discretionary'),
    'WMG': ('Warner Music Group Corp', 'Communication Services'),
    'TRU': ('TransUnion', 'Industrials'),
    'BSM': ('Black Stone Minerals LP', 'Energy'),
    'KRP': ('Kimbell Royalty Partners LP', 'Energy'),
    'NOG': ('Northern Oil & Gas Inc', 'Energy'),
    'CIVI': ('Civitas Resources Inc', 'Energy'),
    'MTDR': ('Matador Resources Co', 'Energy'),
    'OVV': ('Ovintiv Inc', 'Energy'),
    'PR': ('Permian Resources Corp', 'Energy'),
    'RRC': ('Range Resources Corp', 'Energy'),
    'SM': ('SM Energy Co', 'Energy'),
    'DTM': ('DT Midstream Inc', 'Energy'),
    'KNTK': ('Kinetik Holdings Inc', 'Energy'),
    'WES': ('Western Midstream Partners LP', 'Energy'),
    'ARIS': ('Aris Water Solutions Inc', 'Energy'),
    'ENLC': ('EnLink Midstream LLC', 'Energy'),
    'STR': ('Sitio Royalties Corp', 'Energy'),
    'WTTR': ('Select Water Solutions Inc', 'Energy'),
    'FL': ('Foot Locker Inc', 'Consumer Discretionary'),
    'JWN': ('Nordstrom Inc', 'Consumer Discretionary'),
    'SKX': ('Skechers USA Inc', 'Consumer Discretionary'),
    'RH': ('RH', 'Consumer Discretionary'),
    'SHOO': ('Steven Madden Ltd', 'Consumer Discretionary'),
    'URBN': ('Urban Outfitters Inc', 'Consumer Discretionary'),
    'UAA': ('Under Armour Inc', 'Consumer Discretionary'),
    'VFC': ('VF Corp', 'Consumer Discretionary'),
    'CPRI': ('Capri Holdings Ltd', 'Consumer Discretionary'),
    'COLM': ('Columbia Sportswear Co', 'Consumer Discretionary'),
    'CROX': ('Crocs Inc', 'Consumer Discretionary'),
    'ANF': ("Abercrombie & Fitch Co", 'Consumer Discretionary'),
    'DKS': ("Dick's Sporting Goods Inc", 'Consumer Discretionary'),
    'LEVI': ('Levi Strauss & Co', 'Consumer Discretionary'),
    'GAP': ('Gap Inc', 'Consumer Discretionary'),
    'PVH': ('PVH Corp', 'Consumer Discretionary'),
    'BRBR': ('BellRing Brands Inc', 'Consumer Staples'),
    'MZTI': ('The Marzetti Company', 'Consumer Staples'),
    'THS': ('TreeHouse Foods Inc', 'Consumer Staples'),
    'KLG': ('WK Kellogg Co', 'Consumer Staples'),
    'HAIN': ('The Hain Celestial Group Inc', 'Consumer Staples'),
    'INGR': ('Ingredion Inc', 'Consumer Staples'),
    'POST': ('Post Holdings Inc', 'Consumer Staples'),
    'FLO': ('Flowers Foods Inc', 'Consumer Staples'),
}

def main():
    bak = SRC.replace('.json', '_backup_20260930_1030_pre_peerrefresh.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}

    # sanity: every new target is either an existing node or in NEW_NODES
    for src, (filing, peers) in NEW.items():
        for t in peers:
            assert t in by_ticker or t in NEW_NODES, f'{src}: unknown target {t}'
    print('target mapping OK:', sum(len(p) for _, p in NEW.values()), 'targets')

    # add missing peer-only nodes (peer-only nodes omit isSource, per existing convention)
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

    # replace edges per source, asserting before/after sets
    for src, (filing, peers) in NEW.items():
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        old_filings = sorted(set(e['filing'] for e in old))
        print(f'{src}: old {len(old)} edges {old_targets} filings={old_filings}')
        edges = [e for e in edges if e['source'] != src]
        for t in peers:
            edges.append({'source': src, 'target': t, 'year': 2026,
                          'group_type': 'primary', 'filing': filing})
        new_check = sorted(e['target'] for e in edges if e['source'] == src)
        assert new_check == sorted(peers), f'{src}: new edge set mismatch'
        assert len(set(new_check)) == len(new_check), f'{src}: duplicate targets'
        print(f'{src}: new {len(peers)} edges filing={filing}')

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
    # sources stays 472: the 8 refreshes replace existing companies' proxies
    assert net['metadata']['sources'] == ['472 DEF 14A proxy statements from S&P 500 companies']

    with open(SRC, 'w') as f:
        json.dump(net, f, indent=1)
    print('wrote', SRC, '| nodes:', len(nodes), '| edges:', len(edges))

if __name__ == '__main__':
    main()
