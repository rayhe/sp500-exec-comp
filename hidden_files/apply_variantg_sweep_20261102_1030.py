#!/usr/bin/env python3
"""316th review (2026-11-02 10:30 PT): variant-G sweep repairs + VRTX Tatsis 2024.

Variant-G sweep: the 313th review identified variant G (salary-drop left-shift
with the filing Total filed into all_other, total recomputed) but its tier-1
detector gate (option_awards == 0) is blind to variant-G rows whose filing
NEIP > 0 parks in option_awards. This run swept the dataset via the
total-footing identity: implied filing salary = 2*all_other - total, gated on
all_other/total in [0.50, 0.67], implied round to $1k in [$200k, $4M], exact
footing, not dated-verified. 11 candidates -> 3 companies arbitrated against
primary DEF 14A SCTs (EDGAR, declared UA); all CONFIRMED.

SBAC (7 rows, whole-company): the 2025 DEF 14A SCT (acc. 0001193125-25-074669)
has 5 data columns -- Salary | Stock Awards | NEIP | All Other | Total (no
Bonus, no Option Awards, no pension column). The legacy parse dropped the
Salary cell and shifted Stock->salary, NEIP->stock_awards, All Other->
non_equity_incentive, filing Total->all_other, recomputing the total
(variant G, 5-column form). Implied salary (= 2*all_other - total) equals the
filing salary EXACTLY on all 7 rows (e.g. Cavanagh 920,000; Ciarfella 480,000).
The 2025 rows (from the 2026 proxy, acc. 0001193125-26-149656) and Cavanagh
2023 were already filing-verbatim -- byte-equal, no changes. Cross-checked
against the 2026 proxy SCT (identical 2024/2023 values, no restatement).

JBL (7 rows, whole-company): the 2024 DEF 14A SCT (acc. 0001193125-24-277123)
and 2025 DEF 14A SCT (acc. 0001193125-25-316927) both have 6 data columns --
Salary | Stock Awards | NEIP | All Other | Total (no Bonus/Option/pension).
Same variant-G 6-column form. The roundness gate ($1k) caught Mondello 2023,
Borges 2023/2024; full-SCT arbitration caught the 4 non-round-salary siblings
(Mondello 2024 salary $1,049,039, Dastoor 2024 $877,692, Dastoor 2023 $716,923,
Hebard 2024 $480,673) the sweep could not see -- the stated full-SCT standard
(313th/314th reviews) pays off again. CD&A base-salary table independently
confirms Mondello FY23 $1,255,000 / Borges FY23-24 $720,000. All 5 FY2025 rows
(Mondello/Dastoor/Hebard/Borges/Priestley) byte-equal to the 2025 proxy SCT,
no changes.

FDX (1 row): the 2024 DEF 14A SCT (acc. 0001308179-24-000696) has the full 8
data columns. Subramaniam 2023 is variant G, 8-column form, all-other-retained
sub-flavor: salary cell dropped, bonus->salary, stock->bonus, option->stock,
NEIP->option_awards, pension->non_equity_incentive, filing All Other
($1,527,904)->pension_nqdc, filing Total ($13,249,823)->all_other, total
recomputed (differs from the Citi 313th form where the genuine All Other cell
was dropped and pension went to 0). Implied salary = 1,300,000 exactly.
Subramaniam 2024 / Dietrich 2024 / Krishnasamy 2024 byte-equal, no changes.

VRTX: Nia Tatsis 2024 SCT row ($691,154 / -- / $5,250,328 / $1,341,900 /
$50,934 / $7,334,316; title "EVP Chief Regulatory and Quality Officer") was
absent from the dataset -- queued by the 314th review, restored here
filing-verbatim from the 2026 DEF 14A SCT (acc. 0000875320-26-000153),
appended at the END of the VRTX executives list per convention.

Phantom: 15 repairs remove $74,065,637 parser-invented compensation
(SBAC $23,270,457 + JBL $38,845,357 + FDX $11,949,823); Tatsis 2024 restores
$7,334,316 genuine. Net delta +$66,731,321.

Company aggregates untouched (all anchor fiscal years intact; anchor rows
byte-equal). Titles/_total_source untouched ('verified' kept per the
313th/314th convention).

Conventions: old-value guards on every repaired field; exact-footing
assertions; backup before write; compensation.json round-trips with
ensure_ascii=False, indent=1, trailing newline; __main__ honored.
"""

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import phantom_record

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(REPO, "data",
                      "compensation_backup_20261102_1030_pre_variantg.json")
STAMP = "2026-11-02 10:30 PT"

SBAC_ACC = "0001193125-25-074669"
SBAC_URL = ("https://www.sec.gov/Archives/edgar/data/1034054/"
            "000119312525074669/d860468ddef14a.htm")
JBL24_ACC = "0001193125-24-277123"   # FY2023 rows
JBL24_URL = ("https://www.sec.gov/Archives/edgar/data/898293/"
             "000119312524277123/d67416ddef14a.htm")
JBL25_ACC = "0001193125-25-316927"   # FY2024 rows
JBL25_URL = ("https://www.sec.gov/Archives/edgar/data/898293/"
             "000119312525316927/d946966ddef14a.htm")
FDX_ACC = "0001308179-24-000696"
FDX_URL = ("https://www.sec.gov/Archives/edgar/data/1048911/"
           "000130817924000696/fdx4341161-def14a.htm")
VRTX_ACC = "0000875320-26-000153"
VRTX_URL = ("https://www.sec.gov/Archives/edgar/data/875320/"
            "000087532026000153/vrtx-20260402.htm")

SBAC_NOTE = (
    f"{STAMP} (316th review): 2025 DEF 14A SCT (acc. {SBAC_ACC}) has 5 data "
    "columns (Salary | Stock Awards | NEIP | All Other | Total; no Bonus, no "
    "Option Awards, no pension). Legacy parse dropped the Salary cell: "
    "Stock->salary, NEIP->stock_awards, All Other->non_equity_incentive, "
    "filing Total->all_other, total recomputed (variant G, 5-column form). "
    "Implied salary (2*all_other - total) equals the filing salary exactly. "
    "Repaired filing-verbatim."
)
JBL_NOTE_TMPL = (
    "{stamp} (316th review): {proxy} DEF 14A SCT (acc. {acc}) has 6 data "
    "columns (Salary | Stock Awards | NEIP | All Other | Total; no Bonus, no "
    "Option Awards, no pension). Legacy parse dropped the Salary cell: "
    "Stock->salary, NEIP->stock_awards, All Other->non_equity_incentive, "
    "filing Total->all_other, total recomputed (variant G, 6-column form). "
    "Repaired filing-verbatim."
)
FDX_NOTE = (
    f"{STAMP} (316th review): 2024 DEF 14A SCT (acc. {FDX_ACC}) has the full "
    "8 data columns. Legacy parse dropped the Salary cell: bonus->salary, "
    "stock->bonus, option->stock, NEIP->option_awards, pension->"
    "non_equity_incentive, filing All Other ($1,527,904)->pension_nqdc, "
    "filing Total ($13,249,823)->all_other, total recomputed (variant G, "
    "8-column form, all-other-retained sub-flavor -- differs from the Citi "
    "313th form where the genuine All Other cell was dropped). Repaired "
    "filing-verbatim."
)
VRTX_NOTE = (
    f"{STAMP} (316th review): Nia Tatsis 2024 SCT row was absent from the "
    f"dataset (queued by the 314th review). Restored filing-verbatim from "
    f"the 2026 DEF 14A SCT (acc. {VRTX_ACC})."
)

# (name, year, old(sal,bon,stk,opt,neip,pen,ao,tot), new(sal,bon,stk,opt,neip,pen,ao,tot), acc, url, note)
REPAIRS = [
    # ---- SBAC (2025 proxy) ----
    ("SBAC", "Brendan T. Cavanagh", 2024,
     (6589999, 0, 1284435, 0, 23068, 0, 8817502, 16715004),
     (920000, 0, 6589999, 0, 1284435, 0, 23068, 8817502),
     SBAC_ACC, SBAC_URL, SBAC_NOTE),
    ("SBAC", "Marc Montagner", 2024,
     (2744457, 0, 579840, 0, 18225, 0, 3982522, 7325044),
     (640000, 0, 2744457, 0, 579840, 0, 18225, 3982522),
     SBAC_ACC, SBAC_URL, SBAC_NOTE),
    ("SBAC", "Mark R. Ciarfella", 2024,
     (2107016, 0, 471120, 0, 22432, 0, 3120568, 5721136),
     (520000, 0, 2107016, 0, 471120, 0, 22432, 3120568),
     SBAC_ACC, SBAC_URL, SBAC_NOTE),
    ("SBAC", "Mark R. Ciarfella", 2023,
     (1679224, 0, 524160, 0, 20908, 0, 2704292, 4928584),
     (480000, 0, 1679224, 0, 524160, 0, 20908, 2704292),
     SBAC_ACC, SBAC_URL, SBAC_NOTE),
    ("SBAC", "Richard M. Cane", 2024,
     (2043892, 0, 474810, 0, 17452, 0, 3046154, 5582308),
     (510000, 0, 2043892, 0, 474810, 0, 17452, 3046154),
     SBAC_ACC, SBAC_URL, SBAC_NOTE),
    ("SBAC", "Richard M. Cane", 2023,
     (1629881, 0, 550840, 0, 18064, 0, 2668785, 4867570),
     (470000, 0, 1629881, 0, 550840, 0, 18064, 2668785),
     SBAC_ACC, SBAC_URL, SBAC_NOTE),
    ("SBAC", "Joshua M. Koenig", 2024,
     (1960642, 0, 487560, 0, 22432, 0, 2980634, 5451268),
     (510000, 0, 1960642, 0, 487560, 0, 22432, 2980634),
     SBAC_ACC, SBAC_URL, SBAC_NOTE),
    # ---- JBL (2023 rows: 2024 proxy; 2024 rows: 2025 proxy) ----
    ("JBL", "Mark T. Mondello", 2023,
     (11310600, 0, 3680288, 0, 355112, 0, 16601000, 31947000),
     (1255000, 0, 11310600, 0, 3680288, 0, 355112, 16601000),
     JBL24_ACC, JBL24_URL,
     JBL_NOTE_TMPL.format(stamp=STAMP, proxy="2024", acc=JBL24_ACC)),
    ("JBL", "Steven D. Borges", 2023,
     (2092755, 0, 1407600, 0, 82814, 0, 4303169, 7886338),
     (720000, 0, 2092755, 0, 1407600, 0, 82814, 4303169),
     JBL24_ACC, JBL24_URL,
     JBL_NOTE_TMPL.format(stamp=STAMP, proxy="2024", acc=JBL24_ACC)),
    ("JBL", "Mark T. Mondello", 2024,
     (4686056, 0, 2132171, 0, 365193, 0, 8232459, 15415879),
     (1049039, 0, 4686056, 0, 2132171, 0, 365193, 8232459),
     JBL25_ACC, JBL25_URL,
     JBL_NOTE_TMPL.format(stamp=STAMP, proxy="2025", acc=JBL25_ACC)),
    ("JBL", "Michael Dastoor", 2024,
     (2519385, 0, 1769524, 0, 82681, 0, 5249282, 9620872),
     (877692, 0, 2519385, 0, 1769524, 0, 82681, 5249282),
     JBL25_ACC, JBL25_URL,
     JBL_NOTE_TMPL.format(stamp=STAMP, proxy="2025", acc=JBL25_ACC)),
    ("JBL", "Michael Dastoor", 2023,
     (2323707, 0, 1681901, 0, 99783, 0, 4822314, 8927705),
     (716923, 0, 2323707, 0, 1681901, 0, 99783, 4822314),
     JBL24_ACC, JBL24_URL,
     JBL_NOTE_TMPL.format(stamp=STAMP, proxy="2024", acc=JBL24_ACC)),
    ("JBL", "Greg Hebard", 2024,
     (423656, 0, 585649, 0, 27250, 0, 1517228, 2553783),
     (480673, 0, 423656, 0, 585649, 0, 27250, 1517228),
     JBL25_ACC, JBL25_URL,
     JBL_NOTE_TMPL.format(stamp=STAMP, proxy="2025", acc=JBL25_ACC)),
    ("JBL", "Steven D. Borges", 2024,
     (2166671, 0, 975600, 0, 76961, 0, 3939232, 7158464),
     (720000, 0, 2166671, 0, 975600, 0, 76961, 3939232),
     JBL25_ACC, JBL25_URL,
     JBL_NOTE_TMPL.format(stamp=STAMP, proxy="2025", acc=JBL25_ACC)),
    # ---- FDX (2024 proxy) ----
    ("FDX", "Rajesh Subramaniam", 2023,
     (250000, 2251294, 3712859, 3998750, 209016, 1527904, 13249823, 25199646),
     (1300000, 250000, 2251294, 3712859, 3998750, 209016, 1527904, 13249823),
     FDX_ACC, FDX_URL, FDX_NOTE),
]

FIELDS = ["salary", "bonus", "stock_awards", "option_awards",
          "non_equity_incentive", "pension_nqdc", "all_other", "total"]


def foot(row):
    g = lambda k: row.get(k) if isinstance(row.get(k), (int, float)) else 0
    return (g("salary") + g("bonus") + g("stock_awards") + g("option_awards")
            + g("non_equity_incentive") + g("pension_nqdc") + g("all_other"))


def main():
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    by_ticker = {c["ticker"]: c for c in d["companies"]}

    def find_row(ticker, name, year):
        c = by_ticker[ticker]
        hits = [e for e in c["executives"]
                if e["name"] == name and e["year"] == year]
        assert len(hits) == 1, f"{ticker} {name} {year}: {len(hits)} hits"
        return c, hits[0]

    # ---- variant-G repairs (total-changing) ----
    for ticker, name, year, old, new, acc, url, note in REPAIRS:
        c, e = find_row(ticker, name, year)
        for f, o in zip(FIELDS, old):
            got = e.get(f) or 0
            assert got == o, (ticker, name, year, f, got, o)
        for f, n in zip(FIELDS, new):
            e[f] = n
        e["_accession"] = acc
        e["_filing_url"] = url
        e["_repair_note_20261102_1030"] = note
        assert foot(e) == e["total"], (ticker, name, year, "footing")

    # ---- VRTX Tatsis 2024: missing-row restoration (appended at END) ----
    vc = by_ticker["VRTX"]
    assert not [e for e in vc["executives"]
                if e["name"] == "Nia Tatsis" and e["year"] == 2024], \
        "Tatsis 2024 already present"
    new_row = {
        "name": "Nia Tatsis",
        "title": "Executive Vice President, Chief Regulatory and Quality Officer",
        "year": 2024,
        "salary": 691154,
        "stock_awards": 5250328,
        "non_equity_incentive": 1341900,
        "pension_nqdc": 0,
        "all_other": 50934,
        "total": 7334316,
        "_total_source": "verified",
        "_accession": VRTX_ACC,
        "_filing_url": VRTX_URL,
        "_repair_note_20261102_1030": VRTX_NOTE,
    }
    assert foot(new_row) == new_row["total"], "Tatsis 2024 footing"
    vc["executives"].append(new_row)

    # ---- write ----
    shutil.copy2(DATA, BACKUP)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")

    delta = phantom_record.record_batch(
        pre_path=BACKUP, data_path=DATA, stamp=f"{STAMP} (316th review)")
    print(f"phantom delta: ${delta:,}")
    assert delta == 66731321, f"unexpected phantom delta {delta}"
    print("OK: 15 variant-G rows repaired (SBAC 7, JBL 7, FDX 1); "
          "VRTX Tatsis 2024 restored")


if __name__ == "__main__":
    main()
