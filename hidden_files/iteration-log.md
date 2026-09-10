# Iteration log — S&P 500 Executive Compensation Tracker

## 2026-09-10 02:00 PT — CEO-anchor re-verification repair batch

**Trigger:** scheduled run `sp500-exec-comp-iteration`. Prior audit (same night) found 37 companies where
stored `total_compensation` did not exactly match the `ceo_name` row in the anchor fiscal year.

**Repairs applied** (`hidden_files/ceo_anchor_repair_20260910.py`, assert-before-mutate; backup at
`/tmp/compensation_backup_20260910.json`):

- 19 stale/wrong company totals corrected to the anchor-year (FY2024) CEO's verified SCT total:
  AMP, IBM, ABT, PNC, ADM, TDG, GEN, ED, VMC, ENPH, MCO, APA, MOS, ROL, EIX, ALB, MNST, HSIC, ISRG.
  Pay ratios left as filed where they already paired with the corrected total.
- D: exact doubling fixed (25,809,250 -> 12,904,625, Robert M. Blue FY2024).
- WELL/STE/LKQ: stored total was wrong AND the pay ratio paired with the stale total, so ratios recomputed
  from corrected totals: WELL 6569 -> 162 (20,200,824 / 124,716), STE 157 -> 130, LKQ 182 -> 93.
  WELL's $821M was Shankh Mitra's FY2025 front-loaded mega-grant, not FY2024 pay; metadata note corrected.
- 8 CEO-transition judgments (least-false-statement principle: total must equal the verified SCT total of the
  person named in ceo_name, preferring their anchor-year row):
  - TMUS: ceo_name was factually wrong. 2026 DEF 14A proves Srinivasan Gopalan became President & CEO
    2025-11-01; Ulf Ewaldsson (never CEO) was terminated 2025-12-01. ceo_name -> Gopalan, total -> his
    verified 2025 SCT 35,439,421, pay ratio -> filed FY2025 499:1, median 74,097 -> 76,141, tenure -> 2025-11.
  - LEN/V/HPQ/OXY/ODFL: corrected to the FY2024 CEO row (Miller 29,546,675; Kelly 25,999,293;
    Lores 19,360,127; Hollub 18,535,061; Freeman 12,622,664).
  - ISRG: corrected to David J. Rosa's FY2024 President row 13,762,318 (filed ratio 147 is Guthart-based,
    left as filed with caveat).
  - MAA: NO CHANGE (deliberate). Stored 8,445,660 is Bolton's true FY2024 CEO pay and pairs with the filed
    ratio 143; switching to Hill's 2025 figure would destroy a filed ratio and mislabel the year.
- LH full rebuild: 9 corrupt/incomplete rows replaced with 14 DEF 14A rows — 12 from the 2026 proxy SCT
  (Schechter/Wang/Bailey/Caveney/Schroeder FY2023-25) + Eisenberg/Graham 2024 from the 2025 proxy SCT.
  The old Eisenberg 2024 figure (5,129,781) was itself wrong (true: 5,001,908). Company total
  5,129,781 -> 19,327,354 (Adam H. Schechter FY2024, pairs with filed ratio 337); neo_count 2 -> 6;
  total_neo_compensation -> 37,931,259.
- WSM: 2023/2024 "Director" rows -> Laura Alber (filing title "Director, President, and Chief Executive
  Officer"); components foot to filing. 2025 rows were already correct.
- PEG: 2023/2024 "Chair of the Board" rows -> Ralph A. LaRossa; phantom 2023 LaRossa row ($10,925,666,
  nonsense components, no filing match) deleted.
- CARR ("David L. Gitlin") / AMZN ("Andrew R. Jassy") row-name vs ceo_name variants left as-is (filing
  spellings; totals already correct).

**Derived metadata refreshed** (were two runs stale — the re-anchor run had not updated them; recomputed with
the same median formula the UI computes live):
- sector_medians: full recompute (Real Estate max 821,090,355 -> 61,394,770).
- aggregate_stats + top-level median/mean/max/min CEO pay, median worker pay, median pay ratio:
  median CEO pay 17,846,881 -> 17,759,221.5; mean 338.6M -> 336.9M; median pay ratio stays 199
  (TSLA pay_ratio=0 excluded per UI formula, as before).
- gender_coverage: male median 17,700,055 -> 17,545,932; female premium 10.2% -> 11.2% (33F/467M).

**Counts:** 6,774 -> 6,778 records (LH +5 net, PEG -1). Verified buckets: verified 6,316 (-10),
def14a_verified_20260910 = 14 (new); verified_total 6,624 (97.7%). title_coverage 6778/6778.
Guard `scripts/check_metadata_consistency.py` extended with the new label; green.
Independent checks: company neo_count/total_neo_compensation recount-exact; CEO-anchor audit re-run shows
zero unexplained mismatches (remaining: CARR/AMZN name variants, MAA deliberate keep).

**Docs:** README counts + verification line updated; index.html record-count string 6,774 -> 6,778.

**Commit:** as Ray He <rayche@gmail.com>, pushed via HTTPS/proxy pattern. Live GitHub Pages bytes verified.
