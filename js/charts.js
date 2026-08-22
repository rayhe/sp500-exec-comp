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
    drawCompDistChart(companies);
    drawLorenzChart(companies);
    drawTop10Chart(companies);
    drawCompositionChart(trends);
    drawQuartileComposition(companies);
    drawScatterChart(companies);
    drawYoYDistChart(companies);
    drawGenderPayChart(trends);
    drawCeoCfoChart(companies);
    drawSopDistChart(companies);
    drawConcDistChart(companies);
    drawSopScatterChart(companies);
    drawCompTreemap(companies);
    drawCorrelationMatrix(companies);
    drawCrossSectorCorrelation(companies);
    drawGovDistChart(companies);
    drawSectorGovChart(companies);
    drawGovQuartileComp(companies);
    drawGovPayScatter(companies);
    drawPayAnomalyChart(companies);
    drawTenurePayGrowthChart(companies);
    drawTenureGovCrossTab(companies);
    drawGERChart(companies);
    setupChartResize();
    // Scatter log-scale toggles
    var logXCb = document.getElementById('scatter-log-x');
    var logYCb = document.getElementById('scatter-log-y');
    function _redrawScatter() { var el = document.getElementById('scatter-chart'); if (el) el.innerHTML = ''; drawScatterChart(_chartData.companies); }
    if (logXCb) logXCb.addEventListener('change', _redrawScatter);
    if (logYCb) logYCb.addEventListener('change', _redrawScatter);
    // Scatter trend line toggle
    var trendCb = document.getElementById('scatter-trend-line');
    if (trendCb) trendCb.addEventListener('change', _redrawScatter);
    // Scatter axis metric selectors
    var xMetricSel = document.getElementById('scatter-x-metric');
    var yMetricSel = document.getElementById('scatter-y-metric');
    if (xMetricSel) xMetricSel.addEventListener('change', function() { _syncPresetActiveState(); _redrawScatter(); });
    if (yMetricSel) yMetricSel.addEventListener('change', function() { _syncPresetActiveState(); _redrawScatter(); });
    // Scatter axis preset buttons
    setupScatterPresets(_redrawScatter);
    // Top 10 mode toggle buttons
    setupTop10ModeToggle();
    // Trend overlay toggle buttons
    setupTrendOverlayToggle();
}

/* Sync active state of scatter preset buttons to match current dropdowns */
function _syncPresetActiveState() {
    var xSel = document.getElementById('scatter-x-metric');
    var ySel = document.getElementById('scatter-y-metric');
    if (!xSel || !ySel) return;
    var curX = xSel.value, curY = ySel.value;
    document.querySelectorAll('.scatter-preset-btn').forEach(function(btn) {
        var match = btn.dataset.x === curX && btn.dataset.y === curY;
        btn.classList.toggle('active', match);
    });
}

/* Wire up scatter axis preset buttons */
function setupScatterPresets(redrawFn) {
    var container = document.getElementById('scatter-presets');
    if (!container) return;
    container.querySelectorAll('.scatter-preset-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var xSel = document.getElementById('scatter-x-metric');
            var ySel = document.getElementById('scatter-y-metric');
            if (!xSel || !ySel) return;
            xSel.value = btn.dataset.x;
            ySel.value = btn.dataset.y;
            _syncPresetActiveState();
            if (redrawFn) redrawFn();
        });
    });
}

/* Wire up Top 10 chart mode toggle buttons */
function setupTop10ModeToggle() {
    var toggleContainer = document.getElementById('top10-mode-toggle');
    if (!toggleContainer) return;
    toggleContainer.querySelectorAll('.top10-mode-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var mode = btn.dataset.mode;
            if (mode === _top10Mode) return; // already active
            _top10Mode = mode;
            // Update active button state
            toggleContainer.querySelectorAll('.top10-mode-btn').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            // Redraw chart with new mode
            drawTop10Chart(_chartData.companies, mode);
        });
    });
}

/* Debounced resize handler — clears and redraws all SVG charts */
/* Wire up trend chart overlay toggle buttons */
function setupTrendOverlayToggle() {
    var toggleContainer = document.getElementById('trend-overlay-toggle');
    if (!toggleContainer) return;
    toggleContainer.querySelectorAll('.trend-overlay-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            // CEO is always on, but toggle the others
            if (btn.dataset.series === 'ceo') return; // CEO always active
            // Indexed mode: when toggled on, auto-enable worker + ratio if not already
            if (btn.dataset.series === 'indexed') {
                btn.classList.toggle('active');
                if (btn.classList.contains('active')) {
                    toggleContainer.querySelectorAll('.trend-overlay-btn').forEach(function(b) {
                        if (b.dataset.series === 'worker' || b.dataset.series === 'ratio') {
                            b.classList.add('active');
                        }
                    });
                }
            } else {
                btn.classList.toggle('active');
            }
            // Redraw trend chart with new overlay state
            var el = document.getElementById('trend-chart');
            if (el) el.innerHTML = '';
            drawTrendChart(_chartData.trends);
        });
    });
}

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
    var ids = ['sector-chart', 'trend-chart', 'ratio-chart', 'comp-dist-chart', 'lorenz-chart', 'top10-chart', 'composition-chart', 'quartile-comp-chart', 'scatter-chart', 'yoy-dist-chart', 'gender-pay-chart', 'ceo-cfo-chart', 'sop-dist-chart', 'sop-scatter-chart', 'comp-treemap-chart', 'correlation-matrix-chart', 'cross-sector-corr-chart', 'conc-dist-chart', 'gov-dist-chart', 'sector-gov-chart', 'gov-quartile-comp-chart', 'gov-pay-scatter-chart', 'pay-anomaly-chart', 'tenure-pay-growth-chart', 'tenure-gov-crosstab-chart', 'ger-chart'];
    ids.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.innerHTML = '';
    });
    var narrativeEl = document.getElementById('gender-pay-narrative');
    if (narrativeEl) { narrativeEl.textContent = ''; narrativeEl.style.display = 'none'; }
    drawSectorChart(_chartData.trends, _chartData.companies);
    drawTrendChart(_chartData.trends);
    drawRatioChart(_chartData.companies);
    drawCompDistChart(_chartData.companies);
    drawLorenzChart(_chartData.companies);
    drawTop10Chart(_chartData.companies, _top10Mode);
    drawCompositionChart(_chartData.trends);
    drawQuartileComposition(_chartData.companies);
    drawScatterChart(_chartData.companies);
    drawYoYDistChart(_chartData.companies);
    drawGenderPayChart(_chartData.trends);
    drawCeoCfoChart(_chartData.companies);
    drawSopDistChart(_chartData.companies);
    drawConcDistChart(_chartData.companies);
    drawSopScatterChart(_chartData.companies);
    drawCompTreemap(_chartData.companies);
    drawCorrelationMatrix(_chartData.companies);
    drawCrossSectorCorrelation(_chartData.companies);
    drawGovDistChart(_chartData.companies);
    drawSectorGovChart(_chartData.companies);
    drawGovQuartileComp(_chartData.companies);
    drawGovPayScatter(_chartData.companies);
    drawPayAnomalyChart(_chartData.companies);
    drawTenurePayGrowthChart(_chartData.companies);
    drawTenureGovCrossTab(_chartData.companies);
    drawGERChart(_chartData.companies);
}

/* Redraw only sector-aware charts (comp dist + Lorenz) on sector filter change */
window._redrawSectorAwareCharts = function() {
    if (!_chartData) return;
    var sector = window._activeSector || null;
    // Update chart headers to reflect sector context
    var compTitle = document.getElementById('comp-dist-title');
    var compDesc = document.getElementById('comp-dist-desc');
    var lorenzTitle = document.getElementById('lorenz-title');
    var lorenzDesc = document.getElementById('lorenz-desc');
    if (compTitle) compTitle.textContent = sector
        ? sector + ' vs S&P 500 Compensation Distribution'
        : 'CEO Compensation Distribution';
    if (compDesc) compDesc.textContent = sector
        ? 'Comparing ' + sector + ' CEO pay distribution against the full S&P 500. Gray bars = index benchmark, colored bars = sector. Click a bucket to filter.'
        : 'Distribution of CEO total compensation across the S&P 500. Includes Gini coefficient measuring pay inequality. Click a bucket to filter the table.';
    if (lorenzTitle) lorenzTitle.textContent = sector
        ? sector + ' vs S&P 500 Lorenz Curve'
        : 'CEO Pay Lorenz Curve';
    if (lorenzDesc) lorenzDesc.textContent = sector
        ? 'Sector inequality (solid) overlaid on S&P 500 baseline (dashed). Gini delta shows whether the sector has more or less pay concentration than the index.'
        : 'Cumulative share of CEO compensation vs. cumulative share of companies. The gap between the curve and the diagonal (perfect equality) represents the Gini coefficient. Hover for precise percentile breakpoints.';
    // Redraw charts
    var el1 = document.getElementById('comp-dist-chart');
    if (el1) el1.innerHTML = '';
    drawCompDistChart(_chartData.companies);
    var el2 = document.getElementById('lorenz-chart');
    if (el2) el2.innerHTML = '';
    drawLorenzChart(_chartData.companies);
    // Redraw scatter chart (sector-aware)
    var el3 = document.getElementById('scatter-chart');
    if (el3) el3.innerHTML = '';
    drawScatterChart(_chartData.companies);
    // Redraw Top 10 chart (sector-aware)
    var el4 = document.getElementById('top10-chart');
    if (el4) el4.innerHTML = '';
    drawTop10Chart(_chartData.companies, _top10Mode);
    // Redraw correlation matrix (sector-aware)
    var el5 = document.getElementById('correlation-matrix-chart');
    if (el5) el5.innerHTML = '';
    drawCorrelationMatrix(_chartData.companies);
    // Redraw cross-sector correlation (highlights active sector bar)
    var el6 = document.getElementById('cross-sector-corr-chart');
    if (el6) el6.innerHTML = '';
    drawCrossSectorCorrelation(_chartData.companies);
    // Redraw quartile composition chart (sector-aware)
    var el7 = document.getElementById('quartile-comp-chart');
    if (el7) el7.innerHTML = '';
    drawQuartileComposition(_chartData.companies);
    // Redraw concentration distribution chart (sector-aware)
    var concTitle = document.getElementById('conc-dist-title');
    var concDesc = document.getElementById('conc-dist-desc');
    if (concTitle) concTitle.textContent = sector
        ? sector + ' vs S&P 500 CEO Pay Concentration'
        : 'CEO Pay Concentration';
    if (concDesc) concDesc.textContent = sector
        ? 'Comparing ' + sector + ' CEO pay concentration against the full S&P 500. Gray bars = index benchmark, colored bars = sector. Click a bucket to filter.'
        : 'CEO pay as a share of total Named Executive Officer compensation. Higher concentration means the CEO captures a larger slice of the executive pay pool. Click a bucket to filter the table.';
    var el8 = document.getElementById('conc-dist-chart');
    if (el8) el8.innerHTML = '';
    drawConcDistChart(_chartData.companies);
};

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

/* Update YoY distribution chart bar highlighting without full redraw */
window.highlightYoYBucket = function(minPct, maxPct) {
    d3.selectAll('#yoy-dist-chart .yoy-bar rect').each(function(d) {
        if (!d) return;
        if (minPct == null) {
            // Clear: restore all to default
            d3.select(this).attr('opacity', 0.8).attr('stroke', 'none');
        } else if (d.min === minPct && d.max === maxPct) {
            // Active bucket
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
        } else {
            // Inactive bucket
            d3.select(this).attr('opacity', 0.3).attr('stroke', 'none');
        }
    });
    d3.selectAll('#yoy-dist-chart .yoy-bar text').each(function(d) {
        if (!d) return;
        d3.select(this).attr('opacity', minPct == null || (d.min === minPct && d.max === maxPct) ? 1 : 0.4);
    });
};

/* Update SoP distribution chart bar highlighting without full redraw */
window.highlightSopDistBucket = function(minPct, maxPct) {
    d3.selectAll('#sop-dist-chart .sop-bar').each(function(d) {
        if (!d) return;
        if (minPct == null) {
            d3.select(this).attr('opacity', 0.8).attr('stroke', 'none');
        } else if (d.min === minPct && d.max === maxPct) {
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
        } else {
            d3.select(this).attr('opacity', 0.3).attr('stroke', 'none');
        }
    });
    d3.selectAll('#sop-dist-chart .sop-count-label').each(function(d) {
        if (!d) return;
        d3.select(this).attr('opacity', minPct == null || (d.min === minPct && d.max === maxPct) ? 1 : 0.4);
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
        { type: 'box', label: 'IQR (25th–75th) — click to filter', color: '#00b4d8', opacity: 0.18 },
        { type: 'whisker', label: 'Min–Max range — click to filter', color: '#00b4d8', opacity: 0.5 }
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

    // Clickable distribution hit zones — transparent rects over IQR and whisker regions
    var hitZoneG = svg.append('g').attr('class', 'dist-hit-zones');
    data.forEach(function(d) {
        if (!d._dist) return;
        var dist = d._dist;
        var cy = y(d.sector);
        var bh = y.bandwidth();
        var whiskerMax = Math.min(x(dist.max), w);

        // Left whisker zone: min → Q1 (bottom 25%)
        if (x(dist.q1) - x(dist.min) > 4) {
            hitZoneG.append('rect')
                .attr('class', 'dist-hit-zone')
                .attr('x', x(dist.min))
                .attr('y', cy)
                .attr('width', Math.max(x(dist.q1) - x(dist.min), 4))
                .attr('height', bh)
                .attr('fill', 'transparent')
                .style('cursor', 'pointer')
                .datum({ sector: d.sector, min: dist.min, max: dist.q1, label: d.sector + ': Bottom 25%', zone: 'bottom' })
                .on('mouseover', function(event, zd) {
                    d3.select(this).attr('fill', 'rgba(0,180,216,0.12)');
                    var html = '<div class="ct-title">' + zd.sector + ' — Bottom 25%</div>' +
                        '<div class="ct-row"><span class="ct-label">Range</span><span class="ct-val">' + fmtCurr(zd.min) + ' — ' + fmtCurr(zd.max) + '</span></div>' +
                        '<div class="ct-row ct-sub"><span class="ct-label">Click to filter table</span></div>';
                    showChartTooltip(event, html);
                })
                .on('mousemove', function(event) { positionChartTooltip(event); })
                .on('mouseout', function() {
                    d3.select(this).attr('fill', 'transparent');
                    hideChartTooltip();
                })
                .on('click', function(event, zd) {
                    event.stopPropagation();
                    if (window.filterByDistribution) window.filterByDistribution(zd.sector, zd.min, zd.max, zd.label);
                });
        }

        // IQR zone: Q1 → Q3 (middle 50%)
        hitZoneG.append('rect')
            .attr('class', 'dist-hit-zone')
            .attr('x', x(dist.q1))
            .attr('y', cy)
            .attr('width', Math.max(x(dist.q3) - x(dist.q1), 6))
            .attr('height', bh)
            .attr('fill', 'transparent')
            .style('cursor', 'pointer')
            .datum({ sector: d.sector, min: dist.q1, max: dist.q3, label: d.sector + ': IQR (25th–75th)', zone: 'iqr' })
            .on('mouseover', function(event, zd) {
                d3.select(this).attr('fill', 'rgba(0,180,216,0.15)');
                var html = '<div class="ct-title">' + zd.sector + ' — IQR (Middle 50%)</div>' +
                    '<div class="ct-row"><span class="ct-label">25th Percentile</span><span class="ct-val">' + fmtCurr(zd.min) + '</span></div>' +
                    '<div class="ct-row"><span class="ct-label">75th Percentile</span><span class="ct-val">' + fmtCurr(zd.max) + '</span></div>' +
                    '<div class="ct-row ct-sub"><span class="ct-label">Click to filter table</span></div>';
                showChartTooltip(event, html);
            })
            .on('mousemove', function(event) { positionChartTooltip(event); })
            .on('mouseout', function() {
                d3.select(this).attr('fill', 'transparent');
                hideChartTooltip();
            })
            .on('click', function(event, zd) {
                event.stopPropagation();
                if (window.filterByDistribution) window.filterByDistribution(zd.sector, zd.min, zd.max, zd.label);
            });

        // Right whisker zone: Q3 → max (top 25%)
        if (whiskerMax - x(dist.q3) > 4) {
            hitZoneG.append('rect')
                .attr('class', 'dist-hit-zone')
                .attr('x', x(dist.q3))
                .attr('y', cy)
                .attr('width', Math.max(whiskerMax - x(dist.q3), 4))
                .attr('height', bh)
                .attr('fill', 'transparent')
                .style('cursor', 'pointer')
                .datum({ sector: d.sector, min: dist.q3, max: dist.max, label: d.sector + ': Top 25%', zone: 'top' })
                .on('mouseover', function(event, zd) {
                    d3.select(this).attr('fill', 'rgba(0,180,216,0.12)');
                    var html = '<div class="ct-title">' + zd.sector + ' — Top 25%</div>' +
                        '<div class="ct-row"><span class="ct-label">Range</span><span class="ct-val">' + fmtCurr(zd.min) + ' — ' + fmtCurr(zd.max) + '</span></div>' +
                        '<div class="ct-row ct-sub"><span class="ct-label">Click to filter table</span></div>';
                    showChartTooltip(event, html);
                })
                .on('mousemove', function(event) { positionChartTooltip(event); })
                .on('mouseout', function() {
                    d3.select(this).attr('fill', 'transparent');
                    hideChartTooltip();
                })
                .on('click', function(event, zd) {
                    event.stopPropagation();
                    if (window.filterByDistribution) window.filterByDistribution(zd.sector, zd.min, zd.max, zd.label);
                });
        }
    });
}

/* --- Trend Line Chart --- */
function drawTrendChart(trends) {
    var container = document.getElementById('trend-chart');
    var ceoData = trends.median_ceo_pay_by_year && trends.median_ceo_pay_by_year.data
        ? trends.median_ceo_pay_by_year.data : [];
    var workerData = trends.median_worker_pay_by_year && trends.median_worker_pay_by_year.data
        ? trends.median_worker_pay_by_year.data : [];
    var ratioData = trends.pay_ratio_trend && trends.pay_ratio_trend.data
        ? trends.pay_ratio_trend.data : [];

    if (ceoData.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No trend data available</p>';
        return;
    }

    // Determine which series are active from toggle buttons
    var showCeo = true, showWorker = false, showRatio = false, isIndexed = false;
    var toggleBtns = document.querySelectorAll('.trend-overlay-btn');
    toggleBtns.forEach(function(btn) {
        if (btn.dataset.series === 'ceo') showCeo = btn.classList.contains('active');
        if (btn.dataset.series === 'worker') showWorker = btn.classList.contains('active');
        if (btn.dataset.series === 'ratio') showRatio = btn.classList.contains('active');
        if (btn.dataset.series === 'indexed') isIndexed = btn.classList.contains('active');
    });

    // Build lookup maps for worker pay and ratio by year
    var workerByYear = {};
    workerData.forEach(function(d) { workerByYear[d.year] = d; });
    var ratioByYear = {};
    ratioData.forEach(function(d) { ratioByYear[d.year] = d; });

    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
    var textColor = dark ? '#e4e4e7' : '#1a1a2e';
    var mutedColor = dark ? '#6b7280' : '#9ca3af';
    var bgColor = dark ? 'rgba(15,15,26,0.8)' : 'rgba(255,255,255,0.85)';
    var dotStroke = dark ? '#0f0f1a' : '#fff';

    // --- Indexed mode: compute base values and index all series to 100 ---
    var indexBaseYear = 2023; // Common base year where all 3 series have data
    var ceoBaseVal = null, workerBaseVal = null, ratioBaseVal = null;
    var ceoIndexed = [], workerIndexed = [], ratioIndexed = [];

    if (isIndexed && (showWorker || showRatio)) {
        // Find base values at indexBaseYear
        ceoData.forEach(function(d) { if (d.year === indexBaseYear) ceoBaseVal = d.median_pay; });
        workerData.forEach(function(d) { if (d.year === indexBaseYear) workerBaseVal = d.median_worker_pay; });
        ratioData.forEach(function(d) { if (d.year === indexBaseYear) ratioBaseVal = d.median_ratio; });

        if (ceoBaseVal) {
            ceoIndexed = ceoData.map(function(d) {
                return { year: d.year, value: (d.median_pay / ceoBaseVal) * 100, raw: d.median_pay, yoy_change: d.yoy_change };
            });
        }
        if (showWorker && workerBaseVal) {
            workerIndexed = workerData.map(function(d) {
                return { year: d.year, value: (d.median_worker_pay / workerBaseVal) * 100, raw: d.median_worker_pay, yoy_change: d.yoy_change };
            });
        }
        if (showRatio && ratioBaseVal) {
            ratioIndexed = ratioData.map(function(d) {
                return { year: d.year, value: (d.median_ratio / ratioBaseVal) * 100, raw: d.median_ratio, yoy_change: d.yoy_change };
            });
        }
    }

    var useIndexed = isIndexed && (showWorker || showRatio) && ceoBaseVal;

    var hasRightAxis = !useIndexed && (showWorker || showRatio);
    var hasDualRightAxis = !useIndexed && showWorker && showRatio;
    var margin = { top: 20, right: useIndexed ? 40 : hasDualRightAxis ? 120 : hasRightAxis ? 80 : 40, bottom: (showWorker || showRatio) ? 62 : 40, left: 70 };
    var w = container.clientWidth - margin.left - margin.right;
    var h = 280;

    // Compute global X domain across all visible series
    var allYears = ceoData.map(function(d) { return d.year; });
    if (showWorker) workerData.forEach(function(d) { if (allYears.indexOf(d.year) < 0) allYears.push(d.year); });
    if (showRatio) ratioData.forEach(function(d) { if (allYears.indexOf(d.year) < 0) allYears.push(d.year); });
    allYears.sort(function(a, b) { return a - b; });
    var yearMin = allYears[0], yearMax = allYears[allYears.length - 1];

    var svg = d3.select('#trend-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .attr('role', 'img')
        .attr('aria-label', 'S&P 500 compensation trend chart')
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleLinear().domain([yearMin, yearMax]).range([0, w]);

    // --- Y axes depend on indexed mode ---
    var y, yRight, yRatio;

    if (useIndexed) {
        // Single Y axis for indexed values
        var allIndexedVals = ceoIndexed.map(function(d) { return d.value; });
        if (workerIndexed.length) workerIndexed.forEach(function(d) { allIndexedVals.push(d.value); });
        if (ratioIndexed.length) ratioIndexed.forEach(function(d) { allIndexedVals.push(d.value); });
        var idxMin = d3.min(allIndexedVals) * 0.92;
        var idxMax = d3.max(allIndexedVals) * 1.08;
        y = d3.scaleLinear().domain([idxMin, idxMax]).range([h, 0]);
        yRight = null;
        yRatio = null;
    } else {
        // Left Y axis: CEO pay (always present for scale context)
        y = d3.scaleLinear()
            .domain([
                d3.min(ceoData, function(d) { return d.median_pay; }) * 0.9,
                d3.max(ceoData, function(d) { return d.median_pay; }) * 1.05
            ])
            .range([h, 0]);

        // Right Y axis: Worker pay
        yRight = null;
        if (showWorker && workerData.length > 0) {
            yRight = d3.scaleLinear()
                .domain([
                    d3.min(workerData, function(d) { return d.median_worker_pay; }) * 0.92,
                    d3.max(workerData, function(d) { return d.median_worker_pay; }) * 1.08
                ])
                .range([h, 0]);
        }
        yRatio = null;
        if (showRatio && ratioData.length > 0) {
            yRatio = d3.scaleLinear()
                .domain([
                    d3.min(ratioData, function(d) { return d.median_ratio; }) * 0.9,
                    d3.max(ratioData, function(d) { return d.median_ratio; }) * 1.1
                ])
                .range([h, 0]);
        }
    }

    // Grid
    svg.append('g').attr('class', 'grid')
        .call(d3.axisLeft(y).tickSize(-w).tickFormat('').ticks(5));

    // X axis
    var xTickYears = allYears.filter(function(yr) { return Number.isInteger(yr); });
    svg.append('g').attr('class', 'axis')
        .attr('transform', 'translate(0,' + h + ')')
        .call(d3.axisBottom(x).tickValues(xTickYears).tickFormat(d3.format('d')));

    // Left Y axis
    if (useIndexed) {
        svg.append('g').attr('class', 'axis')
            .call(d3.axisLeft(y).ticks(5).tickFormat(function(d) { return Math.round(d); }));
        // Base line at 100
        svg.append('line')
            .attr('x1', 0).attr('x2', w)
            .attr('y1', y(100)).attr('y2', y(100))
            .attr('stroke', '#a78bfa')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '4,3')
            .attr('opacity', 0.5);
        svg.append('text')
            .attr('x', w + 4).attr('y', y(100) + 4)
            .attr('fill', '#a78bfa')
            .attr('font-size', '9px')
            .attr('font-weight', '500')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('100');
        // Y axis label
        svg.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('x', -h / 2).attr('y', -56)
            .attr('text-anchor', 'middle')
            .attr('fill', '#a78bfa')
            .attr('font-size', '10px')
            .attr('font-weight', '500')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('Index (' + indexBaseYear + ' = 100)');
    } else {
        svg.append('g').attr('class', 'axis')
            .call(d3.axisLeft(y).ticks(5).tickFormat(function(d) { return fmtCurr(d); }));
        // Left Y axis label
        svg.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('x', -h / 2).attr('y', -56)
            .attr('text-anchor', 'middle')
            .attr('fill', '#00b4d8')
            .attr('font-size', '10px')
            .attr('font-weight', '500')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('CEO Median Pay');
    }

    // Right Y axes (only in non-indexed mode)
    if (!useIndexed) {
        if (showWorker && yRight) {
            svg.append('g').attr('class', 'axis')
                .attr('transform', 'translate(' + w + ',0)')
                .call(d3.axisRight(yRight).ticks(4).tickFormat(function(d) { return fmtCurr(d); }))
                .selectAll('text').attr('fill', '#06d6a0');

            svg.append('text')
                .attr('transform', 'rotate(90)')
                .attr('x', h / 2).attr('y', -w - 55)
                .attr('text-anchor', 'middle')
                .attr('fill', '#06d6a0')
                .attr('font-size', '10px')
                .attr('font-weight', '500')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .text('Worker Pay');
        }

        if (showRatio && yRatio) {
            var ratioAxisOffset = showWorker && yRight ? w + 40 : w;
            svg.append('g').attr('class', 'axis')
                .attr('transform', 'translate(' + ratioAxisOffset + ',0)')
                .call(d3.axisRight(yRatio).ticks(4).tickFormat(function(d) { return Math.round(d) + ':1'; }))
                .selectAll('text').attr('fill', '#ffd166');

            svg.append('text')
                .attr('transform', 'rotate(90)')
                .attr('x', h / 2).attr('y', -ratioAxisOffset - 55)
                .attr('text-anchor', 'middle')
                .attr('fill', '#ffd166')
                .attr('font-size', '10px')
                .attr('font-weight', '500')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .text('Pay Ratio');
        }
    }

    // --- Draw series ---
    var drawSeriesLine = function(data, yScale, color, dashArray, dotClass, dotR, areaFill) {
        if (areaFill) {
            var area = d3.area()
                .x(function(d) { return x(d.year); })
                .y0(h)
                .y1(function(d) { return yScale(d.value != null ? d.value : d.median_pay); })
                .curve(d3.curveMonotoneX);
            svg.append('path').datum(data).attr('fill', areaFill).attr('d', area);
        }
        var line = d3.line()
            .x(function(d) { return x(d.year); })
            .y(function(d) { return yScale(d.value != null ? d.value : d.median_pay); })
            .curve(d3.curveMonotoneX);
        svg.append('path').datum(data)
            .attr('fill', 'none')
            .attr('stroke', color)
            .attr('stroke-width', dashArray ? 2 : 2.5)
            .attr('stroke-dasharray', dashArray || 'none')
            .attr('d', line);
        svg.selectAll('.' + dotClass).data(data).join('circle')
            .attr('class', dotClass)
            .attr('cx', function(d) { return x(d.year); })
            .attr('cy', function(d) { return yScale(d.value != null ? d.value : d.median_pay); })
            .attr('r', dotR)
            .attr('fill', color)
            .attr('stroke', dotStroke)
            .attr('stroke-width', dotR > 3.5 ? 2 : 1.5)
            .style('cursor', 'pointer');
    };

    // CEO Pay series
    if (showCeo) {
        if (useIndexed) {
            drawSeriesLine(ceoIndexed, y, '#00b4d8', null, 'ceo-dot', 4, 'rgba(0,180,216,0.12)');
        } else {
            // Area fill
            var area = d3.area()
                .x(function(d) { return x(d.year); })
                .y0(h)
                .y1(function(d) { return y(d.median_pay); })
                .curve(d3.curveMonotoneX);
            svg.append('path').datum(ceoData).attr('fill', 'rgba(0,180,216,0.12)').attr('d', area);

            var ceoLine = d3.line()
                .x(function(d) { return x(d.year); })
                .y(function(d) { return y(d.median_pay); })
                .curve(d3.curveMonotoneX);
            svg.append('path').datum(ceoData)
                .attr('fill', 'none').attr('stroke', '#00b4d8').attr('stroke-width', 2.5).attr('d', ceoLine);
            svg.selectAll('.ceo-dot').data(ceoData).join('circle')
                .attr('class', 'ceo-dot')
                .attr('cx', function(d) { return x(d.year); })
                .attr('cy', function(d) { return y(d.median_pay); })
                .attr('r', 4).attr('fill', '#00b4d8').attr('stroke', dotStroke).attr('stroke-width', 2)
                .style('cursor', 'pointer');

            // Value labels (single series only)
            if (!showWorker && !showRatio) {
                svg.selectAll('.ceo-dot-label').data(ceoData).join('text')
                    .attr('class', 'bar-label')
                    .attr('x', function(d) { return x(d.year); })
                    .attr('y', function(d) { return y(d.median_pay) - 12; })
                    .attr('text-anchor', 'middle')
                    .text(function(d) { return fmtCurr(d.median_pay); });
            }
        }
    }

    // Worker Pay series
    if (showWorker && ((useIndexed && workerIndexed.length) || (!useIndexed && yRight && workerData.length))) {
        if (useIndexed) {
            drawSeriesLine(workerIndexed, y, '#06d6a0', '6,3', 'worker-dot', 3.5, 'rgba(6,214,160,0.08)');
        } else {
            var workerArea = d3.area()
                .x(function(d) { return x(d.year); })
                .y0(h)
                .y1(function(d) { return yRight(d.median_worker_pay); })
                .curve(d3.curveMonotoneX);
            svg.append('path').datum(workerData).attr('fill', 'rgba(6,214,160,0.08)').attr('d', workerArea);

            var workerLine = d3.line()
                .x(function(d) { return x(d.year); })
                .y(function(d) { return yRight(d.median_worker_pay); })
                .curve(d3.curveMonotoneX);
            svg.append('path').datum(workerData)
                .attr('fill', 'none').attr('stroke', '#06d6a0').attr('stroke-width', 2).attr('stroke-dasharray', '6,3').attr('d', workerLine);
            svg.selectAll('.worker-dot').data(workerData).join('circle')
                .attr('class', 'worker-dot')
                .attr('cx', function(d) { return x(d.year); })
                .attr('cy', function(d) { return yRight(d.median_worker_pay); })
                .attr('r', 3.5).attr('fill', '#06d6a0').attr('stroke', dotStroke).attr('stroke-width', 1.5)
                .style('cursor', 'pointer');
        }
    }

    // Pay Ratio series
    if (showRatio && ((useIndexed && ratioIndexed.length) || (!useIndexed && yRatio && ratioData.length))) {
        if (useIndexed) {
            drawSeriesLine(ratioIndexed, y, '#ffd166', '4,4', 'ratio-dot', 3.5, null);
        } else {
            var ratioLine = d3.line()
                .x(function(d) { return x(d.year); })
                .y(function(d) { return yRatio(d.median_ratio); })
                .curve(d3.curveMonotoneX);
            svg.append('path').datum(ratioData)
                .attr('fill', 'none').attr('stroke', '#ffd166').attr('stroke-width', 2).attr('stroke-dasharray', '4,4').attr('d', ratioLine);
            svg.selectAll('.ratio-dot').data(ratioData).join('circle')
                .attr('class', 'ratio-dot')
                .attr('cx', function(d) { return x(d.year); })
                .attr('cy', function(d) { return yRatio(d.median_ratio); })
                .attr('r', 3.5).attr('fill', '#ffd166').attr('stroke', dotStroke).attr('stroke-width', 1.5)
                .style('cursor', 'pointer');
        }
    }

    // --- Interactive hover overlay for combined tooltip ---
    var hoverLine = svg.append('line')
        .attr('y1', 0).attr('y2', h)
        .attr('stroke', mutedColor)
        .attr('stroke-width', 0.8)
        .attr('stroke-dasharray', '3,3')
        .attr('opacity', 0)
        .attr('pointer-events', 'none');

    svg.append('rect')
        .attr('width', w).attr('height', h)
        .attr('fill', 'transparent')
        .style('cursor', 'crosshair')
        .on('mousemove', function(event) {
            var mouseX = d3.pointer(event)[0];
            var yearVal = x.invert(mouseX);
            var nearestYear = Math.round(yearVal);
            if (nearestYear < yearMin || nearestYear > yearMax) {
                hoverLine.attr('opacity', 0);
                hideChartTooltip();
                return;
            }
            var snappedX = x(nearestYear);
            hoverLine.attr('x1', snappedX).attr('x2', snappedX).attr('opacity', 0.5);

            var html = '<div class="ct-title">FY ' + nearestYear + '</div>';
            var hasContent = false;

            if (useIndexed) {
                // Indexed mode tooltip
                var ceoIdxPt = ceoIndexed.find(function(d) { return d.year === nearestYear; });
                if (ceoIdxPt) {
                    html += '<div class="ct-row"><span class="ct-label" style="color:#00b4d8">\u25CF CEO Pay</span><span class="ct-val">' + ceoIdxPt.value.toFixed(1) + ' (' + fmtCurr(ceoIdxPt.raw) + ')</span></div>';
                    hasContent = true;
                }
                if (showWorker) {
                    var wIdxPt = workerIndexed.find(function(d) { return d.year === nearestYear; });
                    if (wIdxPt) {
                        html += '<div class="ct-row"><span class="ct-label" style="color:#06d6a0">\u25CF Worker Pay</span><span class="ct-val">' + wIdxPt.value.toFixed(1) + ' (' + fmtCurr(wIdxPt.raw) + ')</span></div>';
                        hasContent = true;
                    }
                }
                if (showRatio) {
                    var rIdxPt = ratioIndexed.find(function(d) { return d.year === nearestYear; });
                    if (rIdxPt) {
                        html += '<div class="ct-row"><span class="ct-label" style="color:#ffd166">\u25CF Pay Ratio</span><span class="ct-val">' + rIdxPt.value.toFixed(1) + ' (' + Math.round(rIdxPt.raw) + ':1)</span></div>';
                        hasContent = true;
                    }
                }
                html += '<div class="ct-row" style="border-top:1px solid rgba(255,255,255,0.1);margin-top:4px;padding-top:4px"><span class="ct-label" style="font-size:0.65rem;color:#a78bfa">Base: ' + indexBaseYear + ' = 100</span></div>';
            } else {
                // Normal mode tooltip
                if (showCeo) {
                    var ceoPt = ceoData.find(function(d) { return d.year === nearestYear; });
                    if (ceoPt) {
                        html += '<div class="ct-row"><span class="ct-label" style="color:#00b4d8">\u25CF CEO Median Pay</span><span class="ct-val">' + fmtCurr(ceoPt.median_pay) + '</span></div>';
                        if (ceoPt.yoy_change) {
                            var isNeg = ceoPt.yoy_change.indexOf('-') === 0;
                            var yoyColor = isNeg ? '#ef476f' : '#06d6a0';
                            html += '<div class="ct-row"><span class="ct-label" style="padding-left:12px;font-size:0.7rem">YoY</span><span class="ct-val" style="color:' + yoyColor + '">' + (isNeg ? '' : '+') + ceoPt.yoy_change + '</span></div>';
                        }
                        hasContent = true;
                    }
                }
                if (showWorker) {
                    var workerPt = workerByYear[nearestYear];
                    if (workerPt) {
                        html += '<div class="ct-row"><span class="ct-label" style="color:#06d6a0">\u25CF Worker Median Pay</span><span class="ct-val">' + fmtCurr(workerPt.median_worker_pay) + '</span></div>';
                        if (workerPt.yoy_change) {
                            var isNeg2 = workerPt.yoy_change.indexOf('-') === 0;
                            var yoyColor2 = isNeg2 ? '#ef476f' : '#06d6a0';
                            html += '<div class="ct-row"><span class="ct-label" style="padding-left:12px;font-size:0.7rem">YoY</span><span class="ct-val" style="color:' + yoyColor2 + '">' + (isNeg2 ? '' : '+') + workerPt.yoy_change + '</span></div>';
                        }
                        hasContent = true;
                    }
                }
                if (showRatio) {
                    var ratioPt = ratioByYear[nearestYear];
                    if (ratioPt) {
                        html += '<div class="ct-row"><span class="ct-label" style="color:#ffd166">\u25CF Pay Ratio</span><span class="ct-val">' + Math.round(ratioPt.median_ratio) + ':1</span></div>';
                        if (ratioPt.yoy_change) {
                            var isNeg3 = ratioPt.yoy_change.indexOf('-') === 0;
                            var yoyColor3 = isNeg3 ? '#ef476f' : '#06d6a0';
                            html += '<div class="ct-row"><span class="ct-label" style="padding-left:12px;font-size:0.7rem">YoY</span><span class="ct-val" style="color:' + yoyColor3 + '">' + (isNeg3 ? '' : '+') + ratioPt.yoy_change + '</span></div>';
                        }
                        hasContent = true;
                    }
                }
                // CEO-to-worker multiplier
                if (showCeo && showWorker) {
                    var ceoPt2 = ceoData.find(function(d) { return d.year === nearestYear; });
                    var workerPt2 = workerByYear[nearestYear];
                    if (ceoPt2 && workerPt2 && workerPt2.median_worker_pay > 0) {
                        var mult = (ceoPt2.median_pay / workerPt2.median_worker_pay).toFixed(0);
                        html += '<div class="ct-row" style="border-top:1px solid rgba(255,255,255,0.1);margin-top:4px;padding-top:4px"><span class="ct-label" style="font-size:0.7rem">CEO = ' + mult + '\u00D7 worker pay</span></div>';
                    }
                }
            }

            if (hasContent) {
                showChartTooltip(event, html);
            } else {
                hideChartTooltip();
            }

            // Highlight dots at this year
            svg.selectAll('.ceo-dot').attr('r', function(d) { return d.year === nearestYear ? 7 : 4; })
                .attr('stroke-width', function(d) { return d.year === nearestYear ? 3 : 2; });
            svg.selectAll('.worker-dot').attr('r', function(d) { return d.year === nearestYear ? 6 : 3.5; })
                .attr('stroke-width', function(d) { return d.year === nearestYear ? 2.5 : 1.5; });
            svg.selectAll('.ratio-dot').attr('r', function(d) { return d.year === nearestYear ? 6 : 3.5; })
                .attr('stroke-width', function(d) { return d.year === nearestYear ? 2.5 : 1.5; });
        })
        .on('mouseout', function() {
            hoverLine.attr('opacity', 0);
            hideChartTooltip();
            svg.selectAll('.ceo-dot').attr('r', 4).attr('stroke-width', 2);
            svg.selectAll('.worker-dot').attr('r', 3.5).attr('stroke-width', 1.5);
            svg.selectAll('.ratio-dot').attr('r', 3.5).attr('stroke-width', 1.5);
        });

    // YoY growth annotations (only when single CEO series, non-indexed)
    if (showCeo && !showWorker && !showRatio && !useIndexed) {
        var yoyPairs = [];
        for (var i = 1; i < ceoData.length; i++) {
            if (ceoData[i].yoy_change) {
                yoyPairs.push({
                    fromYear: ceoData[i - 1].year,
                    toYear: ceoData[i].year,
                    fromPay: ceoData[i - 1].median_pay,
                    toPay: ceoData[i].median_pay,
                    change: ceoData[i].yoy_change
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
            var arrow = isNeg ? '\u25BC' : '\u25B2';
            var labelY = midY + 22;

            var annGroup = yoyGroup.append('g');
            var textNode = annGroup.append('text')
                .attr('x', midX).attr('y', labelY)
                .attr('text-anchor', 'middle')
                .attr('font-size', '9.5px')
                .attr('font-weight', '600')
                .attr('font-family', 'JetBrains Mono, monospace')
                .attr('fill', labelColor)
                .text(arrow + ' ' + labelText);

            var bbox = textNode.node().getBBox();
            var padX = 5, padY = 2;
            annGroup.insert('rect', 'text')
                .attr('x', bbox.x - padX).attr('y', bbox.y - padY)
                .attr('width', bbox.width + padX * 2)
                .attr('height', bbox.height + padY * 2)
                .attr('rx', 6)
                .attr('fill', bgColor);
        });
    }

    // --- Growth rate summary + narrative annotations (multi-series or indexed) ---
    if ((showCeo && (showWorker || showRatio)) && ceoData.length >= 2) {
        var summaryParts = [];
        var ceoFirst = ceoData[0], ceoLast = ceoData[ceoData.length - 1];
        var ceoGrowthPct = ((ceoLast.median_pay - ceoFirst.median_pay) / ceoFirst.median_pay * 100);
        summaryParts.push({ label: 'CEO', color: '#00b4d8', val: '+' + ceoGrowthPct.toFixed(1) + '% (' + ceoFirst.year + '\u2013' + ceoLast.year + ')', growth: ceoGrowthPct, years: ceoLast.year - ceoFirst.year });

        var workerGrowthPct = null, workerYears = null;
        if (showWorker && workerData.length >= 2) {
            var wFirst = workerData[0], wLast = workerData[workerData.length - 1];
            workerGrowthPct = ((wLast.median_worker_pay - wFirst.median_worker_pay) / wFirst.median_worker_pay * 100);
            workerYears = wLast.year - wFirst.year;
            summaryParts.push({ label: 'Worker', color: '#06d6a0', val: '+' + workerGrowthPct.toFixed(1) + '% (' + wFirst.year + '\u2013' + wLast.year + ')', growth: workerGrowthPct, years: workerYears });
        }

        var ratioGrowthPct = null;
        if (showRatio && ratioData.length >= 2) {
            var rFirst = ratioData[0], rLast = ratioData[ratioData.length - 1];
            ratioGrowthPct = ((rLast.median_ratio - rFirst.median_ratio) / rFirst.median_ratio * 100);
            summaryParts.push({ label: 'Ratio', color: '#ffd166', val: '+' + ratioGrowthPct.toFixed(1) + '% (' + rFirst.year + '\u2013' + rLast.year + ')', growth: ratioGrowthPct });
        }

        // Growth summary in top-right
        summaryParts.forEach(function(sp, idx) {
            svg.append('text')
                .attr('x', w - 6)
                .attr('y', 12 + idx * 16)
                .attr('text-anchor', 'end')
                .attr('fill', sp.color)
                .attr('font-size', '10px')
                .attr('font-weight', '600')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .text(sp.label + ': ' + sp.val);
        });

        // --- Narrative annotation callout (bottom of chart area) ---
        var narrativeParts = [];

        // CEO vs Worker growth comparison
        if (showWorker && workerGrowthPct != null && workerYears != null) {
            // Annualize for comparable rates (different date ranges)
            var ceoAnnual = ceoGrowthPct / (ceoLast.year - ceoFirst.year);
            var workerAnnual = workerGrowthPct / workerYears;
            if (workerAnnual > 0) {
                var growthMultiple = (ceoAnnual / workerAnnual).toFixed(1);
                if (parseFloat(growthMultiple) > 1.2) {
                    narrativeParts.push('CEO pay growing ' + growthMultiple + '\u00D7 faster than worker pay (annualized)');
                } else if (parseFloat(growthMultiple) < 0.8) {
                    narrativeParts.push('Worker pay outpacing CEO pay growth (annualized)');
                }
            }
        }

        // Ratio trend narrative
        if (showRatio && ratioGrowthPct != null) {
            var rFirst2 = ratioData[0], rLast2 = ratioData[ratioData.length - 1];
            if (rLast2.median_ratio >= 200) {
                narrativeParts.push('Pay ratio crossed 200:1 \u2014 highest on record');
            } else if (ratioGrowthPct > 15) {
                narrativeParts.push('Pay ratio up ' + ratioGrowthPct.toFixed(0) + '% since ' + rFirst2.year);
            }
        }

        // Render narrative annotation below the chart
        if (narrativeParts.length > 0) {
            var narrativeText = narrativeParts.join(' · ');
            var narrativeY = h + 40;
            var narGroup = svg.append('g').attr('class', 'narrative-annotation');

            var narTextNode = narGroup.append('text')
                .attr('x', w / 2)
                .attr('y', narrativeY)
                .attr('text-anchor', 'middle')
                .attr('fill', dark ? '#a78bfa' : '#6d28d9')
                .attr('font-size', '10px')
                .attr('font-weight', '500')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .text(narrativeText);

            // Background pill behind text
            var narBbox = narTextNode.node().getBBox();
            var narPadX = 10, narPadY = 4;
            narGroup.insert('rect', 'text')
                .attr('x', narBbox.x - narPadX)
                .attr('y', narBbox.y - narPadY)
                .attr('width', narBbox.width + narPadX * 2)
                .attr('height', narBbox.height + narPadY * 2)
                .attr('rx', 8)
                .attr('fill', dark ? 'rgba(167,139,250,0.1)' : 'rgba(109,40,217,0.06)')
                .attr('stroke', dark ? 'rgba(167,139,250,0.25)' : 'rgba(109,40,217,0.15)')
                .attr('stroke-width', 1);
        }
    }

    // --- Inline legend ---
    if (showWorker || showRatio) {
        var legY = h + 28;
        var legX = 0;
        var legItems = [];
        if (showCeo) legItems.push({ label: useIndexed ? 'CEO Pay (indexed)' : 'CEO Median Pay', color: '#00b4d8', dash: null });
        if (showWorker) legItems.push({ label: useIndexed ? 'Worker Pay (indexed)' : 'Worker Median Pay', color: '#06d6a0', dash: '6,3' });
        if (showRatio) legItems.push({ label: useIndexed ? 'Pay Ratio (indexed)' : 'Pay Ratio', color: '#ffd166', dash: '4,4' });

        legItems.forEach(function(item, idx) {
            var lx = legX + idx * 160;
            svg.append('line')
                .attr('x1', lx).attr('x2', lx + 20)
                .attr('y1', legY).attr('y2', legY)
                .attr('stroke', item.color)
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', item.dash || 'none');
            svg.append('text')
                .attr('x', lx + 25).attr('y', legY + 4)
                .attr('fill', textColor)
                .attr('font-size', '9px')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .text(item.label);
        });
    }

    // Update chart title and description dynamically
    var titleEl = document.getElementById('trend-title');
    var descEl = document.getElementById('trend-desc');
    if (titleEl) {
        var seriesNames = ['CEO Pay'];
        if (showWorker) seriesNames.push('Worker Pay');
        if (showRatio) seriesNames.push('Pay Ratio');
        var modeLabel = useIndexed ? ' (Indexed to ' + indexBaseYear + ')' : '';
        titleEl.textContent = seriesNames.length > 1
            ? 'Compensation Trends: ' + seriesNames.join(' + ') + modeLabel
            : 'Median CEO Pay Trend';
    }
    if (descEl) {
        if (useIndexed) {
            descEl.textContent = 'All series indexed to 100 at ' + indexBaseYear + ', making growth rates directly comparable on a single axis regardless of scale differences.';
        } else if (showWorker || showRatio) {
            var parts = ['S\u0026P 500 median CEO total compensation (2020\u20132025)'];
            if (showWorker) parts.push('median worker pay (2023\u20132025)');
            if (showRatio) parts.push('CEO-to-worker pay ratio (2018\u20132025)');
            descEl.textContent = parts.join(', ') + '. Toggle series to compare growth trajectories.';
        } else {
            descEl.textContent = 'S\u0026P 500 median CEO total compensation, 2020\u20132025';
        }
    }
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
/* Top 10 chart mode state */
var _top10Mode = 'comp';

/* Mode definitions for the multi-mode Top 10 chart */
var TOP10_MODES = {
    comp: {
        title: 'Top 10 Highest Paid CEOs',
        desc: 'FY 2024 total compensation from proxy statements',
        filter: function(c) { return c.total_compensation > 0; },
        sort: function(a, b) { return b.total_compensation - a.total_compensation; },
        value: function(c) { return c.total_compensation; },
        label: function(c) { return c.ceo_name || c.ticker; },
        format: function(v) { return fmtCurr(v); },
        xLabel: 'Total Compensation',
        colors: ['#00b4d8', '#0096c7', '#0077b6', '#023e8a', '#03045e', '#1b263b', '#415a77', '#778da9', '#94a3b8', '#94a3b8'],
        tooltipExtra: function(d) {
            var html = '';
            if (d.pay_ratio) html += '<div class="ct-row"><span class="ct-label">Pay Ratio</span><span class="ct-val">' + d.pay_ratio.toLocaleString() + ':1</span></div>';
            return html;
        }
    },
    ratio: {
        title: 'Top 10 Highest Pay Ratios',
        desc: 'CEO-to-median-worker pay ratio — highest inequality gap',
        filter: function(c) { return c.pay_ratio != null && c.pay_ratio > 0; },
        sort: function(a, b) { return b.pay_ratio - a.pay_ratio; },
        value: function(c) { return c.pay_ratio; },
        label: function(c) { return c.ceo_name || c.ticker; },
        format: function(v) { return Math.round(v).toLocaleString() + ':1'; },
        xLabel: 'CEO-to-Worker Pay Ratio',
        colors: ['#ef476f', '#e5383b', '#d90429', '#c1121f', '#a4133c', '#780000', '#6a040f', '#520309', '#3d0208', '#3d0208'],
        tooltipExtra: function(d) {
            var html = '<div class="ct-row"><span class="ct-label">Total Comp</span><span class="ct-val">' + fmtCurr(d.total_compensation) + '</span></div>';
            if (d.median_worker_pay) html += '<div class="ct-row"><span class="ct-label">Worker Pay</span><span class="ct-val">' + fmtCurr(d.median_worker_pay) + '</span></div>';
            return html;
        }
    },
    raise: {
        title: 'Top 10 Biggest CEO Raises',
        desc: 'Largest year-over-year CEO compensation increases',
        filter: function(c) { return c._ceoYoY && c._ceoYoY.pct > 0; },
        sort: function(a, b) { return b._ceoYoY.pct - a._ceoYoY.pct; },
        value: function(c) { return c._ceoYoY.pct; },
        label: function(c) { return c.ceo_name || c.ticker; },
        format: function(v) { return '+' + (Math.abs(v) >= 100 ? Math.round(v) : v.toFixed(1)) + '%'; },
        xLabel: 'Year-over-Year Change (%)',
        colors: ['#06d6a0', '#05c48e', '#04b27c', '#03a06a', '#028e58', '#027c46', '#016a34', '#015822', '#014610', '#013400'],
        tooltipExtra: function(d) {
            var html = '<div class="ct-row"><span class="ct-label">Total Comp</span><span class="ct-val">' + fmtCurr(d.total_compensation) + '</span></div>';
            if (d._ceoYoY) html += '<div class="ct-row"><span class="ct-label">From</span><span class="ct-val">FY' + d._ceoYoY.fromYear + ': ' + fmtCurr(d._ceoYoY.fromComp) + '</span></div>';
            if (d._ceoYoY) html += '<div class="ct-row"><span class="ct-label">To</span><span class="ct-val">FY' + d._ceoYoY.toYear + ': ' + fmtCurr(d._ceoYoY.toComp) + '</span></div>';
            return html;
        }
    },
    cut: {
        title: 'Top 10 Biggest CEO Pay Cuts',
        desc: 'Largest year-over-year CEO compensation decreases',
        filter: function(c) { return c._ceoYoY && c._ceoYoY.pct < 0; },
        sort: function(a, b) { return a._ceoYoY.pct - b._ceoYoY.pct; },
        value: function(c) { return Math.abs(c._ceoYoY.pct); },
        rawValue: function(c) { return c._ceoYoY.pct; },
        label: function(c) { return c.ceo_name || c.ticker; },
        format: function(v, d) { var raw = d && d._ceoYoY ? d._ceoYoY.pct : -v; return (Math.abs(raw) >= 100 ? Math.round(raw) : raw.toFixed(1)) + '%'; },
        xLabel: 'Year-over-Year Change (%)',
        colors: ['#ef476f', '#e5383b', '#d90429', '#c1121f', '#a4133c', '#780000', '#6a040f', '#520309', '#3d0208', '#3d0208'],
        tooltipExtra: function(d) {
            var html = '<div class="ct-row"><span class="ct-label">Total Comp</span><span class="ct-val">' + fmtCurr(d.total_compensation) + '</span></div>';
            if (d._ceoYoY) html += '<div class="ct-row"><span class="ct-label">From</span><span class="ct-val">FY' + d._ceoYoY.fromYear + ': ' + fmtCurr(d._ceoYoY.fromComp) + '</span></div>';
            if (d._ceoYoY) html += '<div class="ct-row"><span class="ct-label">To</span><span class="ct-val">FY' + d._ceoYoY.toYear + ': ' + fmtCurr(d._ceoYoY.toComp) + '</span></div>';
            return html;
        }
    },
    worker: {
        title: 'Top 10 Highest Median Worker Pay',
        desc: 'Companies with the best-paid median workers',
        filter: function(c) { return c.median_worker_pay != null && c.median_worker_pay > 0; },
        sort: function(a, b) { return b.median_worker_pay - a.median_worker_pay; },
        value: function(c) { return c.median_worker_pay; },
        label: function(c) { return (c.company_name || c.ticker).length > 20 ? c.ticker : (c.company_name || c.ticker); },
        format: function(v) { return fmtCurr(v); },
        xLabel: 'Median Worker Pay',
        colors: ['#a78bfa', '#9575f6', '#835ff2', '#7149ee', '#5f33ea', '#4d1de6', '#3b07e2', '#3206c2', '#2905a2', '#200482'],
        tooltipExtra: function(d) {
            var html = '<div class="ct-row"><span class="ct-label">CEO Comp</span><span class="ct-val">' + fmtCurr(d.total_compensation) + '</span></div>';
            if (d.pay_ratio) html += '<div class="ct-row"><span class="ct-label">Pay Ratio</span><span class="ct-val">' + d.pay_ratio.toLocaleString() + ':1</span></div>';
            html += '<div class="ct-row"><span class="ct-label">CEO</span><span class="ct-val">' + (d.ceo_name || '—') + '</span></div>';
            return html;
        }
    },
    sop: {
        title: 'Top 10 Lowest Say-on-Pay Approval',
        desc: 'Companies with the most shareholder resistance to executive compensation',
        filter: function(c) { return c._sopApproval != null; },
        sort: function(a, b) { return a._sopApproval - b._sopApproval; },
        value: function(c) { return c._sopApproval; },
        label: function(c) { return c.ceo_name || c.ticker; },
        format: function(v) { return v.toFixed(1) + '%'; },
        xLabel: 'Shareholder Approval (%)',
        colors: ['#ef476f', '#e5383b', '#d90429', '#c1121f', '#fb923c', '#f59e0b', '#fbbf24', '#fcd34d', '#fde68a', '#fef3c7'],
        tooltipExtra: function(d) {
            var html = '<div class="ct-row"><span class="ct-label">Total Comp</span><span class="ct-val">' + fmtCurr(d.total_compensation) + '</span></div>';
            if (d.pay_ratio) html += '<div class="ct-row"><span class="ct-label">Pay Ratio</span><span class="ct-val">' + d.pay_ratio.toLocaleString() + ':1</span></div>';
            if (d.say_on_pay && d.say_on_pay.filing_date) html += '<div class="ct-row"><span class="ct-label">Filed</span><span class="ct-val">' + d.say_on_pay.filing_date + '</span></div>';
            var sopLabel = d._sopApproval < 50 ? 'Failed' : d._sopApproval < 70 ? 'Significant opposition' : d._sopApproval < 85 ? 'Below average' : 'Passed';
            html += '<div class="ct-row"><span class="ct-label">Status</span><span class="ct-val" style="color:' + (d._sopApproval < 70 ? '#ef476f' : d._sopApproval < 85 ? '#fbbf24' : '#06d6a0') + '">' + sopLabel + '</span></div>';
            return html;
        }
    }
};

function drawTop10Chart(companies, mode) {
    var container = document.getElementById('top10-chart');
    if (!container) return;
    container.innerHTML = '';

    mode = mode || _top10Mode || 'comp';
    var cfg = TOP10_MODES[mode];
    if (!cfg) return;

    // Sector-aware filtering: when a sector is active, show that sector's top companies
    var sectorName = window._activeSector || null;
    var sectorFilteredCompanies = sectorName
        ? companies.filter(function(c) { return c.sector === sectorName; })
        : companies;
    var sectorColor = sectorName && typeof getSectorColor === 'function' ? getSectorColor(sectorName) : null;

    // Build sector-aware title and description
    var sectorAbbr = sectorName
        ? sectorName.replace('Information Technology', 'IT')
            .replace('Communication Services', 'Comm Svcs')
            .replace('Consumer Discretionary', 'Consumer Disc')
            .replace('Consumer Staples', 'Consumer Stpls')
            .replace('Health Care', 'Health Care')
        : null;

    // Update title and description
    var titleEl = document.getElementById('top10-title');
    var descEl = document.getElementById('top10-desc');
    if (titleEl) titleEl.textContent = sectorName
        ? cfg.title.replace('Top 10', 'Top ' + sectorAbbr)
        : cfg.title;
    if (descEl) descEl.textContent = sectorName
        ? cfg.desc + ' — ' + sectorName + ' sector (' + sectorFilteredCompanies.length + ' companies)'
        : cfg.desc;

    // Get and sort data
    var filtered = sectorFilteredCompanies.filter(cfg.filter);
    if (filtered.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No data available' + (sectorName ? ' for ' + sectorName : '') + '</p>';
        return;
    }
    filtered.sort(cfg.sort);
    var showCount = Math.min(10, filtered.length);
    var top10 = filtered.slice(0, showCount);

    // Also get S&P 500 overall #1 for reference line when in sector mode
    var sp500Top1 = null;
    if (sectorName) {
        var sp500Filtered = companies.filter(cfg.filter);
        sp500Filtered.sort(cfg.sort);
        if (sp500Filtered.length > 0) sp500Top1 = sp500Filtered[0];
    }

    var margin = { top: 20, right: 100, bottom: 30, left: 140 };
    var w = container.clientWidth - margin.left - margin.right;
    var barAreaH = Math.max(200, showCount * 32);
    var h = Math.min(barAreaH, 320);

    var svg = d3.select('#top10-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var maxVal = d3.max(top10, function(d) { return cfg.value(d); });
    // When in sector mode, extend x-domain to include S&P 500 #1 so reference line is visible
    var xMax = maxVal;
    if (sp500Top1) {
        var sp500Val = cfg.value(sp500Top1);
        if (sp500Val > xMax) xMax = sp500Val;
    }
    var x = d3.scaleLinear()
        .domain([0, xMax * 1.05])
        .range([0, w]);

    var y = d3.scaleBand()
        .domain(top10.map(function(d) { return cfg.label(d); }))
        .range([0, h])
        .padding(0.3);

    // Grid
    svg.append('g').attr('class', 'grid')
        .call(d3.axisBottom(x).tickSize(h).tickFormat('').ticks(5));

    // Y axis — truncate long names
    svg.append('g').attr('class', 'axis')
        .call(d3.axisLeft(y).tickSize(0).tickPadding(8).tickFormat(function(name) {
            return name.length > 18 ? name.substring(0, 16) + '…' : name;
        }));

    // X axis label
    svg.append('text')
        .attr('class', 'axis-label')
        .attr('x', w / 2)
        .attr('y', h + 28)
        .attr('text-anchor', 'middle')
        .attr('fill', typeof getThemeSecondaryColor === 'function' ? getThemeSecondaryColor() : '#a1a1aa')
        .attr('font-size', '10px')
        .text(cfg.xLabel);

    // Bars — use sector color when sector-filtered, otherwise mode gradient
    var colors = cfg.colors;
    var useSectorColors = !!sectorName;
    svg.selectAll('.top-bar')
        .data(top10)
        .join('rect')
        .attr('x', 0)
        .attr('y', function(d) { return y(cfg.label(d)); })
        .attr('width', function(d) { return Math.max(2, x(cfg.value(d))); })
        .attr('height', y.bandwidth())
        .attr('fill', function(d, i) {
            if (useSectorColors && sectorColor) {
                // Gradient effect: first bar full opacity, later bars slightly faded
                return sectorColor;
            }
            return colors[Math.min(i, colors.length - 1)];
        })
        .attr('rx', 3)
        .attr('opacity', function(d, i) {
            if (useSectorColors) return 0.95 - (i * 0.05);
            return 0.85;
        })
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1);
            // Dim other bars
            svg.selectAll('.top-bar').filter(function(o) { return o !== d; }).attr('opacity', 0.35);
            var rank = top10.indexOf(d) + 1;
            var html = '<div class="ct-title">#' + rank + (sectorName ? ' in ' + sectorAbbr : '') + ' ' + (d.ceo_name || d.ticker) + '</div>';
            html += '<div class="ct-row"><span class="ct-label">Company</span><span class="ct-val">' + d.ticker + ' — ' + (d.company_name || '') + '</span></div>';
            html += '<div class="ct-row"><span class="ct-label">' + cfg.xLabel + '</span><span class="ct-val">' + cfg.format(cfg.value(d), d) + '</span></div>';
            html += cfg.tooltipExtra(d);
            if (d.sector) html += '<div class="ct-row"><span class="ct-label">Sector</span><span class="ct-val">' + d.sector + '</span></div>';
            // Show S&P 500 rank when in sector mode
            if (sectorName) {
                var sp500All = companies.filter(cfg.filter);
                sp500All.sort(cfg.sort);
                var sp500Rank = sp500All.findIndex(function(c) { return c.ticker === d.ticker; }) + 1;
                if (sp500Rank > 0) {
                    html += '<div class="ct-row"><span class="ct-label">S&P 500 Rank</span><span class="ct-val">#' + sp500Rank + ' of ' + sp500All.length + '</span></div>';
                }
            }
            html += '<div class="ct-row ct-sub"><span class="ct-label">Click to find in table</span></div>';
            showChartTooltip(event, html);
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function() {
            svg.selectAll('.top-bar').each(function(d, i) {
                d3.select(this).attr('opacity', useSectorColors ? 0.95 - (i * 0.05) : 0.85);
            });
            d3.select(this).attr('stroke', 'none');
            hideChartTooltip();
        })
        .on('click', function(event, d) {
            if (window.findCompanyInTable) window.findCompanyInTable(d.ticker);
        });

    // Ticker labels on bars (small, inside or next to bar)
    svg.selectAll('.top-ticker')
        .data(top10)
        .join('text')
        .attr('class', 'bar-label')
        .attr('x', function(d) {
            var barW = x(cfg.value(d));
            return barW > 60 ? barW - 6 : barW + 4;
        })
        .attr('y', function(d) { return y(cfg.label(d)) + y.bandwidth() * 0.35; })
        .attr('text-anchor', function(d) { return x(cfg.value(d)) > 60 ? 'end' : 'start'; })
        .attr('fill', function(d) {
            return x(cfg.value(d)) > 60
                ? (typeof isDarkTheme === 'function' && isDarkTheme() ? '#e4e4e7' : '#ffffff')
                : (typeof getThemeTextColor === 'function' ? getThemeTextColor() : '#e4e4e7');
        })
        .attr('font-size', '9px')
        .attr('opacity', 0.7)
        .text(function(d) { return d.ticker; });

    // Value labels
    svg.selectAll('.top-label')
        .data(top10)
        .join('text')
        .attr('class', 'bar-label')
        .attr('x', function(d) { return x(cfg.value(d)) + 6; })
        .attr('y', function(d) { return y(cfg.label(d)) + y.bandwidth() * 0.7; })
        .attr('dy', '0.1em')
        .text(function(d) { return cfg.format(cfg.value(d), d); });

    // Median reference line (for comp and worker modes)
    if (mode === 'comp' || mode === 'worker' || mode === 'ratio' || mode === 'sop') {
        // When sector-filtered, show sector median; always show S&P 500 median
        var sp500Vals = companies.filter(cfg.filter).map(function(c) { return cfg.value(c); }).sort(function(a, b) { return a - b; });
        if (sp500Vals.length > 0) {
            var sp500MedIdx = Math.floor(sp500Vals.length / 2);
            var sp500MedVal = sp500Vals.length % 2 === 0 ? (sp500Vals[sp500MedIdx - 1] + sp500Vals[sp500MedIdx]) / 2 : sp500Vals[sp500MedIdx];

            if (sectorName) {
                // Show sector median as primary line
                var sectorVals = filtered.map(function(c) { return cfg.value(c); }).sort(function(a, b) { return a - b; });
                if (sectorVals.length > 0) {
                    var secMedIdx = Math.floor(sectorVals.length / 2);
                    var secMedVal = sectorVals.length % 2 === 0 ? (sectorVals[secMedIdx - 1] + sectorVals[secMedIdx]) / 2 : sectorVals[secMedIdx];
                    if (secMedVal > 0 && x(secMedVal) > 20 && x(secMedVal) < w - 20) {
                        svg.append('line')
                            .attr('x1', x(secMedVal)).attr('x2', x(secMedVal))
                            .attr('y1', 0).attr('y2', h)
                            .attr('stroke', sectorColor).attr('stroke-width', 1.5)
                            .attr('stroke-dasharray', '6,4').attr('opacity', 0.7);
                        svg.append('text')
                            .attr('x', x(secMedVal) + 4).attr('y', -4)
                            .attr('fill', sectorColor).attr('font-size', '9px').attr('opacity', 0.9)
                            .text(sectorAbbr + ' Median: ' + cfg.format(secMedVal));
                    }
                }
                // Show S&P 500 median as secondary dashed line
                if (sp500MedVal > 0 && x(sp500MedVal) > 20 && x(sp500MedVal) < w - 20) {
                    svg.append('line')
                        .attr('x1', x(sp500MedVal)).attr('x2', x(sp500MedVal))
                        .attr('y1', 0).attr('y2', h)
                        .attr('stroke', '#ffd166').attr('stroke-width', 1)
                        .attr('stroke-dasharray', '3,3').attr('opacity', 0.4);
                    svg.append('text')
                        .attr('x', x(sp500MedVal) + 4).attr('y', h - 4)
                        .attr('fill', '#ffd166').attr('font-size', '8px').attr('opacity', 0.5)
                        .text('S&P 500 Median');
                }
            } else {
                // Standard: show S&P 500 median
                if (sp500MedVal > 0 && sp500MedVal < maxVal) {
                    svg.append('line')
                        .attr('x1', x(sp500MedVal)).attr('x2', x(sp500MedVal))
                        .attr('y1', 0).attr('y2', h)
                        .attr('stroke', '#ffd166').attr('stroke-width', 1)
                        .attr('stroke-dasharray', '6,4').attr('opacity', 0.6);
                    svg.append('text')
                        .attr('x', x(sp500MedVal) + 4).attr('y', -4)
                        .attr('fill', '#ffd166').attr('font-size', '9px').attr('opacity', 0.8)
                        .text('S&P 500 Median: ' + cfg.format(sp500MedVal));
                }
            }
        }
    }

    // S&P 500 #1 reference line — when in sector mode, show where the S&P 500 leader sits
    if (sectorName && sp500Top1) {
        var sp500TopVal = cfg.value(sp500Top1);
        // Only show if the S&P 500 #1 is not already in the sector list
        var sp500TopInSector = top10.some(function(d) { return d.ticker === sp500Top1.ticker; });
        if (!sp500TopInSector && sp500TopVal > 0 && x(sp500TopVal) > 20 && x(sp500TopVal) < w + margin.right - 10) {
            svg.append('line')
                .attr('x1', x(sp500TopVal)).attr('x2', x(sp500TopVal))
                .attr('y1', -8).attr('y2', h + 4)
                .attr('stroke', '#ef476f').attr('stroke-width', 1)
                .attr('stroke-dasharray', '4,3').attr('opacity', 0.5);
            svg.append('text')
                .attr('x', x(sp500TopVal) - 4).attr('y', -4)
                .attr('text-anchor', 'end')
                .attr('fill', '#ef476f').attr('font-size', '8px').attr('opacity', 0.7)
                .text('S&P 500 #1: ' + sp500Top1.ticker + ' ' + cfg.format(sp500TopVal, sp500Top1));
        }
    }

    // SoP-specific threshold lines — failure (50%) and significant opposition (70%)
    if (mode === 'sop') {
        var sopThresholds = [
            { val: 50, label: 'Failed', color: '#ef476f', dash: '6,3', yOff: 14 },
            { val: 70, label: 'Opposition', color: '#fbbf24', dash: '4,4', yOff: 28 },
            { val: 85, label: 'Below avg', color: '#94a3b8', dash: '3,3', yOff: 14 }
        ];
        sopThresholds.forEach(function(t) {
            var xPos = x(t.val);
            if (xPos > 20 && xPos < w - 10) {
                svg.append('line')
                    .attr('x1', xPos).attr('x2', xPos)
                    .attr('y1', -4).attr('y2', h + 4)
                    .attr('stroke', t.color).attr('stroke-width', 1.5)
                    .attr('stroke-dasharray', t.dash).attr('opacity', 0.5);
                svg.append('text')
                    .attr('x', xPos - 3).attr('y', t.yOff)
                    .attr('text-anchor', 'end')
                    .attr('fill', t.color).attr('font-size', '8px').attr('font-weight', '600').attr('opacity', 0.8)
                    .text(t.val + '%');
                svg.append('text')
                    .attr('x', xPos - 3).attr('y', t.yOff + 10)
                    .attr('text-anchor', 'end')
                    .attr('fill', t.color).attr('font-size', '7px').attr('opacity', 0.6)
                    .text(t.label);
            }
        });
    }
}

/* --- CEO Compensation Distribution Histogram --- */
function drawCompDistChart(companies) {
    var container = document.getElementById('comp-dist-chart');
    if (!container) return;
    container.innerHTML = '';

    var withComp = companies.filter(function(c) { return c.total_compensation > 0; });
    if (withComp.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No compensation data available</p>';
        return;
    }

    // Sector overlay mode
    var sectorName = window._activeSector || null;
    var sectorCompanies = sectorName ? withComp.filter(function(c) { return c.sector === sectorName; }) : null;
    var hasSectorOverlay = sectorCompanies && sectorCompanies.length >= 3;
    var sectorColor = hasSectorOverlay && typeof getSectorColor === 'function' ? getSectorColor(sectorName) : '#00b4d8';

    // Define buckets matching the sort summary brackets but with finer granularity
    var buckets = [
        { min: 0, max: 5e6, label: '<$5M', color: '#06d6a0' },
        { min: 5e6, max: 10e6, label: '$5–10M', color: '#00b4d8' },
        { min: 10e6, max: 15e6, label: '$10–15M', color: '#38bdf8' },
        { min: 15e6, max: 20e6, label: '$15–20M', color: '#a78bfa' },
        { min: 20e6, max: 30e6, label: '$20–30M', color: '#818cf8' },
        { min: 30e6, max: 50e6, label: '$30–50M', color: '#ffd166' },
        { min: 50e6, max: 75e6, label: '$50–75M', color: '#fb923c' },
        { min: 75e6, max: Infinity, label: '$75M+', color: '#ef476f' }
    ];

    // Count companies in each bucket and collect them
    buckets.forEach(function(b) {
        b.companies = withComp.filter(function(c) {
            return c.total_compensation >= b.min && c.total_compensation < b.max;
        });
        b.count = b.companies.length;
        b.companies.sort(function(a, bb) { return bb.total_compensation - a.total_compensation; });
        // Sector-specific count
        if (hasSectorOverlay) {
            b.sectorCompanies = sectorCompanies.filter(function(c) {
                return c.total_compensation >= b.min && c.total_compensation < b.max;
            });
            b.sectorCount = b.sectorCompanies.length;
            b.sectorCompanies.sort(function(a, bb) { return bb.total_compensation - a.total_compensation; });
        }
    });

    // Filter out empty buckets (keep bucket if S&P 500 OR sector has entries)
    var activeBuckets = buckets.filter(function(b) { return b.count > 0; });

    // Compute Gini coefficient for S&P 500
    var sortedComps = withComp.map(function(c) { return c.total_compensation; }).sort(function(a, b) { return a - b; });
    var n = sortedComps.length;
    var totalComp = sortedComps.reduce(function(s, v) { return s + v; }, 0);
    var giniSum = 0;
    for (var gi = 0; gi < n; gi++) {
        giniSum += (2 * (gi + 1) - n - 1) * sortedComps[gi];
    }
    var gini = totalComp > 0 ? (giniSum / (n * totalComp)) : 0;

    // Median and mean for S&P 500
    var medianComp = sortedComps[Math.floor(n / 2)];
    var meanComp = totalComp / n;

    // Top 10% share
    var top10Idx = Math.floor(n * 0.9);
    var top10Total = sortedComps.slice(top10Idx).reduce(function(s, v) { return s + v; }, 0);
    var top10Pct = (top10Total / totalComp * 100).toFixed(1);

    // Sector stats
    var sectorGini = 0, sectorMedian = 0, sectorMean = 0, sectorTop10Pct = 0;
    if (hasSectorOverlay) {
        var sComps = sectorCompanies.map(function(c) { return c.total_compensation; }).sort(function(a, b) { return a - b; });
        var sn = sComps.length;
        var sTotalComp = sComps.reduce(function(s, v) { return s + v; }, 0);
        var sGiniSum = 0;
        for (var sgi = 0; sgi < sn; sgi++) {
            sGiniSum += (2 * (sgi + 1) - sn - 1) * sComps[sgi];
        }
        sectorGini = sTotalComp > 0 ? (sGiniSum / (sn * sTotalComp)) : 0;
        sectorMedian = sComps[Math.floor(sn / 2)];
        sectorMean = sTotalComp / sn;
        if (sn >= 10) {
            var sTop10Idx = Math.floor(sn * 0.9);
            var sTop10Total = sComps.slice(sTop10Idx).reduce(function(s, v) { return s + v; }, 0);
            sectorTop10Pct = (sTop10Total / sTotalComp * 100).toFixed(1);
        }
    }

    var margin = { top: 20, right: 50, bottom: 50, left: 70 };
    var w = container.clientWidth - margin.left - margin.right;
    var h = 300;

    var ariaLabel = hasSectorOverlay
        ? 'CEO compensation distribution: ' + sectorName + ' (' + sectorCompanies.length + ' companies) vs S&P 500'
        : 'CEO total compensation distribution across S&P 500';

    var svg = d3.select('#comp-dist-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .attr('role', 'img')
        .attr('aria-label', ariaLabel)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    // Y domain: use max of S&P 500 counts (sector bars will be shorter)
    var maxCount = d3.max(activeBuckets, function(b) { return b.count; });
    // In sector mode, also check percentage scale if sector is small
    var x = d3.scaleBand()
        .domain(activeBuckets.map(function(b) { return b.label; }))
        .range([0, w])
        .padding(0.2);

    var y = d3.scaleLinear()
        .domain([0, maxCount * 1.15])
        .range([h, 0]);

    // If sector overlay, add secondary Y axis for sector count
    var ySector = null;
    if (hasSectorOverlay) {
        var maxSectorCount = d3.max(activeBuckets, function(b) { return b.sectorCount || 0; });
        ySector = d3.scaleLinear()
            .domain([0, Math.max(maxSectorCount * 1.15, 1)])
            .range([h, 0]);
    }

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
        .text('CEO Total Compensation');

    // Y axis (left — S&P 500)
    svg.append('g').attr('class', 'axis')
        .call(d3.axisLeft(y).ticks(6).tickFormat(function(d) { return d; }));

    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -h / 2)
        .attr('y', -50)
        .attr('text-anchor', 'middle')
        .attr('fill', typeof getThemeMutedColor === 'function' ? getThemeMutedColor() : '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(hasSectorOverlay ? 'S&P 500 Companies' : 'Number of Companies');

    // Y axis (right — sector) when overlay is active
    if (hasSectorOverlay && ySector) {
        svg.append('g').attr('class', 'axis')
            .attr('transform', 'translate(' + w + ',0)')
            .call(d3.axisRight(ySector).ticks(4).tickFormat(function(d) { return d; }));
        svg.append('text')
            .attr('transform', 'rotate(90)')
            .attr('x', h / 2)
            .attr('y', -w - 40)
            .attr('text-anchor', 'middle')
            .attr('fill', sectorColor)
            .attr('font-size', '11px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(sectorName + ' Companies');
    }

    // S&P 500 bars (background when sector overlay active)
    var bars = svg.selectAll('.comp-dist-bar')
        .data(activeBuckets)
        .join('g')
        .attr('class', 'comp-dist-bar');

    bars.append('rect')
        .attr('x', function(b) { return x(b.label); })
        .attr('y', function(b) { return y(b.count); })
        .attr('width', x.bandwidth())
        .attr('height', function(b) { return h - y(b.count); })
        .attr('fill', function(b) { return hasSectorOverlay ? (typeof isDarkTheme === 'function' && isDarkTheme() ? '#3f3f46' : '#d4d4d8') : b.color; })
        .attr('rx', 3)
        .attr('opacity', function(b) {
            if (hasSectorOverlay) return 0.5;
            var af = window._activeDistFilter;
            if (af && !af.sector) return (b.min === af.min) ? 1 : 0.3;
            return 0.8;
        })
        .each(function(b) {
            if (!hasSectorOverlay) {
                var af = window._activeDistFilter;
                if (af && !af.sector && b.min === af.min) {
                    d3.select(this).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
                }
            }
        })
        .style('cursor', 'pointer')
        .on('mouseover', function(event, b) {
            if (hasSectorOverlay) return; // Let sector bars handle tooltip
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1);
            var pct = (b.count / withComp.length * 100).toFixed(1);
            var topNames = b.companies.slice(0, 5).map(function(c) {
                return c.ticker + ' (' + fmtCurr(c.total_compensation) + ')';
            }).join('<br>');
            var html = '<div class="ct-title">' + b.label + ' Compensation</div>' +
                '<div class="ct-row"><span class="ct-label">Companies</span><span class="ct-val">' + b.count + ' (' + pct + '%)</span></div>';
            if (topNames) html += '<div class="ct-row ct-sub"><span class="ct-label">Top earners</span><span class="ct-val">' + topNames + '</span></div>';
            html += '<div class="ct-row ct-sub"><span class="ct-label">Click to filter table</span></div>';
            showChartTooltip(event, html);
        })
        .on('mousemove', function(event) { if (!hasSectorOverlay) positionChartTooltip(event); })
        .on('mouseout', function(event, b) {
            if (hasSectorOverlay) return;
            var af = window._activeDistFilter;
            var isActive = af && !af.sector && b.min === af.min;
            d3.select(this)
                .attr('opacity', isActive ? 1 : (af && !af.sector ? 0.3 : 0.8))
                .attr('stroke', isActive ? chartStrokeColor() : 'none')
                .attr('stroke-width', isActive ? 1.5 : 0);
            hideChartTooltip();
        })
        .on('click', function(event, b) {
            if (window.filterByCompBracket) {
                window.filterByCompBracket(b.min, b.max, b.label);
            }
        });

    // S&P 500 count labels (dimmed when sector overlay active)
    bars.append('text')
        .attr('class', 'bar-label')
        .attr('x', function(b) { return x(b.label) + x.bandwidth() / 2; })
        .attr('y', function(b) { return y(b.count) - 6; })
        .attr('text-anchor', 'middle')
        .attr('font-weight', hasSectorOverlay ? '400' : '600')
        .attr('font-size', hasSectorOverlay ? '9px' : null)
        .attr('fill', hasSectorOverlay ? (typeof isDarkTheme === 'function' && isDarkTheme() ? '#71717a' : '#a1a1aa') : null)
        .text(function(b) { return b.count; })
        .attr('opacity', function(b) {
            if (hasSectorOverlay) return 0.6;
            var af = window._activeDistFilter;
            if (af && !af.sector) return (b.min === af.min) ? 1 : 0.4;
            return 1;
        });

    // Sector overlay bars
    if (hasSectorOverlay && ySector) {
        var sectorBars = svg.selectAll('.comp-dist-sector-bar')
            .data(activeBuckets)
            .join('g')
            .attr('class', 'comp-dist-sector-bar');

        // Narrower bars centered within the S&P 500 bar
        var sBarWidth = Math.max(x.bandwidth() * 0.55, 6);
        var sBarOffset = (x.bandwidth() - sBarWidth) / 2;

        sectorBars.append('rect')
            .attr('x', function(b) { return x(b.label) + sBarOffset; })
            .attr('y', function(b) { return ySector(b.sectorCount || 0); })
            .attr('width', sBarWidth)
            .attr('height', function(b) { return h - ySector(b.sectorCount || 0); })
            .attr('fill', sectorColor)
            .attr('rx', 2)
            .attr('opacity', 0.85)
            .style('cursor', 'pointer')
            .on('mouseover', function(event, b) {
                d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1);
                var sPct = sectorCompanies.length > 0 ? ((b.sectorCount / sectorCompanies.length) * 100).toFixed(1) : '0';
                var sp500Pct = (b.count / withComp.length * 100).toFixed(1);
                var topNames = (b.sectorCompanies || []).slice(0, 5).map(function(c) {
                    return c.ticker + ' (' + fmtCurr(c.total_compensation) + ')';
                }).join('<br>');
                var html = '<div class="ct-title">' + b.label + ' — ' + sectorName + '</div>' +
                    '<div class="ct-row"><span class="ct-label">' + sectorName + '</span><span class="ct-val">' + (b.sectorCount || 0) + ' (' + sPct + '%)</span></div>' +
                    '<div class="ct-row"><span class="ct-label">S&P 500</span><span class="ct-val">' + b.count + ' (' + sp500Pct + '%)</span></div>';
                if (topNames) html += '<div class="ct-row ct-sub"><span class="ct-label">Top in sector</span><span class="ct-val">' + topNames + '</span></div>';
                html += '<div class="ct-row ct-sub"><span class="ct-label">Click to filter table</span></div>';
                showChartTooltip(event, html);
            })
            .on('mousemove', function(event) { positionChartTooltip(event); })
            .on('mouseout', function(event, b) {
                d3.select(this).attr('opacity', 0.85).attr('stroke', 'none').attr('stroke-width', 0);
                hideChartTooltip();
            })
            .on('click', function(event, b) {
                if (window.filterByCompBracket) {
                    window.filterByCompBracket(b.min, b.max, b.label);
                }
            });

        // Sector count labels
        sectorBars.append('text')
            .attr('class', 'bar-label')
            .attr('x', function(b) { return x(b.label) + x.bandwidth() / 2; })
            .attr('y', function(b) { return ySector(b.sectorCount || 0) - 6; })
            .attr('text-anchor', 'middle')
            .attr('font-weight', '600')
            .attr('fill', sectorColor)
            .text(function(b) { return b.sectorCount || ''; });
    }

    // Median reference line — find which bucket it falls in
    var medianBucket = activeBuckets.find(function(b) {
        return medianComp >= b.min && medianComp < (b.max === Infinity ? 1e12 : b.max);
    });
    if (medianBucket && !hasSectorOverlay) {
        var medBucketRange = Math.min(medianBucket.max, 200e6) - medianBucket.min;
        var medFrac = medBucketRange > 0 ? (medianComp - medianBucket.min) / medBucketRange : 0.5;
        var medX = x(medianBucket.label) + medFrac * x.bandwidth();

        svg.append('line')
            .attr('x1', medX).attr('x2', medX)
            .attr('y1', 0).attr('y2', h)
            .attr('stroke', '#ffd166').attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '6,4').attr('opacity', 0.7);
        svg.append('text')
            .attr('x', medX + 5).attr('y', 10)
            .attr('fill', '#ffd166').attr('font-size', '9px').attr('font-weight', '500').attr('opacity', 0.8)
            .text('Median: ' + fmtCurr(medianComp));
    }

    // Mean reference line (non-sector mode only)
    var meanBucket = activeBuckets.find(function(b) {
        return meanComp >= b.min && meanComp < (b.max === Infinity ? 1e12 : b.max);
    });
    if (meanBucket && !hasSectorOverlay) {
        var meanBucketRange = Math.min(meanBucket.max, 200e6) - meanBucket.min;
        var meanFrac = meanBucketRange > 0 ? (meanComp - meanBucket.min) / meanBucketRange : 0.5;
        var meanX = x(meanBucket.label) + meanFrac * x.bandwidth();

        svg.append('line')
            .attr('x1', meanX).attr('x2', meanX)
            .attr('y1', 0).attr('y2', h)
            .attr('stroke', '#ef476f').attr('stroke-width', 1)
            .attr('stroke-dasharray', '3,3').attr('opacity', 0.6);
        svg.append('text')
            .attr('x', meanX + 5).attr('y', 24)
            .attr('fill', '#ef476f').attr('font-size', '9px').attr('font-weight', '500').attr('opacity', 0.8)
            .text('Mean: ' + fmtCurr(meanComp));
    }

    // Sector median + S&P 500 median reference lines in overlay mode
    if (hasSectorOverlay) {
        // S&P 500 median (dimmed)
        var sp500MedBucket = activeBuckets.find(function(b) {
            return medianComp >= b.min && medianComp < (b.max === Infinity ? 1e12 : b.max);
        });
        if (sp500MedBucket) {
            var sp500Range = Math.min(sp500MedBucket.max, 200e6) - sp500MedBucket.min;
            var sp500Frac = sp500Range > 0 ? (medianComp - sp500MedBucket.min) / sp500Range : 0.5;
            var sp500MedX = x(sp500MedBucket.label) + sp500Frac * x.bandwidth();
            svg.append('line')
                .attr('x1', sp500MedX).attr('x2', sp500MedX)
                .attr('y1', 0).attr('y2', h)
                .attr('stroke', typeof isDarkTheme === 'function' && isDarkTheme() ? '#71717a' : '#a1a1aa')
                .attr('stroke-width', 1).attr('stroke-dasharray', '4,4').attr('opacity', 0.5);
            svg.append('text')
                .attr('x', sp500MedX + 5).attr('y', 10)
                .attr('fill', typeof isDarkTheme === 'function' && isDarkTheme() ? '#71717a' : '#a1a1aa')
                .attr('font-size', '8px').attr('font-weight', '400').attr('opacity', 0.6)
                .text('S&P 500 Med: ' + fmtCurr(medianComp));
        }
        // Sector median (prominent)
        var secMedBucket = activeBuckets.find(function(b) {
            return sectorMedian >= b.min && sectorMedian < (b.max === Infinity ? 1e12 : b.max);
        });
        if (secMedBucket) {
            var secRange = Math.min(secMedBucket.max, 200e6) - secMedBucket.min;
            var secFrac = secRange > 0 ? (sectorMedian - secMedBucket.min) / secRange : 0.5;
            var secMedX = x(secMedBucket.label) + secFrac * x.bandwidth();
            svg.append('line')
                .attr('x1', secMedX).attr('x2', secMedX)
                .attr('y1', 0).attr('y2', h)
                .attr('stroke', sectorColor).attr('stroke-width', 1.5)
                .attr('stroke-dasharray', '6,4').attr('opacity', 0.8);
            svg.append('text')
                .attr('x', secMedX + 5).attr('y', 24)
                .attr('fill', sectorColor).attr('font-size', '9px').attr('font-weight', '500').attr('opacity', 0.9)
                .text('Sector Med: ' + fmtCurr(sectorMedian));
        }
    }

    // Summary annotation
    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
    var annotColor = dark ? '#a1a1aa' : '#6b7280';
    var annotG = svg.append('g').attr('class', 'comp-dist-annotation');
    var giniX = w - 4;

    if (hasSectorOverlay) {
        // Sector vs S&P 500 comparison annotations
        annotG.append('text')
            .attr('x', giniX).attr('y', 14)
            .attr('text-anchor', 'end')
            .attr('fill', sectorColor).attr('font-size', '11px').attr('font-weight', '600')
            .text(sectorName + ': Gini ' + sectorGini.toFixed(3));
        annotG.append('text')
            .attr('x', giniX).attr('y', 28)
            .attr('text-anchor', 'end')
            .attr('fill', annotColor).attr('font-size', '9px')
            .text('S&P 500: Gini ' + gini.toFixed(3));
        var medDelta = sectorMedian > 0 && medianComp > 0 ? ((sectorMedian / medianComp - 1) * 100).toFixed(0) : '0';
        var medDeltaSign = medDelta >= 0 ? '+' : '';
        annotG.append('text')
            .attr('x', giniX).attr('y', 42)
            .attr('text-anchor', 'end')
            .attr('fill', sectorColor).attr('font-size', '9px')
            .text('Median ' + medDeltaSign + medDelta + '% vs S&P 500');
        annotG.append('text')
            .attr('x', giniX).attr('y', 54)
            .attr('text-anchor', 'end')
            .attr('fill', annotColor).attr('font-size', '9px')
            .text(sectorCompanies.length + ' companies in sector');
    } else {
        // Standard S&P 500 annotations
        annotG.append('text')
            .attr('x', giniX).attr('y', 14)
            .attr('text-anchor', 'end')
            .attr('fill', '#00b4d8').attr('font-size', '11px').attr('font-weight', '600')
            .text('Gini: ' + gini.toFixed(3));
        annotG.append('text')
            .attr('x', giniX).attr('y', 28)
            .attr('text-anchor', 'end')
            .attr('fill', annotColor).attr('font-size', '9px')
            .text('Top 10% earn ' + top10Pct + '% of total');
        annotG.append('text')
            .attr('x', giniX).attr('y', 40)
            .attr('text-anchor', 'end')
            .attr('fill', annotColor).attr('font-size', '9px')
            .text('Mean/Median ratio: ' + (meanComp / medianComp).toFixed(2) + '×');
    }

    // Legend when sector overlay active
    if (hasSectorOverlay) {
        var legendG = svg.append('g').attr('transform', 'translate(0,' + (h + 26) + ')');
        legendG.append('rect').attr('x', 0).attr('y', 0).attr('width', 10).attr('height', 10).attr('rx', 2)
            .attr('fill', dark ? '#3f3f46' : '#d4d4d8').attr('opacity', 0.6);
        legendG.append('text').attr('x', 14).attr('y', 9).attr('fill', annotColor).attr('font-size', '9px').text('S&P 500');
        legendG.append('rect').attr('x', 65).attr('y', 0).attr('width', 10).attr('height', 10).attr('rx', 2)
            .attr('fill', sectorColor).attr('opacity', 0.85);
        legendG.append('text').attr('x', 79).attr('y', 9).attr('fill', sectorColor).attr('font-size', '9px').attr('font-weight', '500').text(sectorName);
    }
}

/* Highlight compensation distribution chart bars when filter is active */
window.highlightCompDistBucket = function(minComp) {
    d3.selectAll('#comp-dist-chart .comp-dist-bar rect').each(function(d) {
        if (!d) return;
        if (minComp == null) {
            // Clear: restore all to default
            d3.select(this).attr('opacity', 0.8).attr('stroke', 'none').attr('stroke-width', 0);
        } else {
            var isActive = d.min === minComp;
            d3.select(this)
                .attr('opacity', isActive ? 1 : 0.3)
                .attr('stroke', isActive ? chartStrokeColor() : 'none')
                .attr('stroke-width', isActive ? 1.5 : 0);
        }
    });
    // Also update count label opacity
    d3.selectAll('#comp-dist-chart .comp-dist-bar text').each(function(d) {
        if (!d) return;
        if (minComp == null) {
            d3.select(this).attr('opacity', 1);
        } else {
            d3.select(this).attr('opacity', d.min === minComp ? 1 : 0.4);
        }
    });
};

/* --- Compensation Composition (Donut Chart with Granular Breakdown) --- */
function drawCompositionChart(trends) {
    var container = document.getElementById('composition-chart');
    container.innerHTML = '';
    var compComp = trends.compensation_composition;
    if (!compComp || !compComp.s_and_p_500) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No composition data</p>';
        return;
    }

    var sp = compComp.s_and_p_500;
    var detail = compComp.s_and_p_500_fy2024_detail;

    // Build segments from granular detail data when available
    var segments;
    if (detail && detail.median_performance_stock_awards) {
        segments = [
            { label: 'Performance Stock', value: detail.median_performance_stock_awards, yoy: detail.perf_stock_yoy_change, color: '#00b4d8', desc: 'Performance-based equity awards' },
            { label: 'Restricted Stock / RSUs', value: detail.median_restricted_stock, yoy: detail.restricted_stock_yoy_change, color: '#0096c7', desc: 'Time-vesting restricted stock units' },
            { label: 'Discretionary Bonus', value: detail.median_discretionary_bonus, yoy: detail.bonus_yoy_change, color: '#a78bfa', desc: 'Board-approved cash bonuses' },
            { label: 'Non-Equity Incentive', value: detail.median_neip_payout, yoy: detail.neip_yoy_change, color: '#8b5cf6', desc: 'Formula-based incentive plan payouts' },
            { label: 'Base Salary', value: sp.median_salary, color: '#06d6a0', desc: 'Fixed annual cash compensation' },
            { label: 'Perks & Other', value: sp.median_perks, yoy: sp.perks_yoy_change, color: '#ffd166', desc: 'Security, travel, insurance, etc.' }
        ];
    } else {
        // Fallback: 4-segment approximation from aggregate data
        var stockPct = sp.stock_awards_pct || 71.6;
        var impliedTotal = sp.median_stock_awards ? sp.median_stock_awards / (stockPct / 100) : 17100000;
        var salaryPct = sp.median_salary ? (sp.median_salary / impliedTotal * 100) : 7.6;
        var perksPct = sp.median_perks ? (sp.median_perks / impliedTotal * 100) : 1.7;
        var otherPct = 100 - stockPct - salaryPct - perksPct;
        segments = [
            { label: 'Stock Awards', value: sp.median_stock_awards || impliedTotal * stockPct / 100, yoy: sp.stock_awards_yoy_change, color: '#00b4d8', desc: 'Equity-based compensation' },
            { label: 'Non-Equity Incentive', value: impliedTotal * otherPct / 100, color: '#a78bfa', desc: 'Performance-based cash' },
            { label: 'Base Salary', value: sp.median_salary || impliedTotal * salaryPct / 100, color: '#06d6a0', desc: 'Fixed annual cash' },
            { label: 'Perks & Other', value: sp.median_perks || impliedTotal * perksPct / 100, yoy: sp.perks_yoy_change, color: '#ffd166', desc: 'Benefits and perquisites' }
        ];
    }

    // Filter out zero-value segments and compute percentages
    segments = segments.filter(function(s) { return s.value && s.value > 0; });
    var total = segments.reduce(function(s, seg) { return s + seg.value; }, 0);
    segments.forEach(function(seg) {
        seg.pct = total > 0 ? (seg.value / total * 100) : 0;
    });

    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
    var textColor = dark ? '#e4e4e7' : '#1a1a2e';
    var mutedColor = dark ? '#6b7280' : '#6b7280';
    var bgStroke = dark ? 'rgba(15,15,26,0.6)' : 'rgba(255,255,255,0.8)';

    // Donut chart dimensions — responsive to container
    var containerW = container.clientWidth;
    var chartSize = Math.min(300, containerW - 60);
    if (chartSize < 200) chartSize = 200;
    var outerRadius = chartSize / 2;
    var innerRadius = outerRadius * 0.55;
    var hoverExpand = 8;

    // Wrapper for centering chart + legend
    var wrapper = document.createElement('div');
    wrapper.className = 'composition-donut-wrapper';
    container.appendChild(wrapper);

    // SVG element
    var svgW = chartSize + hoverExpand * 2 + 4;
    var svgH = svgW;
    var svgEl = d3.select(wrapper).append('svg')
        .attr('width', svgW)
        .attr('height', svgH)
        .attr('class', 'composition-donut-svg');

    var g = svgEl.append('g')
        .attr('transform', 'translate(' + (svgW / 2) + ',' + (svgH / 2) + ')');

    // Pie layout
    var pie = d3.pie()
        .value(function(d) { return d.value; })
        .sort(null)
        .padAngle(0.025);

    var arc = d3.arc()
        .innerRadius(innerRadius)
        .outerRadius(outerRadius)
        .cornerRadius(3);

    var arcHover = d3.arc()
        .innerRadius(innerRadius - 2)
        .outerRadius(outerRadius + hoverExpand)
        .cornerRadius(4);

    var arcs = pie(segments);

    // Draw donut segments
    g.selectAll('.donut-seg')
        .data(arcs)
        .join('path')
        .attr('class', 'donut-seg')
        .attr('d', arc)
        .attr('fill', function(d) { return d.data.color; })
        .attr('opacity', 0.88)
        .attr('stroke', bgStroke)
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .style('transition', 'opacity 0.15s')
        .on('mouseover', function(event, d) {
            d3.select(this)
                .attr('d', arcHover)
                .attr('opacity', 1)
                .attr('stroke-width', 0);

            // Dim other segments
            g.selectAll('.donut-seg').filter(function(dd) { return dd !== d; })
                .attr('opacity', 0.4);

            var yoyHtml = '';
            if (d.data.yoy) {
                var isNeg = d.data.yoy.indexOf('-') === 0;
                var isFlat = d.data.yoy.toLowerCase() === 'flat';
                var yoyColor = isNeg ? '#ef476f' : (isFlat ? mutedColor : '#06d6a0');
                var yoyPrefix = (!isNeg && !isFlat && d.data.yoy.indexOf('+') !== 0) ? '+' : '';
                yoyHtml = '<div class="ct-row"><span class="ct-label">YoY Change</span><span class="ct-val" style="color:' + yoyColor + '">' + yoyPrefix + d.data.yoy + '</span></div>';
            }

            showChartTooltip(event,
                '<div class="ct-title">' + d.data.label + '</div>' +
                '<div class="ct-row"><span class="ct-label">Median Value</span><span class="ct-val">' + fmtCurr(d.data.value) + '</span></div>' +
                '<div class="ct-row"><span class="ct-label">Share of Total</span><span class="ct-val">' + d.data.pct.toFixed(1) + '%</span></div>' +
                yoyHtml +
                '<div class="ct-row ct-sub"><span class="ct-label">' + d.data.desc + '</span></div>');
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function() {
            g.selectAll('.donut-seg')
                .attr('d', arc)
                .attr('opacity', 0.88)
                .attr('stroke', bgStroke)
                .attr('stroke-width', 2);
            hideChartTooltip();
        });

    // Percentage labels on larger segments (> 8%)
    g.selectAll('.donut-label')
        .data(arcs)
        .join('text')
        .attr('class', 'donut-label')
        .attr('transform', function(d) {
            var labelArc = d3.arc().innerRadius(innerRadius + (outerRadius - innerRadius) * 0.45).outerRadius(outerRadius);
            return 'translate(' + labelArc.centroid(d) + ')';
        })
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .attr('fill', '#fff')
        .attr('font-size', function(d) { return d.data.pct >= 15 ? '12px' : '10px'; })
        .attr('font-weight', '700')
        .attr('font-family', "'SF Mono', 'Fira Code', monospace")
        .attr('pointer-events', 'none')
        .attr('opacity', function(d) { return d.data.pct >= 8 ? 0.95 : 0; })
        .text(function(d) { return d.data.pct.toFixed(0) + '%'; });

    // Center text: total compensation
    g.append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '-0.2em')
        .attr('fill', textColor)
        .attr('font-size', '22px')
        .attr('font-weight', '700')
        .attr('font-family', "'SF Mono', 'Fira Code', monospace")
        .text(fmtCurr(total));

    g.append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '1.3em')
        .attr('fill', mutedColor)
        .attr('font-size', '11px')
        .attr('font-weight', '500')
        .attr('font-family', "'Inter', sans-serif")
        .attr('letter-spacing', '0.5px')
        .text('MEDIAN TOTAL');

    // Legend with YoY badges — HTML for responsive wrapping
    var legendDiv = document.createElement('div');
    legendDiv.className = 'composition-legend';
    segments.forEach(function(seg) {
        var item = document.createElement('div');
        item.className = 'composition-legend-item';

        var yoyBadge = '';
        if (seg.yoy) {
            var isNeg = seg.yoy.indexOf('-') === 0;
            var isFlat = seg.yoy.toLowerCase() === 'flat';
            var badgeClass = isNeg ? 'comp-yoy-neg' : (isFlat ? 'comp-yoy-flat' : 'comp-yoy-pos');
            var prefix = (!isNeg && !isFlat && seg.yoy.indexOf('+') !== 0) ? '+' : '';
            yoyBadge = '<span class="comp-yoy-badge ' + badgeClass + '">' + prefix + seg.yoy + '</span>';
        }

        item.innerHTML =
            '<span class="composition-legend-dot" style="background:' + seg.color + '"></span>' +
            '<span class="composition-legend-label">' + seg.label + '</span>' +
            '<span class="composition-legend-val">' + fmtCurr(seg.value) + ' <span class="composition-legend-pct">(' + seg.pct.toFixed(1) + '%)</span>' + yoyBadge + '</span>';
        legendDiv.appendChild(item);
    });
    wrapper.appendChild(legendDiv);

    // Source note
    var sourceNote = document.createElement('div');
    sourceNote.className = 'composition-source';
    sourceNote.textContent = 'Source: ' + ((detail && detail.source) || sp.source || 'Equilar/AP 2025') + ' · FY' + (sp.fiscal_year || 2024);
    wrapper.appendChild(sourceNote);
}

/* --- CEO Pay vs. Pay Ratio Scatter Plot --- */
function drawScatterChart(companies) {
    var container = document.getElementById('scatter-chart');
    if (!container) return;
    container.innerHTML = '';
    // Clear any previous brush selection results
    var _prevBrushResults = document.getElementById('scatter-brush-results');
    if (_prevBrushResults) _prevBrushResults.style.display = 'none';

    var SECTOR_COLORS = {
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

    // Metric definitions — key, human label, accessor, formatter, unit suffix, supports log scale
    var SCATTER_METRICS = {
        total_compensation: {
            label: 'CEO Total Compensation',
            shortLabel: 'CEO Total Comp',
            get: function(c) { return c.total_compensation; },
            fmt: function(v) { return fmtCurr(v); },
            fmtAxis: function(v) { return fmtCurr(v); },
            unit: '',
            minForLog: 100000,
            canBeNegative: false
        },
        pay_ratio: {
            label: 'CEO-to-Worker Pay Ratio',
            shortLabel: 'Pay Ratio',
            get: function(c) { return c.pay_ratio; },
            fmt: function(v) { return v != null ? Math.round(v) + ':1' : '—'; },
            fmtAxis: function(v) { return v >= 1000 ? (v / 1000).toFixed(0) + 'K' : Math.round(v); },
            unit: ':1',
            minForLog: 1,
            canBeNegative: false
        },
        median_worker_pay: {
            label: 'Median Worker Pay',
            shortLabel: 'Worker Pay',
            get: function(c) { return c.median_worker_pay; },
            fmt: function(v) { return fmtCurr(v); },
            fmtAxis: function(v) { return fmtCurr(v); },
            unit: '',
            minForLog: 1000,
            canBeNegative: false
        },
        _ceoStockPctSort: {
            label: 'Stock Awards % of Total',
            shortLabel: 'Stock %',
            get: function(c) { return c._ceoStockPctSort; },
            fmt: function(v) { return v != null ? v.toFixed(1) + '%' : '—'; },
            fmtAxis: function(v) { return Math.round(v) + '%'; },
            unit: '%',
            minForLog: 0.1,
            canBeNegative: false
        },
        _ceoConcPct: {
            label: 'CEO Concentration %',
            shortLabel: 'CEO Conc %',
            get: function(c) { return c._ceoConcPct; },
            fmt: function(v) { return v != null ? v.toFixed(1) + '%' : '—'; },
            fmtAxis: function(v) { return Math.round(v) + '%'; },
            unit: '%',
            minForLog: 1,
            canBeNegative: false
        },
        _ceoYoYPct: {
            label: 'YoY Compensation Change',
            shortLabel: 'YoY Change',
            get: function(c) { return c._ceoYoY && c._ceoYoY.pctChange != null ? c._ceoYoY.pctChange : null; },
            fmt: function(v) {
                if (v == null) return '—';
                var sign = v >= 0 ? '+' : '\u2212';
                return sign + Math.abs(v).toFixed(1) + '%';
            },
            fmtAxis: function(v) { return (v >= 0 ? '+' : '') + Math.round(v) + '%'; },
            unit: '%',
            minForLog: 0.1,
            canBeNegative: true
        },
        _sopApproval: {
            label: 'Say-on-Pay Approval %',
            shortLabel: 'SoP %',
            get: function(c) { return c._sopApproval; },
            fmt: function(v) { return v != null ? v.toFixed(1) + '%' : '—'; },
            fmtAxis: function(v) { return Math.round(v) + '%'; },
            unit: '%',
            minForLog: 1,
            canBeNegative: false
        },
        _ceoCfoPremium: {
            label: 'CEO-to-CFO Premium',
            shortLabel: 'CEO/CFO',
            get: function(c) { return c._ceoCfoPremium; },
            fmt: function(v) { return v != null ? v.toFixed(1) + '×' : '—'; },
            fmtAxis: function(v) { return v.toFixed(1) + '×'; },
            unit: '×',
            minForLog: 0.5,
            canBeNegative: false
        },
        _ceoTenureYears: {
            label: 'CEO Tenure (Years)',
            shortLabel: 'Tenure',
            get: function(c) { return c._ceoTenureYears; },
            fmt: function(v) { return v != null ? v + ' years' : '—'; },
            fmtAxis: function(v) { return v + 'y'; },
            unit: ' years',
            minForLog: 1,
            canBeNegative: false
        },
        _govScore: {
            label: 'Governance Score',
            shortLabel: 'Gov Score',
            get: function(c) { return c._govScore; },
            fmt: function(v) { return v != null ? v + '/100' : '—'; },
            fmtAxis: function(v) { return Math.round(v); },
            unit: '/100',
            minForLog: 1,
            canBeNegative: false
        },
        _gerScore: {
            label: 'Governance Erosion Risk',
            shortLabel: 'GER Score',
            get: function(c) { return c._gerScore; },
            fmt: function(v) { return v != null ? v + '/100' : '—'; },
            fmtAxis: function(v) { return Math.round(v); },
            unit: '/100',
            minForLog: 1,
            canBeNegative: false
        }
    };

    // Read selected axes from dropdown controls
    var xMetricKey = 'total_compensation';
    var yMetricKey = 'pay_ratio';
    var xSelect = document.getElementById('scatter-x-metric');
    var ySelect = document.getElementById('scatter-y-metric');
    if (xSelect) xMetricKey = xSelect.value;
    if (ySelect) yMetricKey = ySelect.value;

    var xMetric = SCATTER_METRICS[xMetricKey];
    var yMetric = SCATTER_METRICS[yMetricKey];
    if (!xMetric || !yMetric) return;

    // Sector overlay mode
    var sectorName = window._activeSector || null;
    var sectorColor = sectorName && typeof getSectorColor === 'function' ? getSectorColor(sectorName) : null;

    // Filter to companies with valid data for both axes
    var pts = companies.filter(function(c) {
        var xv = xMetric.get(c);
        var yv = yMetric.get(c);
        return xv != null && yv != null && isFinite(xv) && isFinite(yv);
    });

    if (pts.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No data available for this axis combination</p>';
        return;
    }

    // Sector-specific data
    var sectorPts = sectorName ? pts.filter(function(c) { return c.sector === sectorName; }) : null;
    var hasSectorOverlay = sectorPts && sectorPts.length >= 3;

    var logX = document.getElementById('scatter-log-x') && document.getElementById('scatter-log-x').checked;
    var logY = document.getElementById('scatter-log-y') && document.getElementById('scatter-log-y').checked;

    // Disable log scale for metrics that can be negative or zero
    if (xMetric.canBeNegative) logX = false;
    if (yMetric.canBeNegative) logY = false;

    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
    var margin = { top: 30, right: 30, bottom: 75, left: 70 };
    var w = container.clientWidth - margin.left - margin.right;
    var h = Math.max(400, Math.min(500, container.clientWidth * 0.55));

    // Update chart title/desc dynamically
    var scatterTitle = document.getElementById('scatter-title');
    var scatterDesc = document.getElementById('scatter-desc');
    if (scatterTitle) {
        var titleText = xMetric.shortLabel + ' vs. ' + yMetric.shortLabel;
        if (hasSectorOverlay) titleText = sectorName + ' — ' + titleText;
        scatterTitle.textContent = titleText;
    }
    if (scatterDesc) {
        if (hasSectorOverlay) {
            scatterDesc.textContent = sectorName + ' companies highlighted against the S&P 500. Sector median crosshairs shown in color. Dot size = CEO pay.';
        } else {
            scatterDesc.textContent = 'Each dot is an S&P 500 company. X = ' + xMetric.label + ', Y = ' + yMetric.label + '. Dot size = CEO pay. Hover for details, click to view in table. Colored by sector.';
        }
    }

    var ariaLabel = (hasSectorOverlay ? sectorName + ' — ' : 'S&P 500 ') + xMetric.shortLabel + ' vs ' + yMetric.shortLabel;

    var svg = d3.select('#scatter-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .attr('role', 'img')
        .attr('aria-label', ariaLabel)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    // Build X scale
    var xVals = pts.map(function(c) { return xMetric.get(c); });
    var xMin = d3.min(xVals);
    var xMax = d3.max(xVals);
    var xPadding = (xMax - xMin) * 0.05 || Math.abs(xMax) * 0.05 || 1;

    var x;
    if (logX && !xMetric.canBeNegative) {
        x = d3.scaleLog()
            .domain([d3.min(xVals.filter(function(v) { return v > 0; }).map(function(v) { return Math.max(v, xMetric.minForLog); })), xMax * 1.05])
            .range([0, w]).clamp(true);
    } else {
        var xDomMin = xMetric.canBeNegative ? xMin - xPadding : 0;
        x = d3.scaleLinear().domain([xDomMin, xMax + xPadding]).range([0, w]);
    }

    // Build Y scale
    var yVals = pts.map(function(c) { return yMetric.get(c); });
    var yMin = d3.min(yVals);
    var yMax2 = d3.max(yVals);
    var yPadding = (yMax2 - yMin) * 0.05 || Math.abs(yMax2) * 0.05 || 1;

    var yScale;
    if (logY && !yMetric.canBeNegative) {
        yScale = d3.scaleLog()
            .domain([d3.min(yVals.filter(function(v) { return v > 0; }).map(function(v) { return Math.max(v, yMetric.minForLog); })), yMax2 * 1.05])
            .range([h, 0]).clamp(true);
    } else {
        var yDomMin = yMetric.canBeNegative ? yMin - yPadding : 0;
        yScale = d3.scaleLinear().domain([yDomMin, yMax2 + yPadding]).range([h, 0]);
    }

    // Size scale — always based on total comp for consistency
    var r = d3.scaleSqrt()
        .domain([0, d3.max(pts, function(d) { return d.total_compensation || 0; })])
        .range([3, 18]);

    // Grid
    svg.append('g').attr('class', 'grid')
        .call(d3.axisBottom(x).tickSize(h).tickFormat('').ticks(6))
        .attr('transform', 'translate(0,0)');
    svg.append('g').attr('class', 'grid')
        .call(d3.axisLeft(yScale).tickSize(-w).tickFormat('').ticks(6));

    // Axes
    svg.append('g').attr('class', 'axis')
        .attr('transform', 'translate(0,' + h + ')')
        .call(d3.axisBottom(x).ticks(6).tickFormat(function(v) { return xMetric.fmtAxis(v); }));

    svg.append('g').attr('class', 'axis')
        .call(d3.axisLeft(yScale).ticks(6).tickFormat(function(v) { return yMetric.fmtAxis(v); }));

    // Axis labels
    var axisLabelColor = typeof getThemeSecondaryColor === 'function' ? getThemeSecondaryColor() : '#a1a1aa';
    svg.append('text')
        .attr('class', 'axis-label')
        .attr('x', w / 2)
        .attr('y', h + 45)
        .attr('text-anchor', 'middle')
        .attr('fill', axisLabelColor)
        .attr('font-size', '12px')
        .text(xMetric.label);

    svg.append('text')
        .attr('class', 'axis-label')
        .attr('transform', 'rotate(-90)')
        .attr('x', -h / 2)
        .attr('y', -55)
        .attr('text-anchor', 'middle')
        .attr('fill', axisLabelColor)
        .attr('font-size', '12px')
        .text(yMetric.label);

    // Median reference lines
    var medX = d3.median(pts, function(d) { return xMetric.get(d); });
    var medY = d3.median(pts, function(d) { return yMetric.get(d); });

    var sp500LineColor = hasSectorOverlay ? (dark ? '#52525b' : '#a1a1aa') : '#00b4d8';
    var sp500LineOpacity = hasSectorOverlay ? 0.35 : 0.5;
    var sp500TextOpacity = hasSectorOverlay ? 0.45 : 0.7;

    // Only show median lines if the medians are within the scale domain
    var medXInRange = medX != null && isFinite(x(medX));
    var medYInRange = medY != null && isFinite(yScale(medY));

    if (medXInRange) {
        svg.append('line')
            .attr('x1', x(medX)).attr('x2', x(medX))
            .attr('y1', 0).attr('y2', h)
            .attr('stroke', sp500LineColor).attr('stroke-width', 1)
            .attr('stroke-dasharray', '6,4').attr('opacity', sp500LineOpacity);
        svg.append('text')
            .attr('x', x(medX) + 4).attr('y', hasSectorOverlay ? 24 : 12)
            .attr('fill', sp500LineColor).attr('font-size', '10px').attr('opacity', sp500TextOpacity)
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text((hasSectorOverlay ? 'S&P 500 ' : '') + 'Median ' + xMetric.fmt(medX));
    }

    if (medYInRange) {
        svg.append('line')
            .attr('x1', 0).attr('x2', w)
            .attr('y1', yScale(medY)).attr('y2', yScale(medY))
            .attr('stroke', sp500LineColor).attr('stroke-width', 1)
            .attr('stroke-dasharray', '6,4').attr('opacity', sp500LineOpacity);
        svg.append('text')
            .attr('x', w - 4).attr('y', yScale(medY) - 4)
            .attr('text-anchor', 'end')
            .attr('fill', sp500LineColor).attr('font-size', '10px').attr('opacity', sp500TextOpacity)
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text((hasSectorOverlay ? 'S&P 500 ' : '') + 'Median ' + yMetric.fmt(medY));
    }

    // Sector median crosshairs (when sector overlay is active)
    var secMedX, secMedY;
    if (hasSectorOverlay) {
        secMedX = d3.median(sectorPts, function(d) { return xMetric.get(d); });
        secMedY = d3.median(sectorPts, function(d) { return yMetric.get(d); });

        var secXInRange = secMedX != null && isFinite(x(secMedX));
        var secYInRange = secMedY != null && isFinite(yScale(secMedY));
        var shortSector = sectorName.replace('Information Technology', 'IT').replace('Communication Services', 'Comm Svcs').replace('Consumer Discretionary', 'Cons Disc').replace('Consumer Staples', 'Cons Stpls');

        if (secXInRange) {
            svg.append('line')
                .attr('x1', x(secMedX)).attr('x2', x(secMedX))
                .attr('y1', 0).attr('y2', h)
                .attr('stroke', sectorColor).attr('stroke-width', 1.5)
                .attr('stroke-dasharray', '8,4').attr('opacity', 0.7);
            svg.append('text')
                .attr('x', x(secMedX) + 4).attr('y', 12)
                .attr('fill', sectorColor).attr('font-size', '10px').attr('font-weight', '600')
                .attr('font-family', 'Inter, system-ui, sans-serif').attr('opacity', 0.9)
                .text(shortSector + ' ' + xMetric.fmt(secMedX));
        }

        if (secYInRange) {
            svg.append('line')
                .attr('x1', 0).attr('x2', w)
                .attr('y1', yScale(secMedY)).attr('y2', yScale(secMedY))
                .attr('stroke', sectorColor).attr('stroke-width', 1.5)
                .attr('stroke-dasharray', '8,4').attr('opacity', 0.7);
            svg.append('text')
                .attr('x', w - 4).attr('y', yScale(secMedY) + 14)
                .attr('text-anchor', 'end')
                .attr('fill', sectorColor).attr('font-size', '10px').attr('font-weight', '600')
                .attr('font-family', 'Inter, system-ui, sans-serif').attr('opacity', 0.9)
                .text(shortSector + ' ' + yMetric.fmt(secMedY));
        }

        // Crosshair intersection marker
        if (secXInRange && secYInRange) {
            svg.append('circle')
                .attr('cx', x(secMedX)).attr('cy', yScale(secMedY))
                .attr('r', 5)
                .attr('fill', 'none').attr('stroke', sectorColor).attr('stroke-width', 2)
                .attr('opacity', 0.8);
            svg.append('circle')
                .attr('cx', x(secMedX)).attr('cy', yScale(secMedY))
                .attr('r', 2)
                .attr('fill', sectorColor).attr('opacity', 0.8);
        }
    }

    // Quadrant statistics — count and percentage of companies in each quadrant
    // relative to the median crosshairs, for ALL axis combinations
    if (medXInRange && medYInRange) {
        var qDataSet = hasSectorOverlay ? sectorPts : pts;
        var qTotal = qDataSet.length;

        // Count companies in each quadrant (relative to median)
        var qRef = hasSectorOverlay ? { x: secMedX, y: secMedY } : { x: medX, y: medY };
        var qTL = 0, qTR = 0, qBL = 0, qBR = 0; // Top-left, Top-right, Bottom-left, Bottom-right
        qDataSet.forEach(function(c) {
            var xv = xMetric.get(c);
            var yv = yMetric.get(c);
            if (xv < qRef.x) {
                if (yv >= qRef.y) qTL++; else qBL++;
            } else {
                if (yv >= qRef.y) qTR++; else qBR++;
            }
        });

        function qPct(count) { return qTotal > 0 ? Math.round(count / qTotal * 100) : 0; }

        // Build quadrant descriptive labels — Low/High relative to X and Y metric short names
        var xShort = xMetric.shortLabel.replace('CEO Total ', '').replace('Median ', '');
        var yShort = yMetric.shortLabel.replace('CEO Total ', '').replace('Median ', '');

        // Position quadrant count labels in each corner with count and percentage
        var qMutedColor = typeof getThemeMutedColor === 'function' ? getThemeMutedColor() : '#6b7280';
        var qLabelColor = hasSectorOverlay ? sectorColor : qMutedColor;
        var qCountOpacity = hasSectorOverlay ? 0.55 : 0.45;
        var qLabelOpacity = hasSectorOverlay ? 0.35 : 0.3;

        var quadrants = [
            { count: qTL, pct: qPct(qTL), label: 'Low ' + xShort + ', High ' + yShort, x: 8, y: 14, countY: 26, anchor: 'start' },
            { count: qTR, pct: qPct(qTR), label: 'High ' + xShort + ', High ' + yShort, x: w - 8, y: 14, countY: 26, anchor: 'end' },
            { count: qBL, pct: qPct(qBL), label: 'Low ' + xShort + ', Low ' + yShort, x: 8, y: h - 20, countY: h - 8, anchor: 'start' },
            { count: qBR, pct: qPct(qBR), label: 'High ' + xShort + ', Low ' + yShort, x: w - 8, y: h - 20, countY: h - 8, anchor: 'end' }
        ];

        quadrants.forEach(function(q) {
            // Quadrant count (primary — larger)
            svg.append('text')
                .attr('class', 'scatter-quadrant-count')
                .attr('x', q.x).attr('y', q.countY)
                .attr('text-anchor', q.anchor)
                .attr('fill', qLabelColor)
                .attr('font-size', '11px')
                .attr('font-weight', '600')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .attr('opacity', qCountOpacity)
                .attr('pointer-events', 'none')
                .text(q.count + ' (' + q.pct + '%)');

            // Quadrant descriptor (secondary — smaller)
            svg.append('text')
                .attr('class', 'scatter-quadrant-label')
                .attr('x', q.x).attr('y', q.y)
                .attr('text-anchor', q.anchor)
                .attr('fill', qMutedColor)
                .attr('font-size', '8.5px')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .attr('opacity', qLabelOpacity)
                .attr('pointer-events', 'none')
                .text(q.label);
        });

        // Dominant quadrant narrative pill — identifies the most populated quadrant
        var maxQ = quadrants.reduce(function(best, q) { return q.count > best.count ? q : best; }, quadrants[0]);
        if (maxQ.pct >= 30 && qTotal >= 10) {
            var domLabel = maxQ.pct + '% of ' + (hasSectorOverlay ? sectorName : 'S&P 500') +
                ' companies have ' + maxQ.label.toLowerCase();
            var domG = svg.append('g').attr('class', 'scatter-quadrant-dominant');

            var domTextNode = domG.append('text')
                .attr('x', w / 2).attr('y', h + 58)
                .attr('text-anchor', 'middle')
                .attr('fill', hasSectorOverlay ? sectorColor : '#00b4d8')
                .attr('font-size', '10px')
                .attr('font-weight', '500')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .attr('opacity', 0.75)
                .text(domLabel);

            // Background pill
            var domBbox = domTextNode.node().getBBox();
            var dpx = 10, dpy = 4;
            var pillFill = dark ? 'rgba(0,180,216,0.06)' : 'rgba(0,180,216,0.05)';
            var pillStroke = dark ? 'rgba(0,180,216,0.15)' : 'rgba(0,180,216,0.12)';
            if (hasSectorOverlay) {
                // Extract sector color for pill
                var cMatch = sectorColor.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
                if (cMatch) {
                    var sr = parseInt(cMatch[1], 16), sg = parseInt(cMatch[2], 16), sb = parseInt(cMatch[3], 16);
                    pillFill = 'rgba(' + sr + ',' + sg + ',' + sb + ',' + (dark ? '0.06' : '0.05') + ')';
                    pillStroke = 'rgba(' + sr + ',' + sg + ',' + sb + ',' + (dark ? '0.15' : '0.12') + ')';
                }
            }
            domG.insert('rect', 'text')
                .attr('x', domBbox.x - dpx)
                .attr('y', domBbox.y - dpy)
                .attr('width', domBbox.width + dpx * 2)
                .attr('height', domBbox.height + dpy * 2)
                .attr('rx', 8)
                .attr('fill', pillFill)
                .attr('stroke', pillStroke)
                .attr('stroke-width', 1);
        }
    }

    // Compute Pearson correlation coefficient for the stats annotation
    var n = pts.length;
    var sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
    pts.forEach(function(c) {
        var xv = xMetric.get(c);
        var yv = yMetric.get(c);
        sumX += xv; sumY += yv;
        sumXY += xv * yv;
        sumX2 += xv * xv; sumY2 += yv * yv;
    });
    var denom = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
    var correlation = denom > 0 ? (n * sumXY - sumX * sumY) / denom : 0;
    var rSquared = correlation * correlation;

    // OLS regression line: y = slope * x + intercept
    var ssDenom = n * sumX2 - sumX * sumX;
    var slope = ssDenom !== 0 ? (n * sumXY - sumX * sumY) / ssDenom : 0;
    var intercept = ssDenom !== 0 ? (sumY - slope * sumX) / n : (sumY / n);

    // Draw regression trend line (if toggle is checked and |r| is meaningful)
    var showTrend = document.getElementById('scatter-trend-line') && document.getElementById('scatter-trend-line').checked;
    if (showTrend && Math.abs(correlation) >= 0.02 && ssDenom !== 0) {
        // Compute line endpoints from x domain, then clip to chart area
        var xDomain = x.domain();
        var x1Raw = xDomain[0];
        var x2Raw = xDomain[1];
        var y1Raw = slope * x1Raw + intercept;
        var y2Raw = slope * x2Raw + intercept;

        // Clip to y domain
        var yDomain = yScale.domain();
        var yLo = Math.min(yDomain[0], yDomain[1]);
        var yHi = Math.max(yDomain[0], yDomain[1]);

        // Parametric clipping: find t values where the line exits y bounds
        function clipLine(x1, y1, x2, y2, yMin, yMax) {
            var pts = [];
            // t goes from 0 (x1,y1) to 1 (x2,y2)
            // y(t) = y1 + t*(y2-y1)
            var dy = y2 - y1;
            var dx = x2 - x1;
            var tMin = 0, tMax = 1;
            if (dy !== 0) {
                var tAtYMin = (yMin - y1) / dy;
                var tAtYMax = (yMax - y1) / dy;
                if (dy > 0) {
                    tMin = Math.max(tMin, tAtYMin);
                    tMax = Math.min(tMax, tAtYMax);
                } else {
                    tMin = Math.max(tMin, tAtYMax);
                    tMax = Math.min(tMax, tAtYMin);
                }
            } else if (y1 < yMin || y1 > yMax) {
                return null; // horizontal line outside y bounds
            }
            if (tMin > tMax) return null;
            return {
                x1: x1 + tMin * dx, y1: y1 + tMin * dy,
                x2: x1 + tMax * dx, y2: y1 + tMax * dy
            };
        }

        // --- Pre-compute sector regression (needed for both CI band and line) ---
        var sectorReg = null;
        if (hasSectorOverlay && sectorPts.length >= 3) {
            var _sn = sectorPts.length;
            var _sSumX = 0, _sSumY = 0, _sSumXY = 0, _sSumX2 = 0, _sSumY2 = 0;
            sectorPts.forEach(function(c) {
                var xv = xMetric.get(c);
                var yv = yMetric.get(c);
                _sSumX += xv; _sSumY += yv;
                _sSumXY += xv * yv;
                _sSumX2 += xv * xv; _sSumY2 += yv * yv;
            });
            var _sDenom = _sn * _sSumX2 - _sSumX * _sSumX;
            var _sSlope = _sDenom !== 0 ? (_sn * _sSumXY - _sSumX * _sSumY) / _sDenom : 0;
            var _sIntercept = _sDenom !== 0 ? (_sSumY - _sSlope * _sSumX) / _sn : (_sSumY / _sn);
            var _sCorrDenom = Math.sqrt((_sn * _sSumX2 - _sSumX * _sSumX) * (_sn * _sSumY2 - _sSumY * _sSumY));
            var _sCorr = _sCorrDenom > 0 ? (_sn * _sSumXY - _sSumX * _sSumY) / _sCorrDenom : 0;
            sectorReg = { n: _sn, slope: _sSlope, intercept: _sIntercept, corr: _sCorr,
                          sumX: _sSumX, sumX2: _sSumX2 };
        }

        // --- 95% Confidence Interval Band ---
        // Compute standard error of the regression for CI shading
        var xMean = sumX / n;
        var ssResid = 0; // sum of squared residuals
        pts.forEach(function(c) {
            var xv = xMetric.get(c);
            var yv = yMetric.get(c);
            var predicted = slope * xv + intercept;
            ssResid += (yv - predicted) * (yv - predicted);
        });
        var mse = n > 2 ? ssResid / (n - 2) : 0; // mean squared error
        var sResid = Math.sqrt(mse); // standard error of regression
        var ssxDeviation = sumX2 - n * xMean * xMean; // Σ(xᵢ - x̄)²

        // Helper: generate CI band polygon path for any regression
        function buildCiBand(regSlope, regIntercept, regN, regSResid, regSsxDev, regXMean, bandXMin, bandXMax) {
            var regTCrit = regN > 120 ? 1.96 : regN > 60 ? 2.0 : regN > 30 ? 2.04 : regN > 15 ? 2.13 : 2.26;
            var steps = 60;
            var stepSize = (bandXMax - bandXMin) / steps;
            var upperPts = [];
            var lowerPts = [];

            for (var ci = 0; ci <= steps; ci++) {
                var ciX = bandXMin + ci * stepSize;
                var ciY = regSlope * ciX + regIntercept;
                // SE(ŷ) = s × √(1/n + (x₀ − x̄)² / Σ(xᵢ − x̄)²)
                var seY = regSResid * Math.sqrt(1.0 / regN + (ciX - regXMean) * (ciX - regXMean) / regSsxDev);
                var ciHalf = regTCrit * seY;
                var ciUpper = Math.max(yLo, Math.min(yHi, ciY + ciHalf));
                var ciLower = Math.max(yLo, Math.min(yHi, ciY - ciHalf));

                var pxX = x(ciX);
                if (pxX >= 0 && pxX <= w) {
                    upperPts.push({ x: pxX, y: yScale(ciUpper) });
                    lowerPts.push({ x: pxX, y: yScale(ciLower) });
                }
            }

            if (upperPts.length < 2) return null;
            var bandPts = upperPts.concat(lowerPts.reverse());
            return 'M' + bandPts.map(function(p) { return p.x.toFixed(1) + ',' + p.y.toFixed(1); }).join('L') + 'Z';
        }

        // Draw CI bands (behind regression lines) if enough data
        if (n >= 10 && sResid > 0 && ssxDeviation > 0) {
            var sp500BandPath = buildCiBand(slope, intercept, n, sResid, ssxDeviation, xMean, x1Raw, x2Raw);

            if (sp500BandPath) {
                if (hasSectorOverlay) {
                    // S&P 500 CI band in muted color
                    svg.append('path')
                        .attr('class', 'regression-ci-band regression-ci-sp500')
                        .attr('d', sp500BandPath)
                        .attr('fill', dark ? 'rgba(82,82,91,0.10)' : 'rgba(161,161,170,0.10)')
                        .attr('stroke', 'none')
                        .attr('pointer-events', 'none');

                    // Sector-specific CI band
                    if (sectorReg && sectorReg.n >= 10) {
                        var sxMean = sectorReg.sumX / sectorReg.n;
                        var sSsResid = 0;
                        sectorPts.forEach(function(c) {
                            var xv = xMetric.get(c);
                            var yv = yMetric.get(c);
                            var sPred = sectorReg.slope * xv + sectorReg.intercept;
                            sSsResid += (yv - sPred) * (yv - sPred);
                        });
                        var sSResid = Math.sqrt(sectorReg.n > 2 ? sSsResid / (sectorReg.n - 2) : 0);
                        var sSsxDev = sectorReg.sumX2 - sectorReg.n * sxMean * sxMean;

                        if (sSResid > 0 && sSsxDev > 0) {
                            var sCiXMin = d3.min(sectorPts, function(c) { return xMetric.get(c); });
                            var sCiXMax = d3.max(sectorPts, function(c) { return xMetric.get(c); });
                            var sCiRange = sCiXMax - sCiXMin;
                            sCiXMin -= sCiRange * 0.05;
                            sCiXMax += sCiRange * 0.05;

                            var sectorBandPath = buildCiBand(sectorReg.slope, sectorReg.intercept, sectorReg.n, sSResid, sSsxDev, sxMean, sCiXMin, sCiXMax);

                            if (sectorBandPath) {
                                var scMatch = sectorColor.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
                                var sCiFill = dark ? 'rgba(0,180,216,0.10)' : 'rgba(0,180,216,0.08)';
                                if (scMatch) {
                                    var scR = parseInt(scMatch[1], 16), scG = parseInt(scMatch[2], 16), scB = parseInt(scMatch[3], 16);
                                    sCiFill = 'rgba(' + scR + ',' + scG + ',' + scB + ',' + (dark ? '0.12' : '0.08') + ')';
                                }

                                svg.append('path')
                                    .attr('class', 'regression-ci-band regression-ci-sector')
                                    .attr('d', sectorBandPath)
                                    .attr('fill', sCiFill)
                                    .attr('stroke', 'none')
                                    .attr('pointer-events', 'none');
                            }
                        }
                    }
                } else {
                    // Standard (non-sector) CI band
                    var trendColor2 = Math.abs(correlation) >= 0.5 ? '#06d6a0' : Math.abs(correlation) >= 0.3 ? '#ffd166' : '#94a3b8';
                    var tcMatch = trendColor2.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
                    var ciFill = dark ? 'rgba(148,163,184,0.08)' : 'rgba(148,163,184,0.06)';
                    if (tcMatch) {
                        var tcR = parseInt(tcMatch[1], 16), tcG = parseInt(tcMatch[2], 16), tcB = parseInt(tcMatch[3], 16);
                        ciFill = 'rgba(' + tcR + ',' + tcG + ',' + tcB + ',' + (dark ? '0.12' : '0.08') + ')';
                    }

                    svg.append('path')
                        .attr('class', 'regression-ci-band')
                        .attr('d', sp500BandPath)
                        .attr('fill', ciFill)
                        .attr('stroke', 'none')
                        .attr('pointer-events', 'none');
                }
            }
        }

        // --- Regression Lines (on top of CI bands) ---
        var clipped = clipLine(x1Raw, y1Raw, x2Raw, y2Raw, yLo, yHi);
        if (clipped) {
            var trendColor = Math.abs(correlation) >= 0.5 ? '#06d6a0' : Math.abs(correlation) >= 0.3 ? '#ffd166' : '#94a3b8';

            if (hasSectorOverlay) {
                // S&P 500 regression in muted color behind sector line
                svg.append('line')
                    .attr('class', 'regression-line regression-line-sp500')
                    .attr('x1', x(clipped.x1)).attr('y1', yScale(clipped.y1))
                    .attr('x2', x(clipped.x2)).attr('y2', yScale(clipped.y2))
                    .attr('stroke', dark ? '#52525b' : '#a1a1aa')
                    .attr('stroke-width', 1.5)
                    .attr('stroke-dasharray', '8,6')
                    .attr('opacity', 0.3)
                    .attr('pointer-events', 'none');

                // Sector-specific regression line (uses pre-computed sectorReg)
                if (sectorReg && Math.abs(sectorReg.corr) >= 0.02) {
                    var sx1Raw = d3.min(sectorPts, function(c) { return xMetric.get(c); });
                    var sx2Raw = d3.max(sectorPts, function(c) { return xMetric.get(c); });
                    var sRange = sx2Raw - sx1Raw;
                    sx1Raw -= sRange * 0.05;
                    sx2Raw += sRange * 0.05;
                    var sy1Raw = sectorReg.slope * sx1Raw + sectorReg.intercept;
                    var sy2Raw = sectorReg.slope * sx2Raw + sectorReg.intercept;

                    var sClipped = clipLine(sx1Raw, sy1Raw, sx2Raw, sy2Raw, yLo, yHi);
                    if (sClipped) {
                        svg.append('line')
                            .attr('class', 'regression-line regression-line-sector')
                            .attr('x1', x(sClipped.x1)).attr('y1', yScale(sClipped.y1))
                            .attr('x2', x(sClipped.x2)).attr('y2', yScale(sClipped.y2))
                            .attr('stroke', sectorColor)
                            .attr('stroke-width', 2)
                            .attr('stroke-dasharray', '10,5')
                            .attr('opacity', 0.7)
                            .attr('pointer-events', 'none');
                    }
                }
            } else {
                // Standard regression line
                svg.append('line')
                    .attr('class', 'regression-line')
                    .attr('x1', x(clipped.x1)).attr('y1', yScale(clipped.y1))
                    .attr('x2', x(clipped.x2)).attr('y2', yScale(clipped.y2))
                    .attr('stroke', trendColor)
                    .attr('stroke-width', 2)
                    .attr('stroke-dasharray', '10,5')
                    .attr('opacity', 0.6)
                    .attr('pointer-events', 'none');
            }
        }
    }

    // Build tooltip HTML helper for a company
    function buildTooltip(d, includeVsSector) {
        var html = '<div class="ct-title">' + d.ticker + ' — ' + (d.company_name || '') + '</div>' +
            '<div class="ct-row"><span class="ct-label">CEO</span><span class="ct-val">' + (d.ceo_name || '—') + '</span></div>' +
            '<div class="ct-row"><span class="ct-label">' + xMetric.shortLabel + '</span><span class="ct-val">' + xMetric.fmt(xMetric.get(d)) + '</span></div>' +
            '<div class="ct-row"><span class="ct-label">' + yMetric.shortLabel + '</span><span class="ct-val">' + yMetric.fmt(yMetric.get(d)) + '</span></div>';
        // Always show total comp if not already on an axis
        if (xMetricKey !== 'total_compensation' && yMetricKey !== 'total_compensation') {
            html += '<div class="ct-row"><span class="ct-label">Total Comp</span><span class="ct-val">' + fmtCurr(d.total_compensation) + '</span></div>';
        }
        // Show sector if not in sector overlay mode
        if (!includeVsSector) {
            html += '<div class="ct-row"><span class="ct-label">Sector</span><span class="ct-val">' + (d.sector || '—') + '</span></div>';
        }
        // Show vs sector median for X metric in sector mode
        if (includeVsSector && secMedX != null && secMedX !== 0) {
            var vsX = ((xMetric.get(d) - secMedX) / Math.abs(secMedX) * 100);
            var vsXSign = vsX >= 0 ? '+' : '\u2212';
            var vsXStr = Math.abs(vsX) >= 100 ? Math.round(Math.abs(vsX)) + '%' : Math.abs(vsX).toFixed(1) + '%';
            html += '<div class="ct-row"><span class="ct-label">vs Sector</span><span class="ct-val">' + vsXSign + vsXStr + '</span></div>';
        }
        return html;
    }

    // Determine default dot opacity based on sector overlay state
    var defaultOpacity = hasSectorOverlay ? 0.12 : 0.7;
    var sectorDotOpacity = 0.9;

    // Dots — render non-sector dots first (background) then sector dots on top
    var nonSectorPts = hasSectorOverlay ? pts.filter(function(c) { return c.sector !== sectorName; }) : [];
    var sectorDotsData = hasSectorOverlay ? sectorPts : [];

    // Helper to get safe x/y position for a dot
    function dotX(d) { var v = x(xMetric.get(d)); return isFinite(v) ? v : -100; }
    function dotY(d) { var v = yScale(yMetric.get(d)); return isFinite(v) ? v : -100; }

    // Background dots (non-sector) when sector overlay is active
    if (hasSectorOverlay) {
        svg.selectAll('.scatter-dot-bg')
            .data(nonSectorPts)
            .join('circle')
            .attr('class', 'scatter-dot scatter-dot-bg')
            .attr('cx', dotX)
            .attr('cy', dotY)
            .attr('r', function(d) { return r(d.total_compensation || 0); })
            .attr('fill', function(d) { return dark ? '#3f3f46' : '#d4d4d8'; })
            .attr('opacity', defaultOpacity)
            .attr('stroke', 'none')
            .style('cursor', 'pointer')
            .on('mouseover', function(event, d) {
                d3.select(this).attr('opacity', 0.6).attr('stroke', chartStrokeColor()).attr('stroke-width', 1)
                    .attr('r', r(d.total_compensation || 0) + 2);
                showChartTooltip(event, buildTooltip(d, false));
            })
            .on('mousemove', function(event) { positionChartTooltip(event); })
            .on('mouseout', function(event, d) {
                d3.select(this).attr('opacity', defaultOpacity).attr('stroke', 'none')
                    .attr('r', r(d.total_compensation || 0));
                hideChartTooltip();
            })
            .on('click', function(event, d) {
                if (typeof window.findCompanyInTable === 'function') {
                    window.findCompanyInTable(d.ticker);
                }
            });

        // Sector dots (foreground — rendered on top)
        svg.selectAll('.scatter-dot-sector')
            .data(sectorDotsData)
            .join('circle')
            .attr('class', 'scatter-dot scatter-dot-sector')
            .attr('cx', dotX)
            .attr('cy', dotY)
            .attr('r', function(d) { return r(d.total_compensation || 0); })
            .attr('fill', sectorColor)
            .attr('opacity', sectorDotOpacity)
            .attr('stroke', dark ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.15)')
            .attr('stroke-width', 1)
            .style('cursor', 'pointer')
            .on('mouseover', function(event, d) {
                d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 2)
                    .attr('r', r(d.total_compensation || 0) + 2);
                svg.selectAll('.scatter-dot-sector').filter(function(o) { return o !== d; })
                    .attr('opacity', 0.45);
                showChartTooltip(event, buildTooltip(d, true));
            })
            .on('mousemove', function(event) { positionChartTooltip(event); })
            .on('mouseout', function(event, d) {
                d3.select(this).attr('opacity', sectorDotOpacity)
                    .attr('stroke', dark ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.15)')
                    .attr('stroke-width', 1)
                    .attr('r', r(d.total_compensation || 0));
                svg.selectAll('.scatter-dot-sector').attr('opacity', sectorDotOpacity);
                hideChartTooltip();
            })
            .on('click', function(event, d) {
                if (typeof window.findCompanyInTable === 'function') {
                    window.findCompanyInTable(d.ticker);
                }
            });
    } else {
        // No sector overlay — standard rendering
        svg.selectAll('.scatter-dot')
            .data(pts)
            .join('circle')
            .attr('class', 'scatter-dot')
            .attr('cx', dotX)
            .attr('cy', dotY)
            .attr('r', function(d) { return r(d.total_compensation || 0); })
            .attr('fill', function(d) { return SECTOR_COLORS[d.sector] || '#94a3b8'; })
            .attr('opacity', 0.7)
            .attr('stroke', 'none')
            .style('cursor', 'pointer')
            .on('mouseover', function(event, d) {
                d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5)
                    .attr('r', r(d.total_compensation || 0) + 2);
                svg.selectAll('.scatter-dot').filter(function(o) { return o !== d; })
                    .attr('opacity', 0.2);
                showChartTooltip(event, buildTooltip(d, false));
            })
            .on('mousemove', function(event) { positionChartTooltip(event); })
            .on('mouseout', function(event, d) {
                d3.select(this).attr('opacity', 0.7).attr('stroke', 'none')
                    .attr('r', r(d.total_compensation || 0));
                svg.selectAll('.scatter-dot').attr('opacity', 0.7);
                hideChartTooltip();
            })
            .on('click', function(event, d) {
                if (typeof window.findCompanyInTable === 'function') {
                    window.findCompanyInTable(d.ticker);
                }
            });
    }

    // Label outliers — top by X and Y values from the relevant set
    var outlierSet = hasSectorOverlay ? sectorPts : pts;
    var topX = outlierSet.slice().sort(function(a, b) { return xMetric.get(b) - xMetric.get(a); }).slice(0, 5);
    var topY = outlierSet.slice().sort(function(a, b) { return yMetric.get(b) - yMetric.get(a); }).slice(0, 3);
    var labeled = {};
    var labelsArr = [];
    topX.concat(topY).forEach(function(d) {
        if (labeled[d.ticker]) return;
        labeled[d.ticker] = true;
        labelsArr.push(d);
    });

    svg.selectAll('.scatter-label')
        .data(labelsArr)
        .join('text')
        .attr('class', 'scatter-label')
        .attr('x', function(d) { return dotX(d) + r(d.total_compensation || 0) + 4; })
        .attr('y', function(d) { return dotY(d) + 3; })
        .attr('fill', hasSectorOverlay ? sectorColor : (typeof getThemeTextColor === 'function' ? getThemeTextColor() : '#e4e4e7'))
        .attr('font-size', '10px')
        .attr('font-weight', hasSectorOverlay ? '600' : '500')
        .attr('pointer-events', 'none')
        .text(function(d) { return d.ticker; });

    // Stats annotation (bottom-right corner)
    var statsGroup = svg.append('g')
        .attr('class', 'scatter-sector-stats')
        .attr('transform', 'translate(' + (w - 8) + ',' + (h - 68) + ')');

    if (hasSectorOverlay) {
        var secMedXVal = secMedX;
        var secMedYVal = secMedY;
        var vsIndexX = medX != null && medX !== 0 ? ((secMedXVal - medX) / Math.abs(medX) * 100) : 0;
        var vsIndexY = medY != null && medY !== 0 ? ((secMedYVal - medY) / Math.abs(medY) * 100) : 0;
        var vsXSign = vsIndexX >= 0 ? '+' : '\u2212';
        var vsYSign = vsIndexY >= 0 ? '+' : '\u2212';
        var vsXStr = Math.abs(vsIndexX).toFixed(0) + '%';
        var vsYStr = Math.abs(vsIndexY).toFixed(0) + '%';

        statsGroup.append('rect')
            .attr('x', -160).attr('y', -4)
            .attr('width', 168).attr('height', 72)
            .attr('rx', 6)
            .attr('fill', dark ? 'rgba(24,24,27,0.85)' : 'rgba(255,255,255,0.9)')
            .attr('stroke', dark ? 'rgba(63,63,70,0.5)' : 'rgba(212,212,216,0.6)')
            .attr('stroke-width', 1);

        statsGroup.append('text')
            .attr('x', -152).attr('y', 12)
            .attr('fill', sectorColor).attr('font-size', '11px').attr('font-weight', '700')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(sectorName.length > 22 ? sectorName.substring(0, 20) + '\u2026' : sectorName);

        statsGroup.append('text')
            .attr('x', -152).attr('y', 28)
            .attr('fill', dark ? '#a1a1aa' : '#6b7280').attr('font-size', '10px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(sectorPts.length + ' cos \u00B7 Med X: ' + xMetric.fmt(secMedXVal));

        statsGroup.append('text')
            .attr('x', -152).attr('y', 42)
            .attr('fill', dark ? '#a1a1aa' : '#6b7280').attr('font-size', '10px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('Med Y: ' + yMetric.fmt(secMedYVal));

        statsGroup.append('text')
            .attr('x', -152).attr('y', 58)
            .attr('fill', dark ? '#71717a' : '#9ca3af').attr('font-size', '9px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('vs Index: ' + vsXSign + vsXStr + ' X, ' + vsYSign + vsYStr + ' Y · r=' + correlation.toFixed(2) + ' R\u00B2=' + rSquared.toFixed(2));
    } else {
        // Show correlation annotation for non-sector mode
        var corrColor = Math.abs(correlation) >= 0.5 ? '#06d6a0' : Math.abs(correlation) >= 0.3 ? '#ffd166' : '#94a3b8';
        var corrLabel = Math.abs(correlation) >= 0.7 ? 'Strong' : Math.abs(correlation) >= 0.5 ? 'Moderate' : Math.abs(correlation) >= 0.3 ? 'Weak' : 'Very Weak';
        corrLabel += correlation < 0 ? ' Negative' : ' Positive';

        var showTrendStats = showTrend && Math.abs(correlation) >= 0.02 && ssDenom !== 0;
        var showCIInfo = showTrendStats && n >= 10;
        var statsBoxH = showCIInfo ? 72 : showTrendStats ? 60 : 46;

        statsGroup.append('rect')
            .attr('x', -140).attr('y', -4)
            .attr('width', 148).attr('height', statsBoxH)
            .attr('rx', 6)
            .attr('fill', dark ? 'rgba(24,24,27,0.85)' : 'rgba(255,255,255,0.9)')
            .attr('stroke', dark ? 'rgba(63,63,70,0.5)' : 'rgba(212,212,216,0.6)')
            .attr('stroke-width', 1);

        statsGroup.append('text')
            .attr('x', -132).attr('y', 14)
            .attr('fill', corrColor).attr('font-size', '11px').attr('font-weight', '700')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('r = ' + correlation.toFixed(3) + (showTrendStats ? '  R\u00B2 = ' + rSquared.toFixed(3) : ''));

        statsGroup.append('text')
            .attr('x', -132).attr('y', 30)
            .attr('fill', dark ? '#a1a1aa' : '#6b7280').attr('font-size', '10px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(corrLabel + ' · n=' + pts.length);

        if (showTrendStats) {
            // Format slope in human-readable terms
            var slopeStr = '';
            if (Math.abs(slope) >= 1000) slopeStr = (slope / 1000).toFixed(1) + 'K';
            else if (Math.abs(slope) >= 1) slopeStr = slope.toFixed(2);
            else if (Math.abs(slope) >= 0.01) slopeStr = slope.toFixed(4);
            else slopeStr = slope.toExponential(1);
            statsGroup.append('text')
                .attr('x', -132).attr('y', 46)
                .attr('fill', dark ? '#71717a' : '#9ca3af').attr('font-size', '9px')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .text('slope: ' + slopeStr + ' · ' + xMetric.shortLabel + ' \u2192 ' + yMetric.shortLabel);

            // 95% CI band label
            if (showCIInfo) {
                statsGroup.append('text')
                    .attr('x', -132).attr('y', 60)
                    .attr('fill', dark ? '#52525b' : '#a1a1aa').attr('font-size', '8px')
                    .attr('font-family', 'Inter, system-ui, sans-serif')
                    .text('Shaded area = 95% confidence interval');
            }
        }
    }

    // === Brush Selection ===
    // Users can click-and-drag on empty space to select a rectangular region of dots
    // Dots remain hoverable/clickable — brush activates only on empty space
    var brushResultsEl = document.getElementById('scatter-brush-results');
    var brushG = svg.append('g').attr('class', 'scatter-brush-layer');

    // Track whether a dot is currently under the pointer
    var _dotUnderPointer = false;
    svg.selectAll('.scatter-dot, .scatter-dot-bg, .scatter-dot-sector')
        .on('mouseenter.brushtrack', function() { _dotUnderPointer = true; })
        .on('mouseleave.brushtrack', function() { _dotUnderPointer = false; });

    var brush = d3.brush()
        .extent([[0, 0], [w, h]])
        .filter(function(event) {
            // Don't start brush if pointer is over a dot — let dot events handle it
            if (_dotUnderPointer) return false;
            // Only left-click, no ctrl/meta
            return !event.ctrlKey && !event.metaKey && !event.button;
        })
        .on('start', function(event) {
            if (event.sourceEvent && event.sourceEvent.type === 'mousedown') {
                hideChartTooltip();
            }
        })
        .on('brush', function(event) {
            if (!event.selection) return;
            var sel = event.selection;
            // Dim dots outside selection
            svg.selectAll('.scatter-dot, .scatter-dot-bg, .scatter-dot-sector').each(function(d) {
                var cx = dotX(d), cy = dotY(d);
                var inside = cx >= sel[0][0] && cx <= sel[1][0] && cy >= sel[0][1] && cy <= sel[1][1];
                d3.select(this).attr('opacity', inside ? 1 : 0.08);
            });
        })
        .on('end', function(event) {
            if (!event.selection) {
                // Brush cleared — restore opacities
                if (hasSectorOverlay) {
                    svg.selectAll('.scatter-dot-bg').attr('opacity', defaultOpacity);
                    svg.selectAll('.scatter-dot-sector').attr('opacity', sectorDotOpacity);
                } else {
                    svg.selectAll('.scatter-dot').attr('opacity', 0.7);
                }
                if (brushResultsEl) brushResultsEl.style.display = 'none';
                return;
            }
            var sel = event.selection;
            // Find companies inside selection
            var selected = pts.filter(function(d) {
                var cx = dotX(d), cy = dotY(d);
                return cx >= sel[0][0] && cx <= sel[1][0] && cy >= sel[0][1] && cy <= sel[1][1];
            });
            _renderBrushResults(selected, xMetric, yMetric, brushResultsEl, brushG, brush, svg, hasSectorOverlay, defaultOpacity, sectorDotOpacity);
        });

    brushG.call(brush);
    // Remove brush overlay rect default fill — let dots underneath handle events normally when not brushing
    brushG.select('.overlay').attr('fill', 'none').attr('pointer-events', 'all').style('cursor', 'crosshair');
    brushG.select('.selection')
        .attr('fill', dark ? 'rgba(0,180,216,0.12)' : 'rgba(0,180,216,0.08)')
        .attr('stroke', dark ? 'rgba(0,180,216,0.5)' : 'rgba(0,180,216,0.4)')
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '4,3');
    brushG.selectAll('.handle').attr('fill', dark ? 'rgba(0,180,216,0.35)' : 'rgba(0,180,216,0.3)');

    // Expose global clear function for Escape key integration
    window._clearScatterBrush = function() {
        brushG.call(brush.move, null);
        if (hasSectorOverlay) {
            svg.selectAll('.scatter-dot-bg').attr('opacity', defaultOpacity);
            svg.selectAll('.scatter-dot-sector').attr('opacity', sectorDotOpacity);
        } else {
            svg.selectAll('.scatter-dot').attr('opacity', 0.7);
        }
        if (brushResultsEl) brushResultsEl.style.display = 'none';
    };

    // Hint text for brush
    svg.append('text')
        .attr('class', 'scatter-brush-hint')
        .attr('x', w / 2).attr('y', h + 66)
        .attr('text-anchor', 'middle')
        .attr('fill', dark ? '#52525b' : '#a1a1aa')
        .attr('font-size', '9px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .attr('pointer-events', 'none')
        .text('Drag on empty space to select a region · Click dots to view details · Esc to clear');

    // Apply any pending scatter highlight (cross-chart navigation)
    _applyScatterHighlight();
}

function _renderBrushResults(selected, xMetric, yMetric, container, brushG, brush, svg, hasSectorOverlay, defaultOpacity, sectorDotOpacity) {
    if (!container) return;
    if (selected.length === 0) {
        container.style.display = 'none';
        return;
    }

    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;

    // Sort by total comp descending
    selected.sort(function(a, b) { return (b.total_compensation || 0) - (a.total_compensation || 0); });

    // Compute aggregate stats
    var xVals = selected.map(function(c) { return xMetric.get(c); }).filter(function(v) { return v != null; }).sort(function(a, b) { return a - b; });
    var yVals = selected.map(function(c) { return yMetric.get(c); }).filter(function(v) { return v != null; }).sort(function(a, b) { return a - b; });
    var medianX = xVals.length > 0 ? xVals[Math.floor(xVals.length / 2)] : null;
    var medianY = yVals.length > 0 ? yVals[Math.floor(yVals.length / 2)] : null;
    var totalComp = selected.reduce(function(s, c) { return s + (c.total_compensation || 0); }, 0);

    // Sector breakdown
    var sectorCounts = {};
    selected.forEach(function(c) {
        var s = c.sector || 'Unknown';
        sectorCounts[s] = (sectorCounts[s] || 0) + 1;
    });
    var sectorList = Object.keys(sectorCounts).sort(function(a, b) { return sectorCounts[b] - sectorCounts[a]; });

    var html = '<div class="sbr-header">';
    html += '<div class="sbr-title"><span class="sbr-count">' + selected.length + '</span> companies selected</div>';
    html += '<button class="sbr-clear" title="Clear selection (Esc)">✕ Clear</button>';
    html += '</div>';

    // Stats bar
    html += '<div class="sbr-stats">';
    html += '<span class="sbr-stat">Median ' + xMetric.shortLabel + ': <b>' + xMetric.fmt(medianX) + '</b></span>';
    html += '<span class="sbr-stat">Median ' + yMetric.shortLabel + ': <b>' + yMetric.fmt(medianY) + '</b></span>';
    html += '<span class="sbr-stat">Combined Pay: <b>' + fmtCurr(totalComp) + '</b></span>';
    html += '</div>';

    // Sector badges
    html += '<div class="sbr-sectors">';
    sectorList.forEach(function(s) {
        var color = typeof getSectorColor === 'function' ? getSectorColor(s) : '#94a3b8';
        html += '<span class="sbr-sector-badge" style="border-color:' + color + ';color:' + color + '">' + s.replace('Information Technology', 'IT').replace('Communication Services', 'Comm Svcs').replace('Consumer Discretionary', 'Cons Disc').replace('Consumer Staples', 'Cons Stpls') + ' <b>' + sectorCounts[s] + '</b></span>';
    });
    html += '</div>';

    // Company list
    html += '<div class="sbr-list-wrap"><table class="sbr-list">';
    html += '<tr class="sbr-list-header"><th>Ticker</th><th>Company</th><th>CEO</th><th>' + xMetric.shortLabel + '</th><th>' + yMetric.shortLabel + '</th><th>Total Comp</th></tr>';
    var showAll = selected.length <= 20;
    var displayList = showAll ? selected : selected.slice(0, 15);
    displayList.forEach(function(c) {
        var sColor = typeof getSectorColor === 'function' ? getSectorColor(c.sector) : '#94a3b8';
        html += '<tr class="sbr-row" data-ticker="' + c.ticker + '" style="cursor:pointer">';
        html += '<td><span class="sbr-dot" style="background:' + sColor + '"></span><b>' + c.ticker + '</b></td>';
        html += '<td>' + (c.company_name || '') + '</td>';
        html += '<td>' + (c.ceo_name || '—') + '</td>';
        html += '<td class="sbr-mono">' + xMetric.fmt(xMetric.get(c)) + '</td>';
        html += '<td class="sbr-mono">' + yMetric.fmt(yMetric.get(c)) + '</td>';
        html += '<td class="sbr-mono">' + fmtCurr(c.total_compensation) + '</td>';
        html += '</tr>';
    });
    if (!showAll) {
        html += '<tr class="sbr-more"><td colspan="6">+ ' + (selected.length - 15) + ' more companies in selection</td></tr>';
    }
    html += '</table></div>';

    container.innerHTML = html;
    container.style.display = 'block';

    // Wire click handlers
    container.querySelectorAll('.sbr-row').forEach(function(row) {
        row.addEventListener('click', function() {
            var ticker = row.dataset.ticker;
            if (typeof window.findCompanyInTable === 'function') {
                window.findCompanyInTable(ticker);
            }
        });
    });

    // Wire clear button
    var clearBtn = container.querySelector('.sbr-clear');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            brushG.call(brush.move, null);
            if (hasSectorOverlay) {
                svg.selectAll('.scatter-dot-bg').attr('opacity', defaultOpacity);
                svg.selectAll('.scatter-dot-sector').attr('opacity', sectorDotOpacity);
            } else {
                svg.selectAll('.scatter-dot').attr('opacity', 0.7);
            }
            container.style.display = 'none';
        });
    }
}

/* === YoY Compensation Change Distribution === */
function drawYoYDistChart(companies) {
    var container = document.getElementById('yoy-dist-chart');
    if (!container) return;
    container.innerHTML = '';

    // Collect companies with YoY data
    var yoyData = companies.filter(function(c) {
        return c._ceoYoY && c._ceoYoY.pctChange != null && isFinite(c._ceoYoY.pctChange);
    }).map(function(c) {
        return {
            ticker: c.ticker,
            name: c.company_name,
            ceo: c.ceo_name,
            pct: c._ceoYoY.pctChange,
            from: c._ceoYoY.fromComp,
            to: c._ceoYoY.toComp,
            sector: c.sector
        };
    });

    if (yoyData.length < 10) return;

    // Define buckets
    var buckets = [
        { label: '< −50%', min: -Infinity, max: -50, color: '#dc2626' },
        { label: '−50% to −20%', min: -50, max: -20, color: '#ef4444' },
        { label: '−20% to −5%', min: -20, max: -5, color: '#f97316' },
        { label: '−5% to +5%', min: -5, max: 5, color: '#94a3b8' },
        { label: '+5% to +20%', min: 5, max: 20, color: '#22c55e' },
        { label: '+20% to +50%', min: 20, max: 50, color: '#06d6a0' },
        { label: '> +50%', min: 50, max: Infinity, color: '#00b4d8' }
    ];

    buckets.forEach(function(b) {
        b.companies = yoyData.filter(function(d) {
            if (b.max === Infinity) return d.pct >= b.min;
            if (b.min === -Infinity) return d.pct < b.max;
            return d.pct >= b.min && d.pct < b.max;
        });
        b.count = b.companies.length;
    });

    var maxCount = Math.max.apply(null, buckets.map(function(b) { return b.count; }));
    if (maxCount === 0) return;

    // Compute summary stats
    var allPcts = yoyData.map(function(d) { return d.pct; }).sort(function(a, b) { return a - b; });
    var medianPct = allPcts[Math.floor(allPcts.length / 2)];
    var meanPct = allPcts.reduce(function(s, v) { return s + v; }, 0) / allPcts.length;
    var raisedCount = yoyData.filter(function(d) { return d.pct > 5; }).length;
    var cutCount = yoyData.filter(function(d) { return d.pct < -5; }).length;
    var flatCount = yoyData.filter(function(d) { return d.pct >= -5 && d.pct <= 5; }).length;

    // Dimensions
    var rect = container.getBoundingClientRect();
    var width = Math.max(rect.width, 300);
    var height = 280;
    var margin = { top: 36, right: 20, bottom: 56, left: 44 };
    var innerW = width - margin.left - margin.right;
    var innerH = height - margin.top - margin.bottom;

    var svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', '0 0 ' + width + ' ' + height)
        .attr('role', 'img')
        .attr('aria-label', 'Year-over-year CEO compensation change distribution');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleBand()
        .domain(buckets.map(function(b) { return b.label; }))
        .range([0, innerW])
        .padding(0.15);

    var y = d3.scaleLinear()
        .domain([0, maxCount * 1.15])
        .range([innerH, 0]);

    // Grid lines
    var gridTicks = y.ticks(5);
    g.selectAll('.grid-line')
        .data(gridTicks)
        .join('line')
        .attr('class', 'grid-line')
        .attr('x1', 0)
        .attr('x2', innerW)
        .attr('y1', function(d) { return y(d); })
        .attr('y2', function(d) { return y(d); })
        .attr('stroke', typeof getThemeMutedColor === 'function' ? getThemeMutedColor() : '#6b7280')
        .attr('stroke-opacity', 0.15)
        .attr('stroke-dasharray', '3,3');

    // Bars
    var bars = g.selectAll('.yoy-bar')
        .data(buckets)
        .join('g')
        .attr('class', 'yoy-bar')
        .attr('transform', function(b) { return 'translate(' + x(b.label) + ',0)'; });

    bars.append('rect')
        .attr('y', function(b) { return y(b.count); })
        .attr('width', x.bandwidth())
        .attr('height', function(b) { return innerH - y(b.count); })
        .attr('fill', function(b) { return b.color; })
        .attr('opacity', function(b) {
            var ab = window._activeYoYBucket;
            if (ab) return (b.min === ab.min && b.max === ab.max) ? 1 : 0.3;
            return 0.8;
        })
        .each(function(b) {
            var ab = window._activeYoYBucket;
            if (ab && b.min === ab.min && b.max === ab.max) {
                d3.select(this).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
            }
        })
        .attr('rx', 3)
        .on('mouseenter', function(event, b) {
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
            var topCompanies = b.companies.slice().sort(function(a, c) {
                return Math.abs(c.pct) - Math.abs(a.pct);
            }).slice(0, 5);
            var compList = topCompanies.map(function(d) {
                var sign = d.pct >= 0 ? '+' : '';
                return '<strong>' + d.ticker + '</strong> ' + sign + d.pct.toFixed(1) + '%';
            }).join('<br>');
            var html = '<div style="font-weight:600;margin-bottom:4px">' + b.label + '</div>';
            html += '<div>' + b.count + ' companies (' + (b.count / yoyData.length * 100).toFixed(1) + '%)</div>';
            if (compList) html += '<div style="margin-top:6px;font-size:0.75rem;opacity:0.85">' + compList + '</div>';
            showChartTooltip(event, html);
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseleave', function(event, b) {
            var ab = window._activeYoYBucket;
            var isActive = ab && b.min === ab.min && b.max === ab.max;
            d3.select(this)
                .attr('opacity', isActive ? 1 : (ab ? 0.3 : 0.8))
                .attr('stroke', isActive ? chartStrokeColor() : 'none')
                .attr('stroke-width', isActive ? 1.5 : 0);
            hideChartTooltip();
        })
        .on('click', function(event, b) {
            // Filter table to companies in this YoY bucket
            if (typeof window.filterByYoYBucket === 'function') {
                window.filterByYoYBucket(b.min, b.max, b.label);
            }
        });

    // Count labels on bars
    bars.append('text')
        .attr('x', x.bandwidth() / 2)
        .attr('y', function(b) { return y(b.count) - 5; })
        .attr('text-anchor', 'middle')
        .attr('fill', typeof getThemeTextColor === 'function' ? getThemeTextColor() : '#e4e4e7')
        .attr('font-size', '11px')
        .attr('font-weight', '600')
        .attr('opacity', function(b) {
            var ab = window._activeYoYBucket;
            if (ab) return (b.min === ab.min && b.max === ab.max) ? 1 : 0.4;
            return 1;
        })
        .text(function(b) { return b.count > 0 ? b.count : ''; });

    // X axis
    g.append('g')
        .attr('transform', 'translate(0,' + innerH + ')')
        .call(d3.axisBottom(x).tickSize(0))
        .select('.domain').remove();

    g.selectAll('.tick text')
        .attr('fill', typeof getThemeSecondaryColor === 'function' ? getThemeSecondaryColor() : '#a1a1aa')
        .attr('font-size', '9px')
        .attr('transform', 'rotate(-25)')
        .attr('text-anchor', 'end')
        .attr('dx', '-0.3em')
        .attr('dy', '0.5em');

    // Y axis
    g.append('g')
        .call(d3.axisLeft(y).ticks(5).tickFormat(function(d) { return d; }))
        .select('.domain').remove();

    g.selectAll('.tick line').attr('stroke-opacity', 0.2);
    g.selectAll('.tick text')
        .attr('fill', typeof getThemeSecondaryColor === 'function' ? getThemeSecondaryColor() : '#a1a1aa')
        .attr('font-size', '10px');

    // Summary annotation
    var summaryText = raisedCount + ' raised · ' + flatCount + ' flat · ' + cutCount + ' cut';
    summaryText += ' · median ' + (medianPct >= 0 ? '+' : '') + medianPct.toFixed(1) + '%';

    svg.append('text')
        .attr('x', margin.left)
        .attr('y', 16)
        .attr('fill', typeof getThemeTextColor === 'function' ? getThemeTextColor() : '#e4e4e7')
        .attr('font-size', '11px')
        .attr('font-weight', '500')
        .text(summaryText);

    // Median line
    var medianBucket = buckets.find(function(b) {
        if (b.max === Infinity) return medianPct >= b.min;
        if (b.min === -Infinity) return medianPct < b.max;
        return medianPct >= b.min && medianPct < b.max;
    });
    if (medianBucket) {
        var medianX = x(medianBucket.label) + x.bandwidth() / 2;
        g.append('line')
            .attr('x1', medianX).attr('x2', medianX)
            .attr('y1', 0).attr('y2', innerH)
            .attr('stroke', '#ffd166')
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '4,3')
            .attr('opacity', 0.7);
        g.append('text')
            .attr('x', medianX + 4)
            .attr('y', 8)
            .attr('fill', '#ffd166')
            .attr('font-size', '9px')
            .attr('font-weight', '500')
            .text('median');
    }
}

/* --- Lorenz Curve: CEO Compensation Inequality --- */
function drawLorenzChart(companies) {
    var container = document.getElementById('lorenz-chart');
    if (!container) return;
    container.innerHTML = '';

    var withComp = companies.filter(function(c) { return c.total_compensation > 0; });
    if (withComp.length < 5) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient data for Lorenz curve</p>';
        return;
    }

    // Sector overlay mode
    var sectorName = window._activeSector || null;
    var sectorCompanies = sectorName ? withComp.filter(function(c) { return c.sector === sectorName; }) : null;
    var hasSectorOverlay = sectorCompanies && sectorCompanies.length >= 5;
    var sectorColor = hasSectorOverlay && typeof getSectorColor === 'function' ? getSectorColor(sectorName) : '#00b4d8';

    // Helper: build Lorenz points and stats from a sorted array
    function buildLorenz(arr) {
        var sArr = arr.slice().sort(function(a, b) { return a - b; });
        var ln = sArr.length;
        var lTotal = sArr.reduce(function(s, v) { return s + v; }, 0);
        var pts = [{ popPct: 0, compPct: 0 }];
        var cum = 0;
        for (var li = 0; li < ln; li++) {
            cum += sArr[li];
            pts.push({ popPct: (li + 1) / ln, compPct: cum / lTotal });
        }
        var gs = 0;
        for (var gi2 = 0; gi2 < ln; gi2++) {
            gs += (2 * (gi2 + 1) - ln - 1) * sArr[gi2];
        }
        var gCoeff = lTotal > 0 ? (gs / (ln * lTotal)) : 0;
        var t10i = Math.floor(ln * 0.9);
        var t10 = sArr.slice(t10i).reduce(function(s, v) { return s + v; }, 0);
        var b50i = Math.floor(ln * 0.5);
        var b50 = sArr.slice(0, b50i).reduce(function(s, v) { return s + v; }, 0);
        return {
            sorted: sArr, points: pts, n: ln, total: lTotal, gini: gCoeff,
            top10Pct: lTotal > 0 ? t10 / lTotal : 0,
            bot50Pct: lTotal > 0 ? b50 / lTotal : 0
        };
    }

    // S&P 500 Lorenz
    var sp500 = buildLorenz(withComp.map(function(c) { return c.total_compensation; }));
    var lorenzPoints = sp500.points;
    var sorted = sp500.sorted;
    var n = sp500.n;
    var gini = sp500.gini;

    // Sector Lorenz
    var sectorLorenz = null;
    if (hasSectorOverlay) {
        sectorLorenz = buildLorenz(sectorCompanies.map(function(c) { return c.total_compensation; }));
    }

    // Key percentile breakpoints for annotations (S&P 500)
    var breakpoints = [
        { label: 'Bottom 50%', idx: Math.floor(n * 0.5) },
        { label: 'Bottom 75%', idx: Math.floor(n * 0.75) },
        { label: 'Bottom 90%', idx: Math.floor(n * 0.90) },
        { label: 'Bottom 95%', idx: Math.floor(n * 0.95) }
    ];
    breakpoints.forEach(function(bp) {
        var cumBp = 0;
        for (var j = 0; j < bp.idx; j++) cumBp += sorted[j];
        bp.compPct = cumBp / sp500.total;
        bp.popPct = bp.idx / n;
    });

    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
    var margin = { top: 24, right: 30, bottom: hasSectorOverlay ? 80 : 50, left: 55 };
    var w = container.clientWidth - margin.left - margin.right;
    var h = Math.min(360, Math.max(280, w * 0.85));

    var ariaLabel = hasSectorOverlay
        ? 'Lorenz curve: ' + sectorName + ' (Gini ' + sectorLorenz.gini.toFixed(3) + ') vs S&P 500 (Gini ' + gini.toFixed(3) + ')'
        : 'Lorenz curve showing CEO compensation inequality across the S&P 500. Gini coefficient: ' + gini.toFixed(3);

    var svg = d3.select('#lorenz-chart').append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .attr('role', 'img')
        .attr('aria-label', ariaLabel)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleLinear().domain([0, 1]).range([0, w]);
    var y = d3.scaleLinear().domain([0, 1]).range([h, 0]);

    // Grid lines
    svg.append('g').attr('class', 'grid')
        .call(d3.axisBottom(x).tickSize(h).tickFormat('').ticks(5))
        .attr('transform', 'translate(0,0)')
        .selectAll('line').attr('stroke-opacity', 0.12);

    svg.append('g').attr('class', 'grid')
        .call(d3.axisLeft(y).tickSize(-w).tickFormat('').ticks(5))
        .selectAll('line').attr('stroke-opacity', 0.12);

    // X axis
    svg.append('g').attr('class', 'axis')
        .attr('transform', 'translate(0,' + h + ')')
        .call(d3.axisBottom(x).ticks(5).tickFormat(function(d) { return Math.round(d * 100) + '%'; }));

    svg.append('text')
        .attr('x', w / 2).attr('y', h + 40)
        .attr('text-anchor', 'middle')
        .attr('fill', dark ? '#a1a1aa' : '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('Cumulative % of CEOs (lowest to highest paid)');

    // Y axis
    svg.append('g').attr('class', 'axis')
        .call(d3.axisLeft(y).ticks(5).tickFormat(function(d) { return Math.round(d * 100) + '%'; }));

    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -h / 2).attr('y', -42)
        .attr('text-anchor', 'middle')
        .attr('fill', dark ? '#a1a1aa' : '#6b7280')
        .attr('font-size', '11px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('Cumulative % of Total Compensation');

    // Line of perfect equality (diagonal)
    svg.append('line')
        .attr('x1', x(0)).attr('y1', y(0))
        .attr('x2', x(1)).attr('y2', y(1))
        .attr('stroke', dark ? '#4b5563' : '#d1d5db')
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '6,4')
        .attr('opacity', 0.8);

    // Label for equality line
    svg.append('text')
        .attr('x', x(0.52)).attr('y', y(0.55))
        .attr('transform', 'rotate(-42,' + x(0.52) + ',' + y(0.55) + ')')
        .attr('fill', dark ? '#6b7280' : '#9ca3af')
        .attr('font-size', '9px')
        .attr('font-style', 'italic')
        .text('Perfect equality');

    // Lorenz curve line helpers
    var lorenzLine = d3.line()
        .x(function(d) { return x(d.popPct); })
        .y(function(d) { return y(d.compPct); })
        .curve(d3.curveMonotoneX);

    var areaPath = d3.area()
        .x(function(d) { return x(d.popPct); })
        .y0(function(d) { return y(d.popPct); })
        .y1(function(d) { return y(d.compPct); })
        .curve(d3.curveMonotoneX);

    if (hasSectorOverlay) {
        // S&P 500 as background reference
        svg.append('path')
            .datum(lorenzPoints)
            .attr('d', areaPath)
            .attr('fill', dark ? '#3f3f46' : '#d4d4d8')
            .attr('opacity', 0.08)
            .attr('stroke', 'none');

        svg.append('path')
            .datum(lorenzPoints)
            .attr('d', lorenzLine)
            .attr('fill', 'none')
            .attr('stroke', dark ? '#52525b' : '#a1a1aa')
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '4,3')
            .attr('opacity', 0.5);

        // Sector Lorenz curve (primary)
        var sectorAreaPath = d3.area()
            .x(function(d) { return x(d.popPct); })
            .y0(function(d) { return y(d.popPct); })
            .y1(function(d) { return y(d.compPct); })
            .curve(d3.curveMonotoneX);

        svg.append('path')
            .datum(sectorLorenz.points)
            .attr('d', sectorAreaPath)
            .attr('fill', sectorColor)
            .attr('opacity', dark ? 0.15 : 0.12)
            .attr('stroke', 'none');

        svg.append('path')
            .datum(sectorLorenz.points)
            .attr('d', lorenzLine)
            .attr('fill', 'none')
            .attr('stroke', sectorColor)
            .attr('stroke-width', 2.5)
            .attr('opacity', 0.9);

        // Sector Gini label in shaded area
        var sGiniLabelPt = sectorLorenz.points[Math.floor(sectorLorenz.points.length * 0.35)];
        if (sGiniLabelPt) {
            var sgx = x(sGiniLabelPt.popPct);
            var sgy = (y(sGiniLabelPt.popPct) + y(sGiniLabelPt.compPct)) / 2;
            svg.append('text')
                .attr('x', sgx).attr('y', sgy)
                .attr('text-anchor', 'middle')
                .attr('fill', sectorColor)
                .attr('font-size', '9px').attr('font-style', 'italic').attr('opacity', 0.6)
                .text('Sector Gini area');
        }
    } else {
        // Standard S&P 500 only view
        svg.append('path')
            .datum(lorenzPoints)
            .attr('class', 'lorenz-gini-area')
            .attr('d', areaPath)
            .attr('fill', '#00b4d8')
            .attr('opacity', dark ? 0.12 : 0.10)
            .attr('stroke', 'none');

        svg.append('path')
            .datum(lorenzPoints)
            .attr('class', 'lorenz-curve-line')
            .attr('d', lorenzLine)
            .attr('fill', 'none')
            .attr('stroke', '#00b4d8')
            .attr('stroke-width', 2.5)
            .attr('opacity', 0.9);

        // "Gini = shaded area" label inside the shaded area
        var giniLabelPt = lorenzPoints[Math.floor(lorenzPoints.length * 0.35)];
        if (giniLabelPt) {
            var gx = x(giniLabelPt.popPct);
            var gy = (y(giniLabelPt.popPct) + y(giniLabelPt.compPct)) / 2;
            svg.append('text')
                .attr('x', gx).attr('y', gy)
                .attr('text-anchor', 'middle')
                .attr('fill', '#00b4d8')
                .attr('font-size', '9px').attr('font-style', 'italic').attr('opacity', 0.6)
                .text('Gini area');
        }
    }

    // Percentile breakpoint dots and annotations (only in non-sector mode for clarity)
    if (!hasSectorOverlay) {
        var annotColors = {
            'Bottom 50%': '#06d6a0',
            'Bottom 75%': '#a78bfa',
            'Bottom 90%': '#ffd166',
            'Bottom 95%': '#fb923c'
        };

        var annotOffsets = [
            { dx: 8, dy: -12 },
            { dx: 8, dy: -12 },
            { dx: -8, dy: 14, anchor: 'end' },
            { dx: -8, dy: 14, anchor: 'end' }
        ];

        breakpoints.forEach(function(bp, bpi) {
            var cx = x(bp.popPct);
            var cy = y(bp.compPct);
            var off = annotOffsets[bpi];

            svg.append('circle')
                .attr('class', 'lorenz-bp-dot')
                .attr('cx', cx).attr('cy', cy)
                .attr('r', 4)
                .attr('fill', annotColors[bp.label] || '#00b4d8')
                .attr('stroke', dark ? '#18181b' : '#fff')
                .attr('stroke-width', 1.5)
                .attr('opacity', 0.9);

            svg.append('line')
                .attr('x1', cx).attr('x2', cx)
                .attr('y1', cy).attr('y2', y(bp.popPct))
                .attr('stroke', annotColors[bp.label] || '#00b4d8')
                .attr('stroke-width', 0.8)
                .attr('stroke-dasharray', '2,2')
                .attr('opacity', 0.5);

            svg.append('text')
                .attr('x', cx + off.dx).attr('y', cy + off.dy)
                .attr('text-anchor', off.anchor || 'start')
                .attr('fill', annotColors[bp.label] || '#00b4d8')
                .attr('font-size', '9px').attr('font-weight', '500')
                .text(bp.label + ': ' + (bp.compPct * 100).toFixed(1) + '%');
        });
    }

    // Gini coefficient badge (top-right area)
    var badgeX = w - 6;
    if (hasSectorOverlay) {
        // Sector vs S&P 500 comparison
        svg.append('text')
            .attr('x', badgeX).attr('y', 14)
            .attr('text-anchor', 'end')
            .attr('fill', sectorColor)
            .attr('font-size', '13px').attr('font-weight', '700')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(sectorName + ': ' + sectorLorenz.gini.toFixed(3));

        svg.append('text')
            .attr('x', badgeX).attr('y', 30)
            .attr('text-anchor', 'end')
            .attr('fill', dark ? '#71717a' : '#a1a1aa')
            .attr('font-size', '10px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('S&P 500: ' + gini.toFixed(3));

        var giniDelta = sectorLorenz.gini - gini;
        var giniDeltaLabel = (giniDelta >= 0 ? '+' : '') + (giniDelta * 1000).toFixed(1) + ' bps';
        var giniDeltaColor = giniDelta > 0.01 ? '#ef476f' : giniDelta < -0.01 ? '#06d6a0' : (dark ? '#a1a1aa' : '#6b7280');
        svg.append('text')
            .attr('x', badgeX).attr('y', 44)
            .attr('text-anchor', 'end')
            .attr('fill', giniDeltaColor)
            .attr('font-size', '9.5px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('Δ ' + giniDeltaLabel + ' vs index');

        svg.append('text')
            .attr('x', badgeX).attr('y', 58)
            .attr('text-anchor', 'end')
            .attr('fill', dark ? '#a1a1aa' : '#6b7280')
            .attr('font-size', '9px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(sectorCompanies.length + ' companies');

        // Legend
        var legY = h - 24;
        svg.append('line')
            .attr('x1', 6).attr('x2', 26).attr('y1', legY).attr('y2', legY)
            .attr('stroke', dark ? '#52525b' : '#a1a1aa').attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '4,3').attr('opacity', 0.5);
        svg.append('text')
            .attr('x', 30).attr('y', legY + 4)
            .attr('fill', dark ? '#71717a' : '#a1a1aa').attr('font-size', '9px')
            .text('S&P 500');
        svg.append('line')
            .attr('x1', 80).attr('x2', 100).attr('y1', legY).attr('y2', legY)
            .attr('stroke', sectorColor).attr('stroke-width', 2.5).attr('opacity', 0.9);
        svg.append('text')
            .attr('x', 104).attr('y', legY + 4)
            .attr('fill', sectorColor).attr('font-size', '9px').attr('font-weight', '500')
            .text(sectorName);
    } else {
        svg.append('text')
            .attr('x', badgeX).attr('y', 14)
            .attr('text-anchor', 'end')
            .attr('fill', '#00b4d8')
            .attr('font-size', '13px').attr('font-weight', '700')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('Gini: ' + gini.toFixed(3));

        svg.append('text')
            .attr('x', badgeX).attr('y', 30)
            .attr('text-anchor', 'end')
            .attr('fill', dark ? '#a1a1aa' : '#6b7280')
            .attr('font-size', '9.5px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('Top 10% earn ' + (sp500.top10Pct * 100).toFixed(1) + '% of total');

        svg.append('text')
            .attr('x', badgeX).attr('y', 44)
            .attr('text-anchor', 'end')
            .attr('fill', dark ? '#a1a1aa' : '#6b7280')
            .attr('font-size', '9.5px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('Bottom 50% earn ' + (sp500.bot50Pct * 100).toFixed(1) + '% of total');
    }

    // --- Narrative annotation pill (sector overlay mode only) ---
    if (hasSectorOverlay && sectorLorenz) {
        var sTop10 = sectorLorenz.top10Pct;
        var sBot50 = sectorLorenz.bot50Pct;
        var iTop10 = sp500.top10Pct;
        var iBot50 = sp500.bot50Pct;

        // Helper: hex color to rgba string
        function hexRgba(hex, alpha) {
            var r = parseInt(hex.slice(1,3),16);
            var g = parseInt(hex.slice(3,5),16);
            var b = parseInt(hex.slice(5,7),16);
            return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
        }

        // Build narrative parts
        var lorenzNarParts = [];

        // Top 10% concentration comparison
        var top10Delta = sTop10 - iTop10;
        if (Math.abs(top10Delta) >= 0.005) {
            var top10Dir = top10Delta > 0 ? 'more' : 'less';
            lorenzNarParts.push('Top 10% of ' + sectorName + ' CEOs earn ' +
                (sTop10 * 100).toFixed(1) + '% of sector comp (' +
                (top10Delta > 0 ? '+' : '') + (top10Delta * 100).toFixed(1) +
                'pp ' + top10Dir + ' concentrated than S&P 500)');
        }

        // Bottom 50% share comparison
        var bot50Delta = sBot50 - iBot50;
        if (Math.abs(bot50Delta) >= 0.005) {
            lorenzNarParts.push('Bottom half earns ' +
                (sBot50 * 100).toFixed(1) + '% (' +
                (bot50Delta > 0 ? '+' : '') + (bot50Delta * 100).toFixed(1) +
                'pp vs index)');
        }

        // Gini interpretation
        var gDelta = sectorLorenz.gini - gini;
        if (Math.abs(gDelta) >= 0.02) {
            if (gDelta > 0) {
                lorenzNarParts.push('pay is more concentrated than the broader index');
            } else {
                lorenzNarParts.push('pay is more evenly distributed than the broader index');
            }
        }

        if (lorenzNarParts.length > 0) {
            var lorenzNarText = lorenzNarParts.join(' \u00B7 ');
            var lorenzNarY = h + 24;
            var lorenzNarGroup = svg.append('g').attr('class', 'narrative-annotation');
            var pillFill = hexRgba(sectorColor, dark ? 0.08 : 0.06);
            var pillStroke = hexRgba(sectorColor, dark ? 0.2 : 0.15);

            var lorenzNarTextNode = lorenzNarGroup.append('text')
                .attr('x', w / 2)
                .attr('y', lorenzNarY)
                .attr('text-anchor', 'middle')
                .attr('fill', sectorColor)
                .attr('font-size', '10px')
                .attr('font-weight', '500')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .attr('opacity', 0.85)
                .text(lorenzNarText);

            // Background pill behind text
            var lorenzNarBbox = lorenzNarTextNode.node().getBBox();
            var lnPadX = 10, lnPadY = 4;
            lorenzNarGroup.insert('rect', 'text')
                .attr('x', lorenzNarBbox.x - lnPadX)
                .attr('y', lorenzNarBbox.y - lnPadY)
                .attr('width', lorenzNarBbox.width + lnPadX * 2)
                .attr('height', lorenzNarBbox.height + lnPadY * 2)
                .attr('rx', 8)
                .attr('fill', pillFill)
                .attr('stroke', pillStroke)
                .attr('stroke-width', 1);

            // If text is too wide for the container, wrap to two lines
            if (lorenzNarBbox.width > w - 20) {
                lorenzNarTextNode.remove();
                lorenzNarGroup.select('rect').remove();

                // Split at the midpoint separator
                var midIdx = Math.floor(lorenzNarParts.length / 2);
                var line1 = lorenzNarParts.slice(0, Math.max(1, midIdx + 1)).join(' \u00B7 ');
                var line2 = lorenzNarParts.slice(Math.max(1, midIdx + 1)).join(' \u00B7 ');

                lorenzNarGroup.append('text')
                    .attr('x', w / 2).attr('y', lorenzNarY - 6)
                    .attr('text-anchor', 'middle')
                    .attr('fill', sectorColor)
                    .attr('font-size', '10px').attr('font-weight', '500')
                    .attr('font-family', 'Inter, system-ui, sans-serif')
                    .attr('opacity', 0.85)
                    .text(line1);

                if (line2) {
                    lorenzNarGroup.append('text')
                        .attr('x', w / 2).attr('y', lorenzNarY + 8)
                        .attr('text-anchor', 'middle')
                        .attr('fill', sectorColor)
                        .attr('font-size', '10px').attr('font-weight', '500')
                        .attr('font-family', 'Inter, system-ui, sans-serif')
                        .attr('opacity', 0.85)
                        .text(line2);
                }

                // Background pill for wrapped text
                var wrapBbox = lorenzNarGroup.node().getBBox();
                lorenzNarGroup.insert('rect', 'text')
                    .attr('x', wrapBbox.x - lnPadX)
                    .attr('y', wrapBbox.y - lnPadY)
                    .attr('width', wrapBbox.width + lnPadX * 2)
                    .attr('height', wrapBbox.height + lnPadY * 2)
                    .attr('rx', 8)
                    .attr('fill', pillFill)
                    .attr('stroke', pillStroke)
                    .attr('stroke-width', 1);
            }
        }
    }

    // Interactive hover overlay
    var hoverLine = svg.append('line')
        .attr('y1', 0).attr('y2', h)
        .attr('stroke', dark ? '#6b7280' : '#9ca3af')
        .attr('stroke-width', 0.8)
        .attr('stroke-dasharray', '3,3')
        .attr('opacity', 0);

    var hoverDot = svg.append('circle')
        .attr('r', 5)
        .attr('fill', hasSectorOverlay ? sectorColor : '#00b4d8')
        .attr('stroke', dark ? '#18181b' : '#fff')
        .attr('stroke-width', 2)
        .attr('opacity', 0);

    var hoverDotEq = svg.append('circle')
        .attr('r', 3)
        .attr('fill', dark ? '#4b5563' : '#d1d5db')
        .attr('stroke', dark ? '#18181b' : '#fff')
        .attr('stroke-width', 1.5)
        .attr('opacity', 0);

    // Secondary hover dot for S&P 500 reference in sector mode
    var hoverDotRef = null;
    if (hasSectorOverlay) {
        hoverDotRef = svg.append('circle')
            .attr('r', 3)
            .attr('fill', dark ? '#52525b' : '#a1a1aa')
            .attr('stroke', dark ? '#18181b' : '#fff')
            .attr('stroke-width', 1)
            .attr('opacity', 0);
    }

    // Use sector Lorenz for hover in sector mode
    var hoverPoints = hasSectorOverlay ? sectorLorenz.points : lorenzPoints;
    var hoverSorted = hasSectorOverlay ? sectorLorenz.sorted : sorted;
    var hoverN = hasSectorOverlay ? sectorLorenz.n : n;

    svg.append('rect')
        .attr('width', w).attr('height', h)
        .attr('fill', 'transparent')
        .style('cursor', 'crosshair')
        .on('mousemove', function(event) {
            var mouseX = d3.pointer(event)[0];
            var popPct = x.invert(mouseX);
            if (popPct < 0 || popPct > 1) return;

            // Find nearest point on primary curve
            var idx = Math.round(popPct * hoverN);
            if (idx < 0) idx = 0;
            if (idx > hoverN) idx = hoverN;
            var pt = hoverPoints[idx];

            hoverLine.attr('x1', x(pt.popPct)).attr('x2', x(pt.popPct)).attr('opacity', 0.5);
            hoverDot.attr('cx', x(pt.popPct)).attr('cy', y(pt.compPct)).attr('opacity', 1);
            hoverDotEq.attr('cx', x(pt.popPct)).attr('cy', y(pt.popPct)).attr('opacity', 1);

            var popPctStr = (pt.popPct * 100).toFixed(1);
            var compPctStr = (pt.compPct * 100).toFixed(1);
            var gap = (pt.popPct - pt.compPct) * 100;
            var compAtIdx = idx > 0 && idx <= hoverN ? hoverSorted[idx - 1] : 0;

            var html = '<div class="ct-title">' + (hasSectorOverlay ? sectorName : 'Lorenz Curve') + '</div>' +
                '<div class="ct-row"><span class="ct-label">Population</span><span class="ct-val">' + popPctStr + '% of CEOs</span></div>' +
                '<div class="ct-row"><span class="ct-label">Compensation</span><span class="ct-val">' + compPctStr + '% of total pay</span></div>' +
                '<div class="ct-row"><span class="ct-label">Gap from equality</span><span class="ct-val">' + gap.toFixed(1) + ' pp</span></div>';
            if (compAtIdx > 0) {
                html += '<div class="ct-row ct-sub"><span class="ct-label">Comp at this point</span><span class="ct-val">' + fmtCurr(compAtIdx) + '</span></div>';
            }

            // S&P 500 reference in sector mode
            if (hasSectorOverlay && hoverDotRef) {
                var sp500Idx = Math.round(popPct * n);
                if (sp500Idx < 0) sp500Idx = 0;
                if (sp500Idx > n) sp500Idx = n;
                var sp500Pt = lorenzPoints[sp500Idx];
                hoverDotRef.attr('cx', x(sp500Pt.popPct)).attr('cy', y(sp500Pt.compPct)).attr('opacity', 0.7);
                html += '<div class="ct-row ct-sub" style="border-top:1px solid rgba(255,255,255,0.1);padding-top:4px;margin-top:4px"><span class="ct-label">S&P 500</span><span class="ct-val">' + (sp500Pt.compPct * 100).toFixed(1) + '% of total</span></div>';
            }

            showChartTooltip(event, html);
        })
        .on('mouseout', function() {
            hoverLine.attr('opacity', 0);
            hoverDot.attr('opacity', 0);
            hoverDotEq.attr('opacity', 0);
            if (hoverDotRef) hoverDotRef.attr('opacity', 0);
            hideChartTooltip();
        });
}

/* === Gender Pay Gap Chart === */
function drawGenderPayChart(trends) {
    var container = document.getElementById('gender-pay-chart');
    if (!container || !trends || !trends.gender_trends || !trends.gender_trends.data || trends.gender_trends.data.length === 0) return;

    var dark = typeof isDarkTheme === 'function' && isDarkTheme();
    var data = trends.gender_trends.data;
    var rect = container.getBoundingClientRect();
    var totalW = rect.width || 500;
    var totalH = 340;

    // Colors
    var femaleColor = '#e879a0';  // rose/pink
    var overallColor = '#00b4d8'; // cyan (matches the tracker's primary)
    var premiumColor = '#ffd166'; // gold for annotations
    var textColor = dark ? '#e4e4e7' : '#1a1a2e';
    var mutedColor = dark ? '#a1a1aa' : '#6b7280';
    var subtleColor = dark ? '#3f3f46' : '#e5e7eb';

    var margin = { top: 50, right: 160, bottom: 65, left: 55 };
    var w = totalW - margin.left - margin.right;
    var h = totalH - margin.top - margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', totalW).attr('height', totalH)
        .attr('aria-label', 'Gender pay gap grouped bar chart');

    var g = svg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    // Prepare data: each item has fiscal_year, female_median_pay, overall_median_pay
    var years = data.map(function(d) { return 'FY' + d.fiscal_year; });
    var maxPay = d3.max(data, function(d) { return Math.max(d.female_median_pay || 0, d.overall_median_pay || 0); });
    maxPay = maxPay * 1.15; // headroom for labels

    // Scales
    var x0 = d3.scaleBand().domain(years).range([0, w]).padding(0.35);
    var x1 = d3.scaleBand().domain(['overall', 'female']).range([0, x0.bandwidth()]).padding(0.12);
    var y = d3.scaleLinear().domain([0, maxPay]).range([h, 0]);

    // Y-axis gridlines
    var yTicks = y.ticks(5);
    yTicks.forEach(function(t) {
        g.append('line')
            .attr('x1', 0).attr('x2', w)
            .attr('y1', y(t)).attr('y2', y(t))
            .attr('stroke', subtleColor).attr('stroke-width', 0.5);
    });

    // Y-axis
    g.append('g')
        .call(d3.axisLeft(y).ticks(5).tickFormat(function(d) { return '$' + (d / 1e6).toFixed(0) + 'M'; }))
        .call(function(g) { g.select('.domain').remove(); })
        .call(function(g) { g.selectAll('.tick line').attr('stroke', subtleColor); })
        .call(function(g) { g.selectAll('.tick text').attr('fill', mutedColor).attr('font-size', '11px'); });

    // X-axis
    g.append('g')
        .attr('transform', 'translate(0,' + h + ')')
        .call(d3.axisBottom(x0).tickSize(0))
        .call(function(g) { g.select('.domain').attr('stroke', subtleColor); })
        .call(function(g) { g.selectAll('.tick text').attr('fill', textColor).attr('font-size', '13px').attr('font-weight', '600').attr('dy', '12'); });

    // Draw grouped bars
    var barGroups = g.selectAll('.gender-bar-group')
        .data(data)
        .enter().append('g')
        .attr('transform', function(d) { return 'translate(' + x0('FY' + d.fiscal_year) + ',0)'; });

    // Overall bars
    barGroups.append('rect')
        .attr('x', function() { return x1('overall'); })
        .attr('y', function(d) { return y(d.overall_median_pay); })
        .attr('width', x1.bandwidth())
        .attr('height', function(d) { return h - y(d.overall_median_pay); })
        .attr('fill', overallColor)
        .attr('rx', 3).attr('ry', 3)
        .attr('opacity', 0.85)
        .on('mouseover', function(event, d) {
            d3.select(this).attr('opacity', 1);
            showChartTooltip(event, '<div class="ct-title">All CEOs — FY' + d.fiscal_year + '</div>' +
                '<div class="ct-row"><span class="ct-label">Median Pay</span><span class="ct-val">' + fmtCurr(d.overall_median_pay) + '</span></div>' +
                '<div class="ct-row"><span class="ct-label">Total CEOs</span><span class="ct-val">' + d.total_ceos_in_study + '</span></div>');
        })
        .on('mousemove', positionChartTooltip)
        .on('mouseout', function() { d3.select(this).attr('opacity', 0.85); hideChartTooltip(); });

    // Female bars
    barGroups.append('rect')
        .attr('x', function() { return x1('female'); })
        .attr('y', function(d) { return y(d.female_median_pay); })
        .attr('width', x1.bandwidth())
        .attr('height', function(d) { return h - y(d.female_median_pay); })
        .attr('fill', femaleColor)
        .attr('rx', 3).attr('ry', 3)
        .attr('opacity', 0.85)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            d3.select(this).attr('opacity', 1);
            var premium = ((d.female_median_pay - d.overall_median_pay) / d.overall_median_pay * 100).toFixed(1);
            showChartTooltip(event, '<div class="ct-title">Female CEOs — FY' + d.fiscal_year + '</div>' +
                '<div class="ct-row"><span class="ct-label">Median Pay</span><span class="ct-val">' + fmtCurr(d.female_median_pay) + '</span></div>' +
                '<div class="ct-row"><span class="ct-label">Female CEOs</span><span class="ct-val">' + d.num_female_ceos + ' / ' + d.total_ceos_in_study + '</span></div>' +
                '<div class="ct-row"><span class="ct-label">Premium</span><span class="ct-val" style="color:' + premiumColor + '">+' + premium + '%</span></div>' +
                (d.highest_paid_woman ? '<div class="ct-row ct-sub"><span class="ct-label">Highest</span><span class="ct-val">' + d.highest_paid_woman + '</span></div>' : '') +
                (d.highest_paid_woman_comp ? '<div class="ct-row ct-sub"><span class="ct-label"></span><span class="ct-val">' + fmtCurr(d.highest_paid_woman_comp) + '</span></div>' : '') +
                '<div class="ct-row ct-sub" style="margin-top:4px;font-size:10px;color:' + mutedColor + '">Click to filter table to female CEOs</div>');
        })
        .on('mousemove', positionChartTooltip)
        .on('mouseout', function() { d3.select(this).attr('opacity', 0.85); hideChartTooltip(); })
        .on('click', function() {
            hideChartTooltip();
            if (window.filterByGender) window.filterByGender('F');
        });

    // Bar value labels
    barGroups.append('text')
        .attr('x', function() { return x1('overall') + x1.bandwidth() / 2; })
        .attr('y', function(d) { return y(d.overall_median_pay) - 6; })
        .attr('text-anchor', 'middle')
        .attr('fill', overallColor)
        .attr('font-size', '11px').attr('font-weight', '600')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(function(d) { return '$' + (d.overall_median_pay / 1e6).toFixed(1) + 'M'; });

    barGroups.append('text')
        .attr('x', function() { return x1('female') + x1.bandwidth() / 2; })
        .attr('y', function(d) { return y(d.female_median_pay) - 6; })
        .attr('text-anchor', 'middle')
        .attr('fill', femaleColor)
        .attr('font-size', '11px').attr('font-weight', '600')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(function(d) { return '$' + (d.female_median_pay / 1e6).toFixed(1) + 'M'; });

    // Premium connector + label between each pair
    data.forEach(function(d) {
        var groupX = x0('FY' + d.fiscal_year);
        var overallBarCenter = groupX + x1('overall') + x1.bandwidth() / 2;
        var femaleBarCenter = groupX + x1('female') + x1.bandwidth() / 2;
        var overallY = y(d.overall_median_pay);
        var femaleY = y(d.female_median_pay);
        var midY = (overallY + femaleY) / 2;
        var premium = ((d.female_median_pay - d.overall_median_pay) / d.overall_median_pay * 100).toFixed(1);

        // Connector line
        g.append('line')
            .attr('x1', overallBarCenter + x1.bandwidth() / 2 + 2)
            .attr('x2', femaleBarCenter - x1.bandwidth() / 2 - 2)
            .attr('y1', midY).attr('y2', midY)
            .attr('stroke', premiumColor)
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '3,2')
            .attr('opacity', 0.7);

        // Premium badge
        var badgeMidX = (overallBarCenter + femaleBarCenter) / 2;
        var badgeW = 52, badgeH = 20;
        g.append('rect')
            .attr('x', badgeMidX - badgeW / 2)
            .attr('y', midY - badgeH / 2)
            .attr('width', badgeW).attr('height', badgeH)
            .attr('rx', 10).attr('ry', 10)
            .attr('fill', dark ? 'rgba(255,209,102,0.15)' : 'rgba(255,209,102,0.2)')
            .attr('stroke', premiumColor)
            .attr('stroke-width', 1);

        g.append('text')
            .attr('x', badgeMidX)
            .attr('y', midY + 4.5)
            .attr('text-anchor', 'middle')
            .attr('fill', premiumColor)
            .attr('font-size', '10.5px').attr('font-weight', '700')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('+' + premium + '%');
    });

    // Right-side stats panel
    var statsX = w + 20;
    var statsY = 0;

    // Latest data point for stats
    var latest = data[data.length - 1];
    var prev = data.length > 1 ? data[0] : null;

    // Representation
    svg.append('text')
        .attr('x', margin.left + statsX).attr('y', margin.top + statsY)
        .attr('fill', mutedColor).attr('font-size', '10px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('REPRESENTATION');

    var repPct = (latest.num_female_ceos / latest.total_ceos_in_study * 100).toFixed(1);
    svg.append('text')
        .attr('x', margin.left + statsX).attr('y', margin.top + statsY + 18)
        .attr('fill', femaleColor).attr('font-size', '22px').attr('font-weight', '700')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(repPct + '%');

    svg.append('text')
        .attr('x', margin.left + statsX).attr('y', margin.top + statsY + 34)
        .attr('fill', mutedColor).attr('font-size', '10px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(latest.num_female_ceos + ' of ' + latest.total_ceos_in_study + ' CEOs');

    // Premium trend
    var latestPremium = ((latest.female_median_pay - latest.overall_median_pay) / latest.overall_median_pay * 100).toFixed(1);
    svg.append('text')
        .attr('x', margin.left + statsX).attr('y', margin.top + statsY + 58)
        .attr('fill', mutedColor).attr('font-size', '10px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('FY' + latest.fiscal_year + ' PREMIUM');

    svg.append('text')
        .attr('x', margin.left + statsX).attr('y', margin.top + statsY + 76)
        .attr('fill', premiumColor).attr('font-size', '18px').attr('font-weight', '700')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('+' + latestPremium + '%');

    if (prev && prev.female_premium_pct) {
        var delta = (parseFloat(latestPremium) - prev.female_premium_pct).toFixed(1);
        var deltaSign = parseFloat(delta) >= 0 ? '+' : '';
        svg.append('text')
            .attr('x', margin.left + statsX).attr('y', margin.top + statsY + 92)
            .attr('fill', parseFloat(delta) < 0 ? '#ef476f' : '#34d399').attr('font-size', '10px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(deltaSign + delta + 'pp vs FY' + prev.fiscal_year);
    }

    // Highest paid
    if (latest.highest_paid_woman) {
        svg.append('text')
            .attr('x', margin.left + statsX).attr('y', margin.top + statsY + 116)
            .attr('fill', mutedColor).attr('font-size', '10px')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('HIGHEST PAID');

        // Extract name and company
        var nameMatch = latest.highest_paid_woman.match(/^([^(]+)/);
        var compMatch = latest.highest_paid_woman.match(/\(([^)]+)\)/);
        var displayName = nameMatch ? nameMatch[1].trim() : latest.highest_paid_woman;
        var displayComp = compMatch ? compMatch[1] : '';

        svg.append('text')
            .attr('x', margin.left + statsX).attr('y', margin.top + statsY + 132)
            .attr('fill', textColor).attr('font-size', '11px').attr('font-weight', '600')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(displayName);

        if (displayComp) {
            svg.append('text')
                .attr('x', margin.left + statsX).attr('y', margin.top + statsY + 146)
                .attr('fill', mutedColor).attr('font-size', '10px')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .text(displayComp + (latest.highest_paid_woman_comp ? ' · ' + fmtCurr(latest.highest_paid_woman_comp) : ''));
        }

        if (latest.note) {
            svg.append('text')
                .attr('x', margin.left + statsX).attr('y', margin.top + statsY + 162)
                .attr('fill', premiumColor).attr('font-size', '9px').attr('font-style', 'italic')
                .attr('font-family', 'Inter, system-ui, sans-serif')
                .text(latest.note.length > 40 ? latest.note.substring(0, 38) + '…' : latest.note);
        }
    }

    // Legend at bottom
    var legY = totalH - 18;
    svg.append('rect')
        .attr('x', margin.left).attr('y', legY - 8)
        .attr('width', 12).attr('height', 12)
        .attr('rx', 2).attr('fill', overallColor).attr('opacity', 0.85);
    svg.append('text')
        .attr('x', margin.left + 16).attr('y', legY + 2)
        .attr('fill', mutedColor).attr('font-size', '11px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('All CEOs (Median)');

    svg.append('rect')
        .attr('x', margin.left + 120).attr('y', legY - 8)
        .attr('width', 12).attr('height', 12)
        .attr('rx', 2).attr('fill', femaleColor).attr('opacity', 0.85);
    svg.append('text')
        .attr('x', margin.left + 136).attr('y', legY + 2)
        .attr('fill', mutedColor).attr('font-size', '11px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('Female CEOs (Median)');

    svg.append('rect')
        .attr('x', margin.left + 270).attr('y', legY - 8)
        .attr('width', 12).attr('height', 12)
        .attr('rx', 2).attr('fill', premiumColor).attr('opacity', 0.3);
    svg.append('text')
        .attr('x', margin.left + 286).attr('y', legY + 2)
        .attr('fill', mutedColor).attr('font-size', '11px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('Premium %');

    // Narrative annotation — bottom pill
    var narrativeDiv = document.getElementById('gender-pay-narrative');
    if (narrativeDiv) {
        var premShrink = prev && prev.female_premium_pct && parseFloat(latestPremium) < prev.female_premium_pct;
        var narrative = '';
        if (premShrink) {
            narrative = 'Female CEO pay premium narrowed from +' + prev.female_premium_pct + '% (FY' + prev.fiscal_year + ') to +' + latestPremium + '% (FY' + latest.fiscal_year + '). ';
        } else {
            narrative = 'Female CEOs earned +' + latestPremium + '% more than the overall median. ';
        }
        narrative += 'The premium reflects selection bias: women who reach CEO of an S&P 500 company tend to lead larger firms where all CEO pay is higher.';
        narrativeDiv.textContent = narrative;
        narrativeDiv.style.display = 'block';
    }
}


/* ========================================================================
   CEO-to-CFO Pay Premium Chart (histogram)
   ======================================================================== */
function drawCeoCfoChart(companies) {
    var container = document.getElementById('ceo-cfo-chart');
    if (!container) return;
    container.innerHTML = '';

    var withPremium = companies.filter(function(c) {
        return c._ceoCfoPremium != null && isFinite(c._ceoCfoPremium);
    });

    if (withPremium.length < 10) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient CEO-CFO data for chart</p>';
        return;
    }

    var dark = typeof isDarkTheme === 'function' && isDarkTheme();
    var textColor = dark ? '#e4e4e7' : '#1a1a2e';
    var mutedColor = dark ? '#a1a1aa' : '#6b7280';
    var subtleColor = dark ? '#3f3f46' : '#e5e7eb';

    // Buckets for CEO/CFO premium ratio
    var buckets = [
        { label: '<1.5×', min: 0, max: 1.5, color: '#06d6a0' },
        { label: '1.5–2×', min: 1.5, max: 2, color: '#34d399' },
        { label: '2–3×', min: 2, max: 3, color: '#00b4d8' },
        { label: '3–4×', min: 3, max: 4, color: '#a78bfa' },
        { label: '4–5×', min: 4, max: 5, color: '#fbbf24' },
        { label: '5–7×', min: 5, max: 7, color: '#fb923c' },
        { label: '7–10×', min: 7, max: 10, color: '#ef476f' },
        { label: '>10×', min: 10, max: Infinity, color: '#dc2626' }
    ];

    buckets.forEach(function(b) {
        b.companies = withPremium.filter(function(c) {
            return c._ceoCfoPremium >= b.min && c._ceoCfoPremium < b.max;
        });
        b.count = b.companies.length;
    });

    var maxCount = d3.max(buckets, function(b) { return b.count; });

    var cw = container.clientWidth || 700;
    var margin = { top: 20, right: 20, bottom: 60, left: 50 };
    var width = cw - margin.left - margin.right;
    var height = 300 - margin.top - margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', cw)
        .attr('height', 300)
        .attr('role', 'img')
        .attr('aria-label', 'CEO-to-CFO pay premium distribution histogram');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleBand()
        .domain(buckets.map(function(b) { return b.label; }))
        .range([0, width])
        .padding(0.15);

    var y = d3.scaleLinear()
        .domain([0, maxCount * 1.12])
        .range([height, 0]);

    // Grid
    y.ticks(5).forEach(function(t) {
        g.append('line')
            .attr('x1', 0).attr('x2', width)
            .attr('y1', y(t)).attr('y2', y(t))
            .attr('stroke', subtleColor).attr('stroke-width', 0.5);
    });

    // Y-axis
    g.append('g')
        .call(d3.axisLeft(y).ticks(5))
        .call(function(ax) { ax.select('.domain').remove(); })
        .call(function(ax) { ax.selectAll('.tick line').attr('stroke', subtleColor); })
        .call(function(ax) { ax.selectAll('.tick text').attr('fill', mutedColor).attr('font-size', '10px'); });

    // X-axis
    g.append('g')
        .attr('transform', 'translate(0,' + height + ')')
        .call(d3.axisBottom(x).tickSize(0))
        .call(function(ax) { ax.select('.domain').attr('stroke', subtleColor); })
        .call(function(ax) { ax.selectAll('.tick text').attr('fill', textColor).attr('font-size', '11px').attr('dy', '10'); });

    // Median line
    var premiums = withPremium.map(function(c) { return c._ceoCfoPremium; }).sort(function(a, b) { return a - b; });
    var medianPremium = premiums[Math.floor(premiums.length / 2)];
    var meanPremium = premiums.reduce(function(s, v) { return s + v; }, 0) / premiums.length;

    // Bars
    var bars = g.selectAll('.cfo-bar')
        .data(buckets)
        .enter().append('rect')
        .attr('class', 'cfo-bar')
        .attr('x', function(b) { return x(b.label); })
        .attr('y', function(b) { return y(b.count); })
        .attr('width', x.bandwidth())
        .attr('height', function(b) { return height - y(b.count); })
        .attr('fill', function(b) { return b.color; })
        .attr('rx', 3).attr('ry', 3)
        .attr('opacity', 0.8)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, b) {
            d3.select(this).attr('opacity', 1);
            var topCompanies = b.companies.slice().sort(function(a, c) {
                return (c._ceoCfoPremium || 0) - (a._ceoCfoPremium || 0);
            }).slice(0, 5);
            var html = '<div class="ct-title">' + b.label + ' CEO/CFO Premium</div>' +
                '<div class="ct-row"><span class="ct-label">Companies</span><span class="ct-val">' + b.count + '</span></div>' +
                '<div class="ct-row"><span class="ct-label">% of Total</span><span class="ct-val">' + (b.count / withPremium.length * 100).toFixed(1) + '%</span></div>';
            if (topCompanies.length > 0) {
                html += '<div style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.1);padding-top:4px;font-size:11px;">';
                topCompanies.forEach(function(c) {
                    html += '<div>' + c.ticker + ' — ' + c._ceoCfoPremium.toFixed(1) + '× (' + fmtCurr(c.total_compensation) + ' / ' + fmtCurr(c._cfoExec.total) + ')</div>';
                });
                html += '</div>';
            }
            html += '<div style="margin-top:4px;font-size:10px;color:' + mutedColor + '">Click to filter table</div>';
            showChartTooltip(event, html);
        })
        .on('mousemove', positionChartTooltip)
        .on('mouseout', function() { d3.select(this).attr('opacity', 0.8); hideChartTooltip(); })
        .on('click', function(event, b) {
            hideChartTooltip();
            // Use the configurable scatter axes to show CEO comp vs CEO-CFO premium
            // For now, just notify the label in the chart
            // Highlight active bucket
            var isActive = window._activeCeoCfoBucket &&
                window._activeCeoCfoBucket.min === b.min && window._activeCeoCfoBucket.max === b.max;
            if (isActive) {
                window._activeCeoCfoBucket = null;
            } else {
                window._activeCeoCfoBucket = { min: b.min, max: b.max, label: b.label };
            }
            highlightCeoCfoBucket(window._activeCeoCfoBucket ? b.min : null, window._activeCeoCfoBucket ? b.max : null);
        });

    // Count labels above bars
    g.selectAll('.cfo-count')
        .data(buckets)
        .enter().append('text')
        .attr('x', function(b) { return x(b.label) + x.bandwidth() / 2; })
        .attr('y', function(b) { return y(b.count) - 5; })
        .attr('text-anchor', 'middle')
        .attr('fill', textColor)
        .attr('font-size', '11px').attr('font-weight', '600')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(function(b) { return b.count > 0 ? b.count : ''; });

    // Median annotation
    var medBucket = buckets.find(function(b) { return medianPremium >= b.min && medianPremium < b.max; });
    if (medBucket) {
        var medBarX = x(medBucket.label) + x.bandwidth() / 2;
        g.append('line')
            .attr('x1', medBarX).attr('x2', medBarX)
            .attr('y1', 0).attr('y2', height)
            .attr('stroke', '#ffd166')
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '6,3')
            .attr('opacity', 0.7);
        g.append('text')
            .attr('x', medBarX + 4).attr('y', 12)
            .attr('fill', '#ffd166')
            .attr('font-size', '10px').attr('font-weight', '600')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text('Median: ' + medianPremium.toFixed(1) + '×');
    }

    // Stats summary
    svg.append('text')
        .attr('x', cw - 12).attr('y', 16)
        .attr('text-anchor', 'end')
        .attr('fill', mutedColor).attr('font-size', '10px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('n=' + withPremium.length + ' · mean=' + meanPremium.toFixed(1) + '× · median=' + medianPremium.toFixed(1) + '×');

    // X-axis label
    svg.append('text')
        .attr('x', margin.left + width / 2).attr('y', 295)
        .attr('text-anchor', 'middle')
        .attr('fill', mutedColor).attr('font-size', '11px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text('CEO Total Compensation ÷ CFO Total Compensation');
}

/* Highlight/dim CEO-CFO chart bars when a bucket is active */
window.highlightCeoCfoBucket = function(minRatio, maxRatio) {
    var bars = d3.selectAll('.cfo-bar');
    if (minRatio == null) {
        bars.attr('opacity', 0.8);
        return;
    }
    bars.each(function(b) {
        var match = b.min === minRatio && b.max === maxRatio;
        d3.select(this)
            .attr('opacity', match ? 1 : 0.25)
            .attr('stroke', match ? '#fff' : 'none')
            .attr('stroke-width', match ? 2 : 0);
    });
};

/* ========================================================================
   CEO Pay Concentration Distribution Chart (histogram)
   Shows how concentrated CEO pay is relative to total NEO compensation.
   ======================================================================== */
function drawConcDistChart(companies) {
    var container = document.getElementById('conc-dist-chart');
    if (!container) return;
    container.innerHTML = '';

    var withConc = companies.filter(function(c) { return c._ceoConcPct != null; });
    if (withConc.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No concentration data available</p>';
        return;
    }

    // Sector overlay mode
    var sectorName = window._activeSector || null;
    var sectorCompanies = sectorName ? withConc.filter(function(c) { return c.sector === sectorName; }) : null;
    var hasSectorOverlay = sectorCompanies && sectorCompanies.length >= 3;
    var sectorColor = hasSectorOverlay && typeof getSectorColor === 'function' ? getSectorColor(sectorName) : '#00b4d8';

    // Buckets: green → yellow → red gradient matching existing conc-badge tiers
    var buckets = [
        { min: 0, max: 25, label: '<25%', color: '#06d6a0', tag: 'Distributed' },
        { min: 25, max: 30, label: '25–30%', color: '#34d399', tag: 'Distributed' },
        { min: 30, max: 35, label: '30–35%', color: '#4ade80', tag: 'Distributed' },
        { min: 35, max: 40, label: '35–40%', color: '#fcd34d', tag: 'Moderate' },
        { min: 40, max: 45, label: '40–45%', color: '#fbbf24', tag: 'Moderate' },
        { min: 45, max: 50, label: '45–50%', color: '#fb923c', tag: 'Moderate' },
        { min: 50, max: 60, label: '50–60%', color: '#ef476f', tag: 'Concentrated' },
        { min: 60, max: 101, label: '≥60%', color: '#dc2626', tag: 'Concentrated' }
    ];

    buckets.forEach(function(b) {
        b.companies = withConc.filter(function(c) {
            return c._ceoConcPct >= b.min && c._ceoConcPct < b.max;
        });
        b.count = b.companies.length;
        b.companies.sort(function(a, bb) { return bb._ceoConcPct - a._ceoConcPct; });
        if (hasSectorOverlay) {
            b.sectorCompanies = sectorCompanies.filter(function(c) {
                return c._ceoConcPct >= b.min && c._ceoConcPct < b.max;
            });
            b.sectorCount = b.sectorCompanies.length;
            b.sectorCompanies.sort(function(a, bb) { return bb._ceoConcPct - a._ceoConcPct; });
        }
    });

    var activeBuckets = buckets.filter(function(b) { return b.count > 0 || (hasSectorOverlay && b.sectorCount > 0); });

    // Stats
    var concVals = withConc.map(function(c) { return c._ceoConcPct; }).sort(function(a, b) { return a - b; });
    var n = concVals.length;
    var medianConc = concVals[Math.floor(n / 2)];
    var meanConc = concVals.reduce(function(s, v) { return s + v; }, 0) / n;
    var above50 = withConc.filter(function(c) { return c._ceoConcPct >= 50; }).length;
    var below25 = withConc.filter(function(c) { return c._ceoConcPct < 25; }).length;

    // Sector stats
    var sectorMedian = 0, sectorMean = 0;
    if (hasSectorOverlay) {
        var sVals = sectorCompanies.map(function(c) { return c._ceoConcPct; }).sort(function(a, b) { return a - b; });
        sectorMedian = sVals[Math.floor(sVals.length / 2)];
        sectorMean = sVals.reduce(function(s, v) { return s + v; }, 0) / sVals.length;
    }

    var cw = container.clientWidth || 700;
    var margin = { top: 30, right: hasSectorOverlay ? 60 : 50, bottom: 55, left: 50 };
    var width = cw - margin.left - margin.right;
    var height = 300;

    var maxCount = d3.max(activeBuckets, function(b) { return b.count; });

    var ariaLabel = hasSectorOverlay
        ? 'CEO pay concentration: ' + sectorName + ' (' + sectorCompanies.length + ' companies) vs S&P 500'
        : 'CEO pay concentration distribution across S&P 500';

    var svg = d3.select(container).append('svg')
        .attr('width', cw)
        .attr('height', height + margin.top + margin.bottom)
        .attr('role', 'img')
        .attr('aria-label', ariaLabel);

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleBand()
        .domain(activeBuckets.map(function(b) { return b.label; }))
        .range([0, width])
        .padding(0.15);

    var y = d3.scaleLinear()
        .domain([0, maxCount * 1.15])
        .range([height, 0]);

    // Sector Y axis
    var ySector = null;
    if (hasSectorOverlay) {
        var maxSectorCount = d3.max(activeBuckets, function(b) { return b.sectorCount || 0; });
        ySector = d3.scaleLinear()
            .domain([0, Math.max(maxSectorCount * 1.15, 1)])
            .range([height, 0]);
    }

    // Grid
    g.append('g').attr('class', 'grid')
        .call(d3.axisLeft(y).tickSize(-width).tickFormat('').ticks(6));

    // Axes
    g.append('g').attr('class', 'axis')
        .attr('transform', 'translate(0,' + height + ')')
        .call(d3.axisBottom(x).tickSize(0).tickPadding(10));

    g.append('text')
        .attr('x', width / 2).attr('y', height + 42)
        .attr('text-anchor', 'middle')
        .attr('fill', typeof getThemeMutedColor === 'function' ? getThemeMutedColor() : '#6b7280')
        .attr('font-size', '11px').attr('font-family', 'Inter, system-ui, sans-serif')
        .text('CEO Share of Total NEO Compensation');

    g.append('g').attr('class', 'axis')
        .call(d3.axisLeft(y).ticks(6).tickFormat(function(d) { return d; }));

    g.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -height / 2).attr('y', -38)
        .attr('text-anchor', 'middle')
        .attr('fill', typeof getThemeMutedColor === 'function' ? getThemeMutedColor() : '#6b7280')
        .attr('font-size', '11px').attr('font-family', 'Inter, system-ui, sans-serif')
        .text(hasSectorOverlay ? 'S&P 500 Companies' : 'Number of Companies');

    if (hasSectorOverlay && ySector) {
        g.append('g').attr('class', 'axis')
            .attr('transform', 'translate(' + width + ',0)')
            .call(d3.axisRight(ySector).ticks(4).tickFormat(function(d) { return d; }));
        g.append('text')
            .attr('transform', 'rotate(90)')
            .attr('x', height / 2).attr('y', -width - 40)
            .attr('text-anchor', 'middle')
            .attr('fill', sectorColor)
            .attr('font-size', '11px').attr('font-family', 'Inter, system-ui, sans-serif')
            .text(sectorName + ' Companies');
    }

    // Determine active filter state for initial bar rendering
    var activeTier = window._activeConcTier;

    // S&P 500 bars
    var bars = g.selectAll('.conc-dist-bar')
        .data(activeBuckets)
        .join('g')
        .attr('class', 'conc-dist-bar');

    bars.append('rect')
        .attr('x', function(b) { return x(b.label); })
        .attr('y', function(b) { return y(b.count); })
        .attr('width', x.bandwidth())
        .attr('height', function(b) { return height - y(b.count); })
        .attr('fill', function(b) {
            return hasSectorOverlay ? (typeof isDarkTheme === 'function' && isDarkTheme() ? '#3f3f46' : '#d4d4d8') : b.color;
        })
        .attr('rx', 3)
        .attr('opacity', function(b) {
            if (hasSectorOverlay) return 0.5;
            if (activeTier) return (b.min === activeTier.min && b.max === activeTier.max) ? 1 : 0.3;
            return 0.8;
        })
        .each(function(b) {
            if (!hasSectorOverlay && activeTier && b.min === activeTier.min && b.max === activeTier.max) {
                d3.select(this).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
            }
        })
        .style('cursor', 'pointer')
        .on('mouseover', function(event, b) {
            var compList = b.companies.slice(0, 8).map(function(c) {
                return c.ticker + ' ' + c._ceoConcPct.toFixed(1) + '%';
            }).join('<br>');
            if (b.count > 8) compList += '<br>...+' + (b.count - 8) + ' more';
            var html = '<strong>' + b.label + ' CEO Concentration</strong><br>' +
                b.count + ' companies (' + (b.count / n * 100).toFixed(1) + '% of S&P 500)<br>';
            if (hasSectorOverlay) {
                html += '<br><strong>' + sectorName + '</strong>: ' + (b.sectorCount || 0) + ' companies<br>';
            }
            html += '<br>' + compList;
            showChartTooltip(event, html);
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function() { hideChartTooltip(); })
        .on('click', function(event, b) {
            if (typeof filterByConcTier === 'function') {
                filterByConcTier(b.min, b.max, b.tag, b.label);
                if (window.highlightConcDistBucket) window.highlightConcDistBucket(
                    window._activeConcTier ? window._activeConcTier.min : null,
                    window._activeConcTier ? window._activeConcTier.max : null
                );
            }
        });

    // Count labels
    bars.append('text')
        .attr('class', 'conc-count-label')
        .attr('x', function(b) { return x(b.label) + x.bandwidth() / 2; })
        .attr('y', function(b) { return y(b.count) - 5; })
        .attr('text-anchor', 'middle')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px')
        .style('font-weight', '600')
        .attr('opacity', function(b) {
            if (activeTier && !hasSectorOverlay) return (b.min === activeTier.min && b.max === activeTier.max) ? 1 : 0.4;
            return 1;
        })
        .text(function(b) { return b.count; });

    // Sector overlay bars
    if (hasSectorOverlay && ySector) {
        var sectorBars = g.selectAll('.conc-sector-bar')
            .data(activeBuckets.filter(function(b) { return b.sectorCount > 0; }))
            .join('g')
            .attr('class', 'conc-sector-bar');

        sectorBars.append('rect')
            .attr('x', function(b) { return x(b.label) + x.bandwidth() * 0.15; })
            .attr('y', function(b) { return ySector(b.sectorCount); })
            .attr('width', x.bandwidth() * 0.7)
            .attr('height', function(b) { return height - ySector(b.sectorCount); })
            .attr('fill', sectorColor)
            .attr('rx', 2)
            .attr('opacity', 0.85)
            .style('cursor', 'pointer')
            .on('mouseover', function(event, b) {
                var compList = b.sectorCompanies.slice(0, 8).map(function(c) {
                    return c.ticker + ' ' + c._ceoConcPct.toFixed(1) + '%';
                }).join('<br>');
                if (b.sectorCount > 8) compList += '<br>...+' + (b.sectorCount - 8) + ' more';
                showChartTooltip(event, '<strong>' + sectorName + ': ' + b.label + '</strong><br>' +
                    b.sectorCount + ' companies<br><br>' + compList);
            })
            .on('mousemove', function(event) { positionChartTooltip(event); })
            .on('mouseout', function() { hideChartTooltip(); })
            .on('click', function(event, b) {
                if (typeof filterByConcTier === 'function') {
                    filterByConcTier(b.min, b.max, b.tag, b.label);
                    if (window.highlightConcDistBucket) window.highlightConcDistBucket(
                        window._activeConcTier ? window._activeConcTier.min : null,
                        window._activeConcTier ? window._activeConcTier.max : null
                    );
                }
            });

        sectorBars.append('text')
            .attr('x', function(b) { return x(b.label) + x.bandwidth() / 2; })
            .attr('y', function(b) { return ySector(b.sectorCount) - 5; })
            .attr('text-anchor', 'middle')
            .style('fill', sectorColor)
            .style('font-size', '10px')
            .style('font-weight', '600')
            .text(function(b) { return b.sectorCount; });
    }

    // Median reference line
    var medianBucket = activeBuckets.find(function(b) { return medianConc >= b.min && medianConc < b.max; });
    if (medianBucket) {
        var medianFrac = (medianConc - medianBucket.min) / (medianBucket.max - medianBucket.min);
        var medianXPos = x(medianBucket.label) + x.bandwidth() * medianFrac;
        var lineColor = typeof isDarkTheme === 'function' && isDarkTheme() ? '#ffd166' : '#d97706';
        g.append('line')
            .attr('x1', medianXPos).attr('x2', medianXPos)
            .attr('y1', 0).attr('y2', height)
            .attr('stroke', lineColor).attr('stroke-width', 2)
            .attr('stroke-dasharray', '6,3').attr('opacity', 0.9);
        g.append('text')
            .attr('x', medianXPos + 4).attr('y', 12)
            .style('fill', lineColor).style('font-size', '11px').style('font-weight', '600')
            .text('Median: ' + medianConc.toFixed(1) + '%');
    }

    // Mean reference line (red dashed)
    var meanBucket = activeBuckets.find(function(b) { return meanConc >= b.min && meanConc < b.max; });
    if (meanBucket) {
        var meanFrac = (meanConc - meanBucket.min) / (meanBucket.max - meanBucket.min);
        var meanXPos = x(meanBucket.label) + x.bandwidth() * meanFrac;
        var meanColor = typeof isDarkTheme === 'function' && isDarkTheme() ? '#ef476f' : '#dc2626';
        g.append('line')
            .attr('x1', meanXPos).attr('x2', meanXPos)
            .attr('y1', 0).attr('y2', height)
            .attr('stroke', meanColor).attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '4,4').attr('opacity', 0.7);
        // Only show mean label if it's far enough from median
        if (Math.abs(meanXPos - (medianBucket ? x(medianBucket.label) + x.bandwidth() * ((medianConc - medianBucket.min) / (medianBucket.max - medianBucket.min)) : 0)) > 30) {
            g.append('text')
                .attr('x', meanXPos + 4).attr('y', 26)
                .style('fill', meanColor).style('font-size', '10px').style('font-weight', '500')
                .text('Mean: ' + meanConc.toFixed(1) + '%');
        }
    }

    // Sector median line
    if (hasSectorOverlay) {
        var sMedBucket = activeBuckets.find(function(b) { return sectorMedian >= b.min && sectorMedian < b.max; });
        if (sMedBucket) {
            var sMedFrac = (sectorMedian - sMedBucket.min) / (sMedBucket.max - sMedBucket.min);
            var sMedXPos = x(sMedBucket.label) + x.bandwidth() * sMedFrac;
            g.append('line')
                .attr('x1', sMedXPos).attr('x2', sMedXPos)
                .attr('y1', 0).attr('y2', height)
                .attr('stroke', sectorColor).attr('stroke-width', 2)
                .attr('stroke-dasharray', '3,3').attr('opacity', 0.8);
            g.append('text')
                .attr('x', sMedXPos + 4).attr('y', 40)
                .style('fill', sectorColor).style('font-size', '10px').style('font-weight', '600')
                .text(sectorName + ': ' + sectorMedian.toFixed(1) + '%');
        }
    }

    // Tier region labels at top
    var tierRegions = [
        { label: 'Distributed', maxPct: 35, color: '#06d6a0' },
        { label: 'Moderate', maxPct: 50, color: '#fbbf24' },
        { label: 'Concentrated', maxPct: 101, color: '#ef476f' }
    ];
    var regionY = -8;
    tierRegions.forEach(function(region) {
        // Find buckets in this region
        var regionBuckets = activeBuckets.filter(function(b) {
            if (region.label === 'Distributed') return b.max <= 35;
            if (region.label === 'Moderate') return b.min >= 35 && b.max <= 50;
            return b.min >= 50;
        });
        if (regionBuckets.length === 0) return;
        var firstB = regionBuckets[0], lastB = regionBuckets[regionBuckets.length - 1];
        var regionX1 = x(firstB.label);
        var regionX2 = x(lastB.label) + x.bandwidth();
        var midX = (regionX1 + regionX2) / 2;
        g.append('text')
            .attr('x', midX).attr('y', regionY)
            .attr('text-anchor', 'middle')
            .style('fill', region.color)
            .style('font-size', '9px')
            .style('font-weight', '600')
            .style('text-transform', 'uppercase')
            .style('letter-spacing', '0.5px')
            .style('opacity', 0.7)
            .text(region.label);
    });

    // Stats annotation
    var statsText = withConc.length + ' companies | Median ' + medianConc.toFixed(1) + '% | Mean ' + meanConc.toFixed(1) + '%';
    statsText += ' | ' + above50 + ' above 50%';
    if (hasSectorOverlay) {
        statsText += ' | ' + sectorName + ': median ' + sectorMedian.toFixed(1) + '%';
        var sectorAbove50 = sectorCompanies.filter(function(c) { return c._ceoConcPct >= 50; }).length;
        if (sectorAbove50 > 0) statsText += ', ' + sectorAbove50 + ' above 50%';
    }
    svg.append('text')
        .attr('x', cw / 2)
        .attr('y', height + margin.top + margin.bottom - 5)
        .attr('text-anchor', 'middle')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px')
        .style('opacity', 0.7)
        .text(statsText);

    // Sector skew narrative annotation (when no sector filter is active)
    var existingNarr = container.querySelector('.conc-dist-narrative');
    if (existingNarr) existingNarr.remove();

    if (!hasSectorOverlay && withConc.length >= 20) {
        // Compute per-sector median concentration
        var sectorGroups = {};
        withConc.forEach(function(c) {
            var s = c.sector || 'Unknown';
            if (!sectorGroups[s]) sectorGroups[s] = [];
            sectorGroups[s].push(c._ceoConcPct);
        });
        var sectorMedians = [];
        Object.keys(sectorGroups).forEach(function(s) {
            if (sectorGroups[s].length >= 5) {
                var sorted = sectorGroups[s].slice().sort(function(a, b) { return a - b; });
                var med = sorted[Math.floor(sorted.length / 2)];
                sectorMedians.push({ name: s, median: med, count: sectorGroups[s].length });
            }
        });
        sectorMedians.sort(function(a, b) { return a.median - b.median; });

        if (sectorMedians.length >= 4) {
            var mostDistributed = sectorMedians[0];
            var mostConcentrated = sectorMedians[sectorMedians.length - 1];
            var spread = mostConcentrated.median - mostDistributed.median;

            var shortName = function(n) {
                return n.replace('Information Technology', 'IT').replace('Communication Services', 'Comm Svcs')
                    .replace('Consumer Discretionary', 'Cons Disc').replace('Consumer Staples', 'Cons Stpls')
                    .replace('Health Care', 'Health');
            };

            var concColor = typeof getSectorColor === 'function' ? getSectorColor(mostConcentrated.name) : '#ef476f';
            var distColor = typeof getSectorColor === 'function' ? getSectorColor(mostDistributed.name) : '#06d6a0';

            var narrativeText = 'Sector skew: ';
            narrativeText += shortName(mostConcentrated.name) + ' has the most CEO-concentrated pay pools (median ' + mostConcentrated.median.toFixed(1) + '%), ';
            narrativeText += 'while ' + shortName(mostDistributed.name) + ' distributes compensation most evenly (median ' + mostDistributed.median.toFixed(1) + '%). ';
            narrativeText += 'The ' + spread.toFixed(0) + 'pp sector gap suggests structural differences in how industries allocate executive compensation across the C-suite.';

            var narrDiv = document.createElement('div');
            narrDiv.className = 'conc-dist-narrative';

            // Build with styled spans for sector names
            var span1 = document.createElement('span');
            span1.textContent = 'Sector skew: ';

            var sConc = document.createElement('span');
            sConc.style.color = concColor;
            sConc.style.fontWeight = '600';
            sConc.textContent = shortName(mostConcentrated.name);

            var mid1 = document.createElement('span');
            mid1.textContent = ' has the most CEO-concentrated pay pools (median ' + mostConcentrated.median.toFixed(1) + '%), while ';

            var sDist = document.createElement('span');
            sDist.style.color = distColor;
            sDist.style.fontWeight = '600';
            sDist.textContent = shortName(mostDistributed.name);

            var mid2 = document.createElement('span');
            mid2.textContent = ' distributes compensation most evenly (median ' + mostDistributed.median.toFixed(1) + '%). ';

            var tail = document.createElement('span');
            tail.textContent = 'The ' + spread.toFixed(0) + 'pp sector gap suggests structural differences in how industries allocate executive compensation across the C-suite.';

            narrDiv.appendChild(span1);
            narrDiv.appendChild(sConc);
            narrDiv.appendChild(mid1);
            narrDiv.appendChild(sDist);
            narrDiv.appendChild(mid2);
            narrDiv.appendChild(tail);

            container.appendChild(narrDiv);
        }
    } else if (hasSectorOverlay) {
        // Sector overlay narrative: compare this sector's concentration to S&P 500
        var delta = sectorMedian - medianConc;
        var sectorAbove50Count = sectorCompanies.filter(function(c) { return c._ceoConcPct >= 50; }).length;
        var indexAbove50Pct = (above50 / n * 100).toFixed(0);
        var sectorAbove50Pct = (sectorAbove50Count / sectorCompanies.length * 100).toFixed(0);

        var narrText = sectorName + ' median CEO concentration is ' + sectorMedian.toFixed(1) + '% vs S&P 500 ' + medianConc.toFixed(1) + '% ';
        narrText += '(' + (delta >= 0 ? '+' : '') + delta.toFixed(1) + 'pp). ';
        narrText += sectorAbove50Pct + '% of ' + sectorName + ' companies are CEO-concentrated (\u226550%) vs ' + indexAbove50Pct + '% across the index.';

        var narrDiv2 = document.createElement('div');
        narrDiv2.className = 'conc-dist-narrative';
        narrDiv2.textContent = narrText;
        container.appendChild(narrDiv2);
    }
}

/* Update CEO concentration distribution chart bar highlighting */
window.highlightConcDistBucket = function(minPct, maxPct) {
    d3.selectAll('#conc-dist-chart .conc-dist-bar rect').each(function(d) {
        if (!d) return;
        if (minPct == null) {
            d3.select(this).attr('opacity', 0.8).attr('stroke', 'none');
        } else if (d.min === minPct && d.max === maxPct) {
            d3.select(this).attr('opacity', 1).attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5);
        } else {
            d3.select(this).attr('opacity', 0.3).attr('stroke', 'none');
        }
    });
    d3.selectAll('#conc-dist-chart .conc-dist-bar text.conc-count-label').each(function(d) {
        if (!d) return;
        d3.select(this).attr('opacity', minPct == null || (d.min === minPct && d.max === maxPct) ? 1 : 0.4);
    });
};

/* ========================================================================
   Say-on-Pay Distribution Chart (histogram)
   ======================================================================== */
function drawSopDistChart(companies) {
    var container = document.getElementById('sop-dist-chart');
    if (!container) return;
    container.innerHTML = '';

    var withSop = companies.filter(function(c) { return c._sopApproval != null; });
    if (withSop.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No say-on-pay data available yet</p>';
        return;
    }

    var buckets = [
        { min: 0, max: 50, label: '<50%', color: '#ef476f' },
        { min: 50, max: 60, label: '50–60%', color: '#f77f7f' },
        { min: 60, max: 70, label: '60–70%', color: '#fb923c' },
        { min: 70, max: 80, label: '70–80%', color: '#fbbf24' },
        { min: 80, max: 85, label: '80–85%', color: '#fcd34d' },
        { min: 85, max: 90, label: '85–90%', color: '#a3e635' },
        { min: 90, max: 95, label: '90–95%', color: '#4ade80' },
        { min: 95, max: 100.1, label: '95–100%', color: '#06d6a0' }
    ];

    buckets.forEach(function(b) {
        b.companies = withSop.filter(function(c) {
            return c._sopApproval >= b.min && c._sopApproval < b.max;
        });
        b.count = b.companies.length;
        b.companies.sort(function(a, bb) { return a._sopApproval - bb._sopApproval; });
    });

    var activeBuckets = buckets.filter(function(b) { return b.count > 0; });
    var maxCount = d3.max(activeBuckets, function(b) { return b.count; });

    // Median / mean
    var sopVals = withSop.map(function(c) { return c._sopApproval; }).sort(function(a, b) { return a - b; });
    var medianSop = sopVals[Math.floor(sopVals.length / 2)];
    var meanSop = sopVals.reduce(function(s, v) { return s + v; }, 0) / sopVals.length;

    var cw = container.clientWidth || 700;
    var margin = { top: 30, right: 30, bottom: 55, left: 50 };
    var width = cw - margin.left - margin.right;
    var height = 320 - margin.top - margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', cw)
        .attr('height', 320)
        .attr('role', 'img')
        .attr('aria-label', 'Say-on-Pay approval distribution histogram');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleBand()
        .domain(activeBuckets.map(function(b) { return b.label; }))
        .range([0, width])
        .padding(0.15);

    var y = d3.scaleLinear()
        .domain([0, maxCount * 1.15])
        .range([height, 0]);

    // Axes
    g.append('g')
        .attr('transform', 'translate(0,' + height + ')')
        .call(d3.axisBottom(x))
        .selectAll('text')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px');

    g.append('g')
        .call(d3.axisLeft(y).ticks(5))
        .selectAll('text')
        .style('fill', chartStrokeColor());

    // Bars
    g.selectAll('.sop-bar')
        .data(activeBuckets)
        .enter()
        .append('rect')
        .attr('class', 'sop-bar')
        .attr('x', function(b) { return x(b.label); })
        .attr('y', function(b) { return y(b.count); })
        .attr('width', x.bandwidth())
        .attr('height', function(b) { return height - y(b.count); })
        .attr('fill', function(b) { return b.color; })
        .attr('rx', 3)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, b) {
            var compList = b.companies.slice(0, 8).map(function(c) {
                return c.ticker + ' ' + c._sopApproval.toFixed(1) + '%';
            }).join('<br>');
            if (b.count > 8) compList += '<br>...+' + (b.count - 8) + ' more';
            showChartTooltip(event, '<strong>' + b.label + ' Approval</strong><br>' +
                b.count + ' companies<br><br>' + compList);
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function() { hideChartTooltip(); })
        .on('click', function(event, b) {
            if (window.highlightSopBucket) window.highlightSopBucket(b.min, b.max);
        });

    // Count labels on top of bars
    g.selectAll('.sop-count-label')
        .data(activeBuckets)
        .enter()
        .append('text')
        .attr('x', function(b) { return x(b.label) + x.bandwidth() / 2; })
        .attr('y', function(b) { return y(b.count) - 5; })
        .attr('text-anchor', 'middle')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px')
        .style('font-weight', '600')
        .text(function(b) { return b.count; });

    // Median line
    var allLabelsX = activeBuckets.map(function(b) { return b.label; });
    var medianBucket = activeBuckets.find(function(b) { return medianSop >= b.min && medianSop < b.max; });
    if (medianBucket) {
        var medianXPos = x(medianBucket.label) + x.bandwidth() * ((medianSop - medianBucket.min) / (medianBucket.max - medianBucket.min));
        g.append('line')
            .attr('x1', medianXPos).attr('x2', medianXPos)
            .attr('y1', 0).attr('y2', height)
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '6,3')
            .attr('opacity', 0.8);
        g.append('text')
            .attr('x', medianXPos + 4)
            .attr('y', 12)
            .style('fill', '#fff')
            .style('font-size', '11px')
            .style('font-weight', '600')
            .text('Median: ' + medianSop.toFixed(1) + '%');
    }

    // Stats annotation
    var statsText = withSop.length + ' companies | Median ' + medianSop.toFixed(1) + '% | Mean ' + meanSop.toFixed(1) + '%';
    var lowCount = withSop.filter(function(c) { return c._sopApproval < 70; }).length;
    if (lowCount > 0) statsText += ' | ' + lowCount + ' below 70%';
    svg.append('text')
        .attr('x', cw / 2)
        .attr('y', 320 - 5)
        .attr('text-anchor', 'middle')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px')
        .style('opacity', 0.7)
        .text(statsText);
}

/* ========================================================================
   Say-on-Pay vs CEO Compensation Scatter Chart
   ======================================================================== */
function drawSopScatterChart(companies) {
    var container = document.getElementById('sop-scatter-chart');
    if (!container) return;
    container.innerHTML = '';

    var withBoth = companies.filter(function(c) {
        return c._sopApproval != null && c.total_compensation > 0;
    });

    if (withBoth.length < 5) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient say-on-pay data for scatter plot</p>';
        return;
    }

    var cw = container.clientWidth || 700;
    var margin = { top: 20, right: 30, bottom: 50, left: 65 };
    var width = cw - margin.left - margin.right;
    var height = 360 - margin.top - margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', cw)
        .attr('height', 360)
        .attr('role', 'img')
        .attr('aria-label', 'Say-on-Pay approval vs CEO total compensation scatter plot');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var maxComp = d3.max(withBoth, function(c) { return c.total_compensation; });
    var x = d3.scaleLog()
        .domain([d3.min(withBoth, function(c) { return c.total_compensation; }) * 0.8, maxComp * 1.1])
        .range([0, width]);

    var y = d3.scaleLinear()
        .domain([Math.min(d3.min(withBoth, function(c) { return c._sopApproval; }) - 2, 50), 101])
        .range([height, 0]);

    // Grid lines
    g.append('g')
        .attr('class', 'grid')
        .attr('transform', 'translate(0,' + height + ')')
        .call(d3.axisBottom(x).ticks(6, '$.2s').tickSize(-height))
        .selectAll('text')
        .style('fill', chartStrokeColor())
        .style('font-size', '10px');
    g.selectAll('.grid line').attr('stroke', chartStrokeColor()).attr('opacity', 0.1);
    g.selectAll('.grid .domain').attr('stroke', chartStrokeColor()).attr('opacity', 0.2);

    g.append('g')
        .call(d3.axisLeft(y).ticks(6).tickFormat(function(d) { return d + '%'; }))
        .selectAll('text')
        .style('fill', chartStrokeColor())
        .style('font-size', '10px');

    // Threshold lines
    var thresholds = [
        { val: 70, label: '70% threshold', color: '#ef476f', dash: '6,3' },
        { val: 85, label: '85% threshold', color: '#fbbf24', dash: '4,4' }
    ];
    thresholds.forEach(function(t) {
        var yPos = y(t.val);
        if (yPos >= 0 && yPos <= height) {
            g.append('line')
                .attr('x1', 0).attr('x2', width)
                .attr('y1', yPos).attr('y2', yPos)
                .attr('stroke', t.color)
                .attr('stroke-width', 1.5)
                .attr('stroke-dasharray', t.dash)
                .attr('opacity', 0.6);
            g.append('text')
                .attr('x', width - 4)
                .attr('y', yPos - 4)
                .attr('text-anchor', 'end')
                .style('fill', t.color)
                .style('font-size', '10px')
                .style('opacity', 0.8)
                .text(t.label);
        }
    });

    // Dots
    var dots = g.selectAll('.sop-dot')
        .data(withBoth)
        .enter()
        .append('circle')
        .attr('class', 'sop-dot')
        .attr('cx', function(c) { return x(c.total_compensation); })
        .attr('cy', function(c) { return y(c._sopApproval); })
        .attr('r', function(c) {
            var sp = c._sopApproval;
            return sp < 70 ? 7 : sp < 85 ? 5 : 4;
        })
        .attr('fill', function(c) {
            var sp = c._sopApproval;
            return sp < 70 ? '#ef476f' : sp < 85 ? '#fbbf24' : '#06d6a0';
        })
        .attr('opacity', 0.75)
        .attr('stroke', function(c) {
            return c._sopApproval < 70 ? '#fff' : 'none';
        })
        .attr('stroke-width', function(c) {
            return c._sopApproval < 70 ? 1.5 : 0;
        })
        .style('cursor', 'pointer')
        .on('mouseover', function(event, c) {
            d3.select(this).attr('r', 8).attr('opacity', 1);
            showChartTooltip(event,
                '<strong>' + c.ticker + '</strong> — ' + c.company_name + '<br>' +
                'CEO: ' + (c.ceo_name || '—') + '<br>' +
                'Total Comp: ' + fmtCurr(c.total_compensation) + '<br>' +
                'Say-on-Pay: <strong>' + c._sopApproval.toFixed(1) + '%</strong>' +
                (c.say_on_pay && c.say_on_pay.filing_date ? '<br>Filed: ' + c.say_on_pay.filing_date : '') +
                '<br>Sector: ' + (c.sector || '—'));
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function(event, c) {
            var sp = c._sopApproval;
            d3.select(this).attr('r', sp < 70 ? 7 : sp < 85 ? 5 : 4).attr('opacity', 0.75);
            hideChartTooltip();
        });

    // Label outliers (< 70%)
    var outliers = withBoth.filter(function(c) { return c._sopApproval < 70; });
    outliers.forEach(function(c) {
        g.append('text')
            .attr('x', x(c.total_compensation) + 9)
            .attr('y', y(c._sopApproval) + 4)
            .style('fill', '#ef476f')
            .style('font-size', '10px')
            .style('font-weight', '600')
            .text(c.ticker + ' ' + c._sopApproval.toFixed(1) + '%');
    });

    // Axis labels
    svg.append('text')
        .attr('x', margin.left + width / 2)
        .attr('y', 360 - 8)
        .attr('text-anchor', 'middle')
        .style('fill', chartStrokeColor())
        .style('font-size', '12px')
        .text('CEO Total Compensation (log scale)');

    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -(margin.top + height / 2))
        .attr('y', 14)
        .attr('text-anchor', 'middle')
        .style('fill', chartStrokeColor())
        .style('font-size', '12px')
        .text('Say-on-Pay Approval %');

    // Compute correlation
    var lnComps = withBoth.map(function(c) { return Math.log(c.total_compensation); });
    var sopVals = withBoth.map(function(c) { return c._sopApproval; });
    var n = withBoth.length;
    var sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
    for (var i = 0; i < n; i++) {
        sumX += lnComps[i]; sumY += sopVals[i];
        sumXY += lnComps[i] * sopVals[i];
        sumX2 += lnComps[i] * lnComps[i];
        sumY2 += sopVals[i] * sopVals[i];
    }
    var corrNum = n * sumXY - sumX * sumY;
    var corrDen = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
    var corr = corrDen > 0 ? corrNum / corrDen : 0;

    svg.append('text')
        .attr('x', cw - margin.right - 5)
        .attr('y', margin.top + 14)
        .attr('text-anchor', 'end')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px')
        .style('opacity', 0.7)
        .text('r = ' + corr.toFixed(3) + ' (n=' + n + ')');
}

/* --- Compensation Treemap --- */
function drawCompTreemap(companies) {
    var container = document.getElementById('comp-treemap-chart');
    if (!container) return;
    container.innerHTML = '';

    var valid = companies.filter(function(c) { return c.total_compensation > 0 && c.sector; });
    if (valid.length === 0) return;

    var dark = typeof isDarkTheme === 'function' && isDarkTheme();
    var textColor = dark ? '#e4e4e7' : '#1a1a2e';
    var mutedColor = dark ? '#a1a1aa' : '#6b7280';
    var bgColor = dark ? 'rgba(0,0,0,0.55)' : 'rgba(255,255,255,0.65)';

    // Build hierarchical data: root → sectors → companies
    var sectorMap = {};
    valid.forEach(function(c) {
        if (!sectorMap[c.sector]) sectorMap[c.sector] = [];
        sectorMap[c.sector].push(c);
    });

    var hierarchyData = {
        name: 'S&P 500',
        children: Object.keys(sectorMap).map(function(sec) {
            return {
                name: sec,
                children: sectorMap[sec].map(function(c) {
                    return {
                        name: c.ticker,
                        company: c.company_name,
                        ceo: c.ceo_name,
                        comp: c.total_compensation,
                        sector: sec,
                        value: c.total_compensation
                    };
                })
            };
        })
    };

    // Sort sectors by total compensation descending for layout
    hierarchyData.children.sort(function(a, b) {
        var sumA = a.children.reduce(function(s, c) { return s + c.value; }, 0);
        var sumB = b.children.reduce(function(s, c) { return s + c.value; }, 0);
        return sumB - sumA;
    });

    var cw = container.clientWidth || 900;
    var ch = 520;
    var margin = { top: 0, right: 0, bottom: 0, left: 0 };
    var width = cw - margin.left - margin.right;
    var height = ch - margin.top - margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', cw)
        .attr('height', ch)
        .attr('role', 'img')
        .attr('aria-label', 'CEO compensation treemap grouped by sector');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    // Create hierarchy and compute treemap layout
    var root = d3.hierarchy(hierarchyData)
        .sum(function(d) { return d.value || 0; })
        .sort(function(a, b) { return b.value - a.value; });

    d3.treemap()
        .size([width, height])
        .paddingTop(22)
        .paddingRight(2)
        .paddingBottom(2)
        .paddingLeft(2)
        .paddingInner(1)
        .round(true)(root);

    var sectorColors = typeof SECTOR_COLORS_APP !== 'undefined' ? SECTOR_COLORS_APP : {};
    function getSectorClr(s) { return sectorColors[s] || '#94a3b8'; }

    // Sector groups (depth 1)
    var sectorNodes = root.children || [];
    var sectorGroups = g.selectAll('.treemap-sector')
        .data(sectorNodes)
        .enter()
        .append('g')
        .attr('class', 'treemap-sector');

    // Sector background rect
    sectorGroups.append('rect')
        .attr('x', function(d) { return d.x0; })
        .attr('y', function(d) { return d.y0; })
        .attr('width', function(d) { return Math.max(0, d.x1 - d.x0); })
        .attr('height', function(d) { return Math.max(0, d.y1 - d.y0); })
        .attr('fill', function(d) {
            var c = d3.color(getSectorClr(d.data.name));
            return c ? c.copy({ opacity: 0.08 }) : 'rgba(128,128,128,0.08)';
        })
        .attr('stroke', function(d) {
            var c = d3.color(getSectorClr(d.data.name));
            return c ? c.copy({ opacity: 0.3 }) : 'rgba(128,128,128,0.3)';
        })
        .attr('stroke-width', 1);

    // Sector label
    sectorGroups.append('text')
        .attr('x', function(d) { return d.x0 + 5; })
        .attr('y', function(d) { return d.y0 + 15; })
        .style('fill', function(d) { return getSectorClr(d.data.name); })
        .style('font-size', '11px')
        .style('font-weight', '600')
        .style('pointer-events', 'none')
        .text(function(d) {
            var w = d.x1 - d.x0;
            // Abbreviate for narrow sectors
            var name = d.data.name;
            if (w < 80) return '';
            if (w < 150) {
                var abbr = {
                    'Information Technology': 'IT',
                    'Communication Services': 'Comm',
                    'Consumer Discretionary': 'Cons Disc',
                    'Consumer Staples': 'Staples',
                    'Health Care': 'Health',
                    'Financials': 'Finance',
                    'Industrials': 'Indust',
                    'Real Estate': 'RE',
                    'Materials': 'Matls',
                    'Utilities': 'Utils',
                    'Energy': 'Energy'
                };
                return abbr[name] || name;
            }
            return name;
        });

    // Company leaf nodes (depth 2)
    var leaves = root.leaves();
    var leafGroups = g.selectAll('.treemap-leaf')
        .data(leaves)
        .enter()
        .append('g')
        .attr('class', 'treemap-leaf')
        .style('cursor', 'pointer');

    leafGroups.append('rect')
        .attr('x', function(d) { return d.x0; })
        .attr('y', function(d) { return d.y0; })
        .attr('width', function(d) { return Math.max(0, d.x1 - d.x0); })
        .attr('height', function(d) { return Math.max(0, d.y1 - d.y0); })
        .attr('fill', function(d) {
            var sec = d.parent ? d.parent.data.name : '';
            var base = d3.color(getSectorClr(sec));
            if (!base) return '#94a3b8';
            // Vary opacity by compensation rank within sector to add depth
            var siblings = d.parent ? d.parent.children : [];
            var maxVal = siblings.length > 0 ? siblings[0].value : d.value;
            var t = maxVal > 0 ? Math.max(0.35, Math.min(0.9, 0.35 + 0.55 * (d.value / maxVal))) : 0.5;
            return base.copy({ opacity: t });
        })
        .attr('stroke', dark ? 'rgba(20,20,30,0.6)' : 'rgba(255,255,255,0.7)')
        .attr('stroke-width', 0.5)
        .attr('rx', 1)
        .on('mouseover', function(event, d) {
            d3.select(this).attr('stroke', '#fff').attr('stroke-width', 2);
            var data = d.data;
            var sec = d.parent ? d.parent.data.name : '';
            var sectorTotal = d.parent ? d.parent.value : 0;
            var pctOfSector = sectorTotal > 0 ? (d.value / sectorTotal * 100).toFixed(1) : '0';
            var pctOfSP500 = root.value > 0 ? (d.value / root.value * 100).toFixed(2) : '0';
            showChartTooltip(event,
                '<strong>' + data.company + '</strong> (' + data.name + ')<br>' +
                'CEO: ' + (data.ceo || 'N/A') + '<br>' +
                'Total Comp: <strong>' + fmtCurr(data.comp) + '</strong><br>' +
                sec + ': ' + pctOfSector + '% of sector<br>' +
                'S&P 500: ' + pctOfSP500 + '% of total'
            );
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function(event, d) {
            d3.select(this)
                .attr('stroke', dark ? 'rgba(20,20,30,0.6)' : 'rgba(255,255,255,0.7)')
                .attr('stroke-width', 0.5);
            hideChartTooltip();
        })
        .on('click', function(event, d) {
            if (window.findCompanyInTable) window.findCompanyInTable(d.data.name);
        });

    // Labels for leaves — show ticker only if cell is large enough
    leafGroups.append('text')
        .attr('x', function(d) { return d.x0 + 3; })
        .attr('y', function(d) { return d.y0 + 13; })
        .style('fill', function() { return dark ? '#fff' : '#1a1a2e'; })
        .style('font-size', function(d) {
            var w = d.x1 - d.x0;
            var h = d.y1 - d.y0;
            if (w > 70 && h > 35) return '11px';
            if (w > 45 && h > 22) return '9px';
            return '7px';
        })
        .style('font-weight', '600')
        .style('pointer-events', 'none')
        .style('opacity', function(d) {
            return (d.x1 - d.x0) > 28 && (d.y1 - d.y0) > 16 ? 1 : 0;
        })
        .text(function(d) { return d.data.name; });

    // Compensation value label (only for large cells)
    leafGroups.append('text')
        .attr('x', function(d) { return d.x0 + 3; })
        .attr('y', function(d) { return d.y0 + 25; })
        .style('fill', mutedColor)
        .style('font-size', '8px')
        .style('font-weight', '400')
        .style('pointer-events', 'none')
        .style('opacity', function(d) {
            return (d.x1 - d.x0) > 55 && (d.y1 - d.y0) > 30 ? 0.85 : 0;
        })
        .text(function(d) { return fmtCurr(d.value); });

    // Stats summary below treemap
    var totalComp = root.value;
    var topSector = sectorNodes[0];
    var topSectorPct = totalComp > 0 ? (topSector.value / totalComp * 100).toFixed(1) : '0';
    var top10Companies = leaves.slice().sort(function(a, b) { return b.value - a.value; }).slice(0, 10);
    var top10Sum = top10Companies.reduce(function(s, c) { return s + c.value; }, 0);
    var top10Pct = totalComp > 0 ? (top10Sum / totalComp * 100).toFixed(1) : '0';

    var statsEl = document.createElement('div');
    statsEl.className = 'treemap-stats';
    statsEl.innerHTML =
        '<span class="treemap-stat">Total CEO Pay: <strong>' + fmtCurr(totalComp) + '</strong></span>' +
        '<span class="treemap-stat-sep">·</span>' +
        '<span class="treemap-stat">Largest Sector: <strong style="color:' + getSectorClr(topSector.data.name) + '">' + topSector.data.name + '</strong> (' + topSectorPct + '%)</span>' +
        '<span class="treemap-stat-sep">·</span>' +
        '<span class="treemap-stat">Top 10 CEOs: <strong>' + top10Pct + '%</strong> of total</span>' +
        '<span class="treemap-stat-sep">·</span>' +
        '<span class="treemap-stat">' + valid.length + ' companies</span>';
    container.appendChild(statsEl);
}

/* ----------------------------------------------------------------
   Correlation Matrix Heatmap
   Shows Pearson correlations between all key compensation metrics.
   Click any cell to configure the scatter plot to that metric pair.
   ---------------------------------------------------------------- */
/* === Statistical helper functions for p-value computation === */

/* Log-gamma function (Lanczos approximation) */
function _lnGamma(x) {
    var cof = [76.18009172947146, -86.50532032941677, 24.01409824083091,
               -1.231739572450155, 0.001208650973866179, -5.395239384953e-6];
    var y = x, tmp = x + 5.5;
    tmp -= (x + 0.5) * Math.log(tmp);
    var ser = 1.000000000190015;
    for (var j = 0; j < 6; j++) ser += cof[j] / ++y;
    return -tmp + Math.log(2.5066282746310005 * ser / x);
}

/* Continued fraction for regularized incomplete beta (Lentz method) */
function _betacf(a, b, x) {
    var maxIter = 200, eps = 3e-12;
    var qab = a + b, qap = a + 1, qam = a - 1;
    var c = 1, d = 1 - qab * x / qap;
    if (Math.abs(d) < 1e-30) d = 1e-30;
    d = 1 / d;
    var h = d;
    for (var m = 1; m <= maxIter; m++) {
        var m2 = 2 * m;
        var aa = m * (b - m) * x / ((qam + m2) * (a + m2));
        d = 1 + aa * d; if (Math.abs(d) < 1e-30) d = 1e-30; d = 1 / d;
        c = 1 + aa / c; if (Math.abs(c) < 1e-30) c = 1e-30;
        h *= d * c;
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
        d = 1 + aa * d; if (Math.abs(d) < 1e-30) d = 1e-30; d = 1 / d;
        c = 1 + aa / c; if (Math.abs(c) < 1e-30) c = 1e-30;
        var del = d * c;
        h *= del;
        if (Math.abs(del - 1) < eps) break;
    }
    return h;
}

/* Regularized incomplete beta function I_x(a, b) */
function _betainc(a, b, x) {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    var bt = Math.exp(_lnGamma(a + b) - _lnGamma(a) - _lnGamma(b) + a * Math.log(x) + b * Math.log(1 - x));
    if (x < (a + 1) / (a + b + 2)) {
        return bt * _betacf(a, b, x) / a;
    } else {
        return 1 - bt * _betacf(b, a, 1 - x) / b;
    }
}

/* Two-tailed p-value for Pearson r given sample size n.
   Uses the t-distribution with df = n-2. */
function _pearsonPValue(r, sampleN) {
    if (r == null || sampleN < 3) return null;
    var absR = Math.abs(r);
    if (absR >= 1) return 0;
    if (absR < 1e-15) return 1;
    var df = sampleN - 2;
    var t2 = r * r * df / (1 - r * r);
    var x = df / (df + t2);
    return _betainc(df / 2, 0.5, x);
}

/* Significance label from p-value */
function _sigStars(p) {
    if (p == null) return '';
    if (p < 0.001) return '***';
    if (p < 0.01) return '**';
    if (p < 0.05) return '*';
    return '';
}

function _sigLabel(p) {
    if (p == null) return 'n/a';
    if (p < 0.001) return 'p < 0.001';
    if (p < 0.01) return 'p < 0.01';
    if (p < 0.05) return 'p < 0.05';
    return 'p = ' + (p < 0.1 ? p.toFixed(3) : p.toFixed(2));
}

function drawCorrelationMatrix(companies) {
    var container = document.getElementById('correlation-matrix-chart');
    if (!container) return;
    container.innerHTML = '';

    var dark = document.body.classList.contains('dark-mode') ||
               (!document.body.classList.contains('light-mode') && window.matchMedia('(prefers-color-scheme: dark)').matches);

    // Sector filter: use only sector companies if active
    var sector = window._activeSector || null;
    var filteredCompanies = sector
        ? companies.filter(function(c) { return c.sector === sector; })
        : companies;

    if (filteredCompanies.length < 15) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient data for correlation analysis (' + filteredCompanies.length + ' companies)</p>';
        return;
    }

    // Update chart panel header for sector context
    var headerTitle = container.closest('.chart-panel');
    if (headerTitle) {
        var h2 = headerTitle.querySelector('h2');
        var desc = headerTitle.querySelector('.section-desc');
        if (h2) h2.textContent = sector ? sector + ' Metric Correlations' : 'Metric Correlations';
        if (desc) desc.textContent = sector
            ? 'Pearson correlations for ' + filteredCompanies.length + ' ' + sector + ' companies. ▲▼ arrows show divergence from S&P 500 overall. Click any cell to explore in the scatter plot.'
            : 'Pearson correlation coefficients between key compensation metrics. Blue = negative correlation, red = positive. Click any cell to explore that pair in the scatter plot.';
    }

    // Define metrics
    var metrics = [
        { key: 'total_compensation', label: 'CEO Pay', short: 'CEO Pay', get: function(c) { return c.total_compensation; } },
        { key: 'pay_ratio', label: 'Pay Ratio', short: 'Ratio', get: function(c) { return c.pay_ratio; } },
        { key: 'median_worker_pay', label: 'Worker Pay', short: 'Worker', get: function(c) { return c.median_worker_pay; } },
        { key: '_ceoStockPctSort', label: 'Stock Awards %', short: 'Stock%', get: function(c) { return c._ceoStockPctSort; } },
        { key: '_ceoConcPct', label: 'CEO Concentration %', short: 'Conc%', get: function(c) { return c._ceoConcPct; } },
        { key: '_ceoYoYPct', label: 'YoY Change %', short: 'YoY%', get: function(c) { return c._ceoYoY ? c._ceoYoY.pct : null; } },
        { key: '_sopApproval', label: 'Say-on-Pay %', short: 'SoP%', get: function(c) { return c._sopApproval; } },
        { key: '_ceoCfoPremium', label: 'CEO/CFO Premium', short: 'CEO/CFO', get: function(c) { return c._ceoCfoPremium; } },
        { key: '_ceoTenureYears', label: 'CEO Tenure (Years)', short: 'Tenure', get: function(c) { return c._ceoTenureYears; } },
        { key: '_govScore', label: 'Governance Score', short: 'Gov', get: function(c) { return c._govScore; } },
        { key: '_gerScore', label: 'Governance Erosion Risk', short: 'GER', get: function(c) { return c._gerScore; } }
    ];

    var n = metrics.length;

    // Compute Pearson correlation for each pair
    function pearson(xArr, yArr) {
        var pairs = [];
        for (var k = 0; k < xArr.length; k++) {
            if (xArr[k] != null && yArr[k] != null && isFinite(xArr[k]) && isFinite(yArr[k])) {
                pairs.push([xArr[k], yArr[k]]);
            }
        }
        if (pairs.length < 10) return { r: null, n: pairs.length, p: null };
        var mx = 0, my = 0;
        pairs.forEach(function(p) { mx += p[0]; my += p[1]; });
        mx /= pairs.length; my /= pairs.length;
        var sxy = 0, sxx = 0, syy = 0;
        pairs.forEach(function(p) {
            var dx = p[0] - mx, dy = p[1] - my;
            sxy += dx * dy; sxx += dx * dx; syy += dy * dy;
        });
        if (sxx === 0 || syy === 0) return { r: 0, n: pairs.length, p: 1 };
        var rVal = sxy / Math.sqrt(sxx * syy);
        return { r: rVal, n: pairs.length, p: _pearsonPValue(rVal, pairs.length) };
    }

    // Pre-extract metric arrays
    var metricArrays = metrics.map(function(m) {
        return filteredCompanies.map(m.get);
    });

    // Build correlation matrix
    var corrMatrix = [];
    for (var i = 0; i < n; i++) {
        corrMatrix[i] = [];
        for (var j = 0; j < n; j++) {
            if (i === j) {
                corrMatrix[i][j] = { r: 1, n: filteredCompanies.length, p: 0 };
            } else if (j < i) {
                corrMatrix[i][j] = corrMatrix[j][i]; // symmetric
            } else {
                corrMatrix[i][j] = pearson(metricArrays[i], metricArrays[j]);
            }
        }
    }

    // When sector is active, also compute S&P 500-wide correlation matrix for comparison
    var overallCorrMatrix = null;
    if (sector) {
        var overallArrays = metrics.map(function(m) { return companies.map(m.get); });
        overallCorrMatrix = [];
        for (var oi = 0; oi < n; oi++) {
            overallCorrMatrix[oi] = [];
            for (var oj = 0; oj < n; oj++) {
                if (oi === oj) {
                    overallCorrMatrix[oi][oj] = { r: 1, n: companies.length, p: 0 };
                } else if (oj < oi) {
                    overallCorrMatrix[oi][oj] = overallCorrMatrix[oj][oi];
                } else {
                    overallCorrMatrix[oi][oj] = pearson(overallArrays[oi], overallArrays[oj]);
                }
            }
        }
    }

    // SVG dimensions
    var fullW = container.clientWidth || 600;
    var cellSize = Math.min(Math.floor((fullW - 140) / n), 72);
    var labelW = 110;
    var labelH = 90;
    var w = labelW + cellSize * n;
    var h = labelH + cellSize * n;
    var totalW = w + 80; // extra for color legend

    var svg = d3.select(container)
        .append('svg')
        .attr('width', totalW)
        .attr('height', h + 10)
        .attr('viewBox', '0 0 ' + totalW + ' ' + (h + 10))
        .attr('role', 'img')
        .attr('aria-label', 'Correlation matrix heatmap showing Pearson correlations between compensation metrics');

    // Color scale: diverging blue-white-red
    var colorScale = function(r) {
        if (r == null) return dark ? '#27272a' : '#f4f4f5';
        // Blue (negative) → neutral → Red (positive)
        var abs = Math.abs(r);
        if (r >= 0) {
            // Neutral to red/warm
            var warmR = Math.round(255 - (255 - 239) * abs);
            var warmG = Math.round((dark ? 39 : 250) - (dark ? 39 : 250 - 68) * abs);
            var warmB = Math.round((dark ? 68 : 245) - (dark ? 68 : 245 - 68) * abs);
            return 'rgb(' + warmR + ',' + warmG + ',' + warmB + ')';
        } else {
            // Neutral to blue/cool
            var coolR = Math.round((dark ? 39 : 250) - (dark ? 39 : 250 - 59) * abs);
            var coolG = Math.round((dark ? 39 : 250) - (dark ? 39 : 250 - 130) * abs);
            var coolB = Math.round(255 - (255 - 246) * abs);
            return 'rgb(' + coolR + ',' + coolG + ',' + coolB + ')';
        }
    };

    var textColor = function(r) {
        if (r == null) return dark ? '#71717a' : '#a1a1aa';
        var abs = Math.abs(r);
        if (abs > 0.5) return '#fff';
        return dark ? '#e4e4e7' : '#27272a';
    };

    // Column labels (top, rotated)
    var colLabels = svg.selectAll('.corr-col-label')
        .data(metrics)
        .enter()
        .append('text')
        .attr('class', 'corr-col-label')
        .attr('x', function(d, i) { return labelW + i * cellSize + cellSize / 2; })
        .attr('y', labelH - 6)
        .attr('text-anchor', 'end')
        .attr('transform', function(d, i) {
            var cx = labelW + i * cellSize + cellSize / 2;
            return 'rotate(-45,' + cx + ',' + (labelH - 6) + ')';
        })
        .attr('fill', dark ? '#a1a1aa' : '#52525b')
        .attr('font-size', '0.7rem')
        .attr('font-weight', '500')
        .text(function(d) { return d.short; });

    // Row labels (left)
    var rowLabels = svg.selectAll('.corr-row-label')
        .data(metrics)
        .enter()
        .append('text')
        .attr('class', 'corr-row-label')
        .attr('x', labelW - 8)
        .attr('y', function(d, i) { return labelH + i * cellSize + cellSize / 2 + 4; })
        .attr('text-anchor', 'end')
        .attr('fill', dark ? '#a1a1aa' : '#52525b')
        .attr('font-size', '0.7rem')
        .attr('font-weight', '500')
        .text(function(d) { return d.short; });

    // Cells
    for (var ri = 0; ri < n; ri++) {
        for (var ci = 0; ci < n; ci++) {
            (function(row, col) {
                var corr = corrMatrix[row][col];
                var r = corr.r;
                var cx = labelW + col * cellSize;
                var cy = labelH + row * cellSize;
                var pad = 2;
                var isDiagonal = row === col;

                // Cell background
                var rect = svg.append('rect')
                    .attr('x', cx + pad)
                    .attr('y', cy + pad)
                    .attr('width', cellSize - pad * 2)
                    .attr('height', cellSize - pad * 2)
                    .attr('rx', 4)
                    .attr('fill', isDiagonal ? (dark ? '#3f3f46' : '#e4e4e7') : colorScale(r))
                    .attr('stroke', 'none')
                    .attr('cursor', isDiagonal ? 'default' : 'pointer')
                    .attr('opacity', isDiagonal ? 0.5 : 1);

                // Significance stars
                var pVal = corr.p;
                var stars = _sigStars(pVal);

                // Compute delta vs S&P 500 when sector is active
                var delta = null;
                var overallR = null;
                if (overallCorrMatrix && !isDiagonal) {
                    overallR = overallCorrMatrix[row][col].r;
                    if (r != null && overallR != null) {
                        delta = r - overallR;
                    }
                }
                var hasDelta = delta != null && sector;

                // Correlation value text + significance indicator
                var label = isDiagonal ? '—' : (r != null ? (r >= 0 ? '+' : '') + r.toFixed(2) : 'n/a');
                // Tighter vertical layout when showing delta
                var baseOffset = hasDelta ? -8 : (stars ? -6 : -3);
                var labelYOffset = r != null && !isDiagonal ? baseOffset : 4;
                svg.append('text')
                    .attr('x', cx + cellSize / 2)
                    .attr('y', cy + cellSize / 2 + labelYOffset)
                    .attr('text-anchor', 'middle')
                    .attr('fill', isDiagonal ? (dark ? '#71717a' : '#a1a1aa') : textColor(r))
                    .attr('font-size', cellSize > 55 ? '0.78rem' : '0.65rem')
                    .attr('font-weight', '600')
                    .text(label);

                // Significance stars (gold, below r value)
                if (!isDiagonal && stars) {
                    var starsY = hasDelta ? -1 : (cellSize > 55 ? 5 : 3);
                    svg.append('text')
                        .attr('x', cx + cellSize / 2)
                        .attr('y', cy + cellSize / 2 + starsY)
                        .attr('text-anchor', 'middle')
                        .attr('fill', dark ? '#fbbf24' : '#d97706')
                        .attr('font-size', cellSize > 55 ? '0.68rem' : '0.55rem')
                        .attr('font-weight', '700')
                        .text(stars);
                }

                // Delta vs S&P 500 (shown when sector is active)
                if (hasDelta) {
                    var deltaSign = delta >= 0 ? '▲' : '▼';
                    var deltaStr = deltaSign + Math.abs(delta).toFixed(2);
                    var deltaColor;
                    if (Math.abs(delta) < 0.05) {
                        deltaColor = dark ? '#71717a' : '#a1a1aa'; // negligible
                    } else if (Math.abs(delta) >= 0.15) {
                        deltaColor = delta > 0 ? (dark ? '#34d399' : '#059669') : (dark ? '#f87171' : '#dc2626'); // large divergence
                    } else {
                        deltaColor = dark ? '#fbbf24' : '#d97706'; // moderate divergence
                    }
                    svg.append('text')
                        .attr('x', cx + cellSize / 2)
                        .attr('y', cy + cellSize / 2 + (stars ? 9 : 6))
                        .attr('text-anchor', 'middle')
                        .attr('fill', deltaColor)
                        .attr('font-size', cellSize > 55 ? '0.52rem' : '0.44rem')
                        .attr('font-weight', '600')
                        .text(deltaStr);
                }

                // Sample size (small, below stars/r value or delta)
                if (!isDiagonal && r != null) {
                    var nY;
                    if (hasDelta) {
                        nY = stars ? 18 : 15;
                    } else {
                        nY = cellSize > 55 ? (stars ? 16 : 12) : (stars ? 12 : 9);
                    }
                    svg.append('text')
                        .attr('x', cx + cellSize / 2)
                        .attr('y', cy + cellSize / 2 + nY)
                        .attr('text-anchor', 'middle')
                        .attr('fill', textColor(r))
                        .attr('font-size', cellSize > 55 ? '0.55rem' : '0.48rem')
                        .attr('opacity', 0.6)
                        .text('n=' + corr.n);
                }

                // Hover and click for non-diagonal cells
                if (!isDiagonal && r != null) {
                    // Capture variables for closure
                    (function(rowIdx, colIdx, corrData, cellDelta, cellOverallR) {
                        var strength = Math.abs(corrData.r) >= 0.7 ? 'Strong' : Math.abs(corrData.r) >= 0.4 ? 'Moderate' : Math.abs(corrData.r) >= 0.2 ? 'Weak' : 'Very weak';
                        var direction = Math.abs(corrData.r) >= 0.2 ? (corrData.r > 0 ? ' positive' : ' negative') : '';
                        var sigText = _sigLabel(corrData.p);
                        var sigStars = _sigStars(corrData.p);

                        rect.on('mouseenter', function(event) {
                            d3.select(this).attr('stroke', dark ? '#ffd166' : '#f59e0b').attr('stroke-width', 2);
                            var html = '<div class="ct-title">' + metrics[rowIdx].label + ' vs ' + metrics[colIdx].label + '</div>' +
                                '<div class="ct-row"><span class="ct-label">Pearson r</span><span class="ct-val">' + (corrData.r >= 0 ? '+' : '') + corrData.r.toFixed(3) + (sigStars ? ' <span style="color:#fbbf24;font-weight:700">' + sigStars + '</span>' : '') + '</span></div>' +
                                '<div class="ct-row"><span class="ct-label">Significance</span><span class="ct-val">' + sigText + '</span></div>' +
                                '<div class="ct-row"><span class="ct-label">Sample size</span><span class="ct-val">n = ' + corrData.n + '</span></div>' +
                                '<div class="ct-row"><span class="ct-label">Strength</span><span class="ct-val">' + strength + direction + '</span></div>';
                            // Sector comparison line
                            if (cellOverallR != null && sector) {
                                var dSign = cellDelta >= 0 ? '+' : '';
                                var dColor = Math.abs(cellDelta) >= 0.15 ? (cellDelta > 0 ? '#34d399' : '#f87171') : (Math.abs(cellDelta) >= 0.05 ? '#fbbf24' : '#94a3b8');
                                html += '<div class="ct-row" style="border-top:1px solid ' + (dark ? '#3f3f46' : '#e4e4e7') + ';margin-top:4px;padding-top:4px;"><span class="ct-label">S&P 500 r</span><span class="ct-val">' + (cellOverallR >= 0 ? '+' : '') + cellOverallR.toFixed(3) + '</span></div>' +
                                    '<div class="ct-row"><span class="ct-label">Sector Δ</span><span class="ct-val" style="color:' + dColor + '">' + dSign + cellDelta.toFixed(3) + '</span></div>';
                            }
                            html += '<div style="margin-top:6px;font-size:0.65rem;color:#a1a1aa;text-align:center;">Click to explore in scatter plot</div>';
                            showChartTooltip(event, html);
                        })
                        .on('mousemove', function(event) {
                            positionChartTooltip(event);
                        })
                        .on('mouseleave', function() {
                            d3.select(this).attr('stroke', 'none');
                            hideChartTooltip();
                        })
                        .on('click', function() {
                            hideChartTooltip();
                            var xSel = document.getElementById('scatter-x-metric');
                            var ySel = document.getElementById('scatter-y-metric');
                            if (xSel && ySel) {
                                xSel.value = metrics[colIdx].key;
                                ySel.value = metrics[rowIdx].key;
                                xSel.dispatchEvent(new Event('change'));
                                var scatterPanel = document.getElementById('scatter-chart-panel');
                                if (scatterPanel) {
                                    scatterPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                }
                            }
                            // Also update cross-sector correlation chart with clicked pair
                            var csEl = document.getElementById('cross-sector-corr-chart');
                            if (csEl) csEl.innerHTML = '';
                            drawCrossSectorCorrelation(_chartData.companies, colIdx, rowIdx);
                        });
                    })(row, col, corr, delta, overallR);
                }
            })(ri, ci);
        }
    }

    // Color legend (right side)
    var legendX = w + 16;
    var legendH = cellSize * n - 20;
    var legendY = labelH + 10;
    var legendW = 14;

    // Legend gradient
    var gradId = 'corr-legend-grad-' + Date.now();
    var defs = svg.append('defs');
    var grad = defs.append('linearGradient')
        .attr('id', gradId)
        .attr('x1', '0')
        .attr('y1', '0')
        .attr('x2', '0')
        .attr('y2', '1');

    var gradStops = [
        { offset: '0%', r: 1 },
        { offset: '25%', r: 0.5 },
        { offset: '50%', r: 0 },
        { offset: '75%', r: -0.5 },
        { offset: '100%', r: -1 }
    ];
    gradStops.forEach(function(s) {
        grad.append('stop')
            .attr('offset', s.offset)
            .attr('stop-color', colorScale(s.r));
    });

    svg.append('rect')
        .attr('x', legendX)
        .attr('y', legendY)
        .attr('width', legendW)
        .attr('height', legendH)
        .attr('rx', 3)
        .attr('fill', 'url(#' + gradId + ')');

    // Legend labels
    var legendLabels = [
        { val: '+1.0', y: legendY },
        { val: '+0.5', y: legendY + legendH * 0.25 },
        { val: '0', y: legendY + legendH * 0.5 },
        { val: '−0.5', y: legendY + legendH * 0.75 },
        { val: '−1.0', y: legendY + legendH }
    ];
    legendLabels.forEach(function(l) {
        svg.append('text')
            .attr('x', legendX + legendW + 6)
            .attr('y', l.y + 4)
            .attr('fill', dark ? '#a1a1aa' : '#71717a')
            .attr('font-size', '0.55rem')
            .text(l.val);
    });

    svg.append('text')
        .attr('x', legendX + legendW / 2)
        .attr('y', legendY - 8)
        .attr('text-anchor', 'middle')
        .attr('fill', dark ? '#a1a1aa' : '#71717a')
        .attr('font-size', '0.55rem')
        .attr('font-weight', '600')
        .text('r');

    // Summary stats below the matrix
    var statsEl = document.createElement('div');
    statsEl.className = 'corr-matrix-stats';

    // Find strongest positive and negative correlations (excluding diagonal)
    var allCorrs = [];
    for (var si = 0; si < n; si++) {
        for (var sj = si + 1; sj < n; sj++) {
            if (corrMatrix[si][sj].r != null) {
                allCorrs.push({
                    r: corrMatrix[si][sj].r,
                    n: corrMatrix[si][sj].n,
                    p: corrMatrix[si][sj].p,
                    m1: metrics[si],
                    m2: metrics[sj]
                });
            }
        }
    }

    allCorrs.sort(function(a, b) { return b.r - a.r; });
    var strongest = allCorrs[0];
    var weakest = allCorrs[allCorrs.length - 1];
    var strongestNeg = allCorrs.filter(function(c) { return c.r < 0; }).sort(function(a, b) { return a.r - b.r; })[0];
    var sigCount = allCorrs.filter(function(c) { return c.p != null && c.p < 0.05; }).length;

    var statsHtml = '';
    if (strongest) {
        statsHtml += '<span class="corr-stat">Strongest +: <strong>' + strongest.m1.short + ' × ' + strongest.m2.short + '</strong> (r=' + strongest.r.toFixed(2) + ')</span>';
    }
    if (strongestNeg) {
        statsHtml += '<span class="corr-stat-sep">·</span>';
        statsHtml += '<span class="corr-stat">Strongest −: <strong>' + strongestNeg.m1.short + ' × ' + strongestNeg.m2.short + '</strong> (r=' + strongestNeg.r.toFixed(2) + ')</span>';
    }
    statsHtml += '<span class="corr-stat-sep">·</span>';
    statsHtml += '<span class="corr-stat">' + sigCount + '/' + allCorrs.length + ' pairs significant (p&lt;0.05)</span>';

    // Sector divergence stats when sector filter is active
    if (sector && overallCorrMatrix) {
        var divergences = [];
        for (var di = 0; di < n; di++) {
            for (var dj = di + 1; dj < n; dj++) {
                var sR = corrMatrix[di][dj].r;
                var oR = overallCorrMatrix[di][dj].r;
                if (sR != null && oR != null) {
                    divergences.push({
                        delta: sR - oR,
                        sectorR: sR,
                        overallR: oR,
                        m1: metrics[di],
                        m2: metrics[dj]
                    });
                }
            }
        }
        divergences.sort(function(a, b) { return Math.abs(b.delta) - Math.abs(a.delta); });
        if (divergences.length > 0) {
            var topDiv = divergences[0];
            var divSign = topDiv.delta >= 0 ? '+' : '';
            var divColor = topDiv.delta > 0 ? (dark ? '#34d399' : '#059669') : (dark ? '#f87171' : '#dc2626');
            statsHtml += '<span class="corr-stat-sep">·</span>';
            statsHtml += '<span class="corr-stat">Largest divergence: <strong>' + topDiv.m1.short + ' × ' + topDiv.m2.short + '</strong> (<span style="color:' + divColor + '">Δ' + divSign + topDiv.delta.toFixed(2) + '</span>, sector r=' + topDiv.sectorR.toFixed(2) + ' vs S&P r=' + topDiv.overallR.toFixed(2) + ')</span>';
        }
        var strongDiv = divergences.filter(function(d) { return Math.abs(d.delta) >= 0.15; }).length;
        if (strongDiv > 0) {
            statsHtml += '<span class="corr-stat-sep">·</span>';
            statsHtml += '<span class="corr-stat">' + strongDiv + ' pairs diverge strongly (|Δ|≥0.15) from S&P 500</span>';
        }
    } else {
        statsHtml += '<span class="corr-stat-sep">·</span>';
        statsHtml += '<span class="corr-stat corr-sig-legend"><span style="color:' + (dark ? '#fbbf24' : '#d97706') + ';font-weight:700">***</span> p&lt;0.001 <span style="color:' + (dark ? '#fbbf24' : '#d97706') + ';font-weight:700">**</span> p&lt;0.01 <span style="color:' + (dark ? '#fbbf24' : '#d97706') + ';font-weight:700">*</span> p&lt;0.05</span>';
    }
    statsEl.innerHTML = statsHtml;
    container.appendChild(statsEl);
}


/* ============================================================
   Cross-Sector Correlation Comparison — horizontal bar chart
   showing how a single metric-pair Pearson r varies across
   all 11 GICS sectors.
   ============================================================ */

var _crossSectorMetricX = 0; // default: CEO Pay
var _crossSectorMetricY = 1; // default: Pay Ratio

function drawCrossSectorCorrelation(companies, metricIdxX, metricIdxY) {
    var container = document.getElementById('cross-sector-corr-chart');
    var controlsEl = document.getElementById('cross-sector-controls');
    if (!container) return;
    container.innerHTML = '';

    if (metricIdxX != null) _crossSectorMetricX = metricIdxX;
    if (metricIdxY != null) _crossSectorMetricY = metricIdxY;

    var dark = document.body.classList.contains('dark-mode') ||
               (!document.body.classList.contains('light-mode') && window.matchMedia('(prefers-color-scheme: dark)').matches);

    // Same metrics array as drawCorrelationMatrix
    var metrics = [
        { key: 'total_compensation', label: 'CEO Pay', short: 'CEO Pay', get: function(c) { return c.total_compensation; } },
        { key: 'pay_ratio', label: 'Pay Ratio', short: 'Ratio', get: function(c) { return c.pay_ratio; } },
        { key: 'median_worker_pay', label: 'Worker Pay', short: 'Worker', get: function(c) { return c.median_worker_pay; } },
        { key: '_ceoStockPctSort', label: 'Stock Awards %', short: 'Stock%', get: function(c) { return c._ceoStockPctSort; } },
        { key: '_ceoConcPct', label: 'CEO Concentration %', short: 'Conc%', get: function(c) { return c._ceoConcPct; } },
        { key: '_ceoYoYPct', label: 'YoY Change %', short: 'YoY%', get: function(c) { return c._ceoYoY ? c._ceoYoY.pct : null; } },
        { key: '_sopApproval', label: 'Say-on-Pay %', short: 'SoP%', get: function(c) { return c._sopApproval; } },
        { key: '_ceoCfoPremium', label: 'CEO/CFO Premium', short: 'CEO/CFO', get: function(c) { return c._ceoCfoPremium; } },
        { key: '_ceoTenureYears', label: 'CEO Tenure (Years)', short: 'Tenure', get: function(c) { return c._ceoTenureYears; } },
        { key: '_govScore', label: 'Governance Score', short: 'Gov', get: function(c) { return c._govScore; } },
        { key: '_gerScore', label: 'Governance Erosion Risk', short: 'GER', get: function(c) { return c._gerScore; } }
    ];

    var SECTOR_COLORS = {
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

    // Build pair selector dropdown (28 unique pairs)
    if (controlsEl) {
        // Only build controls once — check for existing select
        if (!controlsEl.querySelector('.cross-sector-pair-select')) {
            var select = document.createElement('select');
            select.className = 'cross-sector-pair-select';
            select.setAttribute('aria-label', 'Select metric pair for cross-sector comparison');
            var pairIdx = 0;
            for (var pi = 0; pi < metrics.length; pi++) {
                for (var pj = pi + 1; pj < metrics.length; pj++) {
                    var opt = document.createElement('option');
                    opt.value = pi + ',' + pj;
                    opt.textContent = metrics[pi].short + ' × ' + metrics[pj].short;
                    if (pi === _crossSectorMetricX && pj === _crossSectorMetricY) opt.selected = true;
                    select.appendChild(opt);
                }
            }
            select.addEventListener('change', function() {
                var parts = this.value.split(',');
                _crossSectorMetricX = parseInt(parts[0]);
                _crossSectorMetricY = parseInt(parts[1]);
                var el = document.getElementById('cross-sector-corr-chart');
                if (el) el.innerHTML = '';
                drawCrossSectorCorrelation(_chartData.companies);
            });
            controlsEl.innerHTML = '';
            var label = document.createElement('span');
            label.className = 'cross-sector-pair-label';
            label.textContent = 'Metric pair:';
            controlsEl.appendChild(label);
            controlsEl.appendChild(select);
        } else {
            // Update selection state
            var existingSel = controlsEl.querySelector('.cross-sector-pair-select');
            existingSel.value = _crossSectorMetricX + ',' + _crossSectorMetricY;
        }
    }

    var mX = metrics[_crossSectorMetricX];
    var mY = metrics[_crossSectorMetricY];

    // Update title/description
    var titleEl = document.getElementById('cross-sector-corr-title');
    var descEl = document.getElementById('cross-sector-corr-desc');
    if (titleEl) titleEl.textContent = mX.short + ' × ' + mY.short + ' — Cross-Sector Comparison';
    if (descEl) descEl.textContent = 'Pearson correlation between ' + mX.label + ' and ' + mY.label + ' computed independently for each GICS sector. Dashed line = S&P 500 overall.';

    // Pearson helper (same as correlation matrix)
    function pearson(arr, getX, getY) {
        var pairs = [];
        arr.forEach(function(c) {
            var x = getX(c), y = getY(c);
            if (x != null && y != null && isFinite(x) && isFinite(y)) pairs.push([x, y]);
        });
        if (pairs.length < 5) return { r: null, n: pairs.length, p: null };
        var mx = 0, my = 0;
        pairs.forEach(function(p) { mx += p[0]; my += p[1]; });
        mx /= pairs.length; my /= pairs.length;
        var sxy = 0, sxx = 0, syy = 0;
        pairs.forEach(function(p) {
            var dx = p[0] - mx, dy = p[1] - my;
            sxy += dx * dy; sxx += dx * dx; syy += dy * dy;
        });
        if (sxx === 0 || syy === 0) return { r: 0, n: pairs.length, p: 1 };
        var rVal = sxy / Math.sqrt(sxx * syy);
        return { r: rVal, n: pairs.length, p: _pearsonPValue(rVal, pairs.length) };
    }

    // Compute overall S&P 500 correlation
    var overallCorr = pearson(companies, mX.get, mY.get);

    // Compute per-sector correlations
    var sectorNames = Object.keys(SECTOR_COLORS);
    var sectorData = [];
    sectorNames.forEach(function(s) {
        var sectorCompanies = companies.filter(function(c) { return c.sector === s; });
        var corr = pearson(sectorCompanies, mX.get, mY.get);
        sectorData.push({
            sector: s,
            r: corr.r,
            n: corr.n,
            p: corr.p,
            insufficient: corr.n < 10
        });
    });

    // Sort by r value (strongest positive at top), nulls at bottom
    sectorData.sort(function(a, b) {
        if (a.r == null && b.r == null) return 0;
        if (a.r == null) return 1;
        if (b.r == null) return -1;
        return b.r - a.r;
    });

    // SVG dimensions
    var fullW = container.clientWidth || 700;
    var margin = { top: 30, right: 120, bottom: 40, left: 185 };
    var barH = 28;
    var gap = 6;
    var chartH = sectorData.length * (barH + gap) + margin.top + margin.bottom;
    var chartW = fullW;
    var innerW = chartW - margin.left - margin.right;
    var innerH = sectorData.length * (barH + gap);

    var svg = d3.select(container)
        .append('svg')
        .attr('width', chartW)
        .attr('height', chartH)
        .attr('viewBox', '0 0 ' + chartW + ' ' + chartH)
        .attr('role', 'img')
        .attr('aria-label', 'Cross-sector correlation comparison bar chart');

    var g = svg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    // X scale: -1 to +1
    var xScale = d3.scaleLinear().domain([-1, 1]).range([0, innerW]);

    // Color scale: diverging blue-red (same as correlation matrix)
    function barColor(r) {
        if (r == null) return dark ? '#3f3f46' : '#e4e4e7';
        var abs = Math.abs(r);
        if (r >= 0) {
            var warmR = Math.round(255 - (255 - 239) * abs);
            var warmG = Math.round((dark ? 80 : 200) - (dark ? 80 : 200 - 68) * abs);
            var warmB = Math.round((dark ? 100 : 200) - (dark ? 100 : 200 - 68) * abs);
            return 'rgb(' + warmR + ',' + warmG + ',' + warmB + ')';
        } else {
            var coolR = Math.round((dark ? 80 : 200) - (dark ? 80 : 200 - 59) * abs);
            var coolG = Math.round((dark ? 80 : 200) - (dark ? 80 : 200 - 130) * abs);
            var coolB = Math.round(255 - (255 - 246) * abs);
            return 'rgb(' + coolR + ',' + coolG + ',' + coolB + ')';
        }
    }

    // X axis
    var xAxis = d3.axisBottom(xScale).ticks(9).tickFormat(function(d) { return d >= 0 ? '+' + d.toFixed(1) : d.toFixed(1); });
    g.append('g')
        .attr('transform', 'translate(0,' + innerH + ')')
        .call(xAxis)
        .selectAll('text')
        .attr('fill', dark ? '#a1a1aa' : '#71717a')
        .attr('font-size', '0.7rem');
    g.selectAll('.domain, .tick line').attr('stroke', dark ? '#3f3f46' : '#e4e4e7');

    // X axis label
    g.append('text')
        .attr('x', innerW / 2)
        .attr('y', innerH + 34)
        .attr('text-anchor', 'middle')
        .attr('fill', dark ? '#71717a' : '#a1a1aa')
        .attr('font-size', '0.7rem')
        .text('Pearson r');

    // Zero line
    g.append('line')
        .attr('x1', xScale(0))
        .attr('y1', 0)
        .attr('x2', xScale(0))
        .attr('y2', innerH)
        .attr('stroke', dark ? '#52525b' : '#d4d4d8')
        .attr('stroke-width', 1);

    // S&P 500 overall reference line
    if (overallCorr.r != null) {
        g.append('line')
            .attr('x1', xScale(overallCorr.r))
            .attr('y1', -5)
            .attr('x2', xScale(overallCorr.r))
            .attr('y2', innerH + 4)
            .attr('stroke', dark ? '#fbbf24' : '#d97706')
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '6,4')
            .attr('opacity', 0.85);

        g.append('text')
            .attr('x', xScale(overallCorr.r))
            .attr('y', -10)
            .attr('text-anchor', 'middle')
            .attr('fill', dark ? '#fbbf24' : '#d97706')
            .attr('font-size', '0.65rem')
            .attr('font-weight', '600')
            .text('S&P 500 r = ' + (overallCorr.r >= 0 ? '+' : '') + overallCorr.r.toFixed(2));
    }

    // Active sector for highlighting
    var activeSector = window._activeSector || null;

    // Bars
    sectorData.forEach(function(d, i) {
        var y = i * (barH + gap);
        var isActive = activeSector && d.sector === activeSector;
        var sColor = SECTOR_COLORS[d.sector] || '#94a3b8';

        // Sector label (left)
        g.append('text')
            .attr('x', -8)
            .attr('y', y + barH / 2 + 4)
            .attr('text-anchor', 'end')
            .attr('fill', isActive ? sColor : (dark ? '#d4d4d8' : '#3f3f46'))
            .attr('font-size', '0.72rem')
            .attr('font-weight', isActive ? '700' : '500')
            .text(d.sector);

        if (d.insufficient || d.r == null) {
            // Gray bar for insufficient data
            g.append('rect')
                .attr('x', xScale(0) - 1)
                .attr('y', y + 2)
                .attr('width', 3)
                .attr('height', barH - 4)
                .attr('rx', 2)
                .attr('fill', dark ? '#3f3f46' : '#e4e4e7');

            g.append('text')
                .attr('x', xScale(0) + 10)
                .attr('y', y + barH / 2 + 4)
                .attr('fill', dark ? '#71717a' : '#a1a1aa')
                .attr('font-size', '0.68rem')
                .attr('font-style', 'italic')
                .text('n/a (n=' + d.n + ')');
            return;
        }

        var barX, barW;
        if (d.r >= 0) {
            barX = xScale(0);
            barW = xScale(d.r) - xScale(0);
        } else {
            barX = xScale(d.r);
            barW = xScale(0) - xScale(d.r);
        }
        barW = Math.max(barW, 2);

        var barRect = g.append('rect')
            .attr('x', barX)
            .attr('y', y + 2)
            .attr('width', barW)
            .attr('height', barH - 4)
            .attr('rx', 3)
            .attr('fill', barColor(d.r))
            .attr('opacity', d.insufficient ? 0.35 : 0.85)
            .attr('cursor', 'pointer');

        // Active sector highlight border
        if (isActive) {
            barRect.attr('stroke', sColor).attr('stroke-width', 2).attr('opacity', 1);
        }

        // Significance stars
        var stars = _sigStars(d.p);

        // r value + stars + n at end of bar
        var endX = d.r >= 0 ? xScale(d.r) + 6 : xScale(d.r) - 6;
        var anchor = d.r >= 0 ? 'start' : 'end';

        var rLabel = (d.r >= 0 ? '+' : '') + d.r.toFixed(2);
        if (stars) rLabel += ' ' + stars;
        rLabel += '  n=' + d.n;

        // Delta vs S&P 500
        var delta = overallCorr.r != null ? d.r - overallCorr.r : null;

        g.append('text')
            .attr('x', endX)
            .attr('y', y + barH / 2 + 4)
            .attr('text-anchor', anchor)
            .attr('fill', dark ? '#e4e4e7' : '#27272a')
            .attr('font-size', '0.68rem')
            .attr('font-weight', '500')
            .html(function() {
                var txt = (d.r >= 0 ? '+' : '') + d.r.toFixed(2);
                if (stars) txt += ' <tspan fill="' + (dark ? '#fbbf24' : '#d97706') + '" font-weight="700">' + stars + '</tspan>';
                txt += ' <tspan fill="' + (dark ? '#71717a' : '#a1a1aa') + '" font-size="0.6rem">n=' + d.n + '</tspan>';
                return txt;
            });

        // Tooltip on hover
        (function(datum, barEl) {
            var strength = Math.abs(datum.r) >= 0.7 ? 'Strong' : Math.abs(datum.r) >= 0.4 ? 'Moderate' : Math.abs(datum.r) >= 0.2 ? 'Weak' : 'Very weak';
            var direction = datum.r > 0 ? ' positive' : datum.r < 0 ? ' negative' : '';
            var sigText = _sigLabel(datum.p);
            var sigStars = _sigStars(datum.p);

            barEl.on('mouseenter', function(event) {
                d3.select(this).attr('opacity', 1).attr('stroke', sColor).attr('stroke-width', 2);
                var html = '<div class="ct-title">' + datum.sector + '</div>' +
                    '<div class="ct-row"><span class="ct-label">' + mX.short + ' × ' + mY.short + '</span></div>' +
                    '<div class="ct-row"><span class="ct-label">Pearson r</span><span class="ct-val">' + (datum.r >= 0 ? '+' : '') + datum.r.toFixed(3) + (sigStars ? ' <span style="color:#fbbf24;font-weight:700">' + sigStars + '</span>' : '') + '</span></div>' +
                    '<div class="ct-row"><span class="ct-label">Significance</span><span class="ct-val">' + sigText + '</span></div>' +
                    '<div class="ct-row"><span class="ct-label">Sample size</span><span class="ct-val">n = ' + datum.n + '</span></div>' +
                    '<div class="ct-row"><span class="ct-label">Strength</span><span class="ct-val">' + strength + direction + '</span></div>';
                if (delta != null) {
                    var dSign = (datum.r - overallCorr.r) >= 0 ? '+' : '';
                    var dVal = datum.r - overallCorr.r;
                    var dColor = Math.abs(dVal) >= 0.15 ? (dVal > 0 ? '#34d399' : '#f87171') : (Math.abs(dVal) >= 0.05 ? '#fbbf24' : '#94a3b8');
                    html += '<div class="ct-row" style="border-top:1px solid ' + (dark ? '#3f3f46' : '#e4e4e7') + ';margin-top:4px;padding-top:4px;"><span class="ct-label">S&P 500 r</span><span class="ct-val">' + (overallCorr.r >= 0 ? '+' : '') + overallCorr.r.toFixed(3) + '</span></div>' +
                        '<div class="ct-row"><span class="ct-label">Δ vs S&P</span><span class="ct-val" style="color:' + dColor + '">' + dSign + dVal.toFixed(3) + '</span></div>';
                }
                html += '<div style="margin-top:6px;font-size:0.65rem;color:#a1a1aa;text-align:center;">Click to filter table to this sector</div>';
                showChartTooltip(event, html);
            })
            .on('mousemove', function(event) { positionChartTooltip(event); })
            .on('mouseleave', function() {
                if (!isActive) d3.select(this).attr('opacity', 0.85).attr('stroke', 'none');
                else d3.select(this).attr('opacity', 1);
                hideChartTooltip();
            })
            .on('click', function() {
                hideChartTooltip();
                // Apply sector filter (same as sector chip click)
                if (typeof window.filterBySectorFromBar === 'function') {
                    window.filterBySectorFromBar(datum.sector);
                }
            });
        })(d, barRect);
    });
}


/* === Pay Quartile Composition Chart === */
function _extractCeoRows(companyPool) {
    var rows = [];
    companyPool.forEach(function(c) {
        var execs = c.executives;
        if (!execs || execs.length === 0) return;
        var maxYear = 0;
        execs.forEach(function(e) { if (e.year > maxYear) maxYear = e.year; });
        var latestExecs = execs.filter(function(e) { return e.year === maxYear; });
        var ceo = null;
        for (var i = 0; i < latestExecs.length; i++) {
            var e = latestExecs[i];
            if (e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title))) {
                ceo = e; break;
            }
        }
        if (!ceo) {
            var best = null;
            latestExecs.forEach(function(e) { if (!best || (e.total || 0) > (best.total || 0)) best = e; });
            ceo = best;
        }
        if (!ceo || !ceo.total || ceo.total <= 0) return;
        var hasParts = (ceo.salary || 0) + (ceo.stock_awards || 0) + (ceo.option_awards || 0) +
            (ceo.non_equity_incentive || 0) + (ceo.bonus || 0) + (ceo.pension_nqdc || 0) + (ceo.all_other || 0);
        if (hasParts <= 0) return;
        rows.push({
            ticker: c.ticker, company: c.company_name, total: ceo.total,
            salary: ceo.salary || 0, stock_awards: ceo.stock_awards || 0, option_awards: ceo.option_awards || 0,
            non_equity_incentive: ceo.non_equity_incentive || 0, bonus: ceo.bonus || 0,
            pension_nqdc: ceo.pension_nqdc || 0, all_other: ceo.all_other || 0
        });
    });
    return rows;
}

function _buildQuartiles(ceoRows) {
    ceoRows.sort(function(a, b) { return b.total - a.total; });
    var qSize = Math.floor(ceoRows.length / 4);
    var componentKeys = ['salary', 'stock_awards', 'option_awards', 'non_equity_incentive', 'bonus', 'pension_nqdc', 'all_other'];
    var quartiles = [
        { label: 'Q4', desc: 'Top 25%', rows: ceoRows.slice(0, qSize) },
        { label: 'Q3', desc: 'Upper-Mid', rows: ceoRows.slice(qSize, qSize * 2) },
        { label: 'Q2', desc: 'Lower-Mid', rows: ceoRows.slice(qSize * 2, qSize * 3) },
        { label: 'Q1', desc: 'Bottom 25%', rows: ceoRows.slice(qSize * 3) }
    ];
    quartiles.forEach(function(q) {
        var avgPcts = {};
        componentKeys.forEach(function(k) { avgPcts[k] = 0; });
        var avgTotal = 0;
        q.rows.forEach(function(r) {
            var rowTotal = 0;
            componentKeys.forEach(function(k) { rowTotal += r[k]; });
            if (rowTotal <= 0) return;
            componentKeys.forEach(function(k) { avgPcts[k] += (r[k] / rowTotal) * 100; });
            avgTotal += r.total;
        });
        var n = q.rows.length;
        componentKeys.forEach(function(k) { avgPcts[k] /= n; });
        q.avgPcts = avgPcts;
        q.avgTotal = avgTotal / n;
        var sortedTotals = q.rows.map(function(r) { return r.total; }).sort(function(a, b) { return a - b; });
        var mid = Math.floor(sortedTotals.length / 2);
        q.medianTotal = sortedTotals.length % 2 === 0 ? (sortedTotals[mid - 1] + sortedTotals[mid]) / 2 : sortedTotals[mid];
        q.minComp = sortedTotals[0];
        q.maxComp = sortedTotals[sortedTotals.length - 1];
    });
    return quartiles;
}

function drawQuartileComposition(companies) {
    var container = document.getElementById('quartile-comp-chart');
    if (!container) return;
    container.innerHTML = '';

    var sector = window._activeSector || null;
    var pool = sector
        ? companies.filter(function(c) { return c.sector === sector; })
        : companies;

    var ceoRows = _extractCeoRows(pool);

    if (ceoRows.length < 8) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">' +
            (sector ? 'Not enough ' + sector + ' companies with component data (need \u22658, have ' + ceoRows.length + ')' : 'Insufficient component data') + '</p>';
        return;
    }

    var quartiles = _buildQuartiles(ceoRows);

    // Compute S&P 500 overall quartiles when sector filter is active (for ghost bars)
    var overallQuartiles = null;
    if (sector) {
        var overallRows = _extractCeoRows(companies);
        if (overallRows.length >= 8) {
            overallQuartiles = _buildQuartiles(overallRows);
        }
    }

    var componentKeys = ['salary', 'stock_awards', 'option_awards', 'non_equity_incentive', 'bonus', 'pension_nqdc', 'all_other'];
    var componentLabels = {
        salary: 'Base Salary', stock_awards: 'Stock Awards', option_awards: 'Option Awards',
        non_equity_incentive: 'Non-Equity Incentive', bonus: 'Bonus', pension_nqdc: 'Pension/NQDC', all_other: 'All Other'
    };
    var componentColors = {
        salary: '#06d6a0', stock_awards: '#00b4d8', option_awards: '#0096c7',
        non_equity_incentive: '#a78bfa', bonus: '#8b5cf6', pension_nqdc: '#fb923c', all_other: '#ffd166'
    };

    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
    var textColor = dark ? '#e4e4e7' : '#1a1a2e';
    var mutedColor = dark ? '#6b7280' : '#9ca3af';
    var ghostStroke = dark ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.25)';
    var ghostFill = dark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)';

    var margin = { top: 16, right: 90, bottom: 24, left: 200 };
    var cw = container.clientWidth;
    var w = cw - margin.left - margin.right;
    if (w < 200) w = 200;
    var barH = sector && overallQuartiles ? 42 : 36; // taller bars when ghost bars shown
    var barGap = 14;
    var h = quartiles.length * (barH + barGap) - barGap;

    var svg = d3.select(container).append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom)
        .append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleLinear().domain([0, 100]).range([0, w]);

    // Draw bars
    quartiles.forEach(function(q, qi) {
        var by = qi * (barH + barGap);
        var cumX = 0;
        var oq = overallQuartiles ? overallQuartiles[qi] : null;

        // --- Ghost bars (S&P 500 baseline) behind sector bars ---
        if (oq) {
            var ghostCumX = 0;
            var ghostBarH = barH;
            var ghostBarY = by;
            componentKeys.forEach(function(key) {
                var oPct = oq.avgPcts[key];
                if (oPct < 0.3) return;
                var gW = x(oPct);
                svg.append('rect')
                    .attr('x', ghostCumX)
                    .attr('y', ghostBarY)
                    .attr('width', gW)
                    .attr('height', ghostBarH)
                    .attr('fill', ghostFill)
                    .attr('stroke', ghostStroke)
                    .attr('stroke-width', 1.5)
                    .attr('stroke-dasharray', '4,3')
                    .attr('rx', ghostCumX === 0 ? 4 : 0)
                    .attr('ry', ghostCumX === 0 ? 4 : 0)
                    .attr('pointer-events', 'none');
                ghostCumX += gW;
            });
        }

        // Quartile label
        var medStr = fmtCurr(q.medianTotal);
        svg.append('text')
            .attr('x', -8)
            .attr('y', by + barH / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .attr('fill', textColor)
            .attr('font-size', '0.78rem')
            .attr('font-weight', '600')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(q.label + ' \u2014 ' + q.desc + ' (median ' + medStr + ')');

        // Stacked segments (with animated entry)
        var segDelay = qi * 200; // stagger per quartile
        componentKeys.forEach(function(key, ki) {
            var pct = q.avgPcts[key];
            if (pct < 0.3) return;
            var segW = x(pct);
            var segG = svg.append('g')
                .attr('class', 'quartile-seg')
                .style('cursor', 'pointer');

            segG.append('rect')
                .attr('x', cumX)
                .attr('y', by)
                .attr('width', 0) // start at 0 for animation
                .attr('height', barH)
                .attr('fill', componentColors[key])
                .attr('opacity', 0.85)
                .attr('rx', cumX === 0 ? 4 : 0)
                .attr('ry', cumX === 0 ? 4 : 0)
                .transition()
                .duration(400)
                .delay(segDelay + ki * 40)
                .ease(d3.easeCubicOut)
                .attr('width', segW);

            // Percentage label (if >=8%) — fade in after bar grows
            if (pct >= 8 && segW > 30) {
                svg.append('text')
                    .attr('x', cumX + segW / 2)
                    .attr('y', by + barH / 2)
                    .attr('dy', '0.35em')
                    .attr('text-anchor', 'middle')
                    .attr('fill', '#fff')
                    .attr('font-size', '0.68rem')
                    .attr('font-weight', '600')
                    .attr('font-family', 'Inter, system-ui, sans-serif')
                    .attr('pointer-events', 'none')
                    .attr('opacity', 0)
                    .transition()
                    .duration(200)
                    .delay(segDelay + ki * 40 + 300)
                    .attr('opacity', 1)
                    .text(Math.round(pct) + '%');
            }

            // Delta indicator vs S&P 500 (small triangle + delta text above segment) — fade in with bar
            if (oq) {
                var oPct = oq.avgPcts[key] || 0;
                var delta = pct - oPct;
                if (Math.abs(delta) >= 2 && segW > 22) {
                    var deltaColor = Math.abs(delta) >= 5
                        ? (delta > 0 ? '#06d6a0' : '#ef476f')
                        : mutedColor;
                    var deltaSign = delta > 0 ? '\u25B2' : '\u25BC';
                    svg.append('text')
                        .attr('x', cumX + segW / 2)
                        .attr('y', by - 3)
                        .attr('text-anchor', 'middle')
                        .attr('fill', deltaColor)
                        .attr('font-size', '0.52rem')
                        .attr('font-weight', '600')
                        .attr('font-family', 'Inter, system-ui, sans-serif')
                        .attr('pointer-events', 'none')
                        .attr('opacity', 0)
                        .transition()
                        .duration(200)
                        .delay(segDelay + ki * 40 + 300)
                        .attr('opacity', 1)
                        .text(deltaSign + (delta > 0 ? '+' : '') + Math.round(delta) + 'pp');
                }
            }

            // Tooltip — with S&P 500 comparison when sector active
            (function(segKey, segPct, quartileData, segCumX, segSegW, overallQ) {
                segG.on('mouseover', function(event) {
                    d3.select(this).select('rect').attr('opacity', 1);
                    var avgVal = quartileData.avgTotal * segPct / 100;
                    var html = '<div class="ct-title">' + componentLabels[segKey] + '</div>' +
                        '<div class="ct-row"><span class="ct-label">' + (sector || 'S&P 500') + ' Avg Share</span><span class="ct-val">' + segPct.toFixed(1) + '%</span></div>' +
                        '<div class="ct-row"><span class="ct-label">Avg Value</span><span class="ct-val">' + fmtCurr(avgVal) + '</span></div>';
                    if (overallQ) {
                        var oVal = overallQ.avgPcts[segKey] || 0;
                        var dv = segPct - oVal;
                        var dvColor = Math.abs(dv) >= 5 ? (dv > 0 ? '#06d6a0' : '#ef476f') : '#a1a1aa';
                        html += '<div style="border-top:1px solid rgba(161,161,170,0.2);margin:4px 0;"></div>' +
                            '<div class="ct-row"><span class="ct-label">S&P 500 Avg</span><span class="ct-val">' + oVal.toFixed(1) + '%</span></div>' +
                            '<div class="ct-row"><span class="ct-label">Sector \u0394</span><span class="ct-val" style="color:' + dvColor + '">' +
                            (dv > 0 ? '+' : '') + dv.toFixed(1) + 'pp</span></div>';
                    }
                    html += '<div class="ct-row ct-sub"><span class="ct-label">' + quartileData.label + ' (' + quartileData.desc + ') \u2014 ' + quartileData.rows.length + ' CEOs</span></div>';
                    showChartTooltip(event, html);
                })
                .on('mousemove', function(event) { positionChartTooltip(event); })
                .on('mouseout', function() {
                    d3.select(this).select('rect').attr('opacity', 0.85);
                    hideChartTooltip();
                });
            })(key, pct, q, cumX, segW, oq);

            // Click to filter table to this quartile range
            (function(quartileData) {
                segG.on('click', function() {
                    if (window.filterByDistribution) {
                        window.filterByDistribution(
                            sector || null,
                            quartileData.minComp,
                            quartileData.maxComp,
                            quartileData.label + ' (' + quartileData.desc + ')'
                        );
                    }
                });
            })(q);

            cumX += segW;
        });

        // Total label on right
        svg.append('text')
            .attr('x', w + 6)
            .attr('y', by + barH / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'start')
            .attr('fill', mutedColor)
            .attr('font-size', '0.72rem')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(fmtCurr(q.avgTotal));
    });

    // Legend below bars — wrapping layout for narrow screens
    var legendY = h + 8;
    var lx = 0;
    var maxLegendW = w + margin.right;
    var legendRow = 0;
    componentKeys.forEach(function(key) {
        var hasData = quartiles.some(function(q) { return q.avgPcts[key] > 0.5; });
        if (!hasData) return;
        var labelText = componentLabels[key];
        var itemW = labelText.length * 5.5 + 24;
        // Wrap to next line if overflowing
        if (lx + itemW > maxLegendW && lx > 0) {
            lx = 0;
            legendRow++;
        }
        var ly = legendY + legendRow * 18;
        svg.append('rect')
            .attr('x', lx).attr('y', ly)
            .attr('width', 10).attr('height', 10)
            .attr('fill', componentColors[key])
            .attr('opacity', 0.85)
            .attr('rx', 2);
        svg.append('text')
            .attr('x', lx + 14).attr('y', ly + 8)
            .attr('fill', mutedColor)
            .attr('font-size', '0.62rem')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(labelText);
        lx += itemW;
    });

    // Add S&P 500 ghost bar legend entry when sector active
    if (overallQuartiles) {
        var ghostLabelText = 'S&P 500 baseline';
        var ghostItemW = ghostLabelText.length * 5.5 + 24;
        if (lx + ghostItemW > maxLegendW && lx > 0) {
            lx = 0;
            legendRow++;
        }
        var gly = legendY + legendRow * 18;
        svg.append('rect')
            .attr('x', lx).attr('y', gly)
            .attr('width', 10).attr('height', 10)
            .attr('fill', ghostFill)
            .attr('stroke', ghostStroke)
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '3,2')
            .attr('rx', 2);
        svg.append('text')
            .attr('x', lx + 14).attr('y', gly + 8)
            .attr('fill', mutedColor)
            .attr('font-size', '0.62rem')
            .attr('font-style', 'italic')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(ghostLabelText);
    }

    // Resize SVG to accommodate legend rows
    if (legendRow > 0) {
        var svgEl = container.querySelector('svg');
        if (svgEl) {
            var newH = h + margin.top + margin.bottom + legendRow * 18;
            svgEl.setAttribute('height', newH);
        }
    }

    // Narrative annotation pill
    var q4Equity = (quartiles[0].avgPcts.stock_awards || 0) + (quartiles[0].avgPcts.option_awards || 0);
    var q1Equity = (quartiles[3].avgPcts.stock_awards || 0) + (quartiles[3].avgPcts.option_awards || 0);
    var gap = Math.abs(q4Equity - q1Equity);

    var narrativeText;
    if (sector && overallQuartiles) {
        // Sector vs S&P 500 comparative narrative
        var oQ4Equity = (overallQuartiles[0].avgPcts.stock_awards || 0) + (overallQuartiles[0].avgPcts.option_awards || 0);
        var oQ1Equity = (overallQuartiles[3].avgPcts.stock_awards || 0) + (overallQuartiles[3].avgPcts.option_awards || 0);
        var q4Delta = q4Equity - oQ4Equity;
        var q1Delta = q1Equity - oQ1Equity;

        // Find the most divergent component across Q4
        var biggestDivKey = null, biggestDivVal = 0;
        componentKeys.forEach(function(k) {
            var d = Math.abs((quartiles[0].avgPcts[k] || 0) - (overallQuartiles[0].avgPcts[k] || 0));
            if (d > biggestDivVal) { biggestDivVal = d; biggestDivKey = k; }
        });

        narrativeText = sector + ' Q4 CEOs receive ' + Math.round(q4Equity) + '% from equity vs S&P 500 Q4 average of ' +
            Math.round(oQ4Equity) + '% (' + (q4Delta >= 0 ? '+' : '') + Math.round(q4Delta) + 'pp). ';
        narrativeText += 'Q1: ' + Math.round(q1Equity) + '% vs ' + Math.round(oQ1Equity) + '% S&P 500 (' +
            (q1Delta >= 0 ? '+' : '') + Math.round(q1Delta) + 'pp). ';
        if (biggestDivKey && biggestDivVal >= 5) {
            narrativeText += 'Largest structural difference: ' + componentLabels[biggestDivKey] +
                ' (' + (q4Delta >= 0 ? '+' : '') + Math.round(biggestDivVal) + 'pp in Q4 vs S&P 500). ';
        }
        narrativeText += 'Dashed outlines show S&P 500 baseline.';
    } else {
        narrativeText = 'Equity dominance grows with pay level: ' + quartiles[0].label + ' CEOs receive ' +
            Math.round(q4Equity) + '% of pay from stock/options vs ' + Math.round(q1Equity) + '% for ' +
            quartiles[3].label + ' \u2014 a ' + Math.round(gap) + ' percentage point gap.';
    }

    // Remove existing narrative if any
    var existingNarr = container.querySelector('.quartile-narrative');
    if (existingNarr) existingNarr.remove();
    var narrDiv = document.createElement('div');
    narrDiv.className = 'quartile-narrative';
    narrDiv.textContent = narrativeText;
    container.appendChild(narrDiv);

    // Update description for sector context
    var descEl = document.getElementById('quartile-comp-desc');
    if (descEl) {
        descEl.textContent = sector
            ? 'How ' + sector + ' CEO compensation composition shifts by pay level vs S&P 500 baseline \u2014 ' + pool.length + ' companies, ' + ceoRows.length + ' with component data. Dashed outlines = S&P 500 overall.'
            : 'How compensation composition shifts as pay levels rise \u2014 from salary-heavy in the bottom quartile to equity-dominant at the top. Computed from CEO-level DEF 14A data.';
    }
}

/* ========================================================================
   Governance Score Distribution Chart
   ======================================================================== */
function drawGovDistChart(companies) {
    var container = document.getElementById('gov-dist-chart');
    if (!container) return;
    container.innerHTML = '';

    var withGov = companies.filter(function(c) { return c._govScore != null; });
    if (withGov.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No governance score data available</p>';
        return;
    }

    var buckets = [
        { min: 0, max: 20, label: '0–20', grade: 'F', color: '#ef476f' },
        { min: 20, max: 35, label: '20–35', grade: 'F/D', color: '#f77f7f' },
        { min: 35, max: 50, label: '35–50', grade: 'D', color: '#fb923c' },
        { min: 50, max: 65, label: '50–65', grade: 'C', color: '#fbbf24' },
        { min: 65, max: 80, label: '65–80', grade: 'B', color: '#4ade80' },
        { min: 80, max: 100.1, label: '80–100', grade: 'A', color: '#06d6a0' }
    ];

    buckets.forEach(function(b) {
        b.companies = withGov.filter(function(c) {
            return c._govScore >= b.min && c._govScore < b.max;
        });
        b.count = b.companies.length;
        b.companies.sort(function(a, bb) { return bb._govScore - a._govScore; });
    });

    var activeBuckets = buckets.filter(function(b) { return b.count > 0; });
    var maxCount = d3.max(activeBuckets, function(b) { return b.count; });

    // Median / mean
    var govVals = withGov.map(function(c) { return c._govScore; }).sort(function(a, b) { return a - b; });
    var medianGov = govVals[Math.floor(govVals.length / 2)];
    var meanGov = govVals.reduce(function(s, v) { return s + v; }, 0) / govVals.length;

    // Grade counts
    var gradeCounts = { A: 0, B: 0, C: 0, D: 0, F: 0 };
    withGov.forEach(function(c) { if (c._govGrade) gradeCounts[c._govGrade]++; });

    var cw = container.clientWidth || 700;
    var margin = { top: 30, right: 30, bottom: 65, left: 50 };
    var width = cw - margin.left - margin.right;
    var height = 320 - margin.top - margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', cw)
        .attr('height', 340)
        .attr('role', 'img')
        .attr('aria-label', 'Governance score distribution histogram');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleBand()
        .domain(activeBuckets.map(function(b) { return b.label; }))
        .range([0, width])
        .padding(0.15);

    var y = d3.scaleLinear()
        .domain([0, maxCount * 1.15])
        .range([height, 0]);

    // Axes
    g.append('g')
        .attr('transform', 'translate(0,' + height + ')')
        .call(d3.axisBottom(x))
        .selectAll('text')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px');

    g.append('g')
        .call(d3.axisLeft(y).ticks(5))
        .selectAll('text')
        .style('fill', chartStrokeColor());

    // Grade labels under x-axis
    g.selectAll('.gov-grade-label')
        .data(activeBuckets)
        .enter()
        .append('text')
        .attr('x', function(b) { return x(b.label) + x.bandwidth() / 2; })
        .attr('y', height + 35)
        .attr('text-anchor', 'middle')
        .style('fill', function(b) { return b.color; })
        .style('font-size', '10px')
        .style('font-weight', '600')
        .style('opacity', 0.9)
        .text(function(b) { return b.grade; });

    // Bars
    g.selectAll('.gov-bar')
        .data(activeBuckets)
        .enter()
        .append('rect')
        .attr('class', 'gov-bar')
        .attr('x', function(b) { return x(b.label); })
        .attr('y', function(b) { return y(b.count); })
        .attr('width', x.bandwidth())
        .attr('height', function(b) { return height - y(b.count); })
        .attr('fill', function(b) { return b.color; })
        .attr('rx', 3)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, b) {
            var compList = b.companies.slice(0, 8).map(function(c) {
                return c.ticker + ' ' + c._govScore + ' (' + c._govGrade + ')';
            }).join('<br>');
            if (b.count > 8) compList += '<br>...+' + (b.count - 8) + ' more';
            showChartTooltip(event, '<strong>Score ' + b.label + ' (Grade ' + b.grade + ')</strong><br>' +
                b.count + ' companies<br><br>' + compList);
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function() { hideChartTooltip(); })
        .on('click', function(event, b) {
            if (window.filterByGovGrade) {
                // Use the grade letter of the first company in this bucket
                var grade = b.companies.length > 0 ? b.companies[0]._govGrade : 'C';
                window.filterByGovGrade(grade, b.min, b.max);
            }
        });

    // Count labels on top of bars
    g.selectAll('.gov-count-label')
        .data(activeBuckets)
        .enter()
        .append('text')
        .attr('x', function(b) { return x(b.label) + x.bandwidth() / 2; })
        .attr('y', function(b) { return y(b.count) - 5; })
        .attr('text-anchor', 'middle')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px')
        .style('font-weight', '600')
        .text(function(b) { return b.count; });

    // Median line
    var medianBucket = activeBuckets.find(function(b) { return medianGov >= b.min && medianGov < b.max; });
    if (medianBucket) {
        var medianXPos = x(medianBucket.label) + x.bandwidth() * ((medianGov - medianBucket.min) / (medianBucket.max - medianBucket.min));
        g.append('line')
            .attr('x1', medianXPos).attr('x2', medianXPos)
            .attr('y1', 0).attr('y2', height)
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '6,3')
            .attr('opacity', 0.8);
        g.append('text')
            .attr('x', medianXPos + 4)
            .attr('y', 12)
            .style('fill', '#fff')
            .style('font-size', '11px')
            .style('font-weight', '600')
            .text('Median: ' + medianGov);
    }

    // Stats annotation with grade breakdown
    var statsText = withGov.length + ' companies | Median ' + medianGov + ' | Mean ' + meanGov.toFixed(1);
    statsText += ' | A:' + gradeCounts.A + ' B:' + gradeCounts.B + ' C:' + gradeCounts.C + ' D:' + gradeCounts.D + ' F:' + gradeCounts.F;
    svg.append('text')
        .attr('x', cw / 2)
        .attr('y', 335)
        .attr('text-anchor', 'middle')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px')
        .style('opacity', 0.7)
        .text(statsText);
}

/* ========================================================================
   Sector Governance Score Chart — horizontal bar chart showing median 
   governance score per sector with grade-colored bars
   ======================================================================== */
function drawSectorGovChart(companies) {
    var container = document.getElementById('sector-gov-chart');
    if (!container) return;
    container.innerHTML = '';

    var withGov = companies.filter(function(c) { return c._govScore != null && c.sector; });
    if (withGov.length < 20) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient governance data</p>';
        return;
    }

    // Compute per-sector median governance score
    var sectorMap = {};
    withGov.forEach(function(c) {
        if (!sectorMap[c.sector]) sectorMap[c.sector] = [];
        sectorMap[c.sector].push(c._govScore);
    });

    var sectorData = [];
    Object.keys(sectorMap).forEach(function(sector) {
        var scores = sectorMap[sector].sort(function(a, b) { return a - b; });
        var median = scores[Math.floor(scores.length / 2)];
        var mean = scores.reduce(function(s, v) { return s + v; }, 0) / scores.length;
        var min = scores[0];
        var max = scores[scores.length - 1];
        var p25 = scores[Math.floor(scores.length * 0.25)];
        var p75 = scores[Math.floor(scores.length * 0.75)];
        sectorData.push({
            sector: sector,
            median: median,
            mean: Math.round(mean),
            min: min,
            max: max,
            p25: p25,
            p75: p75,
            count: scores.length,
            grade: median >= 80 ? 'A' : median >= 65 ? 'B' : median >= 50 ? 'C' : median >= 35 ? 'D' : 'F'
        });
    });

    sectorData.sort(function(a, b) { return b.median - a.median; });

    var cw = container.clientWidth || 700;
    var barHeight = 28;
    var margin = { top: 20, right: 80, bottom: 30, left: 150 };
    var width = cw - margin.left - margin.right;
    var chartHeight = sectorData.length * (barHeight + 6);
    var totalHeight = chartHeight + margin.top + margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', cw)
        .attr('height', totalHeight)
        .attr('role', 'img')
        .attr('aria-label', 'Governance score by sector');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleLinear()
        .domain([0, 100])
        .range([0, width]);

    var y = d3.scaleBand()
        .domain(sectorData.map(function(d) { return d.sector; }))
        .range([0, chartHeight])
        .padding(0.15);

    // X axis at bottom
    g.append('g')
        .attr('transform', 'translate(0,' + chartHeight + ')')
        .call(d3.axisBottom(x).ticks(5).tickFormat(function(v) { return v; }))
        .selectAll('text')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px');

    // Y axis (sector names)
    g.append('g')
        .call(d3.axisLeft(y))
        .selectAll('text')
        .style('fill', chartStrokeColor())
        .style('font-size', '11px')
        .style('cursor', 'pointer')
        .on('click', function(event, sector) {
            if (window.filterBySector) window.filterBySector(sector);
        });

    function gradeColor(score) {
        if (score >= 80) return '#06d6a0';
        if (score >= 65) return '#4ade80';
        if (score >= 50) return '#fbbf24';
        if (score >= 35) return '#fb923c';
        return '#ef476f';
    }

    // IQR range bars (p25-p75)
    g.selectAll('.gov-iqr')
        .data(sectorData)
        .enter()
        .append('rect')
        .attr('class', 'gov-iqr')
        .attr('x', function(d) { return x(d.p25); })
        .attr('y', function(d) { return y(d.sector) + y.bandwidth() * 0.2; })
        .attr('width', function(d) { return Math.max(0, x(d.p75) - x(d.p25)); })
        .attr('height', y.bandwidth() * 0.6)
        .attr('fill', function(d) { return gradeColor(d.median); })
        .attr('opacity', 0.25)
        .attr('rx', 2);

    // Median bars
    g.selectAll('.gov-sector-bar')
        .data(sectorData)
        .enter()
        .append('rect')
        .attr('class', 'gov-sector-bar')
        .attr('x', 0)
        .attr('y', function(d) { return y(d.sector) + y.bandwidth() * 0.15; })
        .attr('width', function(d) { return x(d.median); })
        .attr('height', y.bandwidth() * 0.7)
        .attr('fill', function(d) { return gradeColor(d.median); })
        .attr('rx', 3)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            showChartTooltip(event,
                '<strong>' + d.sector + '</strong><br>' +
                'Median Gov Score: <strong>' + d.median + '</strong> (Grade ' + d.grade + ')<br>' +
                'Mean: ' + d.mean + ' | Range: ' + d.min + '–' + d.max + '<br>' +
                'IQR: ' + d.p25 + '–' + d.p75 + '<br>' +
                d.count + ' companies');
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function() { hideChartTooltip(); })
        .on('click', function(event, d) {
            if (window.filterBySector) window.filterBySector(d.sector);
        });

    // Score + grade labels at end of bars
    g.selectAll('.gov-sector-label')
        .data(sectorData)
        .enter()
        .append('text')
        .attr('x', function(d) { return x(d.median) + 6; })
        .attr('y', function(d) { return y(d.sector) + y.bandwidth() / 2 + 4; })
        .style('fill', chartStrokeColor())
        .style('font-size', '11px')
        .style('font-weight', '600')
        .text(function(d) { return d.median + ' (' + d.grade + ')'; });

    // S&P 500 overall median line
    var allScores = withGov.map(function(c) { return c._govScore; }).sort(function(a, b) { return a - b; });
    var sp500Median = allScores[Math.floor(allScores.length / 2)];

    g.append('line')
        .attr('x1', x(sp500Median)).attr('x2', x(sp500Median))
        .attr('y1', -5).attr('y2', chartHeight + 5)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '5,3')
        .attr('opacity', 0.7);

    g.append('text')
        .attr('x', x(sp500Median) + 4)
        .attr('y', -8)
        .style('fill', '#fff')
        .style('font-size', '10px')
        .style('font-weight', '600')
        .style('opacity', 0.8)
        .text('S&P 500 Median: ' + sp500Median);
}

/* ========================================================================
   Governance Quartile Composition — stacked horizontal bars showing how
   pay structure (salary, stock, options, bonus, etc.) differs across
   governance-quality quartiles (best-governed vs worst-governed).
   ======================================================================== */
function drawGovQuartileComp(companies) {
    var container = document.getElementById('gov-quartile-comp-chart');
    if (!container) return;
    container.innerHTML = '';

    // Filter to companies with both governance score and exec data
    var pool = companies.filter(function(c) {
        return c._govScore != null && c.executives && c.executives.length > 0;
    });

    var ceoRows = [];
    pool.forEach(function(c) {
        if (!c.executives || c.executives.length === 0) return;
        var allYears = [];
        c.executives.forEach(function(e) { if (allYears.indexOf(e.year) < 0) allYears.push(e.year); });
        allYears.sort(function(a, b) { return b - a; });
        var latestYear = allYears[0];
        var yearExecs = c.executives.filter(function(e) { return e.year === latestYear; });
        var ceo = yearExecs.find(function(e) {
            return e.title && (/chief executive/i.test(e.title) || /\bceo\b/i.test(e.title));
        });
        if (!ceo && yearExecs.length > 0) {
            ceo = yearExecs.slice().sort(function(a, b) { return (b.total || 0) - (a.total || 0); })[0];
        }
        if (!ceo || !ceo.total || ceo.total <= 0) return;
        ceoRows.push({
            ticker: c.ticker,
            company: c.company_name,
            govScore: c._govScore,
            govGrade: c._govGrade,
            total: ceo.total,
            salary: ceo.salary || 0,
            stock_awards: ceo.stock_awards || 0,
            option_awards: ceo.option_awards || 0,
            non_equity_incentive: ceo.non_equity_incentive || 0,
            bonus: ceo.bonus || 0,
            pension_nqdc: ceo.pension_nqdc || 0,
            all_other: ceo.all_other || 0
        });
    });

    if (ceoRows.length < 20) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient governance + compensation data</p>';
        return;
    }

    // Sort by governance score descending (best-governed first)
    ceoRows.sort(function(a, b) { return b.govScore - a.govScore; });

    var qSize = Math.floor(ceoRows.length / 4);
    var componentKeys = ['salary', 'stock_awards', 'option_awards', 'non_equity_incentive', 'bonus', 'pension_nqdc', 'all_other'];
    var componentLabels = {
        salary: 'Base Salary', stock_awards: 'Stock Awards', option_awards: 'Option Awards',
        non_equity_incentive: 'Non-Equity Incentive', bonus: 'Bonus', pension_nqdc: 'Pension/NQDC', all_other: 'All Other'
    };
    var componentColors = {
        salary: '#06d6a0', stock_awards: '#00b4d8', option_awards: '#0096c7',
        non_equity_incentive: '#a78bfa', bonus: '#8b5cf6', pension_nqdc: '#fb923c', all_other: '#ffd166'
    };

    var quartiles = [
        { label: 'Top 25%', desc: 'Best Governed', rows: ceoRows.slice(0, qSize), gradeHint: 'A/B' },
        { label: '2nd Quartile', desc: 'Above Avg', rows: ceoRows.slice(qSize, qSize * 2), gradeHint: 'B/C' },
        { label: '3rd Quartile', desc: 'Below Avg', rows: ceoRows.slice(qSize * 2, qSize * 3), gradeHint: 'C/D' },
        { label: 'Bottom 25%', desc: 'Weakest Gov', rows: ceoRows.slice(qSize * 3), gradeHint: 'D/F' }
    ];

    // Compute avg composition percentages, median total, and gov score range per quartile
    quartiles.forEach(function(q) {
        var avgPcts = {};
        componentKeys.forEach(function(k) { avgPcts[k] = 0; });
        var totalSum = 0;
        var govScores = [];
        q.rows.forEach(function(r) {
            var rowTotal = 0;
            componentKeys.forEach(function(k) { rowTotal += r[k]; });
            if (rowTotal <= 0) return;
            componentKeys.forEach(function(k) { avgPcts[k] += (r[k] / rowTotal) * 100; });
            totalSum += r.total;
            govScores.push(r.govScore);
        });
        var n = q.rows.length;
        componentKeys.forEach(function(k) { avgPcts[k] /= n; });
        q.avgPcts = avgPcts;
        q.avgTotal = totalSum / n;
        govScores.sort(function(a, b) { return a - b; });
        q.govMin = govScores[0];
        q.govMax = govScores[govScores.length - 1];
        q.govMedian = govScores[Math.floor(govScores.length / 2)];
        var sortedTotals = q.rows.map(function(r) { return r.total; }).sort(function(a, b) { return a - b; });
        var mid = Math.floor(sortedTotals.length / 2);
        q.medianTotal = sortedTotals.length % 2 === 0 ? (sortedTotals[mid - 1] + sortedTotals[mid]) / 2 : sortedTotals[mid];
    });

    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
    var textColor = dark ? '#e4e4e7' : '#1a1a2e';
    var mutedColor = dark ? '#6b7280' : '#9ca3af';

    var margin = { top: 16, right: 90, bottom: 40, left: 220 };
    var cw = container.clientWidth || 700;
    var w = cw - margin.left - margin.right;
    if (w < 200) w = 200;
    var barH = 36;
    var barGap = 14;
    var h = quartiles.length * (barH + barGap) - barGap;

    var svg = d3.select(container).append('svg')
        .attr('width', w + margin.left + margin.right)
        .attr('height', h + margin.top + margin.bottom + 30)
        .attr('role', 'img')
        .attr('aria-label', 'Pay composition by governance quartile');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var x = d3.scaleLinear().domain([0, 100]).range([0, w]);

    // Draw stacked bars per quartile
    quartiles.forEach(function(q, qi) {
        var by = qi * (barH + barGap);
        var cumX = 0;

        // Label: quartile name + gov score range + median pay
        var labelLine1 = q.label + ' \u2014 ' + q.desc;
        var labelLine2 = 'Gov ' + q.govMin + '\u2013' + q.govMax + ' | Median Pay ' + fmtCurr(q.medianTotal);

        g.append('text')
            .attr('x', -8)
            .attr('y', by + barH / 2 - 6)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .attr('fill', textColor)
            .attr('font-size', '0.78rem')
            .attr('font-weight', '600')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(labelLine1);

        g.append('text')
            .attr('x', -8)
            .attr('y', by + barH / 2 + 8)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .attr('fill', mutedColor)
            .attr('font-size', '0.65rem')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(labelLine2);

        var segDelay = qi * 200;
        componentKeys.forEach(function(key, ki) {
            var pct = q.avgPcts[key];
            if (pct < 0.3) return;
            var segW = x(pct);

            var segG = g.append('g')
                .style('cursor', 'pointer');

            segG.append('rect')
                .attr('x', cumX)
                .attr('y', by)
                .attr('width', 0)
                .attr('height', barH)
                .attr('fill', componentColors[key])
                .attr('opacity', 0.85)
                .attr('rx', cumX === 0 ? 4 : 0)
                .attr('ry', cumX === 0 ? 4 : 0)
                .transition()
                .duration(400)
                .delay(segDelay + ki * 40)
                .ease(d3.easeCubicOut)
                .attr('width', segW);

            // Percentage label inside bar
            if (pct >= 8 && segW > 30) {
                g.append('text')
                    .attr('x', cumX + segW / 2)
                    .attr('y', by + barH / 2)
                    .attr('dy', '0.35em')
                    .attr('text-anchor', 'middle')
                    .attr('fill', '#fff')
                    .attr('font-size', '0.68rem')
                    .attr('font-weight', '600')
                    .attr('font-family', 'Inter, system-ui, sans-serif')
                    .attr('pointer-events', 'none')
                    .attr('opacity', 0)
                    .transition()
                    .duration(200)
                    .delay(segDelay + ki * 40 + 300)
                    .attr('opacity', 1)
                    .text(Math.round(pct) + '%');
            }

            // Tooltip
            (function(segKey, segPct, quartileData, segCumX, segSegW) {
                segG.on('mouseover', function(event) {
                    d3.select(this).select('rect').attr('opacity', 1);
                    var avgVal = quartileData.avgTotal * segPct / 100;
                    // Compare to overall S&P 500 average for this component
                    var overallPct = 0;
                    var overallCount = 0;
                    ceoRows.forEach(function(r) {
                        var rt = 0;
                        componentKeys.forEach(function(k) { rt += r[k]; });
                        if (rt > 0) { overallPct += (r[segKey] / rt) * 100; overallCount++; }
                    });
                    overallPct = overallCount > 0 ? overallPct / overallCount : 0;
                    var delta = segPct - overallPct;
                    var deltaColor = Math.abs(delta) >= 5 ? (delta > 0 ? '#06d6a0' : '#ef476f') : '#a1a1aa';
                    var html = '<div class="ct-title">' + componentLabels[segKey] + '</div>' +
                        '<div class="ct-row"><span class="ct-label">' + quartileData.label + ' Avg Share</span><span class="ct-val">' + segPct.toFixed(1) + '%</span></div>' +
                        '<div class="ct-row"><span class="ct-label">Avg Value</span><span class="ct-val">' + fmtCurr(avgVal) + '</span></div>' +
                        '<div style="border-top:1px solid rgba(161,161,170,0.2);margin:4px 0;"></div>' +
                        '<div class="ct-row"><span class="ct-label">S&P 500 Avg</span><span class="ct-val">' + overallPct.toFixed(1) + '%</span></div>' +
                        '<div class="ct-row"><span class="ct-label">vs S&P 500</span><span class="ct-val" style="color:' + deltaColor + '">' +
                        (delta > 0 ? '+' : '') + delta.toFixed(1) + 'pp</span></div>' +
                        '<div class="ct-row ct-sub"><span class="ct-label">Gov Score ' + quartileData.govMin + '\u2013' + quartileData.govMax + ' | ' + quartileData.rows.length + ' companies</span></div>';
                    showChartTooltip(event, html);
                })
                .on('mousemove', function(event) { positionChartTooltip(event); })
                .on('mouseout', function() {
                    d3.select(this).select('rect').attr('opacity', 0.85);
                    hideChartTooltip();
                });
            })(key, pct, q, cumX, segW);

            // Click to filter by governance range
            (function(quartileData) {
                segG.on('click', function() {
                    if (window.filterByGovGrade) {
                        // Use the min/max gov scores of this quartile
                        window.filterByGovScore && window.filterByGovScore(quartileData.govMin, quartileData.govMax, quartileData.label);
                    }
                });
            })(q);

            cumX += segW;
        });

        // Total percentage at end of bar
        g.append('text')
            .attr('x', cumX + 6)
            .attr('y', by + barH / 2)
            .attr('dy', '0.35em')
            .attr('fill', mutedColor)
            .attr('font-size', '0.68rem')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(fmtCurr(q.avgTotal));
    });

    // Legend bar at bottom
    var legendY = h + 20;
    var legendX = 0;
    componentKeys.forEach(function(key) {
        var hasData = quartiles.some(function(q) { return q.avgPcts[key] > 0.5; });
        if (!hasData) return;
        g.append('rect')
            .attr('x', legendX)
            .attr('y', legendY)
            .attr('width', 12)
            .attr('height', 12)
            .attr('fill', componentColors[key])
            .attr('rx', 2);
        g.append('text')
            .attr('x', legendX + 16)
            .attr('y', legendY + 10)
            .attr('fill', textColor)
            .attr('font-size', '0.65rem')
            .attr('font-family', 'Inter, system-ui, sans-serif')
            .text(componentLabels[key]);
        legendX += componentLabels[key].length * 6.5 + 28;
    });

    // Narrative: key insight about governance and pay structure
    var topEquity = (quartiles[0].avgPcts.stock_awards || 0) + (quartiles[0].avgPcts.option_awards || 0);
    var botEquity = (quartiles[3].avgPcts.stock_awards || 0) + (quartiles[3].avgPcts.option_awards || 0);
    var topSalary = quartiles[0].avgPcts.salary || 0;
    var botSalary = quartiles[3].avgPcts.salary || 0;
    var narrativeText = '';
    if (Math.abs(topEquity - botEquity) >= 3) {
        narrativeText = 'Best-governed companies allocate ' + Math.round(topEquity) + '% equity vs ' +
            Math.round(botEquity) + '% for the weakest-governed (' + (topEquity > botEquity ? '+' : '') +
            Math.round(topEquity - botEquity) + 'pp gap).';
    }
    if (Math.abs(topSalary - botSalary) >= 3) {
        narrativeText += (narrativeText ? ' ' : '') + 'Base salary share: ' + Math.round(topSalary) + '% (best governed) vs ' +
            Math.round(botSalary) + '% (weakest).';
    }
    if (!narrativeText) {
        narrativeText = 'Pay structure is relatively consistent across governance quartiles — governance quality does not strongly predict compensation mix.';
    }

    svg.append('text')
        .attr('x', margin.left)
        .attr('y', h + margin.top + margin.bottom + 22)
        .attr('fill', mutedColor)
        .attr('font-size', '0.7rem')
        .attr('font-style', 'italic')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(narrativeText);
}


/* --- Governance vs Pay Scatter (dedicated quadrant analysis) --- */
function drawGovPayScatter(companies) {
    var container = document.getElementById('gov-pay-scatter-chart');
    if (!container) return;
    container.innerHTML = '';

    var withBoth = companies.filter(function(c) {
        return c._govScore != null && c.total_compensation > 0;
    });

    if (withBoth.length < 10) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient governance + compensation data</p>';
        return;
    }

    var sectorColors = {
        'Information Technology': '#00b4d8', 'Communication Services': '#06d6a0',
        'Consumer Discretionary': '#ef476f', 'Health Care': '#ffd166',
        'Financials': '#a78bfa', 'Consumer Staples': '#fb923c',
        'Industrials': '#94a3b8', 'Energy': '#34d399',
        'Real Estate': '#f472b6', 'Materials': '#f9a8d4', 'Utilities': '#67e8f9'
    };

    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
    var textColor = dark ? '#e4e4e7' : '#1a1a2e';
    var mutedColor = dark ? '#6b7280' : '#9ca3af';
    var gridColor = dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';

    var cw = container.clientWidth || 700;
    var margin = { top: 24, right: 30, bottom: 56, left: 70 };
    var width = cw - margin.left - margin.right;
    var height = 400 - margin.top - margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', cw)
        .attr('height', 400)
        .attr('role', 'img')
        .attr('aria-label', 'Governance score vs CEO total compensation scatter plot with quadrant analysis');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    // Compute medians for quadrant lines
    var sortedGov = withBoth.map(function(c) { return c._govScore; }).sort(function(a, b) { return a - b; });
    var sortedComp = withBoth.map(function(c) { return c.total_compensation; }).sort(function(a, b) { return a - b; });
    var medianGov = sortedGov[Math.floor(sortedGov.length / 2)];
    var medianComp = sortedComp[Math.floor(sortedComp.length / 2)];

    // Scales
    var x = d3.scaleLinear()
        .domain([Math.max(0, d3.min(withBoth, function(c) { return c._govScore; }) - 5), 100])
        .range([0, width]);

    var y = d3.scaleLog()
        .domain([d3.min(withBoth, function(c) { return c.total_compensation; }) * 0.7,
                 d3.max(withBoth, function(c) { return c.total_compensation; }) * 1.15])
        .range([height, 0]);

    // Grid
    g.append('g')
        .attr('transform', 'translate(0,' + height + ')')
        .call(d3.axisBottom(x).ticks(8))
        .selectAll('text').style('fill', textColor).style('font-size', '10px');

    g.append('g')
        .call(d3.axisLeft(y).ticks(6, '$.2s'))
        .selectAll('text').style('fill', textColor).style('font-size', '10px');

    g.selectAll('.domain').attr('stroke', textColor).attr('opacity', 0.2);
    g.selectAll('.tick line').attr('stroke', textColor).attr('opacity', 0.1);

    // Quadrant shading
    var quadrants = [
        { x1: x(medianGov), y1: 0, w: width - x(medianGov), h: y(medianComp), label: 'Well-Governed\nHigh Pay', color: '#06d6a0', align: 'end' },
        { x1: 0, y1: 0, w: x(medianGov), h: y(medianComp), label: 'Weak Governance\nHigh Pay', color: '#ef476f', align: 'start' },
        { x1: x(medianGov), y1: y(medianComp), w: width - x(medianGov), h: height - y(medianComp), label: 'Well-Governed\nModerate Pay', color: '#00b4d8', align: 'end' },
        { x1: 0, y1: y(medianComp), w: x(medianGov), h: height - y(medianComp), label: 'Weak Governance\nModerate Pay', color: '#fbbf24', align: 'start' }
    ];

    quadrants.forEach(function(q) {
        g.append('rect')
            .attr('x', q.x1).attr('y', q.y1)
            .attr('width', q.w).attr('height', q.h)
            .attr('fill', q.color).attr('opacity', 0.04);

        var lines = q.label.split('\n');
        var tx = q.align === 'end' ? q.x1 + q.w - 8 : q.x1 + 8;
        var ty = q.y1 + 16;
        lines.forEach(function(line, i) {
            g.append('text')
                .attr('x', tx).attr('y', ty + i * 14)
                .attr('text-anchor', q.align)
                .attr('fill', q.color)
                .attr('font-size', '10px')
                .attr('font-weight', '600')
                .attr('opacity', 0.5)
                .text(line);
        });
    });

    // Median lines
    g.append('line')
        .attr('x1', x(medianGov)).attr('x2', x(medianGov))
        .attr('y1', 0).attr('y2', height)
        .attr('stroke', textColor).attr('stroke-width', 1)
        .attr('stroke-dasharray', '5,4').attr('opacity', 0.3);

    g.append('line')
        .attr('x1', 0).attr('x2', width)
        .attr('y1', y(medianComp)).attr('y2', y(medianComp))
        .attr('stroke', textColor).attr('stroke-width', 1)
        .attr('stroke-dasharray', '5,4').attr('opacity', 0.3);

    // Median labels
    g.append('text')
        .attr('x', x(medianGov) + 4).attr('y', height - 4)
        .attr('fill', mutedColor).attr('font-size', '9px')
        .text('Median Gov: ' + medianGov.toFixed(0));

    g.append('text')
        .attr('x', width - 4).attr('y', y(medianComp) - 4)
        .attr('text-anchor', 'end')
        .attr('fill', mutedColor).attr('font-size', '9px')
        .text('Median Pay: ' + fmtCurr(medianComp));

    // Dots
    g.selectAll('.gps-dot')
        .data(withBoth)
        .enter()
        .append('circle')
        .attr('class', 'gps-dot')
        .attr('cx', function(c) { return x(c._govScore); })
        .attr('cy', function(c) { return y(c.total_compensation); })
        .attr('r', function(c) {
            // Size by market significance — larger for extreme outliers
            var comp = c.total_compensation;
            if (comp > 100e6) return 7;
            if (comp > 50e6) return 5.5;
            return 4;
        })
        .attr('fill', function(c) { return sectorColors[c.sector] || '#94a3b8'; })
        .attr('opacity', 0.7)
        .attr('stroke', function(c) {
            // Highlight companies in Low Gov / High Pay quadrant
            return c._govScore < medianGov && c.total_compensation > medianComp ? '#ef476f' : 'none';
        })
        .attr('stroke-width', function(c) {
            return c._govScore < medianGov && c.total_compensation > medianComp ? 1.5 : 0;
        })
        .style('cursor', 'pointer')
        .on('mouseover', function(event, c) {
            d3.select(this).attr('r', 9).attr('opacity', 1);
            var quadLabel = '';
            if (c._govScore >= medianGov && c.total_compensation >= medianComp) quadLabel = 'Well-Governed / High Pay';
            else if (c._govScore < medianGov && c.total_compensation >= medianComp) quadLabel = 'Weak Gov / High Pay ⚠️';
            else if (c._govScore >= medianGov && c.total_compensation < medianComp) quadLabel = 'Well-Governed / Moderate Pay';
            else quadLabel = 'Weak Gov / Moderate Pay';

            showChartTooltip(event,
                '<strong>' + c.ticker + '</strong> — ' + c.company_name + '<br>' +
                'CEO: ' + (c.ceo_name || '—') + '<br>' +
                'Total Comp: ' + fmtCurr(c.total_compensation) + '<br>' +
                'Governance: <strong>' + c._govScore.toFixed(0) + '</strong> (' + (c._govGrade || '—') + ')<br>' +
                'Sector: ' + (c.sector || '—') + '<br>' +
                '<span style="color:' + (quadLabel.indexOf('⚠️') >= 0 ? '#ef476f' : '#06d6a0') + '">' + quadLabel + '</span>');
        })
        .on('mousemove', function(event) { positionChartTooltip(event); })
        .on('mouseout', function(event, c) {
            var comp = c.total_compensation;
            d3.select(this).attr('r', comp > 100e6 ? 7 : comp > 50e6 ? 5.5 : 4).attr('opacity', 0.7);
            hideChartTooltip();
        })
        .on('click', function(event, c) {
            if (window.scrollToCompany) window.scrollToCompany(c.ticker);
        });

    // Label notable outliers — high pay + low governance
    var outliers = withBoth.filter(function(c) {
        return c._govScore < medianGov - 10 && c.total_compensation > medianComp * 3;
    }).sort(function(a, b) { return b.total_compensation - a.total_compensation; }).slice(0, 6);

    outliers.forEach(function(c) {
        g.append('text')
            .attr('x', x(c._govScore) + 10)
            .attr('y', y(c.total_compensation) + 4)
            .attr('fill', '#ef476f')
            .attr('font-size', '9px')
            .attr('font-weight', '600')
            .text(c.ticker);
    });

    // Also label top-right quadrant leaders
    var topRight = withBoth.filter(function(c) {
        return c._govScore > medianGov + 10 && c.total_compensation > medianComp * 3;
    }).sort(function(a, b) { return b.total_compensation - a.total_compensation; }).slice(0, 4);

    topRight.forEach(function(c) {
        g.append('text')
            .attr('x', x(c._govScore) + 10)
            .attr('y', y(c.total_compensation) + 4)
            .attr('fill', '#06d6a0')
            .attr('font-size', '9px')
            .attr('font-weight', '600')
            .text(c.ticker);
    });

    // Regression line (log comp vs gov score)
    var lnComps = withBoth.map(function(c) { return Math.log(c.total_compensation); });
    var govVals = withBoth.map(function(c) { return c._govScore; });
    var n = withBoth.length;
    var sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
    for (var i = 0; i < n; i++) {
        sumX += govVals[i]; sumY += lnComps[i];
        sumXY += govVals[i] * lnComps[i];
        sumX2 += govVals[i] * govVals[i];
        sumY2 += lnComps[i] * lnComps[i];
    }
    var corrNum = n * sumXY - sumX * sumY;
    var corrDen = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
    var corr = corrDen > 0 ? corrNum / corrDen : 0;

    // Linear regression: lnComp = a + b * govScore
    var b = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    var a = (sumY - b * sumX) / n;
    var xDomain = x.domain();
    var regPts = [
        { gv: xDomain[0], comp: Math.exp(a + b * xDomain[0]) },
        { gv: xDomain[1], comp: Math.exp(a + b * xDomain[1]) }
    ];

    g.append('line')
        .attr('x1', x(regPts[0].gv)).attr('x2', x(regPts[1].gv))
        .attr('y1', y(Math.max(y.domain()[0], Math.min(y.domain()[1], regPts[0].comp))))
        .attr('y2', y(Math.max(y.domain()[0], Math.min(y.domain()[1], regPts[1].comp))))
        .attr('stroke', '#a78bfa').attr('stroke-width', 2)
        .attr('stroke-dasharray', '8,4').attr('opacity', 0.6);

    // Correlation annotation
    svg.append('text')
        .attr('x', cw - margin.right - 5)
        .attr('y', margin.top + 14)
        .attr('text-anchor', 'end')
        .attr('fill', textColor)
        .attr('font-size', '11px')
        .attr('opacity', 0.7)
        .text('r = ' + corr.toFixed(3) + ' (n=' + n + ')');

    // Quadrant counts
    var qCounts = { hh: 0, lh: 0, hl: 0, ll: 0 };
    withBoth.forEach(function(c) {
        if (c._govScore >= medianGov && c.total_compensation >= medianComp) qCounts.hh++;
        else if (c._govScore < medianGov && c.total_compensation >= medianComp) qCounts.lh++;
        else if (c._govScore >= medianGov && c.total_compensation < medianComp) qCounts.hl++;
        else qCounts.ll++;
    });

    svg.append('text')
        .attr('x', margin.left + 5)
        .attr('y', 400 - 6)
        .attr('fill', mutedColor)
        .attr('font-size', '10px')
        .text('Quadrants — Well-Gov/High: ' + qCounts.hh + ' · Weak/High: ' + qCounts.lh +
              ' · Well-Gov/Mod: ' + qCounts.hl + ' · Weak/Mod: ' + qCounts.ll);

    // Axis labels
    svg.append('text')
        .attr('x', margin.left + width / 2)
        .attr('y', 400 - 6)
        .attr('text-anchor', 'middle')
        .attr('fill', textColor)
        .attr('font-size', '12px')
        .attr('opacity', 0);

    svg.append('text')
        .attr('x', margin.left + width / 2)
        .attr('y', 400 - 4)
        .attr('text-anchor', 'middle')
        .attr('fill', textColor)
        .attr('font-size', '12px')
        .text('Governance Score (0–100)');

    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -(margin.top + height / 2))
        .attr('y', 14)
        .attr('text-anchor', 'middle')
        .attr('fill', textColor)
        .attr('font-size', '12px')
        .text('CEO Total Compensation (log scale)');
}

/* --- Pay Anomaly Chart — companies whose CEO pay deviates most from sector+governance norm --- */
var _anomalySectorFilter = null; // null = all sectors
var _anomalyCompaniesRef = null; // stash for redraw

function _buildAnomalySectorChips(companies) {
    var chipWrap = document.getElementById('anomaly-sector-chips');
    if (!chipWrap) return;
    chipWrap.innerHTML = '';

    // Gather sectors from companies with governance + comp data
    var sectorSet = {};
    companies.forEach(function(c) {
        if (c._govScore != null && c.total_compensation > 0 && c.sector) sectorSet[c.sector] = true;
    });
    var sectors = Object.keys(sectorSet).sort();

    // "All S&P 500" chip
    var allChip = document.createElement('button');
    allChip.className = 'anomaly-chip' + (_anomalySectorFilter == null ? ' active' : '');
    allChip.textContent = 'All S&P 500';
    allChip.title = 'Show top anomalies across all sectors';
    allChip.addEventListener('click', function() {
        _anomalySectorFilter = null;
        _refreshAnomalyChips();
        drawPayAnomalyChart(_anomalyCompaniesRef || companies);
    });
    chipWrap.appendChild(allChip);

    sectors.forEach(function(sec) {
        var chip = document.createElement('button');
        chip.className = 'anomaly-chip' + (_anomalySectorFilter === sec ? ' active' : '');
        chip.setAttribute('data-sector', sec);
        chip.textContent = sec.replace('Consumer ', 'Cons. ').replace('Communication ', 'Comm. ').replace('Information ', 'Info ');
        chip.title = 'Show anomalies within ' + sec;
        chip.style.borderColor = typeof getSectorColor === 'function' ? getSectorColor(sec) : '#6b7280';
        if (_anomalySectorFilter === sec) {
            chip.style.backgroundColor = (typeof getSectorColor === 'function' ? getSectorColor(sec) : '#6b7280');
            chip.style.color = '#111';
        }
        chip.addEventListener('click', function() {
            _anomalySectorFilter = sec;
            _refreshAnomalyChips();
            drawPayAnomalyChart(_anomalyCompaniesRef || companies);
        });
        chipWrap.appendChild(chip);
    });
}

function _refreshAnomalyChips() {
    var chipWrap = document.getElementById('anomaly-sector-chips');
    if (!chipWrap) return;
    var chips = chipWrap.querySelectorAll('.anomaly-chip');
    for (var i = 0; i < chips.length; i++) {
        var chip = chips[i];
        var isAll = (i === 0);
        var isActive;
        if (isAll) {
            isActive = (_anomalySectorFilter == null);
        } else {
            // Each non-All chip stores its full sector name in data attribute
            isActive = (chip.getAttribute('data-sector') === _anomalySectorFilter);
        }
        chip.classList.toggle('active', isActive);
        if (!isAll && isActive) {
            chip.style.backgroundColor = chip.style.borderColor;
            chip.style.color = '#111';
        } else if (!isAll) {
            chip.style.backgroundColor = '';
            chip.style.color = '';
        }
    }
}

function drawPayAnomalyChart(companies) {
    _anomalyCompaniesRef = companies;
    var container = document.getElementById('pay-anomaly-chart');
    if (!container) return;
    container.innerHTML = '';

    // Build sector chips on first call (or if they don't exist yet)
    var chipWrap = document.getElementById('anomaly-sector-chips');
    if (chipWrap && chipWrap.children.length === 0) {
        _buildAnomalySectorChips(companies);
    }

    // Update title/desc based on sector filter
    var titleEl = document.getElementById('pay-anomaly-title');
    var descEl = document.getElementById('pay-anomaly-desc');
    if (_anomalySectorFilter) {
        if (titleEl) titleEl.textContent = 'Pay Anomalies — ' + _anomalySectorFilter;
        if (descEl) descEl.textContent = 'All ' + _anomalySectorFilter + ' companies ranked by pay deviation from the sector\u2019s governance-adjusted model. Showing every company in the sector.';
    } else {
        if (titleEl) titleEl.textContent = 'Pay Anomalies';
        if (descEl) descEl.textContent = 'Companies whose CEO pay deviates most from what their sector and governance profile would predict. Expected pay is modeled per-sector using log-linear regression on governance score. Overpaid (red) and underpaid (green) relative to the model.';
    }

    // Build sector × governance-bucket expected pay model
    var withData = companies.filter(function(c) {
        return c._govScore != null && c.total_compensation > 0 && c.sector;
    });

    if (withData.length < 50) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient data for anomaly detection</p>';
        return;
    }

    // Group by sector, compute sector median and sector-level regression
    var sectorGroups = {};
    withData.forEach(function(c) {
        if (!sectorGroups[c.sector]) sectorGroups[c.sector] = [];
        sectorGroups[c.sector].push(c);
    });

    // For each company, compute expected pay from sector regression model
    var anomalies = [];

    Object.keys(sectorGroups).forEach(function(sector) {
        var group = sectorGroups[sector];
        if (group.length < 3) return;

        // Compute sector median
        var sortedPay = group.map(function(c) { return c.total_compensation; }).sort(function(a, b) { return a - b; });
        var mid = Math.floor(sortedPay.length / 2);
        var sectorMedian = sortedPay.length % 2 === 0 ? (sortedPay[mid - 1] + sortedPay[mid]) / 2 : sortedPay[mid];

        // Log-linear regression within sector: ln(comp) = a + b*govScore
        var n = group.length;
        var sX = 0, sY = 0, sXY = 0, sX2 = 0;
        group.forEach(function(c) {
            var lnC = Math.log(c.total_compensation);
            sX += c._govScore;
            sY += lnC;
            sXY += c._govScore * lnC;
            sX2 += c._govScore * c._govScore;
        });
        var denom = n * sX2 - sX * sX;
        var bCoeff = denom !== 0 ? (n * sXY - sX * sY) / denom : 0;
        var aCoeff = (sY - bCoeff * sX) / n;

        group.forEach(function(c) {
            var expectedLn = aCoeff + bCoeff * c._govScore;
            var expectedPay = Math.exp(expectedLn);
            var ratio = c.total_compensation / expectedPay;
            var pctDev = (ratio - 1) * 100;
            anomalies.push({
                ticker: c.ticker,
                company: c.company_name,
                ceo: c.ceo_name || '\u2014',
                sector: c.sector,
                actual: c.total_compensation,
                expected: expectedPay,
                ratio: ratio,
                pctDev: pctDev,
                govScore: c._govScore,
                govGrade: c._govGrade || '\u2014',
                sectorMedian: sectorMedian
            });
        });
    });

    // Sort by absolute deviation
    anomalies.sort(function(a, b) { return Math.abs(b.pctDev) - Math.abs(a.pctDev); });

    // Apply sector filter
    var filteredAnomalies = anomalies;
    if (_anomalySectorFilter) {
        filteredAnomalies = anomalies.filter(function(a) { return a.sector === _anomalySectorFilter; });
    }

    // Select display data — in sector mode show ALL companies, otherwise top 15+15
    var displayData;
    if (_anomalySectorFilter) {
        // Show all companies in the sector, split into overpaid then underpaid
        var sectorOver = filteredAnomalies.filter(function(a) { return a.pctDev > 0; });
        sectorOver.sort(function(a, b) { return b.pctDev - a.pctDev; });
        var sectorUnder = filteredAnomalies.filter(function(a) { return a.pctDev <= 0; });
        sectorUnder.sort(function(a, b) { return a.pctDev - b.pctDev; });
        displayData = sectorOver.concat(sectorUnder);
    } else {
        var overpaid = filteredAnomalies.filter(function(a) { return a.pctDev > 0; }).slice(0, 15);
        var underpaid = filteredAnomalies.filter(function(a) { return a.pctDev < 0; }).slice(0, 15).reverse();
        displayData = overpaid.concat(underpaid);
    }

    if (displayData.length === 0) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">No anomaly data for this sector</p>';
        return;
    }

    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
    var textColor = dark ? '#e4e4e7' : '#1a1a2e';
    var mutedColor = dark ? '#6b7280' : '#9ca3af';
    var sectorColor = _anomalySectorFilter && typeof getSectorColor === 'function' ? getSectorColor(_anomalySectorFilter) : null;

    var cw = container.clientWidth || 700;
    var barH = _anomalySectorFilter ? 20 : 22;
    var barGap = _anomalySectorFilter ? 3 : 4;
    var margin = { top: 30, right: 120, bottom: 40, left: 170 };
    var width = cw - margin.left - margin.right;
    var chartH = displayData.length * (barH + barGap) + 30;
    var totalH = chartH + margin.top + margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', cw)
        .attr('height', totalH)
        .attr('role', 'img')
        .attr('aria-label', 'CEO pay anomaly chart' + (_anomalySectorFilter ? ' \u2014 ' + _anomalySectorFilter : '') + ' \u2014 companies paying most above or below sector + governance expectations');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    var maxDev = d3.max(displayData, function(d) { return Math.abs(d.pctDev); });
    if (!maxDev || maxDev < 1) maxDev = 10;
    var x = d3.scaleLinear()
        .domain([-maxDev * 1.05, maxDev * 1.05])
        .range([0, width]);

    // Zero line
    g.append('line')
        .attr('x1', x(0)).attr('x2', x(0))
        .attr('y1', -5).attr('y2', chartH)
        .attr('stroke', textColor).attr('stroke-width', 1)
        .attr('opacity', 0.3);

    g.append('text')
        .attr('x', x(0)).attr('y', -10)
        .attr('text-anchor', 'middle')
        .attr('fill', mutedColor)
        .attr('font-size', '9px')
        .text(_anomalySectorFilter ? 'Expected Pay (' + _anomalySectorFilter + ' model)' : 'Expected Pay (sector + governance model)');

    // Section labels
    var overpaidDisplay = displayData.filter(function(d) { return d.pctDev > 0; });
    var underpaidDisplay = displayData.filter(function(d) { return d.pctDev <= 0; });
    if (overpaidDisplay.length > 0) {
        g.append('text')
            .attr('x', x(maxDev * 0.5))
            .attr('y', -10)
            .attr('text-anchor', 'middle')
            .attr('fill', '#ef476f')
            .attr('font-size', '10px')
            .attr('font-weight', '600')
            .text('\u25B8 Overpaid vs Expected');
    }
    if (underpaidDisplay.length > 0) {
        g.append('text')
            .attr('x', x(-maxDev * 0.5))
            .attr('y', -10)
            .attr('text-anchor', 'middle')
            .attr('fill', '#06d6a0')
            .attr('font-size', '10px')
            .attr('font-weight', '600')
            .text('\u25C2 Underpaid vs Expected');
    }

    // Sector summary stats when filtered — clickable to navigate to Gov vs Pay scatter
    if (_anomalySectorFilter && filteredAnomalies.length > 0) {
        var sectorMedianDev = d3.median(filteredAnomalies, function(a) { return a.pctDev; });
        var sectorMeanGov = d3.mean(filteredAnomalies, function(a) { return a.govScore; });
        var sectorMedPay = d3.median(filteredAnomalies, function(a) { return a.actual; });
        var summaryParts = [];
        summaryParts.push(filteredAnomalies.length + ' companies');
        summaryParts.push('Median Pay ' + fmtCurr(sectorMedPay));
        summaryParts.push('Avg Gov ' + (sectorMeanGov || 0).toFixed(0));
        summaryParts.push('Median Deviation ' + (sectorMedianDev > 0 ? '+' : '') + (sectorMedianDev || 0).toFixed(0) + '%');
        var summaryG = g.append('g')
            .style('cursor', 'pointer')
            .on('mouseover', function() {
                summaryG.select('.anomaly-summary-text').attr('text-decoration', 'underline');
                summaryG.select('.anomaly-nav-hint').attr('opacity', 1);
            })
            .on('mouseout', function() {
                summaryG.select('.anomaly-summary-text').attr('text-decoration', 'none');
                summaryG.select('.anomaly-nav-hint').attr('opacity', 0);
            })
            .on('click', function() {
                // Navigate to Gov vs Pay scatter section
                var govPayPanel = document.getElementById('gov-pay-scatter-panel');
                if (govPayPanel) {
                    var navHeight = document.querySelector('.section-nav') ? document.querySelector('.section-nav').offsetHeight : 0;
                    var panelTop = govPayPanel.getBoundingClientRect().top + window.scrollY - navHeight - 20;
                    window.scrollTo({ top: panelTop, behavior: typeof getScrollBehavior === 'function' ? getScrollBehavior() : 'smooth' });
                    // Flash the panel border briefly
                    govPayPanel.style.outline = '2px solid ' + (sectorColor || '#00b4d8');
                    govPayPanel.style.outlineOffset = '4px';
                    setTimeout(function() {
                        govPayPanel.style.outline = 'none';
                        govPayPanel.style.outlineOffset = '';
                    }, 1500);
                }
            });
        summaryG.append('text')
            .attr('class', 'anomaly-summary-text')
            .attr('x', width / 2)
            .attr('y', chartH + 18)
            .attr('text-anchor', 'middle')
            .attr('fill', sectorColor || mutedColor)
            .attr('font-size', '10px')
            .attr('font-weight', '500')
            .text(summaryParts.join(' \u00B7 '));
        summaryG.append('text')
            .attr('class', 'anomaly-nav-hint')
            .attr('x', width / 2)
            .attr('y', chartH + 32)
            .attr('text-anchor', 'middle')
            .attr('fill', sectorColor || mutedColor)
            .attr('font-size', '9px')
            .attr('opacity', 0)
            .text('\u2192 View in Governance vs Pay scatter');
    }

    // Bars
    displayData.forEach(function(d, i) {
        var by = i * (barH + barGap);
        var barW = Math.abs(x(d.pctDev) - x(0));
        var barX = d.pctDev >= 0 ? x(0) : x(d.pctDev);
        var barColor = d.pctDev >= 0 ? '#ef476f' : '#06d6a0';
        var barOpacity = Math.min(0.9, 0.4 + Math.abs(d.pctDev) / maxDev * 0.5);

        // Bar
        g.append('rect')
            .attr('x', barX).attr('y', by)
            .attr('width', 0).attr('height', barH)
            .attr('fill', barColor)
            .attr('opacity', barOpacity)
            .attr('rx', 3)
            .style('cursor', 'pointer')
            .on('mouseover', function(event) {
                d3.select(this).attr('opacity', 1);
                var rankInSector = '';
                if (_anomalySectorFilter) {
                    var sameDir = filteredAnomalies.filter(function(a) {
                        return d.pctDev >= 0 ? a.pctDev >= 0 : a.pctDev < 0;
                    });
                    sameDir.sort(function(a, b) { return Math.abs(b.pctDev) - Math.abs(a.pctDev); });
                    var rank = sameDir.findIndex(function(a) { return a.ticker === d.ticker; }) + 1;
                    rankInSector = '<br>Sector Rank: #' + rank + ' ' + (d.pctDev >= 0 ? 'most overpaid' : 'most underpaid');
                }
                showChartTooltip(event,
                    '<strong>' + d.ticker + '</strong> \u2014 ' + d.company + '<br>' +
                    'CEO: ' + d.ceo + '<br>' +
                    'Actual Pay: ' + fmtCurr(d.actual) + '<br>' +
                    'Expected (model): ' + fmtCurr(d.expected) + '<br>' +
                    'Deviation: <strong style="color:' + barColor + '">' + (d.pctDev > 0 ? '+' : '') + d.pctDev.toFixed(0) + '%</strong><br>' +
                    'Sector Median: ' + fmtCurr(d.sectorMedian) + '<br>' +
                    'Governance: ' + d.govScore.toFixed(0) + ' (' + d.govGrade + ')' +
                    rankInSector);
            })
            .on('mousemove', function(event) { positionChartTooltip(event); })
            .on('mouseout', function() {
                d3.select(this).attr('opacity', barOpacity);
                hideChartTooltip();
            })
            .on('click', function() {
                if (window.scrollToCompany) window.scrollToCompany(d.ticker);
            })
            .transition()
            .duration(_anomalySectorFilter ? 350 : 500)
            .delay(i * (_anomalySectorFilter ? 12 : 20))
            .ease(d3.easeCubicOut)
            .attr('width', barW);

        // Company label
        g.append('text')
            .attr('x', -6)
            .attr('y', by + barH / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .attr('fill', textColor)
            .attr('font-size', _anomalySectorFilter ? '10px' : '11px')
            .attr('font-weight', '500')
            .style('cursor', 'pointer')
            .on('click', function() {
                if (window.scrollToCompany) window.scrollToCompany(d.ticker);
            })
            .text(d.ticker + ' \u2014 ' + d.ceo.split(/\s+/).slice(-1)[0]);

        // Deviation % label
        var labelX = d.pctDev >= 0 ? x(d.pctDev) + 6 : x(d.pctDev) - 6;
        var labelAnchor = d.pctDev >= 0 ? 'start' : 'end';
        g.append('text')
            .attr('x', labelX)
            .attr('y', by + barH / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', labelAnchor)
            .attr('fill', barColor)
            .attr('font-size', _anomalySectorFilter ? '9px' : '10px')
            .attr('font-weight', '600')
            .attr('opacity', 0)
            .transition()
            .duration(200)
            .delay(i * (_anomalySectorFilter ? 12 : 20) + 300)
            .attr('opacity', 1)
            .text((d.pctDev > 0 ? '+' : '') + d.pctDev.toFixed(0) + '% (' + fmtCurr(d.actual) + ')');
    });

    // Axis label
    svg.append('text')
        .attr('x', margin.left + width / 2)
        .attr('y', totalH - 8)
        .attr('text-anchor', 'middle')
        .attr('fill', textColor)
        .attr('font-size', '12px')
        .text('% Deviation from Expected Pay (' + (_anomalySectorFilter ? _anomalySectorFilter + ' governance model' : 'sector + governance adjusted') + ')');

    // Summary stats (cross-S&P 500 view only)
    if (!_anomalySectorFilter) {
        var meanAbsDev = d3.mean(anomalies, function(a) { return Math.abs(a.pctDev); });
        var overCount = anomalies.filter(function(a) { return a.pctDev > 100; }).length;
        var underCount = anomalies.filter(function(a) { return a.pctDev < -50; }).length;
        svg.append('text')
            .attr('x', margin.left)
            .attr('y', totalH - 8)
            .attr('fill', mutedColor)
            .attr('font-size', '9px')
            .text('Mean |deviation|: ' + meanAbsDev.toFixed(0) + '% \u00B7 ' + overCount + ' companies 2x+ expected \u00B7 ' + underCount + ' companies <50% expected');
    }
}

/* ── Tenure × Pay Growth Analysis ───────────────────────────────────── */

var _tenureGrowthSectorFilter = null; // null = all sectors
var _tenureGrowthCompaniesRef = null; // stash for redraw

function _buildTenureGrowthSectorChips(companies) {
    var chipWrap = document.getElementById('tenure-growth-sector-chips');
    if (!chipWrap) return;
    chipWrap.innerHTML = '';

    // Gather sectors from eligible companies (has tenure + yoy data)
    var sectorSet = {};
    companies.forEach(function(c) {
        if (c._ceoTenureYears != null && c._ceoYoY && c._ceoYoY.pctChange != null && isFinite(c._ceoYoY.pctChange) && c.sector) {
            sectorSet[c.sector] = (sectorSet[c.sector] || 0) + 1;
        }
    });
    var sectors = Object.keys(sectorSet).sort();

    // "All S&P 500" chip
    var allChip = document.createElement('button');
    allChip.className = 'anomaly-chip' + (_tenureGrowthSectorFilter == null ? ' active' : '');
    allChip.textContent = 'All S&P 500';
    allChip.title = 'Show tenure vs pay growth across all sectors';
    allChip.addEventListener('click', function() {
        _tenureGrowthSectorFilter = null;
        _refreshTenureGrowthChips();
        var el = document.getElementById('tenure-pay-growth-chart');
        if (el) el.innerHTML = '';
        drawTenurePayGrowthChart(_tenureGrowthCompaniesRef || companies);
    });
    chipWrap.appendChild(allChip);

    sectors.forEach(function(sec) {
        var chip = document.createElement('button');
        chip.className = 'anomaly-chip' + (_tenureGrowthSectorFilter === sec ? ' active' : '');
        chip.setAttribute('data-sector', sec);
        chip.textContent = sec.replace('Consumer ', 'Cons. ').replace('Communication ', 'Comm. ').replace('Information ', 'Info ');
        chip.title = sec + ' (' + sectorSet[sec] + ' companies)';
        chip.style.borderColor = typeof getSectorColor === 'function' ? getSectorColor(sec) : '#6b7280';
        if (_tenureGrowthSectorFilter === sec) {
            chip.style.backgroundColor = (typeof getSectorColor === 'function' ? getSectorColor(sec) : '#6b7280');
            chip.style.color = '#111';
        }
        chip.addEventListener('click', function() {
            if (_tenureGrowthSectorFilter === sec) {
                _tenureGrowthSectorFilter = null; // toggle off
            } else {
                _tenureGrowthSectorFilter = sec;
            }
            _refreshTenureGrowthChips();
            var el = document.getElementById('tenure-pay-growth-chart');
            if (el) el.innerHTML = '';
            drawTenurePayGrowthChart(_tenureGrowthCompaniesRef || companies);
        });
        chipWrap.appendChild(chip);
    });
}

function _refreshTenureGrowthChips() {
    var chipWrap = document.getElementById('tenure-growth-sector-chips');
    if (!chipWrap) return;
    var chips = chipWrap.querySelectorAll('.anomaly-chip');
    for (var i = 0; i < chips.length; i++) {
        var chip = chips[i];
        var isAll = (i === 0);
        var isActive;
        if (isAll) {
            isActive = (_tenureGrowthSectorFilter == null);
        } else {
            isActive = (chip.getAttribute('data-sector') === _tenureGrowthSectorFilter);
        }
        chip.classList.toggle('active', isActive);
        if (!isAll && isActive) {
            chip.style.backgroundColor = chip.style.borderColor;
            chip.style.color = '#111';
        } else if (!isAll) {
            chip.style.backgroundColor = '';
            chip.style.color = '';
        }
    }
}

function drawTenurePayGrowthChart(companies) {
    _tenureGrowthCompaniesRef = companies;
    var container = document.getElementById('tenure-pay-growth-chart');
    if (!container) return;
    container.innerHTML = '';

    // Build sector chips on first call
    var chipWrap = document.getElementById('tenure-growth-sector-chips');
    if (chipWrap && chipWrap.children.length === 0) {
        _buildTenureGrowthSectorChips(companies);
    }

    // Update title/desc based on sector filter
    var titleEl = document.getElementById('tenure-pay-growth-title');
    var descEl = document.getElementById('tenure-pay-growth-desc');
    var sectorFilter = _tenureGrowthSectorFilter;
    if (sectorFilter) {
        if (titleEl) titleEl.textContent = 'Tenure \u00D7 Pay Growth \u2014 ' + sectorFilter;
        if (descEl) descEl.textContent = sectorFilter + ' CEO pay growth by tenure bracket. Showing all ' + sectorFilter + ' companies with tenure and year-over-year compensation data from DEF 14A proxy filings.';
    } else {
        if (titleEl) titleEl.textContent = 'Tenure \u00D7 Pay Growth';
        if (descEl) descEl.textContent = 'Do long-tenured CEOs accumulate faster pay growth? Median year-over-year CEO compensation change by tenure bracket with IQR range. Individual company dots overlaid. Based on multi-year Summary Compensation Table data from DEF 14A proxy filings.';
    }

    // Gather companies with tenure + multi-year CEO data
    var eligible = [];
    companies.forEach(function(c) {
        if (c._ceoTenureYears == null || !c._ceoYoY || c._ceoYoY.pctChange == null) return;
        if (!isFinite(c._ceoYoY.pctChange)) return;
        if (sectorFilter && c.sector !== sectorFilter) return;
        eligible.push({
            ticker: c.ticker,
            company: c.company_name,
            ceo: c.ceo_name || '\u2014',
            tenure: c._ceoTenureYears,
            yoyPct: c._ceoYoY.pctChange,
            fromComp: c._ceoYoY.fromComp,
            toComp: c._ceoYoY.toComp,
            fromYear: c._ceoYoY.fromYear,
            toYear: c._ceoYoY.toYear,
            sector: c.sector,
            total: c.total_compensation
        });
    });

    if (eligible.length < (sectorFilter ? 5 : 20)) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient tenure + pay growth data' + (sectorFilter ? ' for ' + sectorFilter : '') + '</p>';
        return;
    }

    // Define tenure brackets
    var brackets = [
        { label: 'New CEOs\n(<3 yrs)', min: 0, max: 3, color: '#06d6a0', members: [] },
        { label: 'Mid-tenure\n(3\u201310 yrs)', min: 3, max: 10, color: '#00b4d8', members: [] },
        { label: 'Established\n(10\u201320 yrs)', min: 10, max: 20, color: '#a78bfa', members: [] },
        { label: 'Veterans\n(20+ yrs)', min: 20, max: Infinity, color: '#f59e0b', members: [] }
    ];

    eligible.forEach(function(e) {
        for (var i = 0; i < brackets.length; i++) {
            if (e.tenure >= brackets[i].min && e.tenure < brackets[i].max) {
                brackets[i].members.push(e);
                break;
            }
        }
    });

    // Compute stats per bracket
    brackets.forEach(function(b) {
        if (b.members.length === 0) {
            b.median = 0; b.mean = 0; b.q25 = 0; b.q75 = 0; b.count = 0;
            return;
        }
        b.count = b.members.length;
        var sorted = b.members.map(function(m) { return m.yoyPct; }).sort(function(a, b) { return a - b; });
        // Cap outliers for display (keep data, just limit visual range)
        b.median = sorted[Math.floor(sorted.length / 2)];
        b.mean = sorted.reduce(function(s, v) { return s + v; }, 0) / sorted.length;
        var q1i = Math.floor(sorted.length * 0.25);
        var q3i = Math.floor(sorted.length * 0.75);
        b.q25 = sorted[q1i];
        b.q75 = sorted[q3i];

        // Find best and worst in bracket
        b.best = b.members.slice().sort(function(a, b) { return b.yoyPct - a.yoyPct; })[0];
        b.worst = b.members.slice().sort(function(a, b) { return a.yoyPct - b.yoyPct; })[0];
    });

    var dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
    var textColor = dark ? '#e4e4e7' : '#1a1a2e';
    var mutedColor = dark ? '#6b7280' : '#9ca3af';
    var gridColor = dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';
    var bgPanel = dark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)';

    var cw = container.clientWidth || 700;
    var margin = { top: 40, right: 30, bottom: 60, left: 80 };
    var width = cw - margin.left - margin.right;
    var chartH = 320;
    var totalH = chartH + margin.top + margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', cw)
        .attr('height', totalH)
        .attr('role', 'img')
        .attr('aria-label', 'CEO pay growth by tenure bracket — do longer-tenured CEOs accumulate faster pay growth?');

    var g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    // X scale — tenure brackets
    var x = d3.scaleBand()
        .domain(brackets.map(function(b) { return b.label; }))
        .range([0, width])
        .padding(0.35);

    // Y scale — pay growth %
    var allVals = [];
    brackets.forEach(function(b) {
        if (b.count > 0) { allVals.push(b.median, b.q25, b.q75); }
    });
    var yMin = Math.min(d3.min(allVals) * 1.3, -15);
    var yMax = Math.max(d3.max(allVals) * 1.3, 30);

    var y = d3.scaleLinear()
        .domain([yMin, yMax])
        .range([chartH, 0]);

    // Grid lines
    var ticks = y.ticks(6);
    ticks.forEach(function(t) {
        g.append('line')
            .attr('x1', 0).attr('x2', width)
            .attr('y1', y(t)).attr('y2', y(t))
            .attr('stroke', gridColor);
    });

    // Zero line
    g.append('line')
        .attr('x1', 0).attr('x2', width)
        .attr('y1', y(0)).attr('y2', y(0))
        .attr('stroke', textColor)
        .attr('stroke-width', 1)
        .attr('opacity', 0.4)
        .attr('stroke-dasharray', '4,3');

    g.append('text')
        .attr('x', width + 4)
        .attr('y', y(0))
        .attr('dy', '0.35em')
        .attr('fill', mutedColor)
        .attr('font-size', '9px')
        .text('0%');

    // Draw bars + IQR whiskers for each bracket
    brackets.forEach(function(b, i) {
        if (b.count === 0) return;

        var bx = x(b.label);
        var bw = x.bandwidth();

        // IQR whisker background
        var iqrTop = y(b.q75);
        var iqrBot = y(b.q25);
        g.append('rect')
            .attr('x', bx + bw * 0.3)
            .attr('y', iqrTop)
            .attr('width', bw * 0.4)
            .attr('height', Math.max(1, iqrBot - iqrTop))
            .attr('fill', b.color)
            .attr('opacity', 0.15)
            .attr('rx', 3);

        // Whisker line
        g.append('line')
            .attr('x1', bx + bw / 2).attr('x2', bx + bw / 2)
            .attr('y1', iqrTop).attr('y2', iqrBot)
            .attr('stroke', b.color)
            .attr('stroke-width', 1.5)
            .attr('opacity', 0.4);

        // Median bar
        var barH = Math.abs(y(0) - y(b.median));
        var barY = b.median >= 0 ? y(b.median) : y(0);

        g.append('rect')
            .attr('x', bx)
            .attr('y', barY)
            .attr('width', bw)
            .attr('height', 0)
            .attr('fill', b.color)
            .attr('opacity', 0.8)
            .attr('rx', 4)
            .style('cursor', 'pointer')
            .on('mouseover', function(event) {
                d3.select(this).attr('opacity', 1);
                var tooltipLines = '<strong>' + b.label.replace('\n', ' ') + '</strong><br>' +
                    b.count + ' CEOs<br>' +
                    'Median YoY Growth: <strong style="color:' + b.color + '">' + (b.median > 0 ? '+' : '') + b.median.toFixed(1) + '%</strong><br>' +
                    'Mean YoY Growth: ' + (b.mean > 0 ? '+' : '') + b.mean.toFixed(1) + '%<br>' +
                    'IQR: ' + (b.q25 > 0 ? '+' : '') + b.q25.toFixed(1) + '% to ' + (b.q75 > 0 ? '+' : '') + b.q75.toFixed(1) + '%<br>' +
                    '<span style="color:#06d6a0">\u25B2 ' + b.best.ticker + ' (' + b.best.ceo + '): +' + b.best.yoyPct.toFixed(0) + '%</span><br>' +
                    '<span style="color:#ef476f">\u25BC ' + b.worst.ticker + ' (' + b.worst.ceo + '): ' + b.worst.yoyPct.toFixed(0) + '%</span>';
                showChartTooltip(event, tooltipLines);
            })
            .on('mousemove', function(event) { positionChartTooltip(event); })
            .on('mouseout', function() {
                d3.select(this).attr('opacity', 0.8);
                hideChartTooltip();
            })
            .transition()
            .duration(600)
            .delay(i * 120)
            .ease(d3.easeCubicOut)
            .attr('height', barH);

        // Median value label
        var labelY = b.median >= 0 ? y(b.median) - 8 : y(b.median) + barH + 14;
        g.append('text')
            .attr('x', bx + bw / 2)
            .attr('y', labelY)
            .attr('text-anchor', 'middle')
            .attr('fill', b.color)
            .attr('font-size', '13px')
            .attr('font-weight', '700')
            .attr('opacity', 0)
            .transition()
            .delay(i * 120 + 400)
            .duration(300)
            .attr('opacity', 1)
            .text((b.median > 0 ? '+' : '') + b.median.toFixed(1) + '%');

        // Count label
        g.append('text')
            .attr('x', bx + bw / 2)
            .attr('y', chartH + 18)
            .attr('text-anchor', 'middle')
            .attr('fill', mutedColor)
            .attr('font-size', '10px')
            .text(b.count + ' CEOs');

        // Bracket label (handle multi-line)
        var labelLines = b.label.split('\n');
        labelLines.forEach(function(line, li) {
            g.append('text')
                .attr('x', bx + bw / 2)
                .attr('y', chartH + 32 + li * 13)
                .attr('text-anchor', 'middle')
                .attr('fill', textColor)
                .attr('font-size', '11px')
                .attr('font-weight', li === 0 ? '600' : '400')
                .text(line);
        });

        // Scatter individual company dots overlaid on bar
        b.members.forEach(function(m) {
            var dotY = y(m.yoyPct);
            if (dotY < 0 || dotY > chartH) return; // skip out-of-range
            var jitter = (Math.random() - 0.5) * bw * 0.6;
            g.append('circle')
                .attr('cx', bx + bw / 2 + jitter)
                .attr('cy', dotY)
                .attr('r', 2.5)
                .attr('fill', b.color)
                .attr('opacity', 0.3)
                .style('cursor', 'pointer')
                .on('mouseover', function(event) {
                    d3.select(this).attr('r', 5).attr('opacity', 1);
                    showChartTooltip(event,
                        '<strong>' + m.ticker + '</strong> \u2014 ' + m.company + '<br>' +
                        'CEO: ' + m.ceo + ' (' + m.tenure.toFixed(1) + ' yrs)<br>' +
                        'Pay Growth: <strong style="color:' + (m.yoyPct >= 0 ? '#06d6a0' : '#ef476f') + '">' +
                        (m.yoyPct > 0 ? '+' : '') + m.yoyPct.toFixed(1) + '%</strong><br>' +
                        fmtCurr(m.fromComp) + ' \u2192 ' + fmtCurr(m.toComp) + ' (FY' + m.fromYear + '\u2013' + m.toYear + ')');
                })
                .on('mousemove', function(event) { positionChartTooltip(event); })
                .on('mouseout', function() {
                    d3.select(this).attr('r', 2.5).attr('opacity', 0.3);
                    hideChartTooltip();
                })
                .on('click', function() {
                    if (window.scrollToCompany) window.scrollToCompany(m.ticker);
                });
        });
    });

    // Y-axis labels
    ticks.forEach(function(t) {
        g.append('text')
            .attr('x', -8)
            .attr('y', y(t))
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .attr('fill', mutedColor)
            .attr('font-size', '10px')
            .text((t > 0 ? '+' : '') + t + '%');
    });

    // Y-axis title
    svg.append('text')
        .attr('x', 14)
        .attr('y', margin.top + chartH / 2)
        .attr('transform', 'rotate(-90,14,' + (margin.top + chartH / 2) + ')')
        .attr('text-anchor', 'middle')
        .attr('fill', textColor)
        .attr('font-size', '12px')
        .text('CEO Pay Growth (YoY %)');

    // Overall insight annotation
    var newMedian = brackets[0].count > 0 ? brackets[0].median : null;
    var vetMedian = brackets[3].count > 0 ? brackets[3].median : null;
    if (newMedian != null && vetMedian != null) {
        var scopeLabel = sectorFilter || 'S&P 500';
        var insightText = 'New CEOs grow ' + (newMedian > 0 ? '+' : '') + newMedian.toFixed(0) + '% YoY vs veterans ' +
            (vetMedian > 0 ? '+' : '') + vetMedian.toFixed(0) + '% \u2014 ' +
            (newMedian > vetMedian + 5 ? 'early tenure drives the sharpest pay acceleration' :
             Math.abs(newMedian - vetMedian) < 5 ? 'pay growth is relatively flat across tenure' :
             'longer tenure correlates with higher growth');
        svg.append('text')
            .attr('x', margin.left)
            .attr('y', totalH - 6)
            .attr('fill', mutedColor)
            .attr('font-size', '9px')
            .text(insightText + ' \u00B7 ' + eligible.length + ' ' + scopeLabel + ' companies with tenure + YoY data');
    } else if (eligible.length > 0) {
        // Not enough data in both new and veteran brackets — show what we have
        var scopeLabel2 = sectorFilter || 'S&P 500';
        var activeBrackets = brackets.filter(function(b) { return b.count > 0; });
        var summaryParts = activeBrackets.map(function(b) {
            return b.label.replace('\n', ' ') + ': ' + (b.median > 0 ? '+' : '') + b.median.toFixed(1) + '% (' + b.count + ')';
        });
        svg.append('text')
            .attr('x', margin.left)
            .attr('y', totalH - 6)
            .attr('fill', mutedColor)
            .attr('font-size', '9px')
            .text(summaryParts.join(' \u00B7 ') + ' \u2014 ' + eligible.length + ' ' + scopeLabel2 + ' companies');
    }
}

/* ── Tenure × Governance Cross-Tabulation ──────────────────────────── */

var _crosstabSectorFilter = null; // null = all sectors
var _crosstabCompaniesRef = null; // stash for redraw

function _buildCrosstabSectorChips(companies) {
    var chipWrap = document.getElementById('crosstab-sector-chips');
    if (!chipWrap) return;
    chipWrap.innerHTML = '';

    // Gather sectors from eligible companies (has tenure + governance data)
    var sectorSet = {};
    companies.forEach(function(c) {
        if (c._ceoTenureYears != null && c._govScore != null && c.total_compensation > 0 && c.sector) {
            sectorSet[c.sector] = (sectorSet[c.sector] || 0) + 1;
        }
    });
    var sectors = Object.keys(sectorSet).sort();

    // "All S&P 500" chip
    var allChip = document.createElement('button');
    allChip.className = 'anomaly-chip' + (_crosstabSectorFilter == null ? ' active' : '');
    allChip.textContent = 'All S\u0026P 500';
    allChip.title = 'Show tenure vs governance across all sectors';
    allChip.addEventListener('click', function() {
        _crosstabSectorFilter = null;
        _refreshCrosstabChips();
        var el = document.getElementById('tenure-gov-crosstab-chart');
        if (el) el.innerHTML = '';
        drawTenureGovCrossTab(_crosstabCompaniesRef || companies);
    });
    chipWrap.appendChild(allChip);

    sectors.forEach(function(sec) {
        var chip = document.createElement('button');
        chip.className = 'anomaly-chip' + (_crosstabSectorFilter === sec ? ' active' : '');
        chip.setAttribute('data-sector', sec);
        chip.textContent = sec.replace('Consumer ', 'Cons. ').replace('Communication ', 'Comm. ').replace('Information ', 'Info ');
        chip.title = sec + ' (' + sectorSet[sec] + ' companies)';
        chip.style.borderColor = typeof getSectorColor === 'function' ? getSectorColor(sec) : '#6b7280';
        if (_crosstabSectorFilter === sec) {
            chip.style.backgroundColor = (typeof getSectorColor === 'function' ? getSectorColor(sec) : '#6b7280');
            chip.style.color = '#111';
        }
        chip.addEventListener('click', function() {
            if (_crosstabSectorFilter === sec) {
                _crosstabSectorFilter = null; // toggle off
            } else {
                _crosstabSectorFilter = sec;
            }
            _refreshCrosstabChips();
            var el = document.getElementById('tenure-gov-crosstab-chart');
            if (el) el.innerHTML = '';
            drawTenureGovCrossTab(_crosstabCompaniesRef || companies);
        });
        chipWrap.appendChild(chip);
    });
}

function _refreshCrosstabChips() {
    var chipWrap = document.getElementById('crosstab-sector-chips');
    if (!chipWrap) return;
    var chips = chipWrap.querySelectorAll('.anomaly-chip');
    for (var i = 0; i < chips.length; i++) {
        var chip = chips[i];
        var isAll = (i === 0);
        var isActive;
        if (isAll) {
            isActive = (_crosstabSectorFilter == null);
        } else {
            isActive = (chip.getAttribute('data-sector') === _crosstabSectorFilter);
        }
        chip.classList.toggle('active', isActive);
        if (!isAll && isActive) {
            chip.style.backgroundColor = chip.style.borderColor;
            chip.style.color = '#111';
        } else if (!isAll) {
            chip.style.backgroundColor = '';
            chip.style.color = '';
        }
    }
}

function drawTenureGovCrossTab(companies) {
    _crosstabCompaniesRef = companies;
    var container = document.getElementById('tenure-gov-crosstab-chart');
    if (!container) return;
    container.innerHTML = '';

    // Build sector chips on first call
    var chipWrap = document.getElementById('crosstab-sector-chips');
    if (chipWrap && chipWrap.children.length === 0) {
        _buildCrosstabSectorChips(companies);
    }

    // Update title/desc based on sector filter
    var titleEl = document.getElementById('tenure-gov-crosstab-title');
    var descEl = document.getElementById('tenure-gov-crosstab-desc');
    var sectorFilter = _crosstabSectorFilter;
    if (sectorFilter) {
        if (titleEl) titleEl.textContent = 'Tenure \u00D7 Governance \u2014 ' + sectorFilter;
        if (descEl) descEl.textContent = sectorFilter + ' CEO tenure vs governance quality. Cross-tabulation of tenure brackets by governance quartiles for all ' + sectorFilter + ' companies with tenure and governance data from DEF 14A proxy filings.';
    } else {
        if (titleEl) titleEl.textContent = 'Tenure \u00D7 Governance';
        if (descEl) descEl.textContent = 'Does longer CEO tenure erode corporate governance quality? Cross-tabulation of tenure brackets (rows) by governance score quartiles (columns). Each cell shows company count, median CEO pay, and YoY pay change. Cell color intensity reflects median pay. Click any cell to filter the main table.';
    }

    var textColor = getThemeTextColor();
    var mutedColor = getThemeMutedColor();
    var dark = isDarkTheme();

    // Filter to companies with both tenure and governance data
    var eligible = companies.filter(function(c) {
        var base = c._ceoTenureYears != null && c._govScore != null && c.total_compensation > 0;
        if (sectorFilter) return base && c.sector === sectorFilter;
        return base;
    });
    var minThreshold = sectorFilter ? 5 : 20;
    if (eligible.length < minThreshold) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient tenure + governance data (' + eligible.length + ' companies' + (sectorFilter ? ' in ' + sectorFilter : '') + ')</p>';
        return;
    }

    // Define tenure brackets (rows)
    var tenureBrackets = [
        { label: 'New (<3 yrs)', min: 0, max: 3, key: 'new' },
        { label: 'Mid (3–10)', min: 3, max: 10, key: 'mid' },
        { label: 'Established (10–20)', min: 10, max: 20, key: 'est' },
        { label: 'Veterans (20+)', min: 20, max: 999, key: 'vet' }
    ];

    // Define governance quartiles (columns) using data-driven breaks
    var govVals = eligible.map(function(c) { return c._govScore; }).sort(function(a, b) { return a - b; });
    var q1 = govVals[Math.floor(govVals.length * 0.25)];
    var q2 = govVals[Math.floor(govVals.length * 0.5)];
    var q3 = govVals[Math.floor(govVals.length * 0.75)];

    var govBrackets = [
        { label: 'Weak Gov (Q1)', min: 0, max: q1, key: 'q1', color: '#ef476f' },
        { label: 'Below Avg (Q2)', min: q1, max: q2, key: 'q2', color: '#ffd166' },
        { label: 'Above Avg (Q3)', min: q2, max: q3, key: 'q3', color: '#06d6a0' },
        { label: 'Strong Gov (Q4)', min: q3, max: 101, key: 'q4', color: '#118ab2' }
    ];

    // Build cross-tab cells
    var cells = {};
    var allMedians = [];
    tenureBrackets.forEach(function(tb) {
        govBrackets.forEach(function(gb) {
            var key = tb.key + '-' + gb.key;
            var members = eligible.filter(function(c) {
                return c._ceoTenureYears >= tb.min && c._ceoTenureYears < tb.max &&
                       c._govScore >= gb.min && c._govScore < gb.max;
            });
            // Compute stats
            var pays = members.map(function(c) { return c.total_compensation; }).sort(function(a, b) { return a - b; });
            var medianPay = pays.length > 0 ? pays[Math.floor(pays.length / 2)] : 0;
            var meanPay = pays.length > 0 ? d3.mean(pays) : 0;
            // YoY growth
            var yoyMembers = members.filter(function(c) { return c._ceoYoY && c._ceoYoY.pctChange != null && isFinite(c._ceoYoY.pctChange); });
            var yoyVals = yoyMembers.map(function(c) { return c._ceoYoY.pctChange; }).sort(function(a, b) { return a - b; });
            var medianYoY = yoyVals.length > 0 ? yoyVals[Math.floor(yoyVals.length / 2)] : null;

            cells[key] = {
                count: members.length,
                medianPay: medianPay,
                meanPay: meanPay,
                medianYoY: medianYoY,
                members: members,
                tenureKey: tb.key,
                govKey: gb.key
            };
            if (medianPay > 0) allMedians.push(medianPay);
        });
    });

    // Color scale based on median pay (log scale for better contrast)
    var payExtent = d3.extent(allMedians);
    var payColorScale = d3.scaleSequential(d3.interpolateYlOrRd)
        .domain([Math.log(payExtent[0] || 1), Math.log(payExtent[1] || 2)]);

    // Build HTML table
    var html = '<div class="crosstab-wrapper">';
    html += '<table class="crosstab-table" role="grid" aria-label="Tenure × Governance cross-tabulation">';

    // Header row
    html += '<thead><tr><th class="crosstab-corner" aria-label="Tenure vs Governance"></th>';
    govBrackets.forEach(function(gb) {
        html += '<th class="crosstab-col-header" style="border-bottom:3px solid ' + gb.color + '">' + gb.label + '</th>';
    });
    html += '<th class="crosstab-col-header crosstab-row-total">Row Total</th>';
    html += '</tr></thead>';

    // Body rows
    html += '<tbody>';
    tenureBrackets.forEach(function(tb) {
        html += '<tr>';
        html += '<th class="crosstab-row-header">' + tb.label + '</th>';
        var rowTotal = 0;
        var rowTotalPays = [];
        govBrackets.forEach(function(gb) {
            var key = tb.key + '-' + gb.key;
            var cell = cells[key];
            rowTotal += cell.count;
            cell.members.forEach(function(m) { rowTotalPays.push(m.total_compensation); });

            // Cell background color based on median pay
            var bgColor = 'transparent';
            var cellTextColor = textColor;
            if (cell.count > 0 && cell.medianPay > 0) {
                var intensity = (Math.log(cell.medianPay) - Math.log(payExtent[0] || 1)) / (Math.log(payExtent[1] || 2) - Math.log(payExtent[0] || 1));
                intensity = Math.max(0, Math.min(1, intensity));
                if (dark) {
                    bgColor = 'rgba(239, 71, 111, ' + (0.08 + intensity * 0.42) + ')';
                    cellTextColor = intensity > 0.6 ? '#fff' : textColor;
                } else {
                    bgColor = 'rgba(239, 71, 111, ' + (0.05 + intensity * 0.35) + ')';
                    cellTextColor = intensity > 0.7 ? '#1a1a2e' : '#1a1a2e';
                }
            }

            // YoY arrow
            var yoyStr = '';
            if (cell.medianYoY != null) {
                var yoyColor = cell.medianYoY >= 0 ? '#06d6a0' : '#ef476f';
                yoyStr = '<span class="crosstab-yoy" style="color:' + yoyColor + '">' +
                    (cell.medianYoY >= 0 ? '↑' : '↓') + Math.abs(cell.medianYoY).toFixed(1) + '%</span>';
            }

            // Top company names for tooltip
            var topCompanies = cell.members.slice().sort(function(a, b) { return b.total_compensation - a.total_compensation; }).slice(0, 5);
            var tooltipLines = topCompanies.map(function(c) { return c.ticker + ' (' + c.ceo_name + ') ' + fmtCurr(c.total_compensation); });
            var tooltip = cell.count + ' companies\nMedian: ' + fmtCurr(cell.medianPay) + '\n' + (tooltipLines.length > 0 ? 'Top: ' + tooltipLines.join(', ') : '');

            html += '<td class="crosstab-cell" style="background:' + bgColor + ';color:' + cellTextColor + '" ' +
                'data-tenure="' + tb.key + '" data-gov="' + gb.key + '" ' +
                'title="' + tooltip.replace(/"/g, '&quot;') + '" tabindex="0" role="gridcell">';
            if (cell.count === 0) {
                html += '<span class="crosstab-empty">—</span>';
            } else {
                html += '<span class="crosstab-count">' + cell.count + '</span>';
                html += '<span class="crosstab-pay">' + fmtCurr(cell.medianPay) + '</span>';
                html += yoyStr;
            }
            html += '</td>';
        });
        // Row total
        rowTotalPays.sort(function(a, b) { return a - b; });
        var rowMedian = rowTotalPays.length > 0 ? rowTotalPays[Math.floor(rowTotalPays.length / 2)] : 0;
        html += '<td class="crosstab-cell crosstab-row-total">';
        html += '<span class="crosstab-count">' + rowTotal + '</span>';
        html += '<span class="crosstab-pay">' + fmtCurr(rowMedian) + '</span>';
        html += '</td>';
        html += '</tr>';
    });

    // Column totals row
    html += '<tr class="crosstab-col-total-row">';
    html += '<th class="crosstab-row-header">Column Total</th>';
    var grandTotal = 0;
    var grandTotalPays = [];
    govBrackets.forEach(function(gb) {
        var colTotal = 0;
        var colPays = [];
        tenureBrackets.forEach(function(tb) {
            var key = tb.key + '-' + gb.key;
            colTotal += cells[key].count;
            cells[key].members.forEach(function(m) { colPays.push(m.total_compensation); });
        });
        grandTotal += colTotal;
        colPays.forEach(function(p) { grandTotalPays.push(p); });
        colPays.sort(function(a, b) { return a - b; });
        var colMedian = colPays.length > 0 ? colPays[Math.floor(colPays.length / 2)] : 0;
        html += '<td class="crosstab-cell crosstab-col-total">';
        html += '<span class="crosstab-count">' + colTotal + '</span>';
        html += '<span class="crosstab-pay">' + fmtCurr(colMedian) + '</span>';
        html += '</td>';
    });
    // Grand total
    grandTotalPays.sort(function(a, b) { return a - b; });
    var grandMedian = grandTotalPays.length > 0 ? grandTotalPays[Math.floor(grandTotalPays.length / 2)] : 0;
    html += '<td class="crosstab-cell crosstab-row-total crosstab-col-total">';
    html += '<span class="crosstab-count">' + grandTotal + '</span>';
    html += '<span class="crosstab-pay">' + fmtCurr(grandMedian) + '</span>';
    html += '</td>';
    html += '</tr>';
    html += '</tbody></table>';

    // Quadrant analysis narrative
    var weakVet = cells['vet-q1'];
    var strongNew = cells['new-q4'];
    var weakNew = cells['new-q1'];
    var strongVet = cells['vet-q4'];

    var narrative = '';
    var sectorLabel = sectorFilter ? sectorFilter : 'S&P 500';
    // Key insight: does tenure erode governance?
    var newInWeak = (cells['new-q1'].count + cells['new-q2'].count);
    var newInStrong = (cells['new-q3'].count + cells['new-q4'].count);
    var vetInWeak = (cells['vet-q1'].count + cells['vet-q2'].count);
    var vetInStrong = (cells['vet-q3'].count + cells['vet-q4'].count);
    var newTotal = newInWeak + newInStrong;
    var vetTotal = vetInWeak + vetInStrong;

    if (newTotal > 0 && vetTotal > 0) {
        var newWeakPct = (newInWeak / newTotal * 100).toFixed(0);
        var vetWeakPct = (vetInWeak / vetTotal * 100).toFixed(0);
        var tenureErodesGov = vetInWeak / vetTotal > newInWeak / newTotal + 0.05;
        var tenurePreservesGov = newInWeak / newTotal > vetInWeak / vetTotal + 0.05;

        if (tenureErodesGov) {
            narrative = '<span class="crosstab-finding warning">\u26a0\ufe0f Tenure appears to erode governance' + (sectorFilter ? ' in ' + sectorFilter : '') + ':</span> ' +
                vetWeakPct + '% of veteran CEOs (20+ yrs) fall in weak governance (Q1\u2013Q2), vs only ' +
                newWeakPct + '% of new CEOs (<3 yrs).';
        } else if (tenurePreservesGov) {
            narrative = '<span class="crosstab-finding positive">\u2713 Tenure does not erode governance' + (sectorFilter ? ' in ' + sectorFilter : '') + ':</span> ' +
                'New CEOs are actually more likely to have weak governance (' + newWeakPct + '% in Q1\u2013Q2) than veterans (' + vetWeakPct + '%).';
        } else {
            narrative = '<span class="crosstab-finding neutral">\u2248 Governance is tenure-neutral' + (sectorFilter ? ' in ' + sectorFilter : '') + ':</span> ' +
                'Weak-governance rates are similar for new CEOs (' + newWeakPct + '%) and veterans (' + vetWeakPct + '%).';
        }

        // Pay differential in the danger zone
        if (weakVet.count > 0 && strongNew.count > 0) {
            var dangerPay = weakVet.medianPay;
            var safePay = strongNew.medianPay;
            if (dangerPay > 0 && safePay > 0) {
                var payDelta = ((dangerPay / safePay - 1) * 100).toFixed(0);
                narrative += ' Veteran CEOs with weak governance earn ' +
                    (parseInt(payDelta) > 0 ? payDelta + '% more' : Math.abs(parseInt(payDelta)) + '% less') +
                    ' than new CEOs with strong governance (' + fmtCurr(dangerPay) + ' vs ' + fmtCurr(safePay) + ').';
            }
        }
    } else if (newTotal === 0 && vetTotal > 0) {
        var vetWeakPct2 = (vetInWeak / vetTotal * 100).toFixed(0);
        narrative = '<span class="crosstab-finding neutral">' + sectorLabel + ': No new CEOs (<3 yrs) in dataset.</span> ' +
            vetWeakPct2 + '% of veteran CEOs fall in weak governance (Q1\u2013Q2).';
    } else if (vetTotal === 0 && newTotal > 0) {
        var newWeakPct2 = (newInWeak / newTotal * 100).toFixed(0);
        narrative = '<span class="crosstab-finding neutral">' + sectorLabel + ': No veteran CEOs (20+ yrs) in dataset.</span> ' +
            newWeakPct2 + '% of new CEOs fall in weak governance (Q1\u2013Q2).';
    } else {
        narrative = '<span class="crosstab-finding neutral">' + sectorLabel + ': Insufficient data for new and veteran CEO comparison.</span>';
    }

    html += '<div class="crosstab-narrative">' + narrative + '</div>';

    // Legend
    html += '<div class="crosstab-legend">';
    html += '<span class="crosstab-legend-item">Cell color = median CEO pay intensity</span>';
    html += '<span class="crosstab-legend-item"><span style="color:#06d6a0">↑</span> / <span style="color:#ef476f">↓</span> = median YoY pay change</span>';
    html += '<span class="crosstab-legend-item">Governance quartiles: Q1 = bottom 25%, Q4 = top 25% by governance score</span>';
    html += '</div>';

    html += '</div>';
    container.innerHTML = html;

    // Click handler: click cell to scroll to & filter main table
    container.querySelectorAll('.crosstab-cell[data-tenure]').forEach(function(td) {
        td.style.cursor = 'pointer';
        td.addEventListener('click', function() {
            var tKey = td.getAttribute('data-tenure');
            var gKey = td.getAttribute('data-gov');
            var cellKey = tKey + '-' + gKey;
            var cell = cells[cellKey];
            if (!cell || cell.count === 0) return;

            // Build ticker list and filter the main table
            var tickers = cell.members.map(function(c) { return c.ticker; });
            if (typeof window.filterTableByTickers === 'function') {
                window.filterTableByTickers(tickers, 'Tenure: ' + tKey + ' × Gov: ' + gKey);
            }
            // Scroll to table
            var tableSection = document.getElementById('compensation-table-section');
            if (tableSection) {
                tableSection.scrollIntoView({ behavior: getScrollBehavior(), block: 'start' });
            }
        });
    });
}


var _gerSectorFilter = null;
var _gerCompaniesRef = null;

function _buildGerSectorChips(companies) {
    var chipWrap = document.getElementById('ger-sector-chips');
    if (!chipWrap) return;
    chipWrap.innerHTML = '';
    var sectorSet = {};
    companies.forEach(function(c) {
        if (c._gerScore != null && c.sector) {
            sectorSet[c.sector] = (sectorSet[c.sector] || 0) + 1;
        }
    });
    var sectors = Object.keys(sectorSet).sort();

    var allChip = document.createElement('button');
    allChip.className = 'anomaly-chip' + (_gerSectorFilter == null ? ' active' : '');
    allChip.textContent = 'All S&P 500';
    allChip.title = 'Show governance erosion risk across all sectors';
    allChip.addEventListener('click', function() {
        _gerSectorFilter = null;
        _refreshGerChips();
        var el = document.getElementById('ger-chart');
        if (el) el.innerHTML = '';
        drawGERChart(_gerCompaniesRef || companies);
    });
    chipWrap.appendChild(allChip);

    sectors.forEach(function(sec) {
        var chip = document.createElement('button');
        chip.className = 'anomaly-chip' + (_gerSectorFilter === sec ? ' active' : '');
        chip.setAttribute('data-sector', sec);
        chip.textContent = sec.replace('Consumer ', 'Cons. ').replace('Communication ', 'Comm. ').replace('Information ', 'Info ');
        chip.title = sec + ' (' + sectorSet[sec] + ' companies)';
        chip.style.borderColor = typeof getSectorColor === 'function' ? getSectorColor(sec) : '#6b7280';
        if (_gerSectorFilter === sec) {
            chip.style.backgroundColor = (typeof getSectorColor === 'function' ? getSectorColor(sec) : '#6b7280');
            chip.style.color = '#111';
        }
        chip.addEventListener('click', function() {
            if (_gerSectorFilter === sec) {
                _gerSectorFilter = null;
            } else {
                _gerSectorFilter = sec;
            }
            _refreshGerChips();
            var el = document.getElementById('ger-chart');
            if (el) el.innerHTML = '';
            drawGERChart(_gerCompaniesRef || companies);
        });
        chipWrap.appendChild(chip);
    });
}

function _refreshGerChips() {
    var chipWrap = document.getElementById('ger-sector-chips');
    if (!chipWrap) return;
    var chips = chipWrap.querySelectorAll('.anomaly-chip');
    for (var i = 0; i < chips.length; i++) {
        var chip = chips[i];
        var isAll = (i === 0);
        var isActive;
        if (isAll) {
            isActive = (_gerSectorFilter == null);
        } else {
            isActive = (chip.getAttribute('data-sector') === _gerSectorFilter);
        }
        chip.classList.toggle('active', isActive);
        if (!isAll && isActive) {
            chip.style.backgroundColor = chip.style.borderColor;
            chip.style.color = '#111';
        } else if (!isAll) {
            chip.style.backgroundColor = '';
            chip.style.color = '';
        }
    }
}

function drawGERChart(companies) {
    _gerCompaniesRef = companies;
    var container = document.getElementById('ger-chart');
    if (!container) return;
    container.innerHTML = '';

    // Build sector chips on first call
    var chipWrap = document.getElementById('ger-sector-chips');
    if (chipWrap && chipWrap.children.length === 0) {
        _buildGerSectorChips(companies);
    }

    // Update title/desc based on sector filter
    var titleEl = document.getElementById('ger-chart-title');
    var descEl = document.getElementById('ger-chart-desc');
    var sectorFilter = _gerSectorFilter;
    if (sectorFilter) {
        if (titleEl) titleEl.textContent = 'Governance Erosion Risk \u2014 ' + sectorFilter;
        if (descEl) descEl.textContent = 'Top ' + sectorFilter + ' companies by governance erosion risk. Stacked components show what drives each company\'s risk profile.';
    } else {
        if (titleEl) titleEl.textContent = 'Governance Erosion Risk';
        if (descEl) descEl.textContent = 'Companies most at risk for governance erosion from CEO entrenchment. Score 0\u2013100 from four components: tenure duration, governance quality deficit, pay-governance mismatch, and CEO pay concentration. Click any bar for company details.';
    }

    var textColor = getThemeTextColor();
    var mutedColor = getThemeMutedColor();
    var dark = isDarkTheme();

    // Filter companies
    var eligible = companies.filter(function(c) {
        var base = c._gerScore != null && c._gerScore > 0;
        if (sectorFilter) return base && c.sector === sectorFilter;
        return base;
    });
    eligible.sort(function(a, b) { return b._gerScore - a._gerScore; });

    var showCount = Math.min(25, eligible.length);
    if (showCount < 3) {
        container.innerHTML = '<p style="color:#a1a1aa;padding:40px;text-align:center;">Insufficient data (' + eligible.length + ' companies' + (sectorFilter ? ' in ' + sectorFilter : '') + ')</p>';
        return;
    }
    var top = eligible.slice(0, showCount);

    var margin = { top: 30, right: 100, bottom: 40, left: 120 };
    var width = Math.min(container.clientWidth || 700, 900) - margin.left - margin.right;
    var barHeight = 22;
    var barGap = 4;
    var height = showCount * (barHeight + barGap) + margin.top + margin.bottom;

    var svg = d3.select(container).append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height)
        .attr('viewBox', '0 0 ' + (width + margin.left + margin.right) + ' ' + height)
        .attr('role', 'img')
        .attr('aria-label', 'Governance erosion risk chart');

    var g = svg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

    // Scales
    var xScale = d3.scaleLinear().domain([0, 100]).range([0, width]);
    var yScale = d3.scaleBand()
        .domain(top.map(function(c) { return c.ticker; }))
        .range([0, showCount * (barHeight + barGap)])
        .padding(0.15);

    // X axis
    g.append('g')
        .attr('transform', 'translate(0,' + (showCount * (barHeight + barGap)) + ')')
        .call(d3.axisBottom(xScale).ticks(5).tickFormat(function(d) { return d; }))
        .selectAll('text').style('fill', mutedColor).style('font-size', '10px');
    g.select('.domain').style('stroke', mutedColor);
    g.selectAll('.tick line').style('stroke', mutedColor).style('opacity', 0.3);

    // X axis label
    g.append('text')
        .attr('x', width / 2)
        .attr('y', showCount * (barHeight + barGap) + 32)
        .attr('text-anchor', 'middle')
        .style('fill', mutedColor)
        .style('font-size', '11px')
        .text('Governance Erosion Risk Score (0\u2013100)');

    // Gridlines
    g.append('g').selectAll('line')
        .data([25, 50, 75])
        .enter().append('line')
        .attr('x1', function(d) { return xScale(d); })
        .attr('x2', function(d) { return xScale(d); })
        .attr('y1', 0)
        .attr('y2', showCount * (barHeight + barGap))
        .style('stroke', mutedColor)
        .style('stroke-opacity', 0.15)
        .style('stroke-dasharray', '3,3');

    // Risk threshold line at 60 (High)
    g.append('line')
        .attr('x1', xScale(60))
        .attr('x2', xScale(60))
        .attr('y1', -5)
        .attr('y2', showCount * (barHeight + barGap))
        .style('stroke', '#ef476f')
        .style('stroke-width', 1.5)
        .style('stroke-dasharray', '5,3')
        .style('opacity', 0.7);
    g.append('text')
        .attr('x', xScale(60) + 3)
        .attr('y', -8)
        .style('fill', '#ef476f')
        .style('font-size', '9px')
        .style('font-weight', '600')
        .text('High Risk \u2192');

    // Component colors
    var compColors = {
        tenure: '#a78bfa',
        govDeficit: '#ef476f',
        payMismatch: '#fb923c',
        concentration: '#ffd166'
    };
    var compLabels = {
        tenure: 'Tenure Duration',
        govDeficit: 'Gov Quality Deficit',
        payMismatch: 'Pay-Gov Mismatch',
        concentration: 'CEO Concentration'
    };
    var compKeys = ['tenure', 'govDeficit', 'payMismatch', 'concentration'];

    // Stacked bars
    top.forEach(function(c) {
        var y = yScale(c.ticker);
        var bh = yScale.bandwidth();
        var x0 = 0;
        compKeys.forEach(function(key, ki) {
            var val = c._gerComponents[key] || 0;
            var w = xScale(val);
            if (w < 1) return;
            var bar = g.append('rect')
                .attr('x', x0)
                .attr('y', y)
                .attr('width', w)
                .attr('height', bh)
                .attr('fill', compColors[key])
                .attr('rx', ki === 0 ? 3 : 0)
                .style('cursor', 'pointer')
                .style('opacity', 0.85)
                .on('mouseover', function() {
                    d3.select(this).style('opacity', 1);
                })
                .on('mouseout', function() {
                    d3.select(this).style('opacity', 0.85);
                });
            // Round right edge of last visible component
            if (ki === compKeys.length - 1) {
                bar.attr('rx', 3);
            }
            x0 += w;
        });

        // Risk label on right
        var riskColor = c._gerRisk === 'Critical' ? '#dc2626' : c._gerRisk === 'High' ? '#ef476f' :
            c._gerRisk === 'Elevated' ? '#fb923c' : c._gerRisk === 'Moderate' ? '#ffd166' : '#06d6a0';
        g.append('text')
            .attr('x', xScale(c._gerScore) + 6)
            .attr('y', y + bh / 2 + 4)
            .style('fill', riskColor)
            .style('font-size', '11px')
            .style('font-weight', '700')
            .text(c._gerScore);

        // Company label on left
        g.append('text')
            .attr('x', -4)
            .attr('y', y + bh / 2 + 4)
            .attr('text-anchor', 'end')
            .style('fill', textColor)
            .style('font-size', '11px')
            .style('font-weight', '500')
            .style('cursor', 'pointer')
            .text(c.ticker)
            .on('click', function() {
                if (typeof window.openDetailPanel === 'function') window.openDetailPanel(c.ticker);
            });

        // Tooltip rect overlay
        g.append('rect')
            .attr('x', 0)
            .attr('y', y)
            .attr('width', width)
            .attr('height', bh)
            .attr('fill', 'transparent')
            .style('cursor', 'pointer')
            .on('click', function() {
                if (typeof window.openDetailPanel === 'function') window.openDetailPanel(c.ticker);
            })
            .append('title')
            .text(c.company_name + ' (' + c.ticker + ')\nCEO: ' + c.ceo_name + '\nGER Score: ' + c._gerScore + '/100 (' + c._gerRisk + ')\n' +
                'Tenure: ' + (c._ceoTenureYears || '?') + ' yrs (' + c._gerComponents.tenure + ' pts)\n' +
                'Gov Deficit: ' + c._gerComponents.govDeficit + ' pts\n' +
                'Pay-Gov Mismatch: ' + c._gerComponents.payMismatch + ' pts\n' +
                'CEO Concentration: ' + c._gerComponents.concentration + ' pts\n' +
                'Governance: ' + (c._govScore || '?') + '/100 (' + (c._govGrade || '?') + ')\n' +
                'Total Comp: ' + (typeof fmtCurr === 'function' ? fmtCurr(c.total_compensation) : '$' + Math.round(c.total_compensation / 1000000) + 'M') +
                '\nClick to open detail panel · Double-click for scatter view');

        // Scatter navigation icon (small chart icon after the score label)
        var scatterIconX = Math.min(xScale(c._gerScore) + 22, width - 10);
        (function(ticker) {
            g.append('text')
                .attr('x', scatterIconX)
                .attr('y', y + bh / 2 + 4)
                .style('fill', mutedColor)
                .style('font-size', '10px')
                .style('cursor', 'pointer')
                .style('opacity', 0.4)
                .text('⤴')
                .on('mouseover', function() { d3.select(this).style('opacity', 1); })
                .on('mouseout', function() { d3.select(this).style('opacity', 0.4); })
                .on('click', function(event) {
                    event.stopPropagation();
                    if (typeof window.navigateToScatter === 'function') {
                        window.navigateToScatter(ticker, '_gerScore', 'total_compensation');
                    }
                })
                .append('title')
                .text('View ' + ticker + ' in GER vs Pay scatter');
        })(c.ticker);
    });

    // Legend
    var legendY = -20;
    var legendX = 0;
    compKeys.forEach(function(key) {
        g.append('rect')
            .attr('x', legendX)
            .attr('y', legendY)
            .attr('width', 10)
            .attr('height', 10)
            .attr('rx', 2)
            .attr('fill', compColors[key]);
        g.append('text')
            .attr('x', legendX + 14)
            .attr('y', legendY + 9)
            .style('fill', mutedColor)
            .style('font-size', '10px')
            .text(compLabels[key]);
        legendX += compLabels[key].length * 6.5 + 24;
    });

    // Summary narrative below chart
    var narrativeDiv = document.createElement('div');
    narrativeDiv.className = 'ger-narrative';
    var highRiskCount = eligible.filter(function(c) { return c._gerScore >= 60; }).length;
    var criticalCount = eligible.filter(function(c) { return c._gerScore >= 75; }).length;
    var sectorLabel = sectorFilter || 'S&P 500';

    // Which component contributes most across high-risk companies
    var highRisk = eligible.filter(function(c) { return c._gerScore >= 60; });
    var componentTotals = { tenure: 0, govDeficit: 0, payMismatch: 0, concentration: 0 };
    highRisk.forEach(function(c) {
        compKeys.forEach(function(k) { componentTotals[k] += (c._gerComponents[k] || 0); });
    });
    var topComponent = compKeys.reduce(function(a, b) { return componentTotals[a] > componentTotals[b] ? a : b; });

    var narrativeHtml = '<div class="ger-narrative-inner">';
    if (highRiskCount > 0) {
        narrativeHtml += '<span class="crosstab-finding warning">\u26a0\ufe0f ' + highRiskCount + ' ' + sectorLabel + ' companies score \u226560 (high/critical risk)</span>';
        if (criticalCount > 0) {
            narrativeHtml += ' including ' + criticalCount + ' in the critical zone (\u226575).';
        } else {
            narrativeHtml += '.';
        }
        narrativeHtml += ' The dominant risk factor among high-risk companies is <strong>' + compLabels[topComponent].toLowerCase() + '</strong>.';
    } else {
        narrativeHtml += '<span class="crosstab-finding positive">\u2713 No ' + sectorLabel + ' companies score \u226560 \u2014 governance erosion risk is generally contained.</span>';
    }
    // Average GER by risk level for context
    var avgGer = eligible.length > 0 ? Math.round(eligible.reduce(function(s, c) { return s + c._gerScore; }, 0) / eligible.length) : 0;
    narrativeHtml += ' ' + sectorLabel + ' average GER score: ' + avgGer + '/100.';
    narrativeHtml += '</div>';

    // Cross-chart navigation: top-3 high-GER companies with scatter links
    if (highRiskCount > 0) {
        var topRisk = eligible.filter(function(c) { return c._gerScore >= 60; })
            .sort(function(a, b) { return b._gerScore - a._gerScore; })
            .slice(0, 3);
        narrativeHtml += '<div class="ger-scatter-nav-strip" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;">';
        narrativeHtml += '<span style="font-size:0.75rem;color:var(--text-muted);">Explore in scatter:</span>';
        topRisk.forEach(function(c) {
            narrativeHtml += '<button class="ger-scatter-nav" data-ticker="' + c.ticker + '">' + c.ticker + ' (GER ' + c._gerScore + ') →</button>';
        });
        narrativeHtml += '</div>';
    }

    narrativeDiv.innerHTML = narrativeHtml;
    container.appendChild(narrativeDiv);

    // Wire up scatter navigation buttons
    narrativeDiv.querySelectorAll('.ger-scatter-nav').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var ticker = btn.getAttribute('data-ticker');
            if (typeof window.navigateToScatter === 'function') {
                window.navigateToScatter(ticker, '_gerScore', 'total_compensation');
            }
        });
    });
}

/* === Cross-Chart Navigation: Navigate to Scatter with Company Highlight === */

// Pending highlight ticker — set before scatter redraws, consumed after dots render
var _scatterHighlightTicker = null;
var _scatterHighlightTimer = null;

/**
 * Navigate to the scatter chart, optionally switching to a preset axis combo,
 * and highlight a specific company with a pulsing ring.
 * @param {string} ticker - Company ticker to highlight
 * @param {string} [presetX] - X axis metric key (e.g. '_gerScore')
 * @param {string} [presetY] - Y axis metric key (e.g. 'total_compensation')
 */
window.navigateToScatter = function(ticker, presetX, presetY) {
    // Set preset axes if specified
    var xSel = document.getElementById('scatter-x-metric');
    var ySel = document.getElementById('scatter-y-metric');
    if (presetX && xSel) xSel.value = presetX;
    if (presetY && ySel) ySel.value = presetY;

    // Sync preset button active states
    if (typeof _syncPresetActiveState === 'function') _syncPresetActiveState();

    // Set the highlight ticker before redrawing
    _scatterHighlightTicker = ticker;

    // Redraw scatter
    var el = document.getElementById('scatter-chart');
    if (el) el.innerHTML = '';
    if (_chartData && _chartData.companies) drawScatterChart(_chartData.companies);

    // Scroll to scatter section
    var section = document.getElementById('scatter-chart-panel');
    if (section) {
        var headerHeight = typeof getStickyOffset === 'function' ? getStickyOffset() : 80;
        var sectionTop = section.getBoundingClientRect().top + window.scrollY - headerHeight - 12;
        window.scrollTo({ top: sectionTop, behavior: typeof getScrollBehavior === 'function' ? getScrollBehavior() : 'smooth' });
    }

    if (typeof announce === 'function') {
        announce('Scatter chart: highlighting ' + ticker + (presetX ? ' on ' + (presetX === '_gerScore' ? 'GER' : presetX) + ' vs ' + (presetY === 'total_compensation' ? 'Pay' : presetY) : ''));
    }
};

/**
 * After scatter dots render, check for pending highlight ticker and draw a pulsing ring.
 * Called at the end of drawScatterChart.
 */
function _applyScatterHighlight() {
    if (!_scatterHighlightTicker) return;
    var ticker = _scatterHighlightTicker;
    _scatterHighlightTicker = null; // consume

    // Clear any previous highlight timer
    if (_scatterHighlightTimer) { clearTimeout(_scatterHighlightTimer); _scatterHighlightTimer = null; }

    var container = document.getElementById('scatter-chart');
    if (!container) return;
    var svg = d3.select(container).select('svg');
    if (svg.empty()) return;

    // Find the matching dot
    var matchDot = null;
    svg.selectAll('.scatter-dot, .scatter-dot-sector, .scatter-dot-bg').each(function(d) {
        if (d && d.ticker === ticker) {
            matchDot = d3.select(this);
        }
    });

    if (!matchDot) return;

    var cx = parseFloat(matchDot.attr('cx'));
    var cy = parseFloat(matchDot.attr('cy'));
    var cr = parseFloat(matchDot.attr('r')) || 6;

    // Get the inner <g> that holds the dots (first child g of the svg)
    var g = svg.select('g');
    if (g.empty()) g = svg;

    // Add highlight ring with pulsing animation
    var ringGroup = g.append('g').attr('class', 'scatter-highlight-ring');

    // Outer pulse ring
    ringGroup.append('circle')
        .attr('cx', cx)
        .attr('cy', cy)
        .attr('r', cr + 8)
        .attr('fill', 'none')
        .attr('stroke', '#ef476f')
        .attr('stroke-width', 2.5)
        .attr('opacity', 0.9)
        .attr('class', 'scatter-highlight-pulse');

    // Inner static ring
    ringGroup.append('circle')
        .attr('cx', cx)
        .attr('cy', cy)
        .attr('r', cr + 4)
        .attr('fill', 'none')
        .attr('stroke', '#ef476f')
        .attr('stroke-width', 1.5)
        .attr('opacity', 0.6);

    // Ticker label above dot
    ringGroup.append('text')
        .attr('x', cx)
        .attr('y', cy - cr - 12)
        .attr('text-anchor', 'middle')
        .attr('fill', '#ef476f')
        .attr('font-size', '12px')
        .attr('font-weight', '700')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(ticker);

    // Bring the matched dot to front
    matchDot.raise();
    matchDot.attr('stroke', '#ef476f').attr('stroke-width', 2).attr('opacity', 1);

    // Auto-remove highlight after 6 seconds
    _scatterHighlightTimer = setTimeout(function() {
        ringGroup.transition().duration(800).style('opacity', 0).remove();
    }, 6000);
}
