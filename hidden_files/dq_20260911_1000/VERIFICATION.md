# DQ batch 2026-09-11 10:00 PT — rounding-bucket re-verification (batch 2)

Raw DEF 14A filings fetched 2026-09-11 ~10:00 PT via SEC EDGAR (User-Agent: Kit/1.0 (factoryfactorykit@gmail.com)).
All stored components + totals matched the filings verbatim; deltas are genuine filing-side arithmetic inconsistencies.

| Row | Filing SCT values | Stored | Delta |
|---|---|---|---|
| GPN Cameron M. Bready 2025 | 1,050,000 / - / 12,129,964 / 4,002,022 / 2,903,553 / 223,853 / **20,307,392** | identical | +2,000 |
| EMN Christopher M. Killian 2025 | 648,253 / 0 / 1,932,705 / 499,531 / 263,670 / 276,581 / 75,286 / **3,696,226** | identical | -200 |
| NI Melody Birmingham 2024 | 665,883 / - / 1,583,297 / 975,000 / 77,285 / **3,301,416** | identical | +49 |
| TAP Natalie Maciolek 2024 | 595,253 / - / 924,031 / 300,003 / 454,699 / 128,200 / **2,402,156** | identical | +30 |
| TAP Michelle St. Jacques 2024 | 728,671 / - / 1,155,007 / 375,008 / 593,340 / 208,342 / **3,060,390** | identical | -22 |
| DRI Rajesh Vennam 2023 | 687,019 / - / 1,445,747 / 445,487 / 619,004 / 158,062 / **3,355,329** | identical | -10 |

All 6 relabeled rounding -> component_mismatch per 2026-09-10 CDNS/TSCO/RF precedent.
Also: UNP total_neo_compensation 43,460,309 -> 39,707,000; FRT 12,663,122 -> 13,898,336 (recomputed from fiscal-year rows).
ALB Anderson 2024 relabeled rounding -> component_mismatch (filing-side $90 error, earlier DEF14A verification).
