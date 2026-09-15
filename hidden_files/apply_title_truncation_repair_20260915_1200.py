"""Title mid-phrase-truncation repair - 2026-09-15 12:00 PT batch.

Repairs the remaining title-truncation artifacts whose exact SCT principal-
position wording is confirmed verbatim in primary proxy filings, read via the
browser path (VM egress still dead since 2026-09-12 ~18:00 PT, EDGAR re-reads
and browser.open both impossible; browser.search live):

- ALLE John H. Stone x3 'President and Chief Executive Officer of A' ->
  'President and CEO': 2026 annual proxy SCT prints 'President and CEO';
  stored totals 9,155,073 / 8,458,360 / 8,997,445 match the filing verbatim.
- DPZ Russell J. Weiner x3 'CEO of D' -> 'Chief Executive Officer': 2026
  proxy SCT prints 'Chief Executive Officer'; stored totals 10,696,081 /
  8,944,625 / 10,135,862 match. The June 2026 retirement announcement
  (effective Oct 1, 2026) does not alter the FY2023-2025 SCT title.
- VST James A. Burke x3 'President and Chief Executive Officer of V' ->
  'President and Chief Executive Officer': 2026 DEF 14A SCT prints the
  title cell verbatim, spanning the 2025/2024/2023 rows; stored totals
  15,989,188 / 12,236,044 / 10,453,376 match.
- STLD Mark D. Millett x3 'Chair of the Board During' -> 'Chairman and
  Chief Executive Officer': 2026 DEF 14A SCT prints 'Chairman and Chief
  Executive Officer' spanning 2025/2024/2023; stored totals 12,059,908 /
  11,782,886 / 11,823,662 match. The 2025 DEF 14A SCT prints the same
  wording for its 2024/2023 rows.

12 rows touched, title-only. Numbers asserted unchanged before/after.

Deliberately NOT repaired this batch (stay queued):
- TAP Rahul Goyal 2025 'CEO of our Company (currently': the parenthetical
  tail (likely a transition-date qualifier for the 2025-10-01 CEO
  succession) is not exposed verbatim in any indexed primary source.
  Guessing it would violate the no-fabrication rule.
- UHS 2023 'Behavioral Health' / 'Executive Vice President and President
  of our': the name is an org-label parse artifact (the row is Matthew J.
  Peterson, EVP President of Behavioral Health Division, total $4,049,604
  per the 2025 proxy), so it belongs to the name-ambiguity queue, not a
  title-only batch.
"""

import json
import shutil

COMP = "data/compensation.json"
BACKUP = "hidden_files/compensation_backup_20260915_1200_pre_titletrunc.json"

REPAIRS = {
    # (ticker, old_title) -> new_title, plus expected row count and
    # per-year totals asserted verbatim against the filing.
    ("ALLE", "President and Chief Executive Officer of A"): (
        "President and CEO",
        3,
        {2025: 9155073, 2024: 8458360, 2023: 8997445},
    ),
    ("DPZ", "CEO of D"): (
        "Chief Executive Officer",
        3,
        {2025: 10696081, 2024: 8944625, 2023: 10135862},
    ),
    ("VST", "President and Chief Executive Officer of V"): (
        "President and Chief Executive Officer",
        3,
        {2025: 15989188, 2024: 12236044, 2023: 10453376},
    ),
    ("STLD", "Chair of the Board During"): (
        "Chairman and Chief Executive Officer",
        3,
        {2025: 12059908, 2024: 11782886, 2023: 11823662},
    ),
}

shutil.copy2(COMP, BACKUP)
with open(COMP) as f:
    data = json.load(f)

touched = []
for c in data["companies"]:
    for e in c.get("executives", []):
        key = (c.get("ticker"), (e.get("title") or "").strip())
        if key in REPAIRS:
            new_title, want_n, want_totals = REPAIRS[key]
            assert e["total"] == want_totals[e["year"]], (
                f"total mismatch {c['ticker']} {e['name']} {e['year']}: "
                f"stored {e['total']} != filing {want_totals[e['year']]}"
            )
            e["title"] = new_title
            touched.append((c["ticker"], e["name"], e["year"]))

for key, (_, want_n, _) in REPAIRS.items():
    got = sum(1 for t, _, _ in touched if (t, key[1]) == key)
    assert got == want_n, f"{key}: touched {got}, expected {want_n}"
assert len(touched) == 12, f"touched {len(touched)}, expected 12"

with open(COMP, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")

print("repaired 12 title-truncation rows:")
for t in touched:
    print(" ", t)
