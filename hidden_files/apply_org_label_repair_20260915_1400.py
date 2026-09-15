"""Org-label name repair - 2026-09-15 14:00 PT batch.

Repairs the last 2 rows in the title/name-artifact queue whose NEO names were
parsed as division labels (org-label artifacts), verified via the browser path
(VM egress still dead since 2026-09-12 ~18:00 PT; EDGAR re-reads and
browser.open both impossible; browser.search live):

- UHS 2023 'Behavioral Health' / 'Executive Vice President and President of
  our' -> Matthew J. Peterson / 'Executive Vice President and President of
  our Behavioral Health Division'. The SCT name+title cells were split: the
  name cell captured the tail of the principal-position phrase and the title
  cell captured the head; concatenated they form the full phrase. The person
  is Matthew J. Peterson, verified as UHS's EVP leading the Behavioral Health
  division: SEC Form 4 (sec.gov) signed '/s/ Matthew J. Peterson' as officer;
  Becker's Behavioral Health (2023-05-19): 'Mr. Peterson joined UHS and began
  leading its behavioral health division in 2019'; the stored 2024/2025 rows
  carry the same man with title 'Executive Vice President, President of
  Behavioral Health Division'. Salary continuity $697,527 (2023) -> $725,428
  (2024), ~4% raise. Components foot the stored total exactly.
  Side finding: UHS FY2023 has 3 rows vs 4 in FY2024/2025 - Edward H. Sim's
  FY2023 row was dropped by the parser; left queued for the EDGAR re-read.
- STLD 2023 'Flat Roll Steel' / 'Group' -> Christopher A. Graham /
  'Senior Vice President, Flat Roll Steel Group'. The SCT name cell captured
  the tail of the principal-position phrase. The person is Christopher Graham,
  verified: the 2026 STLD proxy CD&A NEO list (materials.proxyvote.com)
  names 'Mr. Christopher Graham - Senior Vice President, Flat Roll Steel
  Group'; steeldynamics.com executive bio: 'Prior to that, Mr. Graham served
  as the Senior Vice President, Flat Roll Steel Group'; the stored 2025 row
  carries 'Christopher A. Graham' / 'Senior Vice President, Flat Roll Steel
  Group' verbatim. Components foot the stored total exactly.

TAP Rahul Goyal 2025 'CEO of our Company (currently' stays queued: the
parenthetical tail is still not exposed verbatim in any indexed primary
source. A _title_note_20260915_1400 is added documenting the truncation and
the verified role history (Chief Strategy Officer 2019-Sep 30, 2025;
President and CEO since Oct 1, 2025 per molsoncoors.com bio and Reuters
2025-09-22), so the row is annotated rather than silently left with a
dangling paren. No filing text invented.

2 name rows + 2 title rows repaired (title-only/name-only); all numbers
asserted unchanged before/after. Guard section 7d comment, ORG_LABEL_UNRESOLVED
tuple, KNOWN_TITLE_ARTIFACTS, section-4d fallback sync, and the js/app.js
Data Verification modal fallback are updated in the same batch.
"""

import json
import shutil

COMP = "data/compensation.json"
BACKUP = "hidden_files/compensation_backup_20260915_1400_pre_orglabel.json"

NAME_REPAIRS = {
    # (ticker, year, old_name) -> new_name
    ("UHS", 2023, "Behavioral Health"): "Matthew J. Peterson",
    ("STLD", 2023, "Flat Roll Steel"): "Christopher A. Graham",
}

TITLE_REPAIRS = {
    # (ticker, year, old_title) -> new_title
    ("UHS", 2023, "Executive Vice President and President of our"):
        "Executive Vice President and President of our Behavioral Health Division",
    ("STLD", 2023, "Group"): "Senior Vice President, Flat Roll Steel Group",
}

UHS_NAME_NOTE = (
    "org-label name repair 2026-09-15 14:00 PT: SCT name cell captured the "
    "tail of the principal-position phrase; person verified as Matthew J. "
    "Peterson (SEC Form 4 officer signature; Becker's 2023-05-19 notes he "
    "began leading UHS's behavioral health division in 2019; stored "
    "2024/2025 rows carry the same title family). Components and total "
    "($4,049,604, foots exactly) unchanged. FY2023 row count is 3 vs 4 in "
    "FY2024/2025 - Edward H. Sim's FY2023 row was dropped by the parser; "
    "queued for the EDGAR re-read."
)

STLD_NAME_NOTE = (
    "org-label name repair 2026-09-15 14:00 PT: SCT name cell captured the "
    "tail of the principal-position phrase; person verified as Christopher "
    "A. Graham (2026 STLD proxy CD&A NEO list: 'Senior Vice President, Flat "
    "Roll Steel Group'; steeldynamics.com executive bio; stored 2025 row "
    "carries the same name/title verbatim). Components and total "
    "($4,306,985, foots exactly) unchanged."
)

UHS_TITLE_NOTE = (
    "title rejoin repair 2026-09-15 14:00 PT: stored name+title fragments "
    "('Behavioral Health' / 'Executive Vice President and President of our') "
    "concatenate to the full SCT principal-position phrase; no text invented."
)

STLD_TITLE_NOTE = (
    "title rejoin repair 2026-09-15 14:00 PT: stored name+title fragments "
    "('Flat Roll Steel' / 'Group') concatenate with the rank to the full SCT "
    "principal-position wording, verbatim per the 2026 proxy NEO list and "
    "the stored 2025 row."
)

TAP_TITLE_NOTE = (
    "title-truncation note 2026-09-15 14:00 PT: SCT principal-position cell "
    "truncated mid-parenthetical at parse - stored text is 'CEO of our Company "
    "(currently' (dangling open paren, no closing); "
    "the parenthetical tail is not exposed verbatim in any indexed primary "
    "source while the EDGAR re-read is blocked (egress outage since "
    "2026-09-12) - do not guess. Verified offline: Rahul Goyal was Chief "
    "Strategy Officer of Molson Coors (2019-Sep 30, 2025) and has been "
    "President and Chief Executive Officer since Oct 1, 2025 "
    "(molsoncoors.com executive bio; Reuters 2025-09-22)."
)


def snapshot(rows):
    out = {}
    for e in rows:
        comps = {k: e.get(k) for k in
                 ("salary", "bonus", "stock_awards", "option_awards",
                  "non_equity_incentive", "pension_nqdc", "pension_change",
                  "all_other", "total")}
        out[(e["name"], e["year"])] = comps
    return out


def main():
    shutil.copy2(COMP, BACKUP)
    with open(COMP, encoding="utf-8") as f:
        data = json.load(f)
    cos = {c["ticker"]: c for c in data["companies"]}

    before = {}
    for (t, y, old_name) in NAME_REPAIRS:
        rows = [e for e in cos[t]["executives"]
                if e.get("name") == old_name and e.get("year") == y]
        assert len(rows) == 1, f"{t} {y} {old_name!r}: {len(rows)} rows"
        before[(t, y, old_name)] = snapshot(rows)

    touched = 0
    for (t, y, old_name), new_name in NAME_REPAIRS.items():
        rows = [e for e in cos[t]["executives"]
                if e.get("name") == old_name and e.get("year") == y]
        e = rows[0]
        snap = before[(t, y, old_name)][(old_name, y)]
        e["name"] = new_name
        note = UHS_NAME_NOTE if t == "UHS" else STLD_NAME_NOTE
        e["_name_note_20260915_1400"] = note
        touched += 1
        # numbers unchanged
        after = {k: e.get(k) for k in snap}
        assert after == snap, f"{t} {y}: numbers drifted"

    for (t, y, old_title), new_title in TITLE_REPAIRS.items():
        rows = [e for e in cos[t]["executives"]
                if e.get("title") == old_title and e.get("year") == y]
        assert len(rows) == 1, f"{t} {y} {old_title!r}: {len(rows)} rows"
        e = rows[0]
        comps = {k: e.get(k) for k in
                 ("salary", "bonus", "stock_awards", "option_awards",
                  "non_equity_incentive", "pension_nqdc", "pension_change",
                  "all_other", "total")}
        e["title"] = new_title
        e["_title_note_20260915_1400"] = UHS_TITLE_NOTE if t == "UHS" else STLD_TITLE_NOTE
        touched += 1
        after = {k: e.get(k) for k in comps}
        assert after == comps, f"{t} {y}: numbers drifted"

    # TAP: annotate the still-queued truncation, title text untouched
    tap_rows = [e for e in cos["TAP"]["executives"]
                if e.get("name") == "Rahul Goyal" and e.get("year") == 2025]
    assert len(tap_rows) == 1, f"TAP Goyal: {len(tap_rows)} rows"
    te = tap_rows[0]
    assert te["title"] == "CEO of our Company (currently", te["title"]
    snap = {k: te.get(k) for k in
            ("salary", "bonus", "stock_awards", "option_awards",
             "non_equity_incentive", "pension_nqdc", "pension_change",
             "all_other", "total")}
    te["_title_note_20260915_1400"] = TAP_TITLE_NOTE
    after = {k: te.get(k) for k in snap}
    assert after == snap, "TAP Goyal: numbers drifted"

    with open(COMP, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"repaired {touched} name/title rows + 1 TAP annotation; numbers asserted unchanged")


if __name__ == "__main__":
    main()
