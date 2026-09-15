"""Title bullet-bleed repair - 2026-09-15 10:00 PT batch.

Strips footnote-bullet + next-NEO-name-fragment bleed that the parser left in
stored titles. Pure hygiene: base titles verified via the browser path
2026-09-15 (VM egress still dead since 2026-09-12 ~18:00 PT, EDGAR re-reads
and browser.open both impossible; browser.search live):

- DOC Scott M. Brinker x3 'President and Chief Executive Officer \u25cf Kelvin O'
  -> 'President and Chief Executive Officer': Healthpeak IR (Q3 2022
  results release) confirms "appointed Scott Brinker ... as President and
  Chief Executive Officer".
- DOC Kelvin O. Moses 2025 'Chief Financial Officer \u25cf Adam G' -> 'Chief
  Financial Officer': Healthpeak 2025-04-24 release "Names Kelvin Moses as
  Chief Financial Officer" (ir.healthpeak.com + businesswire).
- DOC Adam G. Mabry x3 'Chief Investment Officer \u25cf Scott R' -> 'Chief
  Investment Officer': Healthpeak 2025 IR release names "Adam Mabry, Chief
  Investment Officer".
- DOC Scott R. Bohn x3 'Chief Development Officer and Head of Lab \u25cf Tracy A'
  -> 'Chief Development Officer and Head of Lab': Healthpeak 2025 IR release
  names "Scott Bohn, Chief Development Officer and Head of Lab" verbatim.
- APA John J. Christmann IV x3 'CEO \u25cf Juliet S' -> 'CEO': SEC Form 4
  filings (sec.gov, e.g. wk-form4_1736271720.xml) list Christmann's officer
  title as "CEO"; "Juliet S" is Juliet S. Ellis, an APA director nominee
  (2022 8-K), whose name fragment bled from an adjacent footnote cell.

13 rows touched, title-only. Numbers asserted unchanged before/after.

Name-column-shift check (the 2026-09-14 18:00 batch's worry for DOC): the
bleed chain is a perfect adjacent-row chain Brinker <- "Kelvin O" (Moses),
Moses <- "Adam G" (Mabry), Mabry <- "Scott R" (Bohn), Bohn <- "Tracy A"
(Porter), and every name -- including Tracy A. Porter (2025, stored) -- is a
real stored DOC NEO. Title-cell contamination only; no row shift.
"""

import json
import shutil

COMP = "data/compensation.json"
BACKUP = "hidden_files/compensation_backup_20260915_1000_pre_titlebleed.json"

STRIPS = {
    "President and Chief Executive Officer \u25cf Kelvin O":
        "President and Chief Executive Officer",
    "Chief Financial Officer \u25cf Adam G":
        "Chief Financial Officer",
    "Chief Investment Officer \u25cf Scott R":
        "Chief Investment Officer",
    "Chief Development Officer and Head of Lab \u25cf Tracy A":
        "Chief Development Officer and Head of Lab",
    "CEO \u25cf Juliet S":
        "CEO",
}

shutil.copy2(COMP, BACKUP)
with open(COMP) as f:
    data = json.load(f)

touched = []
for c in data["companies"]:
    for e in c.get("executives", []):
        t = e.get("title")
        if t in STRIPS:
            before = (e.get("total"), e.get("salary"), e.get("stock_awards"),
                      e.get("option_awards"), e.get("non_equity_incentive"),
                      e.get("pension_nqdc"), e.get("pension_change"),
                      e.get("all_other"), e.get("bonus"))
            e["title"] = STRIPS[t]
            after = (e.get("total"), e.get("salary"), e.get("stock_awards"),
                     e.get("option_awards"), e.get("non_equity_incentive"),
                     e.get("pension_nqdc"), e.get("pension_change"),
                     e.get("all_other"), e.get("bonus"))
            assert before == after, \
                f"number drift on {c['ticker']} {e['name']} {e['year']}"
            touched.append((c["ticker"], e["name"], e["year"], t, STRIPS[t]))

assert len(touched) == 13, f"expected 13 rows, got {len(touched)}: {touched}"

with open(COMP, "w") as f:
    json.dump(data, f, indent=2)

print(f"stripped {len(touched)} title rows; backup at {BACKUP}")
for row in sorted(touched):
    print("  ", row)
