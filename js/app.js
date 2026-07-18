/* ===== Main Application ===== */

(async function () {
  // Load data
  const [compRes, peerRes, trendsRes] = await Promise.all([
    fetch('data/compensation.json'),
    fetch('data/peer-network.json'),
    fetch('data/trends.json')
  ]);

  const compData = await compRes.json();
  const peerData = await peerRes.json();
  const trendsData = await trendsRes.json();

  const companies = compData.companies;

  // ---- Key Metrics ----
  computeMetrics(companies, compData.metadata);

  // ---- Network Graph ----
  initNetwork(peerData);

  // ---- Compensation Table ----
  initTable(companies);

  // ---- Charts ----
  initSectorChart(companies, trendsData);
  initPayRatioChart(companies);
  initTrendChart(trendsData);

  // ---- Top 10 ----
  initTop10(companies);

  // ---- Resize ----
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      // Re-render network on resize
      initNetwork(peerData);
      // Charts: clearing and re-rendering
      const sc = document.getElementById('sector-chart');
      const pr = document.getElementById('payratio-chart');
      const tc = document.getElementById('trend-chart');
      if (sc) { sc.innerHTML = ''; initSectorChart(companies, trendsData); }
      if (pr) { pr.innerHTML = ''; initPayRatioChart(companies); }
      if (tc) { tc.innerHTML = ''; initTrendChart(trendsData); }
    }, 300);
  });

})();

/* ---- Compute Key Metrics ---- */
function computeMetrics(companies, metadata) {
  const comps = companies.map(c => c.total_compensation).sort((a, b) => a - b);
  const n = comps.length;
  const median = n % 2 ? comps[Math.floor(n / 2)] : (comps[Math.floor(n / 2) - 1] + comps[Math.floor(n / 2)]) / 2;
  const total = comps.reduce((s, v) => s + v, 0);

  const ratios = companies.filter(c => c.pay_ratio).map(c => c.pay_ratio).sort((a, b) => a - b);
  const avgRatio = ratios.length ? Math.round(ratios.reduce((s, v) => s + v, 0) / ratios.length) : 0;

  // Use S&P 500 median from metadata if available, else our computed median
  const sp500Median = metadata.aggregate_stats.s_and_p_500_median_ceo_pay_2024 || median;

  document.getElementById('metric-median-pay').textContent = formatCompact(sp500Median);
  document.getElementById('metric-avg-ratio').textContent = avgRatio ? avgRatio.toLocaleString() + ':1' : '192:1';
  document.getElementById('metric-total-comp').textContent = formatCurrency(total);
  document.getElementById('metric-companies').textContent = n.toString();
  document.getElementById('metric-yoy').textContent = metadata.aggregate_stats.s_and_p_500_yoy_change_2024 || '+9.7%';
  document.getElementById('metric-stock-pct').textContent = metadata.aggregate_stats.stock_awards_pct_of_total_2024 || '71.6%';
}

/* ---- Table ---- */
let currentSort = { col: 'total_compensation', dir: 'desc' };
let currentFilter = 'All';
let currentSearch = '';
let allCompanies = [];

function initTable(companies) {
  allCompanies = companies;

  // Build sector filter chips
  const sectors = ['All', ...new Set(companies.map(c => c.sector || 'Other').filter(Boolean))].sort();
  const chipsEl = document.getElementById('filter-chips');
  chipsEl.innerHTML = sectors.map(s =>
    `<button class="filter-chip ${s === 'All' ? 'active' : ''}" data-sector="${s}">${s}</button>`
  ).join('');

  chipsEl.addEventListener('click', e => {
    const chip = e.target.closest('.filter-chip');
    if (!chip) return;
    currentFilter = chip.dataset.sector;
    chipsEl.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    renderTable();
  });

  // Search
  const searchEl = document.getElementById('table-search');
  searchEl.addEventListener('input', e => {
    currentSearch = e.target.value.toLowerCase();
    renderTable();
  });

  // Sort headers
  document.querySelectorAll('[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.sort;
      if (currentSort.col === col) {
        currentSort.dir = currentSort.dir === 'desc' ? 'asc' : 'desc';
      } else {
        currentSort.col = col;
        currentSort.dir = 'desc';
      }
      renderTable();
    });
  });

  renderTable();
}

function renderTable() {
  let filtered = allCompanies.slice();

  // Filter by sector
  if (currentFilter !== 'All') {
    filtered = filtered.filter(c => (c.sector || 'Other') === currentFilter);
  }

  // Search
  if (currentSearch) {
    filtered = filtered.filter(c =>
      (c.company_name || '').toLowerCase().includes(currentSearch) ||
      (c.ceo_name || '').toLowerCase().includes(currentSearch) ||
      (c.ticker || '').toLowerCase().includes(currentSearch)
    );
  }

  // Sort
  filtered.sort((a, b) => {
    let va = a[currentSort.col];
    let vb = b[currentSort.col];
    // Handle strings
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    // Handle undefined
    if (va == null) va = currentSort.dir === 'desc' ? -Infinity : Infinity;
    if (vb == null) vb = currentSort.dir === 'desc' ? -Infinity : Infinity;
    if (va < vb) return currentSort.dir === 'asc' ? -1 : 1;
    if (va > vb) return currentSort.dir === 'asc' ? 1 : -1;
    return 0;
  });

  // Update sort indicators
  document.querySelectorAll('[data-sort]').forEach(th => {
    th.classList.toggle('sorted', th.dataset.sort === currentSort.col);
    const arrow = th.querySelector('.sort-arrow');
    if (arrow && th.dataset.sort === currentSort.col) {
      arrow.textContent = currentSort.dir === 'desc' ? '▼' : '▲';
    }
  });

  const tbody = document.getElementById('comp-tbody');
  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No companies match your filters</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(c => {
    const totalComp = c.total_compensation || 0;
    const salary = c.salary || 0;
    const stock = c.stock_awards || 0;
    const hasMiniBar = salary > 0 || stock > 0;
    const otherComp = hasMiniBar ? Math.max(0, totalComp - salary - stock) : 0;
    const salaryPct = hasMiniBar ? (salary / totalComp * 100) : 0;
    const stockPct = hasMiniBar ? (stock / totalComp * 100) : 0;
    const otherPct = hasMiniBar ? (otherComp / totalComp * 100) : 0;

    const sector = c.sector || 'Other';
    const sectorColor = getSectorColor(sector);

    return `<tr>
      <td class="col-ticker">${c.ticker || '—'}</td>
      <td class="col-company" title="${c.company_name}">${c.company_name}</td>
      <td>${c.ceo_name}</td>
      <td class="col-right">${formatCompact(totalComp)}</td>
      <td class="col-right">${c.salary ? formatCompact(c.salary) : '—'}</td>
      <td class="col-right">${c.pay_ratio ? c.pay_ratio.toLocaleString() + ':1' : '—'}</td>
      <td class="col-sector"><span class="sector-badge" style="color:${sectorColor};border:1px solid ${sectorColor}33">${sector}</span></td>
    </tr>`;
  }).join('');
}

/* ---- Top 10 ---- */
function initTop10(companies) {
  const sorted = [...companies].sort((a, b) => b.total_compensation - a.total_compensation);
  const top10 = sorted.slice(0, 10);
  const listEl = document.getElementById('top10-list');

  listEl.innerHTML = top10.map((c, i) => {
    const sector = c.sector || 'Other';
    const color = getSectorColor(sector);
    const initial = (c.ceo_name || '?')[0].toUpperCase();
    const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';

    return `<div class="top10-card">
      <div class="top10-rank ${rankClass}">${i + 1}</div>
      <div class="top10-avatar" style="background:${color}">${initial}</div>
      <div class="top10-info">
        <div class="top10-name">${c.ceo_name}</div>
        <div class="top10-company">${c.company_name} (${c.ticker || ''})</div>
      </div>
      <div>
        <div class="top10-comp">${formatCompact(c.total_compensation)}</div>
        ${c.pay_ratio ? `<div class="top10-ratio">${c.pay_ratio.toLocaleString()}:1</div>` : ''}
      </div>
    </div>`;
  }).join('');
}
