#!/usr/bin/env python3
"""319th review (2026-11-02 17:00 PT): metadata + static-copy sync.

Row count 7316 -> 7317 (FIS Kehoe 2023 missing-NEO restoration,
filing-verbatim from the 2026 DEF 14A SCT; NEO determination confirmed in
the 2024 DEF 14A SCT); verified_total 7272 -> 7273. Title repairs (11 FIS
rows) are total-neutral and move no buckets. Phantom counters already
updated by phantom_record.record_batch in the repair script (gross_removed
$3,064,095,898 unchanged / restored $3,997,306,548->$4,010,158,645 / net
$-933,210,650->$-946,062,747 / batches 90->91).
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
    if m["total_neo_records"] == 7316:
        m["total_neo_records"] = 7317
        m["total_executives"] = 7317
        m["total_neos"] = 7317
        m["title_coverage"] = "7317/7317"
        m["verified_total"] = 7273
        m["description"] = m["description"].replace("7316 NEO records",
                                                    "7317 NEO records", 1)
        for block in ("data_quality", "data_quality_detailed"):
            assert m[block]["verified"] == 5857, block
            assert m[block]["verified_total"] == 7272, block
            m[block]["verified"] = 5858
            m[block]["verified_total"] = 7273
    assert m["total_neo_records"] == 7317
    assert m["verified_total"] == 7273
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("metadata synced")

    # ---- README.md ----
    rp = os.path.join(REPO, "README.md")
    t = open(rp, encoding="utf-8").read()
    if "7,273 of 7,317 records," not in t:
        t = rep_once(t,
                     "99.4% verified component-total consistency (7,272 of 7,316 records,",
                     "99.4% verified component-total consistency (7,273 of 7,317 records,",
                     "README headline")
        t = rep_once(t,
                     "Component-total consistency verified: 99.4% verified (7,272 of 7,316 total NEO records),",
                     "Component-total consistency verified: 99.4% verified (7,273 of 7,317 total NEO records),",
                     "README taxonomy")
        t = rep_once(t,
                     "Buckets (as of 2026-11-02: 7,316 rows):",
                     "Buckets (as of 2026-11-02: 7,317 rows):",
                     "README buckets")
        # append the 319th audit-trail entry to the item-4 paragraph
        anchor = ("Guard green.")
        assert t.count(anchor) >= 1, "README audit anchor missing"
        entry = (" 2026-11-02 17:00 PT missing-NEO restoration + title-repair "
                 "batch (319th review): James Kehoe FY2023 ($12,852,097) "
                 "restored filing-verbatim from the 2026 DEF 14A SCT "
                 "(acc. 0001136893-26-000026, filed 2026-04-28); FY2023 NEO "
                 "determination confirmed in the 2024 DEF 14A SCT "
                 "(acc. 0001193125-24-118098, filed 2024-04-26 - Kehoe named "
                 "EVP/CFO NEO; 2026 row supersedes the 2024 alt-text figures: "
                 "salary 355,459->355,469, NEIP 761,530->761,056, total "
                 "foots exactly at 12,852,097); 11 FIS title repairs "
                 "filing-verbatim from the 2026 SCT name cells (Kehoe "
                 "2025/2024 were mislabeled CEO, actually EVP/CFO; Bhathena "
                 "2025/2024 mislabeled CFO, actually Former Chief Product "
                 "Technology Officer; Toohey/Tsai under-titled), all "
                 "total-neutral. Phantom counter: gross_removed unchanged at "
                 "$3,064,095,898, restored $3,997,306,548->$4,010,158,645, "
                 "batches 90->91, net $-933,210,650->$-946,062,747. "
                 "verified_total 7,272->7,273 (99.4%), component_mismatch 44, "
                 "rows 7,316->7,317. Guard green.")
        t = t.replace(anchor, anchor + entry, 1)
        open(rp, "w", encoding="utf-8").write(t)
        print("README synced")
    else:
        print("README already synced (idempotent)")

    # ---- index.html ----
    ip = os.path.join(REPO, "index.html")
    it = open(ip, encoding="utf-8").read()
    if "7,317 named executive officer records" not in it:
        old_ld = "7,316 named executive officer records"
        assert it.count(old_ld) == 1, f"json-ld desc count {it.count(old_ld)}"
        it = it.replace(old_ld, "7,317 named executive officer records")
        it = rep_once(it, "benchmarked from 7,316 Named Executive Officer records",
                      "benchmarked from 7,317 Named Executive Officer records",
                      "index.html role-comp-desc")
        open(ip, "w", encoding="utf-8").write(it)
        print("index.html synced")
    else:
        print("index.html already synced (idempotent)")

    # ---- js/app.js ----
    jp = os.path.join(REPO, "js", "app.js")
    jt = open(jp, encoding="utf-8").read()
    if "7,273 of 7,317 NEO rows verified (99.4%)" not in jt:
        jt = rep_once(jt, "7,272 of 7,316 NEO rows verified (99.4%)",
                      "7,273 of 7,317 NEO rows verified (99.4%)", "js coverage")
        old_phantom = ("of parser-invented compensation removed across 90 "
                       "re-verification batches since 2026-09-12, partly offset by "
                       "$3,997,306,548 of genuine missing NEO rows restored "
                       "filing-verbatim. Net: $-933,210,650.")
        new_phantom = ("of parser-invented compensation removed across 91 "
                       "re-verification batches since 2026-09-12, partly offset by "
                       "$4,010,158,645 of genuine missing NEO rows restored "
                       "filing-verbatim. Net: $-946,062,747.")
        jt = rep_once(jt, old_phantom, new_phantom, "js phantom-block")
        open(jp, "w", encoding="utf-8").write(jt)
        print("js/app.js synced")
    else:
        print("js/app.js already synced (idempotent)")

    # ---- GOAL.md ----
    gp = os.path.join(GOAL_DIR, "GOAL.md")
    gt = open(gp, encoding="utf-8").read()
    if "7,317 NEO rows" not in gt:
        gt = rep_once(gt, "7,316 NEO rows", "7,317 NEO rows", "GOAL.md rows")
        open(gp, "w", encoding="utf-8").write(gt)
        print("GOAL.md synced")
    else:
        print("GOAL.md already synced (idempotent)")

    # ---- S3 baseline in check_mismatch_reverify_20261028.py ----
    sp = os.path.join(REPO, "scripts", "check_mismatch_reverify_20261028.py")
    st = open(sp, encoding="utf-8").read()
    if 'total == 7317' not in st:
        st = st.replace(
            "# S3 baseline moved 2026-11-02 (317th review): FDX missing-NEO\n"
            "# restoration added 8 verified rows (Allen x2, Carter x3, Lenz x3,\n"
            "# filing-verbatim from the 2024 DEF 14A SCT) -> 7308->7316 rows,\n"
            "# verified_total 7264->7272, mismatch unchanged at 44.\n",
            "# S3 baseline moved 2026-11-02 (319th review): FIS Kehoe 2023\n"
            "# missing-NEO restoration (filing-verbatim from the 2026 DEF 14A\n"
            "# SCT) -> 7316->7317 rows, verified_total 7272->7273, mismatch\n"
            "# unchanged at 44.\n")
        st = st.replace('total == 7316 and mismatch == 44',
                        'total == 7317 and mismatch == 44')
        st = st.replace('["data_quality"]["verified_total"] == 7272',
                        '["data_quality"]["verified_total"] == 7273')
        st = st.replace("S3 counts unchanged (518 / 7316 / mismatch 44 / verified 7272)",
                        "S3 counts unchanged (518 / 7317 / mismatch 44 / verified 7273)")
        open(sp, "w", encoding="utf-8").write(st)
        print("S3 baseline moved")
    else:
        print("S3 baseline already moved (idempotent)")


if __name__ == "__main__":
    main()
