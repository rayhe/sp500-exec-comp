#!/usr/bin/env python3
"""DQ batch 2026-09-15 18:00 PT: title-split / name-fragment repair.

Three parser-artifact classes found by a fresh offline screen (fresh_sct
regexes, no EDGAR access - VM egress still down since 2026-09-12 ~16:20 PT):

1. Heading bleed in titles (3 rows): MET Bill Pappas 2023/2024/2025 stored
   'EVP and Head of GTO 2025 Total Compensation:' - the parser captured a
   document section heading into the title cell. Mechanical strip of the
   heading fragment -> 'EVP and Head of GTO' (MetLife's EVP and Head of
   Global Technology & Operations per company bio; no other reading of the
   SCT cell is plausible).

2. Dangling trailing comma (1 row): LEN Mark Sustana 2024 stored
   'Former Vice President,' - title truncated at a comma with nothing
   after. Mechanical strip -> 'Former Vice President'. (COF's sibling case
   'General Counsel and Corporate Secretary; President, ' keeps its comma
   because the clause after 'President,' is genuinely unknown - queued for
   the EDGAR pass, not guessed.)

3. Role fragment merged into the name field (4 rows): MTD 2023/2024/2025
   stored name 'Richard Wong Head of Asia and Pacific' (title 'Chief Human
   Resources Officer'); GNRC 2025 stored name 'Raj Kanuru VP' (title
   'Executive General Counsel & Secretary'). 'Head of Asia and Pacific' /
   'VP' cannot be part of a person's name - mechanical name repair to
   'Richard Wong' / 'Raj Kanuru'. Titles kept VERBATIM: whether the fragment
   belongs to the title wording ('...and Head of Asia and Pacific',
   'Executive Vice President, General Counsel & Secretary') is queued for
   the EDGAR title-column re-read, never guessed offline.

All numeric fields asserted identical before/after; totals untouched, so no
company aggregates change. Guard section 7 gains NAME_ROLE_FRAGMENT (hard
fail on recurrence - zero remain post-repair) and NAME_TITLE_GLUE (fail on
new, warn on the 5 known FFIV/JBHT tuples queued for the EDGAR pass);
guard section 13 gains dangling-punctuation, 'Total Compensation' heading
bleed, and leading-'and' title screens with the 8 queued (ticker, title)
tuples in KNOWN_TITLE_ARTIFACTS.
"""

import json
import shutil
import sys

REPO = "/home/hatch/repos/sp500-exec-comp"
SRC = REPO + "/data/compensation.json"

EXPECTED = [
    # (ticker, name, year, field, old, new)
    ("MET", "Bill Pappas", 2023, "title",
     "EVP and Head of GTO 2025 Total Compensation:", "EVP and Head of GTO"),
    ("MET", "Bill Pappas", 2024, "title",
     "EVP and Head of GTO 2025 Total Compensation:", "EVP and Head of GTO"),
    ("MET", "Bill Pappas", 2025, "title",
     "EVP and Head of GTO 2025 Total Compensation:", "EVP and Head of GTO"),
    ("LEN", "Mark Sustana", 2024, "title",
     "Former Vice President,", "Former Vice President"),
    ("MTD", "Richard Wong Head of Asia and Pacific", 2023, "name",
     "Richard Wong Head of Asia and Pacific", "Richard Wong"),
    ("MTD", "Richard Wong Head of Asia and Pacific", 2024, "name",
     "Richard Wong Head of Asia and Pacific", "Richard Wong"),
    ("MTD", "Richard Wong Head of Asia and Pacific", 2025, "name",
     "Richard Wong Head of Asia and Pacific", "Richard Wong"),
    ("GNRC", "Raj Kanuru VP", 2025, "name",
     "Raj Kanuru VP", "Raj Kanuru"),
]

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

before_rows = sum(len(c.get("executives", [])) for c in data["companies"])
before_numeric = {
    (c["ticker"], r["name"], r["year"]): (
        r.get("salary"), r.get("all_other"), r["total"], r.get("_total_source"))
    for c in data["companies"] for r in c.get("executives", [])
}

repaired = 0
for ticker, name, year, field, old, new in EXPECTED:
    matches = [
        (c, r) for c in data["companies"] if c["ticker"] == ticker
        for r in c.get("executives", [])
        if r["name"] == name and r["year"] == year
    ]
    assert len(matches) == 1, f"expected 1 match for {ticker}/{name}/{year}, got {len(matches)}"
    c, r = matches[0]
    assert r[field] == old, f"{ticker}/{name}/{year}: {field} is {r[field]!r}, expected {old!r}"
    r[field] = new
    repaired += 1

after_rows = sum(len(c.get("executives", [])) for c in data["companies"])
after_numeric = {
    (c["ticker"], r["name"], r["year"]): (
        r.get("salary"), r.get("all_other"), r["total"], r.get("_total_source"))
    for c in data["companies"] for r in c.get("executives", [])
}
assert after_rows == before_rows, "row count changed"

# numeric identity: allow exactly the 8 repaired (name,key) renames; every
# numeric tuple must be byte-identical before/after
renamed = {
    ("MTD", "Richard Wong Head of Asia and Pacific", y): ("MTD", "Richard Wong", y)
    for y in (2023, 2024, 2025)
}
renamed[("GNRC", "Raj Kanuru VP", 2025)] = ("GNRC", "Raj Kanuru", 2025)
missing = set(before_numeric) - set(after_numeric)
assert set(renamed) == missing, f"unexpected row key changes: {missing ^ set(renamed)}"
for old_k, new_k in renamed.items():
    assert before_numeric[old_k] == after_numeric[new_k], f"numeric drift on {old_k}"
for k in set(before_numeric) & set(after_numeric):
    assert before_numeric[k] == after_numeric[k], f"numeric drift on {k}"

shutil.copy(SRC, SRC + ".bak_20260915_1800")
with open(SRC, "w", encoding="utf-8") as f:
    # indent=2 matches the repo's canonical compensation.json formatting;
    # a compact re-serialization would blow the diff up by 100k+ lines.
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"OK: repaired {repaired}/8 rows, {after_rows} rows total, all numeric fields byte-identical")
sys.exit(0)
