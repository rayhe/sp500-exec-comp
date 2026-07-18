/* === D3 Charts === */

function fmtCurr(val) {
    if (val == null) return '';
    if (val >= 1e9) return '$' + (val / 1e9).toFixed(1) + 'B';
    if (val >= 1e6) return '$' + (val / 1e6).toFixed(1) + 'M';
    if (val >= 1e3) return '$' + (val / 1e3).toFixed(0) + 'K';
    return '$' + val;
}

function initCharts(companies, trends, compData) {
    drawSectorChart(trends);
    drawTrendChart(trends);
    drawRatioChart(companies);
    drawTop10Chart(companies);
    drawCompositionChart(trends);
}

/* --- Sector Bar Chart --- */
function drawSectorChart(trends) {
    var container = document.getElementById('sector-chart');
    var data = trends.median_pay_by_sector_sp500_fy2024 && trends.median_pay_by_sector_sp500_fy2024.data
        ? trends.median_pay_by_sector_sp500_fy2024.data.filter(function(d) { return d.median_pay; })
        : [];

    if (data.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No sector data available</p>';
        return;
    }

    data.sort(function(a, b) { return b.median_pay - a.median_pay; });

    var margin = { top: 20, right: 80, bottom: 30, left: 160 };
    var w = container.clientWidth - margin.left - margin.right;
    var h = Math.max(280, data.length * 32);

    var svg = d3.select('#sector-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleLinear().domain([0, d3.max(data, function(d) { return d.median_pay; }) * 1.1]).range([0, w]);
    var y = d3.scaleBand().domain(data.map(function(d) { return d.sector; })).range([0, h]).padding(0.3);

    // Grid
    svg.append('g').attr('class', 'grid')
        .call(d3.axisBottom(x).tickSize(h).tickFormat('').ticks(5))
        .attr('transform', 'translate(0,0)');

    // Y axis
    svg.append('g').attr('class', 'axis')
        .call(d3.axisLeft(y).tickSize(0).tickPadding(8));

    // Bars
    svg.selectAll('.bar')
        .data(data)
        .join('rect')
        .attr('class', 'bar')
        .attr('x', 0)
        .attr('y', function(d) { return y(d.sector); })
        .attr('width', function(d) { return x(d.median_pay); })
        .attr('height', y.bandwidth())
        .attr('fill', '#00b4d8')
        .attr('rx', 3)
        .attr('opacity', 0.8);

    // Labels
    svg.selectAll('.bar-label')
        .data(data)
        .join('text')
        .attr('class', 'bar-label')
        .attr('x', function(d) { return x(d.median_pay) + 6; })
        .attr('y', function(d) { return y(d.sector) + y.bandwidth() / 2; })
        .attr('dy', '0.35em')
        .text(function(d) { return fmtCurr(d.median_pay); });
}

/* --- Trend Line Chart --- */
function drawTrendChart(trends) {
    var container = document.getElementById('trend-chart');
    var data = trends.median_ceo_pay_by_year && trends.median_ceo_pay_by_year.data
        ? trends.median_ceo_pay_by_year.data
        : [];

    if (data.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No trend data available</p>';
        return;
    }

    var margin = { top: 20, right: 40, bottom: 40, left: 70 };
    var w = container.clientWidth - margin.left - margin.right;
    var h = 280;

    var svg = d3.select('#trend-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleLinear()
        .domain(d3.extent(data, function(d) { return d.year; }))
        .range([0, w]);

    var y = d3.scaleLinear()
        .domain([
            d3.min(data, function(d) { return d.median_pay; }) * 0.9,
            d3.max(data, function(d) { return d.median_pay; }) * 1.05
        ])
        .range([h, 0]);

    // Grid
    svg.append('g').attr('class', 'grid')
        .call(d3.axisLeft(y).tickSize(-w).tickFormat('').ticks(5));

    // X axis
    svg.append('g').attr('class', 'axis')
        .attr('transform', 'translate(0,' + h + ')')
        .call(d3.axisBottom(x).ticks(data.length).tickFormat(d3.format('d')));

    // Y axis
    svg.append('g').attr('class', 'axis')
        .call(d3.axisLeft(y).ticks(5).tickFormat(function(d) { return fmtCurr(d); }));

    // Area
    var area = d3.area()
        .x(function(d) { return x(d.year); })
        .y0(h)
        .y1(function(d) { return y(d.median_pay); })
        .curve(d3.curveMonotoneX);

    svg.append('path')
        .datum(data)
        .attr('fill', 'rgba(0,180,216,0.15)')
        .attr('d', area);

    // Line
    var line = d3.line()
        .x(function(d) { return x(d.year); })
        .y(function(d) { return y(d.median_pay); })
        .curve(d3.curveMonotoneX);

    svg.append('path')
        .datum(data)
        .attr('fill', 'none')
        .attr('stroke', '#00b4d8')
        .attr('stroke-width', 2.5)
        .attr('d', line);

    // Dots
    svg.selectAll('.dot')
        .data(data)
        .join('circle')
        .attr('cx', function(d) { return x(d.year); })
        .attr('cy', function(d) { return y(d.median_pay); })
        .attr('r', 4)
        .attr('fill', '#00b4d8')
        .attr('stroke', '#0f0f1a')
        .attr('stroke-width', 2);

    // Labels on dots
    svg.selectAll('.dot-label')
        .data(data)
        .join('text')
        .attr('class', 'bar-label')
        .attr('x', function(d) { return x(d.year); })
        .attr('y', function(d) { return y(d.median_pay) - 12; })
        .attr('text-anchor', 'middle')
        .text(function(d) { return fmtCurr(d.median_pay); });
}

/* --- Pay Ratio Distribution --- */
function drawRatioChart(companies) {
    var container = document.getElementById('ratio-chart');
    var withRatio = companies.filter(function(c) { return c.pay_ratio != null; })
        .sort(function(a, b) { return b.pay_ratio - a.pay_ratio; });

    if (withRatio.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No pay ratio data available</p>';
        return;
    }

    var margin = { top: 20, right: 60, bottom: 30, left: 80 };
    var w = container.clientWidth - margin.left - margin.right;
    var h = Math.max(280, withRatio.length * 22);

    var svg = d3.select('#ratio-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleLinear()
        .domain([0, d3.max(withRatio, function(d) { return d.pay_ratio; }) * 1.05])
        .range([0, w]);

    var y = d3.scaleBand()
        .domain(withRatio.map(function(d) { return d.ticker; }))
        .range([0, h])
        .padding(0.25);

    // Grid
    svg.append('g').attr('class', 'grid')
        .call(d3.axisBottom(x).tickSize(h).tickFormat('').ticks(5));

    // Y axis
    svg.append('g').attr('class', 'axis')
        .call(d3.axisLeft(y).tickSize(0).tickPadding(6));

    // Bars
    svg.selectAll('.ratio-bar')
        .data(withRatio)
        .join('rect')
        .attr('x', 0)
        .attr('y', function(d) { return y(d.ticker); })
        .attr('width', function(d) { return x(d.pay_ratio); })
        .attr('height', y.bandwidth())
        .attr('fill', function(d) {
            return d.pay_ratio > 2000 ? '#ef476f' : d.pay_ratio > 500 ? '#ffd166' : '#06d6a0';
        })
        .attr('rx', 2)
        .attr('opacity', 0.8);

    // Labels
    svg.selectAll('.ratio-label')
        .data(withRatio)
        .join('text')
        .attr('class', 'bar-label')
        .attr('x', function(d) { return x(d.pay_ratio) + 4; })
        .attr('y', function(d) { return y(d.ticker) + y.bandwidth() / 2; })
        .attr('dy', '0.35em')
        .text(function(d) { return d.pay_ratio.toLocaleString() + ':1'; });
}

/* --- Top 10 Horizontal Bar Chart --- */
function drawTop10Chart(companies) {
    var container = document.getElementById('top10-chart');
    var top10 = companies.slice().sort(function(a, b) {
        return b.total_compensation - a.total_compensation;
    }).slice(0, 10);

    var margin = { top: 20, right: 80, bottom: 30, left: 120 };
    var w = container.clientWidth - margin.left - margin.right;
    var h = 320;

    var svg = d3.select('#top10-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleLinear()
        .domain([0, d3.max(top10, function(d) { return d.total_compensation; }) * 1.05])
        .range([0, w]);

    var y = d3.scaleBand()
        .domain(top10.map(function(d) { return d.ceo_name; }))
        .range([0, h])
        .padding(0.3);

    // Grid
    svg.append('g').attr('class', 'grid')
        .call(d3.axisBottom(x).tickSize(h).tickFormat('').ticks(5));

    // Y axis
    svg.append('g').attr('class', 'axis')
        .call(d3.axisLeft(y).tickSize(0).tickPadding(8));

    // Gradient bars
    var colors = ['#00b4d8', '#0096c7', '#0077b6', '#023e8a', '#03045e', '#1b263b', '#415a77', '#778da9', '#94a3b8', '#94a3b8'];
    svg.selectAll('.top-bar')
        .data(top10)
        .join('rect')
        .attr('x', 0)
        .attr('y', function(d) { return y(d.ceo_name); })
        .attr('width', function(d) { return x(d.total_compensation); })
        .attr('height', y.bandwidth())
        .attr('fill', function(d, i) { return colors[i]; })
        .attr('rx', 3)
        .attr('opacity', 0.85);

    // Labels
    svg.selectAll('.top-label')
        .data(top10)
        .join('text')
        .attr('class', 'bar-label')
        .attr('x', function(d) { return x(d.total_compensation) + 6; })
        .attr('y', function(d) { return y(d.ceo_name) + y.bandwidth() / 2; })
        .attr('dy', '0.35em')
        .text(function(d) { return fmtCurr(d.total_compensation); });
}

/* --- Compensation Composition (Stacked Horizontal Bar) --- */
function drawCompositionChart(trends) {
    var container = document.getElementById('composition-chart');
    var compComp = trends.compensation_composition;
    if (!compComp || !compComp.s_and_p_500) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No composition data</p>';
        return;
    }

    var sp = compComp.s_and_p_500;
    var stockPct = sp.stock_awards_pct || 71.6;
    var salaryPct = 7.6; // ~$1.3M / $17.1M
    var perksPct = 1.7; // ~$286K / $17.1M
    var otherPct = 100 - stockPct - salaryPct - perksPct;

    var segments = [
        { label: 'Stock Awards', pct: stockPct, color: '#00b4d8', value: '$10.3M median' },
        { label: 'Non-Equity Incentive', pct: otherPct, color: '#a78bfa', value: 'Performance-based cash' },
        { label: 'Base Salary', pct: salaryPct, color: '#06d6a0', value: '$1.3M median' },
        { label: 'Perks & Other', pct: perksPct, color: '#ffd166', value: '$286K median' }
    ];

    var margin = { top: 10, right: 20, bottom: 10, left: 20 };
    var w = container.clientWidth - margin.left - margin.right;
    var barH = 40;

    var svg = d3.select('#composition-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', barH + margin.top + margin.bottom + 60)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var xPos = 0;
    segments.forEach(function(seg) {
        var segW = (seg.pct / 100) * w;
        svg.append('rect')
            .attr('x', xPos)
            .attr('y', 0)
            .attr('width', Math.max(segW - 2, 0))
            .attr('height', barH)
            .attr('fill', seg.color)
            .attr('rx', 4)
            .attr('opacity', 0.85);

        if (segW > 50) {
            svg.append('text')
                .attr('x', xPos + segW / 2)
                .attr('y', barH / 2)
                .attr('dy', '0.35em')
                .attr('text-anchor', 'middle')
                .attr('fill', '#fff')
                .attr('font-size', '12px')
                .attr('font-weight', '600')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .text(seg.pct.toFixed(1) + '%');
        }
        xPos += segW;
    });

    // Legend below
    var legendG = svg.append('g').attr('transform', 'translate(0,' + (barH + 16) + ')');
    var lx = 0;
    segments.forEach(function(seg) {
        var g = legendG.append('g').attr('transform', 'translate(' + lx + ',0)');
        g.append('rect').attr('width', 12).attr('height', 12).attr('rx', 2).attr('fill', seg.color);
        g.append('text')
            .attr('x', 16).attr('y', 10)
            .attr('fill', '#a1a1aa')
            .attr('font-size', '11px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(seg.label + ' (' + seg.pct.toFixed(1) + '%) — ' + seg.value);
        lx += 250;
    });
}
