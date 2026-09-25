#!/usr/bin/env python3
"""Peer-network half of roster-add batch 2026-09-24 23:30 PT (backlog #11).
- Remap BK->BNY and MMC->MRSH (ticker changes verified: BNY via SEC
  company_tickers.json, MRSH effective 2026-01-14 via company announcement).
- Promote COHR to company node; add VRT/LITE/BE/FOXA/FDXF company nodes.
- Add 52 new peer-only nodes (SEC-ticker-verified 2026-09-24; COMM/SMAR are
  delisted/take-private peers kept per the PARA/QRVO ex-constituent precedent).
- Add 135 new primary peer edges (8 companies x peer groups).
- Recompute in_degree/out_degree for all nodes.
"""
import json, os, shutil, gzip

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET_PATH = os.path.join(REPO, "data/peer-network.json")
BATCH = os.path.expanduser("~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/sct_fill_20260924_2330")

net = json.load(open(NET_PATH))
nodes = net["nodes"]
edges = net["edges"]
by_ticker = {n["ticker"]: n for n in nodes}

# --- 1. ticker remaps ---
REMAPS = {
    "BK":  ("BNY",  "Bank of New York Mellon Corp"),
    "MMC": ("MRSH", "Marsh McLennan Companies, Inc."),
}
for old, (new, name) in REMAPS.items():
    n = by_ticker.pop(old)
    n["ticker"] = new
    n["name"] = name
    by_ticker[new] = n
    print(f"remap {old} -> {new}: in_degree {n['in_degree']}")
for e in edges:
    if e["source"] in REMAPS:
        e["source"] = REMAPS[e["source"]][0]
    if e["target"] in REMAPS:
        e["target"] = REMAPS[e["target"]][0]

# --- 2. company nodes ---
COMPANY_NODES = {
    "BNY":  ("Bank of New York Mellon Corp", "Financials"),
    "VRT":  ("Vertiv Holdings Co", "Industrials"),
    "LITE": ("Lumentum Holdings Inc.", "Information Technology"),
    "MRSH": ("Marsh McLennan Companies, Inc.", "Financials"),
    "BE":   ("Bloom Energy Corporation", "Industrials"),
    "FOXA": ("Fox Corporation", "Communication Services"),
    "COHR": ("Coherent Corp.", "Information Technology"),
    "FDXF": ("FedEx Freight Holding Company, Inc.", "Industrials"),
}
for t, (name, sector) in COMPANY_NODES.items():
    n = by_ticker.get(t)
    if n is None:
        n = {"ticker": t, "name": name, "sector": sector,
             "in_degree": 0, "out_degree": 0, "market_cap_tier": "large",
             "isSource": True}
        nodes.append(n)
        by_ticker[t] = n
        print(f"new company node {t}")
        continue
    n["name"] = name
    n["sector"] = sector
    n["isSource"] = True
    if t == "COHR":
        n.pop("company_name", None)  # now a full company node

# --- 3. new peer-only nodes (ticker -> (SEC company_name, sector)) ---
PEERS = {
    "AAON": ("AAON, Inc.", "Industrials"),
    "ADTN": ("ADTRAN Holdings, Inc.", "Information Technology"),
    "AEIS": ("ADVANCED ENERGY INDUSTRIES INC", "Information Technology"),
    "AI":   ("C3.ai, Inc.", "Information Technology"),
    "AMCX": ("AMC Global Media Inc.", "Communication Services"),
    "ARCB": ("ARCBEST CORP /TX/", "Industrials"),
    "CALX": ("CALIX, INC", "Information Technology"),
    "CIEN": ("Ciena Corporation", "Information Technology"),
    "CLS":  ("Celestica Inc.", "Information Technology"),
    "COMM": ("COMMSCOPE HOLDING COMPANY, INC.", "Information Technology"),  # delisted peer
    "CRUS": ("CIRRUS LOGIC, INC.", "Information Technology"),
    "CSL":  ("Carlisle Companies Incorporated", "Industrials"),
    "DIOD": ("DIODES INC /DEL/", "Information Technology"),
    "ENTG": ("Entegris, Inc.", "Information Technology"),
    "EXTR": ("EXTREME NETWORKS INC", "Information Technology"),
    "GXO":  ("GXO Logistics, Inc.", "Industrials"),
    "IPGP": ("IPG Photonics Corporation", "Information Technology"),
    "KNX":  ("Knight-Swift Transportation Holdings Inc.", "Industrials"),
    "LBTYA": ("Liberty Global Ltd.", "Communication Services"),
    "LFUS": ("Littelfuse, Inc.", "Information Technology"),
    "LSTR": ("LANDSTAR SYSTEM INC", "Industrials"),
    "MKSI": ("MKS Instruments, Inc.", "Information Technology"),
    "MXL":  ("MAXLINEAR, INC", "Information Technology"),
    "NVT":  ("nVent Electric plc", "Industrials"),
    "NXST": ("NEXSTAR MEDIA GROUP, INC.", "Communication Services"),
    "NXT":  ("Nextracker Inc.", "Industrials"),
    "OLED": ("UNIVERSAL DISPLAY CORP", "Information Technology"),
    "ONTO": ("ONTO INNOVATION INC.", "Information Technology"),
    "ORA":  ("ORMAT TECHNOLOGIES, INC.", "Utilities"),
    "OSIS": ("OSI Systems, Inc.", "Information Technology"),
    "PLUG": ("PLUG POWER INC", "Industrials"),
    "R":    ("RYDER SYSTEM INC", "Industrials"),
    "REZI": ("RESIDEO TECHNOLOGIES, INC.", "Industrials"),
    "RIVN": ("Rivian Automotive, Inc.", "Consumer Discretionary"),
    "RMBS": ("Rambus Inc.", "Information Technology"),
    "RRX":  ("Regal Rexnord Corporation", "Industrials"),
    "RUN":  ("Sunrun Inc.", "Industrials"),
    "RXO":  ("RXO, Inc.", "Industrials"),
    "SAIA": ("SAIA INC", "Industrials"),
    "SBGI": ("Sinclair, Inc.", "Communication Services"),
    "SIRI": ("Sirius XM Holdings Inc.", "Communication Services"),
    "SMAR": ("SMARTSHEET INC", "Information Technology"),  # take-private Jan 2025
    "SMTC": ("Semtech Corporation", "Information Technology"),
    "SNDR": ("Schneider National, Inc.", "Industrials"),
    "SYNA": ("SYNAPTICS Inc", "Information Technology"),
    "TFII": ("TFI International Inc.", "Industrials"),
    "TLN":  ("Talen Energy Corp", "Utilities"),
    "VIAV": ("VIAVI SOLUTIONS INC.", "Information Technology"),
    "VSAT": ("VIASAT INC", "Information Technology"),
    "VYX":  ("NCR Voyix Corp", "Information Technology"),
    "WOLF": ("WOLFSPEED, INC.", "Information Technology"),
    "XPO":  ("XPO, Inc.", "Industrials"),
}
added = 0
for t, (cname, sector) in PEERS.items():
    assert t not in by_ticker, f"{t} unexpectedly already in network"
    n = {"ticker": t, "name": t, "company_name": cname, "sector": sector,
         "in_degree": 0, "out_degree": 0, "market_cap_tier": "large"}
    nodes.append(n)
    by_ticker[t] = n
    added += 1
print(f"added {added} peer-only nodes")

# --- 4. new edges ---
FILING_DATES = {"BK": "2026-03-05", "VRT": "2026-04-24", "LITE": "2025-10-07",
                "MMC": "2026-03-31", "BE": "2026-04-08", "FOXA": "2025-09-25",
                "COHR": "2025-10-02", "FDXF": "2026-08-05"}
new_edges = 0
for xt, m in (("BK", "BNY"), ("VRT", "VRT"), ("LITE", "LITE"), ("MMC", "MRSH"),
              ("BE", "BE"), ("FOXA", "FOXA"), ("COHR", "COHR"), ("FDXF", "FDXF")):
    d = json.load(open(os.path.join(BATCH, f"{xt}_extraction.json")))
    proxy_year = int(FILING_DATES[xt][:4])
    filing = ("10-K " if xt == "FDXF" else "DEF 14A ") + FILING_DATES[xt]
    for p in d["peer_group"]:
        assert p in by_ticker, f"peer {p} missing from network"
        edges.append({"source": m, "target": p, "year": proxy_year,
                      "group_type": "primary", "filing": filing})
        new_edges += 1
print(f"added {new_edges} edges")

# --- 5. recompute degrees ---
for n in nodes:
    n["in_degree"] = 0
    n["out_degree"] = 0
for e in edges:
    by_ticker[e["source"]]["out_degree"] += 1
    by_ticker[e["target"]]["in_degree"] += 1

net["nodes"] = nodes
net["edges"] = edges
if "metadata" in net:
    net["metadata"]["node_count"] = len(nodes)
    net["metadata"]["edge_count"] = len(edges)
json.dump(net, open(NET_PATH, "w"), indent=1)
print(f"network: {len(nodes)} nodes, {len(edges)} edges")
