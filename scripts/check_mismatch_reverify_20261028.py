#!/usr/bin/env python3
"""Regression guard: the 10 queued component_mismatch rows stay filing-verbatim.

The 2026-10-28 10:00 PT run (256th review) closed the queued candidate
from the 255th run: the ten FRT/MOS/NEE/RF/XYZ component_mismatch rows
were re-read against their primary 2026 DEF 14A SCTs (not relabeled on
stored arithmetic alone). Every row is filing-verbatim and every gap is
filing-side, so the component_mismatch labels were RETAINED:
  FRT Wood 2025 / Guglielmone 2024+2023 / Becker 2024: $1 gaps
    (e.g. Wood 1,000,000 + 7,554,434 + 1,350,000 + 24,712 = 9,929,146
     vs printed total 9,929,147, d33770ddef14a.htm).
  NEE Crews 2023: $1 gap (4,418,557 vs 4,418,556, tm261592-1_def14a.htm).
  XYZ Grassadonia 2025 / Weber 2025: $1 gaps (sq-20260423.htm).
  MOS Swager 2024: filing printed total 2,588,145 omits all-other
    229,482; components sum to 2,817,627 (mos-20260415.htm).
  RF Turner 2023: SCT columns sum to 9,222,778 vs printed 9,217,718
    (gap 5,060); Keenan 2023: 2,702,752 vs 2,701,572 (gap 1,180)
    (rf-20260323.htm; stored all-other values follow the SCT
    footnote breakdowns, per the records' own notes).
The same run re-checked VMRK on EDGAR (CIK 906107): still no
post-merger Vivmark DEF 14A; latest DEF 14A remains the 2026-04-14
pre-merger EQR proxy, acc. 0001193125-26-155007.

Checks (all static):
  S1 all 10 rows carry a _reverify_20261028 note.
  S2 VMRK _index_note carries the 2026-10-28 recheck stamp.
  S3 dataset counts unchanged: 518 companies, 7,097 NEO rows,
     component_mismatch 33, verified_total 7064.
     (Baseline moved 2026-10-29, 270th review: MSFT FY2026 proxy batch
      added 5 verified NEO rows; 7079->7084, 7047->7052. Baseline moved
      2026-10-29, 271st review: CSCO + ORCL FY2026 proxy batch added
      12 verified NEO rows (4 CSCO + 8 ORCL) and 1 component_mismatch
      row (CSCO Subaiya 2026, $1 filing-side gap kept verbatim);
      7084->7097, 7052->7064, mismatch 32->33.)

Usage:
  scripts/check_mismatch_reverify_20261028.py
  scripts/check_mismatch_reverify_20261028.py --static-only

Exit: 0 = all checks pass; 1 = a check failed.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    d = json.load(open(DATA, encoding="utf-8"))
    by_ticker = {c["ticker"]: c for c in d["companies"]}

    wanted = [
        ("MOS", "Karen A. Swager", 2024),
        ("RF", "John M. Turner, Jr", 2023),
        ("RF", "David R. Keenan", 2023),
        ("FRT", "Donald C. Wood", 2025),
        ("FRT", "Daniel Guglielmone", 2024),
        ("FRT", "Daniel Guglielmone", 2023),
        ("FRT", "Dawn M. Becker", 2024),
        ("NEE", "Terrell Kirk Crews II", 2023),
        ("XYZ", "Brian Grassadonia", 2025),
        ("XYZ", "Arnaud Weber", 2025),
    ]
    missing = []
    for tick, name, year in wanted:
        recs = [e for e in by_ticker[tick].get("executives", [])
                if e.get("name") == name and e.get("year") == year]
        if len(recs) != 1 or "_reverify_20261028" not in recs[0]:
            missing.append("%s %s %d" % (tick, name, year))
    check("S1 all 10 queued rows carry _reverify_20261028",
          not missing, "" if not missing else "missing: " + ", ".join(missing))

    vmrk = by_ticker["VMRK"]
    s2 = "Re-checked 2026-10-28" in vmrk.get("_index_note", "")
    check("S2 VMRK _index_note carries the 2026-10-28 recheck stamp",
          s2, "" if s2 else "VMRK recheck stamp missing")

    total = sum(len(c.get("executives", [])) for c in d["companies"])
    mismatch = sum(1 for c in d["companies"] for e in c.get("executives", [])
                   if e.get("_total_source") == "component_mismatch")
    # S3 baseline moved 2026-10-29 (270th review): MSFT FY2026 proxy batch
    # added 5 verified NEO rows -> 7079->7084 rows, verified_total 7047->7052.
    # S3 baseline moved 2026-10-29 (271st review): CSCO + ORCL FY2026 proxy
    # batch added 12 verified + 1 mismatch rows -> 7084->7097 rows,
    # verified_total 7052->7064, mismatch 32->33.
    s3 = (len(d["companies"]) == 518 and total == 7097 and mismatch == 33
          and d["metadata"]["data_quality"]["verified_total"] == 7064)
    check("S3 counts unchanged (518 / 7097 / mismatch 33 / verified 7064)",
          s3, "" if s3 else "counts drifted: %d companies, %d rows, %d mismatch"
          % (len(d["companies"]), total, mismatch))


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
