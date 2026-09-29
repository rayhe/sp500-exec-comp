#!/usr/bin/env python3
"""DQ 2026-09-28 22:00 PT: triage the 4 un-noted significant component_mismatch rows.

The 22:00 PT tripwire scan found 34 rows labeled component_mismatch. Ten have
material gaps (>= $20K). Six of those ten already carry detailed _note fields
from prior triage (BE Kurzymski 2025, SBUX Kelly 2024, WAB Schweitzer 2023,
CDNS Cunningham 2024/2023, FDS Shan 2023), all concluding filing-side
arithmetic inconsistencies. The remaining four had no triage note, so this
batch re-read each one cell-by-cell against the primary DEF 14A SCT fetched
fresh from EDGAR (www.sec.gov reachable via the VM egress proxy; User-Agent
Kit/1.0 (factoryfactorykit@gmail.com)).

FINDING for all four: the stored components match the filing verbatim on every
cell, and the filing's own printed total does not foot. These are filer-side
arithmetic errors, NOT parse errors. No values change. Each row gets a _note
documenting the re-read (the UI's data-quality tooltip already renders _note
for component_mismatch rows), so future iterations do not re-triage.

Rows (filing doc cited per row):
1. JCI Julie Brandt 2023 (tm2524665-5_def14a.htm, filed 2026-01-16):
   salary 685,577 + bonus 750,000 + stock 2,649,934 + NEIP 221,943 +
   all_other 7,212 = 4,314,666 vs printed total 3,965,627 (gap -349,039).
2. CDNS Paul Scannell 2024 (d932644ddef14a.htm, filed 2026-03-25):
   salary 429,948 + stock 2,693,905 + options 1,384,209 + NEIP 476,473 +
   all_other 10,457 = 4,994,992 vs printed total 5,172,527 (gap +177,535).
   Sibling rows Cunningham 2024/2023 were already triaged as filing-side.
3. APH C.A. Lampo 2023 (tm261344-1_def14a.htm, filed 2026-04-08):
   salary 680,000 + options 2,981,331 + pension 2,600 + all_other 114,786
   = 3,778,717 vs printed total 3,715,717 (gap -63,000). All other APH SCT
   rows foot exactly; only this row is off.
4. NEE Charles E. Sieving 2023 (tm261592-1_def14a.htm, filed 2026-04-01):
   salary 1,274,300 + stock 2,665,736 + options 509,894 + NEIP 1,641,300 +
   pension 423,332 + all_other 207,615 = 6,722,177 vs printed total
   6,772,178 (gap +50,001).

No anchor changes: company-level total_compensation / total_neo_compensation
are keyed to filing-printed totals, which are unchanged. The 24 remaining
component_mismatch rows are rounding-level (|gap| <= $4,000, mostly <= $300)
and keep the default tooltip.
"""
import json
import shutil
import os

COMP_FILE = "/home/hatch/repos/sp500-exec-comp/data/compensation.json"

NOTES = {
    ("JCI", "Julie Brandt", 2023):
        "Re-read 2026-09-28 vs primary DEF 14A SCT (tm2524665-5_def14a.htm): "
        "stored components match the filing verbatim (salary 685,577 + bonus "
        "750,000 + stock 2,649,934 + NEIP 221,943 + all other 7,212 = "
        "4,314,666) vs filing-printed total 3,965,627 (gap -349,039). "
        "Filer-side arithmetic inconsistency, not a parse error; retained verbatim.",
    ("CDNS", "Paul Scannell", 2024):
        "Re-read 2026-09-28 vs primary DEF 14A SCT (d932644ddef14a.htm): "
        "stored components match the filing verbatim (salary 429,948 + stock "
        "2,693,905 + options 1,384,209 + NEIP 476,473 + all other 10,457 = "
        "4,994,992) vs filing-printed total 5,172,527 (gap +177,535). "
        "Filer-side arithmetic inconsistency, not a parse error; retained verbatim. "
        "Sibling Cunningham 2024/2023 rows triaged identically.",
    ("APH", "C.A. Lampo", 2023):
        "Re-read 2026-09-28 vs primary DEF 14A SCT (tm261344-1_def14a.htm): "
        "stored components match the filing verbatim (salary 680,000 + options "
        "2,981,331 + pension 2,600 + all other 114,786 = 3,778,717) vs "
        "filing-printed total 3,715,717 (gap -63,000). All other APH SCT rows "
        "foot exactly. Filer-side arithmetic inconsistency, not a parse error; "
        "retained verbatim.",
    ("NEE", "Charles E. Sieving", 2023):
        "Re-read 2026-09-28 vs primary DEF 14A SCT (tm261592-1_def14a.htm): "
        "stored components match the filing verbatim (salary 1,274,300 + stock "
        "2,665,736 + options 509,894 + NEIP 1,641,300 + pension 423,332 + "
        "all other 207,615 = 6,722,177) vs filing-printed total 6,772,178 "
        "(gap +50,001). Filer-side arithmetic inconsistency, not a parse "
        "error; retained verbatim.",
}

COMP_KEYS = ["salary", "bonus", "stock_awards", "option_awards",
             "non_equity_incentive", "pension_nqdc", "all_other"]

def main():
    ts = "20260928_2200"
    bak = COMP_FILE.replace("compensation.json",
                            f"compensation_backup_{ts}_pre_dqbatch.json")
    shutil.copy2(COMP_FILE, bak)
    print("backup:", bak)

    d = json.load(open(COMP_FILE))
    cos = d if isinstance(d, list) else d.get("companies", d.get("data", []))
    applied = 0
    for c in cos:
        for e in (c.get("executives") or []):
            key = (c["ticker"], e.get("name"), e.get("year"))
            if key in NOTES and e.get("_total_source") == "component_mismatch":
                # safety: re-assert the stored components still match the note's claim
                s = sum((e.get(k) or 0) for k in COMP_KEYS)
                t = e.get("total") or 0
                assert abs(s - t) > 2, f"gap closed for {key}, aborting note write"
                if not e.get("_note"):
                    e["_note"] = NOTES[key]
                    applied += 1
                    print(f"noted {key[0]} {key[1]} {key[2]}: total={t} compsum={s} gap={t-s:+d}")
    json.dump(d, open(COMP_FILE, "w"), indent=1)
    print(f"applied {applied} _note fields")
    assert applied == 4, f"expected 4, got {applied}"

if __name__ == "__main__":
    main()
