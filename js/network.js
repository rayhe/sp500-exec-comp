/* === Peer Network Force-Directed Graph (D3.js v7) === */

var SECTOR_COLORS = {
    'Information Technology': '#00b4d8',
    'Communication Services': '#06d6a0',
    'Consumer Discretionary': '#ef476f',
    'Health Care': '#ffd166',
    'Financials': '#a78bfa',
    'Consumer Staples': '#fb923c',
    'Industrials': '#94a3b8',
    'Real Estate': '#f472b6'
};

function initNetwork(peerData) {
    var container = document.getElementById('network-graph');
    var width = container.clientWidth;
    var height = container.clientHeight;

    // Clear previous
    container.innerHTML = '';

    var svg = d3.select('#network-graph')
        .append('svg')
        .attr('viewBox', '0 0 ' + width + ' ' + height)
        .attr('preserveAspectRatio', 'xMidYMid meet');

    // Arrow marker
    svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-4L10,0L0,4')
        .attr('fill', 'rgba(255,255,255,0.2)');

    var nodes = peerData.nodes.map(function(n) {
        return Object.assign({}, n);
    });
    var allEdges = peerData.edges.slice();
    var currentFilter = 'all';

    var nodeMap = {};
    nodes.forEach(function(n) { nodeMap[n.ticker] = n; });

    function getFilteredEdges() {
        if (currentFilter === 'all') return allEdges;
        return allEdges.filter(function(e) { return e.group_type === currentFilter; });
    }

    function getRadius(node) {
        var inDeg = node.in_degree || 0;
        var outDeg = node.out_degree || 0;
        var total = inDeg + outDeg;
        return Math.max(8, Math.min(28, 6 + total * 1.2));
    }

    var tooltip = document.getElementById('network-tooltip');

    function showTooltip(event, d) {
        var html = '<div class="tt-title">' + d.ticker + ' — ' + d.name + '</div>';
        html += '<div class="tt-row"><span class="tt-label">Sector</span><span class="tt-value">' + d.sector + '</span></div>';
        html += '<div class="tt-row"><span class="tt-label">Selected by</span><span class="tt-value">' + d.in_degree + ' companies</span></div>';
        html += '<div class="tt-row"><span class="tt-label">Selects</span><span class="tt-value">' + d.out_degree + ' peers</span></div>';
        html += '<div class="tt-row"><span class="tt-label">Market cap</span><span class="tt-value">' + d.market_cap_tier + '</span></div>';
        tooltip.innerHTML = html;
        tooltip.classList.add('visible');
        tooltip.style.left = (event.clientX + 12) + 'px';
        tooltip.style.top = (event.clientY - 10) + 'px';
    }

    function hideTooltip() {
        tooltip.classList.remove('visible');
    }

    function render() {
        var edges = getFilteredEdges();
        var links = edges.map(function(e) {
            return {
                source: e.source,
                target: e.target,
                group_type: e.group_type
            };
        });

        // Clear
        svg.selectAll('g').remove();

        var linkG = svg.append('g');
        var nodeG = svg.append('g');
        var labelG = svg.append('g');

        var link = linkG.selectAll('line')
            .data(links)
            .join('line')
            .attr('class', function(d) { return 'link ' + d.group_type; })
            .attr('marker-end', 'url(#arrowhead)');

        var node = nodeG.selectAll('circle')
            .data(nodes, function(d) { return d.ticker; })
            .join('circle')
            .attr('r', function(d) { return getRadius(d); })
            .attr('fill', function(d) { return SECTOR_COLORS[d.sector] || '#94a3b8'; })
            .attr('fill-opacity', 0.85)
            .attr('stroke', function(d) { return SECTOR_COLORS[d.sector] || '#94a3b8'; })
            .attr('stroke-width', 1.5)
            .attr('stroke-opacity', 0.4)
            .style('cursor', 'pointer')
            .on('mouseover', function(event, d) {
                d3.select(this).attr('fill-opacity', 1).attr('stroke-opacity', 1);
                showTooltip(event, d);
                // Highlight connected links
                link.attr('stroke-opacity', function(l) {
                    return (l.source.ticker || l.source) === d.ticker || (l.target.ticker || l.target) === d.ticker ? 1 : 0.1;
                });
            })
            .on('mousemove', function(event) {
                tooltip.style.left = (event.clientX + 12) + 'px';
                tooltip.style.top = (event.clientY - 10) + 'px';
            })
            .on('mouseout', function() {
                d3.select(this).attr('fill-opacity', 0.85).attr('stroke-opacity', 0.4);
                hideTooltip();
                link.attr('stroke-opacity', null);
            })
            .call(d3.drag()
                .on('start', function(event, d) {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on('drag', function(event, d) {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on('end', function(event, d) {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                })
            );

        var label = labelG.selectAll('text')
            .data(nodes, function(d) { return d.ticker; })
            .join('text')
            .attr('class', 'node-label')
            .attr('dy', function(d) { return getRadius(d) + 12; })
            .text(function(d) { return d.ticker; });

        var simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(function(d) { return d.ticker; }).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(function(d) { return getRadius(d) + 5; }))
            .on('tick', function() {
                link
                    .attr('x1', function(d) { return d.source.x; })
                    .attr('y1', function(d) { return d.source.y; })
                    .attr('x2', function(d) { return d.target.x; })
                    .attr('y2', function(d) { return d.target.y; });
                node
                    .attr('cx', function(d) { return d.x = Math.max(30, Math.min(width - 30, d.x)); })
                    .attr('cy', function(d) { return d.y = Math.max(30, Math.min(height - 30, d.y)); });
                label
                    .attr('x', function(d) { return d.x; })
                    .attr('y', function(d) { return d.y; });
            });
    }

    render();

    // Filter buttons
    document.querySelectorAll('.control-btn[data-filter]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.control-btn[data-filter]').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            render();
        });
    });
}
