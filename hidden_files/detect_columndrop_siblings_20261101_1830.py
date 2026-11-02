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
- Remaining queue: 31 tier-1 (REGN x6 already false-positived), tier-2
  1,172 (the +1 is the adjudicated GLW Weeks 2024 row).
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
