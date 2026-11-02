#!/usr/bin/env python3
"""316th review (2026-11-02 10:30 PT): metadata + static-copy sync.

Row count 7307 -> 7308 (VRTX Tatsis 2024 restored); verified 7263 -> 7264.
Phantom counters already updated by phantom_record.record_batch in the repair
script (gross_removed $3,064,095,898 / restored $3,956,441,779 /
net $-892,345,881 / batches 88 -- gross is the record_batch net-delta
convention per the 312th-run lesson, NOT the pre-net figure).
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")


def rep_once(text, old, new, where):
    assert text.count(old) == 1, f"{where}: found {text.count(old)}x {old!r:.60}"
    return text.replace(old, new, 1)


def main():
    # ---- metadata buckets ----
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    m = d["metadata"]
    # idempotent: values may already be synced from a prior partial run
    if m["total_neo_records"] == 7307:
        m["total_neo_records"] = 7308
        m["total_executives"] = 7308
        m["total_neos"] = 7308
        m["title_coverage"] = "7308/7308"
        m["verified_total"] = 7264
        m["description"] = m["description"].replace("7307 NEO records",
                                                    "7308 NEO records", 1)
        for block in ("data_quality", "data_quality_detailed"):
            assert m[block]["verified"] == 5848, block
            assert m[block]["verified_total"] == 7263, block
            m[block]["verified"] = 5849
            m[block]["verified_total"] = 7264
    assert m["total_neo_records"] == 7308
    assert m["verified_total"] == 7264
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("metadata synced")

    # ---- README.md ----
    rp = os.path.join(REPO, "README.md")
    t = open(rp, encoding="utf-8").read()
    t = rep_once(t,
                 "99.4% verified component-total consistency (7,263 of 7,307 records,",
                 "99.4% verified component-total consistency (7,264 of 7,308 records,",
                 "README headline")
    t = rep_once(t,
                 "Component-total consistency verified: 99.4% verified (7,263 of 7,307 total NEO records),",
                 "Component-total consistency verified: 99.4% verified (7,264 of 7,308 total NEO records),",
                 "README taxonomy")
    t = rep_once(t,
                 "Buckets (as of 2026-10-30: 7,307 rows):",
                 "Buckets (as of 2026-11-02: 7,308 rows):",
                 "README buckets")
    # append the 316th audit-trail entry to the item-4 paragraph
    anchor = ("batches 86->87, net $-959,071,507->$-959,077,202. Tier-1 queue "
              "8->0 (tier-2 1172 advisory). verified_total 7,263 (99.4%), "
              "component_mismatch 44, rows 7,307 unchanged. Guard green.")
    assert t.count(anchor) == 1, "README audit anchor not unique"
    entry = (
        " 2026-11-02 10:30 PT column-drop triage batch (316th review): "
        "variant-G sweep via the total-footing identity (implied filing salary "
        "= 2*all_other - total; all_other/total in [0.50, 0.67]; implied round "
        "to $1k in [$200k, $4M]; exact footing) -- the 313th review's tier-1 "
        "option_awards==0 gate is blind to variant-G rows whose filing NEIP>0 "
        "parks in option_awards. 11 candidates arbitrated against primary DEF "
        "14A SCTs (EDGAR, declared UA), all CONFIRMED: SBAC 7-row whole-company "
        "repair filing-verbatim from the 2025 DEF 14A (acc. 0001193125-25-074669) "
        "-- SCT has 5 data columns (Salary | Stock Awards | NEIP | All Other | "
        "Total; no Bonus/Option/pension); legacy parse dropped the Salary cell "
        "(Stock->salary, NEIP->stock_awards, All Other->non_equity_incentive, "
        "filing Total->all_other, total recomputed; variant G, 5-column form); "
        "implied salary equals the filing salary EXACTLY on all 7 rows "
        "(Cavanagh 2024 $16,715,004->$8,817,502; Montagner 2024 $7,325,044->"
        "$3,982,522; Ciarfella 2024 $5,721,136->$3,120,568 and 2023 "
        "$4,928,584->$2,704,292; Cane 2024 $5,582,308->$3,046,154 and 2023 "
        "$4,867,570->$2,668,785; Koenig 2024 $5,451,268->$2,980,634); the 5 "
        "FY2025 rows and Cavanagh 2023 byte-equal to the 2025/2026-proxy SCTs, "
        "no changes. JBL 7-row whole-company repair -- the 2024 DEF 14A "
        "(acc. 0001193125-24-277123) and 2025 DEF 14A (acc. 0001193125-25-316927) "
        "SCTs both have 6 data columns (Salary | Stock Awards | NEIP | All Other "
        "| Total; variant G, 6-column form); the $1k-roundness gate caught only "
        "Mondello 2023 / Borges 2023+2024, full-SCT arbitration caught the 4 "
        "non-round-salary siblings the sweep could not see (Mondello 2024 "
        "$15,415,879->$8,232,459; Mondello 2023 $31,947,000->$16,601,000; Dastoor "
        "2024 $9,620,872->$5,249,282 and 2023 $8,927,705->$4,822,314; Hebard 2024 "
        "$2,553,783->$1,517,228; Borges 2024 $7,158,464->$3,939,232 and 2023 "
        "$7,886,338->$4,303,169); CD&A base-salary table independently confirms "
        "Mondello FY23 $1,255,000 / Borges $720,000; all 5 FY2025 rows "
        "byte-equal, no changes. FDX 1-row repair filing-verbatim from the 2024 "
        "DEF 14A (acc. 0001308179-24-000696) -- full 8-column SCT; Subramaniam "
        "2023 $25,199,646->$13,249,823 (variant G, 8-column form, "
        "all-other-retained sub-flavor: filing All Other $1,527,904 lands in "
        "pension_nqdc, unlike the Citi 313th form where it was dropped); "
        "Subramaniam/Dietrich/Krishnasamy 2024 byte-equal, no changes. VRTX "
        "Nia Tatsis 2024 ($691,154 / -- / $5,250,328 / $1,341,900 / $50,934 / "
        "$7,334,316) restored filing-verbatim from the 2026 DEF 14A SCT "
        "(acc. 0000875320-26-000153) -- queued by the 314th review. Company "
        "aggregates untouched (all anchor fiscal years intact), titles/ "
        "_total_source untouched. $74,065,637 parser-invented compensation "
        "removed (SBAC $23,270,457 + JBL $38,845,357 + FDX $11,949,823); "
        "$7,334,316 genuine restored. Phantom counter: gross_removed "
        "$2,997,364,577->$3,064,095,898, restored unchanged at "
        "$3,956,441,779, batches 87->88, net $-959,077,202->$-892,345,881. "
        "verified_total 7,263->7,264 (99.4%), component_mismatch 44, rows "
        "7,307->7,308. Guard green."
    )
    t = t.replace(anchor, anchor + entry, 1)
    open(rp, "w", encoding="utf-8").write(t)
    print("README synced")

    # ---- index.html ----
    ip = os.path.join(REPO, "index.html")
    it = open(ip, encoding="utf-8").read()
    it = rep_once(it, "7,307 Named Executive Officer records",
                  "7,308 Named Executive Officer records", "index.html")
    open(ip, "w", encoding="utf-8").write(it)
    print("index.html synced")

    # ---- js/app.js ----
    jp = os.path.join(REPO, "js", "app.js")
    jt = open(jp, encoding="utf-8").read()
    jt = rep_once(jt, "7,263 of 7,307 NEO rows verified (99.4%)",
                  "7,264 of 7,308 NEO rows verified (99.4%)", "js coverage")
    old_phantom = ("$2,997,364,577 of parser-invented compensation removed across 87 "
                   "re-verification batches since 2026-09-12, partly offset by "
                   "$3,956,441,779 of genuine missing NEO rows restored "
                   "filing-verbatim. Net: $-959,077,202.")
    new_phantom = ("$3,064,095,898 of parser-invented compensation removed across 88 "
                   "re-verification batches since 2026-09-12, partly offset by "
                   "$3,956,441,779 of genuine missing NEO rows restored "
                   "filing-verbatim. Net: $-892,345,881.")
    jt = rep_once(jt, old_phantom, new_phantom, "js phantom-block")
    open(jp, "w", encoding="utf-8").write(jt)
    print("js/app.js synced")


if __name__ == "__main__":
    main()
