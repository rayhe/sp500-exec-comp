/* === Peer Network Force-Directed Graph (D3 + Canvas) === */

var SECTOR_COLORS = {
    'Information Technology': '#00b4d8',
    'Communication Services': '#06d6a0',
    'Consumer Discretionary': '#ef476f',
    'Health Care': '#ffd166',
    'Financials': '#a78bfa',
    'Consumer Staples': '#fb923c',
    'Industrials': '#94a3b8',
    'Real Estate': '#f472b6',
    'Energy': '#34d399',
    'Materials': '#f9a8d4',
    'Utilities': '#67e8f9'
};

function initNetwork(peerData) {
    var container = document.getElementById('network-graph');
    container.innerHTML = '';

    var dpr = window.devicePixelRatio || 1;
    var rect = container.getBoundingClientRect();
    var width = rect.width;
    var height = rect.height;

    var canvas = document.createElement('canvas');
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    container.appendChild(canvas);

    var ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    var nodes = peerData.nodes.map(function(n) { return Object.assign({}, n); });
    var allEdges = peerData.edges.slice();
    var currentFilter = 'all';
    var hoveredNode = null;
    var dragNode = null;
    var transform = d3.zoomIdentity;

    var nodeMap = {};
    nodes.forEach(function(n) { nodeMap[n.ticker] = n; });

    // Precompute adjacency for fast hover lookups
    var adjacency = {};
    nodes.forEach(function(n) { adjacency[n.ticker] = { in: [], out: [] }; });
    allEdges.forEach(function(e) {
        if (adjacency[e.source]) adjacency[e.source].out.push(e.target);
        if (adjacency[e.target]) adjacency[e.target].in.push(e.source);
    });

    // Node radius based on in-degree only
    function getRadius(node) {
        var inDeg = node.in_degree || 0;
        return Math.max(4, Math.min(32, 3 + Math.sqrt(inDeg) * 3.5));
    }

    // Label threshold — only show for high in-degree nodes when zoomed out
    function shouldShowLabel(node, scale) {
        if (node === hoveredNode) return true;
        if (scale > 1.8) return true;
        if (scale > 1.2) return node.in_degree >= 5;
        if (scale > 0.8) return node.in_degree >= 15;
        return node.in_degree >= 25;
    }

    function getFilteredEdges() {
        if (currentFilter === 'all') return allEdges;
        return allEdges.filter(function(e) { return e.group_type === currentFilter; });
    }

    // Quadtree for fast mouse hit detection
    var quadtree;
    function rebuildQuadtree() {
        quadtree = d3.quadtree()
            .x(function(d) { return d.x; })
            .y(function(d) { return d.y; })
            .addAll(nodes);
    }

    function findNode(mx, my) {
        var pt = transform.invert([mx, my]);
        var px = pt[0], py = pt[1];
        var closest = null;
        var closestDist = Infinity;
        if (!quadtree) return null;
        quadtree.visit(function(quad, x0, y0, x1, y1) {
            if (quad.data) {
                var d = quad.data;
                var r = getRadius(d) / transform.k + 4;
                var dx = px - d.x, dy = py - d.y;
                var dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < r && dist < closestDist) {
                    closest = d;
                    closestDist = dist;
                }
            }
            // Prune: skip quadrant if too far
            var near = px - 40 / transform.k;
            var far = px + 40 / transform.k;
            var top = py - 40 / transform.k;
            var bottom = py + 40 / transform.k;
            return x0 > far || x1 < near || y0 > bottom || y1 < top;
        });
        return closest;
    }

    // Draw
    function draw() {
        ctx.save();
        ctx.clearRect(0, 0, width, height);
        ctx.translate(transform.x, transform.y);
        ctx.scale(transform.k, transform.k);

        var edges = getFilteredEdges();
        var scale = transform.k;

        // Connected set for hover highlighting
        var connectedSet = null;
        if (hoveredNode) {
            connectedSet = new Set();
            connectedSet.add(hoveredNode.ticker);
            var adj = adjacency[hoveredNode.ticker];
            if (adj) {
                adj.in.forEach(function(t) { connectedSet.add(t); });
                adj.out.forEach(function(t) { connectedSet.add(t); });
            }
        }

        // Edges — draw only visible ones, batch by opacity
        if (hoveredNode) {
            // Dim pass
            ctx.strokeStyle = 'rgba(255,255,255,0.02)';
            ctx.lineWidth = 0.5 / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var s = nodeMap[e.source] || nodeMap[e.source.ticker];
                var t = nodeMap[e.target] || nodeMap[e.target.ticker];
                if (!s || !t) return;
                if (e.source === hoveredNode.ticker || e.target === hoveredNode.ticker ||
                    (e.source.ticker && e.source.ticker === hoveredNode.ticker) ||
                    (e.target.ticker && e.target.ticker === hoveredNode.ticker)) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();

            // Highlight pass
            ctx.strokeStyle = 'rgba(0,180,216,0.6)';
            ctx.lineWidth = 1.5 / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (src !== hoveredNode.ticker && tgt !== hoveredNode.ticker) return;
                var s = nodeMap[src];
                var t = nodeMap[tgt];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();
        } else {
            // Default — batch all edges in one path
            ctx.strokeStyle = 'rgba(255,255,255,0.06)';
            ctx.lineWidth = 0.5 / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var s = nodeMap[e.source] || nodeMap[e.source.ticker];
                var t = nodeMap[e.target] || nodeMap[e.target.ticker];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();
        }

        // Nodes
        nodes.forEach(function(d) {
            var r = getRadius(d);
            var color = SECTOR_COLORS[d.sector] || '#94a3b8';
            var alpha = 0.85;

            if (hoveredNode) {
                if (d === hoveredNode) {
                    alpha = 1;
                } else if (connectedSet && connectedSet.has(d.ticker)) {
                    alpha = 0.9;
                } else {
                    alpha = 0.15;
                }
            }

            ctx.beginPath();
            ctx.arc(d.x, d.y, r, 0, 2 * Math.PI);
            ctx.fillStyle = hexToRGBA(color, alpha);
            ctx.fill();

            if (d === hoveredNode) {
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 2 / scale;
                ctx.stroke();
            }
        });

        // Labels
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        var fontSize = Math.max(9, Math.min(12, 11 / scale));
        ctx.font = '600 ' + fontSize + 'px Inter, system-ui, sans-serif';

        nodes.forEach(function(d) {
            if (!shouldShowLabel(d, scale)) return;
            if (hoveredNode && !connectedSet.has(d.ticker)) return;
            var r = getRadius(d);
            ctx.fillStyle = d === hoveredNode ? '#fff' : 'rgba(255,255,255,0.7)';
            ctx.fillText(d.ticker, d.x, d.y + r + 3);
        });

        ctx.restore();
    }

    function hexToRGBA(hex, alpha) {
        var r = parseInt(hex.slice(1, 3), 16);
        var g = parseInt(hex.slice(3, 5), 16);
        var b = parseInt(hex.slice(5, 7), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    // Tooltip
    var tooltip = document.getElementById('network-tooltip');
    function showTooltip(mx, my, d) {
        var html = '<div class="tt-title">' + d.ticker + ' — ' + d.name + '</div>';
        html += '<div class="tt-row"><span class="tt-label">Sector</span><span class="tt-value">' + d.sector + '</span></div>';
        html += '<div class="tt-row"><span class="tt-label">Selected by</span><span class="tt-value">' + d.in_degree + ' companies</span></div>';
        html += '<div class="tt-row"><span class="tt-label">Selects</span><span class="tt-value">' + d.out_degree + ' peers</span></div>';
        html += '<div class="tt-row"><span class="tt-label">Market cap</span><span class="tt-value">' + d.market_cap_tier + '</span></div>';
        tooltip.innerHTML = html;
        tooltip.classList.add('visible');
        tooltip.style.left = (mx + 12) + 'px';
        tooltip.style.top = (my - 10) + 'px';
    }
    function hideTooltip() {
        tooltip.classList.remove('visible');
    }

    // Force simulation — tuned for 500+ nodes
    var edges = getFilteredEdges();
    var links = edges.map(function(e) {
        return { source: e.source, target: e.target, group_type: e.group_type };
    });

    var simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(function(d) { return d.ticker; }).distance(60).strength(0.15))
        .force('charge', d3.forceManyBody().strength(-80).distanceMax(300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(function(d) { return getRadius(d) + 2; }).iterations(1))
        .alphaDecay(0.03)
        .velocityDecay(0.4)
        .on('tick', function() {
            rebuildQuadtree();
            draw();
        });

    // Cool down faster — stop ticking after layout stabilizes
    simulation.alpha(0.8);

    // Zoom + pan
    var zoom = d3.zoom()
        .scaleExtent([0.2, 6])
        .on('zoom', function(event) {
            transform = event.transform;
            draw();
        });

    d3.select(canvas)
        .call(zoom)
        .on('dblclick.zoom', null);

    // Mouse interaction
    canvas.addEventListener('mousemove', function(event) {
        var rect = canvas.getBoundingClientRect();
        var mx = event.clientX - rect.left;
        var my = event.clientY - rect.top;

        if (dragNode) {
            var pt = transform.invert([mx, my]);
            dragNode.fx = pt[0];
            dragNode.fy = pt[1];
            return;
        }

        var found = findNode(mx, my);
        if (found !== hoveredNode) {
            hoveredNode = found;
            canvas.style.cursor = found ? 'pointer' : 'grab';
            if (found) {
                showTooltip(event.clientX, event.clientY, found);
            } else {
                hideTooltip();
            }
            draw();
        } else if (found) {
            tooltip.style.left = (event.clientX + 12) + 'px';
            tooltip.style.top = (event.clientY - 10) + 'px';
        }
    });

    canvas.addEventListener('mousedown', function(event) {
        var rect = canvas.getBoundingClientRect();
        var mx = event.clientX - rect.left;
        var my = event.clientY - rect.top;
        var found = findNode(mx, my);
        if (found) {
            event.stopPropagation();
            dragNode = found;
            var pt = transform.invert([mx, my]);
            dragNode.fx = pt[0];
            dragNode.fy = pt[1];
            simulation.alphaTarget(0.3).restart();
        }
    });

    canvas.addEventListener('mouseup', function() {
        if (dragNode) {
            dragNode.fx = null;
            dragNode.fy = null;
            dragNode = null;
            simulation.alphaTarget(0);
        }
    });

    canvas.addEventListener('mouseleave', function() {
        hoveredNode = null;
        hideTooltip();
        if (dragNode) {
            dragNode.fx = null;
            dragNode.fy = null;
            dragNode = null;
            simulation.alphaTarget(0);
        }
        draw();
    });

    // Touch support for mobile
    canvas.addEventListener('touchstart', function(event) {
        if (event.touches.length === 1) {
            var touch = event.touches[0];
            var rect = canvas.getBoundingClientRect();
            var mx = touch.clientX - rect.left;
            var my = touch.clientY - rect.top;
            var found = findNode(mx, my);
            if (found) {
                hoveredNode = found;
                showTooltip(touch.clientX, touch.clientY, found);
                draw();
            }
        }
    }, { passive: true });

    canvas.addEventListener('touchend', function() {
        hoveredNode = null;
        hideTooltip();
        draw();
    }, { passive: true });

    // Filter buttons
    document.querySelectorAll('.control-btn[data-filter]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.control-btn[data-filter]').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;

            // Rebuild links for simulation
            var edges = getFilteredEdges();
            var newLinks = edges.map(function(e) {
                return { source: e.source, target: e.target, group_type: e.group_type };
            });
            simulation.force('link').links(newLinks);
            simulation.alpha(0.5).restart();
        });
    });

    // Handle resize
    var resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            rect = container.getBoundingClientRect();
            width = rect.width;
            height = rect.height;
            canvas.style.width = width + 'px';
            canvas.style.height = height + 'px';
            canvas.width = width * dpr;
            canvas.height = height * dpr;
            ctx = canvas.getContext('2d');
            ctx.scale(dpr, dpr);
            simulation.force('center', d3.forceCenter(width / 2, height / 2));
            simulation.alpha(0.3).restart();
        }, 200);
    });
}
