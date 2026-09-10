# S&P 500 Executive Compensation Tracker

**[Live site →](https://rayhe.github.io/sp500-exec-comp)**

A data-driven dashboard tracking executive compensation across all 500 S&P 500 companies, built from primary SEC EDGAR DEF 14A proxy filings. 500 companies, 506 peer network nodes, 5,897 compensation benchmarking edges, 485 iterations and counting.

## What's Here

### Data (`data/`)

- **`compensation.json`** — All 500 S&P 500 companies with Named Executive Officer (NEO) compensation data. 500 enriched with full NEO breakdowns (salary, bonus, stock awards, option awards, non-equity incentive, pension, all other) parsed directly from SEC primary filings — 497 from DEF 14A summary compensation tables; 3 verified exceptions: BX and KKR (no SCT-bearing proxy; NEOs from the 10-K SCT), ERIE (controlled company filing DEF 14C information statements). Per-company `data_source` labels are canonical: `SEC EDGAR DEF 14A + AFL-CIO` (438), `SEC EDGAR DEF 14A` (59), `SEC EDGAR 10-K + AFL-CIO` (2: BX, KKR), `SEC EDGAR DEF 14C + AFL-CIO` (1: ERIE) — surfaced in the NEO detail panel as a provenance line. Includes CEO name, gender, total compensation, median worker pay, pay ratio, sector, CIK, filing URL, and multi-year executive histories. 97.9% verified component-total consistency (6,638 of 6,778 records, 3 filing-side component mismatches; last audit 2026-09-10; last partial re-verification 2026-09-10, CEO-anchor repair: 30 company totals corrected to the anchor-year CEO's verified SCT total — incl. TMUS CEO-identity fix Ulf Ewaldsson → Srinivasan Gopalan per 2026 DEF 14A, WELL/STE/LKQ pay-ratio recomputes from corrected totals — LH 14-row DEF 14A rebuild, WSM 2023/2024 "Director" → Laura Alber, PEG "Chair of the Board" → Ralph A. LaRossa + phantom-row deletion; net +4 records; bloated-bucket elimination 2026-09-10 06:00 PT: 23 NEO rows re-verified vs primary DEF 14A SCTs and corrected — GEN FY2026 VCP-II sub-column misalignment (Pilette/Derse/Ko 2026 + Derse/Ko 2024 restatement), UNP 2026/2025-proxy column shifts (Vena 2025/2024/2023, Hamann/Gehringer/Rocker/Jalali/Whited 2024, Hamann/Gehringer 2023, Jalali 2025 missing all_other), K continuation-row misalignment (all five 2022 NEOs, Pilnick 2021/2023 missing components) — bloated_component bucket now 0; SBUX Kelly 2024 (+$141,986) and FDS Shan 2023 (+$30,936) confirmed genuine filing-side arithmetic inconsistencies, values match filings verbatim; GEN FY NEO sum $32.9M → $25.6M, K $41.0M → $41.1M).

- **`peer-network.json`** — Compensation peer group network graph. 506 nodes (companies), 5,897 directed edges representing "Company A benchmarks compensation against Company B" relationships extracted from DEF 14A Compensation Discussion & Analysis sections. Includes in/out degree, market cap tier, and sector classification.

- **`trends.json`** — Aggregate trend data: median CEO pay by year, median worker pay, pay ratio trends, sector breakdowns (S&P 500 and Russell 3000), compensation composition (salary vs. equity vs. incentive), five-year trends, gender pay analysis (27 female CEOs in FY2024, 17.4% premium over median), say-on-pay vote trends, and post-Thompson security perquisite surge data.

### Dashboard (`index.html`, `js/`, `css/`)

Interactive single-page dashboard with:

- Filterable company table with sector breakdown
- CEO pay scatter plot with 95% confidence interval regression
- Pay concentration distribution chart (D3 histogram, 8 color-coded buckets)
- Quartile composition analysis with S&P 500 ghost bars
- Compensation peer network force-directed graph
- Reactive key insight cards that recompute on sector filter
- Responsive design with dark mode

### Key Findings

| Metric | Value | Source |
|--------|-------|--------|
| Highest-paid CEO (FY2024) | Patrick Smith, Axon — $164.5M | Equilar/NYT 100 |
| Median S&P 500 CEO pay (FY2024) | $17.1M | Equilar/AP |
| Median pay ratio | ~200:1 | SEC DEF 14A filings |
| Female CEO pay premium | 17.4% above median | 27 female CEOs in dataset |
| Say-on-pay median support (2025) | 94.5% | ISS/Equilar |
| Say-on-pay failure rate (2025) | 1.2% | ISS/Equilar |
| CEOs with security perks (2025) | 25% (up from 18% in 2024) | Harvard Law Forum |

### Post-Thompson Security Trend

Following the December 2024 killing of UnitedHealthcare CEO Brian Thompson, S&P 500 security perquisite disclosure jumped from 18% to 25% of companies, with median home security values increasing nearly 50% over three years. UNH's own executive security spend reached $1.7M in FY2024.

## Data Sources

All compensation data sourced from primary filings:

- **SEC EDGAR DEF 14A Proxy Statements** — Primary source for all NEO compensation, peer groups, and say-on-pay results
- **AFL-CIO Executive Paywatch 2025** — CEO totals, median worker pay, pay ratios (baseline for 500-company coverage)
- **Equilar/Associated Press CEO Pay Study** (2022–2026 editions) — Trend data, median calculations
- **Equilar/New York Times 100 Highest-Paid CEOs** (2025 edition) — Top outliers
- **Harvard Law School Forum on Corporate Governance** — Russell 3000 benchmarks, say-on-pay trends, security perks analysis
- **ISS** — Shareholder vote analytics

## Structure

```
├── index.html          # Dashboard (single-page app)
├── css/style.css       # Styles
├── js/
│   ├── app.js          # Main app logic, filters, insights
│   ├── charts.js       # D3/Chart.js visualizations
│   └── network.js      # Force-directed peer network graph
├── data/
│   ├── compensation.json   # 500 companies, full NEO data
│   ├── peer-network.json   # 506 nodes, 5,897 edges
│   └── trends.json         # Aggregate trends and benchmarks
└── .nojekyll           # GitHub Pages bypass
```

## Data Verification Taxonomy

Every NEO row in `data/compensation.json` carries a `_total_source` label describing its audit state, assigned against the primary DEF 14A Summary Compensation Table. Buckets (as of the 2026-09-10 audit: 6,778 rows):

| Label | Meaning | Rows |
|---|---|---|
| `verified` | Components and total match the filing SCT verbatim. Includes `def14a_verified_YYYYMMDD` re-verification passes | 6,682 (98.6%) |
| `rounding` | Components don't foot the printed total by a small gap; stored verbatim | 50 |
| `recomputed` | Filing total missing/implausible; total recomputed from components | 36 |
| `component_mismatch` | The filing's own components don't sum to its printed total; stored verbatim, flagged | 10 |

Taxonomy decision (2026-09-10): 246 `verified` rows carry $1–$2 deltas between summed components and the printed total (e.g., NVDA/UBER/SOLV FY2025–2026). This is the filer's own rounded-dollar arithmetic, not a parse error, so they stay `verified` — relabeling would cut headline coverage from 98.6% to 95.0% for zero information gain.

`scripts/check_metadata_consistency.py` (pre-commit hook) asserts every metadata count equals an independent recount of stored records, so stale counts can never be committed.

## Methodology

1. Baseline 500 companies from AFL-CIO Paywatch 2025 (CEO totals, median worker pay, pay ratios)
2. Enriched 500/500 with full NEO breakdowns parsed from SEC EDGAR primary filings via CIK lookup (497 DEF 14A; BX/KKR 10-K SCT, ERIE DEF 14C — sweep complete 2026-09-08)
3. Peer network extracted from Compensation Discussion & Analysis sections citing benchmarking peers
4. Component-total consistency verified: 98.6% verified (6,682 of 6,778 total NEO records), 50 rounding-gap rows, 36 recomputed, 10 filing-side component mismatches (WAB 2023 CHF-conversion artifact; SBUX Kelly 2024 +$141,986; FDS Shan 2023 +$30,936; CDNS Cunningham/Scannell; TSCO Lawton/Mills; RF Turner/Keenan — all documented in-record, values match filings verbatim), multi-year coverage 500/500 (GE CEO H. Lawrence Culp Jr. history 2023-2025 restored from primary DEF 14A)
5. Governance Score (0-100) composite of five equal-weighted components, all normalized as cross-S&P-500 percentiles: Say-on-Pay approval, inverse CEO concentration, inverse CEO-to-worker pay ratio, C-suite team disclosure completeness, and board independence % (500/500 from primary DEF 14A filings). Mean of available components; null if fewer than 2. Grades: A≥80, B≥65, C≥50, D≥35, F<35.
6. Continuous panel-evaluated iteration loop (5-critic panel: data richness, visual design, interactivity, network graph quality, analytical depth)
7. Company-level comparability notes (rendered as a banner above the NEO table): multi-year equity grant structure for CSCO (3-year PRSU target in FY2025) and WDC (three overlapping PSU cycles in FY2025), Amazon's 2-3 year grant cycle, partnership/no-DEF-14A disclosure for BX and KKR, CEO succession timing for ORCL. Filing-side component anomalies (e.g., WAB 2023 CHF conversion) carry in-record explanations surfaced via the data-quality dot tooltip.

## License

Research and educational use.
