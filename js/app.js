/* === S&P 500 Executive Compensation Tracker — Main App === */

let compData = null;
let trendsData = null;
let peerData = null;
let currentSort = { key: 'total_compensation', dir: 'desc' };
let activeSector = null;
let searchTerm = '';

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
        document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
        allChip.classList.add('active');
        renderTable(companies);
    });
    container.appendChild(allChip);

    sectors.forEach(function(s) {
        var chip = document.createElement('button');
        chip.className = 'chip';
        chip.textContent = s;
        chip.addEventListener('click', function() {
            activeSector = s;
            document.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
            chip.classList.add('active');
            renderTable(companies);
        });
        container.appendChild(chip);
    });
}

function renderTable(companies) {
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

    var tbody = document.getElementById('comp-tbody');
    tbody.innerHTML = '';

    filtered.forEach(function(c, i) {
        var tr = document.createElement('tr');
        var ratioClass = c.pay_ratio > 2000 ? 'ratio-high' : c.pay_ratio > 500 ? 'ratio-mid' : 'ratio-low';
        var ratioCell = c.pay_ratio ? '<span class="' + ratioClass + '">' + formatRatio(c.pay_ratio) + '</span>' : '\u2014';
        var workerCell = c.median_worker_pay ? formatCompact(c.median_worker_pay) : '\u2014';
        tr.innerHTML = '<td>' + (i + 1) + '</td>' +
            '<td><span class="ticker">' + c.ticker + '</span></td>' +
            '<td><span class="company">' + c.company_name + '</span></td>' +
            '<td>' + c.ceo_name + '</td>' +
            '<td><span class="comp-value">' + formatCurrency(c.total_compensation) + '</span></td>' +
            '<td>' + (c.sector || '\u2014') + '</td>' +
            '<td>' + ratioCell + '</td>' +
            '<td>' + workerCell + '</td>';
        tbody.appendChild(tr);
    });

    document.getElementById('table-footer').textContent = 'Showing ' + filtered.length + ' of ' + companies.length + ' companies · Click any row for details';
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

(async function init() {
    var data = await loadData();
    var companies = data.comp.companies;

    populateMetrics(data.comp, data.trends);
    buildSectorChips(companies);
    renderTable(companies);
    setupSorting(companies);
    setupSearch(companies);
    setupDetailPanel(companies);

    if (typeof initNetwork === 'function') {
        initNetwork(data.peer);
    }
    if (typeof initCharts === 'function') {
        initCharts(companies, data.trends, data.comp);
    }
})();
