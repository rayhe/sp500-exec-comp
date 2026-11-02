#!/usr/bin/env python3
"""308th review (2026-11-01 18:30 PT): BALL column-drop sibling detector.

Read-only analysis (no data writes). Enumerates candidate rows that share the
BALL 306th-review corruption signature:
  Variant A: filing.stock -> stored non_equity_incentive,
             filing.option -> stored all_other; filing NEIP/pension/all_other
             dropped; stored stock_awards == 0 and option_awards == 0;
             stored.total recomputed as salary+bonus+neip+all_other (foots
             exactly against the misfiled mapping).
  Variant B: filing.bonus -> stored stock_awards, filing.stock -> stored neip,
             filing.option -> stored all_other; stored bonus == 0;
             stored total == salary+stock+neip+all_other (foots exactly).

Tier 1 (strong): stock_awards == 0 AND option_awards == 0 AND the stored
  total foots exactly against all stored components AND non_equity_incentive
  > 0 AND all_other >= $300,000. Rationale: all_other >= $300k is rare for
  genuine cash compensation (perquisites/severance) but exactly what a
  misfiled option grant looks like; variant-A BALL rows had all_other in the
  $0.17M-$3.2M band. No NEIP threshold: Causey 2024 (neip $472k) and Lewis
  2023 (neip $660k) prove the family reaches below $1M. Footing-exact rows
  only: genuine filing-side non-footing rows are adjudicated elsewhere.
Tier 2 (weak): stored bonus == 0 AND option_awards == 0 AND stock_awards > 0
  AND pension_nqdc == 0 AND stored total foots exactly against the stored
  components AND non_equity_incentive >= $1,000,000. Needs filing check:
  legit bonus=0/no-option rows exist; the variant-B tell (stored.stock ==
  filing.bonus) only shows in the filing.

Exclusions: component_mismatch-labeled rows (already adjudicated as
filing-side non-footing; they fail the exact-footing test anyway), and
already-repaired BALL rows (now carry stock/option values).

308th-review triage results (2026-11-01 18:30 PT):
- REGN (6 rows): FALSE POSITIVES. The founders' SCT stock/option cells are
  em-dashes (no equity granted 2023-2025; the 2026 DEF 14A LTI grant table
  confirms). Stored rows are filing-verbatim. Tier-1 is a triage list, not
  a verdict; every company needs filing arbitration.
- ROL (9 flags + 1 blind spot): CONFIRMED, variant C (split-column). ROL's
  SCT splits Equity Awards into RSA/PSU sub-columns; the legacy parse
  dropped the RSA sub-column on 2023/2025 rows (PSU->neip, NEIP->all_other
  shift, total recomputed). 10 rows repaired filing-verbatim from the 2026
  DEF 14A SCT, +$15,083,902 restored. Gary Rollins 2025 (total == salary,
  all_other dropped) is a detector blind spot: that shape can be
  legitimate, so the filing is the arbiter.
- Remaining queue (44 tier-1 flags across 19 companies after REGN/ROL):
  ELV x8, GLW x5, PAYC x3, PYPL x3, ARE x2, DG x2, TDG x2, RDDT x2,
  C/CHTR/CPB/DVA/EFX/FAST/LII/LYV/VRTX x1. Prioritize whole-company
  clusters (ELV, GLW) and companies whose other rows carry stock>0.
  Tier-2 (1,169) stays an advisory watch-list for variant-B.

310th-review triage (2026-11-01 22:45 PT):
- GLW (14 rows, whole-company): CONFIRMED, new sub-family variant D
  (stock-awards mislabeled as bonus). The legacy parse filed the 2026 DEF
  14A SCT's Stock Awards column into `bonus` and left `stock_awards`=0 on
  every GLW row; Corning's SCT has no Bonus column, option awards are $0
  (Corning grants no options). All other fields were already
  filing-verbatim. Repaired by relabel (bonus->stock_awards, bonus=0;
  totals unchanged), filing-verbatim titles, and 2 missing anchor-company
  NEO rows restored (A. Hal Nelson III 2025/2024; the 2024 row carries the
  filing's own $1 gap, stored verbatim). Script:
  hidden_files/apply_glw_stockbonus_relabel_20261101_2245.py; evidence:
  goal hidden_files/dq_20261101_2245/ (2026 proxy, SCT cell parse,
  VERIFICATION.md).
- Post-repair note: GLW Weeks 2024 now reads tier-2-shaped (bonus=0,
  stock>0, pension=0, option=0, neip>$1M, foots exactly) but is
  filing-verbatim adjudicated - the filing has no bonus column, so the
  variant-B tell cannot apply. Do not re-arbitrate GLW.

315th-review adjudication (2026-11-02 09:00 PT):
- BRO (6 tier-2 flags: Powell Brown 2024/2023, Watts 2024/2023,
  Barrett Brown 2024/2023): FALSE POSITIVES. The 2026 DEF 14A
  (acc. 0001193125-26-122172) SCT Bonus column is genuinely blank
  (em-dash) for all FY2023/2024 rows; the FY2025 Bonus values are
  one-time Accession-acquisition discretionary bonuses (CD&A p.35).
  All 13 stored BRO rows byte-equal to the primary SCT; Walker
  2023's stored bonus=300,000 confirms the parse handles a
  populated Bonus cell correctly. Do not re-arbitrate BRO.
- Remaining queue: 31 tier-1 (REGN x6 already false-positived), tier-2
  1,172 (the +1 is the adjudicated GLW Weeks 2024 row).

311th-review triage (2026-11-02 01:00 PT):
- PAYC (3 rows: Richison 2024/2023/2022): FALSE POSITIVES. The 2026 DEF
  14A SCT (acc. 0001193125-26-140064) shows Richison 2024/2023 with
  stock_awards = em-dash (no equity granted; Paycom's SCT has no Option
  Awards column, Paycom grants no options) - stored rows byte-equal.
  Richison 2022 arbitrated against the 2025 DEF 14A SCT (acc.
  0001193125-25-072358): 785,953 / -- / -- / 1,538,816 / 813,649 /
  3,138,418, byte-equal to stored. No data changes. Evidence: goal
  hidden_files/dq_20261102_0030/ (2026 + 2025 proxies, SCT cell parses).
- PYPL (3 rows): SPLIT verdict. Chriss 2024 FALSE POSITIVE (filing
  1,250,000 / -- / -- / 4,975,000 / 433,527 / 6,658,527, byte-equal to
  stored; PayPal's SCT likewise has no option/pension columns). Miller
  2023 + Gill 2023 CONFIRMED, new sub-family variant E (salary-drop
  left-shift): the legacy parse dropped the Salary cell on these two
  continuation rows and shifted bonus->salary, stock->bonus,
  all_other->NEIP, total->all_other, then recomputed the total. Repaired
  filing-verbatim (Miller 2023: 100,962 / 3,000,000 / 8,825,116 / 0 /
  3,462 / 11,929,539, carries the filing's own $1 gap, stored verbatim;
  Gill 2023: 80,769 / 1,000,000 / 8,825,116 / 0 / 923 / 9,906,808);
  filing-verbatim titles on all 6 Miller/Gill rows (Miller "EVP, Chief
  Financial and Operating Officer", Gill "EVP, General Manager, Small
  Business and Financial Services"). $21,654,617 parser-invented
  compensation removed (phantom batch 84, gross_removed
  $2,856,183,832, net $-1,100,252,252); FY2025-anchored company
  aggregates untouched. Script:
  hidden_files/apply_pypl_salarydrop_20261102_0030.py; evidence: goal
  hidden_files/dq_20261102_0030/ (2026 proxy, SCT TR-parse,
  VERIFICATION.md).
- Remaining queue: 25 tier-1 (REGN x6 + PAYC x3 + PYPL Chriss 2024 already
  adjudicated false-positive; PYPL Miller/Gill 2023 repaired), tier-2
  1,172. Next clusters: ARE x2, DG x2, TDG x2, RDDT x2, ORCL x2
  (Ellison - likely false-positive, founder takes no equity; needs
  filing arbitration), then singles.

312th-review triage (2026-11-02 02:30 PT):
- ARE (2 flagged rows): CONFIRMED, and the corruption ran 7 rows deep.
  Binda 2023 + Kass 2023 were variant E (salary-drop left-shift, the
  311th-review PYPL sub-family); Marcus 2023 + Moglia 2023 were ALSO
  variant E but evaded tier-1 because their filing NEIP > 0 kept stored
  stock_awards > 0 after the shift (and bonus != 0, so tier-2 missed them
  too) -- a detector blind spot of the same shape as ROL's Gary Rollins
  2025. Marcus 2025 + Binda 2025 + Cole 2025 were a NEW sub-family,
  variant F (standalone footnote-marker cell shift): the 2025 SCT rows
  whose Bonus cell carries a standalone footnote-marker cell ((3) Marcus,
  (5) Binda, (7) Cole) had the marker consumed as the Stock Awards value,
  shifting stock->NEIP, NEIP->pension, pension->all_other; the SCT Stock
  Awards column cross-checks against the Grants of Plan-Based Awards
  table sums (Marcus 5,004,205 / Binda 4,006,119 / Cole 3,304,425).
  Marcus 2025 additionally dropped the $197,341 All Other cell and
  recomputed the total (genuine comp restored). Repaired filing-verbatim;
  $36,603,281 net phantom removed (batch 85). Script:
  hidden_files/apply_are_columndrop_20261102_0230.py; evidence: goal
  hidden_files/dq_20261102_0230/.
- DG (2 flagged rows: Vasos 2025, Vasos 2024): FALSE POSITIVES. The 2026
  DEF 14A SCT (acc. 0001104659-26-040394) shows em-dash stock AND option
  cells for Vasos 2025/2024 (no equity granted; the grants table confirms
  "--" both years) -- stored rows byte-equal (Paycom/Regeneron pattern).
  No data changes.
- Remaining queue: 12 tier-1 (TDG x2, RDDT x2, ORCL x2, C/CHTR/CPB/DVA/
  EFX/FAST/LII/LYV/VRTX singles); tier-2 1,172 stays advisory.

313th-review triage (2026-11-02 05:00 PT):
- C (1 flagged row: Mason 2024): CONFIRMED, and the corruption ran 5 rows
  deep -- new sub-family variant G (salary-drop left-shift with filing NEIP
  parked in option_awards, genuine All Other dropped, filing Total filed
  into all_other, total recomputed). Fraser/Mason/Morton 2024/2023 repaired
  filing-verbatim; $104,577,464 phantom removed (batch 86). Structural blind
  spot: tier-1 requires option_awards == 0, but variant G parks filing NEIP
  there, so variant-G rows with genuine non-zero NEIP are invisible to it;
  a total-footing-identity sweep (not the option==0 gate) is the way to find
  missed siblings dataset-wide.
- TDG (Lisman 2022, Murphy 2025), RDDT (Huffman 2025/2024), ORCL (Ellison
  2024/2023): FALSE POSITIVES -- stored rows byte-equal to primary SCTs
  (TransDigm SCT has no Stock Awards column, options-only equity; Huffman
  took no 2024-2025 equity; Ellison $1 salary + security-cost All Other).
- Remaining queue: 8 tier-1 singles
  (CHTR/CPB/DVA/EFX/FAST/LII/LYV/VRTX); tier-2 1,172 stays advisory.

314th-review triage (2026-11-02 06:30 PT):
- VRTX (1 flagged row: Kewalramani 2025): CONFIRMED, and the corruption ran
  12 rows deep (whole-company) -- new sub-family variant H (stock-drop
  right-shift on an option-less SCT): the 2026 DEF 14A SCT (acc.
  0000875320-26-000153) has no Option Awards / pension columns; the legacy
  parse filed Stock Awards -> non_equity_incentive and NEIP -> pension_nqdc
  with stock_awards = 0 (e.g. Kewalramani 2025: $15,002,270 stock /
  $4,118,640 NEIP / $423,351 All Other). All 12 rows repaired
  filing-verbatim as total-neutral relabels (pension_nqdc -> 0). Only
  Kewalramani 2025 tripped tier-1 (all_other $423,351 >= $300k); the other
  11 are the documented all_other-gate blind spot class.
- FAST (1 flagged row: Florness 2025): CONFIRMED on 2 rows (2025 + 2024) --
  the standalone "(5)" footnote-marker cell on the Salary cell was consumed
  as a data cell, shifting Option Awards -> non_equity_incentive,
  NEIP -> all_other, dropping the genuine All Other cell ($2,941 / $2,754)
  and recomputing the total (Florness 2025 $4,180,387->$4,183,328, 2024
  $1,693,133->$1,695,887). Florness 2023 was already filing-verbatim
  (def14a_verified_20260910); all other FAST NEOs have no marker cell and
  parsed correctly (Watts/Tunnicliff/Lisowski/Miller/Soderberg/Lewis 2025
  spot-checked byte-equal). $5,695 genuine compensation restored (batch 87,
  negative delta); FAST aggregates re-anchored (total_neo_compensation
  $13,202,068->$13,205,009, total_compensation $4,180,387->$4,183,328,
  aggregate_stats.mean_ceo_pay 330936874->330936879 per section-17).
- CHTR (Winfrey 2025), CPB (Anderson 2026), DVA (Rodriguez 2023), EFX
  (Horvath 2025), LII (Maskara 2023), LYV (Rapino 2023): FALSE POSITIVES --
  stored rows byte-equal to primary SCTs (Winfrey 2025 no equity granted;
  Anderson 2026 $720,597 All Other is genuine former-CFO severance; CPB SCT
  has no Option column; Rodriguez 2023 no equity; Horvath 2025 $6,030,075
  All Other genuine per filing; Maskara 2023 no equity; Rapino 2023 $18.7M
  NEIP + no equity, filing-verbatim).
- Remaining queue: 0 tier-1 (all 8 singles adjudicated -- do not
  re-arbitrate CHTR/CPB/DVA/EFX/FAST/LII/LYV/VRTX, nor ARE/DG/TDG/RDDT/
  ORCL/PAYC/PYPL/REGN/C); tier-2 1,172 stays advisory. Next: variant-G
  sweep via total-footing identity (option==0 gate is blind); variant-F
  sweep (standalone footnote-marker cells); pure-legacy omitted-zero
  companies (per-filing dash check); VRTX Tatsis 2024 SCT row is absent
  from the dataset (filing shows $691,154 / $5,250,328 / $1,341,900 /
  $50,934 / $7,334,316) -- queue for a missing-row batch.
  Script: hidden_files/apply_vrtx_fast_repair_20261102_0630.py; evidence:
  goal hidden_files/dq_20261102_0630/.
"""
import json
import sys

DATA = "/home/hatch/repos/sp500-exec-comp/data/compensation.json"
PRE_REPAIR_BACKUP = ("/home/hatch/repos/sp500-exec-comp/data/"
                     "compensation_backup_20261101_1445_pre_ball2024_repair.json")

COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]

BALL_306TH_VARIANT_A = {
    ("Daniel W. Fisher", 2024), ("Ronald J. Lewis", 2024),
    ("Carey S. Causey", 2024), ("Daniel W. Fisher", 2023),
    ("Ronald J. Lewis", 2023),
}
BALL_306TH_VARIANT_B = {
    ("Howard H. Yu", 2024), ("Hannah S. Lim-Johnson", 2024),
    ("Howard H. Yu", 2023),
}


def tiers(e):
    c = {k: e.get(k, 0) or 0 for k in COMPS}
    foots = sum(c.values()) == e.get("total", 0)
    if not foots:
        return None
    if c["stock_awards"] == 0 and c["option_awards"] == 0 \
            and c["non_equity_incentive"] > 0 and c["all_other"] >= 300_000:
        return 1
    if c["bonus"] == 0 and c["stock_awards"] > 0 \
            and c["option_awards"] == 0 and c["pension_nqdc"] == 0 \
            and c["non_equity_incentive"] >= 1_000_000:
        return 2
    return None


def scan(d, label):
    t1, t2 = [], []
    for c in d["companies"]:
        for e in c.get("executives", []):
            t = tiers(e)
            if t == 1:
                t1.append((c["ticker"], e["name"], e["year"], e["total"],
                           e.get("_total_source")))
            elif t == 2:
                t2.append((c["ticker"], e["name"], e["year"], e["total"],
                           e.get("_total_source")))
    print(f"[{label}] tier-1 candidates: {len(t1)}, tier-2 candidates: {len(t2)}")
    return t1, t2


def main():
    validate = len(sys.argv) > 1 and sys.argv[1] == "--validate"
    d = json.load(open(DATA))
    t1, t2 = scan(d, "current data")
    for row in t1:
        print("  T1", row)
    if validate:
        b = json.load(open(PRE_REPAIR_BACKUP))
        bt1, bt2 = scan(b, "pre-repair BALL backup")
        fa = {(n, y) for _, n, y, _, _ in bt1}
        fb = {(n, y) for _, n, y, _, _ in bt2}
        ma = BALL_306TH_VARIANT_A - fa
        mb = BALL_306TH_VARIANT_B - fb
        print(f"[validate] variant-A BALL rows in T1: "
              f"{len(fa & BALL_306TH_VARIANT_A)}/5")
        print(f"[validate] variant-B BALL rows in T2: "
              f"{len(fb & BALL_306TH_VARIANT_B)}/3")
        if ma:
            print("  MISSING T1 (detector blind):", sorted(ma))
            sys.exit(1)
        if mb:
            # tier-2 is an advisory watch-list: the variant-B tell
            # (stored.stock == filing.bonus, bonus dropped) only resolves
            # at the filing. Misses are queued, not detector failures.
            print("  T2 misses are queued for filing-level triage, not a "
                  "detector failure:", sorted(mb))
        print("[validate] PASS: all 5 variant-A BALL rows detected in T1")


if __name__ == "__main__":
    main()
