#!/usr/bin/env python3
"""2026-09-25 06:00 PT: ORCL + NCLH CEO-anchor adjudication.

Backlog candidate #1 (panel 2026-09-25 03:40 PT): "ORCL/NCLH stale CEO
anchors (Catz 'Former CEO' as ceo_name; Sommer 'Former President and CEO')".

Adjudication, verified verbatim against primary DEF 14A filings:
- ORCL (Oracle, CIK 1341439): FY2025 proxy filed 2025-09-26 (acc.
  0001193125-25-220801). The filing's "Fiscal 2026 Leadership Transitions"
  prose: on 2025-09-22 Safra A. Catz retired as CEO (appointed Executive
  Vice Chair) and the Board appointed Clayton M. Magouyrk + Michael D.
  Sicilia as co-CEOs. Neither co-CEO is an FY2025 NEO (appointed after the
  May-31 FY2025 year-end), so no filed anchor-year SCT row exists for a
  successor. Least-false-statement: KEEP the FY2025 anchor on Catz
  ($1,113,417, filing-verbatim PEO row, pairs exactly once). The CEO Pay
  Ratio section discloses FY2025 ratio 11:1 (Catz $1,113,417; median global
  employee $98,899) -- the stored 82 / $78,950 was the stale FY2024
  disclosure. Repair: pay_ratio 82 -> 11, median_worker_pay 78950 -> 98899.
  ceo_tenure already transition-encoded (2025-09, high, prose) -- untouched.
- NCLH (Norwegian Cruise Line Holdings, CIK 1513761): FY2025 proxy filed
  2026-04-30 (acc. 0001104659-26-052146). John W. Chidsey: "President and
  Chief Executive Officer, NCLH: February 2026 - Present" (director bio);
  Sommer is "Former President and Chief Executive Officer" in the FY2025
  SCT. Chidsey joined after the Dec-31 FY2025 year-end, so no filed
  anchor-year SCT row exists for him. Least-false-statement: KEEP the
  FY2025 anchor on Sommer ($13,752,560, filing-verbatim PEO row, pairs
  exactly once). The Pay Ratio Disclosure discloses FY2025 ratio 530:1
  (Sommer $13,752,560; median employee $25,954) -- the stored 550 /
  $23,312 was the stale FY2024 disclosure. Repair: pay_ratio 550 -> 530,
  median_worker_pay 23312 -> 25954. ceo_tenure records the transition per
  the WDC/ORCL convention: {2026, February, high, prose}.

All 32 ORCL+NCLH SCT rows (16+16) re-read against the primary SCTs and
confirmed filing-verbatim (components foot exactly); relabeled
verified -> def14a_verified_20260925 with per-row evidence notes. Row
count and verified_total unchanged (bucket move only). No row adds.

Run from repo root.
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260925_0600_pre_anchoradjud.json")
README_PATH = os.path.join(HERE, "..", "README.md")
APPJS_PATH = os.path.join(HERE, "..", "js", "app.js")

SRC = "def14a_verified_20260925"
NOTE = "2026-09-25 06:00 PT"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
companies = {c["ticker"]: c for c in data["companies"]}

COMP8 = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "pension_change", "all_other"]


def foot(e):
    return sum((e.get(k) or 0) for k in COMP8)


# ---------------- pre-write assertions ----------------
n0 = sum(len(c["executives"]) for c in data["companies"])
assert n0 == 7030, f"row count {n0} != 7030"

o = companies["ORCL"]
assert (o["ceo_name"], o["total_compensation"], o["fiscal_year"],
        o["proxy_fiscal_year"], o["pay_ratio"], o["median_worker_pay"],
        o["ceo_gender"]) == \
    ("Safra A. Catz", 1113417, 2025, 2025, 82, 78950, "F"), \
    "ORCL anchor pre-change values drifted"
assert o["ceo_tenure"] == {"year": 2025, "month": "September",
                           "confidence": "high", "sources": ["prose"]}, \
    "ORCL ceo_tenure pre-change drifted"
assert o["filing_url"] == \
    "https://www.sec.gov/Archives/edgar/data/1341439/000119312525220801/d72066ddef14a.htm", \
    "ORCL filing_url drifted"

n = companies["NCLH"]
assert (n["ceo_name"], n["total_compensation"], n["fiscal_year"],
        n["proxy_fiscal_year"], n["pay_ratio"], n["median_worker_pay"],
        n["ceo_gender"]) == \
    ("Harry Sommer", 13752560, 2025, 2025, 550, 23312, "M"), \
    "NCLH anchor pre-change values drifted"
assert n["ceo_tenure"] == {"year": 2023, "month": None,
                           "confidence": "medium", "sources": ["table"]}, \
    "NCLH ceo_tenure pre-change drifted"
assert n["filing_url"] == \
    "https://www.sec.gov/Archives/edgar/data/1513761/000110465926052146/tm261503-1_def14a.htm", \
    "NCLH filing_url drifted"

# every ORCL/NCLH exec row must currently be plain 'verified' and foot exactly
relabel_targets = []
for ticker in ("ORCL", "NCLH"):
    for e in companies[ticker]["executives"]:
        assert e.get("_total_source") == "verified", \
            f"{ticker} {e['name']} {e['year']}: unexpected source {e.get('_total_source')}"
        gap = abs(foot(e) - e["total"])
        assert gap == 0, f"{ticker} {e['name']} {e['year']}: gap {gap}"
        relabel_targets.append((ticker, e))
assert len(relabel_targets) == 32, f"expected 32 rows, got {len(relabel_targets)}"
print("pre-write assertions OK (7030 rows, 32 ORCL+NCLH rows all foot exactly)")

# ---------------- relabel the 32 re-verified rows ----------------
ORCL_ACC = "0001193125-25-220801"
NCLH_ACC = "0001104659-26-052146"
acc_for = {"ORCL": ORCL_ACC, "NCLH": NCLH_ACC}
for ticker, e in relabel_targets:
    e["_total_source"] = SRC
    e["_accession"] = acc_for[ticker]
    e["_repair_note_20260925_0600"] = (
        f"{NOTE}: CEO-anchor adjudication - row re-read against the primary "
        f"DEF 14A SCT (acc. {acc_for[ticker]}); filing-verbatim components, "
        f"total foots exactly (0 rounding gap).")
print(f"relabeled {len(relabel_targets)} rows -> {SRC}")

# ---------------- aggregate repairs ----------------
o["pay_ratio"] = 11
o["median_worker_pay"] = 98899
# anchor stays: Catz was the FY2025 PEO; successors have no filed FY2025 SCT row
anchor_o = [e for e in o["executives"]
            if e["name"] == o["ceo_name"] and e["year"] == o["fiscal_year"]]
assert len(anchor_o) == 1 and anchor_o[0]["total"] == o["total_compensation"] == 1113417
assert "Chief Executive Officer" in anchor_o[0]["title"]

n["pay_ratio"] = 530
n["median_worker_pay"] = 25954
n["ceo_tenure"] = {"year": 2026, "month": "February", "confidence": "high",
                   "sources": ["prose"]}
# anchor stays: Sommer was the FY2025 PEO; Chidsey (CEO since Feb 2026) has
# no filed FY2025 SCT row
anchor_n = [e for e in n["executives"]
            if e["name"] == n["ceo_name"] and e["year"] == n["fiscal_year"]]
assert len(anchor_n) == 1 and anchor_n[0]["total"] == n["total_compensation"] == 13752560
assert "Chief Executive Officer" in anchor_n[0]["title"]
print("aggregates repaired: ORCL 82/$78,950 -> 11/$98,899; "
      "NCLH 550/$23,312 -> 530/$25,954; NCLH tenure -> 2026-02 high/prose")

# ---------------- metadata re-sync ----------------
# NOTE: the def14a_verified_20260925 bucket already held 25 rows from roster
# add #12 (ILMN 11 + Everpure 14); expect 25 + 32 = 57 after this batch.
# The pre-batch backup holds the pre-repair JSON; count its bucket to derive
# the expected total.
shutil.copy(JSON_PATH, BACKUP)
print("backup:", BACKUP)
with open(BACKUP, encoding="utf-8") as bf:
    bdata = json.load(bf)
src_before = sum(1 for co in bdata["companies"] for e in co["executives"]
                 if e.get("_total_source") == SRC)
assert src_before == 25, f"expected 25 pre-existing {SRC} rows, got {src_before}"

recount = {}
for co in data["companies"]:
    for e in co["executives"]:
        recount[e.get("_total_source", "?")] = \
            recount.get(e.get("_total_source", "?"), 0) + 1
assert recount.get(SRC) == src_before + 32, \
    f"new bucket recount {recount.get(SRC)} != {src_before + 32}"
for block_name in ("data_quality", "data_quality_detailed"):
    block = data["metadata"][block_name]
    for k, v in recount.items():
        if k in block or k.startswith("def14a_verified") or k in (
                "verified", "component_mismatch", "rounding", "recomputed"):
            block[k] = v
    block["verified_total"] = (recount.get("verified", 0)
                               + sum(v for k, v in recount.items()
                                     if k.startswith("def14a_verified")))
    block["last_audit"] = "2026-09-25"
assert sum(recount.values()) == 7030
dq = data["metadata"]["data_quality"]
vt, total = dq["verified_total"], 7030
assert (vt, total) == (7000, 7030), f"unexpected buckets {(vt, total)}"
pct = f"{vt / total * 100:.1f}%"
assert pct == "99.6%", f"unexpected headline {vt}/{total} {pct}"
data["metadata"]["last_updated"] = "2026-09-25"
data["metadata"]["last_dq_repair"] = "2026-09-25"
data["last_updated"] = "2026-09-25"
print(f"headline: {vt:,} of {total:,} ({pct}) | {SRC}: 32 (bucket move, row count unchanged)")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
    f.write("\n")

# ---------------- static-copy sync ----------------
# README line 11 (index 10): audit-trail append only (headline unchanged)
with open(README_PATH, encoding="utf-8") as f:
    lines = f.readlines()
head = lines[10]
assert "99.6% verified component-total consistency (7,000 of 7,030 records" in head
audit = ("; 2026-09-25 06:00 PT batch: ORCL + NCLH CEO-anchor adjudication "
         "(backlog candidate #1, panel 2026-09-25 03:40 PT). Both FY2025 "
         "anchors kept per least-false-statement (FY2025 PEOs; successors "
         "appointed after FY year-end have no filed anchor-year SCT row): "
         "ORCL stays Safra A. Catz FY2025 $1,113,417 (retired 2025-09-22; "
         "co-CEOs Magouyrk/Sicilia since), pay ratio 82->$11 and median "
         "$78,950->$98,899 (filed FY2025 disclosure: 11:1, median $98,899, "
         "acc. 0001193125-25-220801); NCLH stays Harry Sommer FY2025 "
         "$13,752,560 (Chidsey President/CEO since Feb 2026), pay ratio "
         "550->$530 and median $23,312->$25,954 (filed FY2025 disclosure: "
         "530:1, median $25,954, acc. 0001104659-26-052146), ceo_tenure "
         "-> {2026, February, high, prose}; 32 SCT rows re-verified "
         "filing-verbatim and relabeled def14a_verified_20260925 (bucket "
         "move only); headline buckets 99.6% (7,000/7,030) unchanged.")
assert head.rstrip("\n").endswith("."), "audit-trail anchor lost"
lines[10] = head.rstrip("\n") + audit + "\n"
with open(README_PATH, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("README audit-trail appended (headline unchanged)")

# js/app.js: pay-ratio dataq fallback re-sync (section 4d recount-exact)
with open(APPJS_PATH, encoding="utf-8") as f:
    js = f.read()
old_fb = ("399 of 512 screened companies\\' disclosed ratios match "
          "<code>total_compensation / median_worker_pay</code> within 3% "
          "tolerance; 14 cluster near 2x, 10 near 0.5x, 89 differ otherwise.")
new_fb = ("401 of 512 screened companies\\' disclosed ratios match "
          "<code>total_compensation / median_worker_pay</code> within 3% "
          "tolerance; 14 cluster near 2x, 10 near 0.5x, 87 differ otherwise.")
assert old_fb in js, "app.js pay-ratio fallback pre-change text drifted"
js = js.replace(old_fb, new_fb)
with open(APPJS_PATH, "w", encoding="utf-8") as f:
    f.write(js)
print("js/app.js pay-ratio fallback re-synced (399/14/10/89 -> 401/14/10/87)")

print("done")
