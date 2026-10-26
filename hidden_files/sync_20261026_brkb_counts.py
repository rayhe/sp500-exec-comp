"""Sync downstream counters after the 2026-10-26 BRK-B DQ repair.

NOT run through hidden_files/phantom_record.py: that helper does a full
json.dumps(indent=1, ensure_ascii=True) rewrite, but this file's canonical
serialization is indent=1, ensure_ascii=False (proven by byte-identical
round-trip); running it would escape all 665 literal em dashes into
\\u2014 noise. This script instead edits values in place and rewrites
with the proven serialization, and updates the phantom counters with the
same arithmetic record_batch() would apply (delta = pre - post = -90,410,201,
i.e. genuine compensation restored filing-verbatim).

Pre/post BRK-B exec totals: 49,165,000 -> 139,575,201 (delta -90,410,201).
Phantom: cumulative 2,284,244,764 -> 2,193,834,563; restored 550,284,451 ->
640,694,652; gross unchanged; batches 66 -> 67.
"""
import json

PATH = "data/compensation.json"

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)
meta = data["metadata"]


def expect(obj, key, old):
    actual = obj.get(key)
    assert actual == old, f"{key}: expected pre-value {old!r}, found {actual!r}"


# Headline counts: +1 exec row (Buffett FY2025).
expect(meta, "total_neo_records", 7078)
expect(meta, "total_executives", 7078)
expect(meta, "total_neos", 7078)
expect(meta, "title_coverage", "7078/7078")
expect(meta, "verified_total", 7046)
meta["total_neo_records"] = 7079
meta["total_executives"] = 7079
meta["total_neos"] = 7079
meta["title_coverage"] = "7079/7079"
meta["verified_total"] = 7047
assert "7078 NEO records" in meta["description"]
meta["description"] = meta["description"].replace("7078 NEO records", "7079 NEO records")

# DQ buckets: new row is _total_source "verified".
for block_name in ("data_quality", "data_quality_detailed"):
    block = meta[block_name]
    expect(block, "verified", 5631)
    expect(block, "verified_total", 7046)
    block["verified"] = 5632
    block["verified_total"] = 7047

# Aggregates (guard section 17 semantics: CEO pays > 0 only).
agg = meta["aggregate_stats"]
expect(agg, "mean_ceo_pay", 329481099)
expect(agg, "median_worker_pay", 82224)
agg["mean_ceo_pay"] = 329481659
agg["median_worker_pay"] = 82701

# Phantom campaign counters (see module docstring).
pr = meta["phantom_removed"]
expect(pr, "cumulative", 2284244764)
expect(pr, "gross_removed", 2834529215)
expect(pr, "restored", 550284451)
expect(pr, "batches", 66)
pr["cumulative"] = 2193834563
pr["restored"] = 640694652
pr["batches"] = 67
pr["last_updated"] = "2026-10-26 10:00 PT"
assert pr["cumulative"] == pr["gross_removed"] - pr["restored"]

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("counters synced: rows 7079, verified_total 7047, phantom cumulative 2193834563")
