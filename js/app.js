/* === S&P 500 Executive Compensation Tracker — Main App === */

let compData = null;
let trendsData = null;
let peerData = null;
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
        detail: over50M.length + ' CEOs received more than $50 million in total compensation — led by ' + sorted[0].ceo_name + ' (' + sorted[0].ticker + ') at ' + formatCurrency(sorted[0].total_compensation) + '.'
    });

    // 3. Extreme Pay Ratios (>1000:1)
    var extremeRatio = companies.filter(function(c) { return c.pay_ratio != null && c.pay_ratio > 1000; });
    var maxRatioComp = companies.filter(function(c) { return c.pay_ratio != null; }).sort(function(a, b) { return b.pay_ratio - a.pay_ratio; })[0];
    insights.push({
        icon: '⚖️',
        label: 'Extreme Ratios',
        value: extremeRatio.length + ' above 1,000:1',
        detail: extremeRatio.length + ' companies have CEO-to-worker pay ratios exceeding 1,000:1. ' + (maxRatioComp ? maxRatioComp.ticker + ' leads at ' + maxRatioComp.pay_ratio.toLocaleString() + ':1.' : '')
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
            detail: zeroNames + ' reported $0 total compensation — typically founder-CEOs with large equity stakes who forgo traditional pay.'
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
            detail: 'From ' + formatCurrency(minPay.total_compensation) + ' (' + minPay.ticker + ') to ' + formatCurrency(maxPay.total_compensation) + ' (' + maxPay.ticker + ') — a ' + span.toLocaleString() + '-fold range across the S&P 500.'
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
        html += '</div>';
        card.innerHTML = html;
        if (ins.action) {
            card.style.cursor = 'pointer';
            card.addEventListener('click', ins.action);
        }
        grid.appendChild(card);
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

function renderTable(companies) {
    computeOutliers(companies);

    var filtered = companies.slice();

    if (activeSector) {
        filtered = filtered.filter(function(c) { return c.sector === activeSector; });
    }
    if (searchTerm) {
        var q = searchTerm.toLowerCase();
        filtered = filtered.filter(function(c) {
            return (c.ticker || '').toLowerCase().indexOf(q) >= 0 ||
                (c.company_name || '').toLowerCase().indexOf(q) >= 0 ||
                (c.ceo_name || '').toLowerCase().indexOf(q) >= 0 ||
                (c.sector || '').toLowerCase().indexOf(q) >= 0;
        });
    }
    if (window._activeRatioBucket) {
        var rb = window._activeRatioBucket;
        filtered = filtered.filter(function(c) {
            return c.pay_ratio != null && c.pay_ratio >= rb.min && c.pay_ratio < rb.max;
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

    // Pagination
    var totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;
    var startIdx = (currentPage - 1) * PAGE_SIZE;
    var pageItems = filtered.slice(startIdx, startIdx + PAGE_SIZE);

    var tbody = document.getElementById('comp-tbody');
    tbody.innerHTML = '';

    pageItems.forEach(function(c, i) {
        var globalIdx = startIdx + i;
        var tr = document.createElement('tr');

        // Compensation value with optional top-10 badge
        var compHtml = '<span class="comp-value">' + formatCurrency(c.total_compensation) + '</span>';
        if (_outlierTop10[c.ticker]) {
            compHtml += ' <span class="outlier-badge top-comp" title="Top 10 highest paid CEO in S&amp;P 500">#' + _outlierTop10[c.ticker] + '</span>';
        }

        // Pay ratio with color class + optional extreme badge
        var ratioClass = c.pay_ratio > 2000 ? 'ratio-high' : c.pay_ratio > 500 ? 'ratio-mid' : 'ratio-low';
        var ratioHtml = '\u2014';
        if (c.pay_ratio) {
            ratioHtml = '<span class="' + ratioClass + '">' + formatRatio(c.pay_ratio) + '</span>';
            if (c.pay_ratio > 2000) {
                ratioHtml += ' <span class="outlier-badge extreme-ratio" title="Extreme pay ratio: CEO earns ' + c.pay_ratio.toLocaleString() + 'x the median worker">!</span>';
            } else if (c.pay_ratio > 1000) {
                ratioHtml += ' <span class="outlier-badge high-ratio" title="High pay ratio: CEO earns ' + c.pay_ratio.toLocaleString() + 'x the median worker">!</span>';
            } else if (_outlierLowRatio[c.ticker]) {
                ratioHtml += ' <span class="outlier-badge low-ratio" title="Most equitable: bottom 5 pay ratio in S&amp;P 500">✓</span>';
            }
        }

        var workerCell = c.median_worker_pay ? formatCompact(c.median_worker_pay) : '\u2014';
        var isCompared = window._compareSet && window._compareSet.indexOf(c.ticker) >= 0;
        var compareBtnHtml = '<button class="compare-btn' + (isCompared ? ' selected' : '') + '" data-ticker="' + c.ticker + '" title="' + (isCompared ? 'Remove from comparison' : 'Add to comparison') + '">' + (isCompared ? '✓' : '+') + '</button>';

        tr.innerHTML = '<td>' + (globalIdx + 1) + ' ' + compareBtnHtml + '</td>' +
            '<td><span class="ticker">' + c.ticker + '</span></td>' +
            '<td><span class="company">' + c.company_name + '</span></td>' +
            '<td>' + c.ceo_name + '</td>' +
            '<td>' + compHtml + '</td>' +
            '<td>' + (c.sector || '\u2014') + '</td>' +
            '<td>' + ratioHtml + '</td>' +
            '<td>' + workerCell + '</td>';

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
        var headerHeight = document.querySelector('header') ? document.querySelector('header').offsetHeight : 0;
        var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 8;
        window.scrollTo({ top: sectionTop, behavior: 'smooth' });
    }
}

function setupSorting(companies) {
    document.querySelectorAll('th.sortable').forEach(function(th) {
        th.addEventListener('click', function() {
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
            });
            th.classList.add(currentSort.dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
            renderTable(companies);
        });
    });
}

function setupSearch(companies) {
    document.getElementById('table-search').addEventListener('input', function(e) {
        searchTerm = e.target.value;
        currentPage = 1;
        renderTable(companies);
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

        if (wasOpen) return; // toggle off

        row.classList.add('selected');
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

        // Build HTML
        var html = '<td colspan="8"><div class="detail-panel">';
        html += '<div class="detail-header">' + company.company_name + ' <span class="detail-ticker">(' + ticker + ')</span></div>';
        html += '<div class="detail-stats">';

        html += '<div class="detail-stat"><div class="detail-stat-label">S&P 500 Rank</div><div class="detail-stat-value">#' + overallRank + '</div><div class="detail-stat-sub">Top ' + topPct + '%</div></div>';
        html += '<div class="detail-stat"><div class="detail-stat-label">Sector Rank</div><div class="detail-stat-value">#' + sectorRank + ' of ' + sectorPeers.length + '</div><div class="detail-stat-sub">' + (company.sector || '') + '</div></div>';

        if (vsMedianPct !== null) {
            var sign = parseInt(vsMedianPct) >= 0 ? '+' : '';
            var cls = parseInt(vsMedianPct) >= 0 ? 'positive' : 'negative';
            html += '<div class="detail-stat"><div class="detail-stat-label">vs Sector Median</div><div class="detail-stat-value ' + cls + '">' + sign + vsMedianPct + '%</div><div class="detail-stat-sub">Median: ' + formatCurrency(sectorMedianPay) + '</div></div>';
        }

        if (ratioText) {
            html += '<div class="detail-stat"><div class="detail-stat-label">Pay Ratio Rank</div><div class="detail-stat-value">' + ratioText + '</div><div class="detail-stat-sub">' + formatRatio(company.pay_ratio) + '</div></div>';
        }

        if (peerInfo) {
            html += '<div class="detail-stat"><div class="detail-stat-label">Peer Network</div><div class="detail-stat-value">' + peerInfo.selectedBy.length + ' in · ' + peerInfo.selects.length + ' out</div><div class="detail-stat-sub">Inbound / outbound</div></div>';
        }

        html += '</div>'; // detail-stats

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
                html += peerInfo.selectedBy.slice(0, 20).map(function(t) { return '<span class="detail-peer-tag">' + t + '</span>'; }).join('');
                if (peerInfo.selectedBy.length > 20) html += '<span class="detail-peer-more">+' + (peerInfo.selectedBy.length - 20) + ' more</span>';
                html += '</div></div>';
            }
            if (peerInfo.selects.length > 0) {
                html += '<div class="detail-peer-group"><span class="detail-peer-label">Benchmarks against:</span>';
                html += '<div class="detail-peer-tags">';
                html += peerInfo.selects.slice(0, 20).map(function(t) { return '<span class="detail-peer-tag">' + t + '</span>'; }).join('');
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

    // Page (apply after filters so pagination is computed correctly)
    if (state.page) {
        currentPage = parseInt(state.page, 10) || 1;
    }

    renderTable(companies);
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
            tHtml += '<tr class="skeleton-table-row-tr"><td colspan="8"><div class="skeleton-table-row">' +
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

    // Remove metric skeletons before populating with real data
    hideMetricSkeletons();

    populateMetrics(data.comp, data.trends);
    populateInsights(data.comp, data.trends);
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

        // Update sector chip active states
        document.querySelectorAll('.chip').forEach(function(chip) {
            chip.classList.remove('active');
            if (!sectorName && chip.textContent === 'All') chip.classList.add('active');
            else if (chip.textContent === sectorName) chip.classList.add('active');
        });

        renderTable(companies);

        // Highlight active bar in sector chart
        if (window.highlightSectorBar) window.highlightSectorBar(sectorName);

        // Clear ratio bucket highlight (sector filter clears ratio)
        if (window.highlightRatioBucket) window.highlightRatioBucket(null);

        // Scroll to the table section
        var section = document.getElementById('compensation-table-section');
        if (section) {
            var headerHeight = document.querySelector('header') ? document.querySelector('header').offsetHeight : 0;
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: 'smooth' });
        }
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
            var headerHeight = document.querySelector('header') ? document.querySelector('header').offsetHeight : 0;
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: 'smooth' });
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
            var headerHeight = document.querySelector('header') ? document.querySelector('header').offsetHeight : 0;
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: 'smooth' });
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
        window.addEventListener('resize', function() { setTimeout(updateScrollIndicator, 300); });

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
                    return (c.ticker || '').toLowerCase().indexOf(q) >= 0 ||
                        (c.company_name || '').toLowerCase().indexOf(q) >= 0 ||
                        (c.ceo_name || '').toLowerCase().indexOf(q) >= 0 ||
                        (c.sector || '').toLowerCase().indexOf(q) >= 0;
                });
            }
            if (window._activeRatioBucket) {
                var rb = window._activeRatioBucket;
                filtered = filtered.filter(function(c) {
                    return c.pay_ratio != null && c.pay_ratio >= rb.min && c.pay_ratio < rb.max;
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
            var headers = ['Rank', 'Ticker', 'Company', 'CEO', 'Total Compensation ($)', 'Sector', 'Pay Ratio', 'Median Worker Pay ($)'];
            var rows = filtered.map(function(c, i) {
                return [
                    i + 1,
                    csvEscape(c.ticker),
                    csvEscape(c.company_name),
                    csvEscape(c.ceo_name),
                    c.total_compensation || '',
                    csvEscape(c.sector || ''),
                    c.pay_ratio || '',
                    c.median_worker_pay || ''
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
            a.download = fname + '.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
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
    }

    function showComparison() {
        if (compareSet.length < 2) return;
        var section = document.getElementById('comparison-section');
        var grid = document.getElementById('comparison-grid');
        section.classList.add('visible');

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

            var html = '<div class="comparison-card-rank">#' + rank + ' / 500</div>';
            html += '<div class="comparison-card-ticker">' + c.ticker + '</div>';
            html += '<div class="comparison-card-company">' + c.company_name + '</div>';
            html += '<div class="comparison-card-ceo">' + c.ceo_name + '</div>';

            // Total Compensation
            html += '<div class="comparison-row"><span class="comparison-row-label">Total Comp</span><span class="comparison-row-value' + compClass + '">' + formatCurrency(c.total_compensation) + '</span></div>';
            html += '<div class="comparison-row-bar"><div class="comparison-row-bar-fill" style="width:' + compPct + '%;background:var(--accent)"></div></div>';

            // Sector Rank
            html += '<div class="comparison-row"><span class="comparison-row-label">Sector</span><span class="comparison-row-value">' + (c.sector || '—') + '</span></div>';
            html += '<div class="comparison-row"><span class="comparison-row-label">Sector Rank</span><span class="comparison-row-value">#' + sRank.rank + ' of ' + sRank.total + '</span></div>';

            // Pay Ratio
            html += '<div class="comparison-row"><span class="comparison-row-label">Pay Ratio</span><span class="comparison-row-value' + ratioClass + '">' + (c.pay_ratio ? formatRatio(c.pay_ratio) : '—') + '</span></div>';
            if (c.pay_ratio) {
                html += '<div class="comparison-row-bar"><div class="comparison-row-bar-fill" style="width:' + ratioPct + '%;background:' + (c.pay_ratio > 1000 ? 'var(--negative)' : c.pay_ratio > 500 ? 'var(--warning)' : 'var(--positive)') + '"></div></div>';
            }

            // Median Worker Pay
            html += '<div class="comparison-row"><span class="comparison-row-label">Worker Pay</span><span class="comparison-row-value' + workerClass + '">' + (c.median_worker_pay ? formatCompact(c.median_worker_pay) : '—') + '</span></div>';
            if (c.median_worker_pay) {
                html += '<div class="comparison-row-bar"><div class="comparison-row-bar-fill" style="width:' + workerPct + '%;background:var(--positive)"></div></div>';
            }

            // Peer Network
            html += '<div class="comparison-row"><span class="comparison-row-label">Peers</span><span class="comparison-row-value">' + peerIn + ' in · ' + peerOut + ' out</span></div>';

            card.innerHTML = html;
            grid.appendChild(card);
        });

        // Scroll to comparison section
        setTimeout(function() {
            var headerHeight = document.querySelector('header') ? document.querySelector('header').offsetHeight : 0;
            var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
            window.scrollTo({ top: sectionTop, behavior: 'smooth' });
        }, 50);
    }

    // Wire up tray buttons
    document.getElementById('compare-go-btn').addEventListener('click', showComparison);
    document.getElementById('compare-clear-btn').addEventListener('click', clearCompare);
    document.getElementById('comparison-close-btn').addEventListener('click', function() {
        document.getElementById('comparison-section').classList.remove('visible');
    });

    // Expose for use in renderTable
    window._compareSet = compareSet;
    window._toggleCompare = toggleCompare;
    window._updateCompareButtons = updateCompareButtons;

    // Listen for browser back/forward
    window.addEventListener('hashchange', function() {
        // Reset to defaults first
        currentSort = { key: 'total_compensation', dir: 'desc' };
        activeSector = null;
        searchTerm = '';
        currentPage = 1;
        window._activeRatioBucket = null;
        document.getElementById('table-search').value = '';
        document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
        var allChip = document.querySelector('.chip');
        if (allChip && allChip.textContent === 'All') allChip.classList.add('active');
        var rc = document.getElementById('ratio-filter-chip');
        if (rc) rc.remove();
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
    });
})();
