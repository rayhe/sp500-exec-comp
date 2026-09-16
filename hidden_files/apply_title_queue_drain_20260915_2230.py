#!/usr/bin/env python3
"""DQ batch 2026-09-15 22:00 PT (part 2): section-13 title queue drained via EDGAR.

The 2026-09-15 18:00 PT batch queued 9 title-artifact tuples (19 rows at 7
companies) for the DEF 14A title-column re-read; VM egress recovered
2026-09-15 ~22:00 PT, so all 7 filings were re-fetched and every title
cell verified against the filed SCT (User-Agent Kit/1.0). The same pass
also adjudicated 3 adjacent finds (LEN Bessette split title, COF LaPrade
name/title glue, STLD Barry Schneider phantom rows).

Repairs (29 rows, all numeric fields asserted byte-identical):

1. TAP (DEF 14A 2026-03-25, acc. 000110465926034154, tap-20260506xdef14a.htm,
   SCT "Name and Principal Position"): Rahul Goyal 2025
   'CEO of our Company (currently' -> 'President and CEO'. The stored
   fragment came from CD&A text; the SCT principal-position row reads
   "President and CEO" (Gavin D.K. Hattersley is "Former President and
   CEO").

2. COF (DEF 14A 2026-03-25, acc. 000119312526124131, d701179ddef14a.htm):
   Matthew W. Cooper 2024/2025 'General Counsel and Corporate Secretary;
   President, ' -> '...; President, Discover Integration' (NEO list +
   director bio: "General Counsel and Corporate Secretary; President,
   Discover Integration"). Frank G. LaPrade 2023/2024/2025: name 'Frank G.
   LaPrade' -> 'Frank G. LaPrade, III' (as filed), title 'III Chief
   Enterprise Services Officer and Chief of Staff to the CEO' -> 'Chief
   Enterprise Services Officer and Chief of Staff to the CEO' (suffix had
   bled into the title cell; not in any queue - found in this pass).

3. FFIV (DEF 14A 2026-01-26, acc. 000104869526000012, ffiv-20260126.htm,
   SCT): name/title cell-boundary splits rejoined as filed (abbreviated
   "Executive VP" kept verbatim per as-disclosed):
   'Cooper Werner VP'/'and Executive Chief Financial Officer' 2025 ->
   'Cooper Werner'/'Executive VP and Chief Financial Officer' (SCT total
   $3,656,085 matches stored); 'John Maddison VP'/'and Executive Chief
   Marketing Officer' 2025 -> 'John Maddison'/'Executive VP and Chief
   Marketing Officer' ($5,295,456 matches); 'Frank PelzerFormer VP'/'and
   Executive Chief Financial Officer' 2023-2025 -> 'Frank Pelzer'/
   'Former Executive VP and Chief Financial Officer' ($2,925,351 matches).

4. JBHT (DEF 14A 2026-03-11, acc. 000143774926007732,
   jbht20260304_def14a.htm, SCT): 'Brad DelcoCFO'/'and EVP' 2025 ->
   'Brad Delco'/'CFO and EVP'; 'John KuhlowCFO, CAO'/'and EVP (partial
   year); CAO' 2023-2025 -> 'John Kuhlow'/'CFO, CAO, and EVP (partial
   year); CAO' (odd doubling of CAO is exactly as filed).

5. PNC (DEF 14A 2026-03-11, acc. 000119312526102189, d62941ddef14a.htm,
   NEO principal-position list): Robert Q. Reilly 2023-2025 'and CFO' ->
   'Executive Vice President and Chief Financial Officer'.

6. EXPE (DEF 14A 2026-04-29, acc. 000132442426000022, expe-20260429.htm,
   SCT title cell + NEO bio list agree): Robert Dzielak 2023-2025 'and
   Secretary' -> 'Chief Legal & People Officer, and Secretary'.

7. LEN (DEF 14A 2026-02-26, acc. 000119312526073504, d940888ddef14a.htm):
   the SCT title cells are split across the year rows IN THE FILING
   ITSELF (Jaffe: "Former Co-Chief Executive Officer" / "and President";
   Bessette: "Vice President and Chief Financial" / "Officer"). Repaired
   to the full as-filed titles: Jonathan M. Jaffe 2023/2024/2025 ->
   'Former Co-Chief Executive Officer and President' (FY2025 NEO list
   agrees; fn 5: retired as Co-Chief Executive Officer and President
   2025-12-31); Diane Bessette 2023/2024/2025 -> 'Vice President and
   Chief Financial Officer' (FY2025 NEO list agrees). The Bessette rows
   were not in any queue - found in this pass.

8. STLD (section-14 name-ambiguity pair RESOLVED): the stored 'Barry
   Schneider' 2023/2024 'SVP, Steel Operations' rows ($4,442,991 /
   $4,573,375) are Glenn A. Pushis's 2025-DEF-14A SCT rows (acc.
   0001558370-25-002901, SCT totals match to the dollar: Pushis 2023
   $4,442,991 salary $640,000, 2024 $4,573,375 salary $670,000) with a
   mangled name and an invented title ('SVP, Steel Operations' / 'Steel
   Operations' appears nowhere as a title in either filing; the 2026
   filing's bio: "Barry T. Schneider has been our President and Chief
   Operating Officer since March 2023" - one Barry Schneider exists).
   Repaired: name -> 'Glenn A. Pushis', title -> 'Senior Vice President'
   (as filed). Components and totals byte-identical.

Guard updates: section 13 KNOWN_TITLE_ARTIFACTS drained to empty (n_art
asserted 0); section 7 KNOWN_NAME_TITLE_GLUE drained to empty (FFIV/JBHT
names repaired; new glue still fails); section 14 STLD pair comment
updated (phantom rows re-attributed, warning retired); dataq modal
titles block + live mirror re-synced (79 repaired since the 2026-09-14
screen, 0 queued).
"""

import json
import shutil
import sys

REPO = "/home/hatch/repos/sp500-exec-comp"
SRC = REPO + "/data/compensation.json"

# (ticker, old_name, year, old_title, new_name, new_title)
EXPECTED = [
    ("TAP", "Rahul Goyal", 2025,
     "CEO of our Company (currently", "Rahul Goyal", "President and CEO"),

    ("COF", "Matthew W. Cooper", 2024,
     "General Counsel and Corporate Secretary; President, ",
     "Matthew W. Cooper",
     "General Counsel and Corporate Secretary; President, Discover Integration"),
    ("COF", "Matthew W. Cooper", 2025,
     "General Counsel and Corporate Secretary; President, ",
     "Matthew W. Cooper",
     "General Counsel and Corporate Secretary; President, Discover Integration"),
    ("COF", "Frank G. LaPrade", 2023,
     "III Chief Enterprise Services Officer and Chief of Staff to the CEO",
     "Frank G. LaPrade, III",
     "Chief Enterprise Services Officer and Chief of Staff to the CEO"),
    ("COF", "Frank G. LaPrade", 2024,
     "III Chief Enterprise Services Officer and Chief of Staff to the CEO",
     "Frank G. LaPrade, III",
     "Chief Enterprise Services Officer and Chief of Staff to the CEO"),
    ("COF", "Frank G. LaPrade", 2025,
     "III Chief Enterprise Services Officer and Chief of Staff to the CEO",
     "Frank G. LaPrade, III",
     "Chief Enterprise Services Officer and Chief of Staff to the CEO"),

    ("FFIV", "Cooper Werner VP", 2025,
     "and Executive Chief Financial Officer",
     "Cooper Werner", "Executive VP and Chief Financial Officer"),
    ("FFIV", "John Maddison VP", 2025,
     "and Executive Chief Marketing Officer",
     "John Maddison", "Executive VP and Chief Marketing Officer"),
    ("FFIV", "Frank PelzerFormer VP", 2023,
     "and Executive Chief Financial Officer",
     "Frank Pelzer", "Former Executive VP and Chief Financial Officer"),
    ("FFIV", "Frank PelzerFormer VP", 2024,
     "and Executive Chief Financial Officer",
     "Frank Pelzer", "Former Executive VP and Chief Financial Officer"),
    ("FFIV", "Frank PelzerFormer VP", 2025,
     "and Executive Chief Financial Officer",
     "Frank Pelzer", "Former Executive VP and Chief Financial Officer"),

    ("JBHT", "Brad DelcoCFO", 2025,
     "and EVP", "Brad Delco", "CFO and EVP"),
    ("JBHT", "John KuhlowCFO, CAO", 2023,
     "and EVP (partial year); CAO",
     "John Kuhlow", "CFO, CAO, and EVP (partial year); CAO"),
    ("JBHT", "John KuhlowCFO, CAO", 2024,
     "and EVP (partial year); CAO",
     "John Kuhlow", "CFO, CAO, and EVP (partial year); CAO"),
    ("JBHT", "John KuhlowCFO, CAO", 2025,
     "and EVP (partial year); CAO",
     "John Kuhlow", "CFO, CAO, and EVP (partial year); CAO"),

    ("PNC", "Robert Q. Reilly", 2023,
     "and CFO", "Robert Q. Reilly",
     "Executive Vice President and Chief Financial Officer"),
    ("PNC", "Robert Q. Reilly", 2024,
     "and CFO", "Robert Q. Reilly",
     "Executive Vice President and Chief Financial Officer"),
    ("PNC", "Robert Q. Reilly", 2025,
     "and CFO", "Robert Q. Reilly",
     "Executive Vice President and Chief Financial Officer"),

    ("EXPE", "Robert Dzielak", 2023,
     "and Secretary", "Robert Dzielak",
     "Chief Legal & People Officer, and Secretary"),
    ("EXPE", "Robert Dzielak", 2024,
     "and Secretary", "Robert Dzielak",
     "Chief Legal & People Officer, and Secretary"),
    ("EXPE", "Robert Dzielak", 2025,
     "and Secretary", "Robert Dzielak",
     "Chief Legal & People Officer, and Secretary"),

    ("LEN", "Jonathan M. Jaffe", 2023,
     "and President", "Jonathan M. Jaffe",
     "Former Co-Chief Executive Officer and President"),
    ("LEN", "Jonathan M. Jaffe", 2024,
     "Former Co-Chief Executive Officer", "Jonathan M. Jaffe",
     "Former Co-Chief Executive Officer and President"),
    ("LEN", "Jonathan M. Jaffe", 2025,
     "President", "Jonathan M. Jaffe",
     "Former Co-Chief Executive Officer and President"),
    ("LEN", "Diane Bessette", 2023,
     "Officer", "Diane Bessette",
     "Vice President and Chief Financial Officer"),
    ("LEN", "Diane Bessette", 2024,
     "Vice President and Chief Financial", "Diane Bessette",
     "Vice President and Chief Financial Officer"),
    ("LEN", "Diane Bessette", 2025,
     "Chief Financial Officer", "Diane Bessette",
     "Vice President and Chief Financial Officer"),

    ("STLD", "Barry Schneider", 2023,
     "SVP, Steel Operations", "Glenn A. Pushis", "Senior Vice President"),
    ("STLD", "Barry Schneider", 2024,
     "SVP, Steel Operations", "Glenn A. Pushis", "Senior Vice President"),
]

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

before_rows = sum(len(c.get("executives", [])) for c in data["companies"])
before_numeric = {
    (c["ticker"], r["name"], r["year"]): tuple(sorted(
        (k, v) for k, v in r.items() if k not in ("name", "title")))
    for c in data["companies"] for r in c.get("executives", [])
}

repaired = 0
for ticker, old_name, year, old_title, new_name, new_title in EXPECTED:
    matches = [
        (c, r) for c in data["companies"] if c["ticker"] == ticker
        for r in c.get("executives", [])
        if r["name"] == old_name and r["year"] == year
    ]
    assert len(matches) == 1, \
        f"expected 1 match for {ticker}/{old_name}/{year}, got {len(matches)}"
    c, r = matches[0]
    assert r["title"] == old_title, \
        f"{ticker}/{old_name}/{year}: title is {r['title']!r}, expected {old_title!r}"
    r["name"] = new_name
    r["title"] = new_title
    repaired += 1

after_rows = sum(len(c.get("executives", [])) for c in data["companies"])
after_numeric = {
    (c["ticker"], r["name"], r["year"]): tuple(sorted(
        (k, v) for k, v in r.items() if k not in ("name", "title")))
    for c in data["companies"] for r in c.get("executives", [])
}
assert after_rows == before_rows, "row count changed"

# renamed keys: only the name/title repairs may move keys
renamed = {
    ("COF", "Frank G. LaPrade", y): ("COF", "Frank G. LaPrade, III", y)
    for y in (2023, 2024, 2025)
}
renamed.update({
    ("FFIV", "Cooper Werner VP", 2025): ("FFIV", "Cooper Werner", 2025),
    ("FFIV", "John Maddison VP", 2025): ("FFIV", "John Maddison", 2025),
    ("FFIV", "Frank PelzerFormer VP", 2023): ("FFIV", "Frank Pelzer", 2023),
    ("FFIV", "Frank PelzerFormer VP", 2024): ("FFIV", "Frank Pelzer", 2024),
    ("FFIV", "Frank PelzerFormer VP", 2025): ("FFIV", "Frank Pelzer", 2025),
    ("JBHT", "Brad DelcoCFO", 2025): ("JBHT", "Brad Delco", 2025),
    ("JBHT", "John KuhlowCFO, CAO", 2023): ("JBHT", "John Kuhlow", 2023),
    ("JBHT", "John KuhlowCFO, CAO", 2024): ("JBHT", "John Kuhlow", 2024),
    ("JBHT", "John KuhlowCFO, CAO", 2025): ("JBHT", "John Kuhlow", 2025),
    ("STLD", "Barry Schneider", 2023): ("STLD", "Glenn A. Pushis", 2023),
    ("STLD", "Barry Schneider", 2024): ("STLD", "Glenn A. Pushis", 2024),
})
missing = set(before_numeric) - set(after_numeric)
assert set(renamed) == missing, f"unexpected row key changes: {missing ^ set(renamed)}"
for old_k, new_k in renamed.items():
    assert before_numeric[old_k] == after_numeric[new_k], \
        f"numeric drift on renamed {old_k}"
for k in set(before_numeric) & set(after_numeric):
    assert before_numeric[k] == after_numeric[k], f"numeric drift on {k}"

shutil.copy(SRC, SRC + ".bak_20260915_2230")
with open(SRC, "w", encoding="utf-8") as f:
    # indent=2 matches the repo's canonical compensation.json formatting;
    # a compact re-serialization would blow the diff up by 100k+ lines.
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"OK: repaired {repaired}/{len(EXPECTED)} rows, {after_rows} rows total, "
      f"all numeric fields byte-identical")
sys.exit(0)
