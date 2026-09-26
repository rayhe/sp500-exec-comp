#!/usr/bin/env python3
"""Apply the 2026-09-25 18:00 PT DQ batch repair JSON to data/compensation.json.

Programmatic only: reads hidden_files/dq_batch_20260925_1800_repair.json,
matches on ticker + name + year, and applies corrected_fields for the three
actionable verdicts (repair_components, filing_does_not_foot_keep_total,
missing_component_found). Canonical serialization: json.dump(indent=1) + trailing
newline. Re-reads and asserts every touched row's corrected fields equal the
repair JSON. Does NOT commit.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260925_1800_pre_dqbatch.json")
REPAIR_PATH = os.path.join(HERE, "dq_batch_20260925_1800_repair.json")

APPLY_VERDICTS = {"repair_components", "filing_does_not_foot_keep_total",
                  "missing_component_found"}

assert os.path.exists(BACKUP), f"backup missing: {BACKUP}"

with open(REPAIR_PATH, encoding="utf-8") as f:
    batch = json.load(f)
with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
companies = {c["ticker"]: c for c in data["companies"]}


def get(ticker, name, year):
    hits = [e for e in companies[ticker]["executives"]
            if e["name"] == name and e["year"] == year]
    assert len(hits) == 1, f"{ticker} {name} {year}: {len(hits)} hits"
    return hits[0]


touched = []
for r in batch["rows"]:
    if r["verdict"] not in APPLY_VERDICTS:
        continue
    e = get(r["ticker"], r["name"], r["year"])
    for k, v in r["corrected_fields"].items():
        e[k] = v
    touched.append((r, e))

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
    f.write("\n")

# Source-equality check: re-read and assert every touched row's corrected
# fields are byte-equal to the repair JSON.
with open(JSON_PATH, encoding="utf-8") as f:
    data2 = json.load(f)
companies2 = {c["ticker"]: c for c in data2["companies"]}
n_checked = 0
for r, _ in touched:
    e2 = [e for e in companies2[r["ticker"]]["executives"]
          if e["name"] == r["name"] and e["year"] == r["year"]]
    assert len(e2) == 1, f"post-apply match failed: {r['ticker']} {r['name']} {r['year']}"
    for k, v in r["corrected_fields"].items():
        assert k in e2[0], f"field {k} missing post-apply: {r['ticker']} {r['name']} {r['year']}"
        assert e2[0][k] == v, (
            f"MISMATCH {r['ticker']} {r['name']} {r['year']} {k}: "
            f"file={e2[0][k]!r} repair={v!r}")
        n_checked += 1

print(f"applied {len(touched)} rows; equality assertions passed on "
      f"{n_checked} corrected fields; no commit performed")
