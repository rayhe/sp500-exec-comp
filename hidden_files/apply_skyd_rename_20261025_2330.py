#!/usr/bin/env python3
"""PSKY -> SKYD roster rename (2026-10-25 23:30 PT, 227th review).

Skydance Corporation: name/symbol change effective 2026-10-06 (WBD
acquisition closed; Class B listing Nasdaq -> NYSE, ticker PSKY -> SKYD;
OCC Info Memo #59906; S&P 500 membership continues under SKYD).
Re-keys the LIVE tracker state only:
  - data/compensation.json: ticker key, company_name, _index_note rewrite
  - data/peer-network.json: node ticker/name, 4 edge targets
Deliberately NOT renamed (historical record, WBD precedent):
  - README audit-trail prose, pay_vs_performance.json wave-history prose,
    guard/batch-script comments, backups, filing-verbatim _notes.
Round-trip proof: compensation.json json.dumps(indent=1,
ensure_ascii=False)+trailing newline is byte-identical pre-edit;
peer-network.json json.dumps(indent=1) is byte-identical pre-edit.
"""
import json

OLD_NOTE = ("Renamed Skydance Corporation on 2026-10-06 (Warner Bros. Discovery "
            "acquisition closed; Class B listing moved Nasdaq -> NYSE, ticker PSKY -> SKYD). "
            "Tracker key stays PSKY until the roster-rename batch; DEF 14A watch continues "
            "under CIK 0002041610. Re-checked 2026-10-25: CIK 0002041610 submissions show no "
            "DEF 14A ever filed (EDGAR now lists tickers SKYD/SKYD-WT). FY2025 SCT remains "
            "the 2026-04-24 10-K/A Part III.")
NEW_NOTE = ("Renamed Skydance Corporation on 2026-10-06 (Warner Bros. Discovery "
            "acquisition closed; Class B listing moved Nasdaq -> NYSE, ticker PSKY -> SKYD). "
            "Tracker key updated to SKYD 2026-10-25 (formerly PSKY). DEF 14A watch continues "
            "under CIK 0002041610. Re-checked 2026-10-25: CIK 0002041610 submissions show no "
            "DEF 14A ever filed (EDGAR now lists tickers SKYD/SKYD-WT). FY2025 SCT remains "
            "the 2026-04-24 10-K/A Part III.")


def replace_once(text, old, new, label):
    n = text.count(old)
    assert n == 1, f"{label}: expected 1 occurrence, found {n}"
    return text.replace(old, new)


# --- compensation.json (string-level surgery preserves byte layout) ---
path = "data/compensation.json"
raw = open(path, encoding="utf-8").read()
data = json.loads(raw)
assert json.dumps(data, indent=1, ensure_ascii=False) + "\n" == raw, "round-trip proof failed"
raw = replace_once(raw, '"ticker": "PSKY",', '"ticker": "SKYD",', "comp ticker")
raw = replace_once(raw, '"company_name": "Paramount Skydance Corp",',
                   '"company_name": "Skydance Corporation",', "comp name")
raw = replace_once(raw, OLD_NOTE, NEW_NOTE, "comp index note")
open(path, "w", encoding="utf-8").write(raw)

# --- peer-network.json ---
path = "data/peer-network.json"
raw = open(path, encoding="utf-8").read()
data = json.loads(raw)
assert json.dumps(data, indent=1) == raw, "round-trip proof failed"
raw = replace_once(raw, '"ticker": "PSKY",', '"ticker": "SKYD",', "peer node ticker")
raw = replace_once(raw, '"name": "Paramount Skydance Corp",',
                   '"name": "Skydance Corporation",', "peer node name")
n = raw.count('"target": "PSKY",')
assert n == 4, f"peer edge targets: expected 4, found {n}"
raw = raw.replace('"target": "PSKY",', '"target": "SKYD",')
open(path, "w", encoding="utf-8").write(raw)

# --- post-edit verification ---
comp = json.load(open("data/compensation.json", encoding="utf-8"))
peer = json.load(open("data/peer-network.json", encoding="utf-8"))
companies = comp["companies"] if isinstance(comp, dict) and "companies" in comp else comp
if isinstance(companies, dict):
    tickers = list(companies.keys())
else:
    tickers = [c["ticker"] for c in companies]
assert "SKYD" in tickers and "PSKY" not in tickers, "comp tickers wrong"
rows = sum(len(c.get("executives", [])) for c in (companies.values() if isinstance(companies, dict) else companies))
print(f"companies={len(tickers)} rows={rows}")
nodes = peer["nodes"] if isinstance(peer, dict) else peer
edges = peer["edges"] if isinstance(peer, dict) else []
print(f"peer nodes={len(nodes)} edges={len(edges)}")
assert any(n.get("ticker") == "SKYD" for n in nodes), "SKYD node missing"
assert not any(n.get("ticker") == "PSKY" for n in nodes), "PSKY node remains"
assert not any(e.get("target") == "PSKY" or e.get("source") == "PSKY" for e in edges), "PSKY edge remains"
print("RENAME OK")
