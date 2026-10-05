#!/usr/bin/env python3
"""Peer-network batch-16 single-edge adjudication (2026-10-04 18:00 PDT run).

FINAL batch of the fingerprint queue: the last 4 pending cross-sector
fingerprint-target edges per the guard's fingerprint-queue warning line
(FINGERPRINT_TARGETS table = scope source, per process note (a)).
Single-edge adjudication against each stored edge's DEF 14A filing
(drop or mark verified, group untouched). Filing-equality asserted on
every source (drop and mark) before mutation - batch-13 hardening.
All four stored filings are also the latest DEF 14A (pinned=False), so
the batch-15 note (b) JKHY-class pin was not needed.

Adjudications (2 DROPPED, 2 MARKED VERIFIED):
- FTNT->NDAQ (DEF 14A 2026-04-29): zero "Nasdaq Inc"/"Nasdaq, Inc"; 10 bare
  "Nasdaq" hits all Nasdaq Stock Market LLC listing boilerplate (broker
  voting rules, committee-independence standards, equity-grant timing,
  closing-price footnotes) - listing-exchange vector (new catch; compare
  the charter-boilerplate class, same shape: exchange/committee name as
  governance language, never a company). The 2025 peer group is printed
  verbatim as 19 tech companies (Akamai/Marvell/Arista/NetApp/Autodesk/
  Palo Alto Networks/Cadence/ServiceNow/Check Point/Snowflake/Cloudflare/
  Synopsys/CrowdStrike/Workday/Datadog/Zoom/Digital Realty/Zscaler/
  Equinix); Nasdaq is not among them. DROP.
- HAS->HSY (DEF 14A 2026-04-17): FILING-GENUINE -> marked verified.
  "The Hershey Company" verbatim in the 2025 compensation peer group
  list (Crocs, Mattel, The Hershey Company, Electronic Arts, Roblox,
  The J.M. Smucker Company, iHeartMedia, Spin Master, Topgolf Callaway,
  Live Nation, ...). NOTE: the same filing discloses HSY was REMOVED
  from the 2026 peer group (talent-competition realignment); the edge is
  genuinely present in the filing's 2025 list and the stored edge's
  adjudication is filing-verbatim, so the mark is correct under the
  filing-equality standard (compare JKHY, batch-15). No TSR-supplement
  second group here.
- MCD->PG (DEF 14A 2026-04-07): FILING-GENUINE -> marked verified.
  "The Procter & Gamble Company" verbatim in the 2025 Peer Companies
  list (Coca-Cola, Colgate, Kraft-Heinz, Marriott, Mastercard, Mondelez,
  Nike, PepsiCo, The Procter & Gamble Company, Starbucks, Target, Visa,
  Wal-Mart, Walt Disney, Yum!). Scope check (batch-15b invariant (b)):
  MCD->PG is in the guard's pending fingerprint-queue list, so the mark
  is in scope. The edge stays; verified_cross_sector grows.
- ULTA->BLK (DEF 14A 2026-04-22): zero "BlackRock, Inc."; 2 bare
  "BlackRock" hits both in the 5%-stockholder Schedule 13G table
  (9% owner) - 13G/5%-holder vector (institutional-shareholder
  false-positive class, 15th cross-sector catch of the shareholder-as-
  peer shape). The 2025 Compensation Peer Group is printed verbatim as
  13 retailers (AutoZone/Gap/Ross/Bath & Body Works/Lululemon/Tractor
  Supply/Burlington/O'Reilly/V.F. Corp/Dick's/PVH/Williams-Sonoma/
  Foot Locker); BlackRock is not among them. DROP.

Queue state after this batch: fingerprint queue fully drained
(0 pending, 79 verified-genuine).

No REPAIR_SCRIPTS registration: the single-filing invariant requires a
wholesale-replaced edge set, which single-edge adjudication does not
produce (batch-9 process note (d) class).

Evidence: goal hidden_files/peer-batch16-20261004/ (<T>_def14a.htm +
<T>_def14a.txt + batch16_submissions.json + fetch_def14a.py + prescan.py).
"""
import json
import shutil
from collections import Counter

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# source -> list of (dropped target, adjudicating filing)
DROPS = {
    'FTNT': [('NDAQ', 'DEF 14A 2026-04-29')],
    'ULTA': [('BLK',  'DEF 14A 2026-04-22')],
}

# source -> (marked target, filing, batch)
MARKS = {
    'HAS': ('HSY', 'DEF 14A 2026-04-17', 'batch-16'),
    'MCD': ('PG',  'DEF 14A 2026-04-07', 'batch-16'),
}


def main():
    bak = SRC.replace('.json', '_backup_20261004_1800_pre_batch16.json')
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
