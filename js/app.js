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

    document.getElementById('table-footer').textContent = 'Showing ' + filtered.length + ' of ' + companies.length + ' companies';
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

(async function init() {
    var data = await loadData();
    var companies = data.comp.companies;

    populateMetrics(data.comp, data.trends);
    buildSectorChips(companies);
    renderTable(companies);
    setupSorting(companies);
    setupSearch(companies);

    if (typeof initNetwork === 'function') {
        initNetwork(data.peer);
    }
    if (typeof initCharts === 'function') {
        initCharts(companies, data.trends, data.comp);
    }
})();
