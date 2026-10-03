#!/usr/bin/env python3
"""Peer-network batch-8t orphan extraction repair (2026-10-03 14:00 PDT run).

Follow-up to batch-8s (2026-10-03 11:30), which extracted the
acquisition-triage cohort and queued this run: the fileable cohort of
the 19 remaining tracked S&P 500 companies with out_degree 0 (19
pending after batch-8s: T 13 / CAH 11 / XOM 7 / DELL 6 / APH 5 / BX 4 /
EXPD 4 / FRT 4 / KKR 4 / PSKY 4 / WST 4 / IPG 3 / AOS 2 / DAY 2 /
ARES 1 / BRK-B 1 / ERIE 1 / IBKR 1 / MO 1).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (CIKs verified
against the submissions name field; APH's CIK is 0000820313 - the
from-memory 0000820319 does NOT exist in EDGAR), filing HTML fetched
with User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential,
~3s pacing; non-padded CIK in Archive URLs; primaryDocument from each
filing's submissions primaryDocument field). Peer sections transcribed
verbatim. Evidence in goal hidden_files/peer-batch8t-20261003/
<TICKER>_peer.txt (verbatim transcriptions) + batch8t_filings.json
(accession/URL/status map); filing HTMLs persisted to the goal dir AT
download time (the batch-8h /tmp-peersweep-wipe lesson).

Repairs (4 extractions + 3 verified-absent):

  T     0 -> 16 (DEF 14A 2026-03-23; 2025 AT&T Peer Group verbatim, same
        as 2024. 2023 Performance Share Grant relative-TSR group +
        S&P 500 Communication Services PvP index are performance/
        index-only -> UNSTORED. No marks: T is Communication Services,
        CHTR fingerprint target home set includes Communication
        Services.)
  CAH   0 -> 24 (DEF 14A 2026-09-21; fiscal 2026 Comparator Group
        verbatim, unchanged from prior year. WBA named in the group ->
        stored verbatim per the CTRA/MRO precedent (taken private but
        named). FY2027 prospective changes (HCA/HUM in; BSX/SYK/UNH
        out) documented, unstored. PvP / PSU relative-TSR = S&P 500
        Health Care Index -> index-only, UNSTORED. CAH->TGT is a
        genuine cross-sector filing edge -> mark via
        mark_verified_cross_sector.)
  XOM   0 -> 12 (DEF 14A 2026-04-08; Compensation Benchmark Companies
        verbatim (Frequently Used Terms; same as 2025 proxy; unchanged
        since 2017). Integrated Oil Company (IOC) peers
        (BP/Chevron/Shell/TotalEnergies) are SAFETY-performance
        comparators -> UNSTORED. GE Aerospace maps to network
        canonical GE. No marks: XOM is Energy, CVX fingerprint target
        home set is Energy.)
  EXPD  0 -> 14 (DEF 14A 2026-03-24; CD&A benchmark-data companies
        verbatim ("used on a limited basis to review base salaries and
        other compensation information") -> stored as the operative
        comp set with the limited-basis nuance documented in
        EXPD_peer.txt. PvP peer = Dow Jones Transportation Average
        Index -> index-only, UNSTORED. No fingerprint targets in the
        group -> no marks.)

  BX    verified-absent: NO DEF 14A EXISTS. Full filing history for
        CIK 0001393818 (730 filings to 2007, both submissions files) +
        EDGAR full-text cik:0001393818/forms=DEF 14A 2020-2026 search
        + SEC company search return zero 14A filings (one DEF 14C
        2014-07-21 only). isSource None -> False.
  DELL  verified-absent: DEF 14A 2026-05-15 discloses NO named comp
        peer group (generic "peer companies" / "market reference
        points"; rTSR = S&P 500 IT Index performance-only; PvP peer =
        same index). "peers" x0, "comparison group" x0.
        isSource None -> False.
  APH   verified-absent: DEF 14A 2026-04-08 discloses NO named comp
        peer group (Meridian "companies similar in size" unnamed +
        general surveys; only named group = PvP DJUSEC index).
        isSource None -> False.

New nodes: 1 (ACH - Accendra Health Inc., Health Care - the renamed
Owens & Minor, Inc.; ticker SEC-verified via
company_tickers_exchange.json 2026-10-03) - registered in
PEER_ONLY_NODES and in mark_verified_cross_sector REPAIR_SCRIPTS
BEFORE the repair ran (the batch-5 / batch-8h lessons held).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'ACH': ('Accendra Health Inc.', 'Health Care'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'T': ('DEF 14A 2026-03-23',
          ['BA', 'CSCO', 'GE', 'IBM', 'NFLX', 'CRM', 'UPS', 'WMT',
           'CHTR', 'CMCSA', 'GM', 'INTC', 'ORCL', 'TMUS', 'VZ', 'DIS']),
    'CAH': ('DEF 14A 2026-09-21',
            ['ABT', 'JNJ', 'ACH', 'KR', 'BAX', 'LH', 'BDX', 'MCK',
             'BSX', 'MDT', 'COR', 'SYK', 'CI', 'SYY', 'CVS', 'TGT',
             'DHR', 'TMO', 'ELV', 'UPS', 'FDX', 'UNH', 'HSIC', 'WBA']),
    'XOM': ('DEF 14A 2026-04-08',
            ['T', 'BA', 'CVX', 'F', 'GE', 'GM', 'IBM', 'JNJ',
             'PFE', 'PG', 'RTX', 'VZ']),
    'EXPD': ('DEF 14A 2026-03-24',
             ['ALK', 'CHRW', 'CSX', 'EXPE', 'GXO', 'JBHT', 'KNX',
              'NSC', 'ODFL', 'R', 'SNDR', 'TFII', 'UNP', 'XPO']),
}

# verified-absent sources: expected no stored edges, flip isSource None->False
ABSENT = ['BX', 'DELL', 'APH']

# never-extracted sources: expected old edge set is EMPTY (assertion guard)
EXPECTED_OLD = {src: [] for src in NEW}


def main():
    bak = SRC.replace('.json', '_backup_20261003_1400_pre_batch8t.json')
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
