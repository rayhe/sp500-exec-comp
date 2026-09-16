#!/usr/bin/env python3
"""DQ batch 2026-09-15 22:00 PT: all-caps full-phrase title repair via EDGAR.

The 2026-09-15 19:30 offline screen found 41 all-caps NEO title rows in two
classes. The 33 abbreviation rows (TITLE_ALLCAPS_ABBREV) were locked as
filing-conventional and need no repair. The 8 full-phrase rows at AFL/MHK
were queued for the EDGAR title-column re-read (VM egress was down since
2026-09-12 ~16:20 PT; direct EDGAR recovered by 2026-09-15 22:00 PT).

Verified against the filed SCT title cells (fetched 2026-09-15 22:00 PT,
User-Agent Kit/1.0):

1. AFL (Aflac) DEF 14A 2026-03-19, accession 000162828026019621,
   afl-20260319.htm, Summary Compensation Table row "Bradley E. Dyslin":
   title cell as filed is Title Case, NOT all caps:
     "Executive Vice President,<br/>Global Chief<br/>Investment Officer;
      <br/>President, Aflac<br/>Global Investments"
   The stored 'EXECUTIVE VICE PRESIDENT' was a truncated + uppercased
   extraction. Repaired to the full as-filed title (2023, 2024, 2025).

2. MHK (Mohawk) DEF 14A 2026-04-03, accession 000110465926039491,
   tm261333-4_def14a.htm, "SUMMARY COMPENSATION TABLE" row
   "Paul F. De Cock": title cell as filed (Title Case):
     "President and Chief Operating Officer; Former President - Flooring
      North America"
   Repaired from 'PRESIDENT AND CHIEF OPERATING OFFICER' (2023-2025).
   Row "Mauro Vandini": title cell as filed:
     "President - Global Ceramic (4)"
   footnote (4): "On September 15, 2024, Mr. Vandini was appointed as
   President of the Company's Global Ceramic reporting segment."
   Repaired from 'PRESIDENT' (2024, 2025). Em dash stored with single
   spaces (filing uses thin-space around it; normalized to plain spaces).

Guard section 15: TITLE_ALLCAPS_FULLPHRASE_QUEUED is now EMPTY (n_full 0)
and the recount assert updated; new all-caps titles still fail hard.

All numeric fields asserted identical before/after; totals untouched, so
no company aggregates change.
"""

import json
import shutil
import sys

REPO = "/home/hatch/repos/sp500-exec-comp"
SRC = REPO + "/data/compensation.json"

DYSLIN_NEW = ("Executive Vice President, Global Chief Investment Officer; "
              "President, Aflac Global Investments")
DECOCK_NEW = ("President and Chief Operating Officer; "
              "Former President \u2014 Flooring North America")
VANDINI_NEW = "President \u2014 Global Ceramic"

EXPECTED = [
    # (ticker, name, year, old, new)
    ("AFL", "Bradley E. Dyslin", 2023, "EXECUTIVE VICE PRESIDENT", DYSLIN_NEW),
    ("AFL", "Bradley E. Dyslin", 2024, "EXECUTIVE VICE PRESIDENT", DYSLIN_NEW),
    ("AFL", "Bradley E. Dyslin", 2025, "EXECUTIVE VICE PRESIDENT", DYSLIN_NEW),
    ("MHK", "Paul F. De Cock", 2023, "PRESIDENT AND CHIEF OPERATING OFFICER",
     DECOCK_NEW),
    ("MHK", "Paul F. De Cock", 2024, "PRESIDENT AND CHIEF OPERATING OFFICER",
     DECOCK_NEW),
    ("MHK", "Paul F. De Cock", 2025, "PRESIDENT AND CHIEF OPERATING OFFICER",
     DECOCK_NEW),
    ("MHK", "Mauro Vandini", 2024, "PRESIDENT", VANDINI_NEW),
    ("MHK", "Mauro Vandini", 2025, "PRESIDENT", VANDINI_NEW),
]

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

before_rows = sum(len(c.get("executives", [])) for c in data["companies"])
before_numeric = {
    (c["ticker"], r["name"], r["year"]): (
        r.get("salary"), r.get("all_other"), r["total"],
        r.get("_total_source"))
    for c in data["companies"] for r in c.get("executives", [])
}

repaired = 0
for ticker, name, year, old, new in EXPECTED:
    matches = [
        (c, r) for c in data["companies"] if c["ticker"] == ticker
        for r in c.get("executives", [])
        if r["name"] == name and r["year"] == year
    ]
    assert len(matches) == 1, \
        f"expected 1 match for {ticker}/{name}/{year}, got {len(matches)}"
    c, r = matches[0]
    assert r["title"] == old, \
        f"{ticker}/{name}/{year}: title is {r['title']!r}, expected {old!r}"
    r["title"] = new
    repaired += 1

after_rows = sum(len(c.get("executives", [])) for c in data["companies"])
after_numeric = {
    (c["ticker"], r["name"], r["year"]): (
        r.get("salary"), r.get("all_other"), r["total"],
        r.get("_total_source"))
    for c in data["companies"] for r in c.get("executives", [])
}
assert after_rows == before_rows, "row count changed"
assert set(before_numeric) == set(after_numeric), "row key set changed"
for k in before_numeric:
    assert before_numeric[k] == after_numeric[k], f"numeric drift on {k}"

shutil.copy(SRC, SRC + ".bak_20260915_2200")
with open(SRC, "w", encoding="utf-8") as f:
    # indent=2 matches the repo's canonical compensation.json formatting;
    # a compact re-serialization would blow the diff up by 100k+ lines.
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"OK: repaired {repaired}/8 rows, {after_rows} rows total, "
      f"all numeric fields byte-identical")
sys.exit(0)
