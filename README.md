# S&P 500 Executive Compensation Tracker

**[Live site →](https://rayhe.github.io/sp500-exec-comp)**

A data-driven dashboard tracking executive compensation across all 500 S&P 500 companies, built from primary SEC EDGAR DEF 14A proxy filings. 500 companies, 506 peer network nodes, 5,897 compensation benchmarking edges, 259 iterations and counting.

## What's Here

### Data (`data/`)

- **`compensation.json`** — All 500 S&P 500 companies with Named Executive Officer (NEO) compensation data. 498 enriched with full NEO breakdowns (salary, bonus, stock awards, option awards, non-equity incentive, pension, all other) parsed directly from DEF 14A summary compensation tables. Includes CEO name, gender, total compensation, median worker pay, pay ratio, sector, CIK, filing URL, and multi-year executive histories. 90.5% verified component-total consistency (6174 records, 0 mismatches).

- **`peer-network.json`** — Compensation peer group network graph. 506 nodes (companies), 5,897 directed edges representing "Company A benchmarks compensation against Company B" relationships extracted from DEF 14A Compensation Discussion & Analysis sections. Includes in/out degree, market cap tier, and sector classification.

- **`trends.json`** — Aggregate trend data: median CEO pay by year, median worker pay, pay ratio trends, sector breakdowns (S&P 500 and Russell 3000), compensation composition (salary vs. equity vs. incentive), five-year trends, gender pay analysis (27 female CEOs in FY2024, 17.4% premium over median), say-on-pay vote trends, and post-Thompson security perquisite surge data.

### Dashboard (`index.html`, `js/`, `css/`)

Interactive single-page dashboard with:

- Filterable company table with sector breakdown
- CEO pay scatter plot with 95% confidence interval regression
- Pay concentration distribution chart (D3 histogram, 8 color-coded buckets)
- Quartile composition analysis with S&P 500 ghost bars
- Compensation peer network force-directed graph
- 19 reactive key insight cards that recompute on sector filter
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

## Methodology

1. Baseline 500 companies from AFL-CIO Paywatch 2025 (CEO totals, median worker pay, pay ratios)
2. Enriched 498/500 with full NEO breakdowns parsed from SEC EDGAR DEF 14A HTML filings via CIK lookup
3. Peer network extracted from Compensation Discussion & Analysis sections citing benchmarking peers
4. Component-total consistency verified: ~90% match, 6174 total NEO records, 0 mismatches, multi-year coverage 492/500
5. Continuous panel-evaluated iteration loop (5-critic panel: data richness, visual design, interactivity, network graph quality, analytical depth)

## License

Research and educational use.
