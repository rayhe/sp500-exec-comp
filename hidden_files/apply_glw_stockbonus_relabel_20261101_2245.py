#!/usr/bin/env python3
"""310th review (2026-11-01 22:45 PT): GLW stock-awards-mislabeled-as-bonus repair.

The tier-1 column-drop sibling detector
(hidden_files/detect_columndrop_siblings_20261101_1830.py) flagged 5 GLW rows
(Weeks 2025/2024/2023, Zhang 2025/2024). Filing arbitration against the 2026
DEF 14A SCT (acc. 0001206774-26-000148, filed 2026-03-20; raw HTML at goal
hidden_files/dq_20261101_2245/glw_2026_def14a.htm, SCT cell-parsed from the
filing) reveals a NEW column-drop sub-family, variant D: the legacy parse
filed the SCT's Stock Awards column into `bonus` and left `stock_awards`=0
on EVERY GLW row (all 14 NEO rows, whole-company). Corning's SCT has no
Bonus column at all; option awards are $0 for every NEO (Corning grants no
options). All other stored values (salary, NEIP, pension, all_other, total)
already match the filing verbatim, so the repair is a relabel: stored bonus
-> stock_awards, bonus -> 0. Totals are unchanged by the relabel.

Also adds 2 missing anchor-company NEO rows: A. Hal Nelson III (2025/2024),
named in the same 2026-proxy SCT but absent from the dataset (305th-review
KVUE Ruh precedent). Nelson 2024 carries the filing's own $1 arithmetic gap
(components sum 4,520,677 vs printed 4,520,678); stored verbatim with the
printed total, label 'verified' per the 2026-09-10 $1-delta taxonomy
decision. New rows are all-12-keys with explicit zeros (batch-4/5/6/7/8/9/10
convention) and go at the END of GLW's executives list.

Filing-verbatim titles: Weeks gains ", President"; Musser becomes "Former
President and Chief Operating Officer"; Steverson becomes "Vice Chairman,
Executive Vice President and Chief Legal and Administration Officer"; Zhang
un-abbreviated to "Executive Vice President and Chief Corporate Development
Officer"; Schlesinger unchanged. Names keep stored spellings (no periods
added, ELV/309th precedent).

Row schema: legacy omitted-zero rows keep their schema (ELV/309th
precedent); the filing's $0 option awards add no key. bonus=0 is written to
the existing bonus key.

Company aggregates (anchor FY2025 scoped): total_neo_compensation
62,635,883 -> 69,425,107 (Nelson 2025 +6,789,224), neo_count 5 -> 6;
total_compensation (Weeks) unchanged $25,756,121. Pay-ratio refresh from the
2026 proxy disclosure (304th-review YUM precedent): 451:1, median $57,059,
CEO $25,756,121. Section-17 aggregates recomputed with the guard's exact
semantics (copied from scripts/check_metadata_consistency.py).

Filing-verbatim values re-read digit-by-digit from the raw filing HTML.
"""
import json
import shutil
import statistics
import sys
from datetime import datetime

sys.path.insert(0, "/home/hatch/repos/sp500-exec-comp/hidden_files")
import phantom_record

REPO = "/home/hatch/repos/sp500-exec-comp"
DATA = f"{REPO}/data/compensation.json"
STAMP = datetime.now().strftime("%Y%m%d_%H%M")
BACKUP = f"{REPO}/data/compensation_backup_{STAMP}_pre_glw_stockbonus.json"

# (name, year): (filing stock_awards, filing-verbatim title or None to keep)
REPAIRS = {
    ("Wendell P Weeks", 2025):
        (11987000, "Chairman, Chief Executive Officer and President"),
    ("Wendell P Weeks", 2024):
        (9175447, "Chairman, Chief Executive Officer and President"),
    ("Wendell P Weeks", 2023):
        (11355517, "Chairman, Chief Executive Officer and President"),
    ("Edward A Schlesinger", 2025): (2854022, None),
    ("Edward A Schlesinger", 2024): (1724762, None),
    ("Edward A Schlesinger", 2023): (2056577, None),
    ("Eric S Musser", 2025):
        (4444609, "Former President and Chief Operating Officer"),
    ("Eric S Musser", 2024):
        (3445279, "Former President and Chief Operating Officer"),
    ("Eric S Musser", 2023):
        (4655565, "Former President and Chief Operating Officer"),
    ("Lewis A Steverson", 2025):
        (3611906, "Vice Chairman, Executive Vice President and Chief Legal and Administration Officer"),
    ("Lewis A Steverson", 2024):
        (2756210, "Vice Chairman, Executive Vice President and Chief Legal and Administration Officer"),
    ("Lewis A Steverson", 2023):
        (3500556, "Vice Chairman, Executive Vice President and Chief Legal and Administration Officer"),
    ("John Z Zhang", 2025):
        (2741127, "Executive Vice President and Chief Corporate Development Officer"),
    ("John Z Zhang", 2024):
        (1647529, "Executive Vice President and Chief Corporate Development Officer"),
}

# pre-repair stored totals asserted before any write (old-value guard)
OLD_TOTALS = {
    ("Wendell P Weeks", 2025): 25756121,
    ("Wendell P Weeks", 2024): 21686436,
    ("Wendell P Weeks", 2023): 15627653,
    ("Edward A Schlesinger", 2025): 7415346,
    ("Edward A Schlesinger", 2024): 5163592,
    ("Edward A Schlesinger", 2023): 3566214,
    ("Eric S Musser", 2025): 12102878,
    ("Eric S Musser", 2024): 9925488,
    ("Eric S Musser", 2023): 6716555,
    ("Lewis A Steverson", 2025): 9083355,
    ("Lewis A Steverson", 2024): 7406544,
    ("Lewis A Steverson", 2023): 5760516,
    ("John Z Zhang", 2025): 8278183,
    ("John Z Zhang", 2024): 6291272,
}

# Missing anchor-company NEO rows, filing-verbatim from the 2026 DEF 14A SCT.
# All-12-keys with explicit zeros (new-row convention). Appended at the END
# of GLW's executives list.
NELSON_ROWS = [
    dict(name="A. Hal Nelson III",
         title="Executive Vice President and Chief Operating Officer",
         year=2025, salary=668269, bonus=0, stock_awards=2741127,
         option_awards=0, non_equity_incentive=1940194, pension_nqdc=1356894,
         all_other=82740, total=6789224, _total_source="verified"),
    dict(name="A. Hal Nelson III",
         title="Executive Vice President and Chief Operating Officer",
         year=2024, salary=609615, bonus=0, stock_awards=1647529,
         option_awards=0, non_equity_incentive=1834844, pension_nqdc=395775,
         all_other=32914, total=4520678, _total_source="verified"),
]

COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]


def _anchor_row_for(c):
    ceo, fy, tot = (c.get("ceo_name", ""), c.get("fiscal_year"),
                    c.get("total_compensation", 0))
    if not tot:
        return None
    rows = [e for e in c.get("executives", [])
            if e.get("name") == ceo and e.get("year") == fy]
    if not rows:
        rows = [e for e in c.get("executives", []) if e.get("total") == tot]
    return rows[0] if rows else None


def _is_verified_source(src):
    return bool(src) and (src.startswith("verified")
                          or src.startswith("def14a_verified"))


def main():
    shutil.copy2(DATA, BACKUP)
    print("backup:", BACKUP)
    data = json.load(open(DATA, encoding="utf-8"))
    cos = data["companies"]
    glw = next(c for c in cos if c["ticker"] == "GLW")

    # Nelson must be absent before we add him (no duplicate rows)
    assert not [e for e in glw["executives"]
                if e["name"] == "A. Hal Nelson III"], "Nelson already present"

    fixed = 0
    for e in glw["executives"]:
        key = (e["name"], e["year"])
        if key not in REPAIRS:
            continue
        assert e["total"] == OLD_TOTALS[key], \
            f"unexpected stored total for {key}: {e['total']}"
        assert e.get("_total_source") == "verified", \
            f"unexpected _total_source for {key}"
        stock, title = REPAIRS[key]
        # pre-repair shape: the misfiled stock value sits in bonus,
        # stock_awards is 0
        assert e.get("bonus") == stock, \
            f"unexpected stored bonus for {key}: {e.get('bonus')}"
        assert e.get("stock_awards", 0) == 0, \
            f"unexpected stored stock_awards for {key}"
        e["stock_awards"] = stock
        e["bonus"] = 0
        if title is not None:
            e["title"] = title
        # relabeled row must foot exactly against the filing mapping
        assert sum(e.get(k, 0) or 0 for k in COMPS) == e["total"], \
            f"repaired row does not foot: {key}"
        e["_repair_note_20261101_2245"] = (
            "2026-11-01 22:45 PT (310th review): 2026 DEF 14A SCT "
            "(acc. 0001206774-26-000148) shows variant D of the column-drop "
            "family: legacy parse filed the SCT Stock Awards column into "
            "bonus on every GLW row (Corning's SCT has no Bonus column; "
            "option awards $0, Corning grants none). Relabeled "
            "filing-verbatim; titles filing-verbatim; _total_source "
            "('verified') untouched.")
        fixed += 1
    assert fixed == 14, f"expected 14 rows fixed, got {fixed}"

    # Nelson rows: explicit key mapping (never positional zip), appended at
    # the END of the company's executives list
    for n in NELSON_ROWS:
        comps = sum(n.get(k, 0) for k in COMPS)
        gap = abs(comps - n["total"])
        assert gap <= 1, f"Nelson row gap too large: {n['year']} {gap}"
        if gap:
            print(f"note: Nelson {n['year']} carries the filing's own "
                  f"${gap} arithmetic gap (stored verbatim)")
        row = dict(name=n["name"], title=n["title"], year=n["year"],
                   salary=n["salary"], bonus=n["bonus"],
                   stock_awards=n["stock_awards"],
                   option_awards=n["option_awards"],
                   non_equity_incentive=n["non_equity_incentive"],
                   pension_nqdc=n["pension_nqdc"], all_other=n["all_other"],
                   total=n["total"], _total_source=n["_total_source"])
        glw["executives"].append(row)
    print("added 2 Nelson rows")

    # company aggregates, anchor FY2025 scoped
    rows25 = [e for e in glw["executives"] if e["year"] == 2025]
    assert len(rows25) == 6, f"expected 6 FY2025 rows, got {len(rows25)}"
    glw["total_neo_compensation"] = sum(e["total"] for e in rows25)
    assert glw["total_neo_compensation"] == 69425107
    glw["neo_count"] = 6
    weeks = next(e for e in rows25 if e["name"] == "Wendell P Weeks")
    assert weeks["total"] == 25756121
    glw["total_compensation"] = weeks["total"]
    # pay-ratio refresh: 2026 proxy discloses 451:1, CEO $25,756,121,
    # median $57,059
    glw["pay_ratio"] = 451
    glw["median_worker_pay"] = 57059

    # section-17 aggregate recompute (guard's exact semantics)
    ceo_pays = [c["total_compensation"] for c in cos
                if c.get("total_compensation", 0) > 0]
    worker_pays = [c["median_worker_pay"] for c in cos
                   if c.get("median_worker_pay")
                   and c["median_worker_pay"] > 0]
    ratios = [c["pay_ratio"] for c in cos
              if c.get("pay_ratio") is not None and c["pay_ratio"] > 0]
    agg = data["metadata"]["aggregate_stats"]
    agg["total_companies"] = len(cos)
    agg["companies_with_pay_ratio"] = len(ratios)
    agg["median_ceo_pay"] = int(statistics.median(ceo_pays))
    agg["mean_ceo_pay"] = int(statistics.mean(ceo_pays))
    agg["max_ceo_pay"] = max(ceo_pays)
    agg["min_ceo_pay"] = min(ceo_pays)
    agg["median_worker_pay"] = int(statistics.median(worker_pays))
    agg["median_pay_ratio"] = int(statistics.median(ratios))

    sector_pays = {}
    for c in cos:
        if c.get("total_compensation", 0) > 0:
            sector_pays.setdefault(c.get("sector", "Unknown"), []).append(
                c["total_compensation"])
    sector_cov = {}
    for c in cos:
        a = _anchor_row_for(c)
        if a is None:
            continue
        s = c.get("sector", "Unknown")
        r = sector_cov.setdefault(s, {"ver": 0, "doc": 0, "undoc": 0})
        src = a.get("_total_source") or ""
        if _is_verified_source(src):
            r["ver"] += 1
        elif a.get("_note"):
            r["doc"] += 1
        else:
            r["undoc"] += 1
    sm = data["metadata"]["sector_medians"]
    assert set(sm.keys()) == set(sector_pays.keys())
    for s, p in sector_pays.items():
        e = sm[s]
        cov = sector_cov.get(s, {"ver": 0, "doc": 0, "undoc": 0})
        e["median_ceo_pay"] = int(statistics.median(p))
        e["count"] = len(p)
        e["min"] = min(p)
        e["max"] = max(p)
        e["verified_anchors"] = cov["ver"]
        e["documented_anchors"] = cov["doc"]
        e["undocumented_anchors"] = cov["undoc"]
        e["verified_pct"] = round(100.0 * cov["ver"] / len(p), 1)

    # record counts + DQ-batch timestamp convention
    data["metadata"]["total_neo_records"] = 7307
    data["metadata"]["last_dq_repair"] = "2026-11-01"
    data["last_updated"] = "2026-11-01"

    json.dump(data, open(DATA, "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    open(DATA, "a", encoding="utf-8").write("\n")
    print("repaired 14 GLW rows, added 2 Nelson rows; aggregates recomputed")

    delta = phantom_record.record_batch(
        pre_path=BACKUP, data_path=DATA, stamp="2026-11-01 22:45 PT")
    print(f"phantom delta: ${delta:,}")


if __name__ == "__main__":
    main()
