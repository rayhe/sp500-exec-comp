/* ===== D3 Charts ===== */

function formatCurrency(val) {
  if (val >= 1e9) return '$' + (val / 1e9).toFixed(1) + 'B';
  if (val >= 1e6) return '$' + (val / 1e6).toFixed(1) + 'M';
  if (val >= 1e3) return '$' + (val / 1e3).toFixed(0) + 'K';
  return '$' + val.toFixed(0);
}

function formatCompact(val) {
  if (val >= 1e6) return '$' + (val / 1e6).toFixed(1) + 'M';
  if (val >= 1e3) return '$' + (val / 1e3).toFixed(0) + 'K';
  return '$' + val;
}

/* ---- Sector Bar Chart ---- */
function initSectorChart(companies, trendsData) {
  const container = document.getElementById('sector-chart');
  if (!container) return;

  // Use FY2024 sector data from trends if available, else compute from company data
  let sectorMedians;
  if (trendsData && trendsData.median_pay_by_sector_sp500_fy2024 && trendsData.median_pay_by_sector_sp500_fy2024.data) {
    sectorMedians = trendsData.median_pay_by_sector_sp500_fy2024.data
      .map(d => ({ sector: d.sector, median: d.median_pay, count: d.num_ceos || 0 }))
      .sort((a, b) => b.median - a.median);
  } else {
    // Compute from company data
    const bySector = {};
    companies.forEach(c => {
      const s = c.sector || 'Other';
      if (!bySector[s]) bySector[s] = [];
      bySector[s].push(c.total_compensation);
    });
    sectorMedians = Object.entries(bySector).map(([sector, vals]) => {
      vals.sort((a, b) => a - b);
      const mid = Math.floor(vals.length / 2);
      const median = vals.length % 2 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2;
      return { sector, median, count: vals.length };
    }).sort((a, b) => b.median - a.median);
  }

  const margin = { top: 16, right: 80, bottom: 20, left: 160 };
  const fullWidth = container.clientWidth;
  const barHeight = 32;
  const fullHeight = margin.top + margin.bottom + sectorMedians.length * (barHeight + 8);

  const svgWidth = fullWidth;
  const svgHeight = fullHeight;
  const w = svgWidth - margin.left - margin.right;
  const h = svgHeight - margin.top - margin.bottom;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', svgWidth)
    .attr('height', svgHeight);

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const x = d3.scaleLinear()
    .domain([0, d3.max(sectorMedians, d => d.median) * 1.1])
    .range([0, w]);

  const y = d3.scaleBand()
    .domain(sectorMedians.map(d => d.sector))
    .range([0, h])
    .padding(0.3);

  // Bars
  g.selectAll('rect')
    .data(sectorMedians)
    .join('rect')
    .attr('x', 0)
    .attr('y', d => y(d.sector))
    .attr('width', d => x(d.median))
    .attr('height', y.bandwidth())
    .attr('fill', d => getSectorColor(d.sector) || '#58a6ff')
    .attr('rx', 3)
    .attr('opacity', 0.85);

  // Labels
  g.selectAll('.bar-label')
    .data(sectorMedians)
    .join('text')
    .attr('class', 'bar-label')
    .attr('x', -8)
    .attr('y', d => y(d.sector) + y.bandwidth() / 2)
    .attr('dy', '0.35em')
    .attr('text-anchor', 'end')
    .attr('fill', '#8b949e')
    .attr('font-size', '12px')
    .text(d => d.sector);

  // Value labels
  g.selectAll('.bar-value')
    .data(sectorMedians)
    .join('text')
    .attr('class', 'bar-value')
    .attr('x', d => x(d.median) + 6)
    .attr('y', d => y(d.sector) + y.bandwidth() / 2)
    .attr('dy', '0.35em')
    .attr('fill', '#e6edf3')
    .attr('font-size', '12px')
    .attr('font-family', 'var(--font-mono)')
    .attr('font-weight', '600')
    .text(d => formatCompact(d.median));
}

/* ---- Pay Ratio Distribution ---- */
function initPayRatioChart(companies) {
  const container = document.getElementById('payratio-chart');
  if (!container) return;

  const withRatio = companies.filter(c => c.pay_ratio && c.pay_ratio > 0);
  if (withRatio.length === 0) {
    container.innerHTML = '<div class="empty-state">No pay ratio data available</div>';
    return;
  }

  withRatio.sort((a, b) => a.pay_ratio - b.pay_ratio);

  const margin = { top: 20, right: 24, bottom: 50, left: 60 };
  const fullWidth = container.clientWidth;
  const fullHeight = 360;
  const w = fullWidth - margin.left - margin.right;
  const h = fullHeight - margin.top - margin.bottom;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', fullWidth)
    .attr('height', fullHeight);

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  // Use log scale for better distribution visibility
  const maxRatio = d3.max(withRatio, d => d.pay_ratio);
  const x = d3.scaleLog()
    .domain([10, maxRatio * 1.2])
    .range([0, w])
    .clamp(true);

  const y = d3.scaleLinear()
    .domain([0, withRatio.length - 1])
    .range([h, 0]);

  // Grid lines
  g.append('g')
    .attr('class', 'grid')
    .selectAll('line')
    .data([100, 500, 1000, 5000, 10000])
    .join('line')
    .attr('x1', d => x(d))
    .attr('x2', d => x(d))
    .attr('y1', 0)
    .attr('y2', h)
    .attr('stroke', 'rgba(255,255,255,0.04)')
    .attr('stroke-width', 1);

  // X axis labels
  g.append('g')
    .attr('transform', `translate(0,${h})`)
    .selectAll('text')
    .data([100, 500, 1000, 5000, 10000])
    .join('text')
    .attr('x', d => x(d))
    .attr('y', 20)
    .attr('text-anchor', 'middle')
    .attr('fill', '#6e7681')
    .attr('font-size', '11px')
    .attr('font-family', 'var(--font-mono)')
    .text(d => d.toLocaleString() + ':1');

  // X axis label
  g.append('text')
    .attr('x', w / 2)
    .attr('y', h + 42)
    .attr('text-anchor', 'middle')
    .attr('fill', '#6e7681')
    .attr('font-size', '11px')
    .text('CEO-to-Worker Pay Ratio (log scale)');

  // Median line
  const ratios = withRatio.map(d => d.pay_ratio).sort((a, b) => a - b);
  const medianRatio = ratios[Math.floor(ratios.length / 2)];

  g.append('line')
    .attr('x1', x(medianRatio))
    .attr('x2', x(medianRatio))
    .attr('y1', 0)
    .attr('y2', h)
    .attr('stroke', '#58a6ff')
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', '6,4')
    .attr('opacity', 0.7);

  g.append('text')
    .attr('x', x(medianRatio) + 6)
    .attr('y', 12)
    .attr('fill', '#58a6ff')
    .attr('font-size', '11px')
    .attr('font-weight', '600')
    .text(`Median ${medianRatio.toLocaleString()}:1`);

  // Tooltip div
  const tooltipEl = document.getElementById('chart-tooltip');

  // Dots
  g.selectAll('circle')
    .data(withRatio)
    .join('circle')
    .attr('cx', d => x(d.pay_ratio))
    .attr('cy', (d, i) => y(i))
    .attr('r', 5)
    .attr('fill', d => {
      if (d.pay_ratio > 5000) return '#f85149';
      if (d.pay_ratio > 2000) return '#d29922';
      return '#3fb9b1';
    })
    .attr('stroke', 'rgba(0,0,0,0.3)')
    .attr('stroke-width', 1)
    .attr('opacity', 0.85)
    .attr('cursor', 'pointer')
    .on('mouseover', function (event, d) {
      d3.select(this).attr('r', 7).attr('opacity', 1);
      if (tooltipEl) {
        tooltipEl.innerHTML = `
          <div style="font-weight:700">${d.company_name}</div>
          <div style="color:#8b949e">${d.ceo_name}</div>
          <div style="margin-top:4px">
            <span style="color:#58a6ff;font-weight:700;font-family:var(--font-mono)">${d.pay_ratio.toLocaleString()}:1</span>
            <span style="color:#6e7681;margin-left:8px">Pay Ratio</span>
          </div>
          <div style="color:#6e7681;font-size:11px">Worker median: ${formatCurrency(d.median_worker_pay)}</div>
        `;
        tooltipEl.classList.add('visible');
        tooltipEl.style.left = (event.clientX + 14) + 'px';
        tooltipEl.style.top = (event.clientY - 10) + 'px';
      }
    })
    .on('mousemove', function (event) {
      if (tooltipEl) {
        tooltipEl.style.left = (event.clientX + 14) + 'px';
        tooltipEl.style.top = (event.clientY - 10) + 'px';
      }
    })
    .on('mouseout', function () {
      d3.select(this).attr('r', 5).attr('opacity', 0.85);
      if (tooltipEl) tooltipEl.classList.remove('visible');
    });

  // Labels for outliers
  withRatio.filter(d => d.pay_ratio > 4000).forEach((d, i) => {
    const idx = withRatio.indexOf(d);
    g.append('text')
      .attr('x', x(d.pay_ratio) + 8)
      .attr('y', y(idx) + 4)
      .attr('fill', '#f85149')
      .attr('font-size', '10px')
      .attr('font-weight', '600')
      .text(d.ticker || d.company_name.slice(0, 10));
  });
}

/* ---- Median Pay Trend (small line chart) ---- */
function initTrendChart(trendsData) {
  const container = document.getElementById('trend-chart');
  if (!container) return;

  const data = trendsData.median_ceo_pay_by_year.data;

  const margin = { top: 20, right: 24, bottom: 36, left: 64 };
  const fullWidth = container.clientWidth;
  const fullHeight = 240;
  const w = fullWidth - margin.left - margin.right;
  const h = fullHeight - margin.top - margin.bottom;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', fullWidth)
    .attr('height', fullHeight);

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const x = d3.scaleLinear()
    .domain(d3.extent(data, d => d.year))
    .range([0, w]);

  const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.median_pay) * 1.15])
    .range([h, 0]);

  // Grid
  g.selectAll('.grid-line')
    .data(y.ticks(4))
    .join('line')
    .attr('x1', 0).attr('x2', w)
    .attr('y1', d => y(d)).attr('y2', d => y(d))
    .attr('stroke', 'rgba(255,255,255,0.04)');

  // Y axis labels
  g.selectAll('.y-label')
    .data(y.ticks(4))
    .join('text')
    .attr('x', -8).attr('y', d => y(d))
    .attr('dy', '0.35em')
    .attr('text-anchor', 'end')
    .attr('fill', '#6e7681')
    .attr('font-size', '11px')
    .attr('font-family', 'var(--font-mono)')
    .text(d => formatCompact(d));

  // X axis
  g.selectAll('.x-label')
    .data(data)
    .join('text')
    .attr('x', d => x(d.year))
    .attr('y', h + 20)
    .attr('text-anchor', 'middle')
    .attr('fill', '#6e7681')
    .attr('font-size', '11px')
    .text(d => d.year);

  // Area gradient
  const areaGrad = svg.append('defs')
    .append('linearGradient')
    .attr('id', 'trend-area-grad')
    .attr('x1', 0).attr('y1', 0)
    .attr('x2', 0).attr('y2', 1);
  areaGrad.append('stop').attr('offset', '0%').attr('stop-color', '#58a6ff').attr('stop-opacity', 0.2);
  areaGrad.append('stop').attr('offset', '100%').attr('stop-color', '#58a6ff').attr('stop-opacity', 0);

  // Area
  const area = d3.area()
    .x(d => x(d.year))
    .y0(h)
    .y1(d => y(d.median_pay))
    .curve(d3.curveMonotoneX);

  g.append('path')
    .datum(data)
    .attr('fill', 'url(#trend-area-grad)')
    .attr('d', area);

  // Line
  const line = d3.line()
    .x(d => x(d.year))
    .y(d => y(d.median_pay))
    .curve(d3.curveMonotoneX);

  g.append('path')
    .datum(data)
    .attr('fill', 'none')
    .attr('stroke', '#58a6ff')
    .attr('stroke-width', 2.5)
    .attr('d', line);

  // Dots
  g.selectAll('.dot')
    .data(data)
    .join('circle')
    .attr('cx', d => x(d.year))
    .attr('cy', d => y(d.median_pay))
    .attr('r', 4)
    .attr('fill', '#58a6ff')
    .attr('stroke', '#0f1117')
    .attr('stroke-width', 2);

  // Value labels on dots
  g.selectAll('.dot-label')
    .data(data)
    .join('text')
    .attr('x', d => x(d.year))
    .attr('y', d => y(d.median_pay) - 12)
    .attr('text-anchor', 'middle')
    .attr('fill', '#e6edf3')
    .attr('font-size', '11px')
    .attr('font-weight', '600')
    .attr('font-family', 'var(--font-mono)')
    .text(d => formatCompact(d.median_pay));
}

window.initSectorChart = initSectorChart;
window.initPayRatioChart = initPayRatioChart;
window.initTrendChart = initTrendChart;
window.formatCurrency = formatCurrency;
window.formatCompact = formatCompact;
