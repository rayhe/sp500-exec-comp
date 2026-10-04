#!/usr/bin/env python3
"""Peer-network batch-15 single-edge adjudication (2026-10-04 15:30 PDT run).

First batch of the <10 tier under the batch-8y tier rule: single-edge
adjudication against the DEF 14A (drop or mark verified, group untouched).
All 18 pending sources with total_out < 10 (11 at 9, 1 at 8, 2 at 6, 2 at 5,
1 at 4, 1 at 2), covering 20 queued cross-sector fingerprint edges (CL and
COST each carry two queued edges from the same filing; both adjudicated
separately against that one filing). Filing-equality asserted on every
source (drop and mark) before mutation - batch-13 hardening.

Adjudications (19 DROPPED, 1 MARKED VERIFIED):
- CL->IP (DEF 14A 2026-03-25): zero "International Paper" mentions.
- CL->TGT (DEF 14A 2026-03-25): zero "Target Corporation"; bare "Target"
  hits are compensation-jargon ("target compensation", "target bonus") -
  compensation-jargon collision class (batch-12 ATO class).
- COST->TGT (DEF 14A 2025-12-04): FILING-GENUINE -> marked verified.
  "Target Corporation" verbatim in "obtained from proxy statements for the
  following peer companies: Walmart Inc., The Home Depot, Inc., Lowe's
  Companies, Inc., The TJX Companies, Inc., Target Corporation, The Kroger
  Company, Best Buy Inc., BJ's Wholesale Club Holdings, Inc., CVS Health
  Corporation, Ross Stores Inc., and Wesfarmers Ltd.".
  NOTE: this mark was REVERTED the same run by
  scripts/peer_batch15b_revert_cost_tgt_mark_20261004.py -- COST (Consumer
  Staples) is inside TGT's home-sector set (FINGERPRINT_TARGETS["TGT"] =
  {"Consumer Staples", "Consumer Discretionary"}), so COST->TGT was never a
  fingerprint-queue member and the mark violated invariant (b). The edge
  itself is genuine per the filing and stays; only the queue-pattern mark
  was removed. Batch-15's scope came from the 14:14 PT iteration-log
  candidate list, computed with the strict sector-inequality definition
  over the 6 batch-8y-era targets rather than the guard's
  FINGERPRINT_TARGETS table -- CL->TGT was likewise out of queue scope
  (its drop stands: zero "Target Corporation" mentions, so the edge was
  fabricated regardless of queue membership). Future batches must derive
  scope from the guard's table (the check_metadata_consistency.py
  fingerprint-queue warning line), not the log's candidate list.
- COST->PSA (DEF 14A 2025-12-04): zero "Public Storage".
- WBD->IP (DEF 14A 2026-04-30): zero "International Paper".
- SCHW->CHTR (DEF 14A 2026-04-06): zero "Charter Communications"; 5 bare
  "Charter" hits all committee-charter boilerplate - charter-boilerplate
  vector (11th catch).
- ABBV->COF (DEF 14A 2026-03-23): zero "Capital One".
- OKE->CHTR (DEF 14A 2026-04-01): zero "Charter Communications"; 10 bare
  "Charter" hits all committee-charter boilerplate - charter-boilerplate
  vector (12th catch).
- HSIC->IP (DEF 14A 2026-04-08): zero "International Paper".
- JKHY->COF: adjudicated against the STORED edge's filing (DEF 14A
  2025-10-02, fetched as JKHY_def14a_2025.htm; latest is 2026-10-02).
  Single "Capital One" hit is a director bio (Mr. Campbell's executive
  roles at Capital One) - director-bio vector (4th catch).
- RF->CHTR (DEF 14A 2026-03-23): zero "Charter Communications"; 92 bare
  "Charter" hits all Certificate-of-Incorporation / committee-charter
  boilerplate - charter-boilerplate vector (13th catch).
- CHRW->TGT (DEF 14A 2026-03-24): single "Target Corporation" hit is an
  executive bio (Global SVP HR 2016-2017 at Target Corporation) -
  exec-bio vector (director-bio class, 5th catch).
- DLTR->GIS (DEF 14A 2026-05-01): zero "General Mills".
- MTCH->TGT (DEF 14A 2026-04-30): zero "Target Corporation"; bare "Target"
  hits are compensation-jargon ("target value", "at target").
- AVB->TGT (DEF 14A 2026-04-06): zero "Target Corporation"; bare "Target"
  hits are compensation-jargon ("target compensation"). AVB's CIK
  (915912, AVALONBAY COMMUNITIES INC) was fetched directly - the batch-8y
  company_tickers_exchange.json snapshot has no AVB row at all.
- CINF->PSA (DEF 14A 2026-03-18): zero "Public Storage".
- OMC->TGT (DEF 14A 2026-03-26): zero "Target Corporation"; bare "Target"
  hits are compensation-jargon ("target incentive").
- DUK->IP (DEF 14A 2026-03-20): zero "International Paper".
- MET->PSA (DEF 14A 2026-04-29): zero "Public Storage".
- AMP->CHTR (DEF 14A 2026-03-20): zero "Charter Communications"; 7 bare
  "Charter" hits all committee-charter boilerplate - charter-boilerplate
  vector (14th catch).

No REPAIR_SCRIPTS registration: the single-filing invariant requires a
wholesale-replaced edge set, which single-edge adjudication does not
produce (batch-9 process note (d) class).

Evidence: goal hidden_files/peer-batch15-20261004/ (<T>_def14a.htm +
<T>_def14a.txt + JKHY_def14a_2025.htm/txt + batch15_submissions.json +
fetch_def14a.py + prescan.py + render_check.py + d3.min.js).
"""

import json
import shutil
from collections import Counter

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# source -> list of (dropped target, adjudicating filing)
DROPS = {
    'CL':   [('IP',  'DEF 14A 2026-03-25'), ('TGT', 'DEF 14A 2026-03-25')],
    'COST': [('PSA', 'DEF 14A 2025-12-04')],
    'WBD':  [('IP',  'DEF 14A 2026-04-30')],
    'SCHW': [('CHTR', 'DEF 14A 2026-04-06')],
    'ABBV': [('COF', 'DEF 14A 2026-03-23')],
    'OKE':  [('CHTR', 'DEF 14A 2026-04-01')],
    'HSIC': [('IP',  'DEF 14A 2026-04-08')],
    'JKHY': [('COF', 'DEF 14A 2025-10-02')],
    'RF':   [('CHTR', 'DEF 14A 2026-03-23')],
    'CHRW': [('TGT', 'DEF 14A 2026-03-24')],
    'DLTR': [('GIS', 'DEF 14A 2026-05-01')],
    'MTCH': [('TGT', 'DEF 14A 2026-04-30')],
    'AVB':  [('TGT', 'DEF 14A 2026-04-06')],
    'CINF': [('PSA', 'DEF 14A 2026-03-18')],
    'OMC':  [('TGT', 'DEF 14A 2026-03-26')],
    'DUK':  [('IP',  'DEF 14A 2026-03-20')],
    'MET':  [('PSA', 'DEF 14A 2026-04-29')],
    'AMP':  [('CHTR', 'DEF 14A 2026-03-20')],
}

# source -> (marked target, filing, batch)
MARKS = {
    'COST': ('TGT', 'DEF 14A 2025-12-04', 'batch-15'),
}


def main():
    bak = SRC.replace('.json', '_backup_20261004_1530_pre_batch15.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}
    n_before = len(edges)
    n_drops = 0

    # 1. assert + drop each adjudicated edge
    for src, drops in sorted(DROPS.items()):
        for tgt, filing in drops:
            assert src in by_ticker, f'{src}: not a node'
            assert tgt in by_ticker, f'{tgt}: not a node'
            matches = [e for e in edges
                       if e['source'] == src and e['target'] == tgt]
            assert len(matches) == 1, \
                f'{src}->{tgt}: expected 1 edge, found {len(matches)}'
            # adjudicating filing must match the stored edge filing
            assert matches[0].get('filing') == filing, \
                f'{src}->{tgt}: stored filing {matches[0].get("filing")} != {filing}'
            edges = [e for e in edges
                     if not (e['source'] == src and e['target'] == tgt)]
            n_drops += 1
            print(f'dropped {src}->{tgt} ({filing})')

    assert n_before - len(edges) == n_drops, 'drop count mismatch'
    print(f'edges: {n_before} -> {len(edges)} ({n_drops} dropped)')

    # 2. mark filing-genuine edges (edge stays; verified list grows)
    vc = net['metadata'].get('verified_cross_sector', [])
    for src, (tgt, filing, batch) in sorted(MARKS.items()):
        matches = [e for e in edges
                   if e['source'] == src and e['target'] == tgt]
        assert len(matches) == 1, \
            f'{src}->{tgt}: expected 1 live edge for marking'
        assert matches[0].get('filing') == filing, \
            f'{src}->{tgt}: stored filing {matches[0].get("filing")} != {filing}'
        assert not any(v['source'] == src and v['target'] == tgt for v in vc), \
            f'{src}->{tgt}: already marked'
        vc.append({'source': src, 'target': tgt,
                   'filing': filing, 'batch': batch})
        print(f'marked verified {src}->{tgt} ({filing})')
    vc.sort(key=lambda v: (v['source'], v['target']))
    net['metadata']['verified_cross_sector'] = vc
    print(f'verified_cross_sector: {len(vc)} entries')

    # 3. recompute degrees exactly; report newly-zero-degree nodes
    indeg = Counter(e['target'] for e in edges)
    outdeg = Counter(e['source'] for e in edges)
    for e in edges:
        assert e['source'] in by_ticker and e['target'] in by_ticker, \
            f"dangling edge {e['source']}->{e['target']}"
    for x in nodes:
        ni, no = indeg.get(x['ticker'], 0), outdeg.get(x['ticker'], 0)
        if ni == 0 and no == 0:
            print(f'NOTE: {x["ticker"]} now isolated (in=0, out=0)')
        x['in_degree'], x['out_degree'] = ni, no
        od = outdeg.get(x['ticker'], 0)
        if od > 0:
            assert x.get('isSource') is True, \
                f"{x['ticker']}: edges but not isSource"
        if x.get('isSource') is False:
            assert od == 0, f"{x['ticker']}: isSource False but has edges"

    # 4. metadata from actuals
    net['nodes'] = nodes
    net['edges'] = edges
    nsrc = sum(1 for x in nodes if x.get('isSource') is True)
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-10-04'
    net['metadata']['last_dq_repair'] = '2026-10-04'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
