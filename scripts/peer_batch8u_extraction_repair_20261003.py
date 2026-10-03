#!/usr/bin/env python3
"""Peer-network batch-8u orphan extraction repair (2026-10-03 15:30 PDT run).

Follow-up to batch-8t (2026-10-03 14:00), which extracted the fileable
cohort and queued this run: the 12 remaining tracked S&P 500 companies
with out_degree 0 (12 pending after batch-8t: FRT 4 / KKR 4 / WST 4 /
PSKY 4 / IPG 3 / DAY 2 / AOS 2 / BRK-B 1 / ERIE 1 / IBKR 1 / MO 1 /
ARES 1).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (CIKs verified
against the submissions name field; IPG's CIK is 0000051644, DAY's is
0001725057), filing HTML fetched with User-Agent "Kit/1.0
(factoryfactorykit@gmail.com)" (sequential, ~3s pacing; non-padded CIK
in Archive URLs; primaryDocument from each filing's submissions
primaryDocument field). Peer sections transcribed verbatim. Evidence in
goal hidden_files/peer-batch8u-20261003/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8u_submissions.json + batch8u_docs.json
(accession/URL map) + verified_absent_batch8u.txt; filing HTMLs
persisted to the goal dir AT download time (the batch-8h
/tmp-peersweep-wipe lesson).

Acquisition-triage (this run):
  IPG: Omnicom completed its acquisition Nov 26, 2025 ($9B; IPG now a
    wholly owned subsidiary). DEF 14A 2024-04-12 is the LAST
    AUTHORITATIVE proxy pre-go-private (no 2025 DEF 14A filed,
    merger-pending). 2022 Comparator Group stored verbatim per the
    HOLX/batch-8r acquisition-absorption precedent.
  DAY: Thoma Bravo completed its $12.3B take-private Feb 4, 2026
    ($70/share; delisted NYSE/TSX). DEF 14A 2025-03-13 is the LAST
    AUTHORITATIVE proxy pre-go-private. The operative "Peer Group Used
    in Determining TDC October 2024 - Present" (17 cos, used Oct 2024 +
    Mar 2025) is stored; the superseded 2023 group is not.

Repairs (4 extractions + 8 verified-absent):

  WST   0 -> 15 (DEF 14A 2026-03-12; 2025 Business Segment Group verbatim.
        The Broad Talent Market Group is an unnamed WTW database sampling
        -> UNSTORED. No fingerprint targets -> no marks.)
  MO    0 -> 21 (DEF 14A 2026-04-02; 2025 Compensation Survey Group
        verbatim. Kellanova (K) named -> stored verbatim per CTRA/MRO
        precedent (taken private but named). Filing spells "The Proctor
        & Gamble Company" (sic) -> maps to network canonical PG.
        Fingerprint targets GIS/HSY/PG are all Consumer Staples home set;
        MO is Consumer Staples -> no marks.)
  IPG   0 -> 21 (DEF 14A 2024-04-12, last pre-Omnicom; 2022 Comparator
        Group verbatim - no 2023/2024 update in the final filing.
        Acquired names stored verbatim: ATVI (Microsoft 2023), NLSN
        (taken private 2022). Filing spells "Quarate Retail Group Inc."
        (sic) -> QRTEA; "Thomson-Reuters Corporation" -> TRI. No
        fingerprint targets -> no marks.)
  DAY   0 -> 17 (DEF 14A 2025-03-13, last pre-Thoma Bravo; Oct 2024 -
        Present peer group verbatim (the operative set for the final
        comp decisions). No fingerprint targets -> no marks.)

  KKR   verified-absent: DEF 14A 2026-02-27 contains ZERO mentions of
        peer/benchmark/comparable-companies/market-data/compensation-
        consultant. No CD&A peer disclosure of any kind.
        isSource None -> False.
  AOS   verified-absent: DEF 14A 2026-03-04 states verbatim "We did not
        rely on a specific subgroup of peer companies within that
        database" (WTW 800-company survey). isSource None -> False.
  BRK-B verified-absent: DEF 14A 2026-03-13 states verbatim "It is
        difficult to identify a Berkshire peer group" / "it would be
        difficult to develop a peer group of companies similar to
        Berkshire." S&P 500 Property & Casualty Index is PvP-only.
        isSource None -> False.
  IBKR  verified-absent: DEF 14A 2026-03-11 CD&A has zero peer/benchmark/
        survey mentions; the only "peer group" is the S&P 500 index for
        PvP (index-only). isSource None -> False.
  FRT   verified-absent: DEF 14A 2026-03-27 - "For 2025 compensation, we
        did not use any compensation consultant"; no named peer group
        (only BBRESHOP Index for PvP TSR). isSource None -> False.
  ARES  verified-absent: DEF 14A 2026-04-21 - the only "peer group" is
        the Dow Jones U.S. Asset Managers Index for PvP TSR (index-only);
        Korn Ferry's "peer companies" (Dec 2023) unnamed.
        isSource None -> False.
  PSKY  verified-absent: NO DEF 14A HAS EVER BEEN FILED (CIK 0002041610;
        entity formed Aug 2025; only 8-Ks/10-Qs/one 10-K/merger forms).
        isSource None -> False.
  ERIE  verified-absent: NO DEF 14A SINCE 2008-03-24 (CIK 0000922621;
        recent filings are Form 4s only). isSource None -> False.

New nodes: 13 (all peer-only, tickers SEC-verified via
company_tickers_exchange.json 2026-10-03) - registered in
PEER_ONLY_NODES and in mark_verified REPAIR_SCRIPTS BEFORE the repair
ran (the batch-5 / batch-8h lessons held):
  ATR (AptarGroup, Health Care), HAE (Haemonetics, Health Care),
  IART (Integra LifeSciences, Health Care) [WST group];
  ATVI (Activision Blizzard, Communication Services),
  PUBGY (Publicis Groupe SA ADR, Communication Services),
  LGF (Lions Gate, Communication Services), QRTEA (Qurate Retail,
  Consumer Discretionary), GCI (Gannett, Communication Services),
  NLSN (Nielsen, Communication Services), WPP (WPP plc ADR,
  Communication Services) [IPG group];
  BILL (BILL Holdings, Information Technology), RNG (RingCentral,
  Information Technology), FIVN (Five9, Information Technology)
  [DAY group].
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'ATR': ('AptarGroup, Inc.', 'Health Care'),
    'HAE': ('Haemonetics Corporation', 'Health Care'),
    'IART': ('Integra LifeSciences Holdings Corp.', 'Health Care'),
    'ATVI': ('Activision Blizzard, Inc.', 'Communication Services'),
    'PUBGY': ('Publicis Groupe SA', 'Communication Services'),
    'LGF': ('Lions Gate Entertainment Corp.', 'Communication Services'),
    'QRTEA': ('Qurate Retail Group Inc.', 'Consumer Discretionary'),
    'GCI': ('Gannett Co., Inc.', 'Communication Services'),
    'NLSN': ('Nielsen Holdings plc', 'Communication Services'),
    'WPP': ('WPP plc', 'Communication Services'),
    'BILL': ('BILL Holdings, Inc.', 'Information Technology'),
    'RNG': ('RingCentral, Inc.', 'Information Technology'),
    'FIVN': ('Five9, Inc.', 'Information Technology'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'WST': ('DEF 14A 2026-03-12',
            ['A', 'ATR', 'BIO', 'XRAY', 'EW', 'HAE', 'HOLX', 'IDXX',
             'ITGR', 'IART', 'RMD', 'RVTY', 'STE', 'TFX', 'COO']),
    'MO': ('DEF 14A 2026-04-02',
           ['MMM', 'GIS', 'MCD', 'ABT', 'HSY', 'MRK', 'BMY', 'K',
            'MDLZ', 'KO', 'KVUE', 'PEP', 'CL', 'KDP', 'PM', 'CAG',
            'KMB', 'PG', 'LLY', 'KHC', 'SBUX']),
    'IPG': ('DEF 14A 2024-04-12',
            ['ATVI', 'IAC', 'PUBGY', 'CTSH', 'LGF', 'QRTEA', 'EBAY',
             'NWSA', 'SBGI', 'EA', 'NXST', 'SIRI', 'FOXA', 'NLSN',
             'TTWO', 'GCI', 'OMC', 'TRI', 'IT', 'PARA', 'WPP']),
    'DAY': ('DEF 14A 2025-03-13',
            ['BILL', 'GWRE', 'PTC', 'DDOG', 'HUBS', 'RNG', 'DT',
             'PAYX', 'SMAR', 'ESTC', 'PAYC', 'TYL', 'FICO', 'PCTY',
             'WDAY', 'FIVN', 'PEGA']),
}

# verified-absent sources: expected no stored edges, flip isSource None->False
ABSENT = ['KKR', 'AOS', 'BRK-B', 'IBKR', 'FRT', 'ARES', 'PSKY', 'ERIE']

# never-extracted sources: expected old edge set is EMPTY (assertion guard)
EXPECTED_OLD = {src: [] for src in NEW}


def main():
    bak = SRC.replace('.json', '_backup_20261003_1530_pre_batch8u.json')
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

    # 2. verified-absent sources: assert no edges, flip isSource
    for t in ABSENT:
        old = [e for e in edges if e['source'] == t]
        assert old == [], f'{t}: unexpected stored edges: {old}'
        assert by_ticker[t].get('isSource') is None, f'{t}: already classified'
        by_ticker[t]['isSource'] = False
    print('verified-absent:', ', '.join(
        f'{t} isSource None -> False' for t in ABSENT))

    # 3. assert (empty) old edge sets + add verbatim edges for the sources
    for src, (filing, peers) in NEW.items():
        assert src in by_ticker, f'{src}: not a node'
        for t in peers:
            assert t in by_ticker, f'{src}: unknown target {t}'
        assert src not in peers, f'{src}: self-edge'
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        assert old_targets == sorted(EXPECTED_OLD[src]), \
            f'{src}: old edge set changed: {old_targets}'
        year = int(filing.rsplit(' ', 1)[1].split('-')[0])
        for t in peers:
            edges.append({'source': src, 'target': t, 'year': year,
                          'group_type': 'primary', 'filing': filing})
        new_check = sorted(e['target'] for e in edges if e['source'] == src)
        assert new_check == sorted(peers), f'{src}: new edge set mismatch'
        assert len(set(new_check)) == len(new_check), f'{src}: duplicates'
        by_ticker[src]['isSource'] = True
        print(f'{src}: {len(old)} old -> {len(peers)} new ({filing})')

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
