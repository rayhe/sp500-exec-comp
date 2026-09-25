#!/usr/bin/env python3
"""Peer-network half of roster-add batch 2026-09-25 02:00 PT (backlog #12).
- Remap PSTG -> P (Pure Storage renamed Everpure, Inc., ticker PSTG -> P
  effective 2026-04-17; SEC company_tickers.json confirms CIK 1474432 /
  ticker P / "Everpure, Inc."). Inbound edges (SNDK, BE) retargeted.
- Promote P to company node (isSource); add ILMN company node.
- Add 11 new peer-only nodes (SEC-ticker-verified 2026-09-25; EXAS/HOLX are
  delisted/take-private peers retained filing-verbatim per the PARA/QRVO /
  COMM/SMAR ex-constituent precedent; JNPR already exists as a node).
- Add 37 new primary peer edges (ILMN x23, P x14).
- Recompute in_degree/out_degree for all nodes.
"""
import json, os, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET_PATH = os.path.join(REPO, "data/peer-network.json")
BATCH = os.path.expanduser("~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/sct_fill_20260925_0200")

shutil.copy2(NET_PATH, os.path.join(REPO, "hidden_files",
              "peer-network_backup_20260925_0200_pre_roster12.json"))
print("backup written")

net = json.load(open(NET_PATH))
nodes = net["nodes"]
edges = net["edges"]
by_ticker = {n["ticker"]: n for n in nodes}

# --- 1. PSTG -> P remap (same company, renamed) ---
n = by_ticker.pop("PSTG")
n["ticker"] = "P"
n["name"] = "Everpure, Inc."
by_ticker["P"] = n
remapped = 0
for e in edges:
    if e["source"] == "PSTG":
        e["source"] = "P"; remapped += 1
    if e["target"] == "PSTG":
        e["target"] = "P"; remapped += 1
print(f"remap PSTG -> P: {remapped} edge endpoints retargeted")

# --- 2. company nodes ---
COMPANY_NODES = {
    "P":    ("Everpure, Inc.", "Information Technology"),
    "ILMN": ("Illumina, Inc.", "Health Care"),
}
for t, (name, sector) in COMPANY_NODES.items():
    nn = by_ticker.get(t)
    if nn is None:
        nn = {"ticker": t, "name": name, "sector": sector,
              "in_degree": 0, "out_degree": 0, "market_cap_tier": "large",
              "isSource": True}
        nodes.append(nn)
        by_ticker[t] = nn
        print(f"new company node {t}")
        continue
    nn["name"] = name
    nn["sector"] = sector
    nn["isSource"] = True
    print(f"promoted {t} to company node")

# --- 3. new peer-only nodes (ticker -> (SEC company_name, sector)) ---
# SEC-verified 2026-09-25 via company_tickers.json except EXAS/HOLX
# (delisted: EXAS acquired by Abbott 2026-03-23; HOLX taken private by
# Blackstone/TPG 2026-04-07) kept filing-verbatim per precedent.
PEERS = {
    "EXAS": ("Exact Sciences Corporation", "Health Care"),   # delisted peer
    "AVTR": ("Avantor, Inc.", "Health Care"),
    "BMRN": ("BioMarin Pharmaceutical Inc.", "Health Care"),
    "BIO":  ("Bio-Rad Laboratories, Inc.", "Health Care"),
    "BRKR": ("Bruker Corporation", "Health Care"),
    "JAZZ": ("Jazz Pharmaceuticals plc", "Health Care"),
    "GWRE": ("Guidewire Software, Inc.", "Information Technology"),
    "NTNX": ("Nutanix, Inc.", "Information Technology"),
    "ESTC": ("Elastic N.V.", "Information Technology"),
    "BOX":  ("Box, Inc.", "Information Technology"),
    "DBX":  ("Dropbox, Inc.", "Information Technology"),
}
for t, (name, sector) in PEERS.items():
    assert t not in by_ticker, f"{t} already a node"
    nn = {"ticker": t, "name": t, "company_name": name, "sector": sector,
          "in_degree": 0, "out_degree": 0, "market_cap_tier": "large"}
    nodes.append(nn)
    by_ticker[t] = nn
print(f"added {len(PEERS)} peer-only nodes")

# --- 4. new primary edges ---
def add_edges(src, xtfile, year, filing):
    d = json.load(open(os.path.join(BATCH, xtfile)))
    new = 0
    for tgt in d["peer_group"]:
        assert tgt in by_ticker, f"peer {tgt} missing node"
        if any(e["source"] == src and e["target"] == tgt for e in edges):
            continue
        edges.append({"source": src, "target": tgt, "year": year,
                      "group_type": "primary", "filing": filing})
        new += 1
    print(f"{src}: {new} new edges")
    return new

n_ilmn = add_edges("ILMN", "ILMN_extraction.json", 2026, "DEF 14A 2026-04-09")
n_p = add_edges("P", "P_extraction.json", 2026, "DEF 14A 2026-05-01")

# --- 5. recompute degrees ---
indeg = {n["ticker"]: 0 for n in nodes}
outdeg = {n["ticker"]: 0 for n in nodes}
for e in edges:
    outdeg[e["source"]] = outdeg.get(e["source"], 0) + 1
    indeg[e["target"]] = indeg.get(e["target"], 0) + 1
for nn in nodes:
    nn["in_degree"] = indeg[nn["ticker"]]
    nn["out_degree"] = outdeg[nn["ticker"]]

md = net.get("metadata", {})
md["node_count"] = len(nodes)
md["edge_count"] = len(edges)
net["metadata"] = md
json.dump(net, open(NET_PATH, "w"), indent=1)
print(f"network: {len(nodes)} nodes, {len(edges)} edges (+{n_ilmn + n_p} new)")
