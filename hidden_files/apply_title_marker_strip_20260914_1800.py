"""Title footnote-marker strip - 2026-09-14 18:00 PT batch.

Strips stray SCT footnote markers ('*', '**') that the parser left in
stored titles. Pure hygiene: base titles verified against primary
sources via the browser path 2026-09-14 (VM egress still dead, EDGAR
re-reads impossible):

- COR Steven H. Collis 'Executive Chairman*' -> 'Executive Chairman':
  Cencora 2024-03-11 succession PR confirms "transition to the role of
  Executive Chair of the Cencora Board of Directors, effective Oct 1, 2024".
- ROST Adam Orvos 'Chief Financial Officer**' -> 'Chief Financial Officer':
  ROST 2025-02-20 8-K + Feb 2025 press releases confirm EVP and CFO
  (retired Sept 30, 2025; Sheehan succeeded Oct 1, 2025).
- SHW Allen J. Mistysyn 'Senior Vice President – Finance and CFO*' ->
  'Senior Vice President – Finance and CFO': SHW corporate leadership
  page confirms verbatim title (CFO until Jan 1, 2026 succession).

8 rows touched, title-only. No numbers change. The title-bleed/truncation
class (DOC x11, ALLE x3, APA x3, DPZ x3, VST x3, UHS x1, STLD x3) needs
DEF 14A re-reads and is queued separately in
title_bleed_truncation_queue_20260914_1800.md.
"""
import json
import shutil

COMP = "data/compensation.json"
BACKUP = "hidden_files/compensation_backup_20260914_1800_pre_titlemarker.json"

STRIPS = {
    "Executive Chairman*": "Executive Chairman",
    "Chief Financial Officer**": "Chief Financial Officer",
    "Senior Vice President \u2013 Finance and CFO*":
        "Senior Vice President \u2013 Finance and CFO",
}

shutil.copy2(COMP, BACKUP)
with open(COMP) as f:
    data = json.load(f)

touched = []
for c in data["companies"]:
    for e in c.get("executives", []):
        t = e.get("title")
        if t in STRIPS:
            before = (e.get("total"), e.get("salary"), e.get("stock_awards"))
            e["title"] = STRIPS[t]
            after = (e.get("total"), e.get("salary"), e.get("stock_awards"))
            assert before == after, f"number drift on {c['ticker']} {e['name']} {e['year']}"
            touched.append((c["ticker"], e["name"], e["year"], t, STRIPS[t]))

assert len(touched) == 8, f"expected 8 rows, got {len(touched)}: {touched}"

with open(COMP, "w") as f:
    json.dump(data, f, indent=2)

print(f"stripped {len(touched)} title rows; backup at {BACKUP}")
for row in sorted(touched):
    print("  ", row)
