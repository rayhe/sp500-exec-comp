#!/usr/bin/env python3
"""317th review (2026-11-02 13:00 PT): metadata + static-copy sync.

Row count 7308 -> 7316 (FDX missing-NEO restoration: Allen x2, Carter x3,
Lenz x3, all filing-verbatim from the 2024 DEF 14A SCT); verified_total
7264 -> 7272. Phantom counters already updated by phantom_record.record_batch
in the repair script (gross_removed $3,064,095,898 unchanged / restored
$3,997,306,548 / net $-933,210,650 / batches 89).
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")


def rep_once(text, old, new, where):
    assert text.count(old) == 1, f"{where}: found {text.count(old)}x {old!r:.70}"
    return text.replace(old, new, 1)


def main():
    # ---- metadata buckets ----
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    m = d["metadata"]
    if m["total_neo_records"] == 7308:
        m["total_neo_records"] = 7316
        m["total_executives"] = 7316
        m["total_neos"] = 7316
        m["title_coverage"] = "7316/7316"
        m["verified_total"] = 7272
        m["description"] = m["description"].replace("7308 NEO records",
                                                    "7316 NEO records", 1)
        for block in ("data_quality", "data_quality_detailed"):
            assert m[block]["verified"] == 5849, block
            assert m[block]["verified_total"] == 7264, block
            m[block]["verified"] = 5857
            m[block]["verified_total"] = 7272
    assert m["total_neo_records"] == 7316
    assert m["verified_total"] == 7272
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("metadata synced")

    # ---- README.md ----
    rp = os.path.join(REPO, "README.md")
    t = open(rp, encoding="utf-8").read()
    if "7,264 of 7,308 records," not in t:
        print("README already synced (idempotent)")
    else:
        t = rep_once(t,
                     "99.4% verified component-total consistency (7,264 of 7,308 records,",
                     "99.4% verified component-total consistency (7,272 of 7,316 records,",
                     "README headline")
        t = rep_once(t,
                     "Component-total consistency verified: 99.4% verified (7,264 of 7,308 total NEO records),",
                     "Component-total consistency verified: 99.4% verified (7,272 of 7,316 total NEO records),",
                     "README taxonomy")
        t = rep_once(t,
                     "Buckets (as of 2026-11-02: 7,308 rows):",
                     "Buckets (as of 2026-11-02: 7,316 rows):",
                     "README buckets")
        # append the 317th audit-trail entry to the item-4 paragraph
        anchor = ("Guard green.")
        assert t.count(anchor) >= 1, "README audit anchor missing"
        entry = (" 2026-11-02 13:00 PT missing-NEO restoration batch (317th review): "
                 "8 rows filing-verbatim from the FDX 2024 DEF 14A SCT "
                 "(acc. 0001308179-24-000696, filed 2024-08-12; SCT grid extracted "
                 "by the 316th review) -- Mark R. Allen 2024 ($5,167,068) / 2023 "
                 "($5,386,177); Robert B. Carter 2024 ($5,116,560) / 2023 "
                 "($5,677,999) / 2022 ($3,452,232); Michael C. Lenz 2024 "
                 "($6,085,807) / 2023 ($6,042,253) / 2022 ($3,936,673); blank "
                 "filing pension cells -> 0 (Dietrich 2024 precedent); all 8 "
                 "totals foot exactly; rows appended at END of the FDX list. FDX "
                 "anchor year FY2026 intact, company aggregates untouched. "
                 "Phantom counter: gross_removed unchanged at $3,064,095,898, "
                 "restored $3,956,441,779->$3,997,306,548, batches 88->89, net "
                 "$-892,345,881->$-933,210,650. verified_total 7,264->7,272 "
                 "(99.4%), component_mismatch 44, rows 7,308->7,316. Guard green.")
        t = t.replace(anchor, anchor + entry, 1)
        open(rp, "w", encoding="utf-8").write(t)
        print("README synced")

    # ---- index.html ----
    ip = os.path.join(REPO, "index.html")
    it = open(ip, encoding="utf-8").read()
    old_ld = "7,308 named executive officer records"
    assert it.count(old_ld) == 1, f"json-ld desc count {it.count(old_ld)}"
    it = it.replace(old_ld, "7,316 named executive officer records")
    it = rep_once(it, "benchmarked from 7,308 Named Executive Officer records",
                  "benchmarked from 7,316 Named Executive Officer records",
                  "index.html role-comp-desc")
    open(ip, "w", encoding="utf-8").write(it)
    print("index.html synced")

    # ---- js/app.js ----
    jp = os.path.join(REPO, "js", "app.js")
    jt = open(jp, encoding="utf-8").read()
    if "7,264 of 7,308 NEO rows verified (99.4%)" not in jt:
        print("js/app.js already synced (idempotent)")
        return
    jt = rep_once(jt, "7,264 of 7,308 NEO rows verified (99.4%)",
                  "7,272 of 7,316 NEO rows verified (99.4%)", "js coverage")
    old_phantom = ("$3,064,095,898 of parser-invented compensation removed across 88 "
                   "re-verification batches since 2026-09-12, partly offset by "
                   "$3,956,441,779 of genuine missing NEO rows restored "
                   "filing-verbatim. Net: $-892,345,881.")
    new_phantom = ("$3,064,095,898 of parser-invented compensation removed across 89 "
                   "re-verification batches since 2026-09-12, partly offset by "
                   "$3,997,306,548 of genuine missing NEO rows restored "
                   "filing-verbatim. Net: $-933,210,650.")
    jt = rep_once(jt, old_phantom, new_phantom, "js phantom-block")
    open(jp, "w", encoding="utf-8").write(jt)
    print("js/app.js synced")


if __name__ == "__main__":
    main()
