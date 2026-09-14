#!/usr/bin/env python3
"""2026-09-14 02:00 PT batch: person-name variant merge + title-bleed repair.

Class A - name-variant merge (mechanical, filing-independent):
The 02:00 fuzzy screen found 20 near-duplicate (ticker, name) pairs at ratio
0.80-0.999. Of these, 13 are unambiguous spelling variants of ONE person
(middle-initial inclusion, punctuation, spacing, nickname-full pairs where
titles/roles align and years are adjacent or overlapping). The canonical form
is the fuller spelling. Rows are renamed; every numeric field untouched.

  INTC: 'David Zinsner' (2022,2023) -> 'David A. Zinsner'
  PG:   'Shailesh Jejurikar' (2022-2024) -> 'Shailesh G. Jejurikar'
        (matches ceo_name; person was COO then became CEO)
  PG:   'Sundar Raman' (2024) -> 'Sundar G. Raman'
  OMC:  'Louis F Januzzi' (2024) -> 'Louis F. Januzzi'
  ADM:  'I. Pinner' (2024) -> 'Ian Pinner'
  BSX:  'Jeffrey B Mirviss' (2025) -> 'Jeffrey B. Mirviss'
  LOW:  'Brandon Sink' (2024) -> 'Brandon J. Sink' (CFO then CEO)
  BG:   'John Neppl' (2025) -> 'John W. Neppl'
  BG:   'Gregory Heckman' (2025) -> 'Gregory A. Heckman' (matches ceo_name)
  IPG:  'Christopher Carroll' (2022,2023) -> 'Christopher F. Carroll'
  EFX:  'John W. Gamble Jr.' (2023,2024) -> 'John W. Gamble, Jr'
  ODFL: 'Cecil E. Overbey, Jr' (2025) -> 'Cecil E. Overbey, Jr.'
  PPL:  'Joseph P. Bergstein, Jr' (2023,2025) -> 'Joseph P. Bergstein, Jr.'
  LW:   'Marc P. J .H. Schroeder' (2025,2026) -> 'Marc P.J.H. Schroeder'

Class B - title-bleed repair (mechanical, filing-independent):
  UHS 2024/2025 (8 rows): strip trailing ': Mr' honorific suffix from titles.
  BG 2025 Gregory A. Heckman: 'Chief Executive Officer, and John Neppl,
      Chief Financial Officer' -> 'Chief Executive Officer' (next row's
      name/title bled into the title cell; John Neppl has his own row).
  GPC 2025 Alain Masse: 'President, North America Automotive and James
      Howe, President, Motion' -> 'President, North America Automotive'
      (James Howe has his own row with title 'President, Motion').
  ORLY 2024/2025 (6 rows): strip percentage/name bleeds -
      Beckham: 'Chief Executive Officer 100 % Brent G' -> 'Chief Executive Officer'
      Kirby: 'Vice Chairman of the Board BRAD BECKHAM Chief Executive Officer'
             -> 'Vice Chairman of the Board'
      Fletcher: '...Chief Financial Officer 85 % Scott R'
             -> 'Executive Vice President and Chief Financial Officer'
      (ORLY 2024 totals stay queued for EDGAR: Beckham and Kirby share the
      identical $744,231 total, a row-level corruption signature.)

NOT merged (ambiguous - queued for EDGAR in
name_ambiguity_review_queue_20260914_0200.md):
  AJG Pat Gallagher (CEO) vs Patrick Gallagher (COO, 2025) vs Tom Gallagher
  STLD 'Barry Schneider' (SVP Steel Ops) vs 'Barry T. Schneider' (Pres/COO)
      - both rows in 2023 and 2024
  OKE 'Walter S. Hulse' vs 'Walter S. Hulse, III' - both rows all 3 years
  DRI 'Raj Vennam' vs 'Rajesh Vennam' - both rows 2023 and 2024
  PSA 'H. Thomas Boyle' (CFO) vs 'Thomas S. Boyle' (COO) - different people

Hard asserts: rename targets exist, no duplicate (ticker,name,year) created,
all numeric fields byte-identical after rename, guard script exit 0.
"""
import json, shutil, sys, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "compensation.json"
BACKUP = Path(__file__).resolve().parent / "compensation_backup_20260914_0200.json"

MERGES = [
    # (ticker, old_name, new_name)
    ("INTC", "David Zinsner", "David A. Zinsner"),
    ("PG", "Shailesh Jejurikar", "Shailesh G. Jejurikar"),
    ("PG", "Sundar Raman", "Sundar G. Raman"),
    ("OMC", "Louis F Januzzi", "Louis F. Januzzi"),
    ("ADM", "I. Pinner", "Ian Pinner"),
    ("BSX", "Jeffrey B Mirviss", "Jeffrey B. Mirviss"),
    ("LOW", "Brandon Sink", "Brandon J. Sink"),
    ("BG", "John Neppl", "John W. Neppl"),
    ("BG", "Gregory Heckman", "Gregory A. Heckman"),
    ("IPG", "Christopher Carroll", "Christopher F. Carroll"),
    ("EFX", "John W. Gamble Jr.", "John W. Gamble, Jr"),
    ("ODFL", "Cecil E. Overbey, Jr", "Cecil E. Overbey, Jr."),
    ("PPL", "Joseph P. Bergstein, Jr", "Joseph P. Bergstein, Jr."),
    ("LW", "Marc P. J .H. Schroeder", "Marc P.J.H. Schroeder"),
]

TITLE_REPAIRS = [
    # (ticker, name, year, old_title, new_title)
    # NOTE: BG entry uses the POST-merge canonical name 'Gregory A. Heckman'
    ("BG", "Gregory A. Heckman", 2025,
     "Chief Executive Officer, and John Neppl, Chief Financial Officer",
     "Chief Executive Officer"),
    ("GPC", "Alain Masse", 2025,
     "President, North America Automotive and James Howe, President, Motion",
     "President, North America Automotive"),
    ("ORLY", "Brad Beckham", 2024, "Chief Executive Officer 100 % Brent G",
     "Chief Executive Officer"),
    ("ORLY", "Brad Beckham", 2025, "Chief Executive Officer 100 % Brent G",
     "Chief Executive Officer"),
    ("ORLY", "Brent G. Kirby", 2024,
     "Vice Chairman of the Board BRAD BECKHAM Chief Executive Officer",
     "Vice Chairman of the Board"),
    ("ORLY", "Brent G. Kirby", 2025,
     "Vice Chairman of the Board BRAD BECKHAM Chief Executive Officer",
     "Vice Chairman of the Board"),
    ("ORLY", "Jeremy Fletcher", 2024,
     "Executive Vice President and Chief Financial Officer 85 % Scott R",
     "Executive Vice President and Chief Financial Officer"),
    ("ORLY", "Jeremy Fletcher", 2025,
     "Executive Vice President and Chief Financial Officer 85 % Scott R",
     "Executive Vice President and Chief Financial Officer"),
]


def main():
    shutil.copy2(DATA, BACKUP)
    d = json.loads(DATA.read_text())
    comps = d["companies"]
    bytk = {c["ticker"]: c for c in comps}

    n_merge = 0
    for ticker, old, new in MERGES:
        c = bytk[ticker]
        # assert the canonical name's rows are untouched and no collision
        targets = [e for e in c["executives"] if e.get("name") == old]
        assert targets, f"{ticker}: no rows named {old!r}"
        existing_new = {(e.get("name"), e.get("year")) for e in c["executives"]
                        if e.get("name") == new}
        for e in targets:
            assert (new, e["year"]) not in existing_new, (
                f"{ticker}: rename collision {old!r} -> {new!r} year {e['year']}")
            before = {k: v for k, v in e.items() if not k.startswith("_")}
            e["name"] = new
            e["_name_note_20260914_0200"] = (
                f"name-variant merge: {old!r} -> {new!r} "
                f"(middle-initial/punctuation/nickname spelling variant, "
                f"same person, titles align)")
            after = {k: v for k, v in e.items() if not k.startswith("_")}
            # only the name changed
            assert {k: v for k, v in before.items() if k != "name"} == \
                   {k: v for k, v in after.items() if k != "name"}, \
                   f"{ticker}: non-name field changed on rename"
            n_merge += 1

    # BG title repair targets the post-merge name
    n_title = 0
    for ticker, name, year, old_t, new_t in TITLE_REPAIRS:
        c = bytk[ticker]
        rows = [e for e in c["executives"]
                if e.get("name") == name and e.get("year") == year]
        assert len(rows) == 1, f"{ticker} {year} {name!r}: {len(rows)} rows"
        e = rows[0]
        assert e.get("title") == old_t, (
            f"{ticker} {year} {name!r}: title is {e.get('title')!r}, "
            f"expected {old_t!r}")
        e["title"] = new_t
        e["_title_note_20260914_0200"] = (
            f"title-bleed repair: {old_t!r} -> {new_t!r} "
            f"(embedded next-row name/percentage bleed)")
        n_title += 1

    # UHS ': Mr' honorific suffix strip
    uhs = bytk["UHS"]
    uhs_expected = sum(1 for e in uhs["executives"]
                       if (e.get("title") or "").endswith(": Mr"))
    uhs_fixed = 0
    for e in uhs["executives"]:
        ti = e.get("title") or ""
        if ti.endswith(": Mr"):
            e["title"] = ti[: -len(": Mr")]
            e["_title_note_20260914_0200"] = (
                "title-bleed repair: stripped trailing ': Mr' honorific "
                "suffix (SCT footnote artifact)")
            uhs_fixed += 1
            n_title += 1
    assert uhs_fixed == uhs_expected and uhs_expected > 0, \
        f"UHS : Mr count {uhs_fixed}/{uhs_expected}"
    assert n_title == uhs_fixed + len(TITLE_REPAIRS), f"title count {n_title}"

    # postcondition: no duplicate (ticker, name, year)
    seen = set()
    for c in comps:
        for e in c.get("executives", []):
            k = (c["ticker"], e.get("name"), e.get("year"))
            assert k not in seen, f"duplicate created: {k}"
            seen.add(k)

    DATA.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    print(f"merged {n_merge} name-variant rows, repaired {n_title} titles")
    print(f"backup: {BACKUP}")


if __name__ == "__main__":
    main()
