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
    searchTerm = '';
    window._activeRatioBucket = null;
    window._activeDistFilter = null;

    // Remove filter chips if present
    var ratioChip = document.getElementById('ratio-filter-chip');
    if (ratioChip) ratioChip.remove();
    var distChip = document.getElementById('dist-filter-chip');
    if (distChip) distChip.remove();

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
    var sortLabelMap = { '_ceoYoYSort': 'CEO comp year over year change', '_ceoStockPctSort': 'CEO equity percentage of total comp', '_compPercentile': 'compensation percentile rank' };
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

    // Click actions for each insight — use closures over computed data
    // Actions reference window-level APIs set up in init(); safe because user clicks happen after init completes

    // Helper: reset table to clean state, apply sort, scroll
    function insightResetAndSort(sortKey, sortDir) {
        currentSort = { key: sortKey, dir: sortDir };
        activeSector = null;
        searchTerm = '';
        currentPage = 1;
        document.getElementById('table-search').value = '';
        if (window._activeRatioBucket) {
            window._activeRatioBucket = null;
            var rc = document.getElementById('ratio-filter-chip');
            if (rc) rc.remove();
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
        // Clear ratio bucket filter if active
        if (window._activeRatioBucket) {
            window._activeRatioBucket = null;
            var rc = document.getElementById('ratio-filter-chip');
            if (rc) rc.remove();
        }
        // Clear distribution filter if active
        if (window._activeDistFilter) {
            window._activeDistFilter = null;
            var dc = document.getElementById('dist-filter-chip');
            if (dc) dc.remove();
        }
        document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
        allChip.classList.add('active');
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
            // Clear ratio bucket filter if active
            if (window._activeRatioBucket) {
                window._activeRatioBucket = null;
                var rc = document.getElementById('ratio-filter-chip');
                if (rc) rc.remove();
            }
            // Clear distribution filter if active
            if (window._activeDistFilter) {
                window._activeDistFilter = null;
                var dc = document.getElementById('dist-filter-chip');
                if (dc) dc.remove();
            }
            document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
            chip.classList.add('active');
            renderTable(companies);
            if (window.highlightSectorBar) window.highlightSectorBar(s);
            if (window.highlightRatioBucket) window.highlightRatioBucket(null);
        });
        container.appendChild(chip);
    });
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
    if (currentSort.key === 'sector') {
        return renderSectorSortSummary(companies);
    }
    return null;
}

/* Compensation distribution summary — shown in default sort (total_compensation) and rank sort.
   Displays total combined pay, median vs mean skewness, bracket distribution with inline mini histogram,
   and min/max range context. */
function renderCompDistSummary(companies) {
    var comps = companies.filter(function(c) { return c.total_compensation != null && c.total_compensation > 0; });
    if (comps.length === 0) return null;

    var vals = comps.map(function(c) { return c.total_compensation; }).sort(function(a, b) { return a - b; });
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
        var v = c.total_compensation;
        for (var bi = brackets.length - 1; bi >= 0; bi--) {
            if (v >= brackets[bi].min) { brackets[bi].count++; break; }
        }
    });
    var maxBracketCount = Math.max.apply(null, brackets.map(function(b) { return b.count; }));

    var html = '';

    // Total combined
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

/* Sector sort context summary — shown when sorted by sector column.
   Displays number of sectors, mini sector distribution with color-coded segment bars,
   highest/lowest median pay sectors, and sector spread ratio. */
function renderSectorSortSummary(companies) {
    if (companies.length === 0) return null;

    // Group companies by sector
    var sectorMap = {};
    companies.forEach(function(c) {
        var s = c.sector || 'Unknown';
        if (!sectorMap[s]) sectorMap[s] = { name: s, companies: [], comps: [] };
        sectorMap[s].companies.push(c);
        if (c.total_compensation != null && c.total_compensation > 0) {
            sectorMap[s].comps.push(c.total_compensation);
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

    html += '<span class="summary-divider"></span>';

    // Highest paying sector
    if (highestSector && highestSector.median > 0) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Highest median</span>';
        html += '<span class="summary-stat-value" style="color:' + getSectorColor(highestSector.name) + '">';
        html += highestSector.name + ' ' + formatCurrency(highestSector.median);
        html += '</span></span>';
    }

    // Lowest paying sector
    if (lowestSector && lowestSector.median > 0 && lowestSector.name !== highestSector.name) {
        html += '<span class="summary-stat">';
        html += '<span class="summary-stat-label">Lowest median</span>';
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

    // Compute statistics
    var comps = filtered.map(function(c) { return c.total_compensation || 0; });
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

    // Company count
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-value accent">' + filtered.length + '</span>';
    html += '<span class="summary-stat-label">companies';
    if (sectorCount === 1) html += ' · ' + Object.keys(sectors)[0];
    else html += ' · ' + sectorCount + ' sectors';
    html += '</span>';
    html += '</span>';

    html += '<span class="summary-divider"></span>';

    // Median Total Comp
    html += '<span class="summary-stat">';
    html += '<span class="summary-stat-label">Median comp</span>';
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
            if (c.total_compensation > 0) sectorMap[s].push(c.total_compensation);
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

    // Render summary statistics bar
    renderSummaryBar(filtered, companies);

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

    // Pagination
    var totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;
    var startIdx = (currentPage - 1) * PAGE_SIZE;
    var pageItems = filtered.slice(startIdx, startIdx + PAGE_SIZE);

    var tbody = document.getElementById('comp-tbody');
    tbody.innerHTML = '';

    // Compute max compensation in filtered view for inline data bars
    var maxFilteredComp = 0;
    filtered.forEach(function(c) { if (c.total_compensation > maxFilteredComp) maxFilteredComp = c.total_compensation; });

    pageItems.forEach(function(c, i) {
        var globalIdx = startIdx + i;
        var tr = document.createElement('tr');

        // Compensation value with inline data bar + optional top-10 badge
        var barPct = maxFilteredComp > 0 ? Math.max(0, Math.min(100, (c.total_compensation || 0) / maxFilteredComp * 100)) : 0;
        var compHtml = '<div class="comp-bar-cell"><div class="comp-bar" style="width:' + barPct.toFixed(1) + '%"></div><span class="comp-value">' + formatCurrency(c.total_compensation) + '</span>';
        if (c.neo_count) {
            compHtml += ' <span class="neo-badge" title="' + c.neo_count + ' Named Executive Officers from SEC EDGAR">' + c.neo_count + ' NEOs</span>';
        }
        if (_outlierTop10[c.ticker]) {
            compHtml += ' <span class="outlier-badge top-comp" title="Top 10 highest paid CEO in S&amp;P 500">#' + _outlierTop10[c.ticker] + '</span>';
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

        tr.innerHTML = '<td>' + (globalIdx + 1) + ' ' + compareBtnHtml + '</td>' +
            '<td><span class="ticker">' + c.ticker + '</span></td>' +
            '<td><span class="company">' + c.company_name + '</span></td>' +
            '<td>' + c.ceo_name + '</td>' +
            '<td>' + compHtml + '</td>' +
            '<td class="yoy-cell">' + yoyCell + '</td>' +
            '<td class="stock-pct-cell">' + stockPctCell + '</td>' +
            '<td class="pctile-cell">' + (function() {
                if (c._compPercentile == null) return '\u2014';
                var pl = getPercentileLabel(c._compPercentile);
                var pc = getPercentileClass(c._compPercentile);
                return '<span class="pctile-badge ' + pc + '" title="Compensation percentile: ' + c._compPercentile + ' of 100">' + pl + '</span>';
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
        var html = '<td colspan="11"><div class="detail-panel" tabindex="-1">';
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

                    html += '<div class="ceo-trend-mini">';
                    html += '<div class="ceo-trend-mini-header">';
                    html += '<span class="ceo-trend-mini-title">CEO Pay Trend</span>';
                    html += '<span class="ceo-trend-mini-change ' + overallCls + '" title="FY' + firstTrend.year + ' to FY' + lastTrend.year + '">' + overallSign + overallAbsStr + ' over ' + ceoTrendData.length + ' years</span>';
                    html += '</div>';

                    html += '<div class="ceo-trend-mini-bars">';
                    ceoTrendData.forEach(function(d, i) {
                        var barH = maxTrend > 0 ? Math.max(8, Math.round(d.total / maxTrend * 64)) : 8;
                        var isLatest = (i === ceoTrendData.length - 1);

                        html += '<div class="ceo-trend-mini-col">';
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

                        html += '<div class="ceo-trend-mini-bar" style="height:' + barH + 'px' + (isLatest ? '' : ';opacity:0.55') + '" title="' + (d.name || '') + ' FY' + d.year + ': ' + formatCurrency(d.total) + '"></div>';
                        html += '<div class="ceo-trend-mini-year">FY' + d.year + '</div>';
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
                    html += '<td class="neo-num neo-total">' + formatCompact(total) + '</td>';
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
            tHtml += '<tr class="skeleton-table-row-tr"><td colspan="11"><div class="skeleton-table-row">' +
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

    // Remove metric skeletons before populating with real data
    hideMetricSkeletons();

    populateMetrics(data.comp, data.trends);
    populateInsights(data.comp, data.trends);
    populateTrends(data.trends);
    buildSectorChips(companies);
    renderTable(companies);
    setupSorting(companies);
    setupSearch(companies);
    setupDetailPanel(companies);

    // Expose global API for chart → table cross-section linking
    window.filterBySector = function(sectorName) {
        // Set active sector (null clears filter)
        activeSector = sectorName || null;
        currentPage = 1;

        // Clear distribution filter when sector filter changes directly
        window._activeDistFilter = null;
        var distChip = document.getElementById('dist-filter-chip');
        if (distChip) distChip.remove();

        // Update sector chip active states
        document.querySelectorAll('.chip').forEach(function(chip) {
            chip.classList.remove('active');
            if (!sectorName && chip.textContent === 'All') chip.classList.add('active');
            else if (chip.textContent === sectorName) chip.classList.add('active');
        });

        renderTable(companies);
        pushState();

        // Highlight active bar in sector chart
        if (window.highlightSectorBar) window.highlightSectorBar(sectorName);

        // Clear ratio bucket highlight (sector filter clears ratio)
        if (window.highlightRatioBucket) window.highlightRatioBucket(null);

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
            var chip = document.createElement('button');
            chip.className = 'chip active';
            chip.id = 'dist-filter-chip';
            chip.style.background = 'rgba(0,180,216,0.15)';
            chip.style.borderColor = 'rgba(0,180,216,0.5)';
            chip.style.color = '#00b4d8';
            chip.innerHTML = df.label + ' <span style="margin-left:4px;font-weight:700;">×</span>';
            chip.title = 'Click to clear distribution filter';
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

        // Clear other filters
        activeSector = null;
        searchTerm = '';
        currentPage = 1;
        document.getElementById('table-search').value = '';
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

        // Reset sector chips
        document.querySelectorAll('.chip').forEach(function(chip) {
            chip.classList.remove('active');
            if (chip.textContent === 'All') chip.classList.add('active');
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

        // Clear other filters
        window._activeDistFilter = null;
        var distChip = document.getElementById('dist-filter-chip');
        if (distChip) distChip.remove();

        if (window._activeRatioBucket) {
            window._activeRatioBucket = null;
            var ratioChip = document.getElementById('ratio-filter-chip');
            if (ratioChip) ratioChip.remove();
        }

        // Update sector chip active states
        document.querySelectorAll('.chip').forEach(function(chip) {
            chip.classList.remove('active');
            if (!activeSector && chip.textContent === 'All') chip.classList.add('active');
            else if (chip.textContent === activeSector) chip.classList.add('active');
        });

        renderTable(companies);
        if (window.highlightSectorBar) window.highlightSectorBar(activeSector);
        if (window.highlightRatioBucket) window.highlightRatioBucket(null);

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

        // Clear other filters for clarity
        activeSector = null;
        searchTerm = '';
        currentPage = 1;
        window._activeDistFilter = null;
        var distChip = document.getElementById('dist-filter-chip');
        if (distChip) distChip.remove();
        document.getElementById('table-search').value = '';
        document.querySelectorAll('.chip').forEach(function(chip) {
            chip.classList.remove('active');
            if (chip.textContent === 'All') chip.classList.add('active');
        });

        // Sort by pay ratio descending
        currentSort = { key: 'pay_ratio', dir: 'desc' };
        document.querySelectorAll('th.sortable').forEach(function(t) {
            t.classList.remove('sorted-asc', 'sorted-desc');
            if (t.dataset.sort === 'pay_ratio') t.classList.add('sorted-desc');
        });

        // Update ratio filter indicator
        updateRatioFilterIndicator();

        renderTable(companies);

        // Clear sector chart highlight (sector was cleared)
        if (window.highlightSectorBar) window.highlightSectorBar(null);

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
            var label = 'Ratio: ' + bucket.min + (bucket.max === Infinity ? '+' : '–' + bucket.max) + ':1';
            var chip = document.createElement('button');
            chip.className = 'chip active';
            chip.id = 'ratio-filter-chip';
            chip.style.background = 'rgba(239,71,111,0.15)';
            chip.style.borderColor = 'rgba(239,71,111,0.5)';
            chip.style.color = '#ef476f';
            chip.innerHTML = label + ' <span style="margin-left:4px;font-weight:700;">×</span>';
            chip.title = 'Click to clear ratio filter';
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

                // Clear distribution filter when sector changes
                window._activeDistFilter = null;
                var distChip = document.getElementById('dist-filter-chip');
                if (distChip) distChip.remove();

                // Clear ratio bucket filter when sector changes
                if (window._activeRatioBucket) {
                    window._activeRatioBucket = null;
                    var ratioChip = document.getElementById('ratio-filter-chip');
                    if (ratioChip) ratioChip.remove();
                }

                renderTable(companies);

                // Update sector chip active states
                document.querySelectorAll('.chip').forEach(function(chip) {
                    chip.classList.remove('active');
                    if (!activeSector && chip.textContent === 'All') chip.classList.add('active');
                    else if (chip.textContent === activeSector) chip.classList.add('active');
                });

                if (window.highlightSectorBar) window.highlightSectorBar(activeSector);
                if (window.highlightRatioBucket) window.highlightRatioBucket(null);

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

    // Restore state from URL hash (after charts/network are initialized)
    applyHashState(companies);
    _stateInitialized = true;

    // Apply sector chart highlight if restored from hash
    if (activeSector && window.highlightSectorBar) window.highlightSectorBar(activeSector);

    // Apply ratio bucket highlight if restored from hash
    if (window._activeRatioBucket && window.highlightRatioBucket) {
        window.highlightRatioBucket(window._activeRatioBucket.min, window._activeRatioBucket.max);
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
        var existing = document.getElementById('ratio-filter-chip');
        if (!existing) {
            var bucket = window._activeRatioBucket;
            var label = 'Ratio: ' + bucket.min + (bucket.max === Infinity ? '+' : '–' + bucket.max) + ':1';
            var chip = document.createElement('button');
            chip.className = 'chip active';
            chip.id = 'ratio-filter-chip';
            chip.style.background = 'rgba(239,71,111,0.15)';
            chip.style.borderColor = 'rgba(239,71,111,0.5)';
            chip.style.color = '#ef476f';
            chip.innerHTML = label + ' <span style="margin-left:4px;font-weight:700;">×</span>';
            chip.title = 'Click to clear ratio filter';
            chip.addEventListener('click', function() {
                window._activeRatioBucket = null;
                chip.remove();
                renderTable(companies);
                pushState();
                if (window.highlightRatioBucket) window.highlightRatioBucket(null);
            });
            var controls = document.querySelector('.table-controls');
            if (controls) controls.appendChild(chip);
        }
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

            // CSV header and rows
            var headers = ['Rank', 'Ticker', 'Company', 'CEO', 'Total Compensation ($)', 'Comp Percentile', 'CEO Comp YoY %', 'Sector', 'Pay Ratio', 'Median Worker Pay ($)',
                'CEO Salary ($)', 'CEO Stock Awards ($)', 'CEO Option Awards ($)', 'CEO Bonus ($)',
                'CEO Non-Equity Incentive ($)', 'CEO Pension/NQDC ($)', 'CEO All Other ($)',
                'CEO Salary %', 'CEO Stock %', 'CEO Options %', 'CEO Bonus %', 'CEO Incentive %', 'CEO Pension %', 'CEO Other %'];
            var rows = filtered.map(function(c, i) {
                var yoyVal = c._ceoYoY ? (c._ceoYoY.pct >= 0 ? '+' : '') + c._ceoYoY.pct.toFixed(1) + '%' : '';
                // Find CEO executive record for composition data
                var ceoExec = null;
                if (c.executives && c.executives.length > 0) {
                    var latestYear = 0;
                    c.executives.forEach(function(e) { if (e.year > latestYear) latestYear = e.year; });
                    var latestExecs = c.executives.filter(function(e) { return e.year === latestYear; });
                    // CEO by title match
                    ceoExec = latestExecs.find(function(e) {
                        return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
                    });
                    // Fallback: highest total
                    if (!ceoExec && latestExecs.length > 0) {
                        ceoExec = latestExecs.reduce(function(a, b) { return (a.total || 0) > (b.total || 0) ? a : b; });
                    }
                }
                var sal = ceoExec ? (ceoExec.salary || 0) : '';
                var stk = ceoExec ? (ceoExec.stock_awards || 0) : '';
                var opt = ceoExec ? (ceoExec.option_awards || 0) : '';
                var bon = ceoExec ? (ceoExec.bonus || 0) : '';
                var inc = ceoExec ? (ceoExec.non_equity_incentive || 0) : '';
                var pen = ceoExec ? (ceoExec.pension_nqdc || ceoExec.pension_change || 0) : '';
                var oth = ceoExec ? (ceoExec.all_other || 0) : '';
                var tot = ceoExec ? (ceoExec.total || 0) : 0;
                // Percentages
                var salP = tot > 0 && ceoExec ? ((sal / tot) * 100).toFixed(1) + '%' : '';
                var stkP = tot > 0 && ceoExec ? ((stk / tot) * 100).toFixed(1) + '%' : '';
                var optP = tot > 0 && ceoExec ? ((opt / tot) * 100).toFixed(1) + '%' : '';
                var bonP = tot > 0 && ceoExec ? ((bon / tot) * 100).toFixed(1) + '%' : '';
                var incP = tot > 0 && ceoExec ? ((inc / tot) * 100).toFixed(1) + '%' : '';
                var penP = tot > 0 && ceoExec ? ((pen / tot) * 100).toFixed(1) + '%' : '';
                var othP = tot > 0 && ceoExec ? ((oth / tot) * 100).toFixed(1) + '%' : '';
                return [
                    i + 1,
                    csvEscape(c.ticker),
                    csvEscape(c.company_name),
                    csvEscape(c.ceo_name),
                    c.total_compensation || '',
                    c._compPercentile != null ? c._compPercentile : '',
                    csvEscape(yoyVal),
                    csvEscape(c.sector || ''),
                    c.pay_ratio || '',
                    c.median_worker_pay || '',
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

            // CSV header — expanded with NEO fields
            var headers = [
                'Rank', 'Ticker', 'Company', 'CEO', 'CEO Total Comp ($)',
                'Sector', 'Pay Ratio', 'Median Worker Pay ($)',
                'Exec Name', 'Exec Title', 'Salary ($)', 'Bonus ($)', 'Stock Awards ($)',
                'Option Awards ($)', 'Non-Equity Incentive ($)', 'Pension/NQDC ($)', 'All Other Comp ($)',
                'Exec Total ($)', 'Fiscal Year', 'Filing Date', 'Filing URL'
            ];

            var rows = [];
            filtered.forEach(function(c, i) {
                var rank = i + 1;
                var baseFields = [
                    rank,
                    csvEscape(c.ticker),
                    csvEscape(c.company_name),
                    csvEscape(c.ceo_name),
                    c.total_compensation || '',
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

    function renderComparisonChart(container, selected, rankMap) {
        container.innerHTML = '';
        if (selected.length < 2) return;

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
                label: 'Total Compensation',
                key: 'total_compensation',
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
            }
        ];

        var totalH = metrics.length * (n * (barH + 4) + 28 + groupGap) - groupGap + 16;
        // Reserve extra space for 4th group (composition) — adjusted dynamically later if rendered
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
            var vals = selected.map(function(c) { return c[metric.key]; }).filter(function(v) { return v != null && v > 0; });
            var maxVal = vals.length > 0 ? Math.max.apply(null, vals) : 1;
            var minVal = vals.length > 0 ? Math.min.apply(null, vals) : 0;

            // Determine best/worst in comparison set for context
            var bestVal = metric.higherBetter ? maxVal : minVal;
            var bestTicker = '';
            selected.forEach(function(c) {
                var v = c[metric.key];
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
                var val = c[metric.key];
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
                                selected.forEach(function(sc) { if (sc[metric.key] === bestInComparison) bestRatioTicker = sc.ticker; });
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

        // Get CEO breakdown for each company
        var compBreakdowns = selected.map(function(c) {
            if (!c.executives || c.executives.length === 0) return null;
            var allYears = [];
            c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
            allYears.sort(function(a, b) { return b - a; });
            var latestExecs = c.executives.filter(function(e) { return e.year === allYears[0]; });
            var ceo = latestExecs.find(function(e) {
                return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
            });
            if (!ceo) ceo = latestExecs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
            if (!ceo) return null;
            var segs = [];
            var segTotal = 0;
            compCompKeys.forEach(function(kd) {
                var val = ceo[kd.key] || 0;
                if (val > 0) {
                    segs.push({ label: kd.label, value: val, color: compCompColors[kd.label] });
                    segTotal += val;
                }
            });
            if (segs.length === 0 || segTotal === 0) return null;
            segs.forEach(function(s) { s.pct = s.value / segTotal * 100; });
            return { segs: segs, total: segTotal, ceoName: ceo.name || c.ceo_name, year: allYears[0] };
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
                .text('Pay Composition');

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

        // ARIA announcement for comparison
        announce('Comparing ' + compareSet.length + ' companies: ' + compareSet.join(', '));

        // Grid columns based on count
        grid.className = 'comparison-grid cols-' + Math.min(compareSet.length, 4);

        // Get company data for each ticker
        var selected = compareSet.map(function(ticker) {
            return companies.find(function(c) { return c.ticker === ticker; });
        }).filter(Boolean);

        // Pre-compute ranks
        var sorted = companies.slice().sort(function(a, b) { return b.total_compensation - a.total_compensation; });
        var rankMap = {};
        sorted.forEach(function(c, i) { rankMap[c.ticker] = i + 1; });

        // Pre-compute sector ranks
        var sectorRankMap = {};
        selected.forEach(function(c) {
            if (sectorRankMap[c.sector]) return;
            var peers = companies.filter(function(x) { return x.sector === c.sector; })
                .sort(function(a, b) { return b.total_compensation - a.total_compensation; });
            sectorRankMap[c.sector] = {};
            peers.forEach(function(p, i) { sectorRankMap[c.sector][p.ticker] = { rank: i + 1, total: peers.length }; });
        });

        // Find max/min for relative bars
        var maxComp = Math.max.apply(null, selected.map(function(c) { return c.total_compensation || 0; }));
        var maxRatio = Math.max.apply(null, selected.map(function(c) { return c.pay_ratio || 0; }));
        var maxWorker = Math.max.apply(null, selected.map(function(c) { return c.median_worker_pay || 0; }));

        // Determine best/worst for highlighting
        var compValues = selected.map(function(c) { return c.total_compensation || 0; });
        var ratioValues = selected.filter(function(c) { return c.pay_ratio != null; }).map(function(c) { return c.pay_ratio; });
        var workerValues = selected.filter(function(c) { return c.median_worker_pay != null; }).map(function(c) { return c.median_worker_pay; });

        // === Comparison Summary Chart (SVG) ===
        var chartContainer = document.getElementById('comparison-chart');
        if (!chartContainer) {
            chartContainer = document.createElement('div');
            chartContainer.id = 'comparison-chart';
            chartContainer.className = 'comparison-chart-container';
            grid.parentNode.insertBefore(chartContainer, grid);
        }
        renderComparisonChart(chartContainer, selected, rankMap);

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

            // Comp bar width
            var compPct = maxComp > 0 ? (c.total_compensation / maxComp * 100) : 0;
            var compClass = c.total_compensation === Math.max.apply(null, compValues) ? ' best' : '';

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

            var html = '<div class="comparison-card-rank">#' + rank + ' / 500';
            // Percentile badge alongside rank
            if (c._compPercentile != null) {
                var _cpLabel = getPercentileLabel(c._compPercentile);
                var _cpClass = getPercentileClass(c._compPercentile);
                html += ' <span class="pctile-badge ' + _cpClass + '" style="font-size:0.6rem;vertical-align:middle;margin-left:6px" title="Compensation percentile: ' + c._compPercentile + ' of 100">' + _cpLabel + '</span>';
            }
            html += '</div>';
            html += '<div class="comparison-card-ticker">' + c.ticker + '</div>';
            html += '<div class="comparison-card-company">' + c.company_name + '</div>';
            html += '<div class="comparison-card-ceo">' + c.ceo_name + '</div>';

            // Total Compensation
            html += '<div class="comparison-row"><span class="comparison-row-label">Total Comp</span><span class="comparison-row-value' + compClass + '">' + formatCurrency(c.total_compensation) + '</span></div>';
            html += '<div class="comparison-row-bar"><div class="comparison-row-bar-fill" style="width:' + compPct + '%;background:var(--accent)"></div></div>';

            // CEO Comp YoY change badge (from multi-year NEO data)
            if (c.executives && c.executives.length > 0) {
                var yoyAllYears = [];
                c.executives.forEach(function(e) { if (yoyAllYears.indexOf(e.year) < 0) yoyAllYears.push(e.year); });
                yoyAllYears.sort(function(a, b) { return b - a; });
                if (yoyAllYears.length >= 2) {
                    var yoyYr1 = yoyAllYears[0];
                    var yoyYr2 = yoyAllYears[1];
                    var yoyExecs1 = c.executives.filter(function(e) { return e.year === yoyYr1; });
                    var yoyExecs2 = c.executives.filter(function(e) { return e.year === yoyYr2; });
                    // Find CEO in each year
                    var yoyCeo1 = yoyExecs1.find(function(e) {
                        return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
                    });
                    if (!yoyCeo1 && yoyExecs1.length > 0) {
                        yoyCeo1 = yoyExecs1.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
                    }
                    var yoyCeo2 = yoyExecs2.find(function(e) {
                        return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
                    });
                    if (!yoyCeo2 && yoyExecs2.length > 0) {
                        yoyCeo2 = yoyExecs2.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
                    }
                    if (yoyCeo1 && yoyCeo2 && yoyCeo1.total > 0 && yoyCeo2.total > 0) {
                        var yoyPctChange = ((yoyCeo1.total - yoyCeo2.total) / yoyCeo2.total * 100);
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

            // Sector Rank
            html += '<div class="comparison-row"><span class="comparison-row-label">Sector</span><span class="comparison-row-value">' + (c.sector || '—') + '</span></div>';
            html += '<div class="comparison-row"><span class="comparison-row-label">Sector Rank</span><span class="comparison-row-value">#' + sRank.rank + ' of ' + sRank.total + '</span></div>';

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
        var sorted = companies.slice().sort(function(a, b) { return b.total_compensation - a.total_compensation; });
        var rankMap = {};
        sorted.forEach(function(c, i) { rankMap[c.ticker] = i + 1; });
        renderComparisonChart(chartEl, selected, rankMap);
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
            if (activeSector || searchTerm || window._activeRatioBucket || window._activeDistFilter) {
                activeSector = null;
                searchTerm = '';
                currentPage = 1;
                document.getElementById('table-search').value = '';
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
