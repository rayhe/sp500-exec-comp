"""2026-09-15 23:30 PT CEO-anchor adjudication: PSA NEO name/title repair.

Primary source: Public Storage 2026 DEF 14A Summary Compensation Table
(accession 0001190131-26-000089, filed 2026-04-22), extracted to
goal hidden_files/dq_20260915_2330/PSA_sct2_dump.txt.

Findings (all verified against the filed SCT):
- The 2026-proxy SCT numeric rows were intact, but four rows carried other
  NEOs' names: 2023 'Nathaniel A. Vitan' ($6,343,867) is H. Thomas Boyle's
  row; 2023 'Lily Yan Hughes' ($2,604,632) is Nathaniel A. Vitan's row;
  2024 'Thomas S. Boyle' ($8,504,894) is Chris C. Sambar's row;
  2024 'Lily Yan Hughes' ($2,386,301) is Nathaniel A. Vitan's row.
  Every numeric field on each row is byte-identical to the correct person's
  filed SCT row, so these are pure name (+title) misattributions.
- Natalia N. Johnson's 2023 SCT row ($4,873,162) was dropped by the parser;
  restored verbatim (components foot exactly to the filed total).
- Title divergences vs the filed SCT principal-position column repaired:
  Vitan rows 'Chief Investment Officer' -> 'Chief Legal Officer and
  Corporate Secretary'; Sambar 2025 'President' -> 'Chief Operating
  Officer'; Johnson 2025 'President' -> 'Chief Administrative Officer';
  Boyle 2024/2025 'CFO and VP' -> 'Chief Financial and Investment Officer';
  Hughes->Vitan rows 'Chief Legal Officer and Secretary' -> 'Chief Legal
  Officer and Corporate Secretary'.

CEO-anchor adjudication for the six queued companies (TMUS, NKE, SWKS, CCI,
PSA, MAA): all six company-level (ceo_name, total_compensation) pairings are
legitimate under the section-6 convention (current CEO paired with their
latest verified SCT total). Verified tonight against the 2026 DEF 14A SCTs:
TMUS Gopalan $35,439,421 = FY2025 SCT total; NKE Hill $36,340,876 = FY2026
SCT total (answers the queue's open question: it is neither Donahoe's 2024
total, $29,184,701 per the pay-versus-performance table, nor an annualized
figure); SWKS Brace $24,536,606 = FY2025 SCT total (components sum exactly);
CCI Hillabrant $14,154,801 = FY2025 SCT total (components sum exactly);
PSA Russell $9,909,777 = FY2025 SCT total; MAA Hill $5,453,480 = FY2025 SCT
total (components sum exactly). No company-level changes.

Net: +1 record (6,780 -> 6,781). No numeric changes to any existing row.
"""
import json

PATH = "data/compensation.json"

d = json.load(open(PATH))
companies = d["companies"]

ACC = "0001190131-26-000089"
SRC = f"2026 DEF 14A SCT (accession {ACC})"


def find(ticker, year, name):
    for c in companies:
        if c["ticker"] == ticker:
            for e in c["executives"]:
                if e["year"] == year and e["name"] == name:
                    return e
    raise KeyError((ticker, year, name))


def numerics(e):
    return (
        e.get("salary"), e.get("bonus"), e.get("stock_awards"),
        e.get("option_awards"), e.get("non_equity_incentive"),
        e.get("all_other"), e.get("total"),
    )


# 1. 2023 'Nathaniel A. Vitan' -> 'H. Thomas Boyle' (components are Boyle's)
e = find("PSA", 2023, "Nathaniel A. Vitan")
assert numerics(e) == (600000, None, 2658700, 2077467, 994500, 13200, 6343867), numerics(e)
e["name"] = "H. Thomas Boyle"
e["title"] = "Chief Financial and Investment Officer"
e["_name_note_20260915_2330"] = (
    "CEO-anchor adjudication 2026-09-15 23:30 PT: stored name 'Nathaniel A. Vitan' "
    f"was a parser misattribution; the {SRC} 2023 row with these exact figures is "
    "H. Thomas Boyle's. All numeric fields asserted byte-identical to the filing."
)
e["_title_note_20260915_2330"] = (
    "CEO-anchor adjudication 2026-09-15 23:30 PT: stored title 'Chief Investment "
    "Officer' was a fragment of this NEO's own filed title; restored to the "
    f"filing-verbatim SCT principal position per the {SRC}."
)

# 2. 2023 'Lily Yan Hughes' -> 'Nathaniel A. Vitan' (components are Vitan's)
e = find("PSA", 2023, "Lily Yan Hughes")
assert numerics(e) == (425000, None, 1013296, 791886, 361250, 13200, 2604632), numerics(e)
e["name"] = "Nathaniel A. Vitan"
e["title"] = "Chief Legal Officer and Corporate Secretary"
e["_name_note_20260915_2330"] = (
    "CEO-anchor adjudication 2026-09-15 23:30 PT: stored name 'Lily Yan Hughes' "
    f"was a parser misattribution; the {SRC} 2023 row with these exact figures is "
    "Nathaniel A. Vitan's. All numeric fields asserted byte-identical to the filing."
)
e["_title_note_20260915_2330"] = (
    "CEO-anchor adjudication 2026-09-15 23:30 PT: title restored to the "
    f"filing-verbatim SCT principal position per the {SRC}."
)

# 3. 2024 'Thomas S. Boyle' -> 'Chris C. Sambar' (components are Sambar's)
e = find("PSA", 2024, "Thomas S. Boyle")
assert numerics(e) == (166667, 1000000, 7338227, None, None, None, 8504894), numerics(e)
assert e["title"] == "Chief Operating Officer", e["title"]
e["name"] = "Chris C. Sambar"
e["_name_note_20260915_2330"] = (
    "CEO-anchor adjudication 2026-09-15 23:30 PT: stored name 'Thomas S. Boyle' "
    f"was a parser misattribution; the {SRC} 2024 row with these exact figures is "
    "Chris C. Sambar's (title 'Chief Operating Officer' was already correct). "
    "All numeric fields asserted byte-identical to the filing."
)

# 4. 2024 'Lily Yan Hughes' -> 'Nathaniel A. Vitan' (components are Vitan's)
e = find("PSA", 2024, "Lily Yan Hughes")
assert numerics(e) == (425000, None, 921740, 662386, 363375, 13800, 2386301), numerics(e)
e["name"] = "Nathaniel A. Vitan"
e["title"] = "Chief Legal Officer and Corporate Secretary"
e["_name_note_20260915_2330"] = (
    "CEO-anchor adjudication 2026-09-15 23:30 PT: stored name 'Lily Yan Hughes' "
    f"was a parser misattribution; the {SRC} 2024 row with these exact figures is "
    "Nathaniel A. Vitan's. All numeric fields asserted byte-identical to the filing."
)
e["_title_note_20260915_2330"] = (
    "CEO-anchor adjudication 2026-09-15 23:30 PT: title restored to the "
    f"filing-verbatim SCT principal position per the {SRC}."
)

# 5. Restore the dropped Natalia N. Johnson 2023 row (filing-verbatim).
#    530,000 + 1,980,862 + 1,558,100 + 791,000 + 13,200 = 4,873,162 (foots exactly).
johnson_2023 = {
    "name": "Natalia N. Johnson",
    "year": 2023,
    "salary": 530000,
    "bonus": None,
    "stock_awards": 1980862,
    "option_awards": 1558100,
    "non_equity_incentive": 791000,
    "all_other": 13200,
    "total": 4873162,
    "title": "Chief Administrative Officer",
    "_total_source": "verified",
    "_note": (
        "CEO-anchor adjudication 2026-09-15 23:30 PT: row absent from the dataset "
        f"(parser dropped it); restored verbatim from the {SRC} "
        "(530,000 / 1,980,862 / 1,558,100 / 791,000 / 13,200 / 4,873,162, "
        "components foot exactly to the filed total)."
    ),
}
assert 530000 + 1980862 + 1558100 + 791000 + 13200 == 4873162
psa_execs = None
for c in companies:
    if c["ticker"] == "PSA":
        psa_execs = c["executives"]
assert psa_execs is not None
# insert into the Johnson person-group (after her 2024 row)
idx = next(i for i, e in enumerate(psa_execs)
           if e["year"] == 2024 and e["name"] == "Natalia N. Johnson")
assert not any(e["year"] == 2023 and e["name"] == "Natalia N. Johnson" for e in psa_execs)
psa_execs.insert(idx + 1, johnson_2023)

# 6. Title-only repairs vs the filed SCT principal-position column.
title_fixes = [
    ("PSA", 2025, "Nathaniel A. Vitan", "Chief Legal Officer and Corporate Secretary",
     (425000, None, 914996, 668119, 425000, 14000, 2447115)),
    ("PSA", 2025, "Chris C. Sambar", "Chief Operating Officer",
     (800000, None, 1694589, 1237285, 1000000, 5333, 4737207)),
    ("PSA", 2025, "Natalia N. Johnson", "Chief Administrative Officer",
     (625000, None, 1793357, 1309441, 857794, 14000, 4599592)),
    ("PSA", 2025, "H. Thomas Boyle", "Chief Financial and Investment Officer",
     (725000, None, 2400618, 1752792, 1104050, 206540, 6189000)),
    ("PSA", 2024, "H. Thomas Boyle", "Chief Financial and Investment Officer",
     (650000, None, 2417777, 1737742, 820000, 13800, 5639319)),
]
for ticker, year, name, title, expected in title_fixes:
    e = find(ticker, year, name)
    assert numerics(e) == expected, (ticker, year, name, numerics(e))
    old = e["title"]
    e["title"] = title
    e["_title_note_20260915_2330"] = (
        "CEO-anchor adjudication 2026-09-15 23:30 PT: stored title "
        f"{old!r} did not match the filed SCT principal position; restored to "
        f"the filing-verbatim title per the {SRC}. Numeric fields unchanged."
    )

# 7. Metadata recount: +1 record.
meta = d["metadata"]
assert meta["total_neo_records"] == 6780, meta["total_neo_records"]
meta["total_neo_records"] = 6781
assert meta["title_coverage"] == "6780/6780", meta["title_coverage"]
meta["title_coverage"] = "6781/6781"
assert meta["total_executives"] == 6780, meta["total_executives"]
meta["total_executives"] = 6781
assert "6780 NEO records" in meta["description"], meta["description"]
meta["description"] = meta["description"].replace("6780 NEO records", "6781 NEO records")

with open(PATH, "w") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("PSA repair complete: 4 renames, 1 row restored, 9 title cells, metadata 6780->6781")
