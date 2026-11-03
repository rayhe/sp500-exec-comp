#!/usr/bin/env python3
"""320th review (2026-11-02 18:30 PT): metadata + static-copy sync.

Row count 7317 -> 7318 (ARE Diamond 2024 missing-NEO restoration,
filing-verbatim from the 2026 DEF 14A SCT); verified_total 7273 -> 7274.
Cole 2025 title repair is total-neutral and moves no buckets. Phantom
counters already updated by phantom_record.record_batch in the repair
script (gross_removed $3,064,095,898 unchanged / restored
$4,010,158,645->$4,013,590,714 / net $-946,062,747->$-949,494,816 /
batches 91->92).
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")
GOAL_DIR = os.path.expanduser(
    "~/workspace/goals/s-p-500-executive-compensation-tracker")


def rep_once(text, old, new, where):
    assert text.count(old) == 1, f"{where}: found {text.count(old)}x {old!r:.70}"
    return text.replace(old, new, 1)


def main():
    # ---- metadata buckets ----
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    m = d["metadata"]
    if m["total_neo_records"] == 7317:
        m["total_neo_records"] = 7318
        m["total_executives"] = 7318
        m["total_neos"] = 7318
        m["title_coverage"] = "7318/7318"
        m["verified_total"] = 7274
        m["description"] = m["description"].replace("7317 NEO records",
                                                    "7318 NEO records", 1)
        for block in ("data_quality", "data_quality_detailed"):
            assert m[block]["verified"] == 5858, block
            assert m[block]["verified_total"] == 7273, block
            m[block]["verified"] = 5859
            m[block]["verified_total"] = 7274
    assert m["total_neo_records"] == 7318
    assert m["verified_total"] == 7274
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("metadata synced")

    # ---- README.md ----
    rp = os.path.join(REPO, "README.md")
    t = open(rp, encoding="utf-8").read()
    if "7,274 of 7,318 records," not in t:
        t = rep_once(t,
                     "99.4% verified component-total consistency (7,273 of 7,317 records,",
                     "99.4% verified component-total consistency (7,274 of 7,318 records,",
                     "README headline")
        t = rep_once(t,
                     "Component-total consistency verified: 99.4% verified (7,273 of 7,317 total NEO records),",
                     "Component-total consistency verified: 99.4% verified (7,274 of 7,318 total NEO records),",
                     "README taxonomy")
        t = rep_once(t,
                     "Buckets (as of 2026-11-02: 7,317 rows):",
                     "Buckets (as of 2026-11-02: 7,318 rows):",
                     "README buckets")
        anchor = ("verified_total 7,272->7,273 (99.4%), component_mismatch 44, "
                  "rows 7,316->7,317. Guard green.")
        assert t.count(anchor) == 1, "README 319th audit anchor missing"
        entry = (" 2026-11-02 18:30 PT missing-NEO restoration + title-repair "
                 "batch (320th review): Lawrence J. Diamond FY2024 "
                 "($3,432,069) restored filing-verbatim from the 2026 DEF "
                 "14A SCT (acc. 0001035443-26-000031, filed 2026-04-01; fn "
                 "(8) not an NEO in 2023, so 2024 is a genuine NEO year the "
                 "dataset had missed); the 319th review's pension>0 / "
                 "NEIP==0 screen cluster for ARE adjudicated FALSE POSITIVE "
                 "(all 8 stored rows byte-equal to the filing: ARE pays "
                 "Bonus, not NEIP, and the small pension values are genuine "
                 "NQDC changes); John Hart Cole 2025 title repaired "
                 "filing-verbatim (was Kass's Greater-Boston title pattern, "
                 "actually Co-President & Co-Regional Market Director - "
                 "Seattle), total-neutral. Phantom counter: gross_removed "
                 "unchanged at $3,064,095,898, restored "
                 "$4,010,158,645->$4,013,590,714, batches 91->92, net "
                 "$-946,062,747->$-949,494,816. verified_total 7,273->7,274 "
                 "(99.4%), component_mismatch 44, rows 7,317->7,318. "
                 "Guard green.")
        t = t.replace(anchor, anchor + entry, 1)
        open(rp, "w", encoding="utf-8").write(t)
        print("README synced")
    else:
        print("README already synced (idempotent)")

    # ---- index.html ----
    ip = os.path.join(REPO, "index.html")
    it = open(ip, encoding="utf-8").read()
    if "7,318 named executive officer records" not in it:
        old_ld = "7,317 named executive officer records"
        assert it.count(old_ld) == 1, f"json-ld desc count {it.count(old_ld)}"
        it = it.replace(old_ld, "7,318 named executive officer records")
        it = rep_once(it, "benchmarked from 7,317 Named Executive Officer records",
                      "benchmarked from 7,318 Named Executive Officer records",
                      "index.html role-comp-desc")
        open(ip, "w", encoding="utf-8").write(it)
        print("index.html synced")
    else:
        print("index.html already synced (idempotent)")

    # ---- js/app.js ----
    jp = os.path.join(REPO, "js", "app.js")
    jt = open(jp, encoding="utf-8").read()
    if "7,274 of 7,318 NEO rows verified (99.4%)" not in jt:
        jt = rep_once(jt, "7,273 of 7,317 NEO rows verified (99.4%)",
                      "7,274 of 7,318 NEO rows verified (99.4%)", "js coverage")
        old_phantom = ("of parser-invented compensation removed across 91 "
                       "re-verification batches since 2026-09-12, partly offset by "
                       "$4,010,158,645 of genuine missing NEO rows restored "
                       "filing-verbatim. Net: $-946,062,747.")
        new_phantom = ("of parser-invented compensation removed across 92 "
                       "re-verification batches since 2026-09-12, partly offset by "
                       "$4,013,590,714 of genuine missing NEO rows restored "
                       "filing-verbatim. Net: $-949,494,816.")
        jt = rep_once(jt, old_phantom, new_phantom, "js phantom-block")
        open(jp, "w", encoding="utf-8").write(jt)
        print("js/app.js synced")
    else:
        print("js/app.js already synced (idempotent)")

    # ---- GOAL.md ----
    gp = os.path.join(GOAL_DIR, "GOAL.md")
    gt = open(gp, encoding="utf-8").read()
    if "7,318 NEO rows" not in gt:
        gt = rep_once(gt, "7,317 NEO rows", "7,318 NEO rows", "GOAL.md rows")
        open(gp, "w", encoding="utf-8").write(gt)
        print("GOAL.md synced")
    else:
        print("GOAL.md already synced (idempotent)")

    # ---- S3 baseline in check_mismatch_reverify_20261028.py ----
    sp = os.path.join(REPO, "scripts", "check_mismatch_reverify_20261028.py")
    st = open(sp, encoding="utf-8").read()
    if "total == 7318" not in st:
        st = rep_once(st, "total == 7317 and mismatch == 44",
                      "total == 7318 and mismatch == 44", "S3 total")
        st = rep_once(st,
                      '["data_quality"]["verified_total"] == 7273',
                      '["data_quality"]["verified_total"] == 7274', "S3 verified")
        st = rep_once(st, "S3 counts unchanged (518 / 7317 / mismatch 44 / verified 7273)",
                      "S3 counts unchanged (518 / 7318 / mismatch 44 / verified 7274)",
                      "S3 label")
        st = st.replace(
            "# S3 baseline moved 2026-11-02 (317th review): FDX missing-NEO\n",
            "# S3 baseline moved 2026-11-02 (320th review): ARE Diamond 2024\n"
            "# missing-NEO restoration (filing-verbatim from the 2026 DEF 14A\n"
            "# SCT) -> 7317->7318 rows, verified_total 7273->7274, mismatch\n"
            "# unchanged at 44.\n"
            "# S3 baseline moved 2026-11-02 (317th review): FDX missing-NEO\n",
            1)
        open(sp, "w", encoding="utf-8").write(st)
        print("S3 baseline moved")
    else:
        print("S3 baseline already moved (idempotent)")


if __name__ == "__main__":
    main()
