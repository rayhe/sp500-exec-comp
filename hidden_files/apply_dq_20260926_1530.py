#!/usr/bin/env python3
"""DQ 2026-09-26 15:30 PT: repair salary-drop column-shift corruption in the
CNP/CINF/HII 2026-proxy SCT parses.

The parser dropped the Salary cell on FY2023/FY2024 SCT rows, shifting every
component one column left: the printed Total landed in all_other and the
stored total was recomputed as a ~2x phantom sum. The full SCT re-read found
17 corrupted rows (the 8-row pension/neip-confusion queue subset plus 9
siblings, including the HII CEO-anchor row). This script:

1. Asserts every row still carries its expected CORRUPTED values (pre-write
   assertion; aborts on any drift).
2. Writes the filing-verbatim values from hidden_files/dq_batch_20260926_1530.json.
3. Re-anchors CNP/HII FY2024 company aggregates and the HII CEO anchor total.
4. Asserts post-repair footing ($0 for all rows except CNP Foster 2024, whose
   genuine $1 filing-side gap is kept verbatim).
"""
import json, sys

REPO = "/home/hatch/repos/sp500-exec-comp"
ACC = {
    "CNP": "0001104659-26-023457",
    "CINF": "0000020286-26-000015",
    "HII": "0001501585-26-000014",
}

# expected CURRENT (corrupted) stored values: (ticker, name, year, stored_tuple)
CORRUPT = {
    ("CNP", "Christopher A. Foster", 2024): (0, 1884987, 0, 725000, 0, 245915, 3574172, 6430074),
    ("CNP", "Monica Karuturi", 2024): (100000, 1884987, 0, 725000, 42968, 189449, 3660674, 6603078),
    ("CNP", "Monica Karuturi", 2023): (0, 1819984, 0, 980000, 64802, 91667, 3651838, 6608291),
    ("CNP", "Jason M. Ryan", 2024): (0, 1050002, 0, 459375, 37755, 172881, 2240975, 3960988),
    ("CNP", "Jason M. Ryan", 2023): (200000, 1570014, 0, 624750, 58652, 99211, 3058589, 5611216),
    ("CINF", "Stephen M. Spray", 2023): (0, 1372772, 855096, 1140111, 398237, 48645, 4708647, 8523508),
    ("CINF", "Michael J. Sewell", 2023): (0, 1511422, 941511, 1255307, 0, 222681, 4926421, 8857342),
    ("CINF", "John S. Kellington", 2023): (0, 1054377, 656505, 875324, 0, 117272, 3397639, 6101117),
    ("CINF", "Teresa C. Cracas", 2023): (0, 960083, 597761, 797014, 0, 125175, 3112092, 5592125),
    ("HII", "Christopher D. Kastner", 2024): (6499823, 1225250, 5316085, 231738, 14553665, 27826561),
    ("HII", "Christopher D. Kastner", 2023): (5799855, 2997000, 3962861, 160519, 14100619, 27020854),
    ("HII", "Thomas E. Stiehle", 2024): (1499604, 307970, 1376737, 78908, 3852816, 7116035),
    ("HII", "Thomas E. Stiehle", 2023): (1499944, 851000, 1823692, 65757, 4815393, 9055786),
    ("HII", "Chad N. Boudreaux", 2024): (1149572, 305292, 0, 207749, 2247083, 3909696),
    ("HII", "Chad N. Boudreaux", 2023): (1149814, 843600, 0, 160846, 2724261, 4878521),
    ("HII", "Edgar A. Green III", 2024): (1149572, 904000, 0, 197330, 2800942, 5051844),
    ("HII", "Edgar A. Green III", 2023): (1149814, 814784, 0, 115846, 2610902, 4691346),
}
# stored tuple layout: CNP/CINF = (salary, bonus, stock, option, neip, pension, all_other, total)
#                       HII    = (salary, stock, neip, pension, all_other, total)

FIELDS8 = ["salary", "bonus", "stock_awards", "option_awards",
           "non_equity_incentive", "pension_nqdc", "all_other", "total"]
FIELDS6 = ["salary", "stock_awards", "non_equity_incentive",
           "pension_nqdc", "all_other", "total"]

def find(co, name, year):
    for e in co["executives"]:
        if e["name"] == name and e["year"] == year:
            return e
    raise AssertionError(f"row not found: {name} {year}")

def main():
    path = REPO + "/data/compensation.json"
    # pre-repair backup FIRST (untracked; never swept into the commit)
    raw = open(path).read()
    with open(REPO + "/hidden_files/compensation_backup_20260926_1530_pre_colshift.json", "w") as fh:
        fh.write(raw)
    d = json.loads(raw)
    cos = {c["ticker"]: c for c in d["companies"]}
    batch = json.load(open(REPO + "/hidden_files/dq_batch_20260926_1530.json"))
    repairs = {(r["ticker"], r["name"], r["year"]): r for r in batch["repairs"]}
    assert set(repairs) == set(CORRUPT), "repair/corrupt key mismatch"

    # 1. pre-write assertions on live corrupted values
    for key, vals in CORRUPT.items():
        t, name, year = key
        e = find(cos[t], name, year)
        fields = FIELDS6 if t == "HII" else FIELDS8
        live = tuple(e[f] for f in fields)
        assert live == vals, f"PRE-WRITE DRIFT {key}: {live} != {vals}"

    # 2. apply filing-verbatim values
    for key, r in repairs.items():
        t, name, year = key
        e = find(cos[t], name, year)
        f = r["filing"]
        for fld in FIELDS8:
            e[fld] = f[fld]
        e["_total_source"] = "def14a_verified_20260926"
        e["_note"] = (
            f"DQ 2026-09-26: salary-drop column-shift repair from {t} 2026 DEF 14A "
            f"(acc. {ACC[t]}). Filed SCT: " +
            (f"salary {f['salary']:,}, stock {f['stock_awards']:,}, NEIP {f['non_equity_incentive']:,}, "
             f"pension {f['pension_nqdc']:,}, all_other {f['all_other']:,}, total {f['total']:,}")
        )
        if r.get("filing_foot_gap") == -1:
            e["_note"] += " Filing-side $1 footing gap kept verbatim."

    # 3. re-anchor company aggregates
    cnp = cos["CNP"]
    cnp24 = [e["total"] for e in cnp["executives"] if e["year"] == 2024]
    assert len(cnp24) == 4, cnp24
    old = cnp["total_neo_compensation"]
    cnp["total_neo_compensation"] = sum(cnp24)
    print(f"CNP FY2024 neo comp: {old:,} -> {cnp['total_neo_compensation']:,}")

    hii = cos["HII"]
    hii24 = [e["total"] for e in hii["executives"] if e["year"] == 2024]
    assert len(hii24) == 4, hii24
    old = hii["total_neo_compensation"]
    hii["total_neo_compensation"] = sum(hii24)
    print(f"HII FY2024 neo comp: {old:,} -> {hii['total_neo_compensation']:,}")
    old = hii["total_compensation"]
    kastner = find(hii, "Christopher D. Kastner", 2024)
    hii["total_compensation"] = kastner["total"]
    print(f"HII CEO anchor total: {old:,} -> {hii['total_compensation']:,}")
    assert hii["total_compensation"] == 14553665

    # 4. post-repair footing assertions
    for key, r in repairs.items():
        t, name, year = key
        e = find(cos[t], name, year)
        comps = sum(e[f] for f in FIELDS8[:7])
        gap = comps - e["total"]
        if key == ("CNP", "Christopher A. Foster", 2024):
            assert gap == -1, f"expected $1 filing gap, got {gap}"
        else:
            assert gap == 0, f"FOOTING FAIL {key}: gap={gap}"

    with open(path, "w") as fh:
        json.dump(d, fh, indent=2)
    print("17 rows repaired, footing clean, aggregates re-anchored.")

if __name__ == "__main__":
    main()
