"""CEO-anchor total_compensation repair batch, 2026-09-10 02:00 PT run.

Fixes the 30 companies where stored total_compensation did not match the
anchor-year (fiscal_year) CEO's verified SCT row:
- 19 stale/wrong stored totals -> anchor-year CEO SCT total (pay_ratio left
  alone where it already pairs with the corrected total)
- 3 (WELL/STE/LKQ) where stored total was wrong AND pay_ratio paired with the
  stale total -> ratio recomputed from corrected total / stored median
- 1 (D) exact doubling -> halved
- 8 CEO-transition cases resolved per the least-false-statement principle:
  total must equal the verified SCT total of the person named in ceo_name,
  preferring their anchor-year row, else their newest verified row
- TMUS: ceo_name was factually wrong (Ulf Ewaldsson was never CEO; terminated
  2025-12-01). 2026 DEF 14A proves Srinivasan Gopalan became President & CEO
  2025-11-01. ceo_name -> Gopalan, total -> his verified 2025 SCT, pay ratio
  -> filed FY2025 disclosure (499:1, median $76,141).
- LH: full 14-row DEF 14A rebuild (12 from 2026 proxy SCT + Eisenberg/Graham
  2024 from 2025 proxy SCT); prior 9 rows were corrupt/incomplete.
- WSM: 2023/2024 "Director" rows -> Laura Alber (filing title).
- PEG: 2023/2024 "Chair of the Board" rows -> Ralph A. LaRossa; delete phantom
  2023 LaRossa row ($10,925,666, nonsense components, no filing match).

Every mutation asserts the pre-change value first. Run from repo root.
"""
import json
import sys

PATH = "data/compensation.json"

# (ticker, old_total, new_total, old_ratio, new_ratio, note)
FIXES = [
    ("D",    25809250, 12904625, 104, 104, "exact doubling of Blue FY2024 12,904,625"),
    ("LEN",  29527931, 29546675, 306, 306, "Miller FY2024 row 29,546,675; ratio recompute 306 unchanged"),
    ("V",    31560660, 25999293, 169, 169, "Kelly FY2024 row 25,999,293"),
    ("WELL", 821090355, 20200824, 6569, 162, "stored was FY2025 mega-grant; ratio recomputed 20,200,824/124,716=162"),
    ("HPQ",  23103812, 19360127, 278, 278, "Lores FY2024 row 19,360,127"),
    ("OXY",  18055969, 18535061, 85, 85, "Hollub FY2024 row 18,535,061"),
    ("ODFL", 11615896, 12622664, 163, 163, "Satterfield FY2024 row 12,622,664"),
    ("LKQ",  8767864, 4501186, 182, 93, "ratio recomputed 4,501,186/48,400=93"),
    ("STE",  11508522, 9550776, 157, 130, "ratio recomputed 9,550,776/73,452=130"),
    ("AMP",  48288430, 28144215, 210, 210, "Cracchiolo FY2024 row"),
    ("IBM",  26177466, 25143682, 518, 518, "Krishna FY2024 row"),
    ("ABT",  22591322, 22777075, 177, 177, "Ford FY2024 row"),
    ("PNC",  14858170, 22352785, 179, 179, "Demchak FY2024 row"),
    ("ADM",  17700055, 21569894, 268, 268, "Luciano FY2024 row"),
    ("TDG",  25188928, 21432369, 343, 343, "Stein FY2024 row"),
    ("GEN",  27723786, 15362827, 188, 188, "Pilette FY2024 row"),
    ("ED",   26966889, 14984213, 116, 116, "Cawley FY2024 row"),
    ("VMC",  24486506, 12860753, 119, 119, "Hill FY2024 row"),
    ("ENPH", 24810010, 12630005, 212, 212, "Kothandaraman FY2024 row"),
    ("MCO",  13749940, 16966442, 159, 159, "Fauber FY2024 row"),
    ("APA",  12139173, 11440709, 55, 55, "Christmann FY2024 row"),
    ("MOS",  10815579, 9880653, 229, 229, "Bodine FY2024 row"),
    ("ROL",  7787083, 8236749, 132, 132, "Gahlhoff FY2024 row"),
    ("EIX",  12536305, 13809571, 75, 75, "Pizarro FY2024 row"),
    ("ALB",  15382737, 14368498, 212, 212, "Masters FY2024 row"),
    ("MNST", 20991964, 17709651, 173, 173, "Sacks FY2024 co-CEO row"),
    ("HSIC", 5026957, 11640272, 152, 152, "Bergman FY2024 row"),
    ("ISRG", 20997480, 13762318, 147, 147, "Rosa FY2024 President row; filed ratio 147 is Guthart-based, left as filed"),
    ("TMUS", 44622892, 35439421, 406, 499, "Gopalan FY2025 SCT; filed FY2025 ratio 499, median 76,141"),
]

LH_ROWS = [
    # name, title, year, salary, bonus, options, stock, neip, pension, other, total
    ("Adam H. Schechter", "President and Chief Executive Officer", 2025, 1435000, 0, 2754582, 11400463, 2062095, 0, 687773, 18339913),
    ("Adam H. Schechter", "President and Chief Executive Officer", 2024, 1416077, 0, 3015965, 12162271, 2113816, 0, 619225, 19327354),
    ("Adam H. Schechter", "President and Chief Executive Officer", 2023, 1373692, 0, 2250072, 9071320, 2346018, 0, 938253, 15979355),
    ("Julia A. Wang", "Executive Vice President and Chief Financial Officer", 2025, 737500, 200000, 649116, 2681239, 706755, 0, 40259, 5014869),
    ("Julia A. Wang", "Executive Vice President and Chief Financial Officer", 2024, 55769, 0, 638067, 2668417, 0, 0, 133, 3362386),
    ("Megan D. Bailey", "Executive Vice President and President, Central Laboratories and International", 2025, 568500, 0, 307914, 1257480, 547622, 0, 34751, 2716267),
    ("Brian J. Caveney", "Executive Vice President and President, Early Development Research Laboratories and Chief Medical and Scientific Officer", 2025, 748461, 0, 557574, 2304466, 719907, 0, 25515, 4355923),
    ("Brian J. Caveney", "Executive Vice President and President, Early Development Research Laboratories and Chief Medical and Scientific Officer", 2024, 660769, 0, 451666, 1825122, 604039, 0, 26161, 3567757),
    ("Brian J. Caveney", "Executive Vice President and President, Early Development Research Laboratories and Chief Medical and Scientific Officer", 2023, 617635, 0, 432955, 1745352, 609719, 0, 70782, 3476443),
    ("Mark S. Schroeder", "Former Executive Vice President and President, Diagnostics and Chief Operations Officer", 2025, 748461, 0, 607506, 2514961, 727399, 11187, 177643, 4787157),
    ("Mark S. Schroeder", "Former Executive Vice President and President, Diagnostics and Chief Operations Officer", 2024, 660769, 0, 502661, 2027426, 678718, 280, 116453, 3986307),
    ("Mark S. Schroeder", "Former Executive Vice President and President, Diagnostics and Chief Operations Officer", 2023, 617635, 0, 461625, 1892720, 718807, 13815, 90506, 3795108),
    ("Glenn A. Eisenberg", "Executive Vice President and Former Chief Financial Officer", 2024, 830462, 0, 655645, 2634274, 826440, 0, 55087, 5001908),
    ("Anita Z. Graham", "Executive Vice President and Chief Human Resources Officer", 2024, 569154, 500000, 218548, 890976, 481437, 0, 25432, 2685547),
]

NEW_LABEL = "def14a_verified_20260910"


def fail(msg):
    print("ASSERT FAILED:", msg, file=sys.stderr)
    sys.exit(1)


def main():
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)
    companies = {c["ticker"]: c for c in data["companies"]}
    changed = []

    # --- 1. company-level total/ratio fixes ---
    for ticker, old_total, new_total, old_ratio, new_ratio, note in FIXES:
        c = companies[ticker]
        if c.get("total_compensation") != old_total:
            fail(f"{ticker}: total_compensation={c.get('total_compensation')} != expected old {old_total}")
        if c.get("pay_ratio") != old_ratio:
            fail(f"{ticker}: pay_ratio={c.get('pay_ratio')} != expected old {old_ratio}")
        fy = c.get("fiscal_year")
        ceo = c.get("ceo_name")
        # find the anchor row the new total must come from.
        # TMUS special case: ceo_name is wrong (Ewaldsson never CEO); the new
        # total comes from Gopalan's 2025 row and ceo_name is fixed below.
        if ticker == "TMUS":
            rows = [e for e in c["executives"]
                    if e.get("name") == "Srinivasan Gopalan" and e.get("year") == 2025]
            src = rows
        else:
            rows = [e for e in c["executives"] if e.get("name") == ceo]
            anchor = [e for e in rows if e.get("year") == fy]
            src = anchor or sorted(rows, key=lambda e: e.get("year", 0), reverse=True)
        if not src:
            fail(f"{ticker}: no rows at all for ceo_name={ceo!r}")
        if src[0].get("total") != new_total:
            fail(f"{ticker}: {ceo} {src[0].get('year')} row total={src[0].get('total')} != new {new_total}")
        c["total_compensation"] = new_total
        c["pay_ratio"] = new_ratio
        changed.append(f"{ticker}: {old_total:,} -> {new_total:,} (ratio {old_ratio}->{new_ratio}) [{note}]")

    # --- 2. TMUS CEO identity fix (asserts done above for totals) ---
    t = companies["TMUS"]
    if t.get("ceo_name") != "Ulf Ewaldsson":
        fail(f"TMUS ceo_name={t.get('ceo_name')!r}")
    if t.get("median_worker_pay") != 74097:
        fail(f"TMUS median_worker_pay={t.get('median_worker_pay')}")
    t["ceo_name"] = "Srinivasan Gopalan"
    t["median_worker_pay"] = 76141
    t["ceo_tenure"] = {"year": 2025, "month": 11, "confidence": "high",
                       "sources": ["def14a_2026_ceo_transition_20251101"]}
    changed.append("TMUS: ceo_name Ulf Ewaldsson -> Srinivasan Gopalan (2026 DEF 14A: CEO from 2025-11-01; Ewaldsson terminated 2025-12-01)")

    # --- 3. WSM renames ---
    w = companies["WSM"]
    for e in w["executives"]:
        if e.get("name") == "Director":
            if e["year"] == 2024 and e["total"] != 27692374:
                fail("WSM 2024 Director row total changed")
            if e["year"] == 2023 and e["total"] != 23696540:
                fail("WSM 2023 Director row total changed")
            e["name"] = "Laura Alber"
            e["title"] = "Director, President, and Chief Executive Officer"
            changed.append(f"WSM: Director {e['year']} -> Laura Alber ({e['total']:,})")

    # --- 4. PEG renames + phantom delete ---
    p = companies["PEG"]
    kept = []
    for e in p["executives"]:
        if e.get("name") == "Chair of the Board" and e["year"] in (2023, 2024):
            exp = {2023: 11778863, 2024: 12367961}[e["year"]]
            if e["total"] != exp:
                fail(f"PEG CoB {e['year']} total={e['total']} != {exp}")
            e["name"] = "Ralph A. LaRossa"
            changed.append(f"PEG: Chair of the Board {e['year']} -> Ralph A. LaRossa ({e['total']:,})")
            kept.append(e)
        elif e.get("name") == "Ralph A. LaRossa" and e["year"] == 2023 and e["total"] == 10925666:
            changed.append("PEG: deleted phantom 2023 Ralph A. LaRossa row (10,925,666, nonsense components)")
        else:
            kept.append(e)
    if len(p["executives"]) - len(kept) != 1:
        fail("PEG phantom delete removed != 1 row")
    p["executives"] = kept

    # --- 5. LH full rebuild ---
    lh = companies["LH"]
    if len(lh["executives"]) != 9:
        fail(f"LH has {len(lh['executives'])} rows, expected 9")
    if lh.get("total_compensation") != 5129781:
        fail(f"LH total_compensation={lh.get('total_compensation')}")
    if lh.get("neo_count") != 2:
        fail(f"LH neo_count={lh.get('neo_count')}")
    if lh.get("total_neo_compensation") != 5767848:
        fail(f"LH total_neo_compensation={lh.get('total_neo_compensation')}")
    if lh.get("pay_ratio") != 337:
        fail(f"LH pay_ratio={lh.get('pay_ratio')}")
    new_rows = []
    for name, title, year, sal, bon, opt, stk, nei, pen, oth, tot in LH_ROWS:
        if sal + bon + opt + stk + nei + pen + oth != tot:
            fail(f"LH new row {name} {year} does not foot")
        new_rows.append({
            "name": name, "title": title, "year": year,
            "salary": sal, "bonus": bon, "option_awards": opt,
            "stock_awards": stk, "non_equity_incentive": nei,
            "pension_nqdc": pen, "all_other": oth, "total": tot,
            "_total_source": NEW_LABEL,
        })
    lh["executives"] = new_rows
    lh_2024 = [e for e in new_rows if e["year"] == 2024]
    lh["total_compensation"] = 19327354
    lh["neo_count"] = len(lh_2024)
    lh["total_neo_compensation"] = sum(e["total"] for e in lh_2024)
    if lh["total_neo_compensation"] != 37931259:
        fail(f"LH neo sum={lh['total_neo_compensation']}")
    changed.append("LH: rebuilt 9 corrupt rows -> 14 DEF 14A rows (2026 proxy SCT x12 + 2025 proxy SCT x2); total 5,129,781 -> 19,327,354; neo_count 2 -> 6")

    # --- 6. metadata ---
    n = sum(len(c.get("executives", [])) for c in data["companies"])
    meta = data["metadata"]
    meta["total_neo_records"] = n
    meta["total_executives"] = n
    meta["title_coverage"] = f"{n}/{n}"
    meta["last_updated"] = "2026-09-10"
    meta["data_collected"] = "2026-09-10"
    from collections import Counter
    buckets = Counter(e.get("_total_source", "?") for c in data["companies"] for e in c.get("executives", []))
    for block in ("data_quality", "data_quality_detailed"):
        dq = meta[block]
        for k, v in buckets.items():
            dq[k] = v
        # zero out (never delete) stale bucket keys so the guard's bucket-sum
        # stays exact and the file shape is stable across runs
        for k in [k for k in dq if k not in buckets and k not in ("verified_total", "last_audit")]:
            dq[k] = 0
        vt = sum(v for k, v in buckets.items() if k == "verified" or k.startswith("def14a_verified_"))
        dq["verified_total"] = vt
    dq = meta["data_quality"]
    if sum(v for k, v in dq.items() if isinstance(v, int) and k != "verified_total") != n:
        fail("bucket sum != n")
    desc = meta.get("description", "")
    meta["description"] = desc.replace("6774 NEO records", f"{n} NEO records").replace(
        "2026-09-09", "2026-09-10")
    meta.setdefault("notes", []).append(
        "CEO-anchor re-verification 2026-09-10 02:00 PT: 30 companies had stored total_compensation "
        "not matching the anchor-year CEO's verified SCT row (19 stale totals, D doubling, WELL/STE/LKQ "
        "stale total + paired ratio, 8 CEO-transition judgments). All corrected to the anchor-year "
        "(or newest verified, where the named CEO has no anchor-year row) SCT total; WELL/STE/LKQ ratios "
        "recomputed from corrected totals. TMUS ceo_name corrected Ulf Ewaldsson -> Srinivasan Gopalan "
        "per 2026 DEF 14A (CEO since 2025-11-01; Ewaldsson terminated 2025-12-01); ratio -> filed FY2025 "
        "499:1, median $76,141. LH rebuilt: 9 corrupt rows replaced with 14 DEF 14A rows (2026 proxy SCT "
        "for Schechter/Wang/Bailey/Caveney/Schroeder + 2025 proxy SCT for Eisenberg/Graham 2024); total "
        "5,129,781 -> 19,327,354 (pairs with filed ratio 337). WSM 2023/2024 'Director' rows -> Laura "
        "Alber. PEG 'Chair of the Board' rows -> Ralph A. LaRossa; phantom 2023 LaRossa row (10,925,666) "
        "deleted. Record count 6774 -> %d." % n)

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"OK: {n} records")
    for line in changed:
        print(" -", line)


if __name__ == "__main__":
    main()
