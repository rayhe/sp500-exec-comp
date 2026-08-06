/* === D3 Charts === */

function chartStrokeColor() {
    return typeof isDarkTheme === 'function' && !isDarkTheme() ? '#333' : '#fff';
}

function fmtCurr(val) {
    if (val == null) return '';
    if (val >= 1e9) return '$' + (val / 1e9).toFixed(1) + 'B';
    if (val >= 1e6) return '$' + (val / 1e6).toFixed(1) + 'M';
    if (val >= 1e3) return '$' + (val / 1e3).toFixed(0) + 'K';
    return '$' + val;
}

/* Shared chart tooltip */
var _chartTooltip = null;
function getChartTooltip() {
    if (!_chartTooltip) {
        _chartTooltip = document.createElement('div');
        _chartTooltip.className = 'chart-tooltip';
        document.body.appendChild(_chartTooltip);
    }
    return _chartTooltip;
}
function showChartTooltip(event, html) {
    var tip = getChartTooltip();
    tip.innerHTML = html;
    tip.classList.add('visible');
    positionChartTooltip(event);
}
function positionChartTooltip(event) {
    var tip = getChartTooltip();
    var x = event.clientX + 14;
    var y = event.clientY - 12;
    var tw = tip.offsetWidth;
    var th = tip.offsetHeight;
    if (x + tw > window.innerWidth - 16) x = event.clientX - tw - 14;
    if (y + th > window.innerHeight - 16) y = event.clientY - th + 12;
    if (y < 8) y = 8;
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
}
function hideChartTooltip() {
    var tip = getChartTooltip();
    tip.classList.remove('visible');
}

/* Store refs for resize redraw */
var _chartData = null;

function initCharts(companies, trends, compData) {
    _chartData = { companies: companies, trends: trends, compData: compData };
    drawSectorChart(trends, companies);
    drawTrendChart(trends);
    drawRatioChart(companies);
    drawTop10Chart(companies);
    drawCompositionChart(trends);
    setupChartResize();
}

/* Debounced resize handler — clears and redraws all SVG charts */
function setupChartResize() {
    var resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (!_chartData) return;
            redrawAllCharts();
        }, 250);
    });
}

function redrawAllCharts() {
    var ids = ['sector-chart', 'trend-chart', 'ratio-chart', 'top10-chart', 'composition-chart'];
    ids.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.innerHTML = '';
    });
    drawSectorChart(_chartData.trends, _chartData.companies);
    drawTrendChart(_chartData.trends);
    drawRatioChart(_chartData.companies);
    drawTop10Chart(_chartData.companies);
    drawCompositionChart(_chartData.trends);
}

/* Update ratio histogram bar highlighting without full redraw */
window.highlightRatioBucket = function(minRatio, maxRatio) {
    d3.selectAll('#ratio-chart .hist-bar rect').each(function(d) {
        if (!d) return;
        if (minRatio == null) {
            // Clear: restore all to default
            d3.select(this).attr('opacity', 0.8).attr('stroke', 'none');
        } else if (d.min === minRatio && d.max === maxRatio) {
            // Active bucket
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
        } else {
            // Inactive bucket
            d3.select(this).attr('opacity', 0.3).attr('stroke', 'none');
        }
    });
    d3.selectAll('#ratio-chart .hist-bar text').each(function(d) {
        if (!d) return;
        d3.select(this).attr('opacity', minRatio == null || (d.min === minRatio && d.max === maxRatio) ? 1 : 0.4);
    });
};

/* Update sector chart bar highlighting without full redraw */
window.highlightSectorBar = function(sectorName) {
    d3.selectAll('#sector-chart .bar').each(function(d) {
        if (!d || !d.sector) return;
        if (!sectorName) {
            d3.select(this).attr('opacity', 0.8).attr('stroke', 'none');
        } else if (d.sector === sectorName) {
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
        } else {
            d3.select(this).attr('opacity', 0.3).attr('stroke', 'none');
        }
    });
    d3.selectAll('#sector-chart .bar-label').each(function(d) {
        if (!d || !d.sector) return;
        d3.select(this).attr('opacity', !sectorName || d.sector === sectorName ? 1 : 0.4);
    });
    // Distribution elements update on full redraw via redrawAllCharts
};

/* --- Sector Bar Chart with Distribution Box Plot --- */
function drawSectorChart(trends, companies) {
    var container = document.getElementById('sector-chart');
    var data = trends.median_pay_by_sector_sp500_fy2024 && trends.median_pay_by_sector_sp500_fy2024.data
        ? trends.median_pay_by_sector_sp500_fy2024.data.filter(function(d) { return d.median_pay; })
        : [];

    if (data.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No sector data available</p>';
        return;
    }

    // Compute per-sector distribution from company data
    var sectorDist = {};
    if (companies && companies.length > 0) {
        companies.forEach(function(c) {
            if (!c.sector || c.total_compensation == null) return;
            if (!sectorDist[c.sector]) sectorDist[c.sector] = [];
            sectorDist[c.sector].push(c.total_compensation);
        });
        Object.keys(sectorDist).forEach(function(s) {
            var vals = sectorDist[s].sort(function(a, b) { return a - b; });
            var n = vals.length;
            var q1Idx = Math.floor(n * 0.25);
            var q3Idx = Math.floor(n * 0.75);
            sectorDist[s] = {
                min: vals[0],
                q1: vals[q1Idx],
                median: vals[Math.floor(n * 0.5)],
                q3: vals[q3Idx],
                max: vals[n - 1],
                count: n,
                values: vals
            };
        });
    }

    // Merge distribution data into chart data
    data.forEach(function(d) {
        if (sectorDist[d.sector]) {
            d._dist = sectorDist[d.sector];
        }
    });

    data.sort(function(a, b) { return b.median_pay - a.median_pay; });

    // Use Q3 (75th pct) for x-axis max to show distribution without extreme outlier stretching
    var xMax = d3.max(data, function(d) {
        return d._dist ? d._dist.q3 : d.median_pay;
    });
    // But ensure max doesn't clip — extend to cover max values with capped whiskers
    var absMax = d3.max(data, function(d) {
        return d._dist ? d._dist.max : d.median_pay;
    });
    // Use the larger of Q3*1.25 or median_pay*1.1 to give room for whiskers
    xMax = Math.max(xMax * 1.25, d3.max(data, function(d) { return d.median_pay; }) * 1.3);

    var margin = { top: 20, right: 100, bottom: 30, left: 160 };
    var w = container.clientWidth - margin.left - margin.right;
    var h = Math.max(280, data.length * 32);

    var svg = d3.select('#sector-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleLinear().domain([0, xMax]).range([0, w]);
    var y = d3.scaleBand().domain(data.map(function(d) { return d.sector; })).range([0, h]).padding(0.3);

    // Grid
    svg.append('g').attr('class', 'grid')
        .call(d3.axisBottom(x).tickSize(h).tickFormat('').ticks(5))
        .attr('transform', 'translate(0,0)');

    // Y axis
    svg.append('g').attr('class', 'axis')
        .call(d3.axisLeft(y).tickSize(0).tickPadding(8));

    // Draw box plot elements for each sector
    var bandH = y.bandwidth();
    var boxH = bandH * 0.6;
    var boxOffset = (bandH - boxH) / 2;

    data.forEach(function(d) {
        if (!d._dist) return;
        var dist = d._dist;
        var cy = y(d.sector) + bandH / 2;
        var byTop = y(d.sector) + boxOffset;

        var isActive = activeSector && d.sector === activeSector;
        var isDimmed = activeSector && d.sector !== activeSector;
        var baseOpacity = isDimmed ? 0.15 : 0.5;

        // Whisker line: min → max (capped at chart width)
        var whiskerMax = Math.min(x(dist.max), w);
        svg.append('line')
            .attr('class', 'dist-whisker')
            .attr('x1', x(dist.min))
            .attr('x2', whiskerMax)
            .attr('y1', cy)
            .attr('y2', cy)
            .attr('stroke', '#00b4d8')
            .attr('stroke-width', 1)
            .attr('opacity', baseOpacity)
            .attr('stroke-dasharray', '3,3');

        // Whisker caps (short vertical lines at min and max)
        var capH = boxH * 0.4;
        svg.append('line')
            .attr('class', 'dist-cap')
            .attr('x1', x(dist.min)).attr('x2', x(dist.min))
            .attr('y1', cy - capH / 2).attr('y2', cy + capH / 2)
            .attr('stroke', '#00b4d8')
            .attr('stroke-width', 1.5)
            .attr('opacity', baseOpacity);
        svg.append('line')
            .attr('class', 'dist-cap')
            .attr('x1', whiskerMax).attr('x2', whiskerMax)
            .attr('y1', cy - capH / 2).attr('y2', cy + capH / 2)
            .attr('stroke', '#00b4d8')
            .attr('stroke-width', 1.5)
            .attr('opacity', baseOpacity);

        // IQR box: Q1 → Q3
        svg.append('rect')
            .attr('class', 'dist-box')
            .attr('x', x(dist.q1))
            .attr('y', byTop)
            .attr('width', Math.max(x(dist.q3) - x(dist.q1), 2))
            .attr('height', boxH)
            .attr('fill', '#00b4d8')
            .attr('opacity', isDimmed ? 0.08 : 0.18)
            .attr('stroke', '#00b4d8')
            .attr('stroke-width', isDimmed ? 0.5 : 1)
            .attr('stroke-opacity', isDimmed ? 0.15 : 0.4)
            .attr('rx', 2);

        // Median line inside box
        svg.append('line')
            .attr('class', 'dist-median')
            .attr('x1', x(dist.median)).attr('x2', x(dist.median))
            .attr('y1', byTop).attr('y2', byTop + boxH)
            .attr('stroke', '#00b4d8')
            .attr('stroke-width', 2)
            .attr('opacity', isDimmed ? 0.2 : 0.7);
    });

    // Bars (median) — drawn on top of distribution
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
        .attr('opacity', function(d) {
            if (activeSector) return d.sector === activeSector ? 1 : 0.3;
            return 0.8;
        })
        .each(function(d) {
            if (activeSector && d.sector === activeSector) {
                d3.select(this).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
            }
        })
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1);
            var html = '<div class="ct-title">' + d.sector + '</div>' +
                '<div class="ct-row"><span class="ct-label">Median CEO Pay</span><span class="ct-val">' + fmtCurr(d.median_pay) + '</span></div>';
            if (d._dist) {
                html += '<div class="ct-row"><span class="ct-label">25th Percentile</span><span class="ct-val">' + fmtCurr(d._dist.q1) + '</span></div>' +
                    '<div class="ct-row"><span class="ct-label">75th Percentile</span><span class="ct-val">' + fmtCurr(d._dist.q3) + '</span></div>' +
                    '<div class="ct-row"><span class="ct-label">Range</span><span class="ct-val">' + fmtCurr(d._dist.min) + ' — ' + fmtCurr(d._dist.max) + '</span></div>' +
                    '<div class="ct-row"><span class="ct-label">Companies</span><span class="ct-val">' + d._dist.count + '</span></div>';
            }
            html += '<div class="ct-row ct-sub"><span class="ct-label">Click to filter table</span></div>';
            showChartTooltip(event, html);
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function(event, d) {
            var isActive = activeSector && d.sector === activeSector;
            d3.select(this)
                .attr('opacity', isActive ? 1 : (activeSector ? 0.3 : 0.8))
                .attr('stroke', isActive ? chartStrokeColor() : 'none')
                .attr('stroke-width', isActive ? 1.5 : 0);
            hideChartTooltip();
        })
        .on('click', function(event, d) {
            if (window.filterBySector) window.filterBySector(d.sector);
        });

    // Labels — show median and count
    svg.selectAll('.bar-label')
        .data(data)
        .join('text')
        .attr('class', 'bar-label')
        .attr('x', function(d) { return x(d.median_pay) + 6; })
        .attr('y', function(d) { return y(d.sector) + y.bandwidth() / 2; })
        .attr('dy', '0.35em')
        .text(function(d) {
            var label = fmtCurr(d.median_pay);
            if (d._dist) label += ' (' + d._dist.count + ')';
            return label;
        })
        .attr('opacity', function(d) {
            if (activeSector) return d.sector === activeSector ? 1 : 0.4;
            return 1;
        });

    // Distribution legend below chart
    var legendG = svg.append('g')
        .attr('class', 'dist-legend')
        .attr('transform', 'translate(0,' + (h + 8) + ')');

    var legendItems = [
        { type: 'bar', label: 'Median', color: '#00b4d8', opacity: 0.8 },
        { type: 'box', label: 'IQR (25th–75th)', color: '#00b4d8', opacity: 0.18 },
        { type: 'whisker', label: 'Min–Max range', color: '#00b4d8', opacity: 0.5 }
    ];

    var lx = 0;
    var textColor = typeof getThemeMutedColor === 'function' ? getThemeMutedColor() : '#6b7280';
    legendItems.forEach(function(item) {
        if (item.type === 'bar') {
            legendG.append('rect')
                .attr('x', lx).attr('y', 2)
                .attr('width', 16).attr('height', 10)
                .attr('fill', item.color).attr('opacity', item.opacity)
                .attr('rx', 2);
        } else if (item.type === 'box') {
            legendG.append('rect')
                .attr('x', lx).attr('y', 2)
                .attr('width', 16).attr('height', 10)
                .attr('fill', item.color).attr('opacity', item.opacity)
                .attr('stroke', item.color).attr('stroke-width', 1).attr('stroke-opacity', 0.4)
                .attr('rx', 2);
        } else if (item.type === 'whisker') {
            legendG.append('line')
                .attr('x1', lx).attr('x2', lx + 16)
                .attr('y1', 7).attr('y2', 7)
                .attr('stroke', item.color).attr('stroke-width', 1)
                .attr('opacity', item.opacity).attr('stroke-dasharray', '3,3');
            legendG.append('line')
                .attr('x1', lx).attr('x2', lx)
                .attr('y1', 4).attr('y2', 10)
                .attr('stroke', item.color).attr('stroke-width', 1.5)
                .attr('opacity', item.opacity);
            legendG.append('line')
                .attr('x1', lx + 16).attr('x2', lx + 16)
                .attr('y1', 4).attr('y2', 10)
                .attr('stroke', item.color).attr('stroke-width', 1.5)
                .attr('opacity', item.opacity);
        }
        legendG.append('text')
            .attr('x', lx + 22).attr('y', 11)
            .attr('fill', textColor)
            .attr('font-size', '10px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(item.label);
        lx += item.label.length * 6 + 36;
    });
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
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            d3.select(this).attr('r', 7).attr('stroke-width', 3);
            var yoyHtml = '';
            if (d.yoy_change) {
                var isNeg = d.yoy_change.indexOf('-') === 0;
                var yoyColor = isNeg ? '#ef476f' : '#06d6a0';
                var yoyPrefix = isNeg ? '' : '+';
                yoyHtml = '<div class="ct-row"><span class="ct-label">YoY Change</span><span class="ct-val" style="color:' + yoyColor + '">' + yoyPrefix + d.yoy_change + '</span></div>';
            }
            showChartTooltip(event,
                '<div class="ct-title">FY ' + d.year + '</div>' +
                '<div class="ct-row"><span class="ct-label">Median CEO Pay</span><span class="ct-val">' + fmtCurr(d.median_pay) + '</span></div>' +
                yoyHtml);
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function() {
            d3.select(this).attr('r', 4).attr('stroke-width', 2);
            hideChartTooltip();
        });

    // Labels on dots
    svg.selectAll('.dot-label')
        .data(data)
        .join('text')
        .attr('class', 'bar-label')
        .attr('x', function(d) { return x(d.year); })
        .attr('y', function(d) { return y(d.median_pay) - 12; })
        .attr('text-anchor', 'middle')
        .text(function(d) { return fmtCurr(d.median_pay); });

    // YoY growth annotations between consecutive dots
    var yoyPairs = [];
    for (var i = 1; i < data.length; i++) {
        if (data[i].yoy_change) {
            yoyPairs.push({
                fromYear: data[i - 1].year,
                toYear: data[i].year,
                fromPay: data[i - 1].median_pay,
                toPay: data[i].median_pay,
                change: data[i].yoy_change
            });
        }
    }

    var yoyGroup = svg.append('g').attr('class', 'yoy-annotations');

    yoyPairs.forEach(function(d) {
        var midX = (x(d.fromYear) + x(d.toYear)) / 2;
        var midY = (y(d.fromPay) + y(d.toPay)) / 2;
        var isNeg = d.change.indexOf('-') === 0;
        var labelColor = isNeg ? '#ef476f' : '#06d6a0';
        var labelText = isNeg ? d.change : '+' + d.change;
        var arrow = isNeg ? '▼' : '▲';
        // Position below line to avoid dot value labels above
        var labelY = midY + 22;

        var annGroup = yoyGroup.append('g');

        // Render text first to measure bounding box, then prepend rect behind it
        var textNode = annGroup.append('text')
            .attr('x', midX)
            .attr('y', labelY)
            .attr('text-anchor', 'middle')
            .attr('font-size', '9.5px')
            .attr('font-weight', '600')
            .attr('font-family', 'JetBrains Mono, monospace')
            .attr('fill', labelColor)
            .text(arrow + ' ' + labelText);

        // Background pill behind text for contrast
        var bbox = textNode.node().getBBox();
        var padX = 5, padY = 2;
        annGroup.insert('rect', 'text')
            .attr('x', bbox.x - padX)
            .attr('y', bbox.y - padY)
            .attr('width', bbox.width + padX * 2)
            .attr('height', bbox.height + padY * 2)
            .attr('rx', 6)
            .attr('fill', typeof isDarkTheme === 'function' && !isDarkTheme() ? 'rgba(255,255,255,0.85)' : 'rgba(15,15,26,0.8)');
    });
}

/* --- Pay Ratio Distribution (Histogram) --- */
function drawRatioChart(companies) {
    var container = document.getElementById('ratio-chart');
    var withRatio = companies.filter(function(c) { return c.pay_ratio != null; });

    if (withRatio.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No pay ratio data available</p>';
        return;
    }

    // Define buckets with meaningful breakpoints
    var buckets = [
        { min: 0, max: 50, label: '0–50', color: '#06d6a0' },
        { min: 50, max: 100, label: '50–100', color: '#06d6a0' },
        { min: 100, max: 200, label: '100–200', color: '#34d399' },
        { min: 200, max: 300, label: '200–300', color: '#ffd166' },
        { min: 300, max: 500, label: '300–500', color: '#ffd166' },
        { min: 500, max: 1000, label: '500–1K', color: '#fb923c' },
        { min: 1000, max: 2000, label: '1K–2K', color: '#ef476f' },
        { min: 2000, max: Infinity, label: '2K+', color: '#ef476f' }
    ];

    // Count companies in each bucket and collect names
    buckets.forEach(function(b) {
        b.companies = withRatio.filter(function(c) {
            return c.pay_ratio >= b.min && c.pay_ratio < b.max;
        });
        b.count = b.companies.length;
        // Sort by pay ratio descending within bucket
        b.companies.sort(function(a, bb) { return bb.pay_ratio - a.pay_ratio; });
    });

    // Filter out empty buckets
    var activeBuckets = buckets.filter(function(b) { return b.count > 0; });

    var margin = { top: 20, right: 50, bottom: 50, left: 70 };
    var w = container.clientWidth - margin.left - margin.right;
    var h = 300;

    var svg = d3.select('#ratio-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleBand()
        .domain(activeBuckets.map(function(b) { return b.label; }))
        .range([0, w])
        .padding(0.2);

    var y = d3.scaleLinear()
        .domain([0, d3.max(activeBuckets, function(b) { return b.count; }) * 1.15])
        .range([h, 0]);

    // Grid
    svg.append('g').attr('class', 'grid')
        .call(d3.axisLeft(y).tickSize(-w).tickFormat('').ticks(6));

    // X axis
    svg.append('g').attr('class', 'axis')
        .attr('transform', 'translate(0,' + h + ')')
        .call(d3.axisBottom(x).tickSize(0).tickPadding(10));

    // X axis label
    svg.append('text')
        .attr('x', w / 2)
        .attr('y', h + 42)
        .attr('text-anchor', 'middle')
        .attr('fill', typeof getThemeMutedColor === 'function' ? getThemeMutedColor() : '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('CEO : Worker Pay Ratio');

    // Y axis
    svg.append('g').attr('class', 'axis')
        .call(d3.axisLeft(y).ticks(6).tickFormat(function(d) { return d; }));

    // Y axis label
    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -h / 2)
        .attr('y', -50)
        .attr('text-anchor', 'middle')
        .attr('fill', typeof getThemeMutedColor === 'function' ? getThemeMutedColor() : '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('Number of Companies');

    // Bars with tooltip area
    var bars = svg.selectAll('.hist-bar')
        .data(activeBuckets)
        .join('g')
        .attr('class', 'hist-bar');

    bars.append('rect')
        .attr('x', function(b) { return x(b.label); })
        .attr('y', function(b) { return y(b.count); })
        .attr('width', x.bandwidth())
        .attr('height', function(b) { return h - y(b.count); })
        .attr('fill', function(b) { return b.color; })
        .attr('rx', 3)
        .attr('opacity', function(b) {
            var ab = window._activeRatioBucket;
            if (ab) return (b.min === ab.min && b.max === ab.max) ? 1 : 0.3;
            return 0.8;
        })
        .each(function(b) {
            var ab = window._activeRatioBucket;
            if (ab && b.min === ab.min && b.max === ab.max) {
                d3.select(this).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
            }
        })
        .style('cursor', 'pointer')
        .on('mouseover', function(event, b) {
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1);
            var pct = (b.count / withRatio.length * 100).toFixed(1);
            var topNames = b.companies.slice(0, 3).map(function(c) { return c.ticker + ' (' + c.pay_ratio.toLocaleString() + ':1)'; }).join(', ');
            var html = '<div class="ct-title">Pay Ratio ' + b.label + '</div>' +
                '<div class="ct-row"><span class="ct-label">Companies</span><span class="ct-val">' + b.count + ' (' + pct + '%)</span></div>';
            if (topNames) html += '<div class="ct-row ct-sub"><span class="ct-label">Highest</span><span class="ct-val">' + topNames + '</span></div>';
            html += '<div class="ct-row ct-sub"><span class="ct-label">Click to filter table by ratio range</span></div>';
            showChartTooltip(event, html);
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function(event, b) {
            var ab = window._activeRatioBucket;
            var isActive = ab && b.min === ab.min && b.max === ab.max;
            d3.select(this)
                .attr('opacity', isActive ? 1 : (ab ? 0.3 : 0.8))
                .attr('stroke', isActive ? chartStrokeColor() : 'none')
                .attr('stroke-width', isActive ? 1.5 : 0);
            hideChartTooltip();
        })
        .on('click', function(event, b) {
            // Filter table by searching for companies in this ratio bucket
            if (window.filterByRatioBucket) window.filterByRatioBucket(b.min, b.max);
        });

    // Count labels on top of bars
    bars.append('text')
        .attr('class', 'bar-label')
        .attr('x', function(b) { return x(b.label) + x.bandwidth() / 2; })
        .attr('y', function(b) { return y(b.count) - 6; })
        .attr('text-anchor', 'middle')
        .attr('font-weight', '600')
        .text(function(b) { return b.count; })
        .attr('opacity', function(b) {
            var ab = window._activeRatioBucket;
            if (ab) return (b.min === ab.min && b.max === ab.max) ? 1 : 0.4;
            return 1;
        });

    // Median line
    var ratios = withRatio.map(function(c) { return c.pay_ratio; }).sort(function(a, b) { return a - b; });
    var medianRatio = ratios[Math.floor(ratios.length / 2)];

    // Find which bucket the median falls in, and position the line there
    var medianBucket = activeBuckets.find(function(b) { return medianRatio >= b.min && medianRatio < b.max; });
    if (medianBucket) {
        // Interpolate position within the bucket
        var bucketFrac = (medianRatio - medianBucket.min) / (Math.min(medianBucket.max, 5000) - medianBucket.min);
        var medianX = x(medianBucket.label) + bucketFrac * x.bandwidth();

        svg.append('line')
            .attr('x1', medianX)
            .attr('x2', medianX)
            .attr('y1', 0)
            .attr('y2', h)
            .attr('stroke', chartStrokeColor())
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '6,4')
            .attr('opacity', 0.6);

        svg.append('text')
            .attr('x', medianX + 6)
            .attr('y', 12)
            .attr('fill', chartStrokeColor())
            .attr('font-size', '11px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .attr('font-weight', '500')
            .attr('opacity', 0.8)
            .text('Median: ' + medianRatio.toLocaleString() + ':1');
    }

    // Summary stats below chart
    var statsG = svg.append('g').attr('transform', 'translate(0,' + (h + 48) + ')');
    var topOutliers = withRatio.sort(function(a, b) { return b.pay_ratio - a.pay_ratio; }).slice(0, 3);
    // Removed — keep chart clean. Top outliers visible via table sort.
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
        .attr('opacity', 0.85)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1);
            var rank = top10.indexOf(d) + 1;
            var html = '<div class="ct-title">#' + rank + ' ' + d.ceo_name + '</div>' +
                '<div class="ct-row"><span class="ct-label">Company</span><span class="ct-val">' + d.ticker + '</span></div>' +
                '<div class="ct-row"><span class="ct-label">Total Compensation</span><span class="ct-val">' + fmtCurr(d.total_compensation) + '</span></div>';
            if (d.pay_ratio) html += '<div class="ct-row"><span class="ct-label">Pay Ratio</span><span class="ct-val">' + d.pay_ratio.toLocaleString() + ':1</span></div>';
            if (d.sector) html += '<div class="ct-row"><span class="ct-label">Sector</span><span class="ct-val">' + d.sector + '</span></div>';
            html += '<div class="ct-row ct-sub"><span class="ct-label">Click to find in table</span></div>';
            showChartTooltip(event, html);
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function() {
            d3.select(this).attr('opacity', 0.85).attr('stroke', 'none');
            hideChartTooltip();
        })
        .on('click', function(event, d) {
            if (window.findCompanyInTable) window.findCompanyInTable(d.ticker);
        });

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
        .attr('height', barH + margin.top + margin.bottom)
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
            .attr('opacity', 0.85)
            .style('cursor', 'pointer')
            .on('mouseover', function(event) {
                d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
                showChartTooltip(event,
                    '<div class="ct-title">' + seg.label + '</div>' +
                    '<div class="ct-row"><span class="ct-label">Share of Total</span><span class="ct-val">' + seg.pct.toFixed(1) + '%</span></div>' +
                    '<div class="ct-row"><span class="ct-label">Median Value</span><span class="ct-val">' + seg.value + '</span></div>');
            })
            .on('mousemove', function(event) { positionChartTooltip(event); })
            .on('mouseout', function() {
                d3.select(this).attr('opacity', 0.85).attr('stroke', 'none');
                hideChartTooltip();
            });

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

    // Legend below — HTML flexbox for responsive wrapping
    var legendDiv = document.createElement('div');
    legendDiv.className = 'composition-legend';
    segments.forEach(function(seg) {
        var item = document.createElement('div');
        item.className = 'composition-legend-item';
        item.innerHTML = '<span class="composition-legend-dot" style="background:' + seg.color + '"></span>' +
            '<span class="composition-legend-text">' + seg.label + ' (' + seg.pct.toFixed(1) + '%) — ' + seg.value + '</span>';
        legendDiv.appendChild(item);
    });
    container.appendChild(legendDiv);
}
