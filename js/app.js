/* === S&P 500 Executive Compensation Tracker — Main App === */

/* === Accessibility — prefers-reduced-motion support === */
function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/* Scroll behavior respecting reduced motion preference */
function getScrollBehavior() {
    return prefersReducedMotion() ? 'instant' : 'smooth';
}

/* Total height of sticky elements (header + section nav) for scroll offset calculations */
function getStickyOffset() {
    var header = document.querySelector('header');
    var sectionNav = document.getElementById('section-nav');
    var h = header ? header.offsetHeight : 0;
    var n = sectionNav ? sectionNav.offsetHeight : 0;
    return h + n;
}

/* === Accessibility — ARIA live region announcements === */
var _announceTimer = null;
function announce(msg) {
    var el = document.getElementById('sr-announce');
    if (!el) return;
    // Clear first so repeated identical messages still fire
    el.textContent = '';
    clearTimeout(_announceTimer);
    _announceTimer = setTimeout(function() { el.textContent = msg; }, 80);
}

/* === Theme Management === */
function initTheme() {
    var saved = localStorage.getItem('sp500-theme');
    if (saved === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    }
}
// Apply theme immediately (before DOMContentLoaded) to prevent flash
initTheme();

function toggleTheme() {
    var isLight = document.documentElement.getAttribute('data-theme') === 'light';
    if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('sp500-theme', 'dark');
        announce('Dark mode enabled');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('sp500-theme', 'light');
        announce('Light mode enabled');
    }
    // Re-render charts with updated CSS variable colors
    if (typeof redrawAllCharts === 'function') redrawAllCharts();
    // Re-render network canvas
    if (window._redrawNetwork) window._redrawNetwork();
    // Re-render comparison chart if visible
    if (window._redrawComparisonChart) window._redrawComparisonChart();
    // Re-render sector compensation heatmap (text contrast depends on theme)
    if (window._redrawSectorHeatmap) window._redrawSectorHeatmap();
    // Re-render role × sector heatmap (text contrast depends on theme)
    if (window._redrawRoleSectorHeatmap) window._redrawRoleSectorHeatmap();
}

function isDarkTheme() {
    return document.documentElement.getAttribute('data-theme') !== 'light';
}

function getThemeTextColor() {
    return isDarkTheme() ? '#e4e4e7' : '#1a1a2e';
}

function getThemeMutedColor() {
    return isDarkTheme() ? '#6b7280' : '#6b7280';
}

function getThemeSecondaryColor() {
    return isDarkTheme() ? '#a1a1aa' : '#4b5563';
}

var SECTOR_COLORS_APP = {
    'Information Technology': '#00b4d8',
    'Communication Services': '#06d6a0',
    'Consumer Discretionary': '#ef476f',
    'Health Care': '#ffd166',
    'Financials': '#a78bfa',
    'Consumer Staples': '#fb923c',
    'Industrials': '#94a3b8',
    'Energy': '#34d399',
    'Real Estate': '#f472b6',
    'Materials': '#f9a8d4',
    'Utilities': '#67e8f9'
};
function getSectorColor(s) { return SECTOR_COLORS_APP[s] || '#94a3b8'; }

let compData = null;
let trendsData = null;
let peerData = null;

/* Pre-compute CEO compensation year-over-year change for each company.
   Sets c._ceoYoY = { pct, fromYear, toYear, fromComp, toComp } or null. */
function computeCeoYoY(companies) {
    companies.forEach(function(c) {
        c._ceoYoY = null;
        c._ceoYoYSort = null;
        if (!c.executives || c.executives.length === 0) return;
        var allYears = [];
        c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
        allYears.sort(function(a, b) { return b - a; });
        if (allYears.length < 2) return;

        var yr1 = allYears[0], yr2 = allYears[1];
        var execs1 = c.executives.filter(function(e) { return e.year === yr1; });
        var execs2 = c.executives.filter(function(e) { return e.year === yr2; });

        function findCeo(execs) {
            var ceo = execs.find(function(e) {
                return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
            });
            if (!ceo && execs.length > 0) {
                ceo = execs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
            }
            return ceo;
        }

        var ceo1 = findCeo(execs1);
        var ceo2 = findCeo(execs2);

        if (ceo1 && ceo2 && ceo1.total > 0 && ceo2.total > 0) {
            var pct = (ceo1.total - ceo2.total) / ceo2.total * 100;
            c._ceoYoY = { pct: pct, fromYear: yr2, toYear: yr1, fromComp: ceo2.total, toComp: ceo1.total };
            c._ceoYoYSort = pct;
        }
    });
}

/* Pre-compute CEO multi-year pay trajectory for inline sparklines.
   Sets c._ceoTrend = [{year, total}, ...] (ascending by year) or null if < 2 points. */
function computeCeoTrend(companies) {
    companies.forEach(function(c) {
        c._ceoTrend = null;
        if (!c.executives || c.executives.length === 0) return;
        var allYears = [];
        c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
        allYears.sort(function(a, b) { return a - b; }); // ascending for left-to-right display

        if (allYears.length < 2) return;

        var trend = [];
        allYears.forEach(function(yr) {
            var yrExecs = c.executives.filter(function(e) { return e.year === yr; });
            var ceo = yrExecs.find(function(e) {
                return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
            });
            if (!ceo && yrExecs.length > 0) {
                ceo = yrExecs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
            }
            if (ceo && ceo.total > 0) {
                trend.push({ year: yr, total: ceo.total });
            }
        });

        if (trend.length >= 2) {
            c._ceoTrend = trend;
        }
    });
}

/* Pre-compute CEO stock awards as percentage of total compensation.
   Sets c._ceoStockPct (0-100 or null) for the latest fiscal year. */
function computeCeoStockPct(companies) {
    companies.forEach(function(c) {
        c._ceoStockPct = null;
        c._ceoStockPctSort = null;
        if (!c.executives || c.executives.length === 0) return;
        var allYears = [];
        c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
        allYears.sort(function(a, b) { return b - a; });
        var latestYear = allYears[0];
        var latestExecs = c.executives.filter(function(e) { return e.year === latestYear; });

        // Find CEO
        var ceo = latestExecs.find(function(e) {
            return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
        });
        if (!ceo && latestExecs.length > 0) {
            ceo = latestExecs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
        }
        if (!ceo || !ceo.total || ceo.total <= 0) return;

        var stockAwards = (ceo.stock_awards || 0) + (ceo.option_awards || 0);
        var pct = stockAwards / ceo.total * 100;
        c._ceoStockPct = Math.round(pct * 10) / 10;
        c._ceoStockPctSort = pct;
    });
}

/* Pre-compute compensation percentile rank for each company (100 = highest paid).
   Sets c._compPercentile (1-100) based on rank within the full dataset. */
/* Pre-compute CEO pay concentration: CEO total as % of total NEO compensation + CEO premium ratio (CEO / #2 exec) */
function computeCeoConcentration(companies) {
    companies.forEach(function(c) {
        c._ceoConcPct = null;
        c._ceoPremiumRatio = null;
        if (!c.executives || c.executives.length === 0) return;

        // Find latest fiscal year
        var latestYear = 0;
        c.executives.forEach(function(e) { if (e.year > latestYear) latestYear = e.year; });
        var latestExecs = c.executives.filter(function(e) { return e.year === latestYear; });
        if (latestExecs.length < 2) return;

        // Identify CEO
        var ceo = latestExecs.find(function(e) {
            return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
        });
        if (!ceo) {
            ceo = latestExecs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
        }
        if (!ceo || !ceo.total || ceo.total <= 0) return;

        // Total NEO comp
        var totalNeo = latestExecs.reduce(function(s, e) { return s + (e.total || 0); }, 0);
        if (totalNeo <= 0) return;

        c._ceoConcPct = (ceo.total / totalNeo * 100);

        // CEO premium: CEO total / #2 exec total
        var otherExecs = latestExecs.filter(function(e) { return e !== ceo && e.total > 0; });
        if (otherExecs.length > 0) {
            otherExecs.sort(function(a, b) { return (b.total || 0) - (a.total || 0); });
            var secondExec = otherExecs[0];
            if (secondExec.total > 0) {
                c._ceoPremiumRatio = ceo.total / secondExec.total;
            }
        }
    });
}

function computeCompPercentile(companies) {
    var withComp = companies.filter(function(c) { return c.total_compensation != null && c.total_compensation > 0; });
    withComp.sort(function(a, b) { return a.total_compensation - b.total_compensation; });
    var n = withComp.length;
    withComp.forEach(function(c, i) {
        c._compPercentile = Math.round((i + 1) / n * 100);
    });
    // Companies without comp data get null
    companies.forEach(function(c) {
        if (c.total_compensation == null || c.total_compensation <= 0) {
            c._compPercentile = null;
        }
    });
}

/* Format a percentile value into a human-readable tier label */
function getPercentileLabel(pctile) {
    if (pctile >= 99) return 'P99';
    if (pctile >= 95) return 'P95';
    if (pctile >= 90) return 'P90';
    if (pctile >= 75) return 'P75';
    if (pctile >= 50) return 'P50';
    if (pctile >= 25) return 'P25';
    if (pctile >= 10) return 'P10';
    if (pctile >= 5) return 'P5';
    return 'P' + pctile;
}

/* Get CSS class for percentile tier coloring */
function getPercentileClass(pctile) {
    if (pctile >= 90) return 'pctile-top';
    if (pctile >= 75) return 'pctile-high';
    if (pctile >= 25) return 'pctile-mid';
    return 'pctile-low';
}

/* Pre-compute CEO transitions: detect when the CEO changed between fiscal years.
   Sets c._ceoTransition = { oldCeo: {name, year, comp}, newCeo: {name, year, comp} } or null.
   Sets c._ceoDataYears = number of fiscal years the current CEO appears in the data. */
function computeCeoTransitions(companies) {
    companies.forEach(function(c) {
        c._ceoTransition = null;
        c._ceoDataYears = null;
        if (!c.executives || c.executives.length === 0) return;

        // Collect unique fiscal years
        var allYears = [];
        c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
        allYears.sort(function(a, b) { return a - b; }); // ascending
        if (allYears.length < 2) {
            c._ceoDataYears = 1;
            return;
        }

        // Helper: find CEO for a given year's execs
        function findCeoForYear(yr) {
            var yrExecs = c.executives.filter(function(e) { return e.year === yr; });
            if (yrExecs.length === 0) return null;
            var ceo = yrExecs.find(function(e) {
                return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
            });
            if (!ceo) {
                ceo = yrExecs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
            }
            return ceo ? { name: ceo.name || '', year: yr, comp: ceo.total || 0 } : null;
        }

        // Helper: normalize name for comparison (strip Jr/Sr/III, middle initials, lower, trim)
        function normName(n) {
            return (n || '').toLowerCase()
                .replace(/\b(jr|sr|iii|iv|ii|mr|ms|dr|phd|former)\b\.?/g, '')
                .replace(/[.,'"()]/g, '')
                .replace(/\b[a-z]\b/g, '') // remove single-letter tokens (middle initials)
                .replace(/\s+/g, ' ').trim();
        }

        // Find CEO for each year
        var ceoByYear = [];
        allYears.forEach(function(yr) {
            var ceoInfo = findCeoForYear(yr);
            if (ceoInfo) ceoByYear.push(ceoInfo);
        });

        if (ceoByYear.length < 2) {
            c._ceoDataYears = ceoByYear.length;
            return;
        }

        // Check for transitions: compare consecutive years from most recent backward
        var latestCeo = ceoByYear[ceoByYear.length - 1];
        var latestNorm = normName(latestCeo.name);

        // Count how many consecutive years the current CEO appears (from latest backward)
        var tenureCount = 1;
        for (var i = ceoByYear.length - 2; i >= 0; i--) {
            if (normName(ceoByYear[i].name) === latestNorm) {
                tenureCount++;
            } else {
                break;
            }
        }
        c._ceoDataYears = tenureCount;

        // Detect transition: did the CEO change between any consecutive years?
        // Report the most recent transition
        for (var j = ceoByYear.length - 1; j >= 1; j--) {
            var currNorm = normName(ceoByYear[j].name);
            var prevNorm = normName(ceoByYear[j - 1].name);
            if (currNorm !== prevNorm && currNorm.length > 0 && prevNorm.length > 0) {
                c._ceoTransition = {
                    oldCeo: ceoByYear[j - 1],
                    newCeo: ceoByYear[j]
                };
                break; // most recent transition only
            }
        }
    });
}

/* Classify an executive's title into a standard C-suite role category.
   Returns one of: CEO, CFO, COO, GC/CLO, CHRO, CTO, CIO, Other */
function classifyExecRole(title) {
    if (!title) return 'Other';
    var t = title.toLowerCase();
    if (/\bceo\b|chief executive/i.test(t)) return 'CEO';
    if (/\bcfo\b|chief financ|principal financial/i.test(t)) return 'CFO';
    if (/\bcoo\b|chief operating/i.test(t)) return 'COO';
    if (/\bclo\b|general counsel|chief legal/i.test(t)) return 'GC/CLO';
    if (/\bchro\b|chief human|chief people/i.test(t)) return 'CHRO';
    if (/\bcto\b|chief technolog/i.test(t)) return 'CTO';
    if (/\bcio\b|chief information/i.test(t)) return 'CIO';
    return 'Other';
}

/* Helper: get the effective compensation value for a company, respecting role filter */
function getEffectiveComp(c) {
    if (activeRole && activeRole !== 'CEO' && c._roleViewComp != null) return c._roleViewComp;
    return c.total_compensation || 0;
}

var ROLE_COLORS = {
    'CEO': '#ef476f',
    'CFO': '#06d6a0',
    'COO': '#00b4d8',
    'GC/CLO': '#a78bfa',
    'CTO': '#ffd166',
    'CHRO': '#fb923c',
    'CIO': '#67e8f9',
    'Other': '#94a3b8'
};

var ROLE_ORDER = ['CEO', 'CFO', 'COO', 'GC/CLO', 'CTO', 'CHRO', 'CIO', 'Other'];

/* Pre-compute S&P 500 role-level compensation benchmarks from latest FY NEO data.
   Sets window._roleBenchmarks = { role: { count, median, mean, p25, p75, max, topEarner } } */
var _roleBenchmarks = null;
function computeRoleBenchmarks(companies) {
    var roleMap = {};
    ROLE_ORDER.forEach(function(r) { roleMap[r] = []; });
    companies.forEach(function(c) {
        if (!c.executives || c.executives.length === 0) return;
        var allYears = [];
        c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
        var maxYr = Math.max.apply(null, allYears);
        c.executives.filter(function(e) { return e.year === maxYr; }).forEach(function(e) {
            var role = classifyExecRole(e.title);
            if (!roleMap[role]) roleMap[role] = [];
            roleMap[role].push({ total: e.total || 0, ticker: c.ticker, name: e.name, sector: c.sector, title: e.title });
        });
    });

    function arrMedian(arr) {
        if (!arr.length) return 0;
        var s = arr.slice().sort(function(a, b) { return a - b; });
        var m = Math.floor(s.length / 2);
        return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
    }

    _roleBenchmarks = {};
    ROLE_ORDER.forEach(function(role) {
        var entries = roleMap[role];
        if (!entries || entries.length === 0) return;
        var totals = entries.map(function(r) { return r.total; }).sort(function(a, b) { return a - b; });
        var topEarner = entries.slice().sort(function(a, b) { return b.total - a.total; })[0];
        _roleBenchmarks[role] = {
            count: totals.length,
            median: arrMedian(totals),
            mean: totals.reduce(function(s, v) { return s + v; }, 0) / totals.length,
            p25: totals[Math.floor(totals.length * 0.25)],
            p75: totals[Math.floor(totals.length * 0.75)],
            max: totals[totals.length - 1],
            topEarner: topEarner
        };
    });
    window._roleBenchmarks = _roleBenchmarks;
}

/* Pre-compute role-specific exec data per company for role filter pivot.
   Sets c._roleExecs = { 'CFO': {name, title, total, year, ...}, 'COO': {...}, ... } */
function computeRoleExecs(companies) {
    companies.forEach(function(c) {
        c._roleExecs = {};
        if (!c.executives || c.executives.length === 0) return;
        var allYears = [];
        c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
        var maxYr = Math.max.apply(null, allYears);
        var latestExecs = c.executives.filter(function(e) { return e.year === maxYr; });

        ROLE_ORDER.forEach(function(role) {
            if (role === 'Other') return;
            var matches = latestExecs.filter(function(e) {
                return classifyExecRole(e.title) === role;
            });
            if (matches.length > 0) {
                matches.sort(function(a, b) { return (b.total || 0) - (a.total || 0); });
                c._roleExecs[role] = matches[0];
            }
        });
    });
}

/* Pre-compute executive team completeness — which C-suite roles each company's NEO disclosure covers.
   Sets c._teamRoles (filled roles), c._teamRoleCount (0-7), c._teamMissingExpected (missing common roles). */
function computeTeamCompleteness(companies) {
    // Expected roles for a typical S&P 500 company: CEO + CFO are near-universal, others vary
    var EXPECTED_ROLES = ['CEO', 'CFO'];
    var C_SUITE_ROLES = ['CEO', 'CFO', 'COO', 'GC/CLO', 'CTO', 'CHRO', 'CIO'];
    companies.forEach(function(c) {
        c._teamRoles = [];
        c._teamRoleCount = 0;
        c._teamMissingExpected = [];
        if (!c.executives || c.executives.length === 0) return;
        var allYears = [];
        c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
        var maxYr = Math.max.apply(null, allYears);
        var latestExecs = c.executives.filter(function(e) { return e.year === maxYr; });
        var rolesFound = {};
        latestExecs.forEach(function(e) {
            var role = classifyExecRole(e.title);
            if (role !== 'Other' && !rolesFound[role]) {
                rolesFound[role] = true;
            }
        });
        c._teamRoles = C_SUITE_ROLES.filter(function(r) { return rolesFound[r]; });
        c._teamRoleCount = c._teamRoles.length;
        c._teamMissingExpected = EXPECTED_ROLES.filter(function(r) { return !rolesFound[r]; });
    });
}

/* Data completeness — reasons for missing pay ratio / median worker pay */
var MISSING_DATA_REASONS = {
    'SOLV': 'Solventum spun off from 3M in April 2024 — no full-year proxy data available for FY2024.',
    'GEV':  'GE Vernova spun off from GE in April 2024 — no full-year proxy data available for FY2024.',
    'SW':   'Smurfit WestRock formed via merger in July 2024 — no full-year proxy data available for FY2024.',
    'TSLA': 'Tesla reports $0 CEO compensation (Elon Musk). Pay ratio not computed by Tesla in proxy filings.'
};

function getMissingDataHtml(ticker, field) {
    var reason = MISSING_DATA_REASONS[ticker];
    if (!reason) return '<span class="data-na">N/A</span>';
    var title = field === 'pay_ratio' ? 'Pay ratio unavailable' : 'Worker pay unavailable';
    return '<span class="data-na" title="' + title + ': ' + reason.replace(/"/g, '&quot;') + '"><span class="data-na-icon">⚠</span> N/A</span>';
}
let currentSort = { key: 'total_compensation', dir: 'desc' };
let activeSector = null;
let activeRole = null;   // C-suite role filter: 'CFO', 'COO', 'GC/CLO', 'CTO', 'CHRO', 'CIO', or null (CEO/default)
let _roleSectorDeltaMode = false; // Delta overlay mode for role × sector heatmap
let searchTerm = '';
let currentPage = 1;
var PAGE_SIZE = 50;

function formatCurrency(val) {
    if (val == null) return '—';
    if (val >= 1e9) return '$' + (val / 1e9).toFixed(1) + 'B';
    if (val >= 1e6) return '$' + (val / 1e6).toFixed(1) + 'M';
    if (val >= 1e3) return '$' + (val / 1e3).toFixed(0) + 'K';
    return '$' + val.toLocaleString();
}

function formatCompact(val) {
    if (val == null) return '—';
    if (val >= 1e6) return '$' + (val / 1e6).toFixed(1) + 'M';
    if (val >= 1e3) return '$' + Math.round(val / 1e3) + 'K';
    return '$' + val.toLocaleString();
}

function formatRatio(val) {
    if (val == null) return '—';
    return val.toLocaleString() + ':1';
}

function csvEscape(val) {
    if (val == null) return '';
    var s = String(val);
    if (s.indexOf(',') >= 0 || s.indexOf('"') >= 0 || s.indexOf('\n') >= 0) {
        return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
}

async function loadData() {
    const [comp, trends, peer] = await Promise.all([
        fetch('data/compensation.json').then(r => r.json()),
        fetch('data/trends.json').then(r => r.json()),
        fetch('data/peer-network.json').then(r => r.json())
    ]);
    compData = comp;
    trendsData = trends;
    peerData = peer;
    return { comp, trends, peer };
}

function populateMetrics(comp, trends) {
    var stats = comp.metadata && comp.metadata.aggregate_stats;
    var medianPay = stats ? stats.median_ceo_pay : null;
    var medianRatio = stats ? stats.median_pay_ratio : null;
    var medianWorker = stats ? stats.median_worker_pay : null;

    document.getElementById('metric-median').textContent = medianPay ? formatCurrency(medianPay) : '$16.8M';
    document.getElementById('metric-median-delta').textContent = 'S&P 500, FY2024';
    document.getElementById('metric-ratio').textContent = medianRatio ? formatRatio(medianRatio) : '195:1';
    document.getElementById('metric-worker').textContent = medianWorker ? formatCompact(medianWorker) : '$81.9K';
    document.getElementById('metric-worker-delta').textContent = 'S&P 500 median employee';

    var sorted = comp.companies.slice().sort(function(a, b) { return b.total_compensation - a.total_compensation; });
    var top = sorted[0];
    document.getElementById('metric-highest').textContent = formatCurrency(top.total_compensation);
    document.getElementById('metric-highest-name').textContent = top.ceo_name + ' \u2014 ' + top.ticker;

    // Dynamic metrics from trends.json
    var stockPctEl = document.getElementById('metric-stock-pct');
    var stockSubEl = document.getElementById('metric-stock-sub');
    var growthEl = document.getElementById('metric-5yr-growth');
    var growthSubEl = document.getElementById('metric-5yr-sub');

    if (trends && trends.compensation_composition && trends.compensation_composition.s_and_p_500) {
        var stockPct = trends.compensation_composition.s_and_p_500.stock_awards_pct;
        var stockFY = trends.compensation_composition.s_and_p_500.fiscal_year;
        if (stockPct != null) {
            stockPctEl.textContent = stockPct + '%';
            stockSubEl.textContent = 'Equity dominates pay (FY' + stockFY + ')';
        }
    }

    if (trends && trends.five_year_trends) {
        var sp500Pct = trends.five_year_trends.s_and_p_500_5yr_increase;
        var period = trends.five_year_trends.period;
        if (sp500Pct) {
            growthEl.textContent = '+' + sp500Pct.replace('%', '') + '%';
            growthSubEl.textContent = 'S&P 500, ' + (period || '2020–2024');
        }
    }

    // === Interactive Metric Cards ===
    // Each metric card becomes a navigation entry point into the data
    var metricCards = document.querySelectorAll('.metric-card');
    var topTicker = top.ticker;
    var metricActions = [
        { cta: 'Sort by compensation →', action: function() { sortTableByKey('total_compensation', 'desc'); } },
        { cta: 'Sort by pay ratio →', action: function() { sortTableByKey('pay_ratio', 'desc'); } },
        { cta: 'Sort by worker pay →', action: function() { sortTableByKey('median_worker_pay', 'desc'); } },
        { cta: 'View ' + topTicker + ' details →', action: function() { if (window.findCompanyInTable) window.findCompanyInTable(topTicker); } },
        { cta: 'View composition →', action: function() { scrollToSectionById('composition-section'); } },
        { cta: 'View trends →', action: function() { scrollToSectionById('trends-section'); } }
    ];

    metricCards.forEach(function(card, i) {
        if (i >= metricActions.length) return;
        var def = metricActions[i];

        // Add CTA text element
        var ctaEl = document.createElement('div');
        ctaEl.className = 'metric-card-cta';
        ctaEl.textContent = def.cta;
        card.appendChild(ctaEl);

        // Make card focusable and interactive
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', card.querySelector('.metric-label').textContent + ': ' + card.querySelector('.metric-value').textContent + '. ' + def.cta.replace(' →', ''));

        card.addEventListener('click', function() {
            def.action();
        });
        card.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                def.action();
            }
        });
    });
}

/* Metric card helper: sort table by a key and scroll to table section */
function sortTableByKey(key, dir) {
    currentSort = { key: key, dir: dir };
    currentPage = 1;
    activeSector = null;
    activeRole = null;
    searchTerm = '';
    window._activeRatioBucket = null;
    window._activeDistFilter = null;
    window._activeConcTier = null;
    window._activeCeoTransitionFilter = false;
    window._activeTeamCompletenessFilter = null; // null=off, 'missing'=missing expected roles, 'complete'=4+ roles

    // Reset role chips
    document.querySelectorAll('.role-chip').forEach(function(rc) { rc.classList.remove('active'); });
    var firstRoleChip = document.querySelector('.role-chip');
    if (firstRoleChip) firstRoleChip.classList.add('active');
    updateRoleColumnHeader();

    // Remove filter chips if present
    var ratioChip = document.getElementById('ratio-filter-chip');
    if (ratioChip) ratioChip.remove();
    var distChip = document.getElementById('dist-filter-chip');
    if (distChip) distChip.remove();
    var concChip = document.getElementById('conc-filter-chip');
    if (concChip) concChip.remove();

    // Clear search input
    var searchInput = document.getElementById('table-search');
    if (searchInput) searchInput.value = '';

    // Clear sector chips
    document.querySelectorAll('.chip').forEach(function(chip) {
        chip.classList.remove('active');
    });
    var allChip = document.querySelector('.chip[data-sector="all"]');
    if (allChip) allChip.classList.add('active');

    // Update sort header indicators
    document.querySelectorAll('th.sortable').forEach(function(t) {
        t.classList.remove('sorted-asc', 'sorted-desc');
        t.setAttribute('aria-sort', 'none');
        if (t.dataset.sort === key) {
            t.classList.add(dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
            t.setAttribute('aria-sort', dir === 'asc' ? 'ascending' : 'descending');
        }
    });

    // Re-render and scroll
    if (compData && compData.companies) renderTable(compData.companies, { suppressAnnounce: true });
    if (window.highlightSectorBar) window.highlightSectorBar(null);
    if (window.highlightRatioBucket) window.highlightRatioBucket(null);
    scrollToTable();
    var sortLabelMap = { '_ceoYoYSort': 'CEO comp year over year change', '_ceoStockPctSort': 'CEO equity percentage of total comp', '_compPercentile': 'compensation percentile rank', '_ceoConcPct': 'CEO concentration percentage', 'ceo_name': 'CEO name' };
    var sortLbl = sortLabelMap[key] || key.replace(/_/g, ' ');
    announce('Table sorted by ' + sortLbl + ', ' + (dir === 'asc' ? 'ascending' : 'descending') + '. ' + _lastTableAnnounce);
}

/* Metric card helper: scroll to any section by ID */
function scrollToSectionById(sectionId) {
    var section = document.getElementById(sectionId);
    if (section) {
        var stickyH = getStickyOffset();
        var sectionTop = section.getBoundingClientRect().top + window.scrollY - stickyH - 12;
        window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
        announce('Scrolled to ' + (section.querySelector('h2') ? section.querySelector('h2').textContent : sectionId));
    }
}

function populateInsights(comp, trends) {
    var companies = comp.companies;
    var grid = document.getElementById('insights-grid');
    if (!grid) return;

    var insights = [];

    // 1. Pay Concentration — top 10 CEOs share of total
    var sorted = companies.slice().sort(function(a, b) { return b.total_compensation - a.total_compensation; });
    var totalAllPay = companies.reduce(function(s, c) { return s + (c.total_compensation || 0); }, 0);
    var top10Pay = sorted.slice(0, 10).reduce(function(s, c) { return s + (c.total_compensation || 0); }, 0);
    var top10Pct = totalAllPay > 0 ? (top10Pay / totalAllPay * 100).toFixed(1) : '0';
    insights.push({
        icon: '📊',
        label: 'Pay Concentration',
        value: formatCurrency(top10Pay) + ' combined',
        detail: 'The top 10 CEOs earned ' + top10Pct + '% of all S&P 500 CEO compensation. The remaining 490 CEOs share the other ' + (100 - parseFloat(top10Pct)).toFixed(1) + '%.'
    });

    // 2. $50M+ Club
    var over50M = companies.filter(function(c) { return c.total_compensation >= 50000000; });
    insights.push({
        icon: '💰',
        label: '$50M+ Club',
        value: over50M.length + ' companies',
        detail: over50M.length + ' CEOs received more than $50 million in total compensation — led by ' + sorted[0].ceo_name + ' (' + sorted[0].ticker + ') at ' + formatCurrency(sorted[0].total_compensation) + '.',
        _tickers: sorted[0] ? [sorted[0].ticker] : []
    });

    // 3. Extreme Pay Ratios (>1000:1)
    var extremeRatio = companies.filter(function(c) { return c.pay_ratio != null && c.pay_ratio > 1000; });
    var maxRatioComp = companies.filter(function(c) { return c.pay_ratio != null; }).sort(function(a, b) { return b.pay_ratio - a.pay_ratio; })[0];
    insights.push({
        icon: '⚖️',
        label: 'Extreme Ratios',
        value: extremeRatio.length + ' above 1,000:1',
        detail: extremeRatio.length + ' companies have CEO-to-worker pay ratios exceeding 1,000:1. ' + (maxRatioComp ? maxRatioComp.ticker + ' leads at ' + maxRatioComp.pay_ratio.toLocaleString() + ':1.' : ''),
        _tickers: maxRatioComp ? [maxRatioComp.ticker] : []
    });

    // 4. Top Sector by Median Pay
    var sectorMedians = comp.metadata && comp.metadata.sector_medians;
    if (sectorMedians) {
        var topSector = null;
        var topSectorPay = 0;
        var bottomSector = null;
        var bottomSectorPay = Infinity;
        Object.keys(sectorMedians).forEach(function(s) {
            var m = sectorMedians[s].median_ceo_pay;
            if (m > topSectorPay) { topSectorPay = m; topSector = s; }
            if (m < bottomSectorPay) { bottomSectorPay = m; bottomSector = s; }
        });
        var sectorSpread = topSectorPay > 0 && bottomSectorPay > 0 ? (topSectorPay / bottomSectorPay).toFixed(1) : null;
        insights.push({
            icon: '🏢',
            label: 'Sector Spread',
            value: topSector,
            detail: topSector + ' leads at ' + formatCurrency(topSectorPay) + ' median CEO pay — ' + (sectorSpread ? sectorSpread + '× higher than ' + bottomSector + ' (' + formatCurrency(bottomSectorPay) + ').' : ''),
            _topSector: topSector
        });
    }

    // 5. Zero/Near-Zero Pay
    var zeroPay = companies.filter(function(c) { return c.total_compensation <= 1; });
    var under1M = companies.filter(function(c) { return c.total_compensation > 1 && c.total_compensation < 1000000; });
    if (zeroPay.length > 0) {
        var zeroNames = zeroPay.map(function(c) { return c.ceo_name + ' (' + c.ticker + ')'; }).join(', ');
        insights.push({
            icon: '🎯',
            label: 'Zero Pay',
            value: zeroPay.length + (zeroPay.length === 1 ? ' CEO' : ' CEOs'),
            detail: zeroNames + ' reported $0 total compensation — typically founder-CEOs with large equity stakes who forgo traditional pay.',
            _tickers: zeroPay.slice(0, 3).map(function(c) { return c.ticker; })
        });
    } else if (under1M.length > 0) {
        insights.push({
            icon: '🎯',
            label: 'Below $1M',
            value: under1M.length + (under1M.length === 1 ? ' CEO' : ' CEOs'),
            detail: under1M.length + ' CEOs earned under $1M in total compensation, well below the S&P 500 median of ' + formatCurrency(comp.metadata.aggregate_stats.median_ceo_pay) + '.'
        });
    }

    // 6. Pay Range Span
    var maxPay = sorted[0];
    var nonZeroSorted = sorted.filter(function(c) { return c.total_compensation > 0; });
    var minPay = nonZeroSorted[nonZeroSorted.length - 1];
    if (maxPay && minPay && minPay.total_compensation > 0) {
        var span = Math.round(maxPay.total_compensation / minPay.total_compensation);
        insights.push({
            icon: '📏',
            label: 'Pay Range',
            value: span.toLocaleString() + '× span',
            detail: 'From ' + formatCurrency(minPay.total_compensation) + ' (' + minPay.ticker + ') to ' + formatCurrency(maxPay.total_compensation) + ' (' + maxPay.ticker + ') — a ' + span.toLocaleString() + '-fold range across the S&P 500.',
            _tickers: [maxPay.ticker, minPay.ticker]
        });
    }

    // 7. Biggest YoY CEO Pay Change
    var yoyCompanies = companies.filter(function(c) { return c._ceoYoY != null; });
    if (yoyCompanies.length > 0) {
        var biggestIncrease = yoyCompanies.slice().sort(function(a, b) { return b._ceoYoYSort - a._ceoYoYSort; })[0];
        var biggestDecrease = yoyCompanies.slice().sort(function(a, b) { return a._ceoYoYSort - b._ceoYoYSort; })[0];
        var incPct = Math.abs(biggestIncrease._ceoYoY.pct);
        var decPct = Math.abs(biggestDecrease._ceoYoY.pct);
        var incStr = incPct >= 100 ? Math.round(incPct) + '%' : incPct.toFixed(1) + '%';
        var decStr = decPct >= 100 ? Math.round(decPct) + '%' : decPct.toFixed(1) + '%';
        insights.push({
            icon: '📈',
            label: 'Biggest Pay Swing',
            value: '▲ +' + incStr + ' / ▼ −' + decStr,
            detail: biggestIncrease.ticker + ' CEO pay surged +' + incStr + ' (' + formatCurrency(biggestIncrease._ceoYoY.fromComp) + ' → ' + formatCurrency(biggestIncrease._ceoYoY.toComp) + '). ' + biggestDecrease.ticker + ' fell −' + decStr + ' (' + formatCurrency(biggestDecrease._ceoYoY.fromComp) + ' → ' + formatCurrency(biggestDecrease._ceoYoY.toComp) + '). ' + yoyCompanies.length + ' companies with YoY data.',
            _yoyCount: yoyCompanies.length
        });
    }

    // 8. Equity-Heavy Pay — most equity-reliant CEOs
    var stockPctCompanies = companies.filter(function(c) { return c._ceoStockPct != null; });
    if (stockPctCompanies.length > 0) {
        var stockSorted = stockPctCompanies.slice().sort(function(a, b) { return b._ceoStockPctSort - a._ceoStockPctSort; });
        var above90 = stockSorted.filter(function(c) { return c._ceoStockPct >= 90; });
        var topEquity = stockSorted[0];
        var allPcts = stockPctCompanies.map(function(c) { return c._ceoStockPct; });
        var medStockPct = Math.round(computeMedian(allPcts));
        insights.push({
            icon: '📊',
            label: 'Equity-Heavy Pay',
            value: above90.length + ' CEOs ≥90% equity',
            detail: above90.length + ' CEOs receive ≥90% of their compensation in stock/options — led by ' + topEquity.ceo_name + ' (' + topEquity.ticker + ') at ' + Math.round(topEquity._ceoStockPct) + '%. S&P 500 median: ' + medStockPct + '% equity.',
            _tickers: stockSorted.slice(0, 2).map(function(c) { return c.ticker; })
        });
    }

    // 9. Percentile Concentration — top 1% vs bottom 50%
    var pctileSorted = companies.slice().sort(function(a, b) { return b.total_compensation - a.total_compensation; });
    var top1PctCount = Math.max(1, Math.round(companies.length * 0.01)); // ~5 companies
    var bottom50PctCount = Math.floor(companies.length * 0.50); // 250 companies
    var top1Pay = pctileSorted.slice(0, top1PctCount).reduce(function(s, c) { return s + (c.total_compensation || 0); }, 0);
    var bottom50Pay = pctileSorted.slice(pctileSorted.length - bottom50PctCount).reduce(function(s, c) { return s + (c.total_compensation || 0); }, 0);
    if (top1Pay > 0 && bottom50Pay > 0) {
        var p1Ratio = (top1Pay / bottom50Pay).toFixed(1);
        var top1Names = pctileSorted.slice(0, top1PctCount).map(function(c) { return c.ticker; }).join(', ');
        insights.push({
            icon: '🔺',
            label: 'Top 1% vs Bottom 50%',
            value: p1Ratio + '× more pay',
            detail: 'The top ' + top1PctCount + ' CEO' + (top1PctCount > 1 ? 's' : '') + ' (P99: ' + top1Names + ') earned ' + formatCurrency(top1Pay) + ' combined — ' + p1Ratio + '× what the bottom 250 CEOs earned together (' + formatCurrency(bottom50Pay) + ').',
            _tickers: pctileSorted.slice(0, Math.min(top1PctCount, 3)).map(function(c) { return c.ticker; })
        });
    }

    // 10. CEO Pay Concentration — how much does the CEO take of total NEO comp
    var concCompanies = companies.filter(function(c) { return c._ceoConcPct != null; });
    if (concCompanies.length > 0) {
        var concSorted = concCompanies.slice().sort(function(a, b) { return b._ceoConcPct - a._ceoConcPct; });
        var mostConc = concSorted[0];
        var leastConc = concSorted[concSorted.length - 1];
        var allConcPcts = concCompanies.map(function(c) { return c._ceoConcPct; });
        var medConc = computeMedian(allConcPcts);
        var above50 = concCompanies.filter(function(c) { return c._ceoConcPct >= 50; });
        insights.push({
            icon: '👑',
            label: 'CEO Concentration',
            value: above50.length + ' CEOs take ≥50%',
            detail: above50.length + ' CEOs earn at least half of their executive team\'s total compensation. Most concentrated: ' + mostConc.ceo_name + ' (' + mostConc.ticker + ') at ' + mostConc._ceoConcPct.toFixed(1) + '%. Most distributed: ' + leastConc.ticker + ' at ' + leastConc._ceoConcPct.toFixed(1) + '%. S&P 500 median: ' + medConc.toFixed(1) + '%.',
            _tickers: [mostConc.ticker, leastConc.ticker]
        });
    }

    // 11. CEO Turnover — companies that changed CEOs within the data window
    var transitionCompanies = companies.filter(function(c) { return c._ceoTransition != null; });
    if (transitionCompanies.length > 0) {
        // Compute median comp for new vs continuing CEOs
        var newCeoComps = transitionCompanies.map(function(c) { return c.total_compensation || 0; }).filter(function(v) { return v > 0; });
        var continuingCeoComps = companies.filter(function(c) { return c._ceoTransition == null && c.total_compensation > 0; })
            .map(function(c) { return c.total_compensation; });
        var medNewCeo = newCeoComps.length > 0 ? computeMedian(newCeoComps) : 0;
        var medContinuingCeo = continuingCeoComps.length > 0 ? computeMedian(continuingCeoComps) : 0;
        // Find fiscal year range
        var transYears = transitionCompanies.map(function(c) { return c._ceoTransition.newCeo.year; });
        var minTransYear = Math.min.apply(null, transYears);
        var maxTransYear = Math.max.apply(null, transYears);
        var yearRange = minTransYear === maxTransYear ? 'FY' + minTransYear : 'FY' + minTransYear + '\u2013' + maxTransYear;
        // Most notable transition (highest paid new CEO)
        var topNewCeo = transitionCompanies.slice().sort(function(a, b) { return (b.total_compensation || 0) - (a.total_compensation || 0); })[0];
        var compDelta = medNewCeo > 0 && medContinuingCeo > 0 ? ((medNewCeo - medContinuingCeo) / medContinuingCeo * 100).toFixed(0) : null;
        var compDeltaStr = compDelta ? (parseInt(compDelta) >= 0 ? '+' + compDelta + '%' : compDelta + '%') : '';
        insights.push({
            icon: '🔄',
            label: 'CEO Turnover',
            value: transitionCompanies.length + ' transitions',
            detail: transitionCompanies.length + ' companies changed CEOs in ' + yearRange + '. New CEO median pay: ' + formatCurrency(medNewCeo) + (compDeltaStr ? ' (' + compDeltaStr + ' vs continuing CEOs at ' + formatCurrency(medContinuingCeo) + ')' : '') + '. Highest-paid new CEO: ' + (topNewCeo.ceo_name || 'N/A') + ' (' + topNewCeo.ticker + ') at ' + formatCurrency(topNewCeo.total_compensation) + '.',
            _tickers: transitionCompanies.slice(0, 3).sort(function(a, b) { return (b.total_compensation || 0) - (a.total_compensation || 0); }).map(function(c) { return c.ticker; })
        });
    }

    // Click actions for each insight — use closures over computed data
    // Actions reference window-level APIs set up in init(); safe because user clicks happen after init completes

    // Helper: reset table to clean state, apply sort, scroll
    function insightResetAndSort(sortKey, sortDir) {
        currentSort = { key: sortKey, dir: sortDir };
        activeSector = null;
        activeRole = null;
        searchTerm = '';
        currentPage = 1;
        document.getElementById('table-search').value = '';
        // Reset role chips
        document.querySelectorAll('.role-chip').forEach(function(rc) { rc.classList.remove('active'); });
        var firstRoleChip = document.querySelector('.role-chip');
        if (firstRoleChip) firstRoleChip.classList.add('active');
        updateRoleColumnHeader();
        if (window._activeRatioBucket) {
            window._activeRatioBucket = null;
            var rc = document.getElementById('ratio-filter-chip');
            if (rc) rc.remove();
        }
        if (window._activeDistFilter) {
            window._activeDistFilter = null;
            var dc = document.getElementById('dist-filter-chip');
            if (dc) dc.remove();
        }
        if (window._activeConcTier) {
            window._activeConcTier = null;
            var cc = document.getElementById('conc-filter-chip');
            if (cc) cc.remove();
        }
        if (window._activeCeoTransitionFilter) {
            window._activeCeoTransitionFilter = false;
            var tc = document.getElementById('transition-filter-chip');
            if (tc) tc.remove();
        }
        if (window._activeTeamCompletenessFilter) {
            window._activeTeamCompletenessFilter = null;
            var tcf = document.getElementById('team-filter-chip');
            if (tcf) tcf.remove();
        }
        if (window._activeYoYBucket) {
            window._activeYoYBucket = null;
            var yfc = document.getElementById('yoy-filter-chip');
            if (yfc) yfc.remove();
        }
        document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
        var allChip = document.querySelector('.chip');
        if (allChip) allChip.classList.add('active');
        document.querySelectorAll('th.sortable').forEach(function(t) {
            t.classList.remove('sorted-asc', 'sorted-desc');
            if (t.dataset.sort === sortKey) t.classList.add(sortDir === 'asc' ? 'sorted-asc' : 'sorted-desc');
        });
        renderTable(companies);
        if (window.highlightSectorBar) window.highlightSectorBar(null);
        if (window.highlightRatioBucket) window.highlightRatioBucket(null);
        scrollToTable();
    }

    // 1. Pay Concentration → sort by comp desc, show top earners
    insights[0].action = function() { insightResetAndSort('total_compensation', 'desc'); };
    insights[0].actionHint = 'View top earners';

    // 2. $50M+ Club → find the #1 earner in the table with detail panel
    var topTicker = sorted[0] ? sorted[0].ticker : null;
    insights[1].action = function() {
        if (topTicker && window.findCompanyInTable) window.findCompanyInTable(topTicker);
    };
    insights[1].actionHint = 'Explore top CEO';

    // 3. Extreme Ratios → filter to ratio > 1000:1
    insights[2].action = function() {
        if (window.filterByRatioBucket) window.filterByRatioBucket(1000, Infinity);
    };
    insights[2].actionHint = 'Filter extreme ratios';

    // 4. Sector Spread → filter to highest-paying sector
    if (insights[3]) {
        var spreadSector = insights[3]._topSector || null;
        insights[3].action = function() {
            if (spreadSector && window.filterBySector) window.filterBySector(spreadSector);
        };
        insights[3].actionHint = 'Filter by sector';
    }

    // 5. Zero Pay / Below $1M → sort by comp asc to show lowest-paid
    if (insights[4]) {
        if (zeroPay.length > 0 && zeroPay.length <= 3) {
            // Search for first zero-pay CEO
            var zeroTicker = zeroPay[0].ticker;
            insights[4].action = function() {
                if (window.findCompanyInTable) window.findCompanyInTable(zeroTicker);
            };
            insights[4].actionHint = 'View details';
        } else {
            insights[4].action = function() { insightResetAndSort('total_compensation', 'asc'); };
            insights[4].actionHint = 'View lowest paid';
        }
    }

    // 6. Pay Range → sort by comp asc to show from minimum
    if (insights[5]) {
        insights[5].action = function() { insightResetAndSort('total_compensation', 'asc'); };
        insights[5].actionHint = 'View full range';
    }

    // 7. Biggest Pay Swing → sort by YoY desc to show biggest increases first
    if (insights[6]) {
        insights[6].action = function() { insightResetAndSort('_ceoYoYSort', 'desc'); };
        insights[6].actionHint = 'Sort by YoY change';
    }

    // 8. Equity-Heavy Pay → sort by stock % desc
    if (insights[7]) {
        insights[7].action = function() { insightResetAndSort('_ceoStockPctSort', 'desc'); };
        insights[7].actionHint = 'Sort by equity %';
    }

    // 9. Percentile Concentration → sort by percentile descending
    if (insights[8]) {
        insights[8].action = function() { insightResetAndSort('_compPercentile', 'desc'); };
        insights[8].actionHint = 'Sort by percentile';
    }

    // 10. CEO Concentration → sort by total comp desc (concentrated CEOs tend to be at the top)
    if (insights[9]) {
        insights[9].action = function() { insightResetAndSort('total_compensation', 'desc'); };
        insights[9].actionHint = 'View top CEOs';
    }

    // 11. CEO Turnover → sort by YoY (new CEOs often have big YoY swings)
    if (insights[10]) {
        insights[10].action = function() { if (window.filterByCeoTransition) window.filterByCeoTransition(); };
        insights[10].actionHint = 'Filter to CEO transitions';
    }

    // 12. C-Suite Pay Gap insight card
    if (_roleBenchmarks && _roleBenchmarks['CEO'] && _roleBenchmarks['CFO']) {
        var _rbCeo = _roleBenchmarks['CEO'];
        var _rbCfo = _roleBenchmarks['CFO'];
        var _rbCoo = _roleBenchmarks['COO'];
        var cfoRatio = _rbCeo.median > 0 ? (_rbCeo.median / _rbCfo.median).toFixed(1) : '?';
        var cooStr = _rbCoo ? formatCompact(_rbCoo.median) + ' (COO, ' + _rbCoo.count + ')' : '';
        var roleCount = ROLE_ORDER.filter(function(r) { return _roleBenchmarks[r] && r !== 'Other'; }).length;
        insights.push({
            icon: '👔',
            label: 'C-Suite Pay Gap',
            value: cfoRatio + '× CEO/CFO',
            detail: 'CEO median ' + formatCurrency(_rbCeo.median) + ' vs CFO median ' + formatCurrency(_rbCfo.median) + ' (' + cfoRatio + '× gap). ' + (cooStr ? 'COO median: ' + formatCompact(_rbCoo.median) + '. ' : '') + roleCount + ' C-suite roles benchmarked across ' + _rbCeo.count + ' CEOs, ' + _rbCfo.count + ' CFOs' + (_rbCoo ? ', ' + _rbCoo.count + ' COOs' : '') + '.'
        });
    }

    if (insights[11]) {
        insights[11].action = function() {
            var section = document.getElementById('role-comp-chart');
            if (section) {
                var headerHeight = getStickyOffset();
                var top = section.getBoundingClientRect().top + window.scrollY - headerHeight - 16;
                window.scrollTo({ top: top, behavior: getScrollBehavior() });
            }
        };
        insights[11].actionHint = 'View role analysis';
    }

    // 13. Team Completeness insight card
    (function() {
        var fullTeam = companies.filter(function(c) { return c._teamRoleCount >= 4; });
        var missingExpected = companies.filter(function(c) { return c._teamMissingExpected && c._teamMissingExpected.length > 0; });
        var missingCFO = companies.filter(function(c) { return c._teamMissingExpected && c._teamMissingExpected.indexOf('CFO') >= 0 && c.executives && c.executives.length > 0; });
        var missingCEO = companies.filter(function(c) { return c._teamMissingExpected && c._teamMissingExpected.indexOf('CEO') >= 0 && c.executives && c.executives.length > 0; });
        // Average role count
        var withExecs = companies.filter(function(c) { return c.executives && c.executives.length > 0; });
        var avgRoles = withExecs.length > 0 ? (withExecs.reduce(function(s, c) { return s + (c._teamRoleCount || 0); }, 0) / withExecs.length).toFixed(1) : '?';
        // Most complete company
        var mostComplete = withExecs.slice().sort(function(a, b) { return (b._teamRoleCount || 0) - (a._teamRoleCount || 0) || (b.total_compensation || 0) - (a.total_compensation || 0); })[0];

        insights.push({
            icon: '🏢',
            label: 'Team Completeness',
            value: avgRoles + ' avg roles',
            detail: fullTeam.length + ' companies disclose 4+ C-suite roles in NEO data (of 7 tracked). ' +
                missingCFO.length + ' companies have no identifiable CFO' +
                (missingCEO.length > 0 ? ', ' + missingCEO.length + ' have no identifiable CEO' : '') +
                '. Most complete: ' + (mostComplete ? mostComplete.ticker + ' (' + (mostComplete._teamRoleCount || 0) + ' roles)' : '—') +
                '.',
            _tickers: mostComplete ? [mostComplete.ticker] : []
        });
    })();

    if (insights[12]) {
        insights[12].action = function() {
            // Toggle team completeness filter to show companies missing expected roles
            if (window.filterByTeamCompleteness) window.filterByTeamCompleteness('missing');
        };
        insights[12].actionHint = 'Filter missing roles';
    }

    // Render cards
    grid.innerHTML = '';
    insights.forEach(function(ins) {
        var card = document.createElement('div');
        card.className = 'insight-card' + (ins.action ? ' insight-clickable' : '');
        var html = '<div class="insight-icon">' + ins.icon + '</div>' +
            '<div class="insight-content">' +
            '<div class="insight-label">' + ins.label + '</div>' +
            '<div class="insight-value">' + ins.value + '</div>' +
            '<div class="insight-detail">' + ins.detail + '</div>';
        if (ins.action && ins.actionHint) {
            html += '<div class="insight-cta">' + ins.actionHint + ' →</div>';
        }
        // Add compare buttons for insights that reference specific tickers
        if (ins._tickers && ins._tickers.length > 0) {
            html += '<div class="insight-compare-actions">';
            ins._tickers.forEach(function(t) {
                var isCompared = window._compareSet && window._compareSet.indexOf(t) >= 0;
                html += '<button class="insight-compare-btn' + (isCompared ? ' selected' : '') + '" data-ticker="' + t + '" aria-pressed="' + (isCompared ? 'true' : 'false') + '" title="' + (isCompared ? 'Remove ' + t + ' from comparison' : 'Add ' + t + ' to comparison') + '"><span class="icb-icon">' + (isCompared ? '✓' : '+') + '</span> ' + t + '</button>';
            });
            html += '</div>';
        }
        html += '</div>';
        card.innerHTML = html;
        if (ins.action) {
            card.style.cursor = 'pointer';
            card.addEventListener('click', ins.action);
        }
        // Wire compare button click handlers (stop propagation to avoid triggering card action)
        card.querySelectorAll('.insight-compare-btn').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (window._toggleCompare) window._toggleCompare(btn.dataset.ticker, e);
            });
        });
        grid.appendChild(card);
    });
}

function populateTrends(trends) {
    var grid = document.getElementById('trends-grid');
    if (!grid || !trends) return;

    var cards = [];

    // 1. Gender Pay Gap
    if (trends.gender_trends && trends.gender_trends.data) {
        var latest = trends.gender_trends.data[trends.gender_trends.data.length - 1];
        var prev = trends.gender_trends.data.length > 1 ? trends.gender_trends.data[0] : null;
        if (latest) {
            var premiumPct = prev && prev.female_premium_pct ? prev.female_premium_pct : '';
            var femalePay = latest.female_median_pay || (prev && prev.female_median_pay);
            var overallPay = latest.overall_median_pay;
            var detail = latest.num_female_ceos + ' female CEOs in the S&P 500';
            if (femalePay && overallPay) {
                detail += ' (median ' + formatCurrency(femalePay) + ' vs ' + formatCurrency(overallPay) + ' overall).';
            } else {
                detail += '.';
            }
            if (latest.highest_paid_woman) {
                detail += ' Highest: ' + latest.highest_paid_woman;
                if (latest.highest_paid_woman_comp) detail += ' at ' + formatCurrency(latest.highest_paid_woman_comp);
                detail += '.';
                if (latest.note) detail += ' ' + latest.note + '.';
            }
            cards.push({
                icon: '👩‍💼',
                label: 'Gender Pay Gap',
                value: premiumPct ? premiumPct + '% female premium' : latest.num_female_ceos + ' female CEOs',
                detail: detail,
                source: 'Equilar/AP ' + (latest.source || '')
            });
        }
    }

    // 2. Say-on-Pay Voting
    if (trends.say_on_pay_trends && trends.say_on_pay_trends.data) {
        var sopData = trends.say_on_pay_trends.data;
        var latestSop = sopData[sopData.length - 1];
        if (latestSop) {
            var detail2 = latestSop.median_support + '% median shareholder support (' + latestSop.year + '). ';
            detail2 += latestSop.failure_rate_pct + '% failure rate.';
            if (latestSop.notable_failures && latestSop.notable_failures.length > 0) {
                detail2 += ' Notable failures: ';
                detail2 += latestSop.notable_failures.map(function(f) {
                    return f.company + ' (' + f.support_pct + '%)';
                }).join(', ') + '.';
            }
            if (latestSop.notable_low_support && latestSop.notable_low_support.length > 0) {
                detail2 += ' Low support: ';
                detail2 += latestSop.notable_low_support.map(function(f) {
                    return f.company + ' (' + f.support_pct + '%)';
                }).join(', ') + '.';
            }
            cards.push({
                icon: '🗳️',
                label: 'Say-on-Pay Voting',
                value: latestSop.median_support + '% median approval',
                detail: detail2,
                source: 'Harvard Law Forum / ISS'
            });
        }
    }

    // 3. Security Perks
    if (trends.security_perks_trend && trends.security_perks_trend.data) {
        var sec = trends.security_perks_trend.data;
        var detail3 = sec.s_and_p_500_ceos_with_security_2025 + ' of S&P 500 CEOs receive personal security perks in 2025, up from ' + sec.s_and_p_500_ceos_with_security_2024 + ' in 2024.';
        if (sec.note) detail3 += ' ' + sec.note + '.';
        cards.push({
            icon: '🛡️',
            label: 'Security Perks Surge',
            value: sec.s_and_p_500_ceos_with_security_2025 + ' of CEOs (2025)',
            detail: detail3,
            source: 'Harvard Law Forum / ISS / Equilar'
        });
    }

    // 4. Five-Year Growth: S&P 500 vs Russell 3000
    if (trends.five_year_trends) {
        var fyt = trends.five_year_trends;
        var detail4 = 'S&P 500 CEO median pay rose ' + fyt.s_and_p_500_5yr_increase + ' over ' + fyt.period + '. ';
        detail4 += 'Russell 3000 CEOs grew even faster at +' + fyt.russell_3000_5yr_increase.replace('+', '') + ' — smaller companies closing the gap.';
        cards.push({
            icon: '📈',
            label: '5-Year Growth Gap',
            value: 'S&P +' + fyt.s_and_p_500_5yr_increase + ' vs R3K +' + fyt.russell_3000_5yr_increase,
            detail: detail4,
            source: fyt.source || 'Harvard Law Forum'
        });
    }

    // 5. Detailed Composition Breakdown
    if (trends.compensation_composition && trends.compensation_composition.s_and_p_500_fy2024_detail) {
        var cd = trends.compensation_composition.s_and_p_500_fy2024_detail;
        var detail5 = 'Performance stock: ' + formatCurrency(cd.median_performance_stock_awards) + ' (' + cd.perf_stock_yoy_change + ' YoY). ';
        detail5 += 'Restricted stock: ' + formatCurrency(cd.median_restricted_stock) + ' (' + cd.restricted_stock_yoy_change + '). ';
        detail5 += 'Discretionary bonus: ' + formatCurrency(cd.median_discretionary_bonus) + ' (' + cd.bonus_yoy_change + '). ';
        detail5 += 'NEIP payout: ' + formatCurrency(cd.median_neip_payout) + ' (' + cd.neip_yoy_change + ').';
        cards.push({
            icon: '💎',
            label: 'Compensation Mix Detail',
            value: 'Bonus surging +' + cd.bonus_yoy_change,
            detail: detail5,
            source: cd.source || 'Harvard Law Forum'
        });
    }

    // 6. Historic Peak
    if (trends.historical_context) {
        var hc = trends.historical_context;
        var detail6 = '';
        if (hc.five_ceos_over_100m_fy2025) {
            detail6 += '5 CEOs exceeded $100M in FY2025 — the highest concentration of nine-figure packages ever recorded. ';
        }
        if (hc.highest_paid_ceo_fy2025_equilar_ap) {
            var top = hc.highest_paid_ceo_fy2025_equilar_ap;
            detail6 += 'Led by ' + top.name + ' (' + top.ticker + ') at ' + formatCurrency(top.total_compensation) + '. ';
            if (top.note) detail6 += top.note + '.';
        }
        if (detail6) {
            cards.push({
                icon: '🏆',
                label: 'Historic Peak (FY2025)',
                value: '5 CEOs over $100M',
                detail: detail6,
                source: 'Equilar/AP 2026'
            });
        }
    }

    // Render cards
    // Add click actions and CTA hints to trend cards
    // Helper: find a company ticker by matching CEO name or company name
    function findTickerByName(nameStr) {
        if (!compData || !compData.companies || !nameStr) return null;
        var lower = nameStr.toLowerCase().replace(/[.,']/g, '');
        // First try CEO name match
        for (var i = 0; i < compData.companies.length; i++) {
            var c = compData.companies[i];
            if (c.ceo_name && c.ceo_name.toLowerCase().replace(/[.,']/g, '').indexOf(lower) >= 0) return c.ticker;
        }
        // Then try company name match
        for (var i = 0; i < compData.companies.length; i++) {
            var c = compData.companies[i];
            if (c.company_name && c.company_name.toLowerCase().replace(/[.,']/g, '').indexOf(lower) >= 0) return c.ticker;
        }
        return null;
    }

    // Helper: scroll to a section by ID
    function scrollToSection(sectionId) {
        var section = document.getElementById(sectionId);
        if (section) {
            var stickyH = getStickyOffset();
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - stickyH - 12;
            window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
        }
    }

    cards.forEach(function(card) {
        if (card.label === 'Gender Pay Gap') {
            // Extract company name from "Name (Company)" pattern in highest_paid_woman
            var latestGender = trends.gender_trends && trends.gender_trends.data ? trends.gender_trends.data[trends.gender_trends.data.length - 1] : null;
            if (latestGender && latestGender.highest_paid_woman) {
                var match = latestGender.highest_paid_woman.match(/\(([^)]+)\)/);
                var companyName = match ? match[1] : null;
                var ticker = companyName ? findTickerByName(companyName) : null;
                if (ticker) {
                    card.action = function() { if (window.findCompanyInTable) window.findCompanyInTable(ticker); };
                    card.actionHint = 'View ' + ticker + ' details';
                }
            }
        } else if (card.label === 'Say-on-Pay Voting') {
            // Link to the worst failure company
            var sopData = trends.say_on_pay_trends && trends.say_on_pay_trends.data;
            var latestSop = sopData ? sopData[sopData.length - 1] : null;
            if (latestSop && latestSop.notable_failures && latestSop.notable_failures.length > 0) {
                var worstCompany = latestSop.notable_failures[0].company;
                var worstTicker = findTickerByName(worstCompany);
                if (worstTicker) {
                    card.action = function() { if (window.findCompanyInTable) window.findCompanyInTable(worstTicker); };
                    card.actionHint = 'View ' + worstTicker + ' details';
                }
            }
        } else if (card.label === '5-Year Growth Gap') {
            card.action = function() { scrollToSection('trend-chart-panel'); };
            card.actionHint = 'View trend chart';
        } else if (card.label === 'Compensation Mix Detail') {
            card.action = function() { scrollToSection('composition-section'); };
            card.actionHint = 'View composition chart';
        } else if (card.label === 'Historic Peak (FY2025)') {
            var hc = trends.historical_context;
            if (hc && hc.highest_paid_ceo_fy2024_equilar_nyt && hc.highest_paid_ceo_fy2024_equilar_nyt.ticker) {
                var peakTicker = hc.highest_paid_ceo_fy2024_equilar_nyt.ticker;
                card.action = function() { if (window.findCompanyInTable) window.findCompanyInTable(peakTicker); };
                card.actionHint = 'View ' + peakTicker + ' details';
            }
        }
    });

    grid.innerHTML = '';
    cards.forEach(function(card) {
        var el = document.createElement('div');
        el.className = 'trend-card' + (card.action ? ' trend-clickable' : '');
        var html = '<div class="trend-icon">' + card.icon + '</div>' +
            '<div class="trend-content">' +
            '<div class="trend-label">' + card.label + '</div>' +
            '<div class="trend-value">' + card.value + '</div>' +
            '<div class="trend-detail">' + card.detail + '</div>' +
            '<div class="trend-source">' + card.source + '</div>';
        if (card.action && card.actionHint) {
            html += '<div class="trend-cta">' + card.actionHint + ' →</div>';
        }
        html += '</div>';
        el.innerHTML = html;
        if (card.action) {
            el.addEventListener('click', card.action);
        }
        grid.appendChild(el);
    });
}

function buildSectorChips(companies) {
    var sectorSet = {};
    companies.forEach(function(c) { if (c.sector) sectorSet[c.sector] = true; });
    var sectors = Object.keys(sectorSet).sort();
    var container = document.getElementById('sector-chips');

    var allChip = document.createElement('button');
    allChip.className = 'chip active';
    allChip.textContent = 'All';
    allChip.addEventListener('click', function() {
        activeSector = null;
        currentPage = 1;
        document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
        allChip.classList.add('active');
        // Refresh combined filter chips to remove sector context
        if (window._updateDistFilterIndicator) window._updateDistFilterIndicator();
        if (window._updateRatioFilterIndicator) window._updateRatioFilterIndicator();
        if (window._updateConcFilterIndicator) window._updateConcFilterIndicator();
        if (window._updateCeoTransitionFilterIndicator) window._updateCeoTransitionFilterIndicator();
        if (window._updateTeamCompletenessFilterIndicator) window._updateTeamCompletenessFilterIndicator();
        renderTable(companies);
        if (window.highlightSectorBar) window.highlightSectorBar(null);
        if (window.highlightRatioBucket) window.highlightRatioBucket(null);
    });
    container.appendChild(allChip);

    sectors.forEach(function(s) {
        var chip = document.createElement('button');
        chip.className = 'chip';
        chip.textContent = s;
        chip.addEventListener('click', function() {
            activeSector = s;
            currentPage = 1;
            document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
            chip.classList.add('active');
            // Refresh combined filter chips to include sector context
            if (window._updateDistFilterIndicator) window._updateDistFilterIndicator();
            if (window._updateRatioFilterIndicator) window._updateRatioFilterIndicator();
            if (window._updateConcFilterIndicator) window._updateConcFilterIndicator();
            if (window._updateCeoTransitionFilterIndicator) window._updateCeoTransitionFilterIndicator();
        if (window._updateTeamCompletenessFilterIndicator) window._updateTeamCompletenessFilterIndicator();
            renderTable(companies);
            if (window.highlightSectorBar) window.highlightSectorBar(s);
            if (window.highlightRatioBucket) window.highlightRatioBucket(null);
        });
        container.appendChild(chip);
    });
}

/* Build role filter chips for the table controls */
function buildRoleChips(companies) {
    var container = document.getElementById('role-chips');
    if (!container) return;
    container.innerHTML = '';

    var roles = ['CEO', 'CFO', 'COO', 'GC/CLO', 'CTO', 'CHRO', 'CIO'];

    // Count companies per role
    var roleCounts = {};
    roles.forEach(function(r) { roleCounts[r] = 0; });
    companies.forEach(function(c) {
        if (!c._roleExecs) return;
        roles.forEach(function(r) { if (c._roleExecs[r]) roleCounts[r]++; });
    });

    roles.forEach(function(role) {
        var chip = document.createElement('button');
        chip.className = 'role-chip' + ((!activeRole && role === 'CEO') || activeRole === role ? ' active' : '');
        chip.style.setProperty('--role-color', ROLE_COLORS[role]);
        chip.textContent = role;
        chip.title = role + ' (' + roleCounts[role] + ' companies)';
        chip.addEventListener('click', function() {
            if (role === 'CEO') {
                activeRole = null;
            } else {
                activeRole = (activeRole === role) ? null : role;
            }
            currentPage = 1;
            // When switching to a role view, sort by total comp descending
            currentSort = { key: 'total_compensation', dir: 'desc' };
            document.querySelectorAll('th.sortable').forEach(function(t) {
                t.classList.remove('sorted-asc', 'sorted-desc');
                t.setAttribute('aria-sort', 'none');
                if (t.dataset.sort === 'total_compensation') {
                    t.classList.add('sorted-desc');
                    t.setAttribute('aria-sort', 'descending');
                }
            });
            // Update active state on chips
            document.querySelectorAll('.role-chip').forEach(function(rc) { rc.classList.remove('active'); });
            if (!activeRole) {
                container.querySelector('.role-chip').classList.add('active'); // First chip = CEO
            } else {
                chip.classList.add('active');
            }
            // Update column header
            updateRoleColumnHeader();
            renderTable(companies);
            pushState();
            announce(activeRole ? 'Viewing ' + role + ' compensation across S&P 500' : 'Viewing CEO compensation (default)');
        });
        container.appendChild(chip);
    });
}

/* Update the CEO/role column header text when role filter changes */
function updateRoleColumnHeader() {
    var th = document.querySelector('th[data-sort="ceo_name"]');
    if (th) {
        th.textContent = activeRole || 'CEO';
    }
}

/* Pre-compute outlier sets (computed once, stable across filters/sorts) */
var _outlierTop10 = null;
var _outlierLowRatio = null;
function computeOutliers(companies) {
    if (_outlierTop10) return;
    var byComp = companies.slice().sort(function(a, b) { return b.total_compensation - a.total_compensation; });
    _outlierTop10 = {};
    byComp.slice(0, 10).forEach(function(c, i) { _outlierTop10[c.ticker] = i + 1; });
    // Bottom-5 pay ratio (lowest CEO:worker ratio — "most equitable")
    var withRatio = companies.filter(function(c) { return c.pay_ratio != null && c.pay_ratio > 0; });
    withRatio.sort(function(a, b) { return a.pay_ratio - b.pay_ratio; });
    _outlierLowRatio = {};
    withRatio.slice(0, 5).forEach(function(c, i) { _outlierLowRatio[c.ticker] = i + 1; });
}

/* === Table Summary Statistics Bar === */
function computeMedian(arr) {
    if (arr.length === 0) return null;
    var sorted = arr.slice().sort(function(a, b) { return a - b; });
    var mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/* Sort-contextual summary — shows distributional stats when sorting by a non-default column */
function renderSortContextSummary(companies) {
    if (currentSort.key === 'total_compensation' || currentSort.key === 'rank') {
        return renderCompDistSummary(companies);
    }
    if (currentSort.key === '_ceoYoYSort') {
        return renderYoYSortSummary(companies);
    }
    if (currentSort.key === 'pay_ratio') {
        return renderRatioSortSummary(companies);
    }
    if (currentSort.key === 'median_worker_pay') {
        return renderWorkerPaySortSummary(companies);
    }
    if (currentSort.key === '_ceoStockPctSort') {
        return renderStockPctSortSummary(companies);
    }
    if (currentSort.key === '_compPercentile') {
        return renderPercentileSortSummary(companies);
    }
    if (currentSort.key === '_ceoConcPct') {
        return renderConcSortSummary(companies);
    }
    if (currentSort.key === 'sector') {
        return renderSectorSortSummary(companies);
    }
    if (currentSort.key === 'ceo_name') {
        return renderCeoNameSortSummary(companies);
    }
    return null;
}

/* Compensation distribution summary — shown in default sort (total_compensation) and rank sort.
   Displays total combined pay, median vs mean skewness, bracket distribution with inline mini histogram,
   and min/max range context. */
function renderCompDistSummary(companies) {
    var isRoleView = activeRole && activeRole !== 'CEO';
    var comps = companies.filter(function(c) {
        var v = isRoleView ? (c._roleViewComp || 0) : (c.total_compensation || 0);
        return v > 0;
    });
    if (comps.length === 0) return null;

    var vals = comps.map(function(c) { return isRoleView ? (c._roleViewComp || 0) : c.total_compensation; }).sort(function(a, b) { return a - b; });
    var totalCombined = vals.reduce(function(s, v) { return s + v; }, 0);
    var mean = totalCombined / vals.length;
    var median = computeMedian(vals);
    var skewRatio = mean / median;

    // Quartiles
    var q25 = vals[Math.floor(vals.length * 0.25)];
    var q75 = vals[Math.floor(vals.length * 0.75)];
    var p90 = vals[Math.floor(vals.length * 0.90)];
    var minComp = vals[0];
    var maxComp = vals[vals.length - 1];

    // Bracket distribution
    var brackets = [
        { label: '<$5M', min: 0, max: 5e6, count: 0, color: '#06d6a0' },
        { label: '$5-10M', min: 5e6, max: 10e6, count: 0, color: '#00b4d8' },
        { label: '$10-20M', min: 10e6, max: 20e6, count: 0, color: '#a78bfa' },
        { label: '$20-50M', min: 20e6, max: 50e6, count: 0, color: '#ffd166' },
        { label: '$50M+', min: 50e6, max: Infinity, count: 0, color: '#ef476f' }
    ];
    comps.forEach(function(c) {
        var v = isRoleView ? (c._roleViewComp || 0) : c.total_compensation;
        for (var bi = brackets.length - 1; bi >= 0; bi--) {
            if (v >= brackets[bi].min) { brackets[bi].count++; break; }
        }
    });
    var maxBracketCount = Math.max.apply(null, brackets.map(function(b) { return b.count; }));

    var html = '';

    // Total combined
    // Role context prefix
    if (isRoleView) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label" style="color:' + ROLE_COLORS[activeRole] + '">' + activeRole + ' Compensation</span>';
        html += '</span>';
        html += '<span class="summary-divider"></span>';
    }

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Total combined</span>';
    html += '<span class="summary-stat-value accent">' + formatCurrency(totalCombined) + '</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    // Median
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Median</span>';
    html += '<span class="summary-stat-value">' + formatCurrency(median) + '</span>';
    html += '</span>';

    // Mean with skewness indicator
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Mean</span>';
    html += '<span class="summary-stat-value">' + formatCurrency(mean) + '</span>';
    html += '</span>';

    // Skewness indicator
    if (skewRatio > 1.05) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Skew</span>';
        html += '<span class="summary-stat-value comp-dist-skew" title="Mean/median ratio of ' + skewRatio.toFixed(2) + ' — pay is concentrated at the top">';
        html += skewRatio.toFixed(1) + '× right-skewed';
        html += '</span></span>';
    }

    html += '<span class="summary-divider"></span>';

    // Range
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Range</span>';
    html += '<span class="summary-stat-value">' + formatCurrency(minComp) + ' – ' + formatCurrency(maxComp) + '</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    // Mini inline histogram
    html += '<span class="summary-stat comp-dist-histogram">';
    html += '<span class="summary-stat-label">Distribution</span>';
    html += '<span class="comp-dist-bars">';
    var activeMin = window._activeDistFilter && !window._activeDistFilter.sector ? window._activeDistFilter.min : null;
    var activeMax = window._activeDistFilter && !window._activeDistFilter.sector ? window._activeDistFilter.max : null;
    brackets.forEach(function(b) {
        var barH = maxBracketCount > 0 ? Math.max(3, Math.round(b.count / maxBracketCount * 24)) : 3;
        var maxVal = b.max === Infinity ? 1e15 : b.max;
        var isActive = (activeMin !== null && b.min === activeMin && maxVal === activeMax);
        var isDimmed = (activeMin !== null && !isActive);
        var dimStyle = isDimmed ? 'opacity:0.3;' : '';
        var activeOutline = isActive ? 'outline:2px solid ' + b.color + ';outline-offset:2px;border-radius:3px;' : '';
        html += '<span class="comp-dist-bar-group clickable-bar' + (isActive ? ' active-bracket' : '') + '" title="' + b.label + ': ' + b.count + ' companies — click to ' + (isActive ? 'clear' : 'filter') + '" onclick="filterByCompBracket(' + b.min + ',' + maxVal + ',\'' + b.label.replace("'","\\'") + '\')" style="cursor:pointer;' + activeOutline + '">';
        html += '<span class="comp-dist-bar" style="height:' + barH + 'px;background:' + b.color + ';' + dimStyle + '"></span>';
        html += '<span class="comp-dist-bar-label" style="' + dimStyle + '">' + b.count + '</span>';
        html += '</span>';
    });
    html += '</span>';
    html += '<span class="comp-dist-bracket-labels">';
    brackets.forEach(function(b) {
        html += '<span class="comp-dist-bracket-label">' + b.label + '</span>';
    });
    html += '</span>';
    html += '</span>';

    return html;
}

function renderYoYSortSummary(companies) {
    var withYoY = companies.filter(function(c) { return c._ceoYoY != null; });
    if (withYoY.length === 0) return null;

    var increases = withYoY.filter(function(c) { return c._ceoYoY.pct > 0; });
    var decreases = withYoY.filter(function(c) { return c._ceoYoY.pct < 0; });
    var unchanged = withYoY.filter(function(c) { return c._ceoYoY.pct === 0; });
    var yoyVals = withYoY.map(function(c) { return c._ceoYoY.pct; });
    var medianYoY = computeMedian(yoyVals);

    var sorted = withYoY.slice().sort(function(a, b) { return b._ceoYoYSort - a._ceoYoYSort; });
    var topInc = sorted[0];
    var topDec = sorted[sorted.length - 1];

    var fmtPct = function(v) {
        var abs = Math.abs(v);
        return (abs >= 100 ? Math.round(abs) : abs.toFixed(1)) + '%';
    };

    var html = '';

    // YoY data count
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value accent">' + withYoY.length + '</span>';
    html += '<span class="summary-stat-label">with YoY data</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    // Increases / decreases
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value positive">▲ ' + increases.length + '</span>';
    html += '<span class="summary-stat-label">increased</span>';
    html += '</span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value negative">▼ ' + decreases.length + '</span>';
    html += '<span class="summary-stat-label">decreased</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    // Median change
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Median Δ</span>';
    html += '<span class="summary-stat-value ' + (medianYoY >= 0 ? 'positive' : 'negative') + '">' + (medianYoY >= 0 ? '+' : '\u2212') + fmtPct(medianYoY) + '</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    // Biggest increase
    if (topInc && topInc._ceoYoY.pct > 0) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Biggest ▲</span>';
        html += '<span class="summary-stat-value positive">' + topInc.ticker + ' +' + fmtPct(topInc._ceoYoY.pct) + '</span>';
        html += '</span>';
    }

    // Biggest decrease
    if (topDec && topDec._ceoYoY.pct < 0) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Biggest ▼</span>';
        html += '<span class="summary-stat-value negative">' + topDec.ticker + ' \u2212' + fmtPct(topDec._ceoYoY.pct) + '</span>';
        html += '</span>';
    }

    return html;
}

function renderRatioSortSummary(companies) {
    var withRatio = companies.filter(function(c) { return c.pay_ratio != null && c.pay_ratio > 0; });
    if (withRatio.length === 0) return null;

    var ratioVals = withRatio.map(function(c) { return c.pay_ratio; });
    var medianR = Math.round(computeMedian(ratioVals));
    var meanR = Math.round(ratioVals.reduce(function(s, v) { return s + v; }, 0) / ratioVals.length);
    var extreme = withRatio.filter(function(c) { return c.pay_ratio > 1000; });
    var equitable = withRatio.filter(function(c) { return c.pay_ratio < 50; });

    var sorted = withRatio.slice().sort(function(a, b) { return b.pay_ratio - a.pay_ratio; });
    var highest = sorted[0];
    var lowest = sorted[sorted.length - 1];

    var html = '';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value accent">' + withRatio.length + '</span>';
    html += '<span class="summary-stat-label">with ratio data</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Median</span>';
    html += '<span class="summary-stat-value">' + medianR.toLocaleString() + ':1</span>';
    html += '</span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Mean</span>';
    html += '<span class="summary-stat-value">' + meanR.toLocaleString() + ':1</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value negative">' + extreme.length + '</span>';
    html += '<span class="summary-stat-label">above 1,000:1</span>';
    html += '</span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value positive">' + equitable.length + '</span>';
    html += '<span class="summary-stat-label">below 50:1</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    if (highest) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Highest</span>';
        html += '<span class="summary-stat-value negative">' + highest.ticker + ' ' + highest.pay_ratio.toLocaleString() + ':1</span>';
        html += '</span>';
    }

    if (lowest) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Lowest</span>';
        html += '<span class="summary-stat-value positive">' + lowest.ticker + ' ' + lowest.pay_ratio.toLocaleString() + ':1</span>';
        html += '</span>';
    }

    return html;
}

function renderWorkerPaySortSummary(companies) {
    var withWorker = companies.filter(function(c) { return c.median_worker_pay != null && c.median_worker_pay > 0; });
    if (withWorker.length === 0) return null;

    var vals = withWorker.map(function(c) { return c.median_worker_pay; });
    var medianW = computeMedian(vals);
    var meanW = Math.round(vals.reduce(function(s, v) { return s + v; }, 0) / vals.length);

    var above100K = withWorker.filter(function(c) { return c.median_worker_pay >= 100000; });
    var below50K = withWorker.filter(function(c) { return c.median_worker_pay < 50000; });

    var sorted = withWorker.slice().sort(function(a, b) { return b.median_worker_pay - a.median_worker_pay; });
    var highest = sorted[0];
    var lowest = sorted[sorted.length - 1];

    var html = '';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value accent">' + withWorker.length + '</span>';
    html += '<span class="summary-stat-label">with worker pay data</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Median</span>';
    html += '<span class="summary-stat-value">' + formatCompact(medianW) + '</span>';
    html += '</span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Mean</span>';
    html += '<span class="summary-stat-value">' + formatCompact(meanW) + '</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value positive">' + above100K.length + '</span>';
    html += '<span class="summary-stat-label">above $100K</span>';
    html += '</span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value negative">' + below50K.length + '</span>';
    html += '<span class="summary-stat-label">below $50K</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    if (highest) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Highest</span>';
        html += '<span class="summary-stat-value positive">' + highest.ticker + ' ' + formatCompact(highest.median_worker_pay) + '</span>';
        html += '</span>';
    }

    if (lowest) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Lowest</span>';
        html += '<span class="summary-stat-value negative">' + lowest.ticker + ' ' + formatCompact(lowest.median_worker_pay) + '</span>';
        html += '</span>';
    }

    return html;
}

function renderStockPctSortSummary(companies) {
    var withData = companies.filter(function(c) { return c._ceoStockPct != null; });
    if (withData.length === 0) return null;

    var vals = withData.map(function(c) { return c._ceoStockPct; });
    var medianPct = Math.round(computeMedian(vals) * 10) / 10;
    var meanPct = Math.round(vals.reduce(function(s, v) { return s + v; }, 0) / vals.length * 10) / 10;

    var above80 = withData.filter(function(c) { return c._ceoStockPct >= 80; });
    var below20 = withData.filter(function(c) { return c._ceoStockPct < 20; });

    var sorted = withData.slice().sort(function(a, b) { return b._ceoStockPctSort - a._ceoStockPctSort; });
    var highest = sorted[0];
    var lowest = sorted[sorted.length - 1];

    var html = '';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value accent">' + withData.length + '</span>';
    html += '<span class="summary-stat-label">with equity data</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Median</span>';
    html += '<span class="summary-stat-value">' + medianPct + '%</span>';
    html += '</span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Mean</span>';
    html += '<span class="summary-stat-value">' + meanPct + '%</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value stock-pct-high">' + above80.length + '</span>';
    html += '<span class="summary-stat-label">≥80% equity</span>';
    html += '</span>';

    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value stock-pct-low">' + below20.length + '</span>';
    html += '<span class="summary-stat-label">&lt;20% equity</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    if (highest) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Most equity-heavy</span>';
        html += '<span class="summary-stat-value stock-pct-high">' + highest.ticker + ' ' + Math.round(highest._ceoStockPct) + '%</span>';
        html += '</span>';
    }

    if (lowest) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Least equity-heavy</span>';
        html += '<span class="summary-stat-value stock-pct-low">' + lowest.ticker + ' ' + Math.round(lowest._ceoStockPct) + '%</span>';
        html += '</span>';
    }

    return html;
}

/* Percentile sort summary — tier distribution + comp range per tier */
function renderPercentileSortSummary(companies) {
    var withData = companies.filter(function(c) { return c._compPercentile != null; });
    if (withData.length === 0) return null;

    // Count companies in each tier
    var tiers = [
        { label: 'P90+', min: 90, max: 101, cls: 'pctile-top', count: 0, comps: [] },
        { label: 'P75–89', min: 75, max: 90, cls: 'pctile-high', count: 0, comps: [] },
        { label: 'P25–74', min: 25, max: 75, cls: 'pctile-mid', count: 0, comps: [] },
        { label: '<P25', min: 0, max: 25, cls: 'pctile-low', count: 0, comps: [] }
    ];

    withData.forEach(function(c) {
        for (var ti = 0; ti < tiers.length; ti++) {
            if (c._compPercentile >= tiers[ti].min && c._compPercentile < tiers[ti].max) {
                tiers[ti].count++;
                tiers[ti].comps.push(c.total_compensation || 0);
                break;
            }
        }
    });

    var sortDir = currentSort.dir === 'desc' ? 'highest first' : 'lowest first';
    var html = '<span class="summary-stat"><span class="summary-stat-label">Compensation Percentile</span>';
    html += '<span class="summary-stat-value">' + withData.length + ' companies, ' + sortDir + '</span></span>';

    tiers.forEach(function(t) {
        if (t.count === 0) return;
        var minComp = Math.min.apply(null, t.comps);
        var maxComp = Math.max.apply(null, t.comps);
        var rangeStr = formatCurrency(minComp) + '–' + formatCurrency(maxComp);
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label"><span class="pctile-badge ' + t.cls + '" style="font-size:0.65rem">' + t.label + '</span></span>';
        html += '<span class="summary-stat-value">' + t.count + ' (' + rangeStr + ')</span>';
        html += '</span>';
    });

    return html;
}

/* CEO Concentration sort context summary — shown when sorted by CEO % column.
   Displays distribution of concentrated (≥50%), moderate (35–49%), and distributed (<35%) companies,
   with a clickable mini histogram and median/mean concentration stats. */
function renderConcSortSummary(companies) {
    var withData = companies.filter(function(c) { return c._ceoConcPct != null; });
    if (withData.length === 0) return null;

    // Tiers — colors match the conc-badge classes
    var tiers = [
        { label: '≥50%', min: 50, max: 101, cls: 'conc-high', count: 0, comps: [], tag: 'Concentrated', color: '#ef476f' },
        { label: '35–49%', min: 35, max: 50, cls: 'conc-mid', count: 0, comps: [], tag: 'Moderate', color: '#ffd166' },
        { label: '<35%', min: 0, max: 35, cls: 'conc-low', count: 0, comps: [], tag: 'Distributed', color: '#06d6a0' }
    ];

    withData.forEach(function(c) {
        for (var ti = 0; ti < tiers.length; ti++) {
            if (c._ceoConcPct >= tiers[ti].min && c._ceoConcPct < tiers[ti].max) {
                tiers[ti].count++;
                tiers[ti].comps.push(c._ceoConcPct);
                break;
            }
        }
    });

    var concVals = withData.map(function(c) { return c._ceoConcPct; }).sort(function(a, b) { return a - b; });
    var medianConc = computeMedian(concVals);
    var meanConc = concVals.reduce(function(s, v) { return s + v; }, 0) / concVals.length;

    // Most and least concentrated
    var sorted = withData.slice().sort(function(a, b) { return b._ceoConcPct - a._ceoConcPct; });
    var most = sorted[0];
    var least = sorted[sorted.length - 1];

    var maxTierCount = Math.max.apply(null, tiers.map(function(t) { return t.count; }));

    var sortDir = currentSort.dir === 'desc' ? 'most concentrated first' : 'most distributed first';
    var html = '<span class="summary-stat"><span class="summary-stat-label">CEO Concentration</span>';
    html += '<span class="summary-stat-value">' + withData.length + ' companies, ' + sortDir + '</span></span>';

    html += '<span class="summary-divider"></span>';

    // Clickable histogram bars (matching comp-dist pattern)
    var activeTier = window._activeConcTier;
    html += '<span class="summary-stat conc-dist-histogram">';
    html += '<span class="summary-stat-label">Distribution</span>';
    html += '<span class="conc-dist-bars">';
    tiers.forEach(function(t) {
        var barH = maxTierCount > 0 ? Math.max(4, Math.round(t.count / maxTierCount * 24)) : 4;
        var isActive = (activeTier && activeTier.min === t.min && activeTier.max === t.max);
        var isDimmed = (activeTier && !isActive);
        var dimStyle = isDimmed ? 'opacity:0.3;' : '';
        var activeOutline = isActive ? 'outline:2px solid ' + t.color + ';outline-offset:2px;border-radius:3px;' : '';
        html += '<span class="conc-dist-bar-group clickable-bar' + (isActive ? ' active-bracket' : '') + '" title="' + t.tag + ' (' + t.label + '): ' + t.count + ' companies — click to ' + (isActive ? 'clear' : 'filter') + '" onclick="filterByConcTier(' + t.min + ',' + t.max + ',\'' + t.tag + '\',\'' + t.label.replace("'","\\'") + '\')" style="cursor:pointer;' + activeOutline + '">';
        html += '<span class="conc-dist-bar" style="height:' + barH + 'px;background:' + t.color + ';' + dimStyle + '"></span>';
        html += '<span class="conc-dist-bar-label" style="' + dimStyle + '">' + t.count + '</span>';
        html += '</span>';
    });
    html += '</span>';
    html += '<span class="conc-dist-bracket-labels">';
    tiers.forEach(function(t) {
        html += '<span class="conc-dist-bracket-label">' + t.label + '</span>';
    });
    html += '</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    // Median and mean
    html += '<span class="summary-stat"><span class="summary-stat-label">Median</span>';
    html += '<span class="summary-stat-value">' + medianConc.toFixed(1) + '%</span></span>';
    html += '<span class="summary-stat"><span class="summary-stat-label">Mean</span>';
    html += '<span class="summary-stat-value">' + meanConc.toFixed(1) + '%</span></span>';

    html += '<span class="summary-divider"></span>';

    // Most / Least concentrated
    html += '<span class="summary-stat"><span class="summary-stat-label">Most concentrated</span>';
    html += '<span class="summary-stat-value conc-high-text">' + most.ceo_name + ' (' + most.ticker + ') ' + most._ceoConcPct.toFixed(1) + '%</span></span>';
    html += '<span class="summary-stat"><span class="summary-stat-label">Most distributed</span>';
    html += '<span class="summary-stat-value conc-low-text">' + least.ceo_name + ' (' + least.ticker + ') ' + least._ceoConcPct.toFixed(1) + '%</span></span>';

    return html;
}

/* Sector sort context summary — shown when sorted by sector column.
   Displays number of sectors, mini sector distribution with color-coded segment bars,
   highest/lowest median pay sectors, and sector spread ratio. */
function renderSectorSortSummary(companies) {
    if (companies.length === 0) return null;
    var isRoleView = activeRole && activeRole !== 'CEO';

    // Group companies by sector
    var sectorMap = {};
    companies.forEach(function(c) {
        var s = c.sector || 'Unknown';
        if (!sectorMap[s]) sectorMap[s] = { name: s, companies: [], comps: [] };
        sectorMap[s].companies.push(c);
        var cv = isRoleView ? (c._roleViewComp || 0) : (c.total_compensation || 0);
        if (cv > 0) {
            sectorMap[s].comps.push(cv);
        }
    });

    var sectors = Object.keys(sectorMap).map(function(k) {
        var s = sectorMap[k];
        var sorted = s.comps.slice().sort(function(a, b) { return a - b; });
        return {
            name: s.name,
            count: s.companies.length,
            median: sorted.length > 0 ? computeMedian(sorted) : 0,
            mean: sorted.length > 0 ? sorted.reduce(function(sum, v) { return sum + v; }, 0) / sorted.length : 0,
            min: sorted.length > 0 ? sorted[0] : 0,
            max: sorted.length > 0 ? sorted[sorted.length - 1] : 0
        };
    });

    // Sort by median descending to find highest/lowest
    var byMedian = sectors.slice().sort(function(a, b) { return b.median - a.median; });
    var highestSector = byMedian[0];
    var lowestSector = byMedian[byMedian.length - 1];

    // Sort by count descending for the bar distribution
    var byCount = sectors.slice().sort(function(a, b) { return b.count - a.count; });
    var maxCount = byCount[0] ? byCount[0].count : 1;

    var spreadRatio = lowestSector && lowestSector.median > 0
        ? (highestSector.median / lowestSector.median).toFixed(1) : '—';

    var html = '';

    // Sector count
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value accent">' + sectors.length + '</span>';
    html += '<span class="summary-stat-label">sectors</span>';
    html += '</span>';

    // Role context prefix
    if (isRoleView) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label" style="color:' + ROLE_COLORS[activeRole] + '">' + activeRole + ' by Sector</span>';
        html += '</span>';
    }

    html += '<span class="summary-divider"></span>';

    // Highest paying sector
    var medianLabel = isRoleView ? 'Highest ' + activeRole : 'Highest median';
    if (highestSector && highestSector.median > 0) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">' + medianLabel + '</span>';
        html += '<span class="summary-stat-value" style="color:' + getSectorColor(highestSector.name) + '">';
        html += highestSector.name + ' ' + formatCurrency(highestSector.median);
        html += '</span></span>';
    }

    // Lowest paying sector
    var lowestLabel = isRoleView ? 'Lowest ' + activeRole : 'Lowest median';
    if (lowestSector && lowestSector.median > 0 && lowestSector.name !== highestSector.name) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">' + lowestLabel + '</span>';
        html += '<span class="summary-stat-value" style="color:' + getSectorColor(lowestSector.name) + '">';
        html += lowestSector.name + ' ' + formatCurrency(lowestSector.median);
        html += '</span></span>';
    }

    // Spread ratio
    if (spreadRatio !== '—') {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Spread</span>';
        html += '<span class="summary-stat-value">' + spreadRatio + '×</span>';
        html += '</span>';
    }

    html += '<span class="summary-divider"></span>';

    // Mini sector distribution — color-coded bars, clickable to filter by sector
    var isActiveSectorSort = !!activeSector;
    html += '<span class="summary-stat sector-sort-dist">';
    html += '<span class="summary-stat-label">Distribution</span>';
    html += '<span class="sector-sort-bars">';
    byCount.forEach(function(s) {
        var barH = Math.max(3, Math.round(s.count / maxCount * 24));
        var color = getSectorColor(s.name);
        var isActive = (activeSector === s.name);
        var isDimmed = (isActiveSectorSort && !isActive);
        var dimStyle = isDimmed ? 'opacity:0.3;' : '';
        var activeOutline = isActive ? 'outline:2px solid ' + color + ';outline-offset:2px;border-radius:3px;' : '';
        var escapedName = s.name.replace(/'/g, "\\'");
        html += '<span class="sector-sort-bar-group clickable-bar' + (isActive ? ' active-bracket' : '') + '" title="' + s.name + ': ' + s.count + ' companies, median ' + formatCurrency(s.median) + ' — click to ' + (isActive ? 'clear' : 'filter') + '" onclick="filterBySectorFromBar(\'' + escapedName + '\')" style="cursor:pointer;' + activeOutline + '">';
        html += '<span class="sector-sort-bar" style="height:' + barH + 'px;background:' + color + ';' + dimStyle + '"></span>';
        html += '<span class="sector-sort-bar-count" style="' + dimStyle + '">' + s.count + '</span>';
        html += '</span>';
    });
    html += '</span>';
    html += '</span>';

    return html;
}

/* CEO Name sort context summary — shows CEO turnover stats when sorted by CEO name column. */
function renderCeoNameSortSummary(companies) {
    if (companies.length === 0) return null;

    var transitionCompanies = companies.filter(function(c) { return c._ceoTransition != null; });
    var continuingCompanies = companies.filter(function(c) { return c._ceoTransition == null && c._ceoDataYears != null && c._ceoDataYears >= 2; });

    var html = '';

    // Total companies shown
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value accent">' + companies.length + '</span>';
    html += '<span class="summary-stat-label">companies</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    // CEO Transitions
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">CEO transitions</span>';
    html += '<span class="summary-stat-value" style="color:#fb923c">' + transitionCompanies.length + '</span>';
    html += '</span>';

    // Continuing CEOs
    if (continuingCompanies.length > 0) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Continuing CEOs</span>';
        html += '<span class="summary-stat-value">' + continuingCompanies.length + '</span>';
        html += '</span>';
    }

    if (transitionCompanies.length > 0) {
        html += '<span class="summary-divider"></span>';

        // New vs continuing CEO median comp
        var newComps = transitionCompanies.map(function(c) { return c.total_compensation || 0; }).filter(function(v) { return v > 0; });
        var contComps = continuingCompanies.map(function(c) { return c.total_compensation || 0; }).filter(function(v) { return v > 0; });
        if (newComps.length > 0 && contComps.length > 0) {
            var medNew = computeMedian(newComps);
            var medCont = computeMedian(contComps);
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">New CEO median</span>';
            html += '<span class="summary-stat-value">' + formatCurrency(medNew) + '</span>';
            html += '</span>';
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">Continuing CEO median</span>';
            html += '<span class="summary-stat-value">' + formatCurrency(medCont) + '</span>';
            html += '</span>';
        }

        // Most recent notable transition
        var sorted = transitionCompanies.slice().sort(function(a, b) { return (b.total_compensation || 0) - (a.total_compensation || 0); });
        if (sorted[0]) {
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">Highest-paid new CEO</span>';
            html += '<span class="summary-stat-value" style="color:#fb923c">' + sorted[0].ceo_name + ' (' + sorted[0].ticker + ') ' + formatCurrency(sorted[0].total_compensation) + '</span>';
            html += '</span>';
        }
    }

    return html;
}

function renderSummaryBar(filtered, allCompanies) {
    var bar = document.getElementById('table-summary-bar');
    if (!bar) return;

    // Show sort-contextual summary for non-default sorts, or filter summary when filtered
    var isFiltered = filtered.length !== allCompanies.length;
    if (!isFiltered) {
        // Show sort-contextual summary for certain sort keys even when unfiltered
        var sortCtx = renderSortContextSummary(filtered);
        if (sortCtx) {
            bar.innerHTML = sortCtx;
            return;
        }
        bar.innerHTML = '';
        return;
    }

    if (filtered.length === 0) {
        bar.innerHTML = '<span class="summary-stat"><span class="summary-stat-label">No companies match current filters</span></span>';
        return;
    }

    // Compute statistics — use role-specific comp when role filter is active
    var comps = filtered.map(function(c) { return getEffectiveComp(c); });
    var totalComp = comps.reduce(function(s, v) { return s + v; }, 0);
    var meanComp = totalComp / comps.length;
    var medianComp = computeMedian(comps);

    var ratios = filtered.filter(function(c) { return c.pay_ratio != null; }).map(function(c) { return c.pay_ratio; });
    var meanRatio = ratios.length > 0 ? Math.round(ratios.reduce(function(s, v) { return s + v; }, 0) / ratios.length) : null;
    var medianRatio = ratios.length > 0 ? Math.round(computeMedian(ratios)) : null;

    var workers = filtered.filter(function(c) { return c.median_worker_pay != null; }).map(function(c) { return c.median_worker_pay; });
    var medianWorker = workers.length > 0 ? computeMedian(workers) : null;

    // Count unique sectors
    var sectors = {};
    filtered.forEach(function(c) { if (c.sector) sectors[c.sector] = true; });
    var sectorCount = Object.keys(sectors).length;

    // Build HTML
    var html = '';

    // Combined filter indicator when 2+ filter dimensions are active
    var filterDims = 0;
    var filterParts = [];
    if (activeSector) { filterDims++; filterParts.push(activeSector); }
    if (window._activeDistFilter && !window._activeDistFilter.sector) { filterDims++; filterParts.push(window._activeDistFilter.label); }
    if (window._activeRatioBucket) {
        filterDims++;
        var rb = window._activeRatioBucket;
        filterParts.push('Ratio ' + rb.min + (rb.max === Infinity ? '+' : '–' + rb.max) + ':1');
    }
    if (searchTerm) { filterDims++; filterParts.push('"' + searchTerm + '"'); }
    if (window._activeConcTier) { filterDims++; filterParts.push(window._activeConcTier.tag + ' (' + window._activeConcTier.label + ')'); }
    if (window._activeCeoTransitionFilter) { filterDims++; filterParts.push('CEO Transitions'); }
    if (window._activeTeamCompletenessFilter) { filterDims++; filterParts.push(window._activeTeamCompletenessFilter === 'missing' ? 'Missing Roles' : 'Complete Teams'); }
    if (window._activeYoYBucket) { filterDims++; filterParts.push('YoY: ' + window._activeYoYBucket.label); }
    if (activeRole && activeRole !== 'CEO') { filterDims++; filterParts.push(activeRole + ' View'); }

    if (filterDims >= 2) {
        html += '<span class="summary-stat combined-filter-badge">';
        html += '<span class="combined-filter-icon">⧉</span>';
        html += '<span class="summary-stat-label">' + filterParts.join(' × ') + '</span>';
        html += '</span>';
        html += '<span class="summary-divider"></span>';
    }

    // Company count
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value accent">' + filtered.length + '</span>';
    html += '<span class="summary-stat-label">companies';
    if (sectorCount === 1) html += ' · ' + Object.keys(sectors)[0];
    else html += ' · ' + sectorCount + ' sectors';
    html += '</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    var compLabel = (activeRole && activeRole !== 'CEO') ? activeRole + ' comp' : 'comp';

    // Median Total Comp
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Median ' + compLabel + '</span>';
    html += '<span class="summary-stat-value">' + formatCurrency(medianComp) + '</span>';
    html += '</span>';

    // Mean Total Comp
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Mean</span>';
    html += '<span class="summary-stat-value">' + formatCurrency(meanComp) + '</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    // Median Pay Ratio
    if (medianRatio != null) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Median ratio</span>';
        html += '<span class="summary-stat-value">' + medianRatio.toLocaleString() + ':1</span>';
        html += '</span>';
    }

    // Mean Pay Ratio
    if (meanRatio != null) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Mean</span>';
        html += '<span class="summary-stat-value">' + meanRatio.toLocaleString() + ':1</span>';
        html += '</span>';
    }

    if (medianRatio != null || meanRatio != null) {
        html += '<span class="summary-divider"></span>';
    }

    // Median Worker Pay
    if (medianWorker != null) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Median worker pay</span>';
        html += '<span class="summary-stat-value">' + formatCompact(medianWorker) + '</span>';
        html += '</span>';
    }

    // Total combined compensation
    html += '<span class="summary-divider"></span>';
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Combined total</span>';
    html += '<span class="summary-stat-value">' + formatCurrency(totalComp) + '</span>';
    html += '</span>';

    // Append sort-contextual YoY stats when filtered AND sorted by YoY
    if (currentSort.key === '_ceoYoYSort') {
        var fYoY = filtered.filter(function(c) { return c._ceoYoY != null; });
        if (fYoY.length > 0) {
            var fInc = fYoY.filter(function(c) { return c._ceoYoY.pct > 0; }).length;
            var fDec = fYoY.filter(function(c) { return c._ceoYoY.pct < 0; }).length;
            var fYoYVals = fYoY.map(function(c) { return c._ceoYoY.pct; });
            var fMedianYoY = computeMedian(fYoYVals);
            var fmtPct = function(v) { var abs = Math.abs(v); return (abs >= 100 ? Math.round(abs) : abs.toFixed(1)) + '%'; };
            html += '<span class="summary-divider"></span>';
            html += '<span class="summary-stat"><span class="summary-stat-value positive">▲ ' + fInc + '</span><span class="summary-stat-label">up</span></span>';
            html += '<span class="summary-stat"><span class="summary-stat-value negative">▼ ' + fDec + '</span><span class="summary-stat-label">down</span></span>';
            html += '<span class="summary-stat"><span class="summary-stat-label">Median Δ</span><span class="summary-stat-value ' + (fMedianYoY >= 0 ? 'positive' : 'negative') + '">' + (fMedianYoY >= 0 ? '+' : '\u2212') + fmtPct(fMedianYoY) + '</span></span>';
        }
    }

    // Append sort-contextual Stock % stats when filtered AND sorted by Stock %
    if (currentSort.key === '_ceoStockPctSort') {
        var fSP = filtered.filter(function(c) { return c._ceoStockPct != null; });
        if (fSP.length > 0) {
            var fAbove80 = fSP.filter(function(c) { return c._ceoStockPct >= 80; }).length;
            var fBelow20 = fSP.filter(function(c) { return c._ceoStockPct < 20; }).length;
            var fSPVals = fSP.map(function(c) { return c._ceoStockPct; });
            var fMedianSP = Math.round(computeMedian(fSPVals) * 10) / 10;
            html += '<span class="summary-divider"></span>';
            html += '<span class="summary-stat"><span class="summary-stat-value stock-pct-high">' + fAbove80 + '</span><span class="summary-stat-label">≥80%</span></span>';
            html += '<span class="summary-stat"><span class="summary-stat-value stock-pct-low">' + fBelow20 + '</span><span class="summary-stat-label">&lt;20%</span></span>';
            html += '<span class="summary-stat"><span class="summary-stat-label">Median</span><span class="summary-stat-value">' + fMedianSP + '%</span></span>';
        }
    }

    // Append CEO Concentration stats when filtered AND sorted by concentration
    if (currentSort.key === '_ceoConcPct') {
        var fConc = filtered.filter(function(c) { return c._ceoConcPct != null; });
        if (fConc.length > 0) {
            var fAbove50 = fConc.filter(function(c) { return c._ceoConcPct >= 50; }).length;
            var fBelow35 = fConc.filter(function(c) { return c._ceoConcPct < 35; }).length;
            var fConcVals = fConc.map(function(c) { return c._ceoConcPct; });
            var fMedianConc = Math.round(computeMedian(fConcVals) * 10) / 10;
            html += '<span class="summary-divider"></span>';
            html += '<span class="summary-stat"><span class="summary-stat-value conc-high-text">' + fAbove50 + '</span><span class="summary-stat-label">≥50%</span></span>';
            html += '<span class="summary-stat"><span class="summary-stat-value conc-low-text">' + fBelow35 + '</span><span class="summary-stat-label">&lt;35%</span></span>';
            html += '<span class="summary-stat"><span class="summary-stat-label">Median</span><span class="summary-stat-value">' + fMedianConc + '%</span></span>';
        }
    }

    // Append sector-vs-benchmark context when a sector filter is active
    if (activeSector && filtered.length > 0) {
        // Compute S&P 500 wide stats for comparison
        var allComps = allCompanies.filter(function(c) { return c.total_compensation > 0; }).map(function(c) { return c.total_compensation; });
        var allMedian = computeMedian(allComps.slice().sort(function(a, b) { return a - b; }));

        // Sector-specific stats (from filtered set since activeSector is already applied)
        var sectorComps = comps.slice().sort(function(a, b) { return a - b; });
        var sectorMedian = computeMedian(sectorComps);
        var deltaVsBenchmark = ((sectorMedian - allMedian) / allMedian * 100);
        var deltaSign = deltaVsBenchmark >= 0 ? '+' : '\u2212';
        var deltaClass = deltaVsBenchmark >= 0 ? 'positive' : 'negative';

        // Sector rank by median CEO pay
        var sectorMap = {};
        allCompanies.forEach(function(c) {
            var s = c.sector || 'Unknown';
            if (!sectorMap[s]) sectorMap[s] = [];
            var cv = (activeRole && activeRole !== 'CEO' && c._roleViewComp != null) ? c._roleViewComp : (c.total_compensation || 0);
            if (cv > 0) sectorMap[s].push(cv);
        });
        var sectorRanking = Object.keys(sectorMap).map(function(s) {
            var sorted = sectorMap[s].slice().sort(function(a, b) { return a - b; });
            return { name: s, median: computeMedian(sorted) };
        }).sort(function(a, b) { return b.median - a.median; });
        var sectorRank = sectorRanking.findIndex(function(s) { return s.name === activeSector; }) + 1;

        // Sector equity stats
        var sectorEqPcts = filtered.filter(function(c) { return c._ceoStockPct != null; }).map(function(c) { return c._ceoStockPct; });
        var sectorMedianEq = sectorEqPcts.length > 0 ? Math.round(computeMedian(sectorEqPcts.slice().sort(function(a, b) { return a - b; })) * 10) / 10 : null;

        html += '<span class="summary-divider"></span>';

        // Sector rank badge
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Sector rank</span>';
        html += '<span class="summary-stat-value" style="color:' + getSectorColor(activeSector) + '">#' + sectorRank + ' of ' + sectorRanking.length + '</span>';
        html += '</span>';

        // vs S&P 500 median
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">vs S&P 500</span>';
        html += '<span class="summary-stat-value ' + deltaClass + '">' + deltaSign + Math.abs(deltaVsBenchmark).toFixed(1) + '%</span>';
        html += '</span>';

        // Sector median equity %
        if (sectorMedianEq != null) {
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">Equity %</span>';
            html += '<span class="summary-stat-value">' + sectorMedianEq + '%</span>';
            html += '</span>';
        }
    }

    // CEO Transition filter summary stats
    if (window._activeCeoTransitionFilter && filtered.length > 0) {
        html += '<span class="summary-divider"></span>';
        // Median transition comp
        var transComps = filtered.map(function(c) { return getEffectiveComp(c); }).filter(function(v) { return v > 0; }).sort(function(a, b) { return a - b; });
        if (transComps.length > 0) {
            var medTransComp = transComps[Math.floor(transComps.length / 2)];
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">Median (new CEOs)</span>';
            html += '<span class="summary-stat-value">' + formatCurrency(medTransComp) + '</span>';
            html += '</span>';
        }
        // Count by transition year
        var transYears = {};
        filtered.forEach(function(c) {
            if (c._ceoTransition) {
                var yr = c._ceoTransition.newCeo.year;
                transYears[yr] = (transYears[yr] || 0) + 1;
            }
        });
        var transYearKeys = Object.keys(transYears).sort();
        if (transYearKeys.length > 0) {
            var yearParts = transYearKeys.map(function(y) { return 'FY' + y + ': ' + transYears[y]; });
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">By Year</span>';
            html += '<span class="summary-stat-value" style="color:#fb923c">' + yearParts.join(', ') + '</span>';
            html += '</span>';
        }
        // Highest paid new CEO
        var topNew = filtered.slice().sort(function(a, b) { return getEffectiveComp(b) - getEffectiveComp(a); })[0];
        if (topNew) {
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">Highest Paid</span>';
            html += '<span class="summary-stat-value">' + (topNew.ceo_name || 'N/A') + ' (' + topNew.ticker + ') ' + formatCurrency(getEffectiveComp(topNew)) + '</span>';
            html += '</span>';
        }

        // Sector distribution histogram — mini bar chart showing transition count by sector
        var transSectorMap = {};
        filtered.forEach(function(c) {
            var s = c.sector || 'Unknown';
            transSectorMap[s] = (transSectorMap[s] || 0) + 1;
        });
        var transSectors = Object.keys(transSectorMap).map(function(k) {
            return { name: k, count: transSectorMap[k] };
        }).sort(function(a, b) { return b.count - a.count; });
        var transMaxCount = transSectors.length > 0 ? transSectors[0].count : 1;

        if (transSectors.length > 1) {
            html += '<span class="summary-divider"></span>';
            html += '<span class="summary-stat sector-sort-dist">';
            html += '<span class="summary-stat-label">By Sector</span>';
            html += '<span class="sector-sort-bars">';
            transSectors.forEach(function(s) {
                var barH = Math.max(3, Math.round(s.count / transMaxCount * 24));
                var color = getSectorColor(s.name);
                var isActive = (activeSector === s.name);
                var isDimmed = (activeSector && !isActive);
                var dimStyle = isDimmed ? 'opacity:0.3;' : '';
                var activeOutline = isActive ? 'outline:2px solid ' + color + ';outline-offset:2px;border-radius:3px;' : '';
                var escapedName = s.name.replace(/'/g, "\\'");
                html += '<span class="sector-sort-bar-group clickable-bar' + (isActive ? ' active-bracket' : '') + '" title="' + s.name + ': ' + s.count + ' CEO transition' + (s.count > 1 ? 's' : '') + ' — click to ' + (isActive ? 'clear sector' : 'filter to ' + s.name) + '" onclick="filterBySectorFromBar(\'' + escapedName + '\')" style="cursor:pointer;' + activeOutline + '">';
                html += '<span class="sector-sort-bar" style="height:' + barH + 'px;background:' + color + ';' + dimStyle + '"></span>';
                html += '<span class="sector-sort-bar-count" style="' + dimStyle + '">' + s.count + '</span>';
                html += '</span>';
            });
            html += '</span>';
            html += '</span>';
        }
    }

    // Team Completeness filter summary stats
    if (window._activeTeamCompletenessFilter && filtered.length > 0) {
        html += '<span class="summary-divider"></span>';
        if (window._activeTeamCompletenessFilter === 'missing') {
            // Count by missing role type
            var missingRoleCounts = {};
            filtered.forEach(function(c) {
                if (c._teamMissingExpected) {
                    c._teamMissingExpected.forEach(function(r) {
                        missingRoleCounts[r] = (missingRoleCounts[r] || 0) + 1;
                    });
                }
            });
            var missingParts = Object.keys(missingRoleCounts).map(function(r) {
                return r + ': ' + missingRoleCounts[r];
            });
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">Missing roles</span>';
            html += '<span class="summary-stat-value" style="color:#f472b6">' + missingParts.join(', ') + '</span>';
            html += '</span>';
            // Average role count in filtered set
            var avgFiltered = filtered.reduce(function(s, c) { return s + (c._teamRoleCount || 0); }, 0) / filtered.length;
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">Avg roles</span>';
            html += '<span class="summary-stat-value">' + avgFiltered.toFixed(1) + '/7</span>';
            html += '</span>';
            // Least complete company
            var leastComplete = filtered.slice().sort(function(a, b) { return (a._teamRoleCount || 0) - (b._teamRoleCount || 0); })[0];
            if (leastComplete) {
                html += '<span class="summary-stat">';
                html += '<span class="summary-stat-label">Least complete</span>';
                html += '<span class="summary-stat-value">' + (leastComplete.ticker || 'N/A') + ' (' + (leastComplete._teamRoleCount || 0) + ' roles)</span>';
                html += '</span>';
            }
        } else {
            // 'complete' mode — show companies with 4+ roles
            var avgComplete = filtered.reduce(function(s, c) { return s + (c._teamRoleCount || 0); }, 0) / filtered.length;
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">Avg roles</span>';
            html += '<span class="summary-stat-value positive">' + avgComplete.toFixed(1) + '/7</span>';
            html += '</span>';
            var mostComp = filtered.slice().sort(function(a, b) { return (b._teamRoleCount || 0) - (a._teamRoleCount || 0); })[0];
            if (mostComp) {
                html += '<span class="summary-stat">';
                html += '<span class="summary-stat-label">Most complete</span>';
                html += '<span class="summary-stat-value">' + (mostComp.ticker || 'N/A') + ' (' + (mostComp._teamRoleCount || 0) + ' roles)</span>';
                html += '</span>';
            }
        }
    }

    // Role filter summary stats
    if (activeRole && activeRole !== 'CEO' && filtered.length > 0) {
        html += '<span class="summary-divider"></span>';
        // Role context label
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Viewing</span>';
        html += '<span class="summary-stat-value" style="color:' + ROLE_COLORS[activeRole] + '">' + activeRole + 's across ' + filtered.length + ' companies</span>';
        html += '</span>';
        // Median role comp
        var roleComps = filtered.map(function(c) { return c._roleViewComp || 0; }).filter(function(v) { return v > 0; }).sort(function(a, b) { return a - b; });
        if (roleComps.length > 0) {
            var medRoleComp = roleComps[Math.floor(roleComps.length / 2)];
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">Median ' + activeRole + '</span>';
            html += '<span class="summary-stat-value">' + formatCurrency(medRoleComp) + '</span>';
            html += '</span>';
        }
        // CEO:Role ratio
        if (_roleBenchmarks && _roleBenchmarks['CEO'] && _roleBenchmarks[activeRole]) {
            var ceoMed = _roleBenchmarks['CEO'].median;
            var roleMed = _roleBenchmarks[activeRole].median;
            if (roleMed > 0) {
                var ratio = (ceoMed / roleMed).toFixed(1);
                html += '<span class="summary-stat">';
                html += '<span class="summary-stat-label">CEO/' + activeRole + '</span>';
                html += '<span class="summary-stat-value">' + ratio + '×</span>';
                html += '</span>';
            }
        }
        // Top earner for this role
        var topRole = filtered.slice().sort(function(a, b) { return (b._roleViewComp || 0) - (a._roleViewComp || 0); })[0];
        if (topRole && topRole._roleExecs && topRole._roleExecs[activeRole]) {
            html += '<span class="summary-stat">';
            html += '<span class="summary-stat-label">Highest Paid</span>';
            html += '<span class="summary-stat-value">' + topRole._roleExecs[activeRole].name + ' (' + topRole.ticker + ') ' + formatCurrency(topRole._roleViewComp) + '</span>';
            html += '</span>';
        }
    }

    bar.innerHTML = html;
}

/* _lastTableAnnounce: stores the last renderTable announce message for callers that suppress and combine */
var _lastTableAnnounce = '';

function renderTable(companies, options) {
    computeOutliers(companies);

    var filtered = companies.slice();

    if (activeSector) {
        filtered = filtered.filter(function(c) { return c.sector === activeSector; });
    }
    if (searchTerm) {
        var q = searchTerm.toLowerCase();
        filtered = filtered.filter(function(c) {
            if ((c.ticker || '').toLowerCase().indexOf(q) >= 0 ||
                (c.company_name || '').toLowerCase().indexOf(q) >= 0 ||
                (c.ceo_name || '').toLowerCase().indexOf(q) >= 0 ||
                (c.sector || '').toLowerCase().indexOf(q) >= 0) return true;
            // Also search NEO names when EDGAR data is available
            if (c.executives) {
                for (var ei = 0; ei < c.executives.length; ei++) {
                    if (c.executives[ei].name && c.executives[ei].name.toLowerCase().indexOf(q) >= 0) return true;
                }
            }
            return false;
        });
    }
    if (window._activeRatioBucket) {
        var rb = window._activeRatioBucket;
        filtered = filtered.filter(function(c) {
            return c.pay_ratio != null && c.pay_ratio >= rb.min && c.pay_ratio < rb.max;
        });
    }
    if (window._activeDistFilter) {
        var df = window._activeDistFilter;
        filtered = filtered.filter(function(c) {
            return c.total_compensation != null && c.total_compensation >= df.min && c.total_compensation <= df.max;
        });
    }
    if (window._activeConcTier) {
        var ct = window._activeConcTier;
        filtered = filtered.filter(function(c) {
            return c._ceoConcPct != null && c._ceoConcPct >= ct.min && c._ceoConcPct < ct.max;
        });
    }
    if (window._activeCeoTransitionFilter) {
        filtered = filtered.filter(function(c) {
            return c._ceoTransition != null;
        });
    }
    if (window._activeTeamCompletenessFilter) {
        if (window._activeTeamCompletenessFilter === 'missing') {
            filtered = filtered.filter(function(c) {
                return c._teamMissingExpected && c._teamMissingExpected.length > 0 && c.executives && c.executives.length > 0;
            });
        } else if (window._activeTeamCompletenessFilter === 'complete') {
            filtered = filtered.filter(function(c) {
                return c._teamRoleCount >= 4;
            });
        }
    }
    if (window._activeYoYBucket) {
        var yb = window._activeYoYBucket;
        filtered = filtered.filter(function(c) {
            if (!c._ceoYoY || c._ceoYoY.pctChange == null || !isFinite(c._ceoYoY.pctChange)) return false;
            var pct = c._ceoYoY.pctChange;
            if (yb.max === Infinity) return pct >= yb.min;
            if (yb.min === -Infinity) return pct < yb.max;
            return pct >= yb.min && pct < yb.max;
        });
    }

    // Role filter: filter to companies with that role + compute role-specific sort value
    if (activeRole && activeRole !== 'CEO') {
        filtered = filtered.filter(function(c) {
            return c._roleExecs && c._roleExecs[activeRole];
        });
        // Set temporary _roleViewComp for sorting
        filtered.forEach(function(c) {
            var re = c._roleExecs[activeRole];
            c._roleViewComp = re ? (re.total || 0) : 0;
        });
    } else {
        // Clear role view data
        filtered.forEach(function(c) { c._roleViewComp = null; });
    }

    // Render summary statistics bar
    renderSummaryBar(filtered, companies);

    filtered.sort(function(a, b) {
        var sortKey = currentSort.key;
        // When role filter is active and sorting by comp or rank, use role-specific comp
        if (activeRole && activeRole !== 'CEO' && (sortKey === 'total_compensation' || sortKey === 'rank')) {
            var av = a._roleViewComp != null ? a._roleViewComp : 0;
            var bv = b._roleViewComp != null ? b._roleViewComp : 0;
            if (av < bv) return currentSort.dir === 'asc' ? -1 : 1;
            if (av > bv) return currentSort.dir === 'asc' ? 1 : -1;
            return 0;
        }
        var av = a[sortKey];
        var bv = b[sortKey];
        if (av == null) av = currentSort.dir === 'asc' ? Infinity : -Infinity;
        if (bv == null) bv = currentSort.dir === 'asc' ? Infinity : -Infinity;
        if (typeof av === 'string') av = av.toLowerCase();
        if (typeof bv === 'string') bv = bv.toLowerCase();
        if (av < bv) return currentSort.dir === 'asc' ? -1 : 1;
        if (av > bv) return currentSort.dir === 'asc' ? 1 : -1;
        return 0;
    });

    // Pagination
    var totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;
    var startIdx = (currentPage - 1) * PAGE_SIZE;
    var pageItems = filtered.slice(startIdx, startIdx + PAGE_SIZE);

    var tbody = document.getElementById('comp-tbody');
    tbody.innerHTML = '';

    // Compute max compensation in filtered view for inline data bars
    var maxFilteredComp = 0;
    if (activeRole && activeRole !== 'CEO') {
        filtered.forEach(function(c) { if ((c._roleViewComp || 0) > maxFilteredComp) maxFilteredComp = c._roleViewComp; });
    } else {
        filtered.forEach(function(c) { if (c.total_compensation > maxFilteredComp) maxFilteredComp = c.total_compensation; });
    }

    // When role filter is active, compute role-specific benchmarks for the filtered set
    var _roleFilterMedian = null;
    if (activeRole && activeRole !== 'CEO' && _roleBenchmarks && _roleBenchmarks[activeRole]) {
        _roleFilterMedian = _roleBenchmarks[activeRole].median;
    }

    pageItems.forEach(function(c, i) {
        var globalIdx = startIdx + i;
        var tr = document.createElement('tr');

        // Determine display values based on role filter
        var isRolePivot = activeRole && activeRole !== 'CEO';
        var displayComp = isRolePivot ? (c._roleViewComp || 0) : (c.total_compensation || 0);
        var roleExec = isRolePivot && c._roleExecs ? c._roleExecs[activeRole] : null;
        var displayName = isRolePivot && roleExec ? roleExec.name : c.ceo_name;
        var displayTitle = isRolePivot && roleExec ? roleExec.title : null;

        // Compensation value with inline data bar + optional top-10 badge
        var barPct = maxFilteredComp > 0 ? Math.max(0, Math.min(100, displayComp / maxFilteredComp * 100)) : 0;
        var compHtml = '<div class="comp-bar-cell"><div class="comp-bar" style="width:' + barPct.toFixed(1) + '%"></div><span class="comp-value">' + formatCurrency(displayComp) + '</span>';
        if (!isRolePivot && c.neo_count) {
            compHtml += ' <span class="neo-badge" title="' + c.neo_count + ' Named Executive Officers from SEC EDGAR">' + c.neo_count + ' NEOs</span>';
        }
        if (!isRolePivot && _outlierTop10[c.ticker]) {
            compHtml += ' <span class="outlier-badge top-comp" title="Top 10 highest paid CEO in S&amp;P 500">#' + _outlierTop10[c.ticker] + '</span>';
        }
        // Role benchmark badge when in role view
        if (isRolePivot && _roleFilterMedian && displayComp > 0) {
            var roleDelta = ((displayComp - _roleFilterMedian) / _roleFilterMedian * 100).toFixed(0);
            var roleDeltaCls = parseInt(roleDelta) >= 0 ? 'positive' : 'negative';
            var roleDeltaSign = parseInt(roleDelta) >= 0 ? '+' : '';
            compHtml += ' <span class="neo-role-badge ' + roleDeltaCls + '" title="' + roleDeltaSign + roleDelta + '% vs S&amp;P 500 ' + activeRole + ' median (' + formatCurrency(_roleFilterMedian) + ')">' + roleDeltaSign + roleDelta + '%</span>';
        }
        compHtml += '</div>';

        // YoY cell (separate column) with inline sparkline for multi-year trend
        var yoyCell = '\u2014';
        if (c._ceoYoY) {
            var yoy = c._ceoYoY;
            var isPos = yoy.pct >= 0;
            var yoyAbs = Math.abs(yoy.pct);
            var yoyStr = yoyAbs >= 100 ? Math.round(yoyAbs) + '%' : yoyAbs.toFixed(1) + '%';
            var yoyArrow = isPos ? '▲' : '▼';
            var yoySign = isPos ? '+' : '\u2212';
            var yoyCls = isPos ? 'positive' : 'negative';
            var yoyTitle = 'CEO comp ' + (isPos ? '+' : '-') + yoyStr + ' vs FY' + yoy.fromYear + ' (' + formatCurrency(yoy.fromComp) + ' \u2192 ' + formatCurrency(yoy.toComp) + ')';

            // Build sparkline SVG if multi-year trend data exists (≥2 points)
            var sparkSvg = '';
            if (c._ceoTrend && c._ceoTrend.length >= 2) {
                var sparkW = 36, sparkH = 14, sparkPad = 1;
                var trendPts = c._ceoTrend;
                var tMin = Math.min.apply(null, trendPts.map(function(d) { return d.total; }));
                var tMax = Math.max.apply(null, trendPts.map(function(d) { return d.total; }));
                var tRange = tMax - tMin || 1;
                var sparkPoints = [];
                trendPts.forEach(function(d, di) {
                    var sx = sparkPad + di / (trendPts.length - 1) * (sparkW - sparkPad * 2);
                    var sy = sparkPad + (1 - (d.total - tMin) / tRange) * (sparkH - sparkPad * 2);
                    sparkPoints.push(sx.toFixed(1) + ',' + sy.toFixed(1));
                });
                var sparkLine = sparkPoints.join(' ');
                // Area fill: close path along bottom
                var sparkArea = sparkPoints[0].split(',')[0] + ',' + (sparkH - sparkPad) + ' ' + sparkLine + ' ' + sparkPoints[sparkPoints.length - 1].split(',')[0] + ',' + (sparkH - sparkPad);
                var sparkColor = isPos ? 'var(--positive)' : 'var(--negative)';
                var sparkFill = isPos ? 'rgba(6,214,160,0.15)' : 'rgba(239,71,111,0.15)';
                // Sparkline tooltip: show year range
                var sparkTitle = 'FY' + trendPts[0].year + '\u2013' + trendPts[trendPts.length - 1].year + ': ' + trendPts.map(function(d) { return formatCurrency(d.total); }).join(' \u2192 ');
                sparkSvg = '<svg class="yoy-spark-svg" width="' + sparkW + '" height="' + sparkH + '" viewBox="0 0 ' + sparkW + ' ' + sparkH + '" aria-hidden="true" title="' + sparkTitle.replace(/"/g, '&quot;') + '"><polygon points="' + sparkArea + '" fill="' + sparkFill + '"/><polyline points="' + sparkLine + '" fill="none" stroke="' + sparkColor + '" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
            }

            yoyCell = '<span class="yoy-cell-wrap">' + sparkSvg + '<span class="yoy-inline ' + yoyCls + '" title="' + yoyTitle.replace(/"/g, '&quot;') + '">' + yoyArrow + ' ' + yoySign + yoyStr + '</span></span>';
        }

        // Pay ratio with color class + optional extreme badge
        var ratioClass = c.pay_ratio > 2000 ? 'ratio-high' : c.pay_ratio > 500 ? 'ratio-mid' : 'ratio-low';
        var ratioHtml = '';
        if (c.pay_ratio != null && c.pay_ratio > 0) {
            ratioHtml = '<span class="' + ratioClass + '">' + formatRatio(c.pay_ratio) + '</span>';
            if (c.pay_ratio > 2000) {
                ratioHtml += ' <span class="outlier-badge extreme-ratio" title="Extreme pay ratio: CEO earns ' + c.pay_ratio.toLocaleString() + 'x the median worker">!</span>';
            } else if (c.pay_ratio > 1000) {
                ratioHtml += ' <span class="outlier-badge high-ratio" title="High pay ratio: CEO earns ' + c.pay_ratio.toLocaleString() + 'x the median worker">!</span>';
            } else if (_outlierLowRatio[c.ticker]) {
                ratioHtml += ' <span class="outlier-badge low-ratio" title="Most equitable: bottom 5 pay ratio in S&amp;P 500">✓</span>';
            }
        } else {
            ratioHtml = getMissingDataHtml(c.ticker, 'pay_ratio');
        }

        var workerCell = c.median_worker_pay ? formatCompact(c.median_worker_pay) : getMissingDataHtml(c.ticker, 'median_worker_pay');

        // Stock % cell
        var stockPctCell = '\u2014';
        if (c._ceoStockPct != null) {
            var spVal = c._ceoStockPct;
            var spCls = spVal >= 80 ? 'stock-pct-high' : spVal >= 50 ? 'stock-pct-mid' : 'stock-pct-low';
            var spTitle = 'CEO equity (stock + options) = ' + spVal.toFixed(1) + '% of total comp';
            stockPctCell = '<span class="stock-pct-badge ' + spCls + '" title="' + spTitle + '">' + Math.round(spVal) + '%</span>';
        }

        var isCompared = window._compareSet && window._compareSet.indexOf(c.ticker) >= 0;
        var compareBtnHtml = '<button class="compare-btn' + (isCompared ? ' selected' : '') + '" data-ticker="' + c.ticker + '" title="' + (isCompared ? 'Remove from comparison' : 'Add to comparison') + '">' + (isCompared ? '✓' : '+') + '</button>';

        // Name cell: show role exec name + title badge when in role view, CEO name + transition badge otherwise
        var nameCellHtml;
        if (isRolePivot && roleExec) {
            nameCellHtml = displayName + ' <span class="role-title-badge" style="color:' + ROLE_COLORS[activeRole] + '" title="' + (displayTitle || activeRole).replace(/"/g, '&quot;') + '">' + activeRole + '</span>';
        } else {
            nameCellHtml = c.ceo_name + (c._ceoTransition ? ' <span class="new-ceo-badge new-ceo-badge-clickable" title="CEO transition: succeeded ' + c._ceoTransition.oldCeo.name.replace(/"/g, '&quot;') + ' after FY' + c._ceoTransition.oldCeo.year + ' \u2014 click to filter" onclick="event.stopPropagation();if(window.filterByCeoTransition)window.filterByCeoTransition()">NEW</span>' : '');
        }

        tr.innerHTML = '<td>' + (globalIdx + 1) + ' ' + compareBtnHtml + '</td>' +
            '<td><span class="ticker">' + c.ticker + '</span></td>' +
            '<td><span class="company">' + c.company_name + '</span></td>' +
            '<td>' + nameCellHtml + '</td>' +
            '<td>' + compHtml + '</td>' +
            '<td class="yoy-cell">' + yoyCell + '</td>' +
            '<td class="stock-pct-cell">' + stockPctCell + '</td>' +
            '<td class="pctile-cell">' + (function() {
                if (c._compPercentile == null) return '\u2014';
                var pl = getPercentileLabel(c._compPercentile);
                var pc = getPercentileClass(c._compPercentile);
                return '<span class="pctile-badge ' + pc + '" title="Compensation percentile: ' + c._compPercentile + ' of 100">' + pl + '</span>';
            })() + '</td>' +
            '<td class="conc-cell">' + (function() {
                if (c._ceoConcPct == null) return '\u2014';
                var cp = c._ceoConcPct;
                var cc = cp >= 50 ? 'conc-high' : cp >= 35 ? 'conc-mid' : 'conc-low';
                var cl = cp >= 50 ? 'Concentrated' : cp >= 35 ? 'Moderate' : 'Distributed';
                var cMin = cp >= 50 ? 50 : cp >= 35 ? 35 : 0;
                var cMax = cp >= 50 ? 101 : cp >= 35 ? 50 : 35;
                var cLbl = cp >= 50 ? '≥50%' : cp >= 35 ? '35–49%' : '<35%';
                var tt = 'CEO earns ' + cp.toFixed(1) + '% of total NEO compensation (' + cl + ') — click to filter';
                if (c._ceoPremiumRatio != null) tt += ' — ' + c._ceoPremiumRatio.toFixed(1) + '× the #2 executive';
                return '<span class="conc-badge ' + cc + ' conc-badge-clickable" title="' + tt + '" onclick="event.stopPropagation();filterByConcTier(' + cMin + ',' + cMax + ',\'' + cl + '\',\'' + cLbl.replace("'","\\'") + '\')">' + Math.round(cp) + '%</span>';
            })() + '</td>' +
            '<td>' + (c.sector || '\u2014') + '</td>' +
            '<td>' + ratioHtml + '</td>' +
            '<td>' + workerCell + '</td>';

        // Make row keyboard-accessible for detail panel expansion
        tr.setAttribute('tabindex', '0');

        // Wire up compare button click
        var cBtn = tr.querySelector('.compare-btn');
        if (cBtn) {
            cBtn.addEventListener('click', function(e) {
                if (window._toggleCompare) window._toggleCompare(this.dataset.ticker, e);
            });
        }

        tbody.appendChild(tr);
    });

    // Footer with pagination controls
    var footerEl = document.getElementById('table-footer');
    footerEl.innerHTML = '';

    var footerText = document.createElement('span');
    footerText.className = 'table-footer-text';
    footerText.textContent = 'Showing ' + (startIdx + 1) + '–' + Math.min(startIdx + PAGE_SIZE, filtered.length) + ' of ' + filtered.length + ' companies';
    if (filtered.length < companies.length) footerText.textContent += ' (filtered from ' + companies.length + ')';
    footerEl.appendChild(footerText);

    // ARIA announcement for filter/page changes
    var announceMsg = 'Showing ' + (startIdx + 1) + ' to ' + Math.min(startIdx + PAGE_SIZE, filtered.length) + ' of ' + filtered.length + ' companies';
    if (activeSector) announceMsg += ', filtered to ' + activeSector;
    if (searchTerm) announceMsg += ', search: ' + searchTerm;
    if (window._activeRatioBucket) announceMsg += ', pay ratio filter active';
    if (window._activeDistFilter) announceMsg += ', ' + window._activeDistFilter.label;
    if (window._activeConcTier) announceMsg += ', concentration: ' + window._activeConcTier.tag;
    if (window._activeCeoTransitionFilter) announceMsg += ', CEO transitions only';
    if (window._activeTeamCompletenessFilter) announceMsg += ', ' + (window._activeTeamCompletenessFilter === 'missing' ? 'missing expected roles' : 'complete teams');
    if (window._activeYoYBucket) announceMsg += ', YoY: ' + window._activeYoYBucket.label;
    if (activeRole && activeRole !== 'CEO') announceMsg += ', viewing ' + activeRole + ' role';
    if (totalPages > 1) announceMsg += '. Page ' + currentPage + ' of ' + totalPages;
    _lastTableAnnounce = announceMsg;
    if (!options || !options.suppressAnnounce) announce(announceMsg);

    if (totalPages > 1) {
        var paginationDiv = document.createElement('div');
        paginationDiv.className = 'pagination';

        var prevBtn = document.createElement('button');
        prevBtn.className = 'pagination-btn' + (currentPage <= 1 ? ' disabled' : '');
        prevBtn.textContent = '← Prev';
        prevBtn.disabled = currentPage <= 1;
        prevBtn.addEventListener('click', function() {
            if (currentPage > 1) { currentPage--; renderTable(companies); scrollToTable(); }
        });
        paginationDiv.appendChild(prevBtn);

        // Page numbers — show max 7 page buttons on desktop, fewer on narrow screens
        var maxVisiblePages = window.innerWidth <= 480 ? 5 : 7;
        var pageNums = buildPageNumbers(currentPage, totalPages, maxVisiblePages);
        pageNums.forEach(function(p) {
            if (p === '...') {
                var ellipsis = document.createElement('span');
                ellipsis.className = 'pagination-ellipsis';
                ellipsis.textContent = '…';
                paginationDiv.appendChild(ellipsis);
            } else {
                var pageBtn = document.createElement('button');
                pageBtn.className = 'pagination-btn pagination-num' + (p === currentPage ? ' active' : '');
                pageBtn.textContent = p;
                pageBtn.addEventListener('click', (function(pg) {
                    return function() { currentPage = pg; renderTable(companies); scrollToTable(); };
                })(p));
                paginationDiv.appendChild(pageBtn);
            }
        });

        var nextBtn = document.createElement('button');
        nextBtn.className = 'pagination-btn' + (currentPage >= totalPages ? ' disabled' : '');
        nextBtn.textContent = 'Next →';
        nextBtn.disabled = currentPage >= totalPages;
        nextBtn.addEventListener('click', function() {
            if (currentPage < totalPages) { currentPage++; renderTable(companies); scrollToTable(); }
        });
        paginationDiv.appendChild(nextBtn);

        footerEl.appendChild(paginationDiv);
    }

    footerEl.appendChild(document.createTextNode(' · Click any row for details'));

    // Persist state to URL hash
    pushState();
}

function buildPageNumbers(current, total, maxVisible) {
    if (total <= maxVisible) {
        var arr = [];
        for (var i = 1; i <= total; i++) arr.push(i);
        return arr;
    }
    var pages = [1];
    var startPage = Math.max(2, current - 1);
    var endPage = Math.min(total - 1, current + 1);
    // Ensure at least 3 middle pages
    if (current <= 3) { startPage = 2; endPage = Math.min(total - 1, 4); }
    if (current >= total - 2) { startPage = Math.max(2, total - 3); endPage = total - 1; }
    if (startPage > 2) pages.push('...');
    for (var j = startPage; j <= endPage; j++) pages.push(j);
    if (endPage < total - 1) pages.push('...');
    pages.push(total);
    return pages;
}

function scrollToTable() {
    var section = document.getElementById('compensation-table-section');
    if (section) {
        var stickyH = getStickyOffset();
        var sectionTop = section.getBoundingClientRect().top + window.scrollY - stickyH - 8;
        window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
    }
}

function setupSorting(companies) {
    function activateSort(th) {
        var key = th.dataset.sort;
        if (key === 'rank') {
            currentSort = { key: 'total_compensation', dir: 'desc' };
        } else if (currentSort.key === key) {
            currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort = { key: key, dir: typeof companies[0][key] === 'string' ? 'asc' : 'desc' };
        }
        currentPage = 1;
        document.querySelectorAll('th.sortable').forEach(function(t) {
            t.classList.remove('sorted-asc', 'sorted-desc');
            t.setAttribute('aria-sort', 'none');
        });
        th.classList.add(currentSort.dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
        th.setAttribute('aria-sort', currentSort.dir === 'asc' ? 'ascending' : 'descending');
        var sortLabel = th.textContent.replace(/[↑↓▲▼]/g, '').trim();
        renderTable(companies, { suppressAnnounce: true });
        announce('Table sorted by ' + sortLabel + ', ' + (currentSort.dir === 'asc' ? 'ascending' : 'descending') + '. ' + _lastTableAnnounce);
    }
    document.querySelectorAll('th.sortable').forEach(function(th) {
        th.addEventListener('click', function() { activateSort(th); });
        th.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                activateSort(th);
            }
        });
    });
}

function setupSearch(companies) {
    var searchInput = document.getElementById('table-search');
    var searchResultsEl = document.getElementById('table-search-results');
    var tsrActiveIdx = -1;
    var _tsrDebounce = null;

    function renderSearchSuggestions(query) {
        if (!searchResultsEl) return;
        searchResultsEl.innerHTML = '';
        tsrActiveIdx = -1;

        if (!query || query.length === 0) {
            searchResultsEl.classList.remove('visible');
            return;
        }

        var q = query.toLowerCase();

        // Match against ticker, company name, CEO name
        var matches = companies.filter(function(c) {
            return (c.ticker || '').toLowerCase().indexOf(q) >= 0 ||
                (c.company_name || '').toLowerCase().indexOf(q) >= 0 ||
                (c.ceo_name || '').toLowerCase().indexOf(q) >= 0;
        });

        // Smart sort: exact ticker → ticker starts-with → company starts-with → CEO starts-with → contains
        matches.sort(function(a, b) {
            var at = (a.ticker || '').toLowerCase();
            var bt = (b.ticker || '').toLowerCase();
            // Exact ticker match
            if (at === q && bt !== q) return -1;
            if (bt === q && at !== q) return 1;
            // Ticker starts with query
            var aTS = at.indexOf(q) === 0 ? 0 : 1;
            var bTS = bt.indexOf(q) === 0 ? 0 : 1;
            if (aTS !== bTS) return aTS - bTS;
            // Company name starts with query
            var an = (a.company_name || '').toLowerCase();
            var bn = (b.company_name || '').toLowerCase();
            var aNS = an.indexOf(q) === 0 ? 0 : 1;
            var bNS = bn.indexOf(q) === 0 ? 0 : 1;
            if (aNS !== bNS) return aNS - bNS;
            // CEO name starts with query
            var ac = (a.ceo_name || '').toLowerCase();
            var bc = (b.ceo_name || '').toLowerCase();
            var aCS = ac.indexOf(q) === 0 ? 0 : 1;
            var bCS = bc.indexOf(q) === 0 ? 0 : 1;
            if (aCS !== bCS) return aCS - bCS;
            // Alphabetical by ticker
            return at < bt ? -1 : at > bt ? 1 : 0;
        });

        var shown = matches.slice(0, 8);

        if (shown.length === 0) {
            searchResultsEl.classList.remove('visible');
            return;
        }

        shown.forEach(function(c) {
            var div = document.createElement('div');
            div.className = 'table-search-result';
            div.setAttribute('data-ticker', c.ticker);
            div.innerHTML = '<span class="tsr-ticker">' + c.ticker + '</span>' +
                '<span class="tsr-info">' +
                '<span class="tsr-company">' + (c.company_name || '') + '</span>' +
                '<span class="tsr-ceo">' + (c.ceo_name || '') + '</span>' +
                '</span>' +
                '<span class="tsr-comp">' + formatCurrency(c.total_compensation) + '</span>' +
                '<span class="tsr-sector">' + (c.sector || '') + '</span>';
            div.addEventListener('mousedown', function(e) {
                e.preventDefault(); // prevent blur before click fires
                selectSearchCompany(c);
            });
            searchResultsEl.appendChild(div);
        });

        // Show remaining count hint
        if (matches.length > 8) {
            var hint = document.createElement('div');
            hint.className = 'table-search-result';
            hint.style.justifyContent = 'center';
            hint.style.color = 'var(--text-muted)';
            hint.style.fontStyle = 'italic';
            hint.style.cursor = 'default';
            hint.style.fontSize = '0.76rem';
            hint.textContent = '+' + (matches.length - 8) + ' more — keep typing to narrow';
            searchResultsEl.appendChild(hint);
        }

        searchResultsEl.classList.add('visible');
    }

    function selectSearchCompany(company) {
        searchInput.value = company.ticker;
        searchResultsEl.classList.remove('visible');
        searchTerm = company.ticker;
        currentPage = 1;
        renderTable(companies);

        // Scroll to table
        scrollToTable();

        // Auto-expand the company detail panel after render
        setTimeout(function() {
            var rows = document.querySelectorAll('#comp-tbody tr:not(.detail-row)');
            for (var i = 0; i < rows.length; i++) {
                var tickerEl = rows[i].querySelector('.ticker');
                if (tickerEl && tickerEl.textContent.trim() === company.ticker) {
                    rows[i].click();
                    break;
                }
            }
        }, 100);

        announce('Selected ' + company.company_name + ' (' + company.ticker + '), ' + formatCurrency(company.total_compensation));
    }

    searchInput.addEventListener('input', function(e) {
        searchTerm = e.target.value;
        currentPage = 1;
        renderTable(companies);

        // Debounce autocomplete rendering
        clearTimeout(_tsrDebounce);
        _tsrDebounce = setTimeout(function() {
            renderSearchSuggestions(e.target.value.trim());
        }, 80);
    });

    searchInput.addEventListener('keydown', function(e) {
        if (!searchResultsEl) return;
        var items = searchResultsEl.querySelectorAll('.table-search-result[data-ticker]');
        if (items.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            tsrActiveIdx = Math.min(tsrActiveIdx + 1, items.length - 1);
            items.forEach(function(el, i) { el.classList.toggle('active', i === tsrActiveIdx); });
            // Scroll active item into view within the dropdown
            if (items[tsrActiveIdx]) items[tsrActiveIdx].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            tsrActiveIdx = Math.max(tsrActiveIdx - 1, 0);
            items.forEach(function(el, i) { el.classList.toggle('active', i === tsrActiveIdx); });
            if (items[tsrActiveIdx]) items[tsrActiveIdx].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
            if (tsrActiveIdx >= 0 && tsrActiveIdx < items.length) {
                e.preventDefault();
                items[tsrActiveIdx].dispatchEvent(new MouseEvent('mousedown'));
            } else if (items.length > 0 && searchResultsEl.classList.contains('visible')) {
                // If dropdown is visible but no item selected, select first
                e.preventDefault();
                items[0].dispatchEvent(new MouseEvent('mousedown'));
            }
            // Otherwise let the default input behavior proceed (filter-as-you-type)
        } else if (e.key === 'Escape') {
            if (searchResultsEl.classList.contains('visible')) {
                searchResultsEl.classList.remove('visible');
                e.stopPropagation(); // Don't let the outer Escape handler fire
            }
        }
    });

    searchInput.addEventListener('blur', function() {
        // Small delay to allow mousedown events on results to fire
        setTimeout(function() {
            if (searchResultsEl) searchResultsEl.classList.remove('visible');
        }, 150);
    });

    searchInput.addEventListener('focus', function() {
        // Re-show suggestions if there's a query
        if (searchInput.value.trim().length > 0) {
            renderSearchSuggestions(searchInput.value.trim());
        }
    });
}

/* === Company Detail Panel (click-to-expand) === */

function getPeerInfo(ticker) {
    if (!peerData || !peerData.edges) return null;
    var selectedBy = [];
    var selects = [];
    peerData.edges.forEach(function(e) {
        var src = typeof e.source === 'object' ? e.source.ticker : e.source;
        var tgt = typeof e.target === 'object' ? e.target.ticker : e.target;
        if (tgt === ticker) selectedBy.push(src);
        if (src === ticker) selects.push(tgt);
    });
    return { selectedBy: selectedBy, selects: selects };
}

/* === Focus Management — track previous focus for panels === */
var _detailTriggerRow = null;  // row that opened the detail panel
var _preFocusElement = null;   // element focused before modal/comparison opens
var _expandedDetailTicker = null; // ticker of currently expanded detail panel (for URL hash)

function setupDetailPanel(companies) {
    var tbody = document.getElementById('comp-tbody');

    tbody.addEventListener('click', function(e) {
        var row = e.target.closest('tr');
        if (!row || row.classList.contains('detail-row')) return;

        var tickerEl = row.querySelector('.ticker');
        if (!tickerEl) return;
        var ticker = tickerEl.textContent.trim();

        // Close any existing detail
        var existing = tbody.querySelector('.detail-row');
        var wasOpen = existing && existing.dataset.ticker === ticker;
        if (existing) existing.remove();
        tbody.querySelectorAll('tr.selected').forEach(function(r) { r.classList.remove('selected'); });
        tbody.querySelectorAll('tr[aria-expanded]').forEach(function(r) { r.removeAttribute('aria-expanded'); });

        if (wasOpen) {
            // Return focus to the triggering row
            if (_detailTriggerRow && _detailTriggerRow.isConnected) {
                _detailTriggerRow.focus();
            }
            _detailTriggerRow = null;
            _expandedDetailTicker = null;
            pushState();
            return; // toggle off
        }

        row.classList.add('selected');
        row.setAttribute('aria-expanded', 'true');
        // Track trigger row for focus return and ensure it's focusable
        _detailTriggerRow = row;
        if (!row.hasAttribute('tabindex')) row.setAttribute('tabindex', '-1');
        var company = companies.find(function(c) { return c.ticker === ticker; });
        if (!company) return;

        // Compute S&P 500 rank
        var sorted = companies.slice().sort(function(a, b) { return b.total_compensation - a.total_compensation; });
        var overallRank = sorted.findIndex(function(c) { return c.ticker === ticker; }) + 1;
        var topPct = (overallRank / companies.length * 100).toFixed(0);

        // Compute sector rank
        var sectorPeers = companies.filter(function(c) { return c.sector === company.sector; })
            .sort(function(a, b) { return b.total_compensation - a.total_compensation; });
        var sectorRank = sectorPeers.findIndex(function(c) { return c.ticker === ticker; }) + 1;

        // vs sector median
        var sectorMedian = compData.metadata && compData.metadata.sector_medians && compData.metadata.sector_medians[company.sector];
        var sectorMedianPay = sectorMedian ? sectorMedian.median_ceo_pay : null;
        var vsMedianPct = sectorMedianPay && sectorMedianPay > 0
            ? ((company.total_compensation - sectorMedianPay) / sectorMedianPay * 100).toFixed(0)
            : null;

        // Pay ratio percentile
        var ratioText = null;
        if (company.pay_ratio != null) {
            var ratioSorted = companies.filter(function(c) { return c.pay_ratio != null; })
                .sort(function(a, b) { return a.pay_ratio - b.pay_ratio; });
            var ratioIdx = ratioSorted.findIndex(function(c) { return c.ticker === ticker; }) + 1;
            var ratioPctile = Math.round(ratioIdx / ratioSorted.length * 100);
            ratioText = ratioPctile + 'th percentile';
        }

        // Peer network
        var peerInfo = getPeerInfo(ticker);

        // Compute position in visible table rows for navigation
        var _visibleRows = Array.from(tbody.querySelectorAll('tr:not(.detail-row):not(.skeleton-table-row-tr)'));
        var _currentIdx = -1;
        for (var vi = 0; vi < _visibleRows.length; vi++) {
            var _vt = _visibleRows[vi].querySelector('.ticker');
            if (_vt && _vt.textContent.trim() === ticker) { _currentIdx = vi; break; }
        }
        var _hasPrev = _currentIdx > 0;
        var _hasNext = _currentIdx >= 0 && _currentIdx < _visibleRows.length - 1;
        var _posLabel = _currentIdx >= 0 ? (_currentIdx + 1) + ' of ' + _visibleRows.length : '';
        var _pctileLabel = company._compPercentile != null ? getPercentileLabel(company._compPercentile) : '';

        // Build HTML
        var html = '<td colspan="12"><div class="detail-panel" tabindex="-1">';
        html += '<div class="detail-header">';
        html += '<button class="detail-nav-btn detail-nav-prev" title="Previous company (←)" aria-label="Previous company"' + (_hasPrev ? '' : ' disabled') + '>‹</button>';
        html += '<div class="detail-header-center">';
        html += '<span class="detail-header-title">' + company.company_name + ' <span class="detail-ticker">(' + ticker + ')</span></span>';
        if (_posLabel || _pctileLabel) {
            var posHtml = '';
            if (_pctileLabel) {
                var _pc = getPercentileClass(company._compPercentile);
                posHtml += '<span class="pctile-badge ' + _pc + '" style="font-size:0.65rem;vertical-align:middle">' + _pctileLabel + '</span>';
            }
            if (_posLabel) {
                if (posHtml) posHtml += ' &mdash; ';
                posHtml += _posLabel;
            }
            html += '<span class="detail-header-pos">' + posHtml + '</span>';
        }
        html += '</div>';
        html += '<button class="detail-nav-btn detail-nav-next" title="Next company (→)" aria-label="Next company"' + (_hasNext ? '' : ' disabled') + '>›</button>';
        html += '<button class="detail-close-btn" title="Close (Esc)" aria-label="Close detail panel">✕</button>';
        html += '</div>';
        html += '<div class="detail-stats">';

        // Helper: build distribution bar HTML
        function distBar(pctLeft, leftLabel, rightLabel) {
            return '<div class="detail-stat-distbar"><div class="detail-stat-distbar-track"></div><div class="detail-stat-distbar-dot" style="left:' + Math.max(2, Math.min(98, pctLeft)).toFixed(1) + '%"></div></div>' +
                '<div class="detail-stat-distbar-labels"><span>' + leftLabel + '</span><span>' + rightLabel + '</span></div>';
        }

        // S&P 500 Rank — left = #1 (highest paid), right = #500
        var rankPct = (overallRank - 1) / (companies.length - 1) * 100;
        html += '<div class="detail-stat"><div class="detail-stat-label">S&P 500 Rank</div><div class="detail-stat-value">#' + overallRank + '</div>' + distBar(rankPct, '#1', '#500') + '<div class="detail-stat-sub">Top ' + topPct + '%</div></div>';

        // Sector Rank — left = #1 in sector, right = #N
        var sectorPct = sectorPeers.length > 1 ? (sectorRank - 1) / (sectorPeers.length - 1) * 100 : 50;
        html += '<div class="detail-stat"><div class="detail-stat-label">Sector Rank</div><div class="detail-stat-value">#' + sectorRank + ' of ' + sectorPeers.length + '</div>' + distBar(sectorPct, '#1', '#' + sectorPeers.length) + '<div class="detail-stat-sub">' + (company.sector || '') + '</div></div>';

        if (vsMedianPct !== null) {
            var sign = parseInt(vsMedianPct) >= 0 ? '+' : '';
            var cls = parseInt(vsMedianPct) >= 0 ? 'positive' : 'negative';
            html += '<div class="detail-stat"><div class="detail-stat-label">vs Sector Median</div><div class="detail-stat-value ' + cls + '">' + sign + vsMedianPct + '%</div><div class="detail-stat-sub">Median: ' + formatCurrency(sectorMedianPay) + '</div></div>';
        }

        if (ratioText) {
            // Pay Ratio Rank — left = lowest ratio (most equitable), right = highest ratio
            var ratioSortedForBar = companies.filter(function(c) { return c.pay_ratio != null; })
                .sort(function(a, b) { return a.pay_ratio - b.pay_ratio; });
            var ratioBarIdx = ratioSortedForBar.findIndex(function(c) { return c.ticker === ticker; });
            var ratioPctBar = ratioSortedForBar.length > 1 ? ratioBarIdx / (ratioSortedForBar.length - 1) * 100 : 50;
            html += '<div class="detail-stat"><div class="detail-stat-label">Pay Ratio Rank</div><div class="detail-stat-value">' + ratioText + '</div>' + distBar(ratioPctBar, 'Low', 'High') + '<div class="detail-stat-sub">' + formatRatio(company.pay_ratio) + '</div></div>';
        }

        if (peerInfo) {
            html += '<div class="detail-stat"><div class="detail-stat-label">Peer Network</div><div class="detail-stat-value">' + peerInfo.selectedBy.length + ' in · ' + peerInfo.selects.length + ' out</div><div class="detail-stat-sub">Inbound / outbound</div></div>';
        }

        // Total NEO compensation stat
        if (company.total_neo_compensation) {
            html += '<div class="detail-stat"><div class="detail-stat-label">Total NEO Comp</div><div class="detail-stat-value">' + formatCurrency(company.total_neo_compensation) + '</div><div class="detail-stat-sub">' + (company.neo_count || '—') + ' Named Executives, FY' + (company.proxy_fiscal_year || '') + '</div></div>';
        }

        // CEO Pay Concentration — CEO comp as % of total NEO compensation
        if (company._ceoConcPct != null) {
            var concPct = company._ceoConcPct;
            var concCls = concPct >= 50 ? 'negative' : concPct >= 35 ? '' : 'positive';
            var concLabel = concPct >= 50 ? 'Concentrated' : concPct >= 35 ? 'Moderate' : 'Distributed';
            html += '<div class="detail-stat"><div class="detail-stat-label">CEO Concentration</div><div class="detail-stat-value ' + concCls + '">' + concPct.toFixed(1) + '%</div>' + distBar(concPct, '0%', '100%') + '<div class="detail-stat-sub">' + concLabel + ' — CEO share of NEO total</div></div>';
        }

        // CEO Premium — CEO pay vs #2 exec
        if (company._ceoPremiumRatio != null) {
            var premRatio = company._ceoPremiumRatio;
            var premStr = premRatio >= 10 ? premRatio.toFixed(0) + '×' : premRatio.toFixed(1) + '×';
            html += '<div class="detail-stat"><div class="detail-stat-label">CEO Premium</div><div class="detail-stat-value">' + premStr + '</div><div class="detail-stat-sub">CEO pay vs. #2 executive</div></div>';
        }

        // CEO History — transition/tenure data
        if (company._ceoTransition) {
            var _tr = company._ceoTransition;
            html += '<div class="detail-stat"><div class="detail-stat-label">CEO Transition</div><div class="detail-stat-value ceo-transition-new">New CEO</div><div class="detail-stat-sub">Succeeded ' + (_tr.oldCeo.name || 'previous CEO') + ' after FY' + _tr.oldCeo.year + '</div></div>';
        } else if (company._ceoDataYears && company._ceoDataYears >= 2) {
            html += '<div class="detail-stat"><div class="detail-stat-label">CEO Tenure</div><div class="detail-stat-value">' + company._ceoDataYears + '+ years</div><div class="detail-stat-sub">In role since at least FY' + (company.executives ? (function() { var yrs = []; company.executives.forEach(function(e) { if (yrs.indexOf(e.year) < 0) yrs.push(e.year); }); yrs.sort(function(a,b){return a-b;}); return yrs[0]; })() : '?') + '</div></div>';
        }

        // Team Completeness — C-suite role coverage visualization
        if (company._teamRoles && company.executives && company.executives.length > 0) {
            var _tcRoles = ['CEO', 'CFO', 'COO', 'GC/CLO', 'CTO', 'CHRO', 'CIO'];
            var _tcCount = company._teamRoleCount || 0;
            var _tcCls = _tcCount >= 4 ? 'positive' : _tcCount >= 2 ? '' : 'negative';
            var _tcDotsHtml = '';
            _tcRoles.forEach(function(r) {
                var filled = company._teamRoles.indexOf(r) >= 0;
                var color = filled ? (ROLE_COLORS[r] || '#94a3b8') : 'transparent';
                var border = filled ? color : 'rgba(161,161,170,0.3)';
                var roleExec = company._roleExecs && company._roleExecs[r];
                var tip = r + (filled ? (roleExec ? ': ' + roleExec.name + ' (' + formatCompact(roleExec.total || 0) + ')' : ' ✓') : ' — not in NEO disclosure');
                _tcDotsHtml += '<span class="tc-dot' + (filled ? ' tc-filled' : '') + '" style="background:' + color + ';border-color:' + border + '" title="' + tip.replace(/"/g, '&quot;') + '"><span class="tc-dot-label">' + r.replace('GC/CLO', 'GC') + '</span></span>';
            });
            var _tcMissing = company._teamMissingExpected && company._teamMissingExpected.length > 0;
            var _tcSubText = _tcCount + '/7 C-suite roles in NEO data';
            if (_tcMissing) {
                _tcSubText += ' · <span class="tc-missing-link" onclick="event.stopPropagation();if(window.filterByTeamCompleteness)window.filterByTeamCompleteness(\'missing\')" title="Click to filter table to companies missing expected roles" style="cursor:pointer;text-decoration:underline;text-decoration-style:dotted;">Missing: ' + company._teamMissingExpected.join(', ') + '</span>';
            }
            html += '<div class="detail-stat detail-stat-wide"><div class="detail-stat-label">Team Completeness</div><div class="detail-stat-value ' + _tcCls + '">' + _tcCount + ' roles</div><div class="tc-dots">' + _tcDotsHtml + '</div><div class="detail-stat-sub">' + _tcSubText + '</div></div>';
        }

        html += '</div>'; // detail-stats

        // CEO Compensation Breakdown — visual stacked bar
        if (company.executives && company.executives.length > 0) {
            var _cbAllYears = [];
            company.executives.forEach(function(e) { if (_cbAllYears.indexOf(e.year) < 0) _cbAllYears.push(e.year); });
            _cbAllYears.sort(function(a,b) { return b - a; });
            var _cbLatestYear = _cbAllYears[0];
            var _cbLatestExecs = company.executives.filter(function(e) { return e.year === _cbLatestYear; });

            // Find the CEO executive
            var ceoExec = _cbLatestExecs.find(function(e) {
                return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
            });
            // Fallback: if no title match, use the executive with highest total
            if (!ceoExec && _cbLatestExecs.length > 0) {
                ceoExec = _cbLatestExecs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
            }

            if (ceoExec && ceoExec.total && ceoExec.total > 0) {
                var cbSegments = [];
                var cbColorMap = {
                    'Base Salary': '#06d6a0',
                    'Stock Awards': '#00b4d8',
                    'Option Awards': '#0096c7',
                    'Non-Equity Incentive': '#a78bfa',
                    'Bonus': '#8b5cf6',
                    'Pension/NQDC': '#fb923c',
                    'All Other': '#ffd166'
                };

                if (ceoExec.salary) cbSegments.push({ label: 'Base Salary', value: ceoExec.salary, color: cbColorMap['Base Salary'] });
                if (ceoExec.stock_awards) cbSegments.push({ label: 'Stock Awards', value: ceoExec.stock_awards, color: cbColorMap['Stock Awards'] });
                if (ceoExec.option_awards) cbSegments.push({ label: 'Option Awards', value: ceoExec.option_awards, color: cbColorMap['Option Awards'] });
                if (ceoExec.non_equity_incentive) cbSegments.push({ label: 'Non-Equity Incentive', value: ceoExec.non_equity_incentive, color: cbColorMap['Non-Equity Incentive'] });
                if (ceoExec.bonus) cbSegments.push({ label: 'Bonus', value: ceoExec.bonus, color: cbColorMap['Bonus'] });
                if (ceoExec.pension_nqdc) cbSegments.push({ label: 'Pension/NQDC', value: ceoExec.pension_nqdc, color: cbColorMap['Pension/NQDC'] });
                if (ceoExec.all_other) cbSegments.push({ label: 'All Other', value: ceoExec.all_other, color: cbColorMap['All Other'] });

                if (cbSegments.length > 0) {
                    var cbTotal = cbSegments.reduce(function(s, seg) { return s + seg.value; }, 0);
                    cbSegments.forEach(function(seg) { seg.pct = cbTotal > 0 ? (seg.value / cbTotal * 100) : 0; });
                    // Sort by value descending for visual clarity
                    cbSegments.sort(function(a, b) { return b.value - a.value; });

                    html += '<div class="ceo-comp-breakdown">';
                    html += '<div class="ceo-comp-breakdown-header">';
                    html += '<span class="ceo-comp-breakdown-title">CEO Pay Composition</span>';
                    html += '<span class="ceo-comp-breakdown-name">' + (ceoExec.name || company.ceo_name) + ' · FY' + _cbLatestYear + '</span>';
                    html += '</div>';

                    // Stacked bar
                    html += '<div class="ceo-comp-bar">';
                    cbSegments.forEach(function(seg) {
                        if (seg.pct < 0.5) return; // Skip tiny segments in the bar
                        html += '<div class="ceo-comp-bar-seg" style="width:' + seg.pct.toFixed(1) + '%;background:' + seg.color + '" title="' + seg.label + ': ' + formatCurrency(seg.value) + ' (' + seg.pct.toFixed(1) + '%)">';
                        if (seg.pct >= 8) {
                            html += '<span class="ceo-comp-bar-seg-label">' + seg.pct.toFixed(0) + '%</span>';
                        }
                        html += '</div>';
                    });
                    html += '</div>';

                    // Legend items
                    html += '<div class="ceo-comp-legend">';
                    cbSegments.forEach(function(seg) {
                        html += '<div class="ceo-comp-legend-item">';
                        html += '<span class="ceo-comp-legend-dot" style="background:' + seg.color + '"></span>';
                        html += '<span class="ceo-comp-legend-label">' + seg.label + '</span>';
                        html += '<span class="ceo-comp-legend-val">' + formatCurrency(seg.value) + ' <span class="ceo-comp-legend-pct">(' + seg.pct.toFixed(1) + '%)</span></span>';
                        html += '</div>';
                    });
                    html += '</div>';
                    html += '</div>';
                }
            }
        }

        // CEO Pay Trend — mini bar chart showing CEO total comp across fiscal years
        if (company.executives && company.executives.length > 0) {
            var _trendYears = [];
            company.executives.forEach(function(e) { if (_trendYears.indexOf(e.year) < 0) _trendYears.push(e.year); });
            _trendYears.sort(function(a, b) { return a - b; }); // ascending for left-to-right display

            if (_trendYears.length >= 2) {
                var ceoTrendData = [];
                _trendYears.forEach(function(yr) {
                    var yrExecs = company.executives.filter(function(e) { return e.year === yr; });
                    var ceoCand = yrExecs.find(function(e) {
                        return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
                    });
                    if (!ceoCand && yrExecs.length > 0) {
                        ceoCand = yrExecs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
                    }
                    if (ceoCand && ceoCand.total > 0) {
                        ceoTrendData.push({ year: yr, total: ceoCand.total, name: ceoCand.name || company.ceo_name });
                    }
                });

                if (ceoTrendData.length >= 2) {
                    var maxTrend = Math.max.apply(null, ceoTrendData.map(function(d) { return d.total; }));
                    var firstTrend = ceoTrendData[0];
                    var lastTrend = ceoTrendData[ceoTrendData.length - 1];
                    var overallPctChange = ((lastTrend.total - firstTrend.total) / firstTrend.total * 100);
                    var overallAbsStr = Math.abs(overallPctChange) >= 100 ? Math.round(Math.abs(overallPctChange)) + '%' : Math.abs(overallPctChange).toFixed(1) + '%';
                    var overallCls = overallPctChange >= 0 ? 'positive' : 'negative';
                    var overallSign = overallPctChange >= 0 ? '+' : '\u2212';

                    // Detect CEO name changes within the trend data for transition annotation
                    function _normTrendName(n) {
                        return (n || '').toLowerCase()
                            .replace(/\b(jr|sr|iii|iv|ii|mr|ms|dr|phd|former)\b\.?/g, '')
                            .replace(/[.,'"()]/g, '')
                            .replace(/\b[a-z]\b/g, '')
                            .replace(/\s+/g, ' ').trim();
                    }
                    var _hasTransition = false;
                    var _transitionIndices = []; // indices where CEO changed (the NEW CEO's index)
                    for (var _ti = 1; _ti < ceoTrendData.length; _ti++) {
                        var _prevNorm = _normTrendName(ceoTrendData[_ti - 1].name);
                        var _currNorm = _normTrendName(ceoTrendData[_ti].name);
                        if (_prevNorm !== _currNorm && _prevNorm.length > 0 && _currNorm.length > 0) {
                            _hasTransition = true;
                            _transitionIndices.push(_ti);
                        }
                    }

                    // Build a map of unique CEO "segments" for coloring (each distinct CEO gets a segment ID)
                    var _ceoSegments = [0]; // segment ID per bar index
                    var _segId = 0;
                    for (var _si = 1; _si < ceoTrendData.length; _si++) {
                        if (_transitionIndices.indexOf(_si) >= 0) _segId++;
                        _ceoSegments.push(_segId);
                    }

                    // Extract short last name for CEO labels
                    function _shortCeoName(fullName) {
                        if (!fullName) return '';
                        var parts = fullName.trim().split(/\s+/);
                        // Return last meaningful token (skip Jr/Sr/III etc.)
                        for (var _k = parts.length - 1; _k >= 0; _k--) {
                            if (!/^(jr|sr|iii|iv|ii)\.?$/i.test(parts[_k])) return parts[_k];
                        }
                        return parts[parts.length - 1] || '';
                    }

                    html += '<div class="ceo-trend-mini">';
                    html += '<div class="ceo-trend-mini-header">';
                    html += '<span class="ceo-trend-mini-title">CEO Pay Trend</span>';
                    if (_hasTransition) {
                        html += '<span class="ceo-trend-transition-badge" title="CEO changed during this period">\u21C4 CEO Transition</span>';
                    }
                    html += '<span class="ceo-trend-mini-change ' + overallCls + '" title="FY' + firstTrend.year + ' to FY' + lastTrend.year + '">' + overallSign + overallAbsStr + ' over ' + ceoTrendData.length + ' years</span>';
                    html += '</div>';

                    html += '<div class="ceo-trend-mini-bars">';
                    ceoTrendData.forEach(function(d, i) {
                        var barH = maxTrend > 0 ? Math.max(8, Math.round(d.total / maxTrend * 64)) : 8;
                        var isLatest = (i === ceoTrendData.length - 1);
                        var isTransitionPoint = _transitionIndices.indexOf(i) >= 0;
                        var isOutgoingCeo = _hasTransition && _ceoSegments[i] < _ceoSegments[ceoTrendData.length - 1];

                        // Insert transition divider before this bar
                        if (isTransitionPoint) {
                            html += '<div class="ceo-trend-divider" title="CEO changed: ' + (ceoTrendData[i - 1].name || '').replace(/"/g, '&quot;') + ' \u2192 ' + (d.name || '').replace(/"/g, '&quot;') + '">';
                            html += '<div class="ceo-trend-divider-line"></div>';
                            html += '<div class="ceo-trend-divider-label">\u2192</div>';
                            html += '</div>';
                        }

                        html += '<div class="ceo-trend-mini-col' + (isTransitionPoint ? ' ceo-trend-new-ceo' : '') + '">';
                        html += '<div class="ceo-trend-mini-val">' + formatCurrency(d.total) + '</div>';

                        // YoY change label between bars
                        if (i > 0) {
                            var prev = ceoTrendData[i - 1];
                            var yoyPct = ((d.total - prev.total) / prev.total * 100);
                            var yoyCls = yoyPct >= 0 ? 'positive' : 'negative';
                            var yoyAbsStr = Math.abs(yoyPct) >= 100 ? Math.round(Math.abs(yoyPct)) + '%' : Math.abs(yoyPct).toFixed(1) + '%';
                            html += '<div class="ceo-trend-mini-yoy ' + yoyCls + '">' + (yoyPct >= 0 ? '\u25B2' : '\u25BC') + ' ' + (yoyPct >= 0 ? '+' : '\u2212') + yoyAbsStr + '</div>';
                        } else {
                            html += '<div class="ceo-trend-mini-yoy">\u00A0</div>';
                        }

                        // Bar: outgoing CEO gets muted color, current CEO gets accent
                        var barStyle = 'height:' + barH + 'px';
                        if (isOutgoingCeo) {
                            barStyle += ';background:#6b7280;opacity:0.5';
                        } else if (!isLatest && !_hasTransition) {
                            barStyle += ';opacity:0.55';
                        }
                        html += '<div class="ceo-trend-mini-bar" style="' + barStyle + '" title="' + (d.name || '') + ' FY' + d.year + ': ' + formatCurrency(d.total) + '"></div>';
                        html += '<div class="ceo-trend-mini-year">FY' + d.year + '</div>';

                        // Show CEO last name label when transition exists
                        if (_hasTransition) {
                            var _showName = false;
                            // Show name on first bar, at each transition point, and if name differs from previous
                            if (i === 0 || isTransitionPoint) _showName = true;
                            if (_showName) {
                                html += '<div class="ceo-trend-name-label' + (isOutgoingCeo ? ' ceo-outgoing' : '') + '">' + _shortCeoName(d.name) + '</div>';
                            } else {
                                html += '<div class="ceo-trend-name-label">\u00A0</div>'; // spacer for alignment
                            }
                        }

                        html += '</div>';
                    });
                    html += '</div>';
                    html += '</div>';
                }
            }
        }

        // Peer Pay Position — horizontal bar chart showing this company vs. comp peers
        if (peerInfo && (peerInfo.selectedBy.length > 0 || peerInfo.selects.length > 0)) {
            var _peerAllTickers = [];
            peerInfo.selects.forEach(function(t) { if (_peerAllTickers.indexOf(t) < 0) _peerAllTickers.push(t); });
            peerInfo.selectedBy.forEach(function(t) { if (_peerAllTickers.indexOf(t) < 0) _peerAllTickers.push(t); });

            var _peerCompList = [];
            _peerAllTickers.forEach(function(t) {
                var peer = companies.find(function(c2) { return c2.ticker === t; });
                if (peer && peer.total_compensation > 0) {
                    _peerCompList.push({ ticker: t, total: peer.total_compensation, name: peer.ceo_name || '', isSelf: false });
                }
            });

            if (_peerCompList.length >= 2) {
                _peerCompList.push({ ticker: ticker, total: company.total_compensation || 0, name: company.ceo_name || '', isSelf: true });
                _peerCompList.sort(function(a, b) { return b.total - a.total; });

                var _peerRank = _peerCompList.findIndex(function(p) { return p.isSelf; }) + 1;
                var _peerMax = _peerCompList[0].total;
                var _peerCount = _peerCompList.length;
                var _maxPeerShow = 15;
                var _peerTruncated = _peerCompList.length > _maxPeerShow;
                var _displayPeers = _peerTruncated ? _peerCompList.slice(0, _maxPeerShow) : _peerCompList;
                // Ensure self is always visible even when truncated
                if (_peerTruncated && !_displayPeers.some(function(p) { return p.isSelf; })) {
                    _displayPeers[_maxPeerShow - 1] = _peerCompList.find(function(p) { return p.isSelf; });
                }

                // Compute vs peer median
                var _peerTotals = _peerCompList.filter(function(p) { return !p.isSelf; }).map(function(p) { return p.total; });
                _peerTotals.sort(function(a, b) { return a - b; });
                var _peerMedian = _peerTotals.length > 0 ? _peerTotals[Math.floor(_peerTotals.length / 2)] : 0;
                var _vsPeerMedianPct = _peerMedian > 0 ? ((company.total_compensation - _peerMedian) / _peerMedian * 100) : 0;
                var _vsPeerSign = _vsPeerMedianPct >= 0 ? '+' : '\u2212';
                var _vsPeerCls = _vsPeerMedianPct >= 0 ? 'positive' : 'negative';
                var _vsPeerAbsStr = Math.abs(_vsPeerMedianPct) >= 100 ? Math.round(Math.abs(_vsPeerMedianPct)) + '%' : Math.abs(_vsPeerMedianPct).toFixed(1) + '%';

                html += '<div class="peer-pay-section">';
                html += '<div class="peer-pay-header">';
                html += '<span class="peer-pay-title">Peer Pay Position</span>';
                html += '<span class="peer-pay-rank">#' + _peerRank + ' of ' + _peerCount + '</span>';
                html += '</div>';
                html += '<div class="peer-pay-sub ' + _vsPeerCls + '">' + _vsPeerSign + _vsPeerAbsStr + ' vs peer median (' + formatCurrency(_peerMedian) + ')</div>';
                html += '<div class="peer-pay-rows">';

                _displayPeers.forEach(function(p) {
                    var barW = _peerMax > 0 ? Math.max(2, p.total / _peerMax * 100) : 0;
                    var cls = p.isSelf ? ' peer-pay-self' : '';
                    var rowTitle = p.name + ': ' + formatCurrency(p.total);
                    html += '<div class="peer-pay-row' + cls + '" data-ticker="' + p.ticker + '" title="' + rowTitle.replace(/"/g, '&quot;') + '">';
                    html += '<span class="peer-pay-ticker">' + p.ticker + '</span>';
                    html += '<div class="peer-pay-bar-track"><div class="peer-pay-bar" style="width:' + barW.toFixed(1) + '%"></div></div>';
                    html += '<span class="peer-pay-val">' + formatCurrency(p.total) + '</span>';
                    html += '</div>';
                });

                if (_peerTruncated) {
                    html += '<div class="peer-pay-more">+ ' + (_peerCount - _maxPeerShow) + ' more peers</div>';
                }

                html += '</div>'; // peer-pay-rows
                html += '</div>'; // peer-pay-section
            }
        }

        // NEO Executive Compensation Breakdown (from EDGAR data)
        if (company.executives && company.executives.length > 0) {
            var allYears = [];
            company.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
            allYears.sort(function(a,b) { return b - a; });
            var latestYear = allYears[0];

            html += '<div class="neo-section">';
            html += '<div class="neo-section-header">';
            html += '<span class="neo-section-title">Named Executive Officers</span>';
            if (company.filing_url) {
                html += ' <a class="neo-filing-link" href="' + company.filing_url + '" target="_blank" rel="noopener" title="View DEF 14A proxy statement on SEC EDGAR">📄 SEC Filing</a>';
            }
            html += '</div>';

            // Year tabs (if multiple years available)
            if (allYears.length > 1) {
                html += '<div class="neo-year-tabs" role="tablist" aria-label="Select fiscal year">';
                allYears.forEach(function(yr, idx) {
                    html += '<button class="neo-year-tab' + (idx === 0 ? ' active' : '') + '" data-year="' + yr + '" role="tab" aria-selected="' + (idx === 0 ? 'true' : 'false') + '" tabindex="' + (idx === 0 ? '0' : '-1') + '">FY' + yr + '</button>';
                });
                html += '</div>';
            }

            // Render a table for each year (only first visible)
            allYears.forEach(function(yr, yrIdx) {
                var yrExecs = company.executives.filter(function(e) { return e.year === yr; });
                var yrTotal = 0;

                html += '<div class="neo-year-panel" data-year="' + yr + '"' + (yrIdx > 0 ? ' style="display:none"' : '') + '>';
                html += '<div class="neo-table-wrap"><table class="neo-table">';
                // Determine which optional columns have data for this year
                var yrHasBonus = yrExecs.some(function(e) { return e.bonus && e.bonus > 0; });
                var yrHasPension = yrExecs.some(function(e) { return (e.pension_nqdc && e.pension_nqdc > 0) || (e.pension_change && e.pension_change > 0); });
                var neoCols = 6 + (yrHasBonus ? 1 : 0) + (yrHasPension ? 1 : 0); // name + title + data cols

                html += '<thead><tr><th>Name</th><th>Title</th><th class="neo-num">Salary</th>';
                if (yrHasBonus) html += '<th class="neo-num">Bonus</th>';
                html += '<th class="neo-num">Stock Awards</th><th class="neo-num">Option Awards</th><th class="neo-num">Non-Equity Incentive</th>';
                if (yrHasPension) html += '<th class="neo-num">Pension/NQDC</th>';
                html += '<th class="neo-num">All Other</th><th class="neo-num neo-total">Total</th></tr></thead>';
                html += '<tbody>';

                yrExecs.forEach(function(exec) {
                    var total = exec.total || 0;
                    yrTotal += total;
                    var isCeo = exec.title && (/chief executive/i.test(exec.title) || /\bceo\b/i.test(exec.title));
                    html += '<tr' + (isCeo ? ' class="neo-ceo-row"' : '') + '>';
                    html += '<td class="neo-name">' + (exec.name || '—') + '</td>';
                    html += '<td class="neo-title">' + (exec.title || '—') + '</td>';
                    html += '<td class="neo-num">' + (exec.salary ? formatCompact(exec.salary) : '—') + '</td>';
                    if (yrHasBonus) html += '<td class="neo-num">' + (exec.bonus ? formatCompact(exec.bonus) : '—') + '</td>';
                    html += '<td class="neo-num">' + (exec.stock_awards ? formatCompact(exec.stock_awards) : '—') + '</td>';
                    html += '<td class="neo-num">' + (exec.option_awards ? formatCompact(exec.option_awards) : '—') + '</td>';
                    html += '<td class="neo-num">' + (exec.non_equity_incentive ? formatCompact(exec.non_equity_incentive) : '—') + '</td>';
                    if (yrHasPension) html += '<td class="neo-num">' + ((exec.pension_nqdc || exec.pension_change) ? formatCompact(exec.pension_nqdc || exec.pension_change) : '—') + '</td>';
                    html += '<td class="neo-num">' + (exec.all_other ? formatCompact(exec.all_other) : '—') + '</td>';
                    html += '<td class="neo-num neo-total">' + formatCompact(total);
                    // Role benchmark context badge
                    if (_roleBenchmarks && total > 0) {
                        var _execRole = classifyExecRole(exec.title);
                        var _rb = _roleBenchmarks[_execRole];
                        if (_rb && _rb.median > 0 && _execRole !== 'Other') {
                            var _vsRolePct = ((total - _rb.median) / _rb.median * 100);
                            var _vsSign = _vsRolePct >= 0 ? '+' : '\u2212';
                            var _vsCls = _vsRolePct >= 0 ? 'positive' : 'negative';
                            var _vsAbsStr = Math.abs(_vsRolePct) >= 100 ? Math.round(Math.abs(_vsRolePct)) + '%' : Math.abs(_vsRolePct).toFixed(0) + '%';
                            var _vsTitle = _vsSign + _vsAbsStr + ' vs S&P 500 ' + _execRole + ' median (' + formatCompact(_rb.median) + ')';
                            html += ' <span class="neo-role-badge ' + _vsCls + '" title="' + _vsTitle + '">' + _vsSign + _vsAbsStr + '</span>';
                        }
                    }
                    html += '</td>';
                    html += '</tr>';
                });

                // Total row
                html += '<tr class="neo-total-row"><td colspan="' + (neoCols + 1) + '" class="neo-total-label">Total NEO Compensation</td>';
                html += '<td class="neo-num neo-total">' + formatCurrency(yrTotal) + '</td></tr>';

                html += '</tbody></table></div>';

                // Year-over-year comparison vs next year (if exists)
                var nextYrIdx = yrIdx + 1;
                if (nextYrIdx < allYears.length) {
                    var nextYr = allYears[nextYrIdx];
                    var nextYrExecs = company.executives.filter(function(e) { return e.year === nextYr; });
                    var nextYrTotal = 0;
                    nextYrExecs.forEach(function(e) { nextYrTotal += (e.total || 0); });
                    if (nextYrTotal > 0) {
                        var yoyChange = ((yrTotal - nextYrTotal) / nextYrTotal * 100).toFixed(1);
                        var yoySign = parseFloat(yoyChange) >= 0 ? '+' : '';
                        var yoyCls = parseFloat(yoyChange) >= 0 ? 'positive' : 'negative';
                        html += '<div class="neo-yoy"><span class="neo-yoy-label">vs FY' + nextYr + ':</span> ' + formatCurrency(nextYrTotal) + ' <span class="' + yoyCls + '">(' + yoySign + yoyChange + '% YoY)</span></div>';
                    }
                }

                html += '</div>'; // neo-year-panel
            });

            html += '<div class="neo-source">Source: SEC EDGAR DEF 14A' + (company.filing_date ? ' (filed ' + company.filing_date + ')' : '') + '</div>';
            html += '</div>'; // neo-section
        }

        // Data completeness notice for companies with missing fields
        if (company.pay_ratio == null || company.median_worker_pay == null) {
            var missingReason = MISSING_DATA_REASONS[ticker] || 'Pay ratio and median worker pay data not available for this company.';
            html += '<div class="detail-data-notice"><span class="detail-data-notice-icon">⚠</span> <strong>Incomplete data:</strong> ' + missingReason + '</div>';
        }

        // "Show in Network" button
        if (peerInfo && (peerInfo.selectedBy.length > 0 || peerInfo.selects.length > 0)) {
            html += '<div class="detail-actions">';
            html += '<button class="detail-network-btn" onclick="if(window.focusNetworkNode)window.focusNetworkNode(\'' + ticker.replace(/'/g, "\\'") + '\')">';
            html += '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/><path d="M6 7l4 3M14 10l4-3M6 17l4-3M14 14l4 3"/></svg>';
            html += ' Show in Network</button>';
            html += '</div>';
        }

        // Peer lists as ticker tags
        if (peerInfo && (peerInfo.selectedBy.length > 0 || peerInfo.selects.length > 0)) {
            html += '<div class="detail-peers">';
            if (peerInfo.selectedBy.length > 0) {
                html += '<div class="detail-peer-group"><span class="detail-peer-label">Selected as comp peer by:</span>';
                html += '<div class="detail-peer-tags">';
                html += peerInfo.selectedBy.slice(0, 20).map(function(t) { return '<span class="detail-peer-tag detail-peer-tag-link" data-ticker="' + t + '" tabindex="0" role="button" title="Click to find in table · Shift+click to show in network">' + t + '</span>'; }).join('');
                if (peerInfo.selectedBy.length > 20) html += '<span class="detail-peer-more">+' + (peerInfo.selectedBy.length - 20) + ' more</span>';
                html += '</div></div>';
            }
            if (peerInfo.selects.length > 0) {
                html += '<div class="detail-peer-group"><span class="detail-peer-label">Benchmarks against:</span>';
                html += '<div class="detail-peer-tags">';
                html += peerInfo.selects.slice(0, 20).map(function(t) { return '<span class="detail-peer-tag detail-peer-tag-link" data-ticker="' + t + '" tabindex="0" role="button" title="Click to find in table · Shift+click to show in network">' + t + '</span>'; }).join('');
                if (peerInfo.selects.length > 20) html += '<span class="detail-peer-more">+' + (peerInfo.selects.length - 20) + ' more</span>';
                html += '</div></div>';
            }
            html += '</div>';
        }

        html += '</div></td>'; // detail-panel

        var detailRow = document.createElement('tr');
        detailRow.className = 'detail-row';
        detailRow.dataset.ticker = ticker;
        detailRow.innerHTML = html;
        row.after(detailRow);

        // Track expanded detail for URL hash deep-linking
        _expandedDetailTicker = ticker;
        pushState();

        // Wire up NEO year tabs — switch between fiscal years
        detailRow.querySelectorAll('.neo-year-tab').forEach(function(tab) {
            tab.addEventListener('click', function(e) {
                e.stopPropagation();
                var yr = tab.getAttribute('data-year');
                var section = tab.closest('.neo-section');
                if (!section) return;
                // Update tab active states
                section.querySelectorAll('.neo-year-tab').forEach(function(t) {
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                    t.setAttribute('tabindex', '-1');
                });
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
                tab.setAttribute('tabindex', '0');
                // Show/hide year panels
                section.querySelectorAll('.neo-year-panel').forEach(function(panel) {
                    panel.style.display = panel.getAttribute('data-year') === yr ? '' : 'none';
                });
            });
            // Arrow key navigation between tabs
            tab.addEventListener('keydown', function(e) {
                if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
                e.preventDefault();
                e.stopPropagation(); // Prevent detail panel from navigating to prev/next company
                var tabs = Array.from(tab.closest('.neo-year-tabs').querySelectorAll('.neo-year-tab'));
                var idx = tabs.indexOf(tab);
                var next = e.key === 'ArrowRight' ? (idx + 1) % tabs.length : (idx - 1 + tabs.length) % tabs.length;
                tabs[next].click();
                tabs[next].focus();
            });
        });

        // Wire up clickable detail peer tags — click to find in table, shift+click to show in network
        detailRow.querySelectorAll('.detail-peer-tag-link').forEach(function(tag) {
            tag.addEventListener('click', function(e) {
                e.stopPropagation();
                var peerTicker = tag.getAttribute('data-ticker');
                if (!peerTicker) return;
                if (e.shiftKey) {
                    if (window.focusNetworkNode) window.focusNetworkNode(peerTicker);
                } else {
                    if (window.findCompanyInTable) window.findCompanyInTable(peerTicker);
                }
            });
            tag.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    e.stopPropagation();
                    var peerTicker = tag.getAttribute('data-ticker');
                    if (!peerTicker) return;
                    if (e.shiftKey) {
                        if (window.focusNetworkNode) window.focusNetworkNode(peerTicker);
                    } else {
                        if (window.findCompanyInTable) window.findCompanyInTable(peerTicker);
                    }
                }
            });
        });

        // Wire up clickable peer pay rows — click to find peer in table
        detailRow.querySelectorAll('.peer-pay-row[data-ticker]').forEach(function(row) {
            if (row.classList.contains('peer-pay-self')) return; // Skip self
            row.style.cursor = 'pointer';
            row.addEventListener('click', function(e) {
                e.stopPropagation();
                var peerTicker = row.getAttribute('data-ticker');
                if (peerTicker && window.findCompanyInTable) window.findCompanyInTable(peerTicker);
            });
        });

        // Wire up prev/next navigation buttons
        function _navigateDetail(direction) {
            var visRows = Array.from(tbody.querySelectorAll('tr:not(.detail-row):not(.skeleton-table-row-tr)'));
            var curIdx = -1;
            for (var ni = 0; ni < visRows.length; ni++) {
                var nt = visRows[ni].querySelector('.ticker');
                if (nt && nt.textContent.trim() === ticker) { curIdx = ni; break; }
            }
            if (curIdx < 0) return;
            var targetIdx = curIdx + direction;
            if (targetIdx < 0 || targetIdx >= visRows.length) return;
            // Scroll the target row into view before clicking to ensure smooth transition
            var targetRow = visRows[targetIdx];
            var stickyH = getStickyOffset();
            var rowTop = targetRow.getBoundingClientRect().top + window.scrollY - stickyH - 16;
            window.scrollTo({ top: rowTop, behavior: getScrollBehavior() });
            setTimeout(function() { targetRow.click(); }, 50);
        }

        var _prevBtn = detailRow.querySelector('.detail-nav-prev');
        var _nextBtn = detailRow.querySelector('.detail-nav-next');
        var _closeBtn = detailRow.querySelector('.detail-close-btn');

        if (_prevBtn) _prevBtn.addEventListener('click', function(e) { e.stopPropagation(); _navigateDetail(-1); });
        if (_nextBtn) _nextBtn.addEventListener('click', function(e) { e.stopPropagation(); _navigateDetail(1); });
        if (_closeBtn) _closeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            detailRow.remove();
            tbody.querySelectorAll('tr.selected').forEach(function(r) { r.classList.remove('selected'); });
            tbody.querySelectorAll('tr[aria-expanded]').forEach(function(r) { r.removeAttribute('aria-expanded'); });
            if (_detailTriggerRow && _detailTriggerRow.isConnected) {
                _detailTriggerRow.focus();
            }
            _detailTriggerRow = null;
            _expandedDetailTicker = null;
            pushState();
        });

        // ARIA announcement for detail panel
        announce(company.company_name + ' detail panel. Rank ' + overallRank + ' of ' + companies.length + ', ' + formatCurrency(company.total_compensation) + ' total compensation.');

        // Move focus to the detail panel for keyboard/screen reader users
        var panelEl = detailRow.querySelector('.detail-panel');
        if (panelEl) {
            // Add keyboard navigation for arrow keys
            panelEl.addEventListener('keydown', function(e) {
                // Skip if the event originated from an interactive child with its own arrow handling
                if (e.target.closest && e.target.closest('.neo-year-tabs')) return;
                if (e.key === 'ArrowLeft' && _hasPrev) {
                    e.preventDefault();
                    e.stopPropagation();
                    _navigateDetail(-1);
                } else if (e.key === 'ArrowRight' && _hasNext) {
                    e.preventDefault();
                    e.stopPropagation();
                    _navigateDetail(1);
                }
            });
            setTimeout(function() { panelEl.focus({ preventScroll: true }); }, 50);
        }
    });

    // Keyboard handler: Enter/Space on a row expands/collapses its detail panel
    tbody.addEventListener('keydown', function(e) {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        var row = e.target.closest('tr');
        if (!row || row.classList.contains('detail-row')) return;
        // Don't intercept if focus is on an interactive child element (buttons, links, inputs)
        var tag = (e.target.tagName || '').toLowerCase();
        if (tag === 'button' || tag === 'a' || tag === 'input') return;
        e.preventDefault();
        row.click();
    });
}

/* === URL Hash State Management === */

function serializeState() {
    var params = [];
    if (currentSort.key !== 'total_compensation' || currentSort.dir !== 'desc') {
        params.push('sort=' + encodeURIComponent(currentSort.key));
        params.push('dir=' + encodeURIComponent(currentSort.dir));
    }
    if (activeSector) params.push('sector=' + encodeURIComponent(activeSector));
    if (searchTerm) params.push('q=' + encodeURIComponent(searchTerm));
    if (currentPage > 1) params.push('page=' + currentPage);
    if (window._activeRatioBucket) {
        params.push('rmin=' + window._activeRatioBucket.min);
        params.push('rmax=' + (window._activeRatioBucket.max === Infinity ? 'inf' : window._activeRatioBucket.max));
    }
    if (window._compareSet && window._compareSet.length > 0) {
        params.push('cmp=' + window._compareSet.map(encodeURIComponent).join(','));
    }
    if (window._activeDistFilter) {
        params.push('dmin=' + window._activeDistFilter.min);
        params.push('dmax=' + window._activeDistFilter.max);
        params.push('dsec=' + encodeURIComponent(window._activeDistFilter.sector || ''));
        params.push('dlbl=' + encodeURIComponent(window._activeDistFilter.label));
    }
    if (window._activeConcTier) {
        params.push('ctmin=' + window._activeConcTier.min);
        params.push('ctmax=' + window._activeConcTier.max);
        params.push('cttag=' + encodeURIComponent(window._activeConcTier.tag));
        params.push('ctlbl=' + encodeURIComponent(window._activeConcTier.label));
    }
    if (window._activeCeoTransitionFilter) {
        params.push('ceotrans=1');
    }
    if (window._activeTeamCompletenessFilter) {
        params.push('teamfilter=' + encodeURIComponent(window._activeTeamCompletenessFilter));
    }
    if (activeRole && activeRole !== 'CEO') {
        params.push('role=' + encodeURIComponent(activeRole));
    }
    if (_expandedDetailTicker) {
        params.push('detail=' + encodeURIComponent(_expandedDetailTicker));
    }
    return params.length > 0 ? '#' + params.join('&') : '';
}

var _stateInitialized = false;

function pushState() {
    if (!_stateInitialized) return; // Don't wipe hash before initial state is restored
    var hash = serializeState();
    if (window.location.hash !== hash) {
        // Use replaceState to avoid polluting history on every keystroke/page click
        history.replaceState(null, '', hash || window.location.pathname + window.location.search);
    }
}

function parseHash() {
    var hash = window.location.hash.replace(/^#/, '');
    if (!hash) return null;
    var state = {};
    hash.split('&').forEach(function(pair) {
        var parts = pair.split('=');
        if (parts.length === 2) state[decodeURIComponent(parts[0])] = decodeURIComponent(parts[1]);
    });
    return state;
}

function applyHashState(companies) {
    var state = parseHash();
    if (!state) return;

    // Sort
    if (state.sort) {
        currentSort.key = state.sort;
        currentSort.dir = state.dir || 'desc';
        document.querySelectorAll('th.sortable').forEach(function(t) {
            t.classList.remove('sorted-asc', 'sorted-desc');
            if (t.dataset.sort === state.sort) {
                t.classList.add(currentSort.dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
            }
        });
    }

    // Sector
    if (state.sector) {
        activeSector = state.sector;
        document.querySelectorAll('.chip').forEach(function(chip) {
            chip.classList.remove('active');
            if (chip.textContent === state.sector) chip.classList.add('active');
        });
    }

    // Search
    if (state.q) {
        searchTerm = state.q;
        document.getElementById('table-search').value = state.q;
    }

    // Ratio bucket
    if (state.rmin != null) {
        var rmax = state.rmax === 'inf' ? Infinity : parseFloat(state.rmax);
        window._activeRatioBucket = { min: parseFloat(state.rmin), max: rmax };
    }

    // Distribution filter
    if (state.dmin != null && state.dmax != null && state.dsec) {
        window._activeDistFilter = {
            min: parseFloat(state.dmin),
            max: parseFloat(state.dmax),
            sector: state.dsec,
            label: state.dlbl || state.dsec + ' (filtered)'
        };
    }

    // Concentration tier filter
    if (state.ctmin != null && state.ctmax != null) {
        window._activeConcTier = {
            min: parseFloat(state.ctmin),
            max: parseFloat(state.ctmax),
            tag: state.cttag || 'Filtered',
            label: state.ctlbl || ''
        };
    }

    // CEO transition filter
    if (state.ceotrans === '1') {
        window._activeCeoTransitionFilter = true;
    }

    // Team completeness filter
    if (state.teamfilter) {
        var tfVal = decodeURIComponent(state.teamfilter);
        if (tfVal === 'missing' || tfVal === 'complete') {
            window._activeTeamCompletenessFilter = tfVal;
        }
    }

    // Role filter
    if (state.role) {
        var validRoles = ['CFO', 'COO', 'GC/CLO', 'CTO', 'CHRO', 'CIO'];
        var roleParsed = decodeURIComponent(state.role);
        if (validRoles.indexOf(roleParsed) >= 0) {
            activeRole = roleParsed;
            updateRoleColumnHeader();
            // Update role chip active states
            document.querySelectorAll('.role-chip').forEach(function(rc) {
                rc.classList.remove('active');
                if (rc.textContent === roleParsed) rc.classList.add('active');
            });
        }
    }

    // Page (apply after filters so pagination is computed correctly)
    if (state.page) {
        currentPage = parseInt(state.page, 10) || 1;
    }

    renderTable(companies);

    // Deep-link: open detail panel for specified ticker (after table is rendered)
    if (state.detail) {
        var detailTicker = decodeURIComponent(state.detail).toUpperCase();
        _expandedDetailTicker = detailTicker;
        // Use search to find the company if not visible on current page
        var companyExists = companies.some(function(c) { return c.ticker === detailTicker; });
        if (companyExists) {
            // Set search to ticker to ensure it's on the visible page
            var needSearch = true;
            setTimeout(function() {
                var tbody = document.getElementById('comp-tbody');
                if (!tbody) return;
                // Check if already visible
                var rows = tbody.querySelectorAll('tr:not(.detail-row):not(.skeleton-table-row-tr)');
                var targetRow = null;
                rows.forEach(function(r) {
                    var te = r.querySelector('.ticker');
                    if (te && te.textContent.trim() === detailTicker) targetRow = r;
                });
                if (!targetRow && needSearch) {
                    // Force search filter to show the ticker
                    searchTerm = detailTicker;
                    document.getElementById('table-search').value = detailTicker;
                    currentPage = 1;
                    renderTable(companies);
                    // Re-query after render
                    setTimeout(function() {
                        var tbody2 = document.getElementById('comp-tbody');
                        var rows2 = tbody2.querySelectorAll('tr:not(.detail-row):not(.skeleton-table-row-tr)');
                        rows2.forEach(function(r) {
                            var te = r.querySelector('.ticker');
                            if (te && te.textContent.trim() === detailTicker) {
                                r.click();
                                setTimeout(function() {
                                    r.scrollIntoView({ behavior: getScrollBehavior(), block: 'start' });
                                    var off = getStickyOffset();
                                    if (off > 0) window.scrollBy({ top: -off - 16, behavior: getScrollBehavior() });
                                }, 100);
                            }
                        });
                    }, 50);
                } else if (targetRow) {
                    targetRow.click();
                    setTimeout(function() {
                        targetRow.scrollIntoView({ behavior: getScrollBehavior(), block: 'start' });
                        var off = getStickyOffset();
                        if (off > 0) window.scrollBy({ top: -off - 16, behavior: getScrollBehavior() });
                    }, 100);
                }
            }, 50);
        }
    }
}

/* === Skeleton Loading State === */
function showSkeletons() {
    // Metrics strip — show shimmer overlay on metric values
    document.querySelectorAll('.metric-value').forEach(function(el) {
        el.dataset.originalText = el.textContent;
        el.innerHTML = '<span class="skeleton-bar" style="display:inline-block;width:70%;height:1.3em;vertical-align:middle"></span>';
    });
    document.querySelectorAll('.metric-delta').forEach(function(el) {
        el.dataset.originalText = el.textContent;
        el.innerHTML = '<span class="skeleton-bar" style="display:inline-block;width:50%;height:0.75em;vertical-align:middle"></span>';
    });

    // Insights grid
    var insGrid = document.getElementById('insights-grid');
    if (insGrid) {
        var insHtml = '';
        for (var i = 0; i < 6; i++) {
            insHtml += '<div class="skeleton-insight-card">' +
                '<div class="skeleton-bar skeleton-insight-icon"></div>' +
                '<div class="skeleton-insight-body">' +
                '<div class="skeleton-bar skeleton-insight-label-bar"></div>' +
                '<div class="skeleton-bar skeleton-insight-value-bar"></div>' +
                '<div class="skeleton-bar skeleton-insight-detail-bar"></div>' +
                '<div class="skeleton-bar skeleton-insight-detail-bar2"></div>' +
                '</div></div>';
        }
        insGrid.innerHTML = insHtml;
    }

    // Network graph
    var netGraph = document.getElementById('network-graph');
    if (netGraph) {
        netGraph.innerHTML = '<div class="skeleton-network"><div class="skeleton-network-inner">' +
            '<div class="skeleton-network-spinner"></div>' +
            '<div class="skeleton-network-label">Loading peer network…</div>' +
            '</div></div>';
    }

    // Table body
    var tbody = document.getElementById('comp-tbody');
    if (tbody) {
        var tHtml = '';
        for (var r = 0; r < 10; r++) {
            // Vary bar widths slightly for visual interest
            var wTicker = 45 + (r % 3) * 10;
            var wCompany = 130 + (r % 4) * 20;
            var wCeo = 100 + (r % 3) * 25;
            tHtml += '<tr class="skeleton-table-row-tr"><td colspan="12"><div class="skeleton-table-row">' +
                '<div class="skeleton-bar skeleton-cell-sm"></div>' +
                '<div class="skeleton-bar skeleton-cell-ticker" style="width:' + wTicker + 'px"></div>' +
                '<div class="skeleton-bar skeleton-cell-lg" style="width:' + wCompany + 'px"></div>' +
                '<div class="skeleton-bar skeleton-cell-md" style="width:' + wCeo + 'px"></div>' +
                '<div class="skeleton-bar skeleton-cell-comp"></div>' +
                '<div class="skeleton-bar skeleton-cell-sector"></div>' +
                '<div class="skeleton-bar skeleton-cell-comp"></div>' +
                '<div class="skeleton-bar skeleton-cell-comp"></div>' +
                '</div></td></tr>';
        }
        tbody.innerHTML = tHtml;
    }

    // Charts
    var chartIds = ['sector-chart', 'trend-chart', 'ratio-chart', 'top10-chart', 'composition-chart'];
    chartIds.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) {
            el.innerHTML = '<div class="skeleton-bar skeleton-chart"></div>';
        }
    });

    // Trends grid
    var trendsGrid = document.getElementById('trends-grid');
    if (trendsGrid) {
        var trendHtml = '';
        for (var t = 0; t < 6; t++) {
            trendHtml += '<div class="skeleton-insight-card">' +
                '<div class="skeleton-bar skeleton-insight-icon"></div>' +
                '<div class="skeleton-insight-body">' +
                '<div class="skeleton-bar skeleton-insight-label-bar"></div>' +
                '<div class="skeleton-bar skeleton-insight-value-bar"></div>' +
                '<div class="skeleton-bar skeleton-insight-detail-bar"></div>' +
                '<div class="skeleton-bar skeleton-insight-detail-bar2"></div>' +
                '</div></div>';
        }
        trendsGrid.innerHTML = trendHtml;
    }

    // Table footer placeholder
    var footerEl = document.getElementById('table-footer');
    if (footerEl) {
        footerEl.innerHTML = '<span class="skeleton-bar" style="display:inline-block;width:200px;height:12px"></span>';
    }
}

function hideMetricSkeletons() {
    // Restore metric text that was replaced — actual values will overwrite in populateMetrics
    document.querySelectorAll('.metric-value').forEach(function(el) {
        if (el.dataset.originalText) el.textContent = el.dataset.originalText;
    });
    document.querySelectorAll('.metric-delta').forEach(function(el) {
        if (el.dataset.originalText) el.textContent = el.dataset.originalText;
    });
}

(async function init() {
    // Show skeletons immediately before data loads
    showSkeletons();

    var data = await loadData();
    var companies = data.comp.companies;

    // Pre-compute CEO YoY change for inline table badges
    computeCeoYoY(companies);

    // Pre-compute CEO multi-year trend for inline sparklines
    computeCeoTrend(companies);

    // Pre-compute CEO stock % for sortable column
    computeCeoStockPct(companies);

    // Pre-compute compensation percentile rank for cross-reference badges
    computeCompPercentile(companies);

    // Pre-compute CEO pay concentration (CEO % of total NEO comp + CEO premium ratio)
    computeCeoConcentration(companies);

    // Pre-compute CEO transitions (detect CEO changes between fiscal years)
    computeCeoTransitions(companies);

    // Pre-compute C-suite role benchmarks for role analysis section + detail panel context
    computeRoleBenchmarks(companies);

    // Pre-compute role-specific execs per company for role filter pivot
    computeRoleExecs(companies);

    // Pre-compute executive team completeness (C-suite role coverage per company)
    computeTeamCompleteness(companies);

    // Remove metric skeletons before populating with real data
    hideMetricSkeletons();

    populateMetrics(data.comp, data.trends);
    populateInsights(data.comp, data.trends);
    populateTrends(data.trends);
    buildSectorChips(companies);
    buildRoleChips(companies);
    renderTable(companies);
    setupSorting(companies);
    setupSearch(companies);
    setupDetailPanel(companies);

    // Expose global API for chart → table cross-section linking
    window.filterBySector = function(sectorName) {
        // Set active sector (null clears filter)
        activeSector = sectorName || null;
        currentPage = 1;

        // Update sector chip active states
        document.querySelectorAll('.chip').forEach(function(chip) {
            chip.classList.remove('active');
            if (!sectorName && chip.textContent === 'All') chip.classList.add('active');
            else if (chip.textContent === sectorName) chip.classList.add('active');
        });

        // Refresh filter chips to show/hide sector context
        updateDistFilterIndicator();
        updateRatioFilterIndicator();
        updateConcFilterIndicator();
        updateCeoTransitionFilterIndicator();
        updateTeamCompletenessFilterIndicator();

        renderTable(companies);
        pushState();

        // Highlight active bar in sector chart
        if (window.highlightSectorBar) window.highlightSectorBar(sectorName);

        // Scroll to the table section
        var section = document.getElementById('compensation-table-section');
        if (section) {
            var headerHeight = getStickyOffset();
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
        }
    };

    // Distribution percentile filter — stores active comp range for renderTable
    window._activeDistFilter = null;

    window.filterByDistribution = function(sector, minComp, maxComp, label) {
        // Toggle off if same filter clicked again
        if (window._activeDistFilter &&
            window._activeDistFilter.sector === sector &&
            window._activeDistFilter.min === minComp &&
            window._activeDistFilter.max === maxComp) {
            window._activeDistFilter = null;
        } else {
            window._activeDistFilter = { sector: sector, min: minComp, max: maxComp, label: label };
        }

        // Set sector to the clicked sector
        activeSector = window._activeDistFilter ? sector : null;
        searchTerm = '';
        currentPage = 1;
        document.getElementById('table-search').value = '';

        // Clear ratio filter
        window._activeRatioBucket = null;
        var rc = document.getElementById('ratio-filter-chip');
        if (rc) rc.remove();

        // Sort by total compensation descending
        currentSort = { key: 'total_compensation', dir: 'desc' };
        document.querySelectorAll('th.sortable').forEach(function(t) {
            t.classList.remove('sorted-asc', 'sorted-desc');
            t.setAttribute('aria-sort', 'none');
            if (t.dataset.sort === 'total_compensation') {
                t.classList.add('sorted-desc');
                t.setAttribute('aria-sort', 'descending');
            }
        });

        // Update sector chip active states
        document.querySelectorAll('.chip').forEach(function(chip) {
            chip.classList.remove('active');
            if (window._activeDistFilter && chip.textContent === sector) chip.classList.add('active');
            else if (!window._activeDistFilter && chip.textContent === 'All') chip.classList.add('active');
        });

        // Update distribution filter indicator chip
        updateDistFilterIndicator();

        renderTable(companies);
        pushState();

        // Highlight active bar in sector chart
        if (window.highlightSectorBar) window.highlightSectorBar(window._activeDistFilter ? sector : null);
        if (window.highlightRatioBucket) window.highlightRatioBucket(null);

        // Scroll to the table section
        var section = document.getElementById('compensation-table-section');
        if (section) {
            var headerHeight = getStickyOffset();
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
        }
    };

    function updateDistFilterIndicator() {
        var existing = document.getElementById('dist-filter-chip');
        if (existing) existing.remove();

        if (window._activeDistFilter) {
            var df = window._activeDistFilter;
            // Build label with sector context when combined filtering
            var isCombined = activeSector && !df.sector;
            var chipLabel = isCombined ? activeSector + ' × ' + df.label : df.label;
            var chip = document.createElement('button');
            chip.className = 'chip active combined-filter-chip';
            chip.id = 'dist-filter-chip';
            chip.style.background = isCombined ? 'rgba(167,139,250,0.15)' : 'rgba(0,180,216,0.15)';
            chip.style.borderColor = isCombined ? 'rgba(167,139,250,0.5)' : 'rgba(0,180,216,0.5)';
            chip.style.color = isCombined ? '#a78bfa' : '#00b4d8';
            chip.innerHTML = chipLabel + ' <span style="margin-left:4px;font-weight:700;">×</span>';
            chip.title = isCombined ? 'Click to clear combined sector + bracket filter' : 'Click to clear distribution filter';
            chip.addEventListener('click', function() {
                window._activeDistFilter = null;
                activeSector = null;
                chip.remove();
                document.querySelectorAll('.chip').forEach(function(c) {
                    c.classList.remove('active');
                    if (c.textContent === 'All') c.classList.add('active');
                });
                renderTable(companies);
                if (window.highlightSectorBar) window.highlightSectorBar(null);
            });
            var controls = document.querySelector('.table-controls');
            if (controls) controls.appendChild(chip);
        }
    }
    window._updateDistFilterIndicator = updateDistFilterIndicator;

    // Compensation bracket filter — filter table by clicking histogram bars
    window.filterByCompBracket = function(minComp, maxComp, label) {
        // Toggle off if same bracket clicked again
        if (window._activeDistFilter &&
            window._activeDistFilter.min === minComp &&
            window._activeDistFilter.max === maxComp &&
            !window._activeDistFilter.sector) {
            window._activeDistFilter = null;
        } else {
            window._activeDistFilter = { sector: null, min: minComp, max: maxComp, label: label };
        }

        // Clear ratio filter (mutually exclusive histogram-style filters)
        currentPage = 1;
        window._activeRatioBucket = null;
        var rc = document.getElementById('ratio-filter-chip');
        if (rc) rc.remove();

        // Sort by total compensation descending
        currentSort = { key: 'total_compensation', dir: 'desc' };
        document.querySelectorAll('th.sortable').forEach(function(t) {
            t.classList.remove('sorted-asc', 'sorted-desc');
            t.setAttribute('aria-sort', 'none');
            if (t.dataset.sort === 'total_compensation') {
                t.classList.add('sorted-desc');
                t.setAttribute('aria-sort', 'descending');
            }
        });

        updateDistFilterIndicator();
        renderTable(companies);
        pushState();
        announce(window._activeDistFilter ? 'Filtered to ' + label + ' compensation bracket' : 'Filter cleared');
    };

    // Sector filter from sector sort distribution bars
    window.filterBySectorFromBar = function(sectorName) {
        // Toggle off if same sector clicked again
        if (activeSector === sectorName) {
            activeSector = null;
        } else {
            activeSector = sectorName;
        }
        currentPage = 1;

        // Update sector chip active states
        document.querySelectorAll('.chip').forEach(function(chip) {
            chip.classList.remove('active');
            if (!activeSector && chip.textContent === 'All') chip.classList.add('active');
            else if (chip.textContent === activeSector) chip.classList.add('active');
        });

        // Refresh filter chips to show/hide sector context
        updateDistFilterIndicator();
        updateRatioFilterIndicator();
        updateConcFilterIndicator();
        updateCeoTransitionFilterIndicator();
        updateTeamCompletenessFilterIndicator();

        renderTable(companies);
        if (window.highlightSectorBar) window.highlightSectorBar(activeSector);

        // Highlight active row in sector analytics table
        var saRows = document.querySelectorAll('.sector-analytics-row');
        saRows.forEach(function(r) {
            r.classList.toggle('sa-active', r.dataset.sector === activeSector);
        });

        pushState();
        announce(activeSector ? 'Filtered to ' + activeSector : 'Sector filter cleared');
    };

    // Ratio bucket filter — stores active bucket for renderTable filtering
    window._activeRatioBucket = null;

    window.filterByRatioBucket = function(minRatio, maxRatio) {
        // Toggle off if same bucket clicked again
        if (window._activeRatioBucket && window._activeRatioBucket.min === minRatio && window._activeRatioBucket.max === maxRatio) {
            window._activeRatioBucket = null;
        } else {
            window._activeRatioBucket = { min: minRatio, max: maxRatio };
        }

        // Clear dist filter (mutually exclusive histogram-style filters), preserve sector
        currentPage = 1;
        window._activeDistFilter = null;
        var distChip = document.getElementById('dist-filter-chip');
        if (distChip) distChip.remove();

        // Sort by pay ratio descending
        currentSort = { key: 'pay_ratio', dir: 'desc' };
        document.querySelectorAll('th.sortable').forEach(function(t) {
            t.classList.remove('sorted-asc', 'sorted-desc');
            if (t.dataset.sort === 'pay_ratio') t.classList.add('sorted-desc');
        });

        // Update ratio filter indicator
        updateRatioFilterIndicator();

        renderTable(companies);

        // Highlight active ratio bucket in histogram
        if (window.highlightRatioBucket) {
            if (window._activeRatioBucket) {
                window.highlightRatioBucket(window._activeRatioBucket.min, window._activeRatioBucket.max);
            } else {
                window.highlightRatioBucket(null);
            }
        }

        // Scroll to the table section
        var section = document.getElementById('compensation-table-section');
        if (section) {
            var headerHeight = getStickyOffset();
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
        }
    };

    function updateRatioFilterIndicator() {
        // Add or remove a ratio filter chip in the table controls
        var existing = document.getElementById('ratio-filter-chip');
        if (existing) existing.remove();

        if (window._activeRatioBucket) {
            var bucket = window._activeRatioBucket;
            var baseLabel = 'Ratio: ' + bucket.min + (bucket.max === Infinity ? '+' : '–' + bucket.max) + ':1';
            // Build label with sector context when combined filtering
            var isCombined = !!activeSector;
            var label = isCombined ? activeSector + ' × ' + baseLabel : baseLabel;
            var chip = document.createElement('button');
            chip.className = 'chip active combined-filter-chip';
            chip.id = 'ratio-filter-chip';
            chip.style.background = isCombined ? 'rgba(167,139,250,0.15)' : 'rgba(239,71,111,0.15)';
            chip.style.borderColor = isCombined ? 'rgba(167,139,250,0.5)' : 'rgba(239,71,111,0.5)';
            chip.style.color = isCombined ? '#a78bfa' : '#ef476f';
            chip.innerHTML = label + ' <span style="margin-left:4px;font-weight:700;">×</span>';
            chip.title = isCombined ? 'Click to clear combined sector + ratio filter' : 'Click to clear ratio filter';
            chip.addEventListener('click', function() {
                window._activeRatioBucket = null;
                chip.remove();
                renderTable(companies);
                if (window.highlightRatioBucket) window.highlightRatioBucket(null);
            });
            var controls = document.querySelector('.table-controls');
            if (controls) controls.appendChild(chip);
        }
    }
    window._updateRatioFilterIndicator = updateRatioFilterIndicator;

    // CEO Concentration tier filter — filter table by clicking histogram bars in conc sort summary
    window.filterByConcTier = function(minPct, maxPct, tag, label) {
        // Toggle off if same tier clicked again
        if (window._activeConcTier && window._activeConcTier.min === minPct && window._activeConcTier.max === maxPct) {
            window._activeConcTier = null;
        } else {
            window._activeConcTier = { min: minPct, max: maxPct, tag: tag, label: label };
        }

        currentPage = 1;

        // Sort by CEO concentration descending
        currentSort = { key: '_ceoConcPct', dir: 'desc' };
        document.querySelectorAll('th.sortable').forEach(function(t) {
            t.classList.remove('sorted-asc', 'sorted-desc');
            t.setAttribute('aria-sort', 'none');
            if (t.dataset.sort === '_ceoConcPct') {
                t.classList.add('sorted-desc');
                t.setAttribute('aria-sort', 'descending');
            }
        });

        updateConcFilterIndicator();
        updateTeamCompletenessFilterIndicator();
        renderTable(companies);
        pushState();
        announce(window._activeConcTier ? 'Filtered to ' + tag + ' CEO concentration (' + label + ')' : 'Concentration filter cleared');
    };

    function updateConcFilterIndicator() {
        var existing = document.getElementById('conc-filter-chip');
        if (existing) existing.remove();

        if (window._activeConcTier) {
            var ct = window._activeConcTier;
            var isCombined = !!activeSector;
            var chipLabel = isCombined ? activeSector + ' × ' + ct.tag : ct.tag + ' (' + ct.label + ')';
            var tierColor = ct.min >= 50 ? '#ef476f' : (ct.min >= 35 ? '#ffd166' : '#06d6a0');
            var chip = document.createElement('button');
            chip.className = 'chip active combined-filter-chip';
            chip.id = 'conc-filter-chip';
            chip.style.background = isCombined ? 'rgba(167,139,250,0.15)' : hexToChipBg(tierColor);
            chip.style.borderColor = isCombined ? 'rgba(167,139,250,0.5)' : hexToChipBorder(tierColor);
            chip.style.color = isCombined ? '#a78bfa' : tierColor;
            chip.innerHTML = chipLabel + ' <span style="margin-left:4px;font-weight:700;">×</span>';
            chip.title = isCombined ? 'Click to clear combined sector + concentration filter' : 'Click to clear concentration tier filter';
            chip.addEventListener('click', function() {
                window._activeConcTier = null;
                chip.remove();
                renderTable(companies);
            });
            var controls = document.querySelector('.table-controls');
            if (controls) controls.appendChild(chip);
        }
    }
    window._updateConcFilterIndicator = updateConcFilterIndicator;

    // YoY bucket filter — filter table by clicking bars in YoY distribution chart
    window._activeYoYBucket = null;

    window.filterByYoYBucket = function(minPct, maxPct, label) {
        // Toggle off if same bucket clicked again
        if (window._activeYoYBucket && window._activeYoYBucket.min === minPct && window._activeYoYBucket.max === maxPct) {
            window._activeYoYBucket = null;
        } else {
            window._activeYoYBucket = { min: minPct, max: maxPct, label: label };
        }

        currentPage = 1;

        // Sort by YoY descending
        currentSort = { key: '_ceoYoYSort', dir: 'desc' };
        document.querySelectorAll('th.sortable').forEach(function(t) {
            t.classList.remove('sorted-asc', 'sorted-desc');
            t.setAttribute('aria-sort', 'none');
            if (t.dataset.sort === '_ceoYoYSort') {
                t.classList.add('sorted-desc');
                t.setAttribute('aria-sort', 'descending');
            }
        });

        updateYoYFilterIndicator();
        renderTable(companies);
        pushState();
        announce(window._activeYoYBucket ? 'Filtered to YoY ' + label : 'YoY filter cleared');
    };

    function updateYoYFilterIndicator() {
        var existing = document.getElementById('yoy-filter-chip');
        if (existing) existing.remove();

        if (window._activeYoYBucket) {
            var yb = window._activeYoYBucket;
            var isCombined = !!activeSector;
            var chipLabel = isCombined ? activeSector + ' × YoY ' + yb.label : 'YoY: ' + yb.label;
            var chip = document.createElement('button');
            chip.className = 'chip active combined-filter-chip';
            chip.id = 'yoy-filter-chip';
            chip.style.background = isCombined ? 'rgba(167,139,250,0.15)' : 'rgba(0,180,216,0.15)';
            chip.style.borderColor = isCombined ? 'rgba(167,139,250,0.5)' : 'rgba(0,180,216,0.5)';
            chip.style.color = isCombined ? '#a78bfa' : '#00b4d8';
            chip.innerHTML = chipLabel + ' <span style="margin-left:4px;font-weight:700;">×</span>';
            chip.title = 'Click to clear YoY filter';
            chip.addEventListener('click', function() {
                window._activeYoYBucket = null;
                chip.remove();
                renderTable(companies);
            });
            var controls = document.querySelector('.table-controls');
            if (controls) controls.appendChild(chip);
        }
    }
    window._updateYoYFilterIndicator = updateYoYFilterIndicator;

    // CEO Transition filter — toggle to show only companies with CEO changes
    window.filterByCeoTransition = function() {
        window._activeCeoTransitionFilter = !window._activeCeoTransitionFilter;
        currentPage = 1;

        // Sort by total compensation descending when activating
        if (window._activeCeoTransitionFilter) {
            currentSort = { key: 'total_compensation', dir: 'desc' };
            document.querySelectorAll('th.sortable').forEach(function(t) {
                t.classList.remove('sorted-asc', 'sorted-desc');
                t.setAttribute('aria-sort', 'none');
                if (t.dataset.sort === 'total_compensation') {
                    t.classList.add('sorted-desc');
                    t.setAttribute('aria-sort', 'descending');
                }
            });
        }

        updateCeoTransitionFilterIndicator();
        renderTable(companies);
        pushState();
        announce(window._activeCeoTransitionFilter ? 'Filtered to companies with CEO transitions' : 'CEO transition filter cleared');

        // Scroll to table
        var section = document.getElementById('compensation-table-section');
        if (section) {
            var headerHeight = getStickyOffset();
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
        }
    };

    function updateCeoTransitionFilterIndicator() {
        var existing = document.getElementById('transition-filter-chip');
        if (existing) existing.remove();

        if (window._activeCeoTransitionFilter) {
            var isCombined = !!activeSector;
            var chipLabel = isCombined ? activeSector + ' × CEO Transitions' : 'CEO Transitions';
            var chip = document.createElement('button');
            chip.className = 'chip active combined-filter-chip';
            chip.id = 'transition-filter-chip';
            chip.style.background = isCombined ? 'rgba(167,139,250,0.15)' : 'rgba(251,146,60,0.15)';
            chip.style.borderColor = isCombined ? 'rgba(167,139,250,0.5)' : 'rgba(251,146,60,0.5)';
            chip.style.color = isCombined ? '#a78bfa' : '#fb923c';
            chip.innerHTML = chipLabel + ' <span style="margin-left:4px;font-weight:700;">×</span>';
            chip.title = isCombined ? 'Click to clear combined sector + transition filter' : 'Click to clear CEO transition filter';
            chip.addEventListener('click', function() {
                window._activeCeoTransitionFilter = false;
                chip.remove();
                renderTable(companies);
                pushState();
            });
            var controls = document.querySelector('.table-controls');
            if (controls) controls.appendChild(chip);
        }
    }
    window._updateCeoTransitionFilterIndicator = updateCeoTransitionFilterIndicator;

    // Team Completeness filter — toggle to show only companies missing expected roles or with complete teams
    window.filterByTeamCompleteness = function(mode) {
        // mode: 'missing' = companies missing expected roles (CEO/CFO), 'complete' = 4+ roles
        // Toggle off if same mode re-clicked
        if (window._activeTeamCompletenessFilter === mode) {
            window._activeTeamCompletenessFilter = null;
        } else {
            window._activeTeamCompletenessFilter = mode;
        }
        currentPage = 1;

        // Sort by total compensation descending when activating
        if (window._activeTeamCompletenessFilter) {
            currentSort = { key: 'total_compensation', dir: 'desc' };
            document.querySelectorAll('th.sortable').forEach(function(t) {
                t.classList.remove('sorted-asc', 'sorted-desc');
                t.setAttribute('aria-sort', 'none');
                if (t.dataset.sort === 'total_compensation') {
                    t.classList.add('sorted-desc');
                    t.setAttribute('aria-sort', 'descending');
                }
            });
        }

        updateTeamCompletenessFilterIndicator();
        renderTable(companies);
        pushState();

        var msg = window._activeTeamCompletenessFilter
            ? 'Filtered to companies ' + (window._activeTeamCompletenessFilter === 'missing' ? 'missing expected C-suite roles' : 'with 4+ C-suite roles')
            : 'Team completeness filter cleared';
        announce(msg);

        // Scroll to table
        var section = document.getElementById('compensation-table-section');
        if (section) {
            var headerHeight = getStickyOffset();
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
        }
    };

    function updateTeamCompletenessFilterIndicator() {
        var existing = document.getElementById('team-filter-chip');
        if (existing) existing.remove();

        if (window._activeTeamCompletenessFilter) {
            var isCombined = !!activeSector;
            var modeLabel = window._activeTeamCompletenessFilter === 'missing' ? 'Missing Roles' : 'Complete Teams';
            var chipLabel = isCombined ? activeSector + ' × ' + modeLabel : modeLabel;
            var chipColor = window._activeTeamCompletenessFilter === 'missing' ? '#f472b6' : '#34d399';
            var chip = document.createElement('button');
            chip.className = 'chip active combined-filter-chip';
            chip.id = 'team-filter-chip';
            chip.style.background = isCombined ? 'rgba(167,139,250,0.15)' : hexToChipBg(chipColor);
            chip.style.borderColor = isCombined ? 'rgba(167,139,250,0.5)' : hexToChipBorder(chipColor);
            chip.style.color = isCombined ? '#a78bfa' : chipColor;
            chip.innerHTML = chipLabel + ' <span style="margin-left:4px;font-weight:700;">×</span>';
            chip.title = isCombined ? 'Click to clear combined sector + team filter' : 'Click to clear team completeness filter';
            chip.addEventListener('click', function() {
                window._activeTeamCompletenessFilter = null;
                chip.remove();
                renderTable(companies);
                pushState();
            });
            var controls = document.querySelector('.table-controls');
            if (controls) controls.appendChild(chip);
        }
    }
    window._updateTeamCompletenessFilterIndicator = updateTeamCompletenessFilterIndicator;

    // Helper to derive rgba chip background from hex color
    function hexToChipBg(hex) {
        var r = parseInt(hex.slice(1,3), 16), g = parseInt(hex.slice(3,5), 16), b = parseInt(hex.slice(5,7), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',0.15)';
    }
    function hexToChipBorder(hex) {
        var r = parseInt(hex.slice(1,3), 16), g = parseInt(hex.slice(3,5), 16), b = parseInt(hex.slice(5,7), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',0.5)';
    }

    // Find a specific company in the table by ticker — used by Top 10 chart click
    window.findCompanyInTable = function(ticker) {
        // Clear filters to ensure company is visible
        activeSector = null;
        searchTerm = '';
        if (window._activeRatioBucket) {
            window._activeRatioBucket = null;
            var rc = document.getElementById('ratio-filter-chip');
            if (rc) rc.remove();
        }
        if (window._activeDistFilter) {
            window._activeDistFilter = null;
            var dc = document.getElementById('dist-filter-chip');
            if (dc) dc.remove();
        }
        if (window._activeConcTier) {
            window._activeConcTier = null;
            var cc2 = document.getElementById('conc-filter-chip');
            if (cc2) cc2.remove();
        }
        if (window._activeTeamCompletenessFilter) {
            window._activeTeamCompletenessFilter = null;
            var tfc2 = document.getElementById('team-filter-chip');
            if (tfc2) tfc2.remove();
        }
        document.getElementById('table-search').value = ticker;
        searchTerm = ticker;
        currentPage = 1;

        document.querySelectorAll('.chip').forEach(function(chip) {
            chip.classList.remove('active');
            if (chip.textContent === 'All') chip.classList.add('active');
        });

        renderTable(companies);
        if (window.highlightSectorBar) window.highlightSectorBar(null);
        if (window.highlightRatioBucket) window.highlightRatioBucket(null);

        // Scroll to the table section
        var section = document.getElementById('compensation-table-section');
        if (section) {
            var headerHeight = getStickyOffset();
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
        }

        // Auto-click the first matching row after a short delay to expand its detail panel
        setTimeout(function() {
            var rows = document.querySelectorAll('#comp-tbody tr:not(.detail-row)');
            for (var i = 0; i < rows.length; i++) {
                var tickerEl = rows[i].querySelector('.ticker');
                if (tickerEl && tickerEl.textContent.trim() === ticker) {
                    rows[i].click();
                    break;
                }
            }
        }, 100);
    };

    if (typeof initNetwork === 'function') {
        initNetwork(data.peer);
    }
    if (typeof initCharts === 'function') {
        initCharts(companies, data.trends, data.comp);
    }

    // === Sector Analytics Summary Table (sortable) ===
    (function renderSectorAnalytics() {
        var tbody = document.getElementById('sector-analytics-tbody');
        var thead = document.querySelector('#sector-analytics-table thead');
        if (!tbody) return;

        // Current sort state for sector analytics table
        var saSort = { key: 'median', dir: 'desc' };

        // Compute per-sector metrics (once)
        var sectorMap = {};
        companies.forEach(function(c) {
            if (!c.sector) return;
            if (!sectorMap[c.sector]) sectorMap[c.sector] = [];
            sectorMap[c.sector].push(c);
        });

        var saRows = [];
        Object.keys(sectorMap).forEach(function(sector) {
            var comps = sectorMap[sector];
            var count = comps.length;

            // CEO pay values (filter out nulls)
            var pays = comps.map(function(c) { return c.total_compensation; }).filter(function(v) { return v != null && v > 0; }).sort(function(a, b) { return a - b; });
            var median = pays.length ? pays[Math.floor(pays.length / 2)] : 0;
            var mean = pays.length ? pays.reduce(function(a, b) { return a + b; }, 0) / pays.length : 0;

            // Equity % — compute per company
            var eqPcts = [];
            comps.forEach(function(c) {
                if (!c.executives || !c.executives.length) return;
                var latestYear = Math.max.apply(null, c.executives.map(function(e) { return e.year || 0; }));
                var ceoExecs = c.executives.filter(function(e) { return e.year === latestYear; });
                // Find CEO by title
                var ceo = ceoExecs.find(function(e) { return /chief executive|\\bceo\\b/i.test(e.title || ''); });
                if (!ceo) ceo = ceoExecs.reduce(function(a, b) { return (a.total || 0) > (b.total || 0) ? a : b; }, ceoExecs[0]);
                if (ceo && ceo.total > 0) {
                    var equity = ((ceo.stock_awards || 0) + (ceo.option_awards || 0));
                    eqPcts.push(Math.round(equity / ceo.total * 100));
                }
            });
            eqPcts.sort(function(a, b) { return a - b; });
            var medianEq = eqPcts.length ? eqPcts[Math.floor(eqPcts.length / 2)] : null;

            // Pay ratio
            var ratios = comps.map(function(c) { return c.pay_ratio; }).filter(function(v) { return v != null && v > 0; }).sort(function(a, b) { return a - b; });
            var medianRatio = ratios.length ? ratios[Math.floor(ratios.length / 2)] : null;

            // Highest paid CEO
            var highest = comps.reduce(function(best, c) {
                return (c.total_compensation || 0) > (best.total_compensation || 0) ? c : best;
            }, comps[0]);

            saRows.push({
                sector: sector,
                count: count,
                median: median,
                mean: mean,
                medianEq: medianEq,
                medianRatio: medianRatio,
                highestName: highest ? highest.ceo_name : '—',
                highestTicker: highest ? highest.ticker : '',
                highestPay: highest ? highest.total_compensation : 0
            });
        });

        function fmt(v) {
            if (v == null || v <= 0) return '—';
            if (v >= 1e9) return '$' + (v / 1e9).toFixed(1) + 'B';
            if (v >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M';
            if (v >= 1e3) return '$' + (v / 1e3).toFixed(0) + 'K';
            return '$' + v.toLocaleString();
        }

        // Render rows with current sort
        function renderSARows() {
            // Sort rows
            var sorted = saRows.slice();
            sorted.sort(function(a, b) {
                var av = a[saSort.key];
                var bv = b[saSort.key];
                // Handle nulls — push to bottom
                if (av == null) av = saSort.dir === 'asc' ? Infinity : -Infinity;
                if (bv == null) bv = saSort.dir === 'asc' ? Infinity : -Infinity;
                if (typeof av === 'string') av = av.toLowerCase();
                if (typeof bv === 'string') bv = bv.toLowerCase();
                if (av < bv) return saSort.dir === 'asc' ? -1 : 1;
                if (av > bv) return saSort.dir === 'asc' ? 1 : -1;
                return 0;
            });

            var maxMedian = Math.max.apply(null, saRows.map(function(r) { return r.median; }));

            tbody.innerHTML = sorted.map(function(r) {
                var barW = maxMedian > 0 ? Math.round(r.median / maxMedian * 100) : 0;
                var eqClass = r.medianEq != null ? (r.medianEq >= 70 ? 'eq-high' : r.medianEq >= 40 ? 'eq-mid' : 'eq-low') : '';
                var ratioClass = r.medianRatio != null ? (r.medianRatio > 500 ? 'ratio-high' : r.medianRatio > 200 ? 'ratio-mid' : 'ratio-low') : '';
                var isActive = activeSector === r.sector;
                return '<tr class="sector-analytics-row' + (isActive ? ' sa-active' : '') + '" data-sector="' + r.sector + '" tabindex="0">' +
                    '<td class="sa-sector"><span class="sa-sector-dot" style="background:' + getSectorColor(r.sector) + '"></span>' + r.sector + '</td>' +
                    '<td class="sa-count">' + r.count + '</td>' +
                    '<td class="sa-pay"><div class="sa-bar-cell"><div class="sa-bar" style="width:' + barW + '%"></div><span class="sa-bar-val">' + fmt(r.median) + '</span></div></td>' +
                    '<td class="sa-pay">' + fmt(r.mean) + '</td>' +
                    '<td class="sa-eq ' + eqClass + '">' + (r.medianEq != null ? r.medianEq + '%' : '—') + '</td>' +
                    '<td class="sa-ratio ' + ratioClass + '">' + (r.medianRatio != null ? r.medianRatio.toLocaleString() + ':1' : '—') + '</td>' +
                    '<td class="sa-ceo" title="' + r.highestTicker + '">' + (r.highestName || '—') + '</td>' +
                    '<td class="sa-pay">' + fmt(r.highestPay) + '</td>' +
                    '</tr>';
            }).join('');
        }

        // Update header sort indicators
        function updateSAHeaders() {
            if (!thead) return;
            thead.querySelectorAll('.sa-sortable').forEach(function(th) {
                th.classList.remove('sa-sorted-asc', 'sa-sorted-desc');
                th.setAttribute('aria-sort', 'none');
                if (th.dataset.saSort === saSort.key) {
                    th.classList.add(saSort.dir === 'asc' ? 'sa-sorted-asc' : 'sa-sorted-desc');
                    th.setAttribute('aria-sort', saSort.dir === 'asc' ? 'ascending' : 'descending');
                }
            });
        }

        // Initial render
        renderSARows();
        updateSAHeaders();

        // Sort handler for header clicks
        function handleSASort(th) {
            var key = th.dataset.saSort;
            if (!key) return;
            if (saSort.key === key) {
                // Toggle direction
                saSort.dir = saSort.dir === 'asc' ? 'desc' : 'asc';
            } else {
                // New column — default direction: desc for numeric, asc for text
                saSort.key = key;
                saSort.dir = (key === 'sector' || key === 'highestName') ? 'asc' : 'desc';
            }
            updateSAHeaders();
            renderSARows();
            var sortLabel = th.textContent.replace(/[↑↓▲▼]/g, '').trim();
            announce('Sector analytics sorted by ' + sortLabel + ', ' + (saSort.dir === 'asc' ? 'ascending' : 'descending'));
        }

        // Wire up header click and keyboard handlers
        if (thead) {
            thead.querySelectorAll('.sa-sortable').forEach(function(th) {
                th.addEventListener('click', function(e) {
                    e.stopPropagation();
                    handleSASort(th);
                });
                th.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        e.stopPropagation();
                        handleSASort(th);
                    }
                });
            });
        }

        // Click to filter main table by sector (on tbody rows only)
        tbody.addEventListener('click', function(ev) {
            var row = ev.target.closest('.sector-analytics-row');
            if (!row) return;
            var sector = row.dataset.sector;
            if (sector) {
                // Toggle sector filter
                if (activeSector === sector) {
                    activeSector = null;
                } else {
                    activeSector = sector;
                }
                currentPage = 1;

                // Refresh combined filter chips to include/exclude sector context
                if (window._updateDistFilterIndicator) window._updateDistFilterIndicator();
                if (window._updateRatioFilterIndicator) window._updateRatioFilterIndicator();
                if (window._updateConcFilterIndicator) window._updateConcFilterIndicator();
                if (window._updateCeoTransitionFilterIndicator) window._updateCeoTransitionFilterIndicator();
        if (window._updateTeamCompletenessFilterIndicator) window._updateTeamCompletenessFilterIndicator();

                renderTable(companies);

                // Update sector chip active states
                document.querySelectorAll('.chip').forEach(function(chip) {
                    chip.classList.remove('active');
                    if (!activeSector && chip.textContent === 'All') chip.classList.add('active');
                    else if (chip.textContent === activeSector) chip.classList.add('active');
                });

                if (window.highlightSectorBar) window.highlightSectorBar(activeSector);

                // Highlight active row in sector analytics table
                tbody.querySelectorAll('.sector-analytics-row').forEach(function(r) {
                    r.classList.toggle('sa-active', r.dataset.sector === activeSector);
                });

                // Scroll to table
                var tableSection = document.getElementById('compensation-table-section');
                if (tableSection) {
                    var hh = getStickyOffset();
                    var tp = tableSection.getBoundingClientRect().top + window.scrollY - hh - 12;
                    window.scrollTo({ top: tp, behavior: getScrollBehavior() });
                }
            }
        });

        // Keyboard support for row clicks
        tbody.addEventListener('keydown', function(ev) {
            if (ev.key === 'Enter' || ev.key === ' ') {
                ev.preventDefault();
                var row = ev.target.closest('.sector-analytics-row');
                if (row) row.click();
            }
        });
    })();

    // === Sector × Component Compensation Heatmap ===
    function renderSectorCompHeatmap() {
        var container = document.getElementById('sector-comp-heatmap');
        if (!container) return;

        var COMP_KEYS = [
            { key: 'salary', label: 'Salary', color: '#06d6a0' },
            { key: 'stock_awards', label: 'Stock', color: '#00b4d8' },
            { key: 'option_awards', label: 'Options', color: '#0096c7' },
            { key: 'non_equity_incentive', label: 'Incentive', color: '#a78bfa' },
            { key: 'bonus', label: 'Bonus', color: '#8b5cf6' },
            { key: 'all_other', label: 'Other', color: '#ffd166' }
        ];

        // Group companies by sector and compute CEO component medians
        var sectorMap = {};
        companies.forEach(function(c) {
            if (!c.sector || !c.executives || c.executives.length === 0) return;
            if (!sectorMap[c.sector]) sectorMap[c.sector] = [];

            // Find CEO in latest year
            var allYears = [];
            c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
            allYears.sort(function(a, b) { return b - a; });
            var latestExecs = c.executives.filter(function(e) { return e.year === allYears[0]; });

            var ceo = latestExecs.find(function(e) {
                return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
            });
            if (!ceo && latestExecs.length > 0) {
                ceo = latestExecs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
            }
            if (ceo && ceo.total && ceo.total > 0) sectorMap[c.sector].push(ceo);
        });

        function median(arr) {
            if (!arr.length) return 0;
            var s = arr.slice().sort(function(a, b) { return a - b; });
            var mid = Math.floor(s.length / 2);
            return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
        }

        // Build sector rows with median component %
        var sectorRows = [];
        var allSectors = Object.keys(sectorMap).sort(function(a, b) {
            var medA = median(sectorMap[a].map(function(e) { return e.total; }));
            var medB = median(sectorMap[b].map(function(e) { return e.total; }));
            return medB - medA;
        });

        var globalMaxPct = 0;
        allSectors.forEach(function(sector) {
            var ceos = sectorMap[sector];
            var row = { sector: sector, count: ceos.length, medianTotal: median(ceos.map(function(e) { return e.total; })), components: {} };
            COMP_KEYS.forEach(function(ck) {
                var pcts = ceos.map(function(e) {
                    var val = e[ck.key] || 0;
                    return e.total > 0 ? (val / e.total * 100) : 0;
                });
                var medPct = median(pcts);
                var medDollar = median(ceos.map(function(e) { return e[ck.key] || 0; }));
                row.components[ck.key] = { pct: medPct, dollar: medDollar };
                if (medPct > globalMaxPct) globalMaxPct = medPct;
            });
            sectorRows.push(row);
        });

        // Render table
        var html = '<div class="sector-comp-heatmap-wrapper"><table class="sector-comp-heatmap" aria-label="Compensation component mix by sector"><thead><tr>';
        html += '<th class="hm-sector-th">Sector</th>';
        COMP_KEYS.forEach(function(ck) {
            html += '<th>' + ck.label + '</th>';
        });
        html += '<th>Median Total</th></tr></thead><tbody>';

        sectorRows.forEach(function(row) {
            html += '<tr>';
            var sColor = getSectorColor(row.sector);
            html += '<td class="hm-sector-label" data-sector="' + row.sector + '" title="Click to filter table to ' + row.sector + ' (' + row.count + ' companies)"><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:' + sColor + ';margin-right:6px;vertical-align:middle;"></span>' + row.sector + '</td>';

            COMP_KEYS.forEach(function(ck) {
                var comp = row.components[ck.key];
                if (comp.pct < 0.5) {
                    html += '<td><div class="hm-cell hm-zero" title="' + ck.label + ': <0.5% in ' + row.sector + '"><span class="hm-cell-val">—</span></div></td>';
                    return;
                }
                // Color intensity: opacity 0.2 (low) to 0.9 (high), scaled by component's max across sectors
                var intensity = Math.min(0.92, 0.18 + (comp.pct / globalMaxPct) * 0.74);
                var bgColor = hexToRgba(ck.color, intensity);
                // Text contrast: light text on dark backgrounds, dark on light
                var textColor = intensity > 0.55 ? '#fff' : (isDarkTheme() ? '#e4e4e7' : '#1a1a2e');
                var title = row.sector + ' — ' + ck.label + ': ' + comp.pct.toFixed(1) + '% (median ' + formatCompact(comp.dollar) + ')';
                html += '<td><div class="hm-cell" style="background:' + bgColor + ';color:' + textColor + '" data-sector="' + row.sector + '" data-component="' + ck.key + '" title="' + title + '"><span class="hm-cell-val">' + Math.round(comp.pct) + '%</span><span class="hm-cell-dollar">' + formatCompact(comp.dollar) + '</span></div></td>';
            });

            html += '<td class="hm-total">' + formatCurrency(row.medianTotal) + '</td>';
            html += '</tr>';
        });
        html += '</tbody></table></div>';

        // Color scale legend
        html += '<div class="hm-footer">';
        COMP_KEYS.forEach(function(ck) {
            html += '<span class="hm-footer-stat"><span class="hm-footer-swatch" style="background:' + ck.color + '"></span>' + ck.label + '</span>';
        });
        html += '</div>';

        container.innerHTML = html;

        // Click handlers: sector labels → filter table
        container.querySelectorAll('.hm-sector-label').forEach(function(td) {
            td.addEventListener('click', function() {
                var sector = td.dataset.sector;
                if (window.filterBySector) window.filterBySector(sector);
            });
        });

        // Click handlers: cells → filter table to sector + sort by stock %
        container.querySelectorAll('.hm-cell:not(.hm-zero)').forEach(function(cell) {
            cell.addEventListener('click', function() {
                var sector = cell.dataset.sector;
                if (window.filterBySector) window.filterBySector(sector);
            });
        });
    }
    renderSectorCompHeatmap();
    window._redrawSectorHeatmap = renderSectorCompHeatmap;

    // === C-Suite Role Compensation Analysis ===
    (function renderRoleCompAnalysis() {
        var container = document.getElementById('role-comp-chart');
        if (!container || !_roleBenchmarks) return;

        var ceoMedian = _roleBenchmarks['CEO'] ? _roleBenchmarks['CEO'].median : 1;
        var maxMedian = 0;
        ROLE_ORDER.forEach(function(role) {
            if (_roleBenchmarks[role] && _roleBenchmarks[role].median > maxMedian) maxMedian = _roleBenchmarks[role].median;
        });

        var html = '<div class="role-chart-container">';

        // Horizontal bar chart
        html += '<div class="role-bars">';
        ROLE_ORDER.forEach(function(role) {
            var rb = _roleBenchmarks[role];
            if (!rb || role === 'Other') return; // Skip 'Other' in bars, show in table below
            var barW = maxMedian > 0 ? (rb.median / maxMedian * 100) : 0;
            var vsCeo = ceoMedian > 0 ? (rb.median / ceoMedian * 100).toFixed(0) : '—';
            var color = ROLE_COLORS[role] || '#94a3b8';
            var tooltip = role + ': Median ' + formatCurrency(rb.median) + ' (' + rb.count + ' execs across S&P 500). ' + vsCeo + '% of CEO median.';

            html += '<div class="role-bar-row" title="' + tooltip.replace(/"/g, '&quot;') + '">';
            html += '<div class="role-bar-label">';
            html += '<span class="role-bar-name">' + role + '</span>';
            html += '<span class="role-bar-count">' + rb.count + '</span>';
            html += '</div>';
            html += '<div class="role-bar-track">';
            // IQR range bar (P25-P75)
            var iqrLeft = maxMedian > 0 ? (rb.p25 / maxMedian * 100) : 0;
            var iqrWidth = maxMedian > 0 ? ((rb.p75 - rb.p25) / maxMedian * 100) : 0;
            html += '<div class="role-bar-iqr" style="left:' + iqrLeft.toFixed(1) + '%;width:' + iqrWidth.toFixed(1) + '%;background:' + hexToRgba(color, 0.18) + ';border:1px solid ' + hexToRgba(color, 0.35) + '" title="P25–P75: ' + formatCompact(rb.p25) + ' – ' + formatCompact(rb.p75) + '"></div>';
            // Median bar
            html += '<div class="role-bar-fill" style="width:' + barW.toFixed(1) + '%;background:' + color + '"></div>';
            // Median marker line
            html += '</div>';
            html += '<div class="role-bar-value">';
            html += '<span class="role-bar-median">' + formatCompact(rb.median) + '</span>';
            if (role !== 'CEO') {
                html += '<span class="role-bar-ratio">' + vsCeo + '% of CEO</span>';
            }
            html += '</div>';
            html += '</div>';
        });
        html += '</div>';

        // Role summary table
        html += '<div class="role-table-wrap"><table class="role-table" aria-label="C-Suite role compensation benchmarks">';
        html += '<thead><tr><th>Role</th><th class="role-num">Count</th><th class="role-num">Median</th><th class="role-num">Mean</th><th class="role-num">P25</th><th class="role-num">P75</th><th class="role-num">vs CEO</th><th>Highest Paid</th></tr></thead>';
        html += '<tbody>';
        ROLE_ORDER.forEach(function(role) {
            var rb = _roleBenchmarks[role];
            if (!rb) return;
            var color = ROLE_COLORS[role] || '#94a3b8';
            var vsCeo = role === 'CEO' ? '—' : (ceoMedian > 0 ? (rb.median / ceoMedian * 100).toFixed(0) + '%' : '—');
            var topName = rb.topEarner ? rb.topEarner.name : '—';
            var topTicker = rb.topEarner ? rb.topEarner.ticker : '';
            var topVal = rb.topEarner ? formatCompact(rb.topEarner.total) : '—';

            html += '<tr>';
            html += '<td><span class="role-dot" style="background:' + color + '"></span>' + role + '</td>';
            html += '<td class="role-num">' + rb.count + '</td>';
            html += '<td class="role-num">' + formatCompact(rb.median) + '</td>';
            html += '<td class="role-num">' + formatCompact(rb.mean) + '</td>';
            html += '<td class="role-num">' + formatCompact(rb.p25) + '</td>';
            html += '<td class="role-num">' + formatCompact(rb.p75) + '</td>';
            html += '<td class="role-num">' + vsCeo + '</td>';
            html += '<td class="role-top-earner">' + topName + (topTicker ? ' <span class="role-top-ticker">(' + topTicker + ')</span>' : '') + ' <span class="role-top-val">' + topVal + '</span></td>';
            html += '</tr>';
        });
        html += '</tbody></table></div>';

        html += '</div>';
        container.innerHTML = html;
    })();

    function hexToRgba(hex, alpha) {
        var r = parseInt(hex.slice(1, 3), 16);
        var g = parseInt(hex.slice(3, 5), 16);
        var b = parseInt(hex.slice(5, 7), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha.toFixed(2) + ')';
    }

    // === Role × Sector Compensation Heatmap ===
    function renderRoleSectorHeatmap() {
        var container = document.getElementById('role-sector-heatmap');
        if (!container) return;

        var ROLES_DISPLAY = ROLE_ORDER.filter(function(r) { return r !== 'Other'; });
        // 7 roles: CEO, CFO, COO, GC/CLO, CTO, CHRO, CIO

        // Build sector → role → [totals] map from latest-year NEO data
        var sectorRoleMap = {};
        companies.forEach(function(c) {
            if (!c.sector || !c.executives || c.executives.length === 0) return;
            if (!sectorRoleMap[c.sector]) sectorRoleMap[c.sector] = {};

            // Find latest year
            var allYears = [];
            c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
            var maxYr = Math.max.apply(null, allYears);

            c.executives.filter(function(e) { return e.year === maxYr; }).forEach(function(e) {
                var role = classifyExecRole(e.title);
                if (role === 'Other') return;
                if (!sectorRoleMap[c.sector][role]) sectorRoleMap[c.sector][role] = [];
                sectorRoleMap[c.sector][role].push({
                    total: e.total || 0, name: e.name, ticker: c.ticker
                });
            });
        });

        function arrMedianLocal(arr) {
            if (!arr.length) return 0;
            var s = arr.slice().sort(function(a, b) { return a - b; });
            var m = Math.floor(s.length / 2);
            return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
        }

        // Compute per-column (role) max for within-role color scaling
        var roleMaxMedian = {};
        var roleMinMedian = {};
        ROLES_DISPLAY.forEach(function(role) { roleMaxMedian[role] = 0; roleMinMedian[role] = Infinity; });

        // Build rows
        var sectors = Object.keys(sectorRoleMap);
        var sectorRows = [];
        sectors.forEach(function(sector) {
            var row = { sector: sector, roles: {} };
            var ceoMedian = 0;
            ROLES_DISPLAY.forEach(function(role) {
                var entries = sectorRoleMap[sector][role] || [];
                if (entries.length === 0) {
                    row.roles[role] = { median: 0, count: 0, topEarner: null };
                    return;
                }
                var totals = entries.map(function(e) { return e.total; });
                var med = arrMedianLocal(totals);
                var top = entries.slice().sort(function(a, b) { return b.total - a.total; })[0];
                row.roles[role] = { median: med, count: entries.length, topEarner: top };
                if (med > roleMaxMedian[role]) roleMaxMedian[role] = med;
                if (med > 0 && med < roleMinMedian[role]) roleMinMedian[role] = med;
                if (role === 'CEO') ceoMedian = med;
            });
            row.ceoMedian = ceoMedian;
            sectorRows.push(row);
        });

        // Sort sectors by CEO median descending
        sectorRows.sort(function(a, b) { return b.ceoMedian - a.ceoMedian; });

        // Render
        var html = '<div class="role-sector-heatmap-wrapper"><table class="role-sector-heatmap" aria-label="C-Suite role compensation by sector">';
        html += '<thead><tr><th class="rs-sector-th">Sector</th>';
        ROLES_DISPLAY.forEach(function(role) {
            var rc = ROLE_COLORS[role] || '#94a3b8';
            html += '<th><span class="rs-role-dot" style="background:' + rc + '"></span>' + role + '</th>';
        });
        html += '</tr></thead><tbody>';

        sectorRows.forEach(function(row) {
            var sColor = getSectorColor(row.sector);
            var escapedSector = row.sector.replace(/'/g, "\\'");
            html += '<tr>';
            html += '<td class="rs-sector-label" onclick="if(window.filterBySector)window.filterBySector(\'' + escapedSector + '\')" title="Click to filter table to ' + row.sector + '">';
            html += '<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:' + sColor + ';margin-right:6px;vertical-align:middle;"></span>' + row.sector + '</td>';

            ROLES_DISPLAY.forEach(function(role) {
                var data = row.roles[role];
                var rc = ROLE_COLORS[role] || '#94a3b8';
                if (!data || data.count === 0) {
                    html += '<td><div class="rs-cell rs-cell-empty" title="No ' + role + ' records for ' + row.sector + '"><span class="rs-cell-val">—</span></div></td>';
                    return;
                }

                var globalRb = _roleBenchmarks && _roleBenchmarks[role] ? _roleBenchmarks[role] : null;
                var topStr = data.topEarner ? ('. Highest: ' + data.topEarner.name + ' (' + data.topEarner.ticker + ') ' + formatCompact(data.topEarner.total)) : '';

                if (_roleSectorDeltaMode && globalRb && globalRb.median > 0) {
                    // Delta mode: show ±% vs S&P 500 role median with diverging green/red color
                    var deltaPct = ((data.median - globalRb.median) / globalRb.median * 100);
                    var deltaSign = deltaPct >= 0 ? '+' : '';
                    var deltaLabel = deltaSign + Math.round(deltaPct) + '%';
                    // Diverging color: green for above median, red for below
                    // Cap intensity at ±60% for color scaling
                    var clampedPct = Math.max(-60, Math.min(60, deltaPct));
                    var absNorm = Math.abs(clampedPct) / 60; // 0 to 1
                    var cellIntensity = 0.12 + absNorm * 0.68;
                    var bgColor, textColor;
                    if (deltaPct >= 0) {
                        bgColor = hexToRgba('#06d6a0', cellIntensity); // green
                    } else {
                        bgColor = hexToRgba('#ef476f', cellIntensity); // red
                    }
                    textColor = cellIntensity > 0.45 ? '#fff' : (isDarkTheme() ? '#e4e4e7' : '#1a1a2e');

                    var title = row.sector + ' ' + role + ': ' + deltaLabel + ' vs S&P 500 ' + role + ' median (' + formatCompact(globalRb.median) + '). Sector median: ' + formatCompact(data.median) + ' (' + data.count + ' execs)' + topStr;

                    html += '<td><div class="rs-cell rs-cell-delta" style="background:' + bgColor + ';color:' + textColor + '" onclick="if(window.filterBySector)window.filterBySector(\'' + escapedSector + '\')" title="' + title.replace(/"/g, '&quot;') + '">';
                    html += '<span class="rs-cell-val">' + deltaLabel + '</span>';
                    html += '<span class="rs-cell-dollar-sub">' + formatCompact(data.median) + '</span>';
                    html += '</div></td>';
                } else {
                    // Absolute mode (default): show dollar values with role-colored intensity
                    var maxM = roleMaxMedian[role] || 1;
                    var intensity = Math.min(0.88, 0.15 + (data.median / maxM) * 0.73);
                    var bgColor = hexToRgba(rc, intensity);
                    var textColor = intensity > 0.50 ? '#fff' : (isDarkTheme() ? '#e4e4e7' : '#1a1a2e');
                    var vsGlobalStr = '';
                    if (globalRb && globalRb.median > 0) {
                        var vsPct = ((data.median - globalRb.median) / globalRb.median * 100);
                        vsGlobalStr = (vsPct >= 0 ? '+' : '') + vsPct.toFixed(0) + '% vs S&P 500 ' + role + ' median';
                    }
                    var title = row.sector + ' ' + role + ': median ' + formatCompact(data.median) + ' (' + data.count + ' execs)';
                    if (vsGlobalStr) title += '. ' + vsGlobalStr;
                    title += topStr;

                    html += '<td><div class="rs-cell" style="background:' + bgColor + ';color:' + textColor + '" onclick="if(window.filterBySector)window.filterBySector(\'' + escapedSector + '\')" title="' + title.replace(/"/g, '&quot;') + '">';
                    html += '<span class="rs-cell-val">' + formatCompact(data.median) + '</span>';
                    html += '<span class="rs-cell-count">' + data.count + '</span>';
                    html += '</div></td>';
                }
            });

            html += '</tr>';
        });
        html += '</tbody></table></div>';

        // Footer: role legend or delta legend
        html += '<div class="rs-footer">';
        if (_roleSectorDeltaMode) {
            html += '<span class="rs-footer-stat"><span class="rs-footer-swatch" style="background:#ef476f"></span>Below index median</span>';
            html += '<span class="rs-footer-stat"><span class="rs-footer-swatch" style="background:' + (isDarkTheme() ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)') + ';border:1px solid ' + (isDarkTheme() ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)') + '"></span>At index median</span>';
            html += '<span class="rs-footer-stat"><span class="rs-footer-swatch" style="background:#06d6a0"></span>Above index median</span>';
        } else {
            ROLES_DISPLAY.forEach(function(role) {
                var rc = ROLE_COLORS[role] || '#94a3b8';
                html += '<span class="rs-footer-stat"><span class="rs-footer-swatch" style="background:' + rc + '"></span>' + role + '</span>';
            });
        }
        html += '</div>';

        container.innerHTML = html;
    }
    renderRoleSectorHeatmap();
    window._redrawRoleSectorHeatmap = renderRoleSectorHeatmap;

    // Role × Sector heatmap mode toggle (absolute ↔ delta)
    window.setRoleSectorMode = function(mode) {
        _roleSectorDeltaMode = (mode === 'delta');
        // Update button active state
        var absBtn = document.getElementById('rs-mode-abs');
        var deltaBtn = document.getElementById('rs-mode-delta');
        if (absBtn) absBtn.classList.toggle('active', !_roleSectorDeltaMode);
        if (deltaBtn) deltaBtn.classList.toggle('active', _roleSectorDeltaMode);
        // Update description
        var desc = document.getElementById('role-sector-desc');
        if (desc) {
            desc.textContent = _roleSectorDeltaMode
                ? 'Deviation from S&P 500 median for each C-suite role \u2014 green cells pay above index, red cells pay below. Intensity scales with distance from the benchmark. Click any cell to filter the table.'
                : 'Median total compensation for each C-suite role across GICS sectors \u2014 revealing how industry context shapes pay at every level. Color intensity is scaled within each role column to highlight sector outliers. Click any cell to filter the table.';
        }
        renderRoleSectorHeatmap();
        announce(_roleSectorDeltaMode ? 'Showing deviation from S&P 500 role medians' : 'Showing absolute median compensation');
    };

    // Restore state from URL hash (after charts/network are initialized)
    applyHashState(companies);
    _stateInitialized = true;

    // Apply sector chart highlight if restored from hash
    if (activeSector && window.highlightSectorBar) window.highlightSectorBar(activeSector);

    // Apply ratio bucket highlight if restored from hash
    if (window._activeRatioBucket && window.highlightRatioBucket) {
        window.highlightRatioBucket(window._activeRatioBucket.min, window._activeRatioBucket.max);
    }

    // Apply CEO transition filter chip if restored from hash
    if (window._activeCeoTransitionFilter) {
        updateCeoTransitionFilterIndicator();
    }

    // Apply team completeness filter chip if restored from hash
    if (window._activeTeamCompletenessFilter) {
        updateTeamCompletenessFilterIndicator();
    }

    // === Table horizontal scroll indicator ===
    var tableWrapper = document.getElementById('table-wrapper');
    if (tableWrapper) {
        function updateScrollIndicator() {
            var el = tableWrapper;
            var scrollable = el.scrollWidth > el.clientWidth + 2;
            var atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 4;
            var hasStarted = el.scrollLeft > 10;

            if (scrollable) {
                el.classList.add('has-scroll-right');
            } else {
                el.classList.remove('has-scroll-right');
            }

            if (atEnd) {
                el.classList.add('scroll-end');
            } else {
                el.classList.remove('scroll-end');
            }

            if (hasStarted) {
                el.classList.add('scroll-started');
            } else {
                el.classList.remove('scroll-started');
            }
        }

        tableWrapper.addEventListener('scroll', updateScrollIndicator, { passive: true });
        window.addEventListener('resize', function() {
            setTimeout(updateScrollIndicator, 300);
            // Redraw comparison chart on resize
            if (window._redrawComparisonChart) setTimeout(window._redrawComparisonChart, 260);
        });

        // Check after initial render and after any re-render
        var origRenderTable = window._renderTableRef;
        setTimeout(updateScrollIndicator, 100);

        // Observe table for changes (pagination, filter, etc.)
        var tableObserver = new MutationObserver(function() {
            setTimeout(updateScrollIndicator, 50);
        });
        var tbody = document.getElementById('comp-tbody');
        if (tbody) {
            tableObserver.observe(tbody, { childList: true });
        }
    }

    // Update ratio filter chip UI if restored from hash
    if (window._activeRatioBucket) {
        updateRatioFilterIndicator();
    }

    // Update dist filter chip UI if restored from hash
    if (window._activeDistFilter) {
        updateDistFilterIndicator();
    }

    // Update conc filter chip UI if restored from hash
    if (window._activeConcTier) {
        updateConcFilterIndicator();
    }

    // === CSV Export ===
    // Wire up theme toggle
    var themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', toggleTheme);
    }

    var csvBtn = document.getElementById('export-csv-btn');
    if (csvBtn) {
        csvBtn.addEventListener('click', function() {
            // Build the same filtered/sorted list that renderTable uses
            var filtered = companies.slice();
            if (activeSector) {
                filtered = filtered.filter(function(c) { return c.sector === activeSector; });
            }
            if (searchTerm) {
                var q = searchTerm.toLowerCase();
                filtered = filtered.filter(function(c) {
                    if ((c.ticker || '').toLowerCase().indexOf(q) >= 0 ||
                        (c.company_name || '').toLowerCase().indexOf(q) >= 0 ||
                        (c.ceo_name || '').toLowerCase().indexOf(q) >= 0 ||
                        (c.sector || '').toLowerCase().indexOf(q) >= 0) return true;
                    // Also search NEO names when EDGAR data is available
                    if (c.executives) {
                        for (var ei = 0; ei < c.executives.length; ei++) {
                            if (c.executives[ei].name && c.executives[ei].name.toLowerCase().indexOf(q) >= 0) return true;
                        }
                    }
                    return false;
                });
            }
            if (window._activeRatioBucket) {
                var rb = window._activeRatioBucket;
                filtered = filtered.filter(function(c) {
                    return c.pay_ratio != null && c.pay_ratio >= rb.min && c.pay_ratio < rb.max;
                });
            }
            if (window._activeDistFilter) {
                var df = window._activeDistFilter;
                filtered = filtered.filter(function(c) {
                    return c.total_compensation != null && c.total_compensation >= df.min && c.total_compensation <= df.max;
                });
            }
            if (activeRole && activeRole !== 'CEO') {
                filtered = filtered.filter(function(c) { return c._roleExecs && c._roleExecs[activeRole]; });
            }
            filtered.sort(function(a, b) {
                var av = a[currentSort.key];
                var bv = b[currentSort.key];
                if (av == null) av = currentSort.dir === 'asc' ? Infinity : -Infinity;
                if (bv == null) bv = currentSort.dir === 'asc' ? Infinity : -Infinity;
                if (typeof av === 'string') av = av.toLowerCase();
                if (typeof bv === 'string') bv = bv.toLowerCase();
                if (av < bv) return currentSort.dir === 'asc' ? -1 : 1;
                if (av > bv) return currentSort.dir === 'asc' ? 1 : -1;
                return 0;
            });

            // CSV header and rows — adapt labels and data to active role filter
            var isRoleExport = activeRole && activeRole !== 'CEO';
            var roleLabel = isRoleExport ? activeRole : 'CEO';
            var headers = ['Rank', 'Ticker', 'Company', roleLabel, roleLabel + ' Total Compensation ($)', 'Comp Percentile', 'CEO Comp YoY %', 'Sector', 'Pay Ratio', 'Median Worker Pay ($)',
                'CEO Concentration %', 'CEO Premium Ratio', 'CEO Transition', 'CEO Data Years',
                'Team Roles Filled', 'Team Roles', 'Missing Expected Roles',
                roleLabel + ' Salary ($)', roleLabel + ' Stock Awards ($)', roleLabel + ' Option Awards ($)', roleLabel + ' Bonus ($)',
                roleLabel + ' Non-Equity Incentive ($)', roleLabel + ' Pension/NQDC ($)', roleLabel + ' All Other ($)',
                roleLabel + ' Salary %', roleLabel + ' Stock %', roleLabel + ' Options %', roleLabel + ' Bonus %', roleLabel + ' Incentive %', roleLabel + ' Pension %', roleLabel + ' Other %'];
            var rows = filtered.map(function(c, i) {
                var yoyVal = c._ceoYoY ? (c._ceoYoY.pct >= 0 ? '+' : '') + c._ceoYoY.pct.toFixed(1) + '%' : '';
                // Find executive record for composition data — role exec when role-filtered, CEO otherwise
                var compExec = null;
                if (isRoleExport && c._roleExecs && c._roleExecs[activeRole]) {
                    compExec = c._roleExecs[activeRole];
                } else if (c.executives && c.executives.length > 0) {
                    var latestYear = 0;
                    c.executives.forEach(function(e) { if (e.year > latestYear) latestYear = e.year; });
                    var latestExecs = c.executives.filter(function(e) { return e.year === latestYear; });
                    // CEO by title match
                    compExec = latestExecs.find(function(e) {
                        return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
                    });
                    // Fallback: highest total
                    if (!compExec && latestExecs.length > 0) {
                        compExec = latestExecs.reduce(function(a, b) { return (a.total || 0) > (b.total || 0) ? a : b; });
                    }
                }
                // Executive name and total comp adapt to role filter
                var exportName = isRoleExport && c._roleExecs && c._roleExecs[activeRole]
                    ? c._roleExecs[activeRole].name : c.ceo_name;
                var exportComp = isRoleExport
                    ? (compExec ? (compExec.total || 0) : 0)
                    : (c.total_compensation || '');
                var sal = compExec ? (compExec.salary || 0) : '';
                var stk = compExec ? (compExec.stock_awards || 0) : '';
                var opt = compExec ? (compExec.option_awards || 0) : '';
                var bon = compExec ? (compExec.bonus || 0) : '';
                var inc = compExec ? (compExec.non_equity_incentive || 0) : '';
                var pen = compExec ? (compExec.pension_nqdc || compExec.pension_change || 0) : '';
                var oth = compExec ? (compExec.all_other || 0) : '';
                var tot = compExec ? (compExec.total || 0) : 0;
                // Percentages
                var salP = tot > 0 && compExec ? ((sal / tot) * 100).toFixed(1) + '%' : '';
                var stkP = tot > 0 && compExec ? ((stk / tot) * 100).toFixed(1) + '%' : '';
                var optP = tot > 0 && compExec ? ((opt / tot) * 100).toFixed(1) + '%' : '';
                var bonP = tot > 0 && compExec ? ((bon / tot) * 100).toFixed(1) + '%' : '';
                var incP = tot > 0 && compExec ? ((inc / tot) * 100).toFixed(1) + '%' : '';
                var penP = tot > 0 && compExec ? ((pen / tot) * 100).toFixed(1) + '%' : '';
                var othP = tot > 0 && compExec ? ((oth / tot) * 100).toFixed(1) + '%' : '';
                return [
                    i + 1,
                    csvEscape(c.ticker),
                    csvEscape(c.company_name),
                    csvEscape(exportName),
                    exportComp,
                    c._compPercentile != null ? c._compPercentile : '',
                    csvEscape(yoyVal),
                    csvEscape(c.sector || ''),
                    c.pay_ratio || '',
                    c.median_worker_pay || '',
                    c._ceoConcPct != null ? c._ceoConcPct.toFixed(1) : '',
                    c._ceoPremiumRatio != null ? c._ceoPremiumRatio.toFixed(2) : '',
                    c._ceoTransition ? csvEscape('Yes: ' + c._ceoTransition.oldCeo.name + ' → ' + c._ceoTransition.newCeo.name) : 'No',
                    c._ceoDataYears || '',
                    c._teamRoleCount || 0,
                    csvEscape((c._teamRoles || []).join('; ')),
                    csvEscape((c._teamMissingExpected || []).join('; ')),
                    sal, stk, opt, bon, inc, pen, oth,
                    csvEscape(salP), csvEscape(stkP), csvEscape(optP), csvEscape(bonP),
                    csvEscape(incP), csvEscape(penP), csvEscape(othP)
                ].join(',');
            });

            var csv = headers.join(',') + '\n' + rows.join('\n');
            var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            var fname = 'sp500-exec-comp';
            if (activeSector) fname += '-' + activeSector.toLowerCase().replace(/\s+/g, '-');
            if (activeRole && activeRole !== 'CEO') fname += '-' + activeRole.toLowerCase().replace(/[^a-z0-9]+/g, '-');
            if (searchTerm) fname += '-' + searchTerm.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 20);
            if (window._activeDistFilter) fname += '-dist-' + window._activeDistFilter.label.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30);
            if (window._activeRatioBucket) fname += '-ratio-' + window._activeRatioBucket.min + '-' + (window._activeRatioBucket.max === Infinity ? 'max' : window._activeRatioBucket.max);
            a.download = fname + '.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }

    // === Full NEO CSV Export ===
    var neoBtn = document.getElementById('export-neo-btn');
    if (neoBtn) {
        neoBtn.addEventListener('click', function() {
            // Build the same filtered/sorted list that renderTable uses
            var filtered = companies.slice();
            if (activeSector) {
                filtered = filtered.filter(function(c) { return c.sector === activeSector; });
            }
            if (searchTerm) {
                var q = searchTerm.toLowerCase();
                filtered = filtered.filter(function(c) {
                    if ((c.ticker || '').toLowerCase().indexOf(q) >= 0 ||
                        (c.company_name || '').toLowerCase().indexOf(q) >= 0 ||
                        (c.ceo_name || '').toLowerCase().indexOf(q) >= 0 ||
                        (c.sector || '').toLowerCase().indexOf(q) >= 0) return true;
                    if (c.executives) {
                        for (var ei = 0; ei < c.executives.length; ei++) {
                            if (c.executives[ei].name && c.executives[ei].name.toLowerCase().indexOf(q) >= 0) return true;
                        }
                    }
                    return false;
                });
            }
            if (window._activeRatioBucket) {
                var rb = window._activeRatioBucket;
                filtered = filtered.filter(function(c) {
                    return c.pay_ratio != null && c.pay_ratio >= rb.min && c.pay_ratio < rb.max;
                });
            }
            if (window._activeDistFilter) {
                var df = window._activeDistFilter;
                filtered = filtered.filter(function(c) {
                    return c.total_compensation != null && c.total_compensation >= df.min && c.total_compensation <= df.max;
                });
            }
            if (activeRole && activeRole !== 'CEO') {
                filtered = filtered.filter(function(c) { return c._roleExecs && c._roleExecs[activeRole]; });
            }
            filtered.sort(function(a, b) {
                var av = a[currentSort.key];
                var bv = b[currentSort.key];
                if (av == null) av = currentSort.dir === 'asc' ? Infinity : -Infinity;
                if (bv == null) bv = currentSort.dir === 'asc' ? Infinity : -Infinity;
                if (typeof av === 'string') av = av.toLowerCase();
                if (typeof bv === 'string') bv = bv.toLowerCase();
                if (av < bv) return currentSort.dir === 'asc' ? -1 : 1;
                if (av > bv) return currentSort.dir === 'asc' ? 1 : -1;
                return 0;
            });

            // CSV header — expanded with NEO fields; adapt to role filter
            var isRoleNeo = activeRole && activeRole !== 'CEO';
            var roleLabelNeo = isRoleNeo ? activeRole : 'CEO';
            var headers = [
                'Rank', 'Ticker', 'Company', roleLabelNeo, roleLabelNeo + ' Total Comp ($)',
                'Sector', 'Pay Ratio', 'Median Worker Pay ($)',
                'Exec Name', 'Exec Title', 'Role Category', 'Salary ($)', 'Bonus ($)', 'Stock Awards ($)',
                'Option Awards ($)', 'Non-Equity Incentive ($)', 'Pension/NQDC ($)', 'All Other Comp ($)',
                'Exec Total ($)', 'Fiscal Year', 'Filing Date', 'Filing URL'
            ];

            var rows = [];
            filtered.forEach(function(c, i) {
                var rank = i + 1;
                // Use role exec name and comp when role-filtered
                var neoExportName = isRoleNeo && c._roleExecs && c._roleExecs[activeRole]
                    ? c._roleExecs[activeRole].name : c.ceo_name;
                var neoExportComp = isRoleNeo && c._roleExecs && c._roleExecs[activeRole]
                    ? (c._roleExecs[activeRole].total || 0)
                    : (c.total_compensation || '');
                var baseFields = [
                    rank,
                    csvEscape(c.ticker),
                    csvEscape(c.company_name),
                    csvEscape(neoExportName),
                    neoExportComp,
                    csvEscape(c.sector || ''),
                    c.pay_ratio || '',
                    c.median_worker_pay || ''
                ];

                if (c.executives && c.executives.length > 0) {
                    // Export ALL exec records across all years (multi-year)
                    c.executives.forEach(function(exec) {
                        rows.push(baseFields.concat([
                            csvEscape(exec.name || ''),
                            csvEscape(exec.title || ''),
                            csvEscape(classifyExecRole(exec.title)),
                            exec.salary || '',
                            exec.bonus || '',
                            exec.stock_awards || '',
                            exec.option_awards || '',
                            exec.non_equity_incentive || '',
                            exec.pension_nqdc || exec.pension_change || '',
                            exec.all_other || '',
                            exec.total || '',
                            exec.year || c.proxy_fiscal_year || '',
                            csvEscape(c.filing_date || ''),
                            csvEscape(c.filing_url || '')
                        ]).join(','));
                    });
                } else {
                    // No NEO data — single summary row with empty exec fields
                    rows.push(baseFields.concat([
                        '', '', '', '', '', '', '', '', '', '',
                        c.proxy_fiscal_year || '',
                        csvEscape(c.filing_date || ''),
                        csvEscape(c.filing_url || '')
                    ]).join(','));
                }
            });

            var csv = headers.join(',') + '\n' + rows.join('\n');
            var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            var fname = 'sp500-neo-comp';
            if (activeSector) fname += '-' + activeSector.toLowerCase().replace(/\s+/g, '-');
            if (activeRole && activeRole !== 'CEO') fname += '-' + activeRole.toLowerCase().replace(/[^a-z0-9]+/g, '-');
            if (searchTerm) fname += '-' + searchTerm.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 20);
            if (window._activeDistFilter) fname += '-dist-' + window._activeDistFilter.label.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30);
            if (window._activeRatioBucket) fname += '-ratio-' + window._activeRatioBucket.min + '-' + (window._activeRatioBucket.max === Infinity ? 'max' : window._activeRatioBucket.max);
            a.download = fname + '.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            announce('Downloaded full multi-year NEO compensation data for ' + filtered.length + ' companies');
        });
    }

    // === Company Comparison Mode ===
    var compareSet = []; // array of tickers
    var MAX_COMPARE = 4;

    function toggleCompare(ticker, event) {
        if (event) { event.stopPropagation(); event.preventDefault(); }
        var idx = compareSet.indexOf(ticker);
        if (idx >= 0) {
            compareSet.splice(idx, 1);
        } else {
            if (compareSet.length >= MAX_COMPARE) return; // max reached
            compareSet.push(ticker);
        }
        updateCompareTray();
        updateCompareButtons();
        pushState();
    }

    function updateCompareButtons() {
        document.querySelectorAll('.compare-btn').forEach(function(btn) {
            var t = btn.dataset.ticker;
            if (compareSet.indexOf(t) >= 0) {
                btn.classList.add('selected');
                btn.textContent = '✓';
                btn.title = 'Remove from comparison';
            } else {
                btn.classList.remove('selected');
                btn.textContent = '+';
                btn.title = compareSet.length >= MAX_COMPARE ? 'Max ' + MAX_COMPARE + ' companies' : 'Add to comparison';
            }
        });
        // Update insight card compare buttons (show ticker label, not just icon)
        document.querySelectorAll('.insight-compare-btn').forEach(function(btn) {
            var t = btn.dataset.ticker;
            var icon = btn.querySelector('.icb-icon');
            if (compareSet.indexOf(t) >= 0) {
                btn.classList.add('selected');
                btn.setAttribute('aria-pressed', 'true');
                if (icon) icon.textContent = '✓';
                btn.title = 'Remove ' + t + ' from comparison';
            } else {
                btn.classList.remove('selected');
                btn.setAttribute('aria-pressed', 'false');
                if (icon) icon.textContent = '+';
                btn.title = compareSet.length >= MAX_COMPARE ? 'Max ' + MAX_COMPARE + ' companies' : 'Add ' + t + ' to comparison';
            }
        });
    }

    function updateCompareTray() {
        var tray = document.getElementById('compare-tray');
        var itemsEl = document.getElementById('compare-tray-items');
        if (compareSet.length < 2) {
            tray.classList.remove('visible');
            return;
        }
        tray.classList.add('visible');
        itemsEl.innerHTML = '';
        compareSet.forEach(function(ticker) {
            var tag = document.createElement('span');
            tag.className = 'compare-tray-tag';
            tag.innerHTML = ticker + ' <span class="remove-tag" data-ticker="' + ticker + '">×</span>';
            tag.querySelector('.remove-tag').addEventListener('click', function(e) {
                e.stopPropagation();
                toggleCompare(ticker);
            });
            itemsEl.appendChild(tag);
        });
    }

    function clearCompare() {
        compareSet.length = 0; // mutate in-place so window._compareSet stays in sync
        updateCompareTray();
        updateCompareButtons();
        var section = document.getElementById('comparison-section');
        if (section) section.classList.remove('visible');
        pushState();
    }

    /* === Comparison Summary Chart === */
    var COMP_COLORS = ['#00b4d8', '#06d6a0', '#ffd166', '#a78bfa'];

    function renderComparisonChart(container, selected, rankMap, roleCtx) {
        container.innerHTML = '';
        if (selected.length < 2) return;
        // roleCtx: { role: 'CFO'|..., getComp: fn(c)->number, getExec: fn(c)->exec } or null

        var cWidth = container.clientWidth || 600;
        var barH = 28;
        var groupGap = 32;
        var labelW = 60;
        var valueW = 90;
        var chartLeft = labelW + 8;
        var chartRight = cWidth - valueW - 8;
        var barAreaW = chartRight - chartLeft;
        if (barAreaW < 100) barAreaW = 100;
        var n = selected.length;
        var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
        var textCol = dark ? '#e4e4e7' : '#1a1a2e';
        var mutedCol = dark ? '#6b7280' : '#6b7280';
        var gridCol = dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
        var hoverBg = dark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)';

        // Pre-compute S&P 500 ranks for all 3 metrics
        var ratioRankMap = {};
        var workerRankMap = {};
        var companiesWithRatio = companies.filter(function(c) { return c.pay_ratio != null && c.pay_ratio > 0; })
            .sort(function(a, b) { return b.pay_ratio - a.pay_ratio; });
        companiesWithRatio.forEach(function(c, i) { ratioRankMap[c.ticker] = { rank: i + 1, total: companiesWithRatio.length }; });
        var companiesWithWorker = companies.filter(function(c) { return c.median_worker_pay != null && c.median_worker_pay > 0; })
            .sort(function(a, b) { return b.median_worker_pay - a.median_worker_pay; });
        companiesWithWorker.forEach(function(c, i) { workerRankMap[c.ticker] = { rank: i + 1, total: companiesWithWorker.length }; });
        var totalCompanies = companies.length;

        // Three metric groups
        var metrics = [
            {
                label: roleCtx ? roleCtx.role + ' Total Compensation' : 'Total Compensation',
                key: 'total_compensation',
                getValue: roleCtx ? function(c) { return roleCtx.getComp(c); } : null,
                format: function(v) { return formatCurrency(v); },
                color: function(v, max, min) {
                    return v === max ? (dark ? '#00b4d8' : '#0077b6') : null;
                },
                higherBetter: true,
                getRank: function(ticker) { var r = rankMap[ticker]; return r ? { rank: r, total: totalCompanies } : null; },
                unit: ''
            },
            {
                label: 'CEO:Worker Pay Ratio',
                key: 'pay_ratio',
                format: function(v) { return v != null ? v.toLocaleString() + ':1' : 'N/A'; },
                color: function(v, max, min) {
                    if (v == null) return null;
                    if (v > 1000) return '#ef476f';
                    if (v > 500) return '#ffd166';
                    return '#06d6a0';
                },
                higherBetter: false,
                getRank: function(ticker) { return ratioRankMap[ticker] || null; },
                unit: ':1'
            },
            {
                label: 'Median Worker Pay',
                key: 'median_worker_pay',
                format: function(v) { return v != null ? formatCompact(v) : 'N/A'; },
                color: function(v, max, min) {
                    return v === max ? (dark ? '#06d6a0' : '#059669') : null;
                },
                higherBetter: true,
                getRank: function(ticker) { return workerRankMap[ticker] || null; },
                unit: ''
            },
            {
                label: 'CEO Concentration',
                key: '_ceoConcPct',
                format: function(v) { return v != null ? v.toFixed(1) + '%' : 'N/A'; },
                color: function(v, max, min) {
                    if (v == null) return null;
                    if (v >= 50) return '#ef476f';
                    if (v >= 35) return '#ffd166';
                    return '#06d6a0';
                },
                higherBetter: false,
                getRank: function() { return null; },
                unit: '%'
            }
        ];

        var totalH = metrics.length * (n * (barH + 4) + 28 + groupGap) - groupGap + 16;
        // Reserve extra space for composition group
        totalH += n * (barH + 4) + 28 + groupGap + 24;

        var svg = d3.select(container).append('svg')
            .attr('width', cWidth)
            .attr('height', totalH)
            .style('display', 'block');

        var yOffset = 8;

        metrics.forEach(function(metric) {
            // Group label
            svg.append('text')
                .attr('x', 0)
                .attr('y', yOffset + 14)
                .attr('fill', mutedCol)
                .attr('font-size', '11px')
                .attr('font-weight', '600')
                .attr('letter-spacing', '0.5px')
                .attr('font-family', "'Inter', sans-serif")
                .style('text-transform', 'uppercase')
                .text(metric.label);

            yOffset += 24;

            // Compute max for this metric
            // Helper: get metric value, using custom getValue if provided (for role-aware comp)
            function mVal(c) { return metric.getValue ? metric.getValue(c) : c[metric.key]; }
            var vals = selected.map(function(c) { return mVal(c); }).filter(function(v) { return v != null && v > 0; });
            var maxVal = vals.length > 0 ? Math.max.apply(null, vals) : 1;
            var minVal = vals.length > 0 ? Math.min.apply(null, vals) : 0;

            // Determine best/worst in comparison set for context
            var bestVal = metric.higherBetter ? maxVal : minVal;
            var bestTicker = '';
            selected.forEach(function(c) {
                var v = mVal(c);
                if (v != null && v === bestVal) bestTicker = c.ticker;
            });

            // Gridline at max
            svg.append('line')
                .attr('x1', chartLeft)
                .attr('y1', yOffset - 2)
                .attr('x2', chartRight)
                .attr('y2', yOffset - 2)
                .attr('stroke', gridCol)
                .attr('stroke-width', 1);

            selected.forEach(function(c, i) {
                var val = mVal(c);
                var barY = yOffset + i * (barH + 4);
                var barW = (val != null && val > 0 && maxVal > 0) ? (val / maxVal * barAreaW) : 0;

                // Determine bar color
                var barColor = COMP_COLORS[i % COMP_COLORS.length];
                var specialColor = metric.color(val, maxVal, minVal);

                // Create a group for this bar row for hover coordination
                var barGroup = svg.append('g')
                    .attr('class', 'comp-chart-bar-group')
                    .style('cursor', 'pointer');

                // Ticker label
                barGroup.append('text')
                    .attr('x', labelW)
                    .attr('y', barY + barH / 2 + 4)
                    .attr('text-anchor', 'end')
                    .attr('fill', COMP_COLORS[i % COMP_COLORS.length])
                    .attr('font-size', '12px')
                    .attr('font-weight', '700')
                    .attr('font-family', "'SF Mono', 'Fira Code', monospace")
                    .text(c.ticker);

                // Bar background
                barGroup.append('rect')
                    .attr('x', chartLeft)
                    .attr('y', barY)
                    .attr('width', barAreaW)
                    .attr('height', barH)
                    .attr('rx', 4)
                    .attr('fill', gridCol);

                // Bar fill with transition
                var barFill = null;
                if (barW > 0) {
                    barFill = barGroup.append('rect')
                        .attr('x', chartLeft)
                        .attr('y', barY)
                        .attr('width', 0)
                        .attr('height', barH)
                        .attr('rx', 4)
                        .attr('fill', barColor)
                        .attr('opacity', 0.85);
                    // Animate bar growth
                    barFill.transition()
                        .duration(500)
                        .delay(i * 80)
                        .ease(d3.easeCubicOut)
                        .attr('width', barW);
                }

                // Value label
                var valueLabel = barGroup.append('text')
                    .attr('x', chartRight + 8)
                    .attr('y', barY + barH / 2 + 4)
                    .attr('text-anchor', 'start')
                    .attr('fill', specialColor || textCol)
                    .attr('font-size', '12px')
                    .attr('font-weight', '600')
                    .attr('font-family', "'SF Mono', 'Fira Code', monospace")
                    .style('font-variant-numeric', 'tabular-nums')
                    .text(metric.format(val));

                // Invisible hit-area rect covering the entire bar row (for consistent hover)
                barGroup.append('rect')
                    .attr('x', 0)
                    .attr('y', barY - 1)
                    .attr('width', cWidth)
                    .attr('height', barH + 2)
                    .attr('fill', 'transparent')
                    .style('cursor', 'pointer');

                // Build tooltip content
                var rankInfo = metric.getRank(c.ticker);
                var rankStr = rankInfo ? '#' + rankInfo.rank + ' / ' + rankInfo.total : 'N/A';
                var pctile = rankInfo ? Math.round((1 - (rankInfo.rank - 1) / rankInfo.total) * 100) : null;
                var pctileStr = pctile != null ? pctile + 'th percentile' : '';

                // Comparison context
                var compContext = '';
                if (val != null && val > 0 && bestVal > 0 && n > 1) {
                    if (val === bestVal) {
                        compContext = metric.higherBetter ? '🏆 Highest in comparison' : '⚠️ Highest in comparison';
                    } else {
                        var diff = Math.abs((val - bestVal) / bestVal * 100);
                        if (metric.higherBetter) {
                            compContext = Math.round(diff) + '% less than ' + bestTicker;
                        } else {
                            // For pay ratio (lower is better), show how much higher than the lowest
                            var worstInComparison = maxVal;
                            var bestInComparison = minVal > 0 ? minVal : maxVal;
                            if (val === bestInComparison) {
                                compContext = '✅ Lowest in comparison';
                            } else {
                                var diffFromBest = Math.abs((val - bestInComparison) / bestInComparison * 100);
                                var bestRatioTicker = '';
                                selected.forEach(function(sc) { if (mVal(sc) === bestInComparison) bestRatioTicker = sc.ticker; });
                                compContext = Math.round(diffFromBest) + '% higher than ' + bestRatioTicker;
                            }
                        }
                    }
                }

                // Hover interactions
                barGroup
                    .on('mouseover', function(event) {
                        // Highlight bar
                        if (barFill) barFill.attr('opacity', 1);
                        // Highlight value label
                        valueLabel.attr('font-weight', '800');

                        // Build tooltip HTML
                        var tipHtml = '<div class="ct-title">' + c.company_name + '</div>';
                        tipHtml += '<div class="ct-row"><span class="ct-label">' + metric.label + '</span><span class="ct-val">' + metric.format(val) + '</span></div>';
                        tipHtml += '<div class="ct-row"><span class="ct-label">S&P 500 Rank</span><span class="ct-val">' + rankStr + '</span></div>';
                        if (pctileStr) {
                            tipHtml += '<div class="ct-row"><span class="ct-label">Percentile</span><span class="ct-val">' + pctileStr + '</span></div>';
                        }
                        if (compContext) {
                            tipHtml += '<div class="ct-sub"><div class="ct-row"><span class="ct-val">' + compContext + '</span></div></div>';
                        }
                        tipHtml += '<div class="ct-sub"><div class="ct-row"><span class="ct-val" style="color:var(--accent);font-size:0.68rem">Click to view in table</span></div></div>';
                        showChartTooltip(event, tipHtml);
                    })
                    .on('mousemove', function(event) {
                        positionChartTooltip(event);
                    })
                    .on('mouseout', function() {
                        if (barFill) barFill.attr('opacity', 0.85);
                        valueLabel.attr('font-weight', '600');
                        hideChartTooltip();
                    })
                    .on('click', function() {
                        hideChartTooltip();
                        if (window.findCompanyInTable) window.findCompanyInTable(c.ticker);
                    });

                // Best/worst indicator for the last bar bottom gridline
                if (i === n - 1) {
                    svg.append('line')
                        .attr('x1', chartLeft)
                        .attr('y1', barY + barH + 2)
                        .attr('x2', chartRight)
                        .attr('y2', barY + barH + 2)
                        .attr('stroke', gridCol)
                        .attr('stroke-width', 1);
                }
            });

            yOffset += n * (barH + 4) + groupGap;
        });

        // === 4th metric group: CEO Pay Composition (stacked bars) ===
        // Build composition data for each selected company
        var compCompColors = {
            'Salary': '#06d6a0', 'Stock': '#00b4d8', 'Options': '#0096c7',
            'Incentive': '#a78bfa', 'Bonus': '#8b5cf6', 'Pension': '#fb923c', 'Other': '#ffd166'
        };
        var compCompKeys = [
            { key: 'salary', label: 'Salary' },
            { key: 'stock_awards', label: 'Stock' },
            { key: 'option_awards', label: 'Options' },
            { key: 'non_equity_incentive', label: 'Incentive' },
            { key: 'bonus', label: 'Bonus' },
            { key: 'pension_nqdc', label: 'Pension' },
            { key: 'all_other', label: 'Other' }
        ];

        // Get exec breakdown for each company (role-aware: uses role exec when roleCtx active)
        var compBreakdowns = selected.map(function(c) {
            if (!c.executives || c.executives.length === 0) return null;
            var allYears = [];
            c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
            allYears.sort(function(a, b) { return b - a; });
            var latestExecs = c.executives.filter(function(e) { return e.year === allYears[0]; });
            var exec;
            if (roleCtx) {
                // Use role exec from pre-computed data
                exec = roleCtx.getExec(c);
                if (!exec) return null;
            } else {
                exec = latestExecs.find(function(e) {
                    return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
                });
                if (!exec) exec = latestExecs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
            }
            if (!exec) return null;
            var segs = [];
            var segTotal = 0;
            compCompKeys.forEach(function(kd) {
                var val = exec[kd.key] || 0;
                if (val > 0) {
                    segs.push({ label: kd.label, value: val, color: compCompColors[kd.label] });
                    segTotal += val;
                }
            });
            if (segs.length === 0 || segTotal === 0) return null;
            segs.forEach(function(s) { s.pct = s.value / segTotal * 100; });
            return { segs: segs, total: segTotal, ceoName: exec.name || c.ceo_name, year: allYears[0] };
        });

        var hasCompData = compBreakdowns.some(function(b) { return b !== null; });

        if (hasCompData) {
            // Extend SVG height for the composition section
            var compSectionH = n * (barH + 4) + 48; // bars + header + legend
            var legendH = 24;

            // Group label
            svg.append('text')
                .attr('x', 0)
                .attr('y', yOffset + 14)
                .attr('fill', mutedCol)
                .attr('font-size', '11px')
                .attr('font-weight', '600')
                .attr('letter-spacing', '0.5px')
                .attr('font-family', "'Inter', sans-serif")
                .style('text-transform', 'uppercase')
                .text(roleCtx ? roleCtx.role + ' Pay Composition' : 'Pay Composition');

            yOffset += 24;

            // Gridline
            svg.append('line')
                .attr('x1', chartLeft)
                .attr('y1', yOffset - 2)
                .attr('x2', chartRight)
                .attr('y2', yOffset - 2)
                .attr('stroke', gridCol)
                .attr('stroke-width', 1);

            selected.forEach(function(c, i) {
                var bd = compBreakdowns[i];
                var barY = yOffset + i * (barH + 4);

                // Ticker label
                svg.append('text')
                    .attr('x', labelW)
                    .attr('y', barY + barH / 2 + 4)
                    .attr('text-anchor', 'end')
                    .attr('fill', COMP_COLORS[i % COMP_COLORS.length])
                    .attr('font-size', '12px')
                    .attr('font-weight', '700')
                    .attr('font-family', "'SF Mono', 'Fira Code', monospace")
                    .text(c.ticker);

                // Bar background
                svg.append('rect')
                    .attr('x', chartLeft)
                    .attr('y', barY)
                    .attr('width', barAreaW)
                    .attr('height', barH)
                    .attr('rx', 4)
                    .attr('fill', gridCol);

                if (bd) {
                    // Stacked segments
                    var xCursor = chartLeft;
                    bd.segs.forEach(function(seg, si) {
                        var segW = seg.pct / 100 * barAreaW;
                        if (segW < 1) return;
                        var segGroup = svg.append('g').style('cursor', 'pointer');
                        var segRect = segGroup.append('rect')
                            .attr('x', xCursor)
                            .attr('y', barY)
                            .attr('width', segW)
                            .attr('height', barH)
                            .attr('fill', seg.color)
                            .attr('opacity', 0.85);
                        // First and last segments get rounded corners
                        if (si === 0) segRect.attr('rx', 4).attr('ry', 4).attr('clip-path', 'inset(0 0 0 0 round 4px 0 0 4px)');
                        if (si === bd.segs.length - 1) segRect.attr('rx', 4).attr('ry', 4);

                        // Percentage label on segment if wide enough
                        if (segW > 28) {
                            segGroup.append('text')
                                .attr('x', xCursor + segW / 2)
                                .attr('y', barY + barH / 2 + 4)
                                .attr('text-anchor', 'middle')
                                .attr('fill', '#fff')
                                .attr('font-size', '9px')
                                .attr('font-weight', '700')
                                .attr('font-family', "'Inter', sans-serif")
                                .text(seg.pct.toFixed(0) + '%');
                        }

                        // Hover tooltip
                        segGroup
                            .on('mouseover', function(event) {
                                segRect.attr('opacity', 1);
                                var tipHtml = '<div class="ct-title">' + c.company_name + '</div>';
                                tipHtml += '<div class="ct-row"><span class="ct-label">' + seg.label + '</span><span class="ct-val">' + formatCurrency(seg.value) + '</span></div>';
                                tipHtml += '<div class="ct-row"><span class="ct-label">% of Total</span><span class="ct-val">' + seg.pct.toFixed(1) + '%</span></div>';
                                tipHtml += '<div class="ct-sub"><div class="ct-row"><span class="ct-val" style="font-size:0.68rem">' + (bd.ceoName || c.ceo_name) + ' · FY' + bd.year + '</span></div></div>';
                                showChartTooltip(event, tipHtml);
                            })
                            .on('mousemove', function(event) { positionChartTooltip(event); })
                            .on('mouseout', function() {
                                segRect.attr('opacity', 0.85);
                                hideChartTooltip();
                            })
                            .on('click', function() {
                                hideChartTooltip();
                                if (window.findCompanyInTable) window.findCompanyInTable(c.ticker);
                            });

                        xCursor += segW;
                    });

                    // Total label on right
                    svg.append('text')
                        .attr('x', chartRight + 8)
                        .attr('y', barY + barH / 2 + 4)
                        .attr('text-anchor', 'start')
                        .attr('fill', textCol)
                        .attr('font-size', '12px')
                        .attr('font-weight', '600')
                        .attr('font-family', "'SF Mono', 'Fira Code', monospace")
                        .style('font-variant-numeric', 'tabular-nums')
                        .text(formatCurrency(bd.total));
                } else {
                    svg.append('text')
                        .attr('x', chartLeft + barAreaW / 2)
                        .attr('y', barY + barH / 2 + 4)
                        .attr('text-anchor', 'middle')
                        .attr('fill', mutedCol)
                        .attr('font-size', '11px')
                        .attr('font-family', "'Inter', sans-serif")
                        .text('No breakdown data');
                }
            });

            yOffset += n * (barH + 4) + 8;

            // Bottom gridline
            svg.append('line')
                .attr('x1', chartLeft)
                .attr('y1', yOffset - 6)
                .attr('x2', chartRight)
                .attr('y2', yOffset - 6)
                .attr('stroke', gridCol)
                .attr('stroke-width', 1);

            // Shared legend
            var legendItems = ['Salary', 'Stock', 'Options', 'Incentive', 'Bonus', 'Pension', 'Other'];
            var legendUsed = {};
            compBreakdowns.forEach(function(bd) {
                if (!bd) return;
                bd.segs.forEach(function(s) { legendUsed[s.label] = true; });
            });
            var activeLegend = legendItems.filter(function(l) { return legendUsed[l]; });
            var legendX = chartLeft;
            activeLegend.forEach(function(label) {
                var g = svg.append('g');
                g.append('rect')
                    .attr('x', legendX)
                    .attr('y', yOffset)
                    .attr('width', 8)
                    .attr('height', 8)
                    .attr('rx', 2)
                    .attr('fill', compCompColors[label]);
                g.append('text')
                    .attr('x', legendX + 12)
                    .attr('y', yOffset + 8)
                    .attr('fill', mutedCol)
                    .attr('font-size', '10px')
                    .attr('font-family', "'Inter', sans-serif")
                    .text(label);
                legendX += label.length * 6 + 22;
            });

            yOffset += legendH + groupGap;

            // Resize SVG to fit new content
            svg.attr('height', yOffset);
        }
    }

    /* === Peer Overlap Analysis for Comparison View === */
    function renderPeerOverlap(selected, gridEl) {
        // Remove existing overlap panel if present
        var existingPanel = document.getElementById('peer-overlap-panel');
        if (existingPanel) existingPanel.remove();

        if (selected.length < 2) return;

        // Gather each company's full peer set (union of inbound + outbound, excluding self and other compared companies)
        var comparedTickers = selected.map(function(c) { return c.ticker; });
        var peerSets = {};
        selected.forEach(function(c) {
            var info = getPeerInfo(c.ticker);
            if (!info) { peerSets[c.ticker] = []; return; }
            var allPeers = {};
            info.selectedBy.forEach(function(t) { if (comparedTickers.indexOf(t) === -1) allPeers[t] = true; });
            info.selects.forEach(function(t) { if (comparedTickers.indexOf(t) === -1) allPeers[t] = true; });
            peerSets[c.ticker] = Object.keys(allPeers);
        });

        // Compute pairwise overlap
        var pairs = [];
        for (var i = 0; i < selected.length; i++) {
            for (var j = i + 1; j < selected.length; j++) {
                var a = selected[i].ticker;
                var b = selected[j].ticker;
                var setA = peerSets[a];
                var setB = peerSets[b];
                var shared = setA.filter(function(t) { return setB.indexOf(t) !== -1; });
                var unionCount = setA.length + setB.length - shared.length;
                var similarity = unionCount > 0 ? Math.round(shared.length / unionCount * 100) : 0;
                pairs.push({
                    tickerA: a,
                    tickerB: b,
                    shared: shared.sort(),
                    countA: setA.length,
                    countB: setB.length,
                    similarity: similarity
                });
            }
        }

        // Find peers common to ALL compared companies
        var commonToAll = [];
        if (selected.length >= 2) {
            var firstSet = peerSets[selected[0].ticker];
            commonToAll = firstSet.filter(function(t) {
                return selected.every(function(c) { return peerSets[c.ticker].indexOf(t) !== -1; });
            }).sort();
        }

        // Build the panel
        var panel = document.createElement('div');
        panel.id = 'peer-overlap-panel';
        panel.className = 'peer-overlap-panel';

        var html = '<div class="peer-overlap-header">';
        html += '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="12" r="6" opacity="0.6"/><circle cx="15" cy="12" r="6" opacity="0.6"/></svg>';
        html += ' Peer Overlap Analysis</div>';

        // Pairwise overlap rows
        html += '<div class="peer-overlap-pairs">';
        pairs.forEach(function(p) {
            var simColor = p.similarity >= 50 ? 'var(--accent)' : p.similarity >= 25 ? 'var(--warning)' : 'var(--text-secondary)';
            var simLabel = p.similarity >= 50 ? 'High' : p.similarity >= 25 ? 'Moderate' : 'Low';

            html += '<div class="peer-overlap-pair">';
            html += '<div class="peer-overlap-pair-header">';
            html += '<span class="peer-overlap-tickers">' + p.tickerA + ' ↔ ' + p.tickerB + '</span>';
            html += '<span class="peer-overlap-sim" style="color:' + simColor + '">' + p.shared.length + ' shared · ' + p.similarity + '% similarity</span>';
            html += '</div>';

            // Similarity bar
            html += '<div class="peer-overlap-bar">';
            html += '<div class="peer-overlap-bar-fill" style="width:' + Math.max(p.similarity, 2) + '%;background:' + simColor + '"></div>';
            html += '</div>';

            // Show shared peer tickers (up to 12, then "+N more") — clickable
            if (p.shared.length > 0) {
                html += '<div class="peer-overlap-tags">';
                var showCount = Math.min(p.shared.length, 12);
                for (var k = 0; k < showCount; k++) {
                    html += '<span class="peer-overlap-tag peer-overlap-tag-link" data-ticker="' + p.shared[k] + '" tabindex="0" role="button" title="Click to find in table · Shift+click to show in network">' + p.shared[k] + '</span>';
                }
                if (p.shared.length > 12) {
                    html += '<span class="peer-overlap-tag more">+' + (p.shared.length - 12) + ' more</span>';
                }
                html += '</div>';
            } else {
                html += '<div class="peer-overlap-empty">No shared compensation peers</div>';
            }
            html += '</div>';
        });
        html += '</div>';

        // Common to all (only shown when 3+ companies and at least 1 common peer)
        if (selected.length >= 3 && commonToAll.length > 0) {
            html += '<div class="peer-overlap-common">';
            html += '<div class="peer-overlap-common-header">Common to all ' + selected.length + ' companies: ' + commonToAll.length + ' peer' + (commonToAll.length !== 1 ? 's' : '') + '</div>';
            html += '<div class="peer-overlap-tags">';
            var showCommon = Math.min(commonToAll.length, 16);
            for (var m = 0; m < showCommon; m++) {
                html += '<span class="peer-overlap-tag common peer-overlap-tag-link" data-ticker="' + commonToAll[m] + '" tabindex="0" role="button" title="Click to find in table · Shift+click to show in network">' + commonToAll[m] + '</span>';
            }
            if (commonToAll.length > 16) {
                html += '<span class="peer-overlap-tag more">+' + (commonToAll.length - 16) + ' more</span>';
            }
            html += '</div>';
            html += '</div>';
        }

        panel.innerHTML = html;

        // Wire up clickable peer overlap tags — click to find in table, shift+click to show in network
        var tagLinks = panel.querySelectorAll('.peer-overlap-tag-link');
        tagLinks.forEach(function(tag) {
            tag.addEventListener('click', function(e) {
                var ticker = tag.getAttribute('data-ticker');
                if (!ticker) return;
                if (e.shiftKey) {
                    // Shift+click: show in network graph
                    if (window.focusNetworkNode) window.focusNetworkNode(ticker);
                } else {
                    // Regular click: find in table and expand detail panel
                    if (window.findCompanyInTable) window.findCompanyInTable(ticker);
                }
            });
            tag.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    var ticker = tag.getAttribute('data-ticker');
                    if (!ticker) return;
                    if (e.shiftKey) {
                        if (window.focusNetworkNode) window.focusNetworkNode(ticker);
                    } else {
                        if (window.findCompanyInTable) window.findCompanyInTable(ticker);
                    }
                }
            });
        });

        // Insert between comparison chart and grid
        gridEl.parentNode.insertBefore(panel, gridEl);
    }

    function showComparison() {
        if (compareSet.length < 2) return;
        var section = document.getElementById('comparison-section');
        var grid = document.getElementById('comparison-grid');
        // Store focus for return on close
        _preFocusElement = document.activeElement;
        section.classList.add('visible');

        // Role-aware comparison context
        var isRoleComp = activeRole && activeRole !== 'CEO';
        var roleLabel = isRoleComp ? activeRole : 'CEO';

        // ARIA announcement for comparison
        var announceMsg = 'Comparing ' + compareSet.length + ' companies: ' + compareSet.join(', ');
        if (isRoleComp) announceMsg += ' (' + roleLabel + ' view)';
        announce(announceMsg);

        // Grid columns based on count
        grid.className = 'comparison-grid cols-' + Math.min(compareSet.length, 4);

        // Get company data for each ticker
        var selected = compareSet.map(function(ticker) {
            return companies.find(function(c) { return c.ticker === ticker; });
        }).filter(Boolean);

        // Helper: get role exec for a company
        function getRoleExec(c) {
            return (isRoleComp && c._roleExecs && c._roleExecs[activeRole]) ? c._roleExecs[activeRole] : null;
        }
        // Helper: get display comp (role exec total or CEO total)
        function getDisplayComp(c) {
            if (isRoleComp) {
                var re = getRoleExec(c);
                return re ? (re.total || 0) : 0;
            }
            return c.total_compensation || 0;
        }
        // Helper: get display name (role exec name or CEO name)
        function getDisplayName(c) {
            if (isRoleComp) {
                var re = getRoleExec(c);
                return re ? (re.name || '—') : '—';
            }
            return c.ceo_name || '—';
        }

        // Pre-compute ranks (role-aware)
        var sorted;
        var rankMap = {};
        if (isRoleComp) {
            sorted = companies.filter(function(c) { return c._roleExecs && c._roleExecs[activeRole]; })
                .slice().sort(function(a, b) { return (b._roleExecs[activeRole].total || 0) - (a._roleExecs[activeRole].total || 0); });
            sorted.forEach(function(c, i) { rankMap[c.ticker] = i + 1; });
        } else {
            sorted = companies.slice().sort(function(a, b) { return b.total_compensation - a.total_compensation; });
            sorted.forEach(function(c, i) { rankMap[c.ticker] = i + 1; });
        }
        var rankTotal = sorted.length;

        // Pre-compute sector ranks (role-aware)
        var sectorRankMap = {};
        selected.forEach(function(c) {
            if (sectorRankMap[c.sector]) return;
            var peers;
            if (isRoleComp) {
                peers = companies.filter(function(x) { return x.sector === c.sector && x._roleExecs && x._roleExecs[activeRole]; })
                    .sort(function(a, b) { return (b._roleExecs[activeRole].total || 0) - (a._roleExecs[activeRole].total || 0); });
            } else {
                peers = companies.filter(function(x) { return x.sector === c.sector; })
                    .sort(function(a, b) { return b.total_compensation - a.total_compensation; });
            }
            sectorRankMap[c.sector] = {};
            peers.forEach(function(p, i) { sectorRankMap[c.sector][p.ticker] = { rank: i + 1, total: peers.length }; });
        });

        // Find max/min for relative bars (role-aware)
        var maxComp = Math.max.apply(null, selected.map(function(c) { return getDisplayComp(c); }));
        var maxRatio = Math.max.apply(null, selected.map(function(c) { return c.pay_ratio || 0; }));
        var maxWorker = Math.max.apply(null, selected.map(function(c) { return c.median_worker_pay || 0; }));

        // Determine best/worst for highlighting (role-aware)
        var compValues = selected.map(function(c) { return getDisplayComp(c); });
        var ratioValues = selected.filter(function(c) { return c.pay_ratio != null; }).map(function(c) { return c.pay_ratio; });
        var workerValues = selected.filter(function(c) { return c.median_worker_pay != null; }).map(function(c) { return c.median_worker_pay; });

        // Build role context for chart rendering
        var roleCtx = isRoleComp ? {
            role: activeRole,
            getComp: getDisplayComp,
            getExec: getRoleExec
        } : null;

        // === Comparison Summary Chart (SVG) ===
        var chartContainer = document.getElementById('comparison-chart');
        if (!chartContainer) {
            chartContainer = document.createElement('div');
            chartContainer.id = 'comparison-chart';
            chartContainer.className = 'comparison-chart-container';
            grid.parentNode.insertBefore(chartContainer, grid);
        }
        renderComparisonChart(chartContainer, selected, rankMap, roleCtx);

        // === Peer Overlap Analysis ===
        renderPeerOverlap(selected, grid);

        grid.innerHTML = '';
        selected.forEach(function(c) {
            var card = document.createElement('div');
            card.className = 'comparison-card';

            var rank = rankMap[c.ticker] || '—';
            var sRank = sectorRankMap[c.sector] && sectorRankMap[c.sector][c.ticker]
                ? sectorRankMap[c.sector][c.ticker] : { rank: '—', total: '—' };

            // Peer network info
            var peerInfo = getPeerInfo(c.ticker);
            var peerIn = peerInfo ? peerInfo.selectedBy.length : 0;
            var peerOut = peerInfo ? peerInfo.selects.length : 0;

            // Ratio class (lower is better)
            var ratioClass = '';
            if (c.pay_ratio != null && ratioValues.length > 1) {
                if (c.pay_ratio === Math.min.apply(null, ratioValues)) ratioClass = ' best';
                else if (c.pay_ratio === Math.max.apply(null, ratioValues)) ratioClass = ' worst';
            }
            var ratioPct = maxRatio > 0 && c.pay_ratio ? (c.pay_ratio / maxRatio * 100) : 0;

            // Worker pay class (higher is better)
            var workerClass = '';
            if (c.median_worker_pay != null && workerValues.length > 1) {
                if (c.median_worker_pay === Math.max.apply(null, workerValues)) workerClass = ' best';
                else if (c.median_worker_pay === Math.min.apply(null, workerValues)) workerClass = ' worst';
            }
            var workerPct = maxWorker > 0 && c.median_worker_pay ? (c.median_worker_pay / maxWorker * 100) : 0;

            var displayComp = getDisplayComp(c);
            var displayName = getDisplayName(c);

            var html = '<div class="comparison-card-rank">#' + rank + ' / ' + rankTotal;
            // Percentile badge alongside rank (CEO-only)
            if (!isRoleComp && c._compPercentile != null) {
                var _cpLabel = getPercentileLabel(c._compPercentile);
                var _cpClass = getPercentileClass(c._compPercentile);
                html += ' <span class="pctile-badge ' + _cpClass + '" style="font-size:0.6rem;vertical-align:middle;margin-left:6px" title="Compensation percentile: ' + c._compPercentile + ' of 100">' + _cpLabel + '</span>';
            }
            html += '</div>';
            html += '<div class="comparison-card-ticker">' + c.ticker + '</div>';
            html += '<div class="comparison-card-company">' + c.company_name + '</div>';
            // Exec name with role badge when role-filtered
            html += '<div class="comparison-card-ceo">' + displayName;
            if (isRoleComp) {
                html += ' <span class="role-title-badge" style="--role-color:' + (ROLE_COLORS[activeRole] || '#94a3b8') + '">' + roleLabel + '</span>';
            }
            if (!isRoleComp && c._ceoTransition) {
                html += ' <span class="new-ceo-badge" title="CEO transition: succeeded ' + (c._ceoTransition.oldCeo.name || 'previous CEO').replace(/"/g, '&quot;') + ' after FY' + c._ceoTransition.oldCeo.year + '">NEW</span>';
            }
            html += '</div>';

            // Total Compensation (role-aware)
            var compPct = maxComp > 0 ? (displayComp / maxComp * 100) : 0;
            var compClass = displayComp === Math.max.apply(null, compValues) ? ' best' : '';
            html += '<div class="comparison-row"><span class="comparison-row-label">' + roleLabel + ' Total Comp</span><span class="comparison-row-value' + compClass + '">' + formatCurrency(displayComp) + '</span></div>';
            html += '<div class="comparison-row-bar"><div class="comparison-row-bar-fill" style="width:' + compPct + '%;background:' + (isRoleComp ? (ROLE_COLORS[activeRole] || 'var(--accent)') : 'var(--accent)') + '"></div></div>';

            // YoY change badge (role-aware — finds role exec in both years)
            if (c.executives && c.executives.length > 0) {
                var yoyAllYears = [];
                c.executives.forEach(function(e) { if (yoyAllYears.indexOf(e.year) < 0) yoyAllYears.push(e.year); });
                yoyAllYears.sort(function(a, b) { return b - a; });
                if (yoyAllYears.length >= 2) {
                    var yoyYr1 = yoyAllYears[0];
                    var yoyYr2 = yoyAllYears[1];
                    var yoyExecs1 = c.executives.filter(function(e) { return e.year === yoyYr1; });
                    var yoyExecs2 = c.executives.filter(function(e) { return e.year === yoyYr2; });
                    var yoyExec1, yoyExec2;
                    if (isRoleComp) {
                        // Find role exec in each year
                        yoyExec1 = yoyExecs1.find(function(e) { return classifyExecRole(e.title) === activeRole; });
                        yoyExec2 = yoyExecs2.find(function(e) { return classifyExecRole(e.title) === activeRole; });
                    } else {
                        // Find CEO in each year
                        yoyExec1 = yoyExecs1.find(function(e) {
                            return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
                        });
                        if (!yoyExec1 && yoyExecs1.length > 0) {
                            yoyExec1 = yoyExecs1.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
                        }
                        yoyExec2 = yoyExecs2.find(function(e) {
                            return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
                        });
                        if (!yoyExec2 && yoyExecs2.length > 0) {
                            yoyExec2 = yoyExecs2.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
                        }
                    }
                    if (yoyExec1 && yoyExec2 && yoyExec1.total > 0 && yoyExec2.total > 0) {
                        var yoyPctChange = ((yoyExec1.total - yoyExec2.total) / yoyExec2.total * 100);
                        var yoyIsPos = yoyPctChange >= 0;
                        var yoyArrow = yoyIsPos ? '▲' : '▼';
                        var yoySign = yoyIsPos ? '+' : '';
                        var yoyCls = yoyIsPos ? 'positive' : 'negative';
                        html += '<div class="comparison-yoy-badge ' + yoyCls + '">';
                        html += '<span class="comparison-yoy-arrow">' + yoyArrow + '</span> ';
                        html += yoySign + yoyPctChange.toFixed(1) + '% vs FY' + yoyYr2;
                        html += '</div>';
                    }
                }
            }

            // Sector Rank (role-aware)
            html += '<div class="comparison-row"><span class="comparison-row-label">Sector</span><span class="comparison-row-value">' + (c.sector || '—') + '</span></div>';
            html += '<div class="comparison-row"><span class="comparison-row-label">' + (isRoleComp ? roleLabel + ' ' : '') + 'Sector Rank</span><span class="comparison-row-value">#' + sRank.rank + ' of ' + sRank.total + '</span></div>';

            // Pay Ratio
            var ratioDisplay = c.pay_ratio ? formatRatio(c.pay_ratio) : '<span class="data-na"><span class="data-na-icon">⚠</span> N/A</span>';
            html += '<div class="comparison-row"><span class="comparison-row-label">Pay Ratio</span><span class="comparison-row-value' + ratioClass + '">' + ratioDisplay + '</span></div>';
            if (c.pay_ratio) {
                html += '<div class="comparison-row-bar"><div class="comparison-row-bar-fill" style="width:' + ratioPct + '%;background:' + (c.pay_ratio > 1000 ? 'var(--negative)' : c.pay_ratio > 500 ? 'var(--warning)' : 'var(--positive)') + '"></div></div>';
            }

            // Median Worker Pay
            var workerDisplay = c.median_worker_pay ? formatCompact(c.median_worker_pay) : '<span class="data-na"><span class="data-na-icon">⚠</span> N/A</span>';
            html += '<div class="comparison-row"><span class="comparison-row-label">Worker Pay</span><span class="comparison-row-value' + workerClass + '">' + workerDisplay + '</span></div>';
            if (c.median_worker_pay) {
                html += '<div class="comparison-row-bar"><div class="comparison-row-bar-fill" style="width:' + workerPct + '%;background:var(--positive)"></div></div>';
            }

            // Peer Network
            html += '<div class="comparison-row"><span class="comparison-row-label">Peers</span><span class="comparison-row-value">' + peerIn + ' in · ' + peerOut + ' out</span></div>';

            // Action buttons row — always shown (Find in Table is always available)
            html += '<div class="comparison-card-actions">';

            // "Find in Table" button — searches the table for this company and expands its detail panel
            html += '<button class="detail-table-btn" data-ticker="' + c.ticker.replace(/"/g, '&quot;') + '">';
            html += '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>';
            html += ' Find in Table</button>';

            // "Show in Network" button — only shown for companies with peer connections
            if (peerInfo && (peerInfo.selectedBy.length > 0 || peerInfo.selects.length > 0)) {
                html += '<button class="detail-network-btn" data-ticker="' + c.ticker.replace(/"/g, '&quot;') + '">';
                html += '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/><path d="M6 7l4 3M14 10l4-3M6 17l4-3M14 14l4 3"/></svg>';
                html += ' Show in Network</button>';
            }

            html += '</div>';

            card.innerHTML = html;

            // Attach click handler for the "Find in Table" button
            var tableBtn = card.querySelector('.detail-table-btn[data-ticker]');
            if (tableBtn) {
                tableBtn.addEventListener('click', function() {
                    var ticker = this.getAttribute('data-ticker');
                    if (window.findCompanyInTable) window.findCompanyInTable(ticker);
                });
            }

            // Attach click handler for the "Show in Network" button
            var netBtn = card.querySelector('.detail-network-btn[data-ticker]');
            if (netBtn) {
                netBtn.addEventListener('click', function() {
                    var ticker = this.getAttribute('data-ticker');
                    if (window.focusNetworkNode) window.focusNetworkNode(ticker);
                });
            }

            grid.appendChild(card);
        });

        // Scroll to comparison section and focus it
        setTimeout(function() {
            var headerHeight = getStickyOffset();
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
            // Focus the comparison section for keyboard/screen reader users
            if (!section.hasAttribute('tabindex')) section.setAttribute('tabindex', '-1');
            setTimeout(function() { section.focus({ preventScroll: true }); }, 400);
        }, 50);
    }

    // Wire up tray buttons
    document.getElementById('compare-go-btn').addEventListener('click', showComparison);
    document.getElementById('compare-clear-btn').addEventListener('click', clearCompare);
    document.getElementById('comparison-close-btn').addEventListener('click', function() {
        document.getElementById('comparison-section').classList.remove('visible');
        var chartEl = document.getElementById('comparison-chart');
        if (chartEl) chartEl.innerHTML = '';
        var overlapEl = document.getElementById('peer-overlap-panel');
        if (overlapEl) overlapEl.remove();
        // Return focus to the element that triggered the comparison
        if (_preFocusElement && _preFocusElement.isConnected) {
            _preFocusElement.focus();
            _preFocusElement = null;
        }
    });

    // === Comparison Export: Build data rows for copy/download ===
    function getComparisonExportData() {
        if (compareSet.length < 2) return null;
        var isRoleExport = activeRole && activeRole !== 'CEO';
        var roleLabel = isRoleExport ? activeRole : 'CEO';
        var selected = compareSet.map(function(ticker) {
            return companies.find(function(c) { return c.ticker === ticker; });
        }).filter(Boolean);
        if (selected.length < 2) return null;

        // Build column headers
        var headers = ['Ticker', 'Company', roleLabel + ' Name', roleLabel + ' Total Comp ($)',
            'YoY Change (%)', 'Sector', 'Pay Ratio', 'Median Worker Pay ($)',
            'Stock Awards %', 'Peer In', 'Peer Out'];
        if (!isRoleExport) {
            headers.push('CEO Concentration %');
            headers.push('Percentile');
        }

        var rows = selected.map(function(c) {
            var displayName, displayComp;
            if (isRoleExport && c._roleExecs && c._roleExecs[activeRole]) {
                var re = c._roleExecs[activeRole];
                displayName = re.name || '';
                displayComp = re.total || 0;
            } else {
                displayName = c.ceo_name || '';
                displayComp = c.total_compensation || 0;
            }

            // YoY for this exec
            var yoyVal = '';
            if (c.executives && c.executives.length > 0) {
                var allYrs = [];
                c.executives.forEach(function(e) { if (allYrs.indexOf(e.year) < 0) allYrs.push(e.year); });
                allYrs.sort(function(a, b) { return b - a; });
                if (allYrs.length >= 2) {
                    var execs1 = c.executives.filter(function(e) { return e.year === allYrs[0]; });
                    var execs2 = c.executives.filter(function(e) { return e.year === allYrs[1]; });
                    var exec1, exec2;
                    if (isRoleExport) {
                        exec1 = execs1.find(function(e) { return classifyExecRole(e.title) === activeRole; });
                        exec2 = execs2.find(function(e) { return classifyExecRole(e.title) === activeRole; });
                    } else {
                        exec1 = execs1.find(function(e) { return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title)); });
                        if (!exec1 && execs1.length > 0) exec1 = execs1.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
                        exec2 = execs2.find(function(e) { return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title)); });
                        if (!exec2 && execs2.length > 0) exec2 = execs2.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
                    }
                    if (exec1 && exec2 && exec1.total > 0 && exec2.total > 0) {
                        yoyVal = ((exec1.total - exec2.total) / exec2.total * 100).toFixed(1);
                    }
                }
            }

            var peerInfo = getPeerInfo(c.ticker);
            var peerIn = peerInfo ? peerInfo.selectedBy.length : 0;
            var peerOut = peerInfo ? peerInfo.selects.length : 0;

            var row = [
                c.ticker,
                c.company_name || '',
                displayName,
                displayComp,
                yoyVal,
                c.sector || '',
                c.pay_ratio || '',
                c.median_worker_pay || '',
                c._ceoStockPct != null ? c._ceoStockPct : '',
                peerIn,
                peerOut
            ];
            if (!isRoleExport) {
                row.push(c._ceoConcPct != null ? Math.round(c._ceoConcPct * 10) / 10 : '');
                row.push(c._compPercentile || '');
            }
            return row;
        });
        return { headers: headers, rows: rows, roleLabel: roleLabel };
    }

    // Copy comparison as tab-separated table to clipboard
    document.getElementById('comparison-copy-btn').addEventListener('click', function() {
        var data = getComparisonExportData();
        if (!data) return;
        var tsv = data.headers.join('\t') + '\n' + data.rows.map(function(r) { return r.join('\t'); }).join('\n');
        var btn = this;
        navigator.clipboard.writeText(tsv).then(function() {
            btn.classList.add('copied');
            var svgEl = btn.querySelector('svg');
            var origHtml = btn.innerHTML;
            btn.innerHTML = '';
            if (svgEl) btn.appendChild(svgEl);
            btn.appendChild(document.createTextNode(' Copied!'));
            announce('Comparison table copied to clipboard with ' + data.rows.length + ' companies');
            setTimeout(function() {
                btn.classList.remove('copied');
                btn.innerHTML = origHtml;
            }, 2000);
        }).catch(function() {
            // Fallback for older browsers
            var ta = document.createElement('textarea');
            ta.value = tsv;
            ta.style.position = 'fixed'; ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            btn.classList.add('copied');
            setTimeout(function() { btn.classList.remove('copied'); }, 2000);
            announce('Comparison table copied to clipboard');
        });
    });

    // Download comparison as CSV
    document.getElementById('comparison-csv-btn').addEventListener('click', function() {
        var data = getComparisonExportData();
        if (!data) return;
        var csv = data.headers.map(csvEscape).join(',') + '\n' + data.rows.map(function(r) {
            return r.map(function(v) { return csvEscape(String(v)); }).join(',');
        }).join('\n');
        var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        var fname = 'comparison-' + data.roleLabel.toLowerCase() + '-' + compareSet.join('-');
        a.download = fname + '.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        announce('Downloaded comparison CSV for ' + data.rows.length + ' companies');
    });

    // Expose for use in renderTable
    window._compareSet = compareSet;
    window._toggleCompare = toggleCompare;
    window._updateCompareButtons = updateCompareButtons;

    // Restore comparison set from URL hash (after comparison system is initialized)
    (function restoreCompareFromHash() {
        var state = parseHash();
        if (!state || !state.cmp) return;
        var tickers = state.cmp.split(',').map(decodeURIComponent).filter(function(t) {
            return t && companies.some(function(c) { return c.ticker === t; });
        }).slice(0, MAX_COMPARE);
        if (tickers.length === 0) return;
        tickers.forEach(function(t) {
            if (compareSet.indexOf(t) < 0) compareSet.push(t);
        });
        updateCompareTray();
        updateCompareButtons();
        // Auto-show comparison view if 2+ valid tickers
        if (compareSet.length >= 2) {
            setTimeout(function() { showComparison(); }, 150);
        }
    })();

    // Expose comparison chart redraw for theme toggle
    window._redrawComparisonChart = function() {
        var section = document.getElementById('comparison-section');
        if (!section || !section.classList.contains('visible')) return;
        var chartEl = document.getElementById('comparison-chart');
        if (!chartEl) return;
        var selected = compareSet.map(function(ticker) {
            return companies.find(function(c) { return c.ticker === ticker; });
        }).filter(Boolean);
        if (selected.length < 2) return;
        var isRoleRedraw = activeRole && activeRole !== 'CEO';
        var sorted, rankMap = {};
        if (isRoleRedraw) {
            sorted = companies.filter(function(c) { return c._roleExecs && c._roleExecs[activeRole]; })
                .slice().sort(function(a, b) { return (b._roleExecs[activeRole].total || 0) - (a._roleExecs[activeRole].total || 0); });
        } else {
            sorted = companies.slice().sort(function(a, b) { return b.total_compensation - a.total_compensation; });
        }
        sorted.forEach(function(c, i) { rankMap[c.ticker] = i + 1; });
        var roleCtxRedraw = isRoleRedraw ? {
            role: activeRole,
            getComp: function(c) { return (c._roleExecs && c._roleExecs[activeRole]) ? (c._roleExecs[activeRole].total || 0) : 0; },
            getExec: function(c) { return (c._roleExecs && c._roleExecs[activeRole]) ? c._roleExecs[activeRole] : null; }
        } : null;
        renderComparisonChart(chartEl, selected, rankMap, roleCtxRedraw);
    };

    // Listen for browser back/forward
    window.addEventListener('hashchange', function() {
        // Reset to defaults first
        currentSort = { key: 'total_compensation', dir: 'desc' };
        activeSector = null;
        searchTerm = '';
        currentPage = 1;
        window._activeRatioBucket = null;
        window._activeDistFilter = null;
        window._activeCeoTransitionFilter = false;
        window._activeTeamCompletenessFilter = null;
        window._activeYoYBucket = null;
        _expandedDetailTicker = null;
        // Close any open detail panel
        var existingDetail = document.querySelector('#comp-tbody .detail-row');
        if (existingDetail) existingDetail.remove();
        document.querySelectorAll('#comp-tbody tr.selected').forEach(function(r) { r.classList.remove('selected'); });
        document.querySelectorAll('#comp-tbody tr[aria-expanded]').forEach(function(r) { r.removeAttribute('aria-expanded'); });
        document.getElementById('table-search').value = '';
        document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
        var allChip = document.querySelector('.chip');
        if (allChip && allChip.textContent === 'All') allChip.classList.add('active');
        var rc = document.getElementById('ratio-filter-chip');
        if (rc) rc.remove();
        var dc = document.getElementById('dist-filter-chip');
        if (dc) dc.remove();
        var tc2 = document.getElementById('transition-filter-chip');
        if (tc2) tc2.remove();
        var tfc3 = document.getElementById('team-filter-chip');
        if (tfc3) tfc3.remove();
        var cc4 = document.getElementById('conc-filter-chip');
        if (cc4) cc4.remove();
        var yc5 = document.getElementById('yoy-filter-chip');
        if (yc5) yc5.remove();
        document.querySelectorAll('th.sortable').forEach(function(t) {
            t.classList.remove('sorted-asc', 'sorted-desc');
            if (t.dataset.sort === 'total_compensation') t.classList.add('sorted-desc');
        });
        applyHashState(companies);
        if (window.highlightSectorBar) window.highlightSectorBar(activeSector);
        if (window.highlightRatioBucket) {
            if (window._activeRatioBucket) {
                window.highlightRatioBucket(window._activeRatioBucket.min, window._activeRatioBucket.max);
            } else {
                window.highlightRatioBucket(null);
            }
        }
        // Restore dist filter chip if present in hash state
        if (window._activeDistFilter) {
            updateDistFilterIndicator();
        }
        // Restore CEO transition filter chip if present in hash state
        if (window._activeCeoTransitionFilter) {
            updateCeoTransitionFilterIndicator();
        }

        // Restore team completeness filter chip if present in hash state
        if (window._activeTeamCompletenessFilter) {
            updateTeamCompletenessFilterIndicator();
        }

        // Restore or clear comparison set from hash
        var hashState = parseHash();
        var hashCmp = hashState && hashState.cmp
            ? hashState.cmp.split(',').map(decodeURIComponent).filter(function(t) {
                return t && companies.some(function(c) { return c.ticker === t; });
            }).slice(0, MAX_COMPARE)
            : [];
        // Sync compareSet with hash
        compareSet.length = 0;
        hashCmp.forEach(function(t) { compareSet.push(t); });
        updateCompareTray();
        updateCompareButtons();
        // Show or hide comparison section
        var compSection = document.getElementById('comparison-section');
        if (compareSet.length >= 2) {
            showComparison();
        } else if (compSection) {
            compSection.classList.remove('visible');
            var chartEl = document.getElementById('comparison-chart');
            if (chartEl) chartEl.innerHTML = '';
            var overlapEl = document.getElementById('peer-overlap-panel');
            if (overlapEl) overlapEl.remove();
        }
    });

    // === Print Support: show all rows during print ===
    var _savedPageSize = PAGE_SIZE;
    window.addEventListener('beforeprint', function() {
        _savedPageSize = PAGE_SIZE;
        PAGE_SIZE = 99999;
        currentPage = 1;
        renderTable(companies);
    });
    window.addEventListener('afterprint', function() {
        PAGE_SIZE = _savedPageSize;
        renderTable(companies);
    });

    // === Keyboard Shortcuts ===
    var kbdOverlay = document.getElementById('kbd-modal-overlay');
    var kbdCloseBtn = document.getElementById('kbd-modal-close');
    var kbdHint = document.getElementById('kbd-hint');

    function showKbdModal() {
        if (kbdOverlay) {
            _preFocusElement = document.activeElement;
            kbdOverlay.classList.add('visible');
            // Focus the close button so keyboard users can dismiss immediately
            if (kbdCloseBtn) setTimeout(function() { kbdCloseBtn.focus(); }, 50);
        }
    }
    function hideKbdModal() {
        if (kbdOverlay) {
            kbdOverlay.classList.remove('visible');
            // Return focus to the element that was focused before the modal opened
            if (_preFocusElement && _preFocusElement.isConnected) {
                _preFocusElement.focus();
                _preFocusElement = null;
            }
        }
    }

    // === Focus Trap for Keyboard Modal ===
    // Trap Tab/Shift+Tab within the modal so focus doesn't escape to the page behind the overlay.
    // Collects all focusable elements inside .kbd-modal at trap time and cycles between them.
    if (kbdOverlay) {
        kbdOverlay.addEventListener('keydown', function(e) {
            if (e.key !== 'Tab') return;
            if (!isKbdModalOpen()) return;

            var modal = kbdOverlay.querySelector('.kbd-modal');
            if (!modal) return;

            var focusable = modal.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            if (focusable.length === 0) return;

            var first = focusable[0];
            var last = focusable[focusable.length - 1];

            if (e.shiftKey) {
                // Shift+Tab: if on first element, wrap to last
                if (document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                }
            } else {
                // Tab: if on last element, wrap to first
                if (document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        });
    }
    function isKbdModalOpen() {
        return kbdOverlay && kbdOverlay.classList.contains('visible');
    }

    if (kbdCloseBtn) kbdCloseBtn.addEventListener('click', hideKbdModal);
    if (kbdOverlay) {
        kbdOverlay.addEventListener('click', function(e) {
            if (e.target === kbdOverlay) hideKbdModal();
        });
    }
    if (kbdHint) kbdHint.addEventListener('click', showKbdModal);

    // Dismiss kbd hint after first interaction (localStorage)
    var kbdHintDismissed = localStorage.getItem('sp500-kbd-hint-dismissed');
    if (kbdHintDismissed && kbdHint) kbdHint.style.display = 'none';

    document.addEventListener('keydown', function(e) {
        var tag = (e.target.tagName || '').toLowerCase();
        var inInput = tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable;

        // Escape works everywhere
        if (e.key === 'Escape') {
            // Priority: close kbd modal → close comparison → close detail panel → clear filters
            if (isKbdModalOpen()) {
                hideKbdModal();
                e.preventDefault();
                return;
            }
            var compSection = document.getElementById('comparison-section');
            if (compSection && compSection.classList.contains('visible')) {
                compSection.classList.remove('visible');
                var chartEl = document.getElementById('comparison-chart');
                if (chartEl) chartEl.innerHTML = '';
                announce('Comparison panel closed');
                // Return focus to the element that triggered the comparison
                if (_preFocusElement && _preFocusElement.isConnected) {
                    _preFocusElement.focus();
                    _preFocusElement = null;
                }
                e.preventDefault();
                return;
            }
            var detailRow = document.querySelector('.detail-row');
            if (detailRow) {
                detailRow.remove();
                document.querySelectorAll('tr.selected').forEach(function(r) { r.classList.remove('selected'); });
                announce('Detail panel closed');
                // Return focus to the row that opened the detail panel
                if (_detailTriggerRow && _detailTriggerRow.isConnected) {
                    _detailTriggerRow.focus();
                    _detailTriggerRow = null;
                }
                e.preventDefault();
                return;
            }
            // Clear all filters and search
            if (activeSector || searchTerm || window._activeRatioBucket || window._activeDistFilter || window._activeConcTier || window._activeCeoTransitionFilter || window._activeTeamCompletenessFilter || window._activeYoYBucket || (activeRole && activeRole !== 'CEO')) {
                activeSector = null;
                searchTerm = '';
                activeRole = null;
                currentPage = 1;
                document.getElementById('table-search').value = '';
                // Reset role chips to CEO default
                document.querySelectorAll('.role-chip').forEach(function(rc) { rc.classList.remove('active'); });
                var firstRoleChip = document.querySelector('.role-chip');
                if (firstRoleChip) firstRoleChip.classList.add('active');
                updateRoleColumnHeader();
                if (window._activeRatioBucket) {
                    window._activeRatioBucket = null;
                    var rc = document.getElementById('ratio-filter-chip');
                    if (rc) rc.remove();
                }
                if (window._activeDistFilter) {
                    window._activeDistFilter = null;
                    var dc = document.getElementById('dist-filter-chip');
                    if (dc) dc.remove();
                }
                if (window._activeConcTier) {
                    window._activeConcTier = null;
                    var cc3 = document.getElementById('conc-filter-chip');
                    if (cc3) cc3.remove();
                }
                if (window._activeCeoTransitionFilter) {
                    window._activeCeoTransitionFilter = false;
                    var tc = document.getElementById('transition-filter-chip');
                    if (tc) tc.remove();
                }
                if (window._activeTeamCompletenessFilter) {
                    window._activeTeamCompletenessFilter = null;
                    var tfc = document.getElementById('team-filter-chip');
                    if (tfc) tfc.remove();
                }
                if (window._activeYoYBucket) {
                    window._activeYoYBucket = null;
                    var yfc2 = document.getElementById('yoy-filter-chip');
                    if (yfc2) yfc2.remove();
                }
                document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
                var allChip = document.querySelector('.chip');
                if (allChip) allChip.classList.add('active');
                currentSort = { key: 'total_compensation', dir: 'desc' };
                document.querySelectorAll('th.sortable').forEach(function(t) {
                    t.classList.remove('sorted-asc', 'sorted-desc');
                    t.setAttribute('aria-sort', 'none');
                    if (t.dataset.sort === 'total_compensation') {
                        t.classList.add('sorted-desc');
                        t.setAttribute('aria-sort', 'descending');
                    }
                });
                announce('All filters cleared');
                renderTable(companies);
                if (window.highlightSectorBar) window.highlightSectorBar(null);
                if (window.highlightRatioBucket) window.highlightRatioBucket(null);
                e.preventDefault();
                return;
            }
            // If in search, blur it
            if (inInput) {
                e.target.blur();
                e.preventDefault();
            }
            return;
        }

        // All other shortcuts only fire when not in an input field
        if (inInput) return;

        // Don't fire with Ctrl/Cmd/Alt modifiers (except for our specific combos)
        if (e.ctrlKey || e.metaKey || e.altKey) return;

        switch (e.key) {
            case '/':
                // Focus table search
                e.preventDefault();
                var searchInput = document.getElementById('table-search');
                if (searchInput) {
                    var headerHeight = getStickyOffset();
                    var tableSection = document.getElementById('compensation-table-section');
                    if (tableSection) {
                        var sectionTop = tableSection.getBoundingClientRect().top + window.scrollY - headerHeight - 8;
                        window.scrollTo({ top: sectionTop, behavior: getScrollBehavior() });
                    }
                    setTimeout(function() { searchInput.focus(); searchInput.select(); }, 150);
                }
                // Dismiss the hint badge permanently
                if (kbdHint && !kbdHintDismissed) {
                    kbdHint.style.display = 'none';
                    localStorage.setItem('sp500-kbd-hint-dismissed', '1');
                    kbdHintDismissed = '1';
                }
                break;

            case '?':
                e.preventDefault();
                if (isKbdModalOpen()) {
                    hideKbdModal();
                } else {
                    showKbdModal();
                }
                if (kbdHint && !kbdHintDismissed) {
                    kbdHint.style.display = 'none';
                    localStorage.setItem('sp500-kbd-hint-dismissed', '1');
                    kbdHintDismissed = '1';
                }
                break;

            case 'ArrowLeft':
                // Previous table page
                if (currentPage > 1) {
                    e.preventDefault();
                    currentPage--;
                    renderTable(companies);
                    scrollToTable();
                }
                break;

            case 'ArrowRight':
                // Next table page
                var totalFiltered = companies.slice();
                if (activeSector) totalFiltered = totalFiltered.filter(function(c) { return c.sector === activeSector; });
                if (searchTerm) {
                    var sq = searchTerm.toLowerCase();
                    totalFiltered = totalFiltered.filter(function(c) {
                        if ((c.ticker || '').toLowerCase().indexOf(sq) >= 0 ||
                            (c.company_name || '').toLowerCase().indexOf(sq) >= 0 ||
                            (c.ceo_name || '').toLowerCase().indexOf(sq) >= 0 ||
                            (c.sector || '').toLowerCase().indexOf(sq) >= 0) return true;
                        // Also search NEO names when EDGAR data is available
                        if (c.executives) {
                            for (var ei = 0; ei < c.executives.length; ei++) {
                                if (c.executives[ei].name && c.executives[ei].name.toLowerCase().indexOf(sq) >= 0) return true;
                            }
                        }
                        return false;
                    });
                }
                if (window._activeRatioBucket) {
                    var arb = window._activeRatioBucket;
                    totalFiltered = totalFiltered.filter(function(c) {
                        return c.pay_ratio != null && c.pay_ratio >= arb.min && c.pay_ratio < arb.max;
                    });
                }
                if (window._activeDistFilter) {
                    var adf = window._activeDistFilter;
                    totalFiltered = totalFiltered.filter(function(c) {
                        return c.total_compensation != null && c.total_compensation >= adf.min && c.total_compensation <= adf.max;
                    });
                }
                if (window._activeCeoTransitionFilter) {
                    totalFiltered = totalFiltered.filter(function(c) { return c._ceoTransition != null; });
                }
                if (window._activeTeamCompletenessFilter) {
                    if (window._activeTeamCompletenessFilter === 'missing') {
                        totalFiltered = totalFiltered.filter(function(c) { return c._teamMissingExpected && c._teamMissingExpected.length > 0 && c.executives && c.executives.length > 0; });
                    } else if (window._activeTeamCompletenessFilter === 'complete') {
                        totalFiltered = totalFiltered.filter(function(c) { return c._teamRoleCount >= 4; });
                    }
                }
                if (activeRole && activeRole !== 'CEO') {
                    totalFiltered = totalFiltered.filter(function(c) { return c._roleExecs && c._roleExecs[activeRole]; });
                }
                var maxPages = Math.max(1, Math.ceil(totalFiltered.length / PAGE_SIZE));
                if (currentPage < maxPages) {
                    e.preventDefault();
                    currentPage++;
                    renderTable(companies);
                    scrollToTable();
                }
                break;

            case 't':
            case 'T':
                e.preventDefault();
                scrollToTable();
                break;

            case 'n':
            case 'N':
                e.preventDefault();
                var netSection = document.getElementById('peer-network-section');
                if (netSection) {
                    var hh = getStickyOffset();
                    var nt = netSection.getBoundingClientRect().top + window.scrollY - hh - 12;
                    window.scrollTo({ top: nt, behavior: getScrollBehavior() });
                }
                break;

            case 'c':
            case 'C':
                e.preventDefault();
                var chartPanel = document.getElementById('sector-chart-panel');
                if (chartPanel) {
                    var hh2 = getStickyOffset();
                    var ct = chartPanel.getBoundingClientRect().top + window.scrollY - hh2 - 12;
                    window.scrollTo({ top: ct, behavior: getScrollBehavior() });
                }
                break;

            case 'i':
            case 'I':
                e.preventDefault();
                var insightsSection = document.getElementById('insights-section');
                if (insightsSection) {
                    var hh3 = getStickyOffset();
                    var it = insightsSection.getBoundingClientRect().top + window.scrollY - hh3 - 12;
                    window.scrollTo({ top: it, behavior: getScrollBehavior() });
                }
                break;

            case 'o':
            case 'O':
                e.preventDefault();
                var compSection2 = document.getElementById('composition-section');
                if (compSection2) {
                    var hh4 = getStickyOffset();
                    var ot = compSection2.getBoundingClientRect().top + window.scrollY - hh4 - 12;
                    window.scrollTo({ top: ot, behavior: getScrollBehavior() });
                }
                break;

            case 'r':
            case 'R':
                e.preventDefault();
                var trendsSection = document.getElementById('trends-section');
                if (trendsSection) {
                    var hh5 = getStickyOffset();
                    var rt = trendsSection.getBoundingClientRect().top + window.scrollY - hh5 - 12;
                    window.scrollTo({ top: rt, behavior: getScrollBehavior() });
                }
                break;

            case 's':
            case 'S':
                e.preventDefault();
                var sectorsSection = document.getElementById('sector-analytics-section');
                if (sectorsSection) {
                    var hh6 = getStickyOffset();
                    var st = sectorsSection.getBoundingClientRect().top + window.scrollY - hh6 - 12;
                    window.scrollTo({ top: st, behavior: getScrollBehavior() });
                }
                break;

            case 'd':
            case 'D':
                e.preventDefault();
                toggleTheme();
                break;
        }
    });

    // === Section Navigation Bar — scroll tracking + click handlers ===
    (function initSectionNav() {
        var nav = document.getElementById('section-nav');
        if (!nav) return;
        var links = nav.querySelectorAll('.section-nav-link');
        if (!links.length) return;

        // Dynamic top position based on actual header height
        var header = document.querySelector('header');
        function updateNavTop() {
            if (header) {
                nav.style.top = header.offsetHeight + 'px';
            }
        }
        updateNavTop();
        window.addEventListener('resize', function() {
            setTimeout(updateNavTop, 100);
        });

        // Map of section IDs to their link elements
        var sectionIds = [];
        links.forEach(function(link) {
            sectionIds.push(link.dataset.section);
        });

        // Smooth scroll to section on click
        links.forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                var targetId = link.dataset.section;
                var target = document.getElementById(targetId);
                if (!target) return;

                var stickyH = getStickyOffset();
                var targetTop = target.getBoundingClientRect().top + window.scrollY - stickyH - 8;
                window.scrollTo({ top: targetTop, behavior: getScrollBehavior() });

                // Update active state immediately
                links.forEach(function(l) { l.classList.remove('active'); });
                link.classList.add('active');

                // ARIA announcement
                var sectionName = link.textContent.trim();
                announce('Navigated to ' + sectionName + ' section');
            });
        });

        // IntersectionObserver to track which section is currently visible
        // Use a rootMargin that accounts for the sticky header + nav bar height
        var _navUpdatePending = false;
        var _visibleSections = {};

        var observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                _visibleSections[entry.target.id] = entry.isIntersecting ? entry.intersectionRatio : 0;
            });

            if (_navUpdatePending) return;
            _navUpdatePending = true;
            requestAnimationFrame(function() {
                _navUpdatePending = false;

                // Find the topmost visible section
                var bestSection = null;
                var bestTop = Infinity;

                sectionIds.forEach(function(id) {
                    var el = document.getElementById(id);
                    if (!el) return;
                    var rect = el.getBoundingClientRect();
                    // Consider a section "active" if its top is above the viewport midpoint
                    // and it's partially visible (not entirely scrolled past)
                    var viewportMid = window.innerHeight * 0.4;
                    if (rect.top < viewportMid && rect.bottom > 0) {
                        if (rect.top < bestTop || (rect.top === bestTop)) {
                            // Pick the one whose top is closest to the nav bar (most recently scrolled into)
                            bestSection = id;
                            bestTop = rect.top;
                        }
                    }
                });

                // Fallback: if nothing is above midpoint, use the first section
                if (!bestSection) {
                    for (var i = 0; i < sectionIds.length; i++) {
                        var el = document.getElementById(sectionIds[i]);
                        if (el && el.getBoundingClientRect().top < window.innerHeight) {
                            bestSection = sectionIds[i];
                            break;
                        }
                    }
                }

                if (bestSection) {
                    links.forEach(function(l) {
                        l.classList.toggle('active', l.dataset.section === bestSection);
                    });

                    // Scroll the active link into view within the nav bar (for narrow screens)
                    var activeLink = nav.querySelector('.section-nav-link.active');
                    if (activeLink) {
                        var navInner = nav.querySelector('.section-nav-inner');
                        if (navInner && navInner.scrollWidth > navInner.clientWidth) {
                            var linkLeft = activeLink.offsetLeft;
                            var linkRight = linkLeft + activeLink.offsetWidth;
                            var scrollLeft = navInner.scrollLeft;
                            var visibleRight = scrollLeft + navInner.clientWidth;
                            if (linkLeft < scrollLeft + 20) {
                                navInner.scrollTo({ left: Math.max(0, linkLeft - 20), behavior: 'auto' });
                            } else if (linkRight > visibleRight - 20) {
                                navInner.scrollTo({ left: linkRight - navInner.clientWidth + 20, behavior: 'auto' });
                            }
                        }
                    }
                }
            });
        }, {
            rootMargin: '-80px 0px -40% 0px',
            threshold: [0, 0.1, 0.25]
        });

        // Observe each tracked section
        sectionIds.forEach(function(id) {
            var el = document.getElementById(id);
            if (el) observer.observe(el);
        });

        // Add scrolled shadow class to nav when page scrolls past metrics strip
        var _navScrolledTimer = null;
        window.addEventListener('scroll', function() {
            if (_navScrolledTimer) return;
            _navScrolledTimer = requestAnimationFrame(function() {
                _navScrolledTimer = null;
                nav.classList.toggle('scrolled', window.scrollY > 120);
            });
        }, { passive: true });
    })();
})();
