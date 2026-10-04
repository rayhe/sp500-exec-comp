#!/usr/bin/env python3
"""Peer-network batch-9 single-edge adjudication (2026-10-04 03:30 PDT run).

First batch of the 10-19 tier under the batch-8y tier rule: single-edge
adjudication against the latest DEF 14A (drop or mark verified, group
untouched). The 13 heaviest one-edge sources (total_out 18-19), each with
exactly one queued cross-sector fingerprint edge, adjudicated filing-verbatim
via EDGAR (SEC Archives curl open this run; Kit/1.0 UA; sequential ~3s pacing;
CIKs from company_tickers_exchange.json, cross-checked against the submissions
name field; no subagents per the task execution rule). Evidence: goal
hidden_files/peer-batch9-20261004/ (<TICKER>_def14a.htm + <TICKER>_def14a.txt
verbatim text + batch9_submissions.json accession/URL map + batch9_ciks.json).

Adjudications (all 13 DROPPED - none filing-genuine):
- CPB->CHTR: "Charter" hits are corporate-charter boilerplate; Campbell's comp
  peer group is food/beverage/consumer-products cos (DEF 14A 2025-10-08).
- ED->GIS: zero "General Mills" mentions in the full filing (DEF 14A 2026-04-08).
- PNC->MSFT: "Microsoft" hits are Microsoft Copilot AI-platform mentions; the
  2025 Performance Peer Group is 11 banks (BAC/COF/CFG/FITB/JPM/KEY/MTB/RF/TFC/
  USB/WFC) and the Compensation Peer Group is those + 10 more financial
  institutions, insurers excluded (DEF 14A 2026-03-11).
- ROK->GIS: 2025 Compensation Peer Group verbatim 18 (AMETEK/Amphenol/Autodesk/
  Corning/Dover/Eaton/Emerson/Fortive/Intuit/Keysight/NetApp/PANW/Parker-Hannifin/
  Seagate/Synopsys/TE Connectivity/Trimble/Zebra); GIS absent (DEF 14A 2025-12-22).
  NOTE: stored set also carries AMAT+WTW (not in the filing) and lacks GLW+TEL -
  flagged for a future wholesale batch; group untouched per tier rule.
- SNPS->GIS: zero "General Mills" mentions in the full filing (DEF 14A 2026-02-19).
- ADSK->PFG: FY2026 comp peer group verbatim 18 (Adobe/Akamai/ANSYS/Block/Cadence/
  DocuSign/EA/Fortinet/Gen Digital/Intuit/NetApp/PANW/PTC/Salesforce/ServiceNow/
  Synopsys/Workday); "Principal" hits are officer-title boilerplate, no
  "Principal Financial" anywhere (DEF 14A 2026-05-06).
- AMD->GIS: zero "General Mills" mentions in the full filing (DEF 14A 2026-03-27).
- CAT->IP: zero "International Paper" mentions in the full filing (DEF 14A 2026-04-30).
- CDNS->GIS: zero "General Mills" mentions in the full filing (DEF 14A 2026-03-25).
- DHI->PSA: zero "Public Storage" mentions in the full filing; Performance Peer
  Group (8 homebuilders) + Benchmarking Peer Group dual-role pattern
  (DEF 14A 2025-12-10).
- IP->GIS: the single "General Mills" hit is a director bio; 2025 CCG verbatim 18
  (BALL/BERY/BG/CARR/CCK/CMI/ETN/EMR/GD/JCI/LYB/NOC/NUE/PKG/PH/PPG/SLB/SW)
  (DEF 14A 2026-03-27). NOTE: stored set differs (DD/DOW/ECL/EMN/AVY in;
  BG/BERY/CCK/NOC/SLB/SW out) - future wholesale candidate; group untouched.
- NI->IP: zero "International Paper" mentions in the full filing (DEF 14A 2026-03-30).
- PRU->TGT: "Target" hits are target-compensation language; the Compensation Peer
  Group is 20 retirement/insurance/asset-management/custody-bank cos
  (DEF 14A 2026-03-26).

Tier rule (batch-8y, for future runs): total_out >= 20 -> full verbatim re-read
+ wholesale replace (batches 8y/8z, done); 10-19 -> single-edge adjudication
(this batch and following); <10 -> single-edge adjudication, lowest priority.

This is a DROP-ONLY batch: no new nodes, no REPAIR_SCRIPTS registration (the
mark_verified single-filing invariant requires a wholesale-replaced edge set;
dropped edges leave the queue naturally because queued_edges() scans live edges).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# source -> (dropped target, adjudicating filing)
DROPS = {
    'CPB': ('CHTR', 'DEF 14A 2025-10-08'),
    'ED': ('GIS', 'DEF 14A 2026-04-08'),
    'PNC': ('MSFT', 'DEF 14A 2026-03-11'),
    'ROK': ('GIS', 'DEF 14A 2025-12-22'),
    'SNPS': ('GIS', 'DEF 14A 2026-02-19'),
    'ADSK': ('PFG', 'DEF 14A 2026-05-06'),
    'AMD': ('GIS', 'DEF 14A 2026-03-27'),
    'CAT': ('IP', 'DEF 14A 2026-04-30'),
    'CDNS': ('GIS', 'DEF 14A 2026-03-25'),
    'DHI': ('PSA', 'DEF 14A 2025-12-10'),
    'IP': ('GIS', 'DEF 14A 2026-03-27'),
    'NI': ('IP', 'DEF 14A 2026-03-30'),
    'PRU': ('TGT', 'DEF 14A 2026-03-26'),
}


def main():
    bak = SRC.replace('.json', '_backup_20261004_0330_pre_batch9.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}
    n_before = len(edges)

    # 1. assert + drop each adjudicated edge (exactly one per source)
    for src, (tgt, filing) in sorted(DROPS.items()):
        assert src in by_ticker, f'{src}: not a node'
        assert tgt in by_ticker, f'{tgt}: not a node'
        matches = [e for e in edges if e['source'] == src and e['target'] == tgt]
        assert len(matches) == 1, f'{src}->{tgt}: expected 1 edge, found {len(matches)}'
        edges = [e for e in edges if not (e['source'] == src and e['target'] == tgt)]
        print(f'dropped {src}->{tgt} ({filing})')

    assert n_before - len(edges) == len(DROPS), 'drop count mismatch'
    print(f'edges: {n_before} -> {len(edges)}')

    # 2. recompute degrees exactly; report newly-zero-degree nodes
    from collections import Counter
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
            assert x.get('isSource') is True, f"{x['ticker']}: edges but not isSource"
        if x.get('isSource') is False:
            assert od == 0, f"{x['ticker']}: isSource False but has edges"

    # 3. metadata from actuals
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
