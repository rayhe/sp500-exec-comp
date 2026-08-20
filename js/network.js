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

    // Create cluster stats panel inside the container (survives innerHTML wipe)
    var clusterStatsEl = document.createElement('div');
    clusterStatsEl.id = 'network-cluster-stats';
    clusterStatsEl.className = 'network-cluster-stats';
    clusterStatsEl.setAttribute('role', 'complementary');
    clusterStatsEl.setAttribute('aria-label', 'Sector cluster statistics');
    container.appendChild(clusterStatsEl);

    var ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    var nodes = peerData.nodes.map(function(n) { return Object.assign({}, n); });
    var allEdges = peerData.edges.slice();
    var currentFilter = 'all';
    var hoveredNode = null;
    var dragNode = null;
    var transform = d3.zoomIdentity;
    var activeLegendSector = null; // sector legend click-to-filter state
    var activePath = null; // { nodes: [ticker,...], edges: [{source, target},...] } for path finder
    var compHeatmapMode = false; // when true, nodes colored by CEO pay instead of sector
    var prHeatmapMode = false;  // when true, nodes colored by PageRank centrality
    var ccHeatmapMode = false;  // when true, nodes colored by local clustering coefficient

    var nodeMap = {};
    nodes.forEach(function(n) { nodeMap[n.ticker] = n; });

    // Precompute adjacency for fast hover lookups
    var adjacency = {};
    nodes.forEach(function(n) { adjacency[n.ticker] = { in: [], out: [] }; });
    allEdges.forEach(function(e) {
        if (adjacency[e.source]) adjacency[e.source].out.push(e.target);
        if (adjacency[e.target]) adjacency[e.target].in.push(e.source);
    });

    // Precompute adjacency sets for clustering coefficient
    var adjSets = {};
    nodes.forEach(function(n) {
        var adj = adjacency[n.ticker];
        var neighborSet = new Set();
        adj.in.forEach(function(t) { neighborSet.add(t); });
        adj.out.forEach(function(t) { neighborSet.add(t); });
        adjSets[n.ticker] = neighborSet;
    });

    // Precompute local clustering coefficient for each node
    // C(v) = number of edges among v's neighbors / (k * (k-1)) for directed graph
    var clusteringCoeff = {};
    nodes.forEach(function(n) {
        var neighbors = adjSets[n.ticker];
        var k = neighbors.size;
        if (k < 2) { clusteringCoeff[n.ticker] = 0; return; }
        var edgesAmongNeighbors = 0;
        neighbors.forEach(function(a) {
            var aAdj = adjSets[a];
            if (!aAdj) return;
            neighbors.forEach(function(b) {
                if (a !== b && aAdj.has(b)) edgesAmongNeighbors++;
            });
        });
        clusteringCoeff[n.ticker] = edgesAmongNeighbors / (k * (k - 1));
    });

    // Compute global average clustering coefficient
    var ccSum = 0, ccCount = 0;
    nodes.forEach(function(n) {
        if (adjSets[n.ticker].size >= 2) {
            ccSum += clusteringCoeff[n.ticker];
            ccCount++;
        }
    });
    var globalAvgCC = ccCount > 0 ? ccSum / ccCount : 0;

    // Compute max clustering coefficient for heatmap normalization
    var maxCC = 0;
    nodes.forEach(function(n) {
        if (adjSets[n.ticker].size >= 2 && clusteringCoeff[n.ticker] > maxCC) {
            maxCC = clusteringCoeff[n.ticker];
        }
    });

    // Precompute reciprocal edge count for each node
    var reciprocalCount = {};
    nodes.forEach(function(n) {
        var adj = adjacency[n.ticker];
        var count = 0;
        adj.out.forEach(function(t) {
            if (adj.in.indexOf(t) >= 0) count++;
        });
        reciprocalCount[n.ticker] = count;
    });

    // === Global Network Statistics (always-visible summary bar) ===
    function renderGlobalStats() {
        var el = document.getElementById('network-global-stats');
        if (!el) return;

        var totalNodes = nodes.length;
        var totalEdges = allEdges.length;
        var density = totalNodes > 1 ? (totalEdges / (totalNodes * (totalNodes - 1))) * 100 : 0;

        // Total reciprocal (mutual) edge pairs
        var mutualPairs = 0;
        nodes.forEach(function(n) { mutualPairs += reciprocalCount[n.ticker] || 0; });
        mutualPairs = Math.round(mutualPairs / 2);

        // Average degree (in-degree)
        var degSum = 0;
        nodes.forEach(function(n) { degSum += (n.in_degree || 0); });
        var avgDegree = totalNodes > 0 ? degSum / totalNodes : 0;

        function fmt(n) { return n.toLocaleString(); }

        var stats = [
            { label: 'Nodes', value: fmt(totalNodes) },
            { label: 'Edges', value: fmt(totalEdges) },
            { label: 'Density', value: density.toFixed(2) + '%' },
            { label: 'Avg Clustering', value: (globalAvgCC * 100).toFixed(1) + '%' },
            { label: 'Mutual Pairs', value: fmt(mutualPairs) },
            { label: 'Avg Degree', value: avgDegree.toFixed(1) }
        ];

        var html = '';
        stats.forEach(function(s) {
            html += '<span class="ngs-stat"><span class="ngs-label">' + s.label + '</span> <span class="ngs-value">' + s.value + '</span></span>';
        });
        el.innerHTML = html;
    }
    renderGlobalStats();

    // Node radius based on in-degree — area-proportional scaling
    // Range: 4px (0 peers) to 60px (max ~194 peers)
    // Uses area-proportional mapping so visual size reflects magnitude
    var maxInDegree = 1;
    nodes.forEach(function(n) { if ((n.in_degree || 0) > maxInDegree) maxInDegree = n.in_degree; });
    function getRadius(node) {
        if (ccHeatmapMode) {
            // In CC heatmap mode, size by clustering coefficient
            var cc = clusteringCoeff[node.ticker];
            var neighbors = adjSets[node.ticker] ? adjSets[node.ticker].size : 0;
            if (neighbors < 2) return 5; // insufficient neighbors
            if (maxCC <= 0) return 8;
            var t = cc / maxCC;
            var minR = 5, maxR = 40;
            var minA = minR * minR;
            var maxA = maxR * maxR;
            return Math.sqrt(minA + t * (maxA - minA));
        }
        var inDeg = node.in_degree || 0;
        if (inDeg === 0) return 4;
        // Normalize to 0-1, then map to area range [minA, maxA]
        var t = inDeg / maxInDegree;
        var minR = 5, maxR = 55;
        // Area-proportional: r = sqrt(lerp(minA, maxA, t))
        var minA = minR * minR;
        var maxA = maxR * maxR;
        return Math.sqrt(minA + t * (maxA - minA));
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

        // Theme-aware colors for canvas
        var _dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
        var _hiContrast = window.matchMedia && window.matchMedia('(prefers-contrast: high)').matches;

        var labelColor = _dark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.65)';
        var labelHoverColor = _dark ? '#fff' : '#000';
        var nodeHoverStroke = _dark ? '#fff' : '#000';
        var edgeDimColor = _dark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.03)';
        var edgeSectorDimColor = _dark ? 'rgba(255,255,255,0.015)' : 'rgba(0,0,0,0.025)';

        // High-contrast overrides — stronger edges, labels, and node strokes
        if (_hiContrast) {
            labelColor = _dark ? 'rgba(255,255,255,0.92)' : 'rgba(0,0,0,0.88)';
            edgeDimColor = _dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)';
            edgeSectorDimColor = _dark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.06)';
        }

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

        // Build sector node set if legend sector is active
        var sectorNodeSet = null;
        if (activeLegendSector) {
            sectorNodeSet = new Set();
            nodes.forEach(function(n) {
                if (n.sector === activeLegendSector) sectorNodeSet.add(n.ticker);
            });
        }

        // Edges — draw only visible ones, batch by opacity
        if (hoveredNode) {
            // Dim pass
            ctx.strokeStyle = edgeDimColor;
            ctx.lineWidth = (_hiContrast ? 0.7 : 0.5) / scale;
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

            // Highlight pass — directional arrows with inbound/outbound color coding
            // Outbound (hovered node selects these peers): cyan
            // Inbound  (these companies select hovered node): green
            var outColor = _hiContrast ? 'rgba(0,180,216,0.85)' : 'rgba(0,180,216,0.6)';
            var inColor  = _hiContrast ? 'rgba(6,214,160,0.85)'  : 'rgba(6,214,160,0.6)';
            var hlLineW  = (_hiContrast ? 2.5 : 1.5) / scale;
            var arrowLen  = Math.max(6, Math.min(14, 10 / scale)); // arrowhead size

            // Helper: draw arrowhead triangle at the edge of target node
            function _drawArrow(sx, sy, tx, ty, targetR, color) {
                var dx = tx - sx, dy = ty - sy;
                var dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < targetR * 2 + 2) return; // nodes overlap, skip
                var angle = Math.atan2(dy, dx);
                // Tip sits at target node edge
                var tipX = tx - Math.cos(angle) * targetR;
                var tipY = ty - Math.sin(angle) * targetR;
                ctx.beginPath();
                ctx.moveTo(tipX, tipY);
                ctx.lineTo(tipX - arrowLen * Math.cos(angle - Math.PI / 7),
                           tipY - arrowLen * Math.sin(angle - Math.PI / 7));
                ctx.lineTo(tipX - arrowLen * Math.cos(angle + Math.PI / 7),
                           tipY - arrowLen * Math.sin(angle + Math.PI / 7));
                ctx.closePath();
                ctx.fillStyle = color;
                ctx.fill();
            }

            // Draw outbound edges (hovered → peer)
            ctx.strokeStyle = outColor;
            ctx.lineWidth = hlLineW;
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (src !== hoveredNode.ticker) return;
                var s = nodeMap[src];
                var t = nodeMap[tgt];
                if (!s || !t) return;
                ctx.beginPath();
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
                ctx.stroke();
                _drawArrow(s.x, s.y, t.x, t.y, getRadius(t), outColor);
            });

            // Draw inbound edges (peer → hovered)
            ctx.strokeStyle = inColor;
            ctx.lineWidth = hlLineW;
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (tgt !== hoveredNode.ticker) return;
                var s = nodeMap[src];
                var t = nodeMap[tgt];
                if (!s || !t) return;
                ctx.beginPath();
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
                ctx.stroke();
                _drawArrow(s.x, s.y, t.x, t.y, getRadius(t), inColor);
            });
        } else if (activeLegendSector && sectorNodeSet) {
            // Sector filter active — dim edges not involving the sector
            ctx.strokeStyle = edgeSectorDimColor;
            ctx.lineWidth = (_hiContrast ? 0.5 : 0.3) / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (sectorNodeSet.has(src) || sectorNodeSet.has(tgt)) return;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();

            // Highlight edges touching the active sector
            ctx.strokeStyle = _hiContrast ? 'rgba(0,180,216,0.55)' : 'rgba(0,180,216,0.35)';
            ctx.lineWidth = (_hiContrast ? 1.2 : 0.8) / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (!sectorNodeSet.has(src) && !sectorNodeSet.has(tgt)) return;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();
        } else {
            // Default — differentiate same-sector vs cross-sector edges
            var edgeCrossColor = _dark ? 'rgba(255,255,255,0.035)' : 'rgba(0,0,0,0.05)';
            var edgeSameColor = _dark ? 'rgba(0,180,216,0.1)' : 'rgba(0,120,180,0.12)';
            var edgeCrossWidth = 0.4;
            var edgeSameWidth = 0.7;

            // When path finder is active, dim all background edges further
            if (activePath && activePath.nodes.length >= 2) {
                edgeCrossColor = _dark ? 'rgba(255,255,255,0.012)' : 'rgba(0,0,0,0.015)';
                edgeSameColor = _dark ? 'rgba(0,180,216,0.03)' : 'rgba(0,120,180,0.04)';
                edgeCrossWidth = 0.3;
                edgeSameWidth = 0.4;
            }

            // High-contrast: significantly increase edge visibility
            if (_hiContrast) {
                edgeCrossColor = _dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.12)';
                edgeSameColor = _dark ? 'rgba(0,180,216,0.25)' : 'rgba(0,120,180,0.3)';
                edgeCrossWidth = 0.6;
                edgeSameWidth = 1.0;
            }

            // Cross-sector edges (dimmer, thinner)
            ctx.strokeStyle = edgeCrossColor;
            ctx.lineWidth = edgeCrossWidth / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                if (s.sector && t.sector && s.sector === t.sector) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();

            // Same-sector edges (brighter, slightly thicker, accent-tinted)
            ctx.strokeStyle = edgeSameColor;
            ctx.lineWidth = edgeSameWidth / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                if (!s.sector || !t.sector || s.sector !== t.sector) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();
        }

        // Nodes
        nodes.forEach(function(d) {
            var r = getRadius(d);
            var color = getNodeColor(d.ticker, d.sector);
            var alpha = 0.85;

            if (hoveredNode) {
                if (d === hoveredNode) {
                    alpha = 1;
                } else if (connectedSet && connectedSet.has(d.ticker)) {
                    alpha = 0.9;
                } else {
                    alpha = _hiContrast ? 0.25 : 0.15;
                }
            } else if (activePath && activePath.nodes.length >= 2) {
                // When path is active, dim non-path nodes
                if (activePath.nodes.indexOf(d.ticker) >= 0) {
                    alpha = 1; // path nodes drawn again on top with glow
                } else {
                    alpha = _hiContrast ? 0.12 : 0.08;
                }
            } else if (activeLegendSector && sectorNodeSet) {
                if (sectorNodeSet.has(d.ticker)) {
                    alpha = 1;
                } else {
                    alpha = _hiContrast ? 0.18 : 0.1;
                }
            }

            ctx.beginPath();
            ctx.arc(d.x, d.y, r, 0, 2 * Math.PI);
            ctx.fillStyle = hexToRGBA(color, alpha);
            ctx.fill();

            if (d === hoveredNode) {
                ctx.strokeStyle = nodeHoverStroke;
                ctx.lineWidth = (_hiContrast ? 3 : 2) / scale;
                ctx.stroke();
            } else if (activeLegendSector && sectorNodeSet && sectorNodeSet.has(d.ticker) && !hoveredNode) {
                ctx.strokeStyle = hexToRGBA(color, _hiContrast ? 0.7 : 0.5);
                ctx.lineWidth = (_hiContrast ? 1.5 : 1) / scale;
                ctx.stroke();
            } else if (_hiContrast && alpha > 0.2) {
                // High-contrast: add subtle outline to all visible nodes for separation
                ctx.strokeStyle = _dark ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.25)';
                ctx.lineWidth = 1 / scale;
                ctx.stroke();
            }
        });

        // Cluster sector labels — floating sector names at centroids when zoomed out
        // Provides orientation without requiring users to match colors to the legend
        // When a sector filter is active, show ONLY that sector's label (at full opacity)
        // In heatmap mode: hidden when no sector filter, but show sector label when sector IS filtered
        // (so users know which sector they're viewing in heatmap-filtered mode)
        if (!hoveredNode && ((!compHeatmapMode && !prHeatmapMode && !ccHeatmapMode) || activeLegendSector)) {
            var clusterAlpha = 0;
            var _showFilteredSectorLabel = false;
            if (activeLegendSector) {
                // When sector filter is active, show the filtered sector's label at all zoom levels
                clusterAlpha = 0.85;
                _showFilteredSectorLabel = true;
            } else if (scale <= 0.55) {
                clusterAlpha = 0.9;
            } else if (scale < 1.2) {
                clusterAlpha = 0.9 * (1 - (scale - 0.55) / 0.65);
            }

            if (clusterAlpha > 0.02) {
                // Compute sector centroids from current node positions
                var _cSums = {};
                nodes.forEach(function(n) {
                    if (!n.sector) return;
                    // When filtering by sector, only compute centroid for the active sector
                    if (_showFilteredSectorLabel && n.sector !== activeLegendSector) return;
                    if (!_cSums[n.sector]) _cSums[n.sector] = { x: 0, y: 0, c: 0 };
                    _cSums[n.sector].x += n.x;
                    _cSums[n.sector].y += n.y;
                    _cSums[n.sector].c++;
                });

                var _clusterShort = {
                    'Information Technology': 'Info Tech',
                    'Communication Services': 'Comm Svcs',
                    'Consumer Discretionary': 'Consumer Disc',
                    'Health Care': 'Health Care',
                    'Consumer Staples': 'Staples',
                    'Financials': 'Financials',
                    'Industrials': 'Industrials',
                    'Real Estate': 'Real Estate',
                    'Energy': 'Energy',
                    'Materials': 'Materials',
                    'Utilities': 'Utilities'
                };

                var clusterFontSize = Math.max(13, Math.min(24, _showFilteredSectorLabel ? 18 / scale : 16 / scale));
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.font = (_hiContrast ? '800 ' : '700 ') + clusterFontSize + 'px Inter, system-ui, sans-serif';

                for (var _cs in _cSums) {
                    var _cd = _cSums[_cs];
                    var _cx = _cd.x / _cd.c;
                    var _cy = _cd.y / _cd.c;
                    var _cc = SECTOR_COLORS[_cs] || '#94a3b8';
                    var _cn = _clusterShort[_cs] || _cs;

                    // Text shadow for readability against nodes
                    ctx.shadowColor = _dark ? 'rgba(0,0,0,0.7)' : 'rgba(255,255,255,0.85)';
                    ctx.shadowBlur = (_hiContrast ? 12 : 8) / scale;
                    ctx.fillStyle = hexToRGBA(_cc, _hiContrast ? Math.min(clusterAlpha * 1.3, 1) : clusterAlpha);
                    ctx.fillText(_cn, _cx, _cy);
                }
                // Reset shadow state
                ctx.shadowColor = 'transparent';
                ctx.shadowBlur = 0;
            }
        }

        // === Path Finder Highlight ===
        if (activePath && activePath.nodes.length >= 2 && !hoveredNode) {
            var pathSet = new Set(activePath.nodes);
            var pathEdgeSet = new Set();
            activePath.edges.forEach(function(e) { pathEdgeSet.add(e.source + '>' + e.target); });

            // Dim all non-path nodes
            // (Already drawn above — draw path nodes on top with full opacity + glow)
            activePath.nodes.forEach(function(ticker, idx) {
                var n = nodeMap[ticker];
                if (!n) return;
                var r = getRadius(n);
                var color = getNodeColor(n.ticker, n.sector);

                // Glow ring
                ctx.beginPath();
                ctx.arc(n.x, n.y, r + 4 / scale, 0, 2 * Math.PI);
                ctx.strokeStyle = '#a855f7';
                ctx.lineWidth = 2.5 / scale;
                ctx.stroke();

                // Filled node on top
                ctx.beginPath();
                ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();
                ctx.strokeStyle = '#a855f7';
                ctx.lineWidth = 2 / scale;
                ctx.stroke();

                // Step number badge
                var badgeR = Math.max(6, 8 / scale);
                ctx.beginPath();
                ctx.arc(n.x + r * 0.7, n.y - r * 0.7, badgeR, 0, 2 * Math.PI);
                ctx.fillStyle = '#a855f7';
                ctx.fill();
                ctx.fillStyle = '#fff';
                ctx.font = '600 ' + Math.max(7, 9 / scale) + 'px Inter, system-ui, sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(String(idx + 1), n.x + r * 0.7, n.y - r * 0.7);
            });

            // Draw path edges — distinguish mutual vs one-directional
            activePath.edges.forEach(function(e) {
                var s = nodeMap[e.source];
                var t = nodeMap[e.target];
                if (!s || !t) return;

                // Check if edge is mutual (both companies select each other)
                var adjSrc = adjacency[e.source];
                var isMutual = adjSrc && adjSrc.in.indexOf(e.target) >= 0;

                if (isMutual) {
                    // Mutual edge: gold double-line with glow
                    ctx.save();
                    ctx.shadowColor = 'rgba(255,209,102,0.4)';
                    ctx.shadowBlur = 6 / scale;

                    // Compute perpendicular offset for double-line
                    var dx = t.x - s.x, dy = t.y - s.y;
                    var dist = Math.sqrt(dx * dx + dy * dy);
                    var px = -dy / dist * 1.5 / scale; // perpendicular
                    var py = dx / dist * 1.5 / scale;

                    ctx.beginPath();
                    ctx.moveTo(s.x + px, s.y + py);
                    ctx.lineTo(t.x + px, t.y + py);
                    ctx.strokeStyle = 'rgba(255,209,102,0.85)';
                    ctx.lineWidth = 2.5 / scale;
                    ctx.stroke();

                    ctx.beginPath();
                    ctx.moveTo(s.x - px, s.y - py);
                    ctx.lineTo(t.x - px, t.y - py);
                    ctx.strokeStyle = 'rgba(255,209,102,0.85)';
                    ctx.lineWidth = 2.5 / scale;
                    ctx.stroke();

                    ctx.restore();

                    // Bidirectional arrowheads (both directions)
                    if (dist > 1) {
                        var angle = Math.atan2(dy, dx);
                        var tr = getRadius(t);
                        var sr = getRadius(s);
                        var aLen = Math.max(8, 12 / scale);

                        // Arrow at target
                        var tipX = t.x - Math.cos(angle) * tr;
                        var tipY = t.y - Math.sin(angle) * tr;
                        ctx.beginPath();
                        ctx.moveTo(tipX, tipY);
                        ctx.lineTo(tipX - aLen * Math.cos(angle - Math.PI / 6), tipY - aLen * Math.sin(angle - Math.PI / 6));
                        ctx.lineTo(tipX - aLen * Math.cos(angle + Math.PI / 6), tipY - aLen * Math.sin(angle + Math.PI / 6));
                        ctx.closePath();
                        ctx.fillStyle = 'rgba(255,209,102,0.9)';
                        ctx.fill();

                        // Arrow at source (reverse direction)
                        var rAngle = angle + Math.PI;
                        var rtipX = s.x - Math.cos(rAngle) * sr;
                        var rtipY = s.y - Math.sin(rAngle) * sr;
                        ctx.beginPath();
                        ctx.moveTo(rtipX, rtipY);
                        ctx.lineTo(rtipX - aLen * Math.cos(rAngle - Math.PI / 6), rtipY - aLen * Math.sin(rAngle - Math.PI / 6));
                        ctx.lineTo(rtipX - aLen * Math.cos(rAngle + Math.PI / 6), rtipY - aLen * Math.sin(rAngle + Math.PI / 6));
                        ctx.closePath();
                        ctx.fillStyle = 'rgba(255,209,102,0.9)';
                        ctx.fill();
                    }
                } else {
                    // One-directional edge: purple (existing style)
                    ctx.beginPath();
                    ctx.moveTo(s.x, s.y);
                    ctx.lineTo(t.x, t.y);
                    ctx.strokeStyle = 'rgba(168,85,247,0.7)';
                    ctx.lineWidth = 3 / scale;
                    ctx.stroke();

                    // Arrowhead at target
                    var dx = t.x - s.x, dy = t.y - s.y;
                    var dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist > 1) {
                        var angle = Math.atan2(dy, dx);
                        var tr = getRadius(t);
                        var tipX = t.x - Math.cos(angle) * tr;
                        var tipY = t.y - Math.sin(angle) * tr;
                        var aLen = Math.max(8, 12 / scale);
                        ctx.beginPath();
                        ctx.moveTo(tipX, tipY);
                        ctx.lineTo(tipX - aLen * Math.cos(angle - Math.PI / 6), tipY - aLen * Math.sin(angle - Math.PI / 6));
                        ctx.lineTo(tipX - aLen * Math.cos(angle + Math.PI / 6), tipY - aLen * Math.sin(angle + Math.PI / 6));
                        ctx.closePath();
                        ctx.fillStyle = 'rgba(168,85,247,0.8)';
                        ctx.fill();
                    }
                }
            });

            // Request continuous redraw for animation (throttled)
            if (!activePath._animFrame) {
                activePath._animFrame = true;
                requestAnimationFrame(function() {
                    if (activePath) { activePath._animFrame = false; draw(); }
                });
            }
        }

        // Labels
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        var fontSize = Math.max(9, Math.min(12, 11 / scale));
        ctx.font = (_hiContrast ? '700 ' : '600 ') + fontSize + 'px Inter, system-ui, sans-serif';

        nodes.forEach(function(d) {
            var isPathNode = activePath && activePath.nodes.indexOf(d.ticker) >= 0;
            if (activeLegendSector && sectorNodeSet && !sectorNodeSet.has(d.ticker) && !hoveredNode && !isPathNode) return;
            if (!activeLegendSector && !isPathNode && !shouldShowLabel(d, scale)) return;
            if (hoveredNode && !connectedSet.has(d.ticker)) return;
            // When sector filter is active, show labels for sector nodes based on zoom
            if (activeLegendSector && sectorNodeSet && sectorNodeSet.has(d.ticker) && !hoveredNode) {
                if (!shouldShowLabel(d, scale * 1.5)) return; // more lenient threshold
            }
            var r = getRadius(d);
            ctx.fillStyle = d === hoveredNode ? labelHoverColor : labelColor;
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

    // Build ticker→compensation lookup from global compData
    var _compLookup = {};
    function _buildCompLookup() {
        if (typeof compData !== 'undefined' && compData && compData.companies) {
            compData.companies.forEach(function(c) {
                _compLookup[c.ticker] = {
                    ceo: c.ceo_name || null,
                    total: c.total_compensation || null,
                    ratio: c.pay_ratio || null,
                    worker: c.median_worker_pay || null,
                    sector: c.sector || null
                };
            });
        }
    }
    _buildCompLookup();

    function _fmtComp(val) {
        if (val == null) return '—';
        if (val >= 1e9) return '$' + (val / 1e9).toFixed(1) + 'B';
        if (val >= 1e6) return '$' + (val / 1e6).toFixed(1) + 'M';
        if (val >= 1e3) return '$' + (val / 1e3).toFixed(0) + 'K';
        return '$' + val;
    }

    // Compute peer group comp stats for a node (outbound peers = companies it benchmarks against)
    function _peerCompStats(ticker) {
        var adj = adjacency[ticker];
        if (!adj) return null;
        var peers = adj.out; // outbound = companies this node selected as peers
        if (peers.length === 0) return null;
        var vals = [];
        peers.forEach(function(t) {
            var c = _compLookup[t];
            if (c && c.total != null && c.total > 0) vals.push(c.total);
        });
        if (vals.length === 0) return null;
        vals.sort(function(a, b) { return a - b; });
        var median = vals.length % 2 === 0 ? (vals[vals.length / 2 - 1] + vals[vals.length / 2]) / 2 : vals[Math.floor(vals.length / 2)];
        var min = vals[0];
        var max = vals[vals.length - 1];
        return { median: median, min: min, max: max, count: vals.length, vals: vals };
    }

    // Compute peer group comp stats for INBOUND peers (companies that selected this node)
    function _peerCompStatsInbound(ticker) {
        var adj = adjacency[ticker];
        if (!adj) return null;
        var peers = adj.in; // inbound = companies that selected this node as a peer
        if (peers.length === 0) return null;
        var vals = [];
        peers.forEach(function(t) {
            var c = _compLookup[t];
            if (c && c.total != null && c.total > 0) vals.push(c.total);
        });
        if (vals.length === 0) return null;
        vals.sort(function(a, b) { return a - b; });
        var median = vals.length % 2 === 0 ? (vals[vals.length / 2 - 1] + vals[vals.length / 2]) / 2 : vals[Math.floor(vals.length / 2)];
        var min = vals[0];
        var max = vals[vals.length - 1];
        return { median: median, min: min, max: max, count: vals.length, vals: vals };
    }

    // Compensation heatmap color — log-scale green→yellow→red gradient
    var _compVals = [];
    (function _buildCompScale() {
        if (typeof compData !== 'undefined' && compData && compData.companies) {
            compData.companies.forEach(function(c) {
                if (c.total_compensation && c.total_compensation > 0) _compVals.push(c.total_compensation);
            });
            _compVals.sort(function(a, b) { return a - b; });
        }
    })();
    var _compP10 = _compVals.length > 0 ? _compVals[Math.floor(_compVals.length * 0.1)] : 1e6;
    var _compP90 = _compVals.length > 0 ? _compVals[Math.floor(_compVals.length * 0.9)] : 50e6;
    var _compP25 = _compVals.length > 0 ? _compVals[Math.floor(_compVals.length * 0.25)] : 5e6;
    var _compP50 = _compVals.length > 0 ? _compVals[Math.floor(_compVals.length * 0.50)] : 15e6;
    var _compP75 = _compVals.length > 0 ? _compVals[Math.floor(_compVals.length * 0.75)] : 25e6;

    // Populate heatmap legend ticks with P25/P50/P75 values
    (function _buildHeatmapTicks() {
        var ticksEl = document.getElementById('comp-heatmap-ticks');
        if (!ticksEl || _compVals.length === 0) return;
        var logMin = Math.log(_compP10);
        var logMax = Math.log(_compP90);
        var percentiles = [
            { val: _compP25, label: 'P25' },
            { val: _compP50, label: 'P50' },
            { val: _compP75, label: 'P75' }
        ];
        ticksEl.innerHTML = '';
        percentiles.forEach(function(p) {
            var logVal = Math.log(Math.max(p.val, _compP10));
            var pct = Math.max(0, Math.min(100, ((logVal - logMin) / (logMax - logMin)) * 100));
            var tick = document.createElement('span');
            tick.className = 'comp-heatmap-tick';
            tick.style.left = pct + '%';
            var fmtVal = p.val >= 1e6 ? '$' + (p.val / 1e6).toFixed(0) + 'M' : '$' + (p.val / 1e3).toFixed(0) + 'K';
            tick.textContent = fmtVal;
            tick.title = p.label + ': ' + fmtVal;
            ticksEl.appendChild(tick);
        });
    })();

    function getCompHeatmapColor(ticker) {
        var c = _compLookup[ticker];
        if (!c || c.total == null || c.total <= 0) return '#555';
        var val = c.total;
        // Log-scale normalization between P10 and P90
        var logMin = Math.log(_compP10);
        var logMax = Math.log(_compP90);
        var logVal = Math.log(Math.max(val, _compP10));
        var t = Math.max(0, Math.min(1, (logVal - logMin) / (logMax - logMin)));
        // Green (low) → Yellow (mid) → Red (high)
        var r, g, b;
        if (t < 0.5) {
            var t2 = t * 2;
            r = Math.round(6 + t2 * (255 - 6));
            g = Math.round(214 - t2 * (214 - 209));
            b = Math.round(160 - t2 * (160 - 102));
        } else {
            var t2 = (t - 0.5) * 2;
            r = Math.round(255 - t2 * (255 - 239));
            g = Math.round(209 - t2 * (209 - 71));
            b = Math.round(102 - t2 * (102 - 111));
        }
        return 'rgb(' + r + ',' + g + ',' + b + ')';
    }

    // PageRank heatmap color — blue→cyan→gold gradient
    function getPRHeatmapColor(ticker) {
        if (!window._pageRankLookup) return '#555';
        var pr = window._pageRankLookup[ticker];
        if (!pr) return '#555';
        var t = pr.percentile / 100; // 0–1
        // Blue (low) → Cyan (mid) → Gold (high)
        var r, g, b;
        if (t < 0.5) {
            var t2 = t * 2;
            r = Math.round(30 + t2 * (0 - 30));
            g = Math.round(58 + t2 * (180 - 58));
            b = Math.round(138 + t2 * (216 - 138));
        } else {
            var t2 = (t - 0.5) * 2;
            r = Math.round(0 + t2 * 255);
            g = Math.round(180 + t2 * (209 - 180));
            b = Math.round(216 - t2 * (216 - 102));
        }
        return 'rgb(' + r + ',' + g + ',' + b + ')';
    }

    // Clustering coefficient heatmap color — cyan→gold→green gradient
    // Bridge positions (low CC) are cyan, moderate is gold, dense clusters (high CC) are green
    function getCCHeatmapColor(ticker) {
        var cc = clusteringCoeff[ticker];
        if (cc === undefined || cc === null) return '#555';
        var neighbors = adjSets[ticker] ? adjSets[ticker].size : 0;
        if (neighbors < 2) return '#555'; // not enough neighbors for meaningful CC
        // CC ranges from 0 to ~0.8 in practice; normalize using max observed
        var t = Math.min(cc / (maxCC || 0.01), 1); // 0 (bridge) → 1 (dense cluster)
        var r, g, b;
        if (t < 0.5) {
            // Cyan (bridge) → Gold (moderate)
            var t2 = t * 2;
            r = Math.round(0 + t2 * 255);
            g = Math.round(180 + t2 * (209 - 180));
            b = Math.round(216 - t2 * (216 - 102));
        } else {
            // Gold (moderate) → Green (dense cluster)
            var t2 = (t - 0.5) * 2;
            r = Math.round(255 - t2 * (255 - 6));
            g = Math.round(209 + t2 * (214 - 209));
            b = Math.round(102 - t2 * (102 - 160));
        }
        return 'rgb(' + r + ',' + g + ',' + b + ')';
    }

    // Unified node color resolver: checks heatmap modes first, then sector
    function getNodeColor(ticker, sector) {
        if (ccHeatmapMode) return getCCHeatmapColor(ticker);
        if (prHeatmapMode) return getPRHeatmapColor(ticker);
        if (compHeatmapMode) return getCompHeatmapColor(ticker);
        return SECTOR_COLORS[sector] || '#94a3b8';
    }

    // Tooltip
    var tooltip = document.getElementById('network-tooltip');
    function showTooltip(mx, my, d) {
        // Count same-sector vs cross-sector peers
        var adj = adjacency[d.ticker] || { in: [], out: [] };
        var inSame = 0, inCross = 0, outSame = 0, outCross = 0;
        adj.in.forEach(function(t) {
            var peer = nodeMap[t];
            if (peer && peer.sector && d.sector && peer.sector === d.sector) inSame++;
            else inCross++;
        });
        adj.out.forEach(function(t) {
            var peer = nodeMap[t];
            if (peer && peer.sector && d.sector && peer.sector === d.sector) outSame++;
            else outCross++;
        });
        var inTotal = inSame + inCross;
        var outTotal = outSame + outCross;

        // Get compensation data for this company
        var comp = _compLookup[d.ticker];
        var peerStats = _peerCompStats(d.ticker);
        var inboundStats = _peerCompStatsInbound(d.ticker);

        var html = '<div class="tt-title">' + d.ticker + ' — ' + d.name + '</div>';

        // Compensation section — CEO pay + peer comparison
        if (comp && comp.total != null && comp.total > 0) {
            html += '<div class="tt-comp-section">';
            html += '<div class="tt-row"><span class="tt-label">CEO Pay</span><span class="tt-value tt-comp-value">' + _fmtComp(comp.total) + '</span></div>';
            if (comp.ceo) {
                html += '<div class="tt-comp-ceo">' + comp.ceo + '</div>';
            }
            // Peer group comparison bar
            if (peerStats && peerStats.count >= 2) {
                var pctInGroup;
                var logMin = Math.log(peerStats.min);
                var logMax = Math.log(peerStats.max);
                var logRange = logMax - logMin;
                if (logRange > 0) {
                    pctInGroup = Math.max(0, Math.min(100, ((Math.log(comp.total) - logMin) / logRange) * 100));
                } else {
                    pctInGroup = 50;
                }
                // Determine rank among peers
                var rank = 1;
                peerStats.vals.forEach(function(v) { if (v > comp.total) rank++; });
                // Delta vs peer median
                var deltaVsMedian = ((comp.total - peerStats.median) / peerStats.median * 100);
                var deltaSign = deltaVsMedian >= 0 ? '+' : '';
                var deltaClass = deltaVsMedian >= 10 ? 'tt-delta-high' : deltaVsMedian <= -10 ? 'tt-delta-low' : 'tt-delta-neutral';

                html += '<div class="tt-comp-vs">';
                html += '<span class="tt-comp-vs-label">vs ' + peerStats.count + ' peers</span>';
                html += '<span class="tt-comp-vs-delta ' + deltaClass + '">' + deltaSign + deltaVsMedian.toFixed(0) + '% vs median</span>';
                html += '</div>';
                html += '<div class="tt-comp-bar-wrap">';
                html += '<div class="tt-comp-bar">';
                html += '<div class="tt-comp-bar-median" style="left:50%"></div>';
                html += '<div class="tt-comp-bar-marker" style="left:' + pctInGroup.toFixed(1) + '%"></div>';
                html += '</div>';
                html += '<div class="tt-comp-bar-labels">';
                html += '<span>' + _fmtComp(peerStats.min) + '</span>';
                html += '<span>' + _fmtComp(peerStats.max) + '</span>';
                html += '</div>';
                html += '</div>';
            }
            // Inbound peer comparison — companies that selected THIS company as a peer
            if (inboundStats && inboundStats.count >= 2) {
                var inPctInGroup;
                var inLogMin = Math.log(inboundStats.min);
                var inLogMax = Math.log(inboundStats.max);
                var inLogRange = inLogMax - inLogMin;
                if (inLogRange > 0) {
                    inPctInGroup = Math.max(0, Math.min(100, ((Math.log(comp.total) - inLogMin) / inLogRange) * 100));
                } else {
                    inPctInGroup = 50;
                }
                var inDeltaVsMedian = ((comp.total - inboundStats.median) / inboundStats.median * 100);
                var inDeltaSign = inDeltaVsMedian >= 0 ? '+' : '';
                var inDeltaClass = inDeltaVsMedian >= 10 ? 'tt-delta-high' : inDeltaVsMedian <= -10 ? 'tt-delta-low' : 'tt-delta-neutral';

                html += '<div class="tt-comp-vs tt-comp-inbound">';
                html += '<span class="tt-comp-vs-label">vs ' + inboundStats.count + ' who chose us</span>';
                html += '<span class="tt-comp-vs-delta ' + inDeltaClass + '">' + inDeltaSign + inDeltaVsMedian.toFixed(0) + '%</span>';
                html += '</div>';
                html += '<div class="tt-comp-bar-wrap">';
                html += '<div class="tt-comp-bar tt-comp-bar-inbound">';
                html += '<div class="tt-comp-bar-median" style="left:50%"></div>';
                html += '<div class="tt-comp-bar-marker tt-comp-bar-marker-in" style="left:' + inPctInGroup.toFixed(1) + '%"></div>';
                html += '</div>';
                html += '<div class="tt-comp-bar-labels">';
                html += '<span>' + _fmtComp(inboundStats.min) + '</span>';
                html += '<span>' + _fmtComp(inboundStats.max) + '</span>';
                html += '</div>';
                html += '</div>';
            }
            if (comp.ratio != null && comp.ratio > 0) {
                html += '<div class="tt-row"><span class="tt-label">Pay Ratio</span><span class="tt-value">' + Math.round(comp.ratio) + ':1</span></div>';
            }
            html += '</div>';
        }

        html += '<div class="tt-row"><span class="tt-label">Sector</span><span class="tt-value">' + d.sector + '</span></div>';
        html += '<div class="tt-row"><span class="tt-label"><span class="tt-dir-dot tt-dir-in"></span>Selected by</span><span class="tt-value">' + d.in_degree + ' companies</span></div>';
        if (inTotal > 0) {
            var inSamePct = Math.round(inSame / inTotal * 100);
            html += '<div class="tt-peer-bar"><div class="tt-peer-bar-fill tt-same" style="width:' + inSamePct + '%"></div><div class="tt-peer-bar-fill tt-cross" style="width:' + (100 - inSamePct) + '%"></div></div>';
            html += '<div class="tt-peer-detail"><span class="tt-peer-same">' + inSame + ' same-sector</span><span class="tt-peer-cross">' + inCross + ' cross-sector</span></div>';
        }
        html += '<div class="tt-row"><span class="tt-label"><span class="tt-dir-dot tt-dir-out"></span>Selects</span><span class="tt-value">' + d.out_degree + ' peers</span></div>';
        if (outTotal > 0) {
            var outSamePct = Math.round(outSame / outTotal * 100);
            html += '<div class="tt-peer-bar"><div class="tt-peer-bar-fill tt-same" style="width:' + outSamePct + '%"></div><div class="tt-peer-bar-fill tt-cross" style="width:' + (100 - outSamePct) + '%"></div></div>';
            html += '<div class="tt-peer-detail"><span class="tt-peer-same">' + outSame + ' same-sector</span><span class="tt-peer-cross">' + outCross + ' cross-sector</span></div>';
        }
        html += '<div class="tt-row"><span class="tt-label">Market cap</span><span class="tt-value">' + d.market_cap_tier + '</span></div>';
        // PageRank centrality score
        if (window._pageRankLookup && window._pageRankLookup[d.ticker]) {
            var _prData = window._pageRankLookup[d.ticker];
            var _prPct = Math.round(_prData.percentile);
            var _prScore = Math.round(_prData.score * 10000);
            var _prTier = _prPct >= 99 ? 'P99' : _prPct >= 95 ? 'P95' : _prPct >= 90 ? 'P90' : _prPct >= 75 ? 'P75' : _prPct >= 50 ? 'P50' : _prPct >= 25 ? 'P25' : '<P25';
            var _prCls = _prPct >= 95 ? 'tt-pr-high' : _prPct >= 75 ? 'tt-pr-mid' : 'tt-pr-low';
            html += '<div class="tt-row"><span class="tt-label">PageRank</span><span class="tt-value ' + _prCls + '">' + _prTier + ' <span class="tt-pr-score">(' + _prScore + ')</span></span></div>';
        }
        // Local clustering coefficient — how interconnected this node's peers are
        var cc = clusteringCoeff[d.ticker];
        var totalNeighbors = adjSets[d.ticker] ? adjSets[d.ticker].size : 0;
        if (totalNeighbors >= 2) {
            var ccPct = Math.round(cc * 100);
            var ccCls = ccPct >= 40 ? 'tt-cc-high' : ccPct >= 20 ? 'tt-cc-mid' : 'tt-cc-low';
            var ccLabel = ccPct >= 40 ? 'Dense cluster' : ccPct >= 20 ? 'Moderate' : 'Bridge position';
            html += '<div class="tt-row"><span class="tt-label">Clustering</span><span class="tt-value ' + ccCls + '">' + ccPct + '% <span class="tt-cc-label">' + ccLabel + '</span></span></div>';
        }
        // Reciprocal peer selections
        var rCount = reciprocalCount[d.ticker] || 0;
        if (rCount > 0) {
            html += '<div class="tt-row"><span class="tt-label">Mutual peers</span><span class="tt-value tt-mutual-val">' + rCount + ' ⇄</span></div>';
        }
        html += '<div class="tt-path-actions">';
        html += '<span class="tt-path-btn" data-action="path-from" data-ticker="' + d.ticker + '">Path from here</span>';
        html += '<span class="tt-path-sep">·</span>';
        html += '<span class="tt-path-btn" data-action="path-to" data-ticker="' + d.ticker + '">Path to here</span>';
        html += '</div>';
        html += '<div class="tt-hint">Click for details · Drag to reposition</div>';
        tooltip.innerHTML = html;
        tooltip.classList.add('visible');
        tooltip.style.left = (mx + 12) + 'px';
        tooltip.style.top = (my - 10) + 'px';

        // Attach path action handlers
        tooltip.querySelectorAll('.tt-path-btn').forEach(function(btn) {
            btn.addEventListener('mousedown', function(e) {
                e.preventDefault();
                e.stopPropagation();
                var ticker = btn.getAttribute('data-ticker');
                var action = btn.getAttribute('data-action');
                hideTooltip();
                hoveredNode = null;
                draw();
                if (action === 'path-from') {
                    pfPrefill(ticker, 'from');
                } else if (action === 'path-to') {
                    pfPrefill(ticker, 'to');
                }
            });
        });
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

    // Click vs drag detection — click navigates to detail, drag repositions node
    var _mdStartX = 0, _mdStartY = 0, _mdNode = null, _mdDragged = false;
    var CLICK_THRESHOLD = 5; // px — movement below this is a click, above is a drag

    canvas.addEventListener('mousedown', function(event) {
        var rect = canvas.getBoundingClientRect();
        var mx = event.clientX - rect.left;
        var my = event.clientY - rect.top;
        var found = findNode(mx, my);
        _mdStartX = event.clientX;
        _mdStartY = event.clientY;
        _mdNode = found;
        _mdDragged = false;
        if (found) {
            event.stopPropagation();
            dragNode = found;
            var pt = transform.invert([mx, my]);
            dragNode.fx = pt[0];
            dragNode.fy = pt[1];
            simulation.alphaTarget(0.3).restart();
        }
    });

    canvas.addEventListener('mousemove', function(event) {
        // Track if mouse moved enough to count as a drag
        if (_mdNode && !_mdDragged) {
            var dx = event.clientX - _mdStartX;
            var dy = event.clientY - _mdStartY;
            if (Math.sqrt(dx * dx + dy * dy) > CLICK_THRESHOLD) {
                _mdDragged = true;
            }
        }

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

    canvas.addEventListener('mouseup', function(event) {
        var clickedNode = _mdNode;
        var wasDrag = _mdDragged;

        if (dragNode) {
            dragNode.fx = null;
            dragNode.fy = null;
            dragNode = null;
            simulation.alphaTarget(0);
        }

        // If this was a click (not a drag) on a node, navigate to company detail
        if (clickedNode && !wasDrag && window.findCompanyInTable) {
            hideTooltip();
            window.findCompanyInTable(clickedNode.ticker);
        }

        _mdNode = null;
        _mdDragged = false;
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

    // Long-press touch support for mobile node details
    // Tap = pan/zoom (handled by D3). Hold 400ms on a node = show tooltip.
    var _lpTimer = null;
    var _lpNode = null;
    var _lpActive = false; // true while a long-press tooltip is showing
    var _lpStartX = 0;
    var _lpStartY = 0;
    var LP_DELAY = 400; // ms hold before tooltip fires
    var LP_MOVE_THRESHOLD = 10; // px movement cancels long-press
    var _lpStartTime = 0; // timestamp when long-press began
    var _lpAnimFrame = null; // requestAnimationFrame handle for progress ring

    function cancelLongPress() {
        if (_lpTimer) { clearTimeout(_lpTimer); _lpTimer = null; }
        if (_lpAnimFrame) { cancelAnimationFrame(_lpAnimFrame); _lpAnimFrame = null; }
        _lpNode = null;
        _lpStartTime = 0;
    }

    // Draw a circular progress ring around the long-press target node
    function drawLongPressRing() {
        if (!_lpNode || !_lpStartTime) return;
        // Skip ring animation when user prefers reduced motion
        if (typeof prefersReducedMotion === 'function' && prefersReducedMotion()) return;
        var elapsed = Date.now() - _lpStartTime;
        var progress = Math.min(elapsed / LP_DELAY, 1);
        if (progress >= 1) { _lpAnimFrame = null; return; }

        var t = d3.zoomTransform(canvas);
        var cx = t.applyX(_lpNode.x) * dpr;
        var cy = t.applyY(_lpNode.y) * dpr;
        var baseR = getRadius(_lpNode) * t.k * dpr;
        var ringR = baseR + 6 * dpr;

        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0); // reset to pixel space

        // Background track ring (subtle)
        ctx.beginPath();
        ctx.arc(cx, cy, ringR, 0, 2 * Math.PI);
        ctx.strokeStyle = (typeof isDarkTheme === 'function' ? isDarkTheme() : true) ? 'rgba(0,180,216,0.15)' : 'rgba(0,119,182,0.15)';
        ctx.lineWidth = 3 * dpr;
        ctx.stroke();

        // Progress arc (accent color, fills clockwise from top)
        ctx.beginPath();
        ctx.arc(cx, cy, ringR, -Math.PI / 2, -Math.PI / 2 + progress * 2 * Math.PI);
        ctx.strokeStyle = (typeof isDarkTheme === 'function' ? isDarkTheme() : true) ? 'rgba(0,180,216,0.7)' : 'rgba(0,119,182,0.7)';
        ctx.lineWidth = 3 * dpr;
        ctx.lineCap = 'round';
        ctx.stroke();

        ctx.restore();

        // Continue animation
        _lpAnimFrame = requestAnimationFrame(function() {
            draw(); // triggers full redraw which includes this ring via the hook
        });
    }

    canvas.addEventListener('touchstart', function(event) {
        // Multi-touch (pinch zoom) cancels long-press
        if (event.touches.length !== 1) {
            cancelLongPress();
            return;
        }

        // If a long-press tooltip is already visible, tap on same node navigates to detail
        if (_lpActive) {
            var touch = event.touches[0];
            var rect = canvas.getBoundingClientRect();
            var mx = touch.clientX - rect.left;
            var my = touch.clientY - rect.top;
            var tapped = findNode(mx, my);
            var prevNode = _lpNode; // save before cancelLongPress clears it

            _lpActive = false;
            hoveredNode = null;
            hideTooltip();
            draw();
            cancelLongPress();

            // If tapped the same node that was showing tooltip, navigate to detail
            if (tapped && prevNode && tapped.ticker === prevNode.ticker && window.findCompanyInTable) {
                window.findCompanyInTable(tapped.ticker);
            }
            return;
        }

        var touch = event.touches[0];
        _lpStartX = touch.clientX;
        _lpStartY = touch.clientY;

        var rect = canvas.getBoundingClientRect();
        var mx = touch.clientX - rect.left;
        var my = touch.clientY - rect.top;
        var found = findNode(mx, my);

        if (found) {
            _lpNode = found;
            _lpStartTime = Date.now();
            var capturedX = touch.clientX;
            var capturedY = touch.clientY;
            // Start the progress ring animation (skip animation if reduced motion)
            var _reducedMotion = typeof prefersReducedMotion === 'function' && prefersReducedMotion();
            if (!_reducedMotion) {
                _lpAnimFrame = requestAnimationFrame(function() { draw(); });
            }
            _lpTimer = setTimeout(function() {
                if (_lpNode) {
                    // Stop the progress ring animation
                    if (_lpAnimFrame) { cancelAnimationFrame(_lpAnimFrame); _lpAnimFrame = null; }
                    _lpStartTime = 0;
                    hoveredNode = _lpNode;
                    showTooltip(capturedX, capturedY, _lpNode);
                    _lpActive = true;
                    draw();
                    // Haptic feedback if supported
                    if (navigator.vibrate) navigator.vibrate(30);
                }
                _lpTimer = null;
            }, _reducedMotion ? 100 : LP_DELAY);
        }
    }, { passive: true });

    canvas.addEventListener('touchmove', function(event) {
        if (event.touches.length < 1) return;
        var touch = event.touches[0];
        var dx = touch.clientX - _lpStartX;
        var dy = touch.clientY - _lpStartY;
        var dist = Math.sqrt(dx * dx + dy * dy);

        // Cancel pending long-press if finger moved too far
        if (_lpTimer && dist > LP_MOVE_THRESHOLD) {
            cancelLongPress();
        }

        // Dismiss active tooltip if user starts panning
        if (_lpActive && dist > LP_MOVE_THRESHOLD) {
            _lpActive = false;
            hoveredNode = null;
            hideTooltip();
            draw();
        }
    }, { passive: true });

    canvas.addEventListener('touchend', function() {
        cancelLongPress();
        // Keep tooltip visible after long-press — user dismisses with next tap
        if (!_lpActive) {
            hoveredNode = null;
            hideTooltip();
            draw();
        }
    }, { passive: true });

    canvas.addEventListener('touchcancel', function() {
        cancelLongPress();
        _lpActive = false;
        hoveredNode = null;
        hideTooltip();
        draw();
    }, { passive: true });

    // Check which edge types actually exist in the data
    var edgeTypesPresent = {};
    allEdges.forEach(function(e) {
        edgeTypesPresent[e.group_type || 'primary'] = true;
    });

    // Filter buttons — disable those with no matching data
    document.querySelectorAll('.control-btn[data-filter]').forEach(function(btn) {
        var filterType = btn.dataset.filter;

        // Disable filter buttons for edge types not present in data
        if (filterType !== 'all' && !edgeTypesPresent[filterType]) {
            btn.classList.add('control-btn-disabled');
            btn.setAttribute('disabled', 'true');
            btn.setAttribute('title', 'No ' + filterType + ' peer data available in this dataset');
            btn.setAttribute('aria-disabled', 'true');
            return; // skip adding click handler
        }

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

    /* === Network Search ===
     * Autocomplete dropdown over the peer network graph.
     * Selecting a result zooms + highlights that node.
     */
    var searchInput = document.getElementById('network-search');
    var searchResults = document.getElementById('network-search-results');
    var activeIdx = -1;

    // Extract heatmap dot color from an .nsr-dot element and return as low-opacity background tint
    function _dotBgTint(dotEl) {
        var bg = dotEl.style.background || dotEl.style.backgroundColor || '';
        var m = bg.match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/);
        if (m) return 'rgba(' + m[1] + ',' + m[2] + ',' + m[3] + ',0.18)';
        return '';
    }

    function renderSearchResults(matches) {
        searchResults.innerHTML = '';
        activeIdx = -1;
        if (matches.length === 0) {
            searchResults.classList.remove('visible');
            return;
        }
        matches.forEach(function(n, i) {
            var div = document.createElement('div');
            div.className = 'network-search-result';
            var comp = _compLookup[n.ticker];
            var payHtml = '';
            if (comp && comp.total != null && comp.total > 0) {
                payHtml = '<span class="nsr-pay">' + _fmtComp(comp.total) + '</span>';
            }
            // In heatmap mode: show a colored dot matching the company's heatmap color
            // Outside heatmap: show a sector-colored dot
            var dotColor = getNodeColor(n.ticker, n.sector);
            var dotHtml = '<span class="nsr-dot" style="background:' + dotColor + '"></span>';
            div.innerHTML = dotHtml +
                '<span class="nsr-ticker">' + n.ticker + '</span>' +
                '<span class="nsr-name">' + n.name + '</span>' +
                payHtml +
                '<span class="nsr-sector">' + (n.sector || '') + '</span>';
            div.addEventListener('mousedown', function(e) {
                e.preventDefault(); // prevent blur before click fires
                selectSearchNode(n);
            });
            searchResults.appendChild(div);
        });
        searchResults.classList.add('visible');
    }

    function selectSearchNode(node) {
        searchInput.value = node.ticker + ' — ' + node.name;
        searchResults.classList.remove('visible');

        // ARIA announcement for network node focus
        var adj = adjacency[node.ticker];
        var inCount = adj ? adj.in.length : 0;
        var outCount = adj ? adj.out.length : 0;
        var inSameCount = 0, inCrossCount = 0;
        if (adj) {
            adj.in.forEach(function(t) {
                var peer = nodeMap[t];
                if (peer && peer.sector && node.sector && peer.sector === node.sector) inSameCount++;
                else inCrossCount++;
            });
        }
        if (typeof announce === 'function') {
            var msg = 'Focused on ' + node.name + ' (' + node.ticker + ') in ' + node.sector + '. ' + inCount + ' inbound peers';
            if (inCount > 0) msg += ' (' + inSameCount + ' same-sector, ' + inCrossCount + ' cross-sector)';
            msg += ', ' + outCount + ' outbound peers.';
            announce(msg);
        }

        // Zoom to node
        var scale = 2.5;
        var tx = width / 2 - node.x * scale;
        var ty = height / 2 - node.y * scale;
        var newTransform = d3.zoomIdentity.translate(tx, ty).scale(scale);

        d3.select(canvas)
            .transition()
            .duration(prefersReducedMotion() ? 0 : 750)
            .call(zoom.transform, newTransform);

        // Set as hovered to highlight connections
        hoveredNode = node;
        showTooltip(width / 2 + 12, height / 2 - 10, node);
        draw();
    }

    // Expose global API for cross-section linking (table → network)
    window._redrawNetwork = draw;
    window.focusNetworkNode = function(ticker) {
        var node = nodeMap[ticker];
        if (!node) return false;

        // Scroll to the network section
        var section = document.getElementById('peer-network-section');
        if (section) {
            section.scrollIntoView({ behavior: (typeof getScrollBehavior === 'function' ? getScrollBehavior() : 'smooth'), block: 'start' });
        }

        // Small delay to let scroll settle, then zoom (instant when reduced motion)
        setTimeout(function() {
            selectSearchNode(node);
        }, prefersReducedMotion() ? 50 : 400);

        return true;
    };

    // Expose heatmap toggle for keyboard shortcut
    window.toggleCompHeatmap = function() {
        if (compHeatmapToggle) compHeatmapToggle.click();
    };

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            var q = searchInput.value.trim().toLowerCase();
            if (q.length === 0) {
                searchResults.classList.remove('visible');
                // Clear highlight
                hoveredNode = null;
                hideTooltip();
                draw();
                return;
            }
            // Match against ticker and name
            var matches = nodes.filter(function(n) {
                return n.ticker.toLowerCase().indexOf(q) >= 0 ||
                    n.name.toLowerCase().indexOf(q) >= 0;
            });
            // Sort: exact ticker match first, then starts-with, then contains
            matches.sort(function(a, b) {
                var at = a.ticker.toLowerCase();
                var bt = b.ticker.toLowerCase();
                // Exact ticker match
                if (at === q && bt !== q) return -1;
                if (bt === q && at !== q) return 1;
                // Ticker starts with query
                var aStarts = at.indexOf(q) === 0 ? 0 : 1;
                var bStarts = bt.indexOf(q) === 0 ? 0 : 1;
                if (aStarts !== bStarts) return aStarts - bStarts;
                // Name starts with query
                var an = a.name.toLowerCase();
                var bn = b.name.toLowerCase();
                var anStarts = an.indexOf(q) === 0 ? 0 : 1;
                var bnStarts = bn.indexOf(q) === 0 ? 0 : 1;
                if (anStarts !== bnStarts) return anStarts - bnStarts;
                // Alphabetical by ticker
                return at < bt ? -1 : at > bt ? 1 : 0;
            });
            renderSearchResults(matches.slice(0, 8));
        });

        searchInput.addEventListener('keydown', function(e) {
            var items = searchResults.querySelectorAll('.network-search-result');
            if (items.length === 0) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeIdx = Math.min(activeIdx + 1, items.length - 1);
                items.forEach(function(el, i) {
                    el.classList.toggle('active', i === activeIdx);
                    el.style.backgroundColor = '';
                });
                if ((compHeatmapMode || prHeatmapMode || ccHeatmapMode) && activeIdx >= 0 && activeIdx < items.length) {
                    var dot = items[activeIdx].querySelector('.nsr-dot');
                    if (dot) items[activeIdx].style.backgroundColor = _dotBgTint(dot);
                }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIdx = Math.max(activeIdx - 1, 0);
                items.forEach(function(el, i) {
                    el.classList.toggle('active', i === activeIdx);
                    el.style.backgroundColor = '';
                });
                if ((compHeatmapMode || prHeatmapMode || ccHeatmapMode) && activeIdx >= 0 && activeIdx < items.length) {
                    var dot = items[activeIdx].querySelector('.nsr-dot');
                    if (dot) items[activeIdx].style.backgroundColor = _dotBgTint(dot);
                }
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (activeIdx >= 0 && activeIdx < items.length) {
                    items[activeIdx].dispatchEvent(new MouseEvent('mousedown'));
                } else if (items.length > 0) {
                    items[0].dispatchEvent(new MouseEvent('mousedown'));
                }
            } else if (e.key === 'Escape') {
                searchResults.classList.remove('visible');
                searchInput.blur();
            }
        });

        searchInput.addEventListener('blur', function() {
            // Small delay to allow click events on results to fire
            setTimeout(function() { searchResults.classList.remove('visible'); }, 150);
        });

        searchInput.addEventListener('focus', function() {
            if (searchInput.value.trim().length > 0) {
                searchInput.dispatchEvent(new Event('input'));
            }
        });
    }

    // === Network Legend Click-to-Filter ===
    // Clicking a sector in the legend isolates that sector's nodes
    var legendItems = document.querySelectorAll('.network-legend .legend-item');
    var sectorNameMap = {
        'Info Tech': 'Information Technology',
        'Comm Svcs': 'Communication Services',
        'Consumer Disc': 'Consumer Discretionary',
        'Health Care': 'Health Care',
        'Financials': 'Financials',
        'Consumer Staples': 'Consumer Staples',
        'Industrials': 'Industrials',
        'Energy': 'Energy',
        'Real Estate': 'Real Estate',
        'Materials': 'Materials',
        'Utilities': 'Utilities'
    };

    legendItems.forEach(function(item) {
        item.style.cursor = 'pointer';
        item.addEventListener('click', function() {
            // Get sector name from legend item text
            var text = item.textContent.trim();
            var sectorFull = sectorNameMap[text] || text;

            // Toggle
            if (activeLegendSector === sectorFull) {
                activeLegendSector = null;
            } else {
                activeLegendSector = sectorFull;
            }

            // Update legend item visual state
            legendItems.forEach(function(li) {
                li.classList.remove('legend-active');
                if (activeLegendSector) {
                    var liText = li.textContent.trim();
                    var liSector = sectorNameMap[liText] || liText;
                    if (liSector === activeLegendSector) {
                        li.classList.add('legend-active');
                    } else {
                        li.classList.add('legend-dimmed');
                    }
                }
                if (!activeLegendSector) {
                    li.classList.remove('legend-dimmed');
                }
            });
            if (!activeLegendSector) {
                legendItems.forEach(function(li) { li.classList.remove('legend-dimmed'); });
            }

            updateClusterStats(activeLegendSector);
            _updateHeatmapSectorNote();
            draw();
        });
    });

    // Expose API for clearing sector filter externally
    window.clearNetworkSectorFilter = function() {
        activeLegendSector = null;
        legendItems.forEach(function(li) {
            li.classList.remove('legend-active', 'legend-dimmed');
        });
        updateClusterStats(null);
        _updateHeatmapSectorNote();
        draw();
    };

    // === Compensation Heatmap Mode Toggle ===
    var compHeatmapToggle = document.getElementById('comp-heatmap-toggle');
    var prHeatmapToggle = document.getElementById('pr-heatmap-toggle');
    var sectorLegendEl = document.getElementById('network-legend');
    var compHeatmapLegendEl = document.getElementById('comp-heatmap-legend');
    var prHeatmapLegendEl = document.getElementById('pr-heatmap-legend');
    var ccHeatmapToggle = document.getElementById('cc-heatmap-toggle');
    var ccHeatmapLegendEl = document.getElementById('cc-heatmap-legend');

    if (compHeatmapToggle) {
        compHeatmapToggle.addEventListener('click', function() {
            compHeatmapMode = !compHeatmapMode;
            // Mutual exclusion: turn off PageRank and clustering heatmaps
            if (compHeatmapMode && prHeatmapMode) {
                prHeatmapMode = false;
                if (prHeatmapToggle) prHeatmapToggle.classList.remove('active');
                if (prHeatmapLegendEl) prHeatmapLegendEl.style.display = 'none';
            }
            if (compHeatmapMode && ccHeatmapMode) {
                ccHeatmapMode = false;
                if (ccHeatmapToggle) ccHeatmapToggle.classList.remove('active');
                if (ccHeatmapLegendEl) ccHeatmapLegendEl.style.display = 'none';
            }
            compHeatmapToggle.classList.toggle('active', compHeatmapMode);

            // Show heatmap legend when active; keep sector legend visible for filtering
            if (compHeatmapLegendEl) compHeatmapLegendEl.style.display = compHeatmapMode ? 'flex' : 'none';

            // Update sector note in heatmap legend
            _updateHeatmapSectorNote();

            draw();
            announce(compHeatmapMode ? 'Compensation heatmap enabled' + (activeLegendSector ? ' — filtered to ' + activeLegendSector : '') : 'Sector coloring restored');
            // Refresh cluster stats to show/hide compensation section
            if (activeLegendSector) updateClusterStats(activeLegendSector);
        });
    }

    // PageRank centrality heatmap toggle
    if (prHeatmapToggle) {
        prHeatmapToggle.addEventListener('click', function() {
            prHeatmapMode = !prHeatmapMode;
            // Mutual exclusion: turn off comp and clustering heatmaps
            if (prHeatmapMode && compHeatmapMode) {
                compHeatmapMode = false;
                if (compHeatmapToggle) compHeatmapToggle.classList.remove('active');
                if (compHeatmapLegendEl) compHeatmapLegendEl.style.display = 'none';
            }
            if (prHeatmapMode && ccHeatmapMode) {
                ccHeatmapMode = false;
                if (ccHeatmapToggle) ccHeatmapToggle.classList.remove('active');
                if (ccHeatmapLegendEl) ccHeatmapLegendEl.style.display = 'none';
            }
            prHeatmapToggle.classList.toggle('active', prHeatmapMode);
            if (prHeatmapLegendEl) prHeatmapLegendEl.style.display = prHeatmapMode ? 'flex' : 'none';
            draw();
            announce(prHeatmapMode ? 'PageRank centrality heatmap enabled' : 'Sector coloring restored');
            if (activeLegendSector) updateClusterStats(activeLegendSector);
        });
    }

    // Clustering coefficient heatmap toggle
    if (ccHeatmapToggle) {
        ccHeatmapToggle.addEventListener('click', function() {
            ccHeatmapMode = !ccHeatmapMode;
            // Mutual exclusion: turn off comp and PageRank heatmaps
            if (ccHeatmapMode && compHeatmapMode) {
                compHeatmapMode = false;
                if (compHeatmapToggle) compHeatmapToggle.classList.remove('active');
                if (compHeatmapLegendEl) compHeatmapLegendEl.style.display = 'none';
            }
            if (ccHeatmapMode && prHeatmapMode) {
                prHeatmapMode = false;
                if (prHeatmapToggle) prHeatmapToggle.classList.remove('active');
                if (prHeatmapLegendEl) prHeatmapLegendEl.style.display = 'none';
            }
            ccHeatmapToggle.classList.toggle('active', ccHeatmapMode);
            if (ccHeatmapLegendEl) ccHeatmapLegendEl.style.display = ccHeatmapMode ? 'flex' : 'none';
            // Update node-size legend and recalculate collision force for new radii
            updateNodeSizeLegend();
            simulation.force('collision', d3.forceCollide().radius(function(d) { return getRadius(d) + 2; }).iterations(1));
            simulation.alpha(0.15).restart();
            draw();
            announce(ccHeatmapMode ? 'Clustering coefficient heatmap enabled — cyan = bridge, green = dense cluster' : 'Sector coloring restored');
            if (activeLegendSector) updateClusterStats(activeLegendSector);
        });
    }

    // Update heatmap legend with sector filter context
    function _updateHeatmapSectorNote() {
        if (!compHeatmapLegendEl) return;
        var existingNote = compHeatmapLegendEl.querySelector('.comp-heatmap-sector-note');
        if (existingNote) existingNote.remove();
        if (compHeatmapMode && activeLegendSector) {
            var note = document.createElement('span');
            note.className = 'comp-heatmap-sector-note';
            note.textContent = '· ' + activeLegendSector + ' only';
            compHeatmapLegendEl.appendChild(note);
        }
    }

    // === Cluster Statistics Panel ===
    // Shows aggregate analytics when a sector filter is active

    function updateClusterStats(sectorName) {
        if (!clusterStatsEl) return;
        if (!sectorName) {
            clusterStatsEl.classList.remove('visible');
            return;
        }

        var sectorColor = SECTOR_COLORS[sectorName] || '#94a3b8';

        // Gather sector nodes
        var sectorNodes = nodes.filter(function(n) { return n.sector === sectorName; });
        var sectorTickers = new Set();
        sectorNodes.forEach(function(n) { sectorTickers.add(n.ticker); });
        var nodeCount = sectorNodes.length;

        // Compute edge stats
        var intraEdges = 0;
        var crossEdges = 0;
        allEdges.forEach(function(e) {
            var src = e.source.ticker || e.source;
            var tgt = e.target.ticker || e.target;
            var srcIn = sectorTickers.has(src);
            var tgtIn = sectorTickers.has(tgt);
            if (srcIn && tgtIn) {
                intraEdges++;
            } else if (srcIn || tgtIn) {
                crossEdges++;
            }
        });
        var totalSectorEdges = intraEdges + crossEdges;
        var intraPct = totalSectorEdges > 0 ? Math.round(intraEdges / totalSectorEdges * 100) : 0;

        // Compute connectivity stats
        var inDegrees = [];
        var totalInDeg = 0;
        var totalOutDeg = 0;
        var maxInNode = null, maxInDeg = -1;
        var minInNode = null, minInDeg = Infinity;
        sectorNodes.forEach(function(n) {
            var deg = n.in_degree || 0;
            inDegrees.push(deg);
            totalInDeg += deg;
            totalOutDeg += (n.out_degree || 0);
            if (deg > maxInDeg) { maxInDeg = deg; maxInNode = n; }
            if (deg < minInDeg) { minInDeg = deg; minInNode = n; }
        });
        var avgInDeg = nodeCount > 0 ? (totalInDeg / nodeCount).toFixed(1) : '0';

        // Find top bridge company — most cross-sector inbound connections
        var bridgeScores = [];
        sectorNodes.forEach(function(n) {
            var adj = adjacency[n.ticker] || { in: [], out: [] };
            var crossIn = 0;
            adj.in.forEach(function(t) {
                var peer = nodeMap[t];
                if (peer && peer.sector !== sectorName) crossIn++;
            });
            var crossOut = 0;
            adj.out.forEach(function(t) {
                var peer = nodeMap[t];
                if (peer && peer.sector !== sectorName) crossOut++;
            });
            bridgeScores.push({ node: n, crossTotal: crossIn + crossOut, crossIn: crossIn, crossOut: crossOut });
        });
        bridgeScores.sort(function(a, b) { return b.crossTotal - a.crossTotal; });
        var topBridge = bridgeScores.length > 0 ? bridgeScores[0] : null;

        // Compute density: actual intra-edges / possible intra-edges
        var possibleIntra = nodeCount * (nodeCount - 1); // directed graph
        var density = possibleIntra > 0 ? (intraEdges / possibleIntra * 100).toFixed(1) : '0';

        // Build HTML
        var html = '<div class="cluster-stats-title">' +
            '<span class="cs-dot" style="background:' + sectorColor + '"></span>' +
            sectorName + '</div>';

        html += '<div class="cluster-stats-grid">';
        html += '<div class="cs-stat"><span class="cs-stat-label">Companies</span><span class="cs-stat-value">' + nodeCount + '</span></div>';
        html += '<div class="cs-stat"><span class="cs-stat-label">Avg Inbound</span><span class="cs-stat-value cs-accent">' + avgInDeg + '</span></div>';
        html += '<div class="cs-stat"><span class="cs-stat-label">Total Edges</span><span class="cs-stat-value">' + totalSectorEdges.toLocaleString() + '</span></div>';
        html += '<div class="cs-stat"><span class="cs-stat-label">Density</span><span class="cs-stat-value">' + density + '%</span></div>';

        // Sector-level clustering coefficient
        var sectorCcSum = 0, sectorCcCount = 0;
        sectorNodes.forEach(function(n) {
            if (adjSets[n.ticker] && adjSets[n.ticker].size >= 2) {
                sectorCcSum += (clusteringCoeff[n.ticker] || 0);
                sectorCcCount++;
            }
        });
        var sectorAvgCC = sectorCcCount > 0 ? (sectorCcSum / sectorCcCount * 100).toFixed(1) : '0';
        html += '<div class="cs-stat"><span class="cs-stat-label">Clustering</span><span class="cs-stat-value" title="Average local clustering coefficient — how interconnected peers are within this sector (S&P 500 avg: ' + (globalAvgCC * 100).toFixed(1) + '%)">' + sectorAvgCC + '%</span></div>';

        // Reciprocal edges within sector
        var sectorReciprocal = 0;
        sectorNodes.forEach(function(n) {
            var adj = adjacency[n.ticker];
            adj.out.forEach(function(t) {
                if (sectorTickers.has(t) && adj.in.indexOf(t) >= 0) sectorReciprocal++;
            });
        });
        sectorReciprocal = Math.floor(sectorReciprocal / 2); // each mutual counted twice
        if (sectorReciprocal > 0) {
            html += '<div class="cs-stat"><span class="cs-stat-label">Mutual</span><span class="cs-stat-value" title="Reciprocal peer selections within sector">' + sectorReciprocal + ' ⇄</span></div>';
        }

        html += '</div>';

        // Edge composition bar
        html += '<div class="cs-edge-bar">';
        html += '<div class="cs-edge-bar-fill cs-intra" style="width:' + intraPct + '%"></div>';
        html += '<div class="cs-edge-bar-fill cs-cross" style="width:' + (100 - intraPct) + '%"></div>';
        html += '</div>';
        html += '<div class="cs-edge-labels">';
        html += '<span class="cs-intra-label">' + intraEdges + ' intra-sector (' + intraPct + '%)</span>';
        html += '<span class="cs-cross-label">' + crossEdges + ' cross-sector</span>';
        html += '</div>';

        // Notable nodes
        html += '<div class="cs-node-list">';
        if (maxInNode) {
            html += '<div class="cs-node-row">';
            html += '<span><span class="cs-node-role">Most selected </span><span class="cs-node-ticker" data-ticker="' + maxInNode.ticker + '">' + maxInNode.ticker + '</span></span>';
            html += '<span class="cs-node-degree">' + maxInDeg + ' inbound</span>';
            html += '</div>';
        }
        if (minInNode && minInNode !== maxInNode) {
            html += '<div class="cs-node-row">';
            html += '<span><span class="cs-node-role">Least selected </span><span class="cs-node-ticker" data-ticker="' + minInNode.ticker + '">' + minInNode.ticker + '</span></span>';
            html += '<span class="cs-node-degree">' + minInDeg + ' inbound</span>';
            html += '</div>';
        }
        if (topBridge && topBridge.crossTotal > 0) {
            html += '<div class="cs-node-row">';
            html += '<span><span class="cs-node-role">Top bridge </span><span class="cs-node-ticker" data-ticker="' + topBridge.node.ticker + '">' + topBridge.node.ticker + '</span>';
            html += '<span class="cs-bridge-pill">' + topBridge.crossTotal + ' cross-sector</span></span>';
            html += '</div>';
        }
        html += '</div>';

        // Compensation stats section — shown when heatmap mode is active
        if (compHeatmapMode) {
            var sectorCompVals = [];
            var highestPayNode = null, highestPay = -1;
            var lowestPayNode = null, lowestPay = Infinity;
            sectorNodes.forEach(function(n) {
                var c = _compLookup[n.ticker];
                if (c && c.total != null && c.total > 0) {
                    sectorCompVals.push(c.total);
                    if (c.total > highestPay) { highestPay = c.total; highestPayNode = n; }
                    if (c.total < lowestPay) { lowestPay = c.total; lowestPayNode = n; }
                }
            });
            if (sectorCompVals.length > 1) {
                sectorCompVals.sort(function(a, b) { return a - b; });
                var scMedian = sectorCompVals[Math.floor(sectorCompVals.length / 2)];
                var scP25 = sectorCompVals[Math.floor(sectorCompVals.length * 0.25)];
                var scP75 = sectorCompVals[Math.floor(sectorCompVals.length * 0.75)];
                var scSpread = highestPay / lowestPay;
                // Count aspirational benchmarkers: companies whose outbound peer median > their own pay
                var aspirCount = 0;
                sectorNodes.forEach(function(n) {
                    var c = _compLookup[n.ticker];
                    if (!c || c.total == null || c.total <= 0) return;
                    var stats = _peerCompStats(n.ticker);
                    if (stats && stats.median > c.total * 1.1) aspirCount++;
                });
                html += '<div class="cs-comp-section">';
                html += '<div class="cs-comp-title">💰 Pay Distribution</div>';
                html += '<div class="cluster-stats-grid">';
                html += '<div class="cs-stat"><span class="cs-stat-label">Median CEO</span><span class="cs-stat-value">' + _fmtComp(scMedian) + '</span></div>';
                html += '<div class="cs-stat"><span class="cs-stat-label">P25 – P75</span><span class="cs-stat-value">' + _fmtComp(scP25) + ' – ' + _fmtComp(scP75) + '</span></div>';
                html += '</div>';
                // Highest and lowest paid
                html += '<div class="cs-node-list">';
                if (highestPayNode) {
                    html += '<div class="cs-node-row">';
                    html += '<span><span class="cs-node-role">Highest </span><span class="cs-node-ticker" data-ticker="' + highestPayNode.ticker + '">' + highestPayNode.ticker + '</span></span>';
                    html += '<span class="cs-node-degree" style="color:' + getCompHeatmapColor(highestPayNode.ticker) + '">' + _fmtComp(highestPay) + '</span>';
                    html += '</div>';
                }
                if (lowestPayNode && lowestPayNode !== highestPayNode) {
                    html += '<div class="cs-node-row">';
                    html += '<span><span class="cs-node-role">Lowest </span><span class="cs-node-ticker" data-ticker="' + lowestPayNode.ticker + '">' + lowestPayNode.ticker + '</span></span>';
                    html += '<span class="cs-node-degree" style="color:' + getCompHeatmapColor(lowestPayNode.ticker) + '">' + _fmtComp(lowestPay) + '</span>';
                    html += '</div>';
                }
                if (aspirCount > 0) {
                    html += '<div class="cs-node-row">';
                    html += '<span class="cs-node-role cs-aspir-label">⬆ Aspirational benchmarkers</span>';
                    html += '<span class="cs-node-degree">' + aspirCount + ' / ' + sectorNodes.length + '</span>';
                    html += '</div>';
                }
                html += '</div>';
                html += '<div class="cs-comp-spread">Pay spread: ' + scSpread.toFixed(1) + '×</div>';
                html += '</div>';
            }
        }

        // PageRank centrality stats section — shown when PR heatmap mode is active
        if (prHeatmapMode && window._pageRankLookup) {
            var sectorPRVals = [];
            var highestPRNode = null, highestPR = -1;
            var lowestPRNode = null, lowestPR = Infinity;
            sectorNodes.forEach(function(n) {
                var pr = window._pageRankLookup[n.ticker];
                if (pr) {
                    sectorPRVals.push(pr.percentile);
                    if (pr.percentile > highestPR) { highestPR = pr.percentile; highestPRNode = n; }
                    if (pr.percentile < lowestPR) { lowestPR = pr.percentile; lowestPRNode = n; }
                }
            });
            if (sectorPRVals.length > 1) {
                sectorPRVals.sort(function(a, b) { return a - b; });
                var prMedian = sectorPRVals[Math.floor(sectorPRVals.length / 2)];
                var prP75 = sectorPRVals[Math.floor(sectorPRVals.length * 0.75)];
                var p90Count = sectorPRVals.filter(function(v) { return v >= 90; }).length;
                html += '<div class="cs-comp-section">';
                html += '<div class="cs-comp-title">🕸️ Centrality Distribution</div>';
                html += '<div class="cluster-stats-grid">';
                html += '<div class="cs-stat"><span class="cs-stat-label">Median Pctile</span><span class="cs-stat-value">' + Math.round(prMedian) + '</span></div>';
                html += '<div class="cs-stat"><span class="cs-stat-label">Top 10% (P90+)</span><span class="cs-stat-value cs-accent">' + p90Count + ' / ' + sectorPRVals.length + '</span></div>';
                html += '</div>';
                html += '<div class="cs-node-list">';
                if (highestPRNode) {
                    html += '<div class="cs-node-row">';
                    html += '<span><span class="cs-node-role">Most central </span><span class="cs-node-ticker" data-ticker="' + highestPRNode.ticker + '">' + highestPRNode.ticker + '</span></span>';
                    html += '<span class="cs-node-degree" style="color:' + getPRHeatmapColor(highestPRNode.ticker) + '">P' + Math.round(highestPR) + '</span>';
                    html += '</div>';
                }
                if (lowestPRNode && lowestPRNode !== highestPRNode) {
                    html += '<div class="cs-node-row">';
                    html += '<span><span class="cs-node-role">Least central </span><span class="cs-node-ticker" data-ticker="' + lowestPRNode.ticker + '">' + lowestPRNode.ticker + '</span></span>';
                    html += '<span class="cs-node-degree" style="color:' + getPRHeatmapColor(lowestPRNode.ticker) + '">P' + Math.round(lowestPR) + '</span>';
                    html += '</div>';
                }
                html += '</div>';
                html += '</div>';
            }
        }

        // Clustering coefficient stats section — shown when CC heatmap mode is active
        if (ccHeatmapMode) {
            var sectorCCVals = [];
            var highestCCNode = null, highestCCVal = -1;
            var lowestCCNode = null, lowestCCVal = Infinity;
            var bridgeNodes = [], denseNodes = [];
            sectorNodes.forEach(function(n) {
                var cc = clusteringCoeff[n.ticker];
                var neighbors = adjSets[n.ticker] ? adjSets[n.ticker].size : 0;
                if (neighbors < 2) return;
                sectorCCVals.push(cc);
                if (cc > highestCCVal) { highestCCVal = cc; highestCCNode = n; }
                if (cc < lowestCCVal) { lowestCCVal = cc; lowestCCNode = n; }
                if (cc < 0.2) bridgeNodes.push(n);
                if (cc >= 0.4) denseNodes.push(n);
            });
            if (sectorCCVals.length > 1) {
                sectorCCVals.sort(function(a, b) { return a - b; });
                var ccMedian = sectorCCVals[Math.floor(sectorCCVals.length / 2)];
                html += '<div class="cs-comp-section">';
                html += '<div class="cs-comp-title">🔷 Clustering Distribution</div>';
                html += '<div class="cluster-stats-grid">';
                html += '<div class="cs-stat"><span class="cs-stat-label">Median CC</span><span class="cs-stat-value">' + (ccMedian * 100).toFixed(1) + '%</span></div>';
                html += '<div class="cs-stat"><span class="cs-stat-label">Dense (≥40%)</span><span class="cs-stat-value cs-accent">' + denseNodes.length + ' / ' + sectorCCVals.length + '</span></div>';
                html += '<div class="cs-stat"><span class="cs-stat-label">Bridges (<20%)</span><span class="cs-stat-value">' + bridgeNodes.length + ' / ' + sectorCCVals.length + '</span></div>';
                html += '</div>';
                html += '<div class="cs-node-list">';
                if (highestCCNode) {
                    html += '<div class="cs-node-row">';
                    html += '<span><span class="cs-node-role">Most clustered </span><span class="cs-node-ticker" data-ticker="' + highestCCNode.ticker + '">' + highestCCNode.ticker + '</span></span>';
                    html += '<span class="cs-node-degree" style="color:' + getCCHeatmapColor(highestCCNode.ticker) + '">' + (highestCCVal * 100).toFixed(1) + '%</span>';
                    html += '</div>';
                }
                if (lowestCCNode && lowestCCNode !== highestCCNode) {
                    html += '<div class="cs-node-row">';
                    html += '<span><span class="cs-node-role">Most bridging </span><span class="cs-node-ticker" data-ticker="' + lowestCCNode.ticker + '">' + lowestCCNode.ticker + '</span></span>';
                    html += '<span class="cs-node-degree" style="color:' + getCCHeatmapColor(lowestCCNode.ticker) + '">' + (lowestCCVal * 100).toFixed(1) + '%</span>';
                    html += '</div>';
                }
                html += '</div>';
                html += '</div>';
            }
        }

        clusterStatsEl.innerHTML = html;
        clusterStatsEl.classList.add('visible');

        // Apply light theme class if needed
        var _dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
        clusterStatsEl.classList.toggle('light-theme', !_dark);

        // Attach click handlers to ticker links
        clusterStatsEl.querySelectorAll('.cs-node-ticker').forEach(function(el) {
            el.addEventListener('click', function() {
                var ticker = el.getAttribute('data-ticker');
                var node = nodeMap[ticker];
                if (node) selectSearchNode(node);
            });
        });
    }

    // === Node Size Legend ===
    // Reusable function: updates legend based on ccHeatmapMode
    function updateNodeSizeLegend() {
        var labelEl = document.getElementById('node-size-legend-label');
        var samplesEl = document.getElementById('node-size-legend-samples');
        if (!samplesEl) return;

        if (ccHeatmapMode) {
            // CC mode — show clustering coefficient samples
            if (labelEl) labelEl.textContent = 'Node size = clustering coefficient';

            var lowCC = maxCC * 0.05;
            var midCC = maxCC * 0.5;
            var highCC = maxCC;

            var samples = [
                { cc: lowCC, label: (lowCC * 100).toFixed(0) + '%' },
                { cc: midCC, label: (midCC * 100).toFixed(0) + '%' },
                { cc: highCC, label: (highCC * 100).toFixed(0) + '%' }
            ];

            // Compute radius for each sample using CC sizing logic
            function ccRadius(cc) {
                if (maxCC <= 0) return 8;
                var t = cc / maxCC;
                var minR = 5, maxR = 40;
                var minA = minR * minR;
                var maxA = maxR * maxR;
                return Math.sqrt(minA + t * (maxA - minA));
            }

            var maxR = ccRadius(highCC);
            var scaleFactor = 11 / maxR;

            var html = '';
            samples.forEach(function(s) {
                var r = ccRadius(s.cc) * scaleFactor;
                var d = Math.max(Math.round(r * 2), 6);
                html += '<span class="node-size-sample">' +
                    '<span class="node-size-sample-circle" style="width:' + d + 'px;height:' + d + 'px"></span>' +
                    '<span class="node-size-sample-text">' + s.label + '</span>' +
                    '</span>';
            });
            samplesEl.innerHTML = html;
        } else {
            // Default — in-degree mode
            if (labelEl) labelEl.textContent = 'Node size = inbound peers';

            var lowDeg = 1;
            var midDeg = Math.round(maxInDegree / 2);
            var highDeg = maxInDegree;

            var samples = [
                { deg: lowDeg, label: lowDeg + '' },
                { deg: midDeg, label: midDeg + '' },
                { deg: highDeg, label: highDeg + '' }
            ];

            var maxR = getRadius({ in_degree: highDeg });
            var scaleFactor = 11 / maxR;

            var html = '';
            samples.forEach(function(s) {
                var r = getRadius({ in_degree: s.deg }) * scaleFactor;
                var d = Math.max(Math.round(r * 2), 6);
                html += '<span class="node-size-sample">' +
                    '<span class="node-size-sample-circle" style="width:' + d + 'px;height:' + d + 'px"></span>' +
                    '<span class="node-size-sample-text">' + s.label + '</span>' +
                    '</span>';
            });
            samplesEl.innerHTML = html;
        }
    }
    updateNodeSizeLegend();

    // === Mini-Map (Overview Indicator) ===
    // Small canvas in the bottom-right showing all nodes and the current viewport
    var MM_W = 160, MM_H = 110, MM_PAD = 10;
    var mmCanvas = document.createElement('canvas');
    mmCanvas.className = 'network-minimap';
    mmCanvas.width = MM_W * dpr;
    mmCanvas.height = MM_H * dpr;
    mmCanvas.style.width = MM_W + 'px';
    mmCanvas.style.height = MM_H + 'px';
    container.appendChild(mmCanvas);
    var mmCtx = mmCanvas.getContext('2d');
    mmCtx.scale(dpr, dpr);

    // Compute node extent for mapping world coords → mini-map coords
    var mmExtent = { xMin: Infinity, xMax: -Infinity, yMin: Infinity, yMax: -Infinity };
    var mmExtentReady = false;

    function updateMiniMapExtent() {
        mmExtent.xMin = Infinity; mmExtent.xMax = -Infinity;
        mmExtent.yMin = Infinity; mmExtent.yMax = -Infinity;
        nodes.forEach(function(n) {
            if (n.x < mmExtent.xMin) mmExtent.xMin = n.x;
            if (n.x > mmExtent.xMax) mmExtent.xMax = n.x;
            if (n.y < mmExtent.yMin) mmExtent.yMin = n.y;
            if (n.y > mmExtent.yMax) mmExtent.yMax = n.y;
        });
        // Add padding
        var pw = (mmExtent.xMax - mmExtent.xMin) * 0.08 || 50;
        var ph = (mmExtent.yMax - mmExtent.yMin) * 0.08 || 50;
        mmExtent.xMin -= pw; mmExtent.xMax += pw;
        mmExtent.yMin -= ph; mmExtent.yMax += ph;
        mmExtentReady = true;
    }

    // Map world coord to mini-map pixel
    function mmMapX(wx) {
        return MM_PAD + (wx - mmExtent.xMin) / (mmExtent.xMax - mmExtent.xMin) * (MM_W - 2 * MM_PAD);
    }
    function mmMapY(wy) {
        return MM_PAD + (wy - mmExtent.yMin) / (mmExtent.yMax - mmExtent.yMin) * (MM_H - 2 * MM_PAD);
    }

    function drawMiniMap() {
        if (!mmExtentReady) updateMiniMapExtent();

        var _dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;
        var _mmHiContrast = window.matchMedia && window.matchMedia('(prefers-contrast: high)').matches;
        mmCtx.clearRect(0, 0, MM_W, MM_H);

        // Background
        mmCtx.fillStyle = _dark ? 'rgba(15,15,26,0.88)' : 'rgba(244,245,247,0.92)';
        mmCtx.fillRect(0, 0, MM_W, MM_H);

        // Border — stronger in high-contrast
        mmCtx.strokeStyle = _mmHiContrast
            ? (_dark ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.3)')
            : (_dark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)');
        mmCtx.lineWidth = _mmHiContrast ? 2 : 1;
        mmCtx.strokeRect(0.5, 0.5, MM_W - 1, MM_H - 1);

        // Draw nodes as small dots — slightly larger in high-contrast
        nodes.forEach(function(n) {
            var mx = mmMapX(n.x);
            var my = mmMapY(n.y);
            var color = getNodeColor(n.ticker, n.sector);
            var dotR = Math.max(_mmHiContrast ? 1.5 : 1.2, getRadius(n) / (_mmHiContrast ? 15 : 18));
            mmCtx.beginPath();
            mmCtx.arc(mx, my, dotR, 0, 2 * Math.PI);
            mmCtx.fillStyle = color;
            mmCtx.fill();
        });

        // Draw viewport rectangle
        // The main canvas shows world coords from transform.invert([0,0]) to transform.invert([width, height])
        var topLeft = transform.invert([0, 0]);
        var bottomRight = transform.invert([width, height]);
        var vx1 = mmMapX(topLeft[0]);
        var vy1 = mmMapY(topLeft[1]);
        var vx2 = mmMapX(bottomRight[0]);
        var vy2 = mmMapY(bottomRight[1]);

        // Clamp to mini-map bounds
        vx1 = Math.max(0, vx1); vy1 = Math.max(0, vy1);
        vx2 = Math.min(MM_W, vx2); vy2 = Math.min(MM_H, vy2);

        var vw = vx2 - vx1;
        var vh = vy2 - vy1;

        // Only draw viewport rect if it's smaller than the full mini-map (i.e., user is zoomed in)
        if (vw < MM_W - 2 || vh < MM_H - 2) {
            mmCtx.strokeStyle = _dark ? 'rgba(0,180,216,0.8)' : 'rgba(0,119,182,0.8)';
            mmCtx.lineWidth = _mmHiContrast ? 2.5 : 1.5;
            mmCtx.strokeRect(vx1, vy1, vw, vh);

            // Semi-transparent fill
            mmCtx.fillStyle = _dark ? 'rgba(0,180,216,0.06)' : 'rgba(0,119,182,0.06)';
            mmCtx.fillRect(vx1, vy1, vw, vh);
        }
    }

    // Hook drawMiniMap into the main draw cycle
    var _origDraw = draw;
    draw = function() {
        _origDraw();
        drawLongPressRing();
        drawMiniMap();
    };
    window._redrawNetwork = draw;

    // Update extent periodically during simulation warmup
    var mmExtentTimer = setInterval(function() {
        updateMiniMapExtent();
        drawMiniMap();
    }, 500);
    setTimeout(function() { clearInterval(mmExtentTimer); }, 8000);

    // Mini-map click/drag to pan the main view
    var mmDragging = false;

    function mmPanTo(px, py) {
        // Convert mini-map pixel to world coord
        var wx = mmExtent.xMin + (px - MM_PAD) / (MM_W - 2 * MM_PAD) * (mmExtent.xMax - mmExtent.xMin);
        var wy = mmExtent.yMin + (py - MM_PAD) / (MM_H - 2 * MM_PAD) * (mmExtent.yMax - mmExtent.yMin);

        // Center the main view on this world point at the current zoom level
        var newTx = width / 2 - wx * transform.k;
        var newTy = height / 2 - wy * transform.k;
        var newTransform = d3.zoomIdentity.translate(newTx, newTy).scale(transform.k);

        d3.select(canvas)
            .transition()
            .duration(mmDragging ? 0 : (prefersReducedMotion() ? 0 : 300))
            .call(zoom.transform, newTransform);
    }

    function mmGetPos(event) {
        var r = mmCanvas.getBoundingClientRect();
        return { x: event.clientX - r.left, y: event.clientY - r.top };
    }

    mmCanvas.addEventListener('mousedown', function(event) {
        event.stopPropagation();
        event.preventDefault();
        mmDragging = true;
        var pos = mmGetPos(event);
        mmPanTo(pos.x, pos.y);
    });

    mmCanvas.addEventListener('mousemove', function(event) {
        if (!mmDragging) return;
        event.stopPropagation();
        var pos = mmGetPos(event);
        mmPanTo(pos.x, pos.y);
    });

    mmCanvas.addEventListener('mouseup', function(event) {
        mmDragging = false;
        event.stopPropagation();
    });

    mmCanvas.addEventListener('mouseleave', function() {
        mmDragging = false;
    });

    // Touch event handlers for mobile mini-map interaction
    function mmGetTouchPos(event) {
        var touch = event.touches[0] || event.changedTouches[0];
        var r = mmCanvas.getBoundingClientRect();
        return { x: touch.clientX - r.left, y: touch.clientY - r.top };
    }

    mmCanvas.addEventListener('touchstart', function(event) {
        event.stopPropagation();
        event.preventDefault();
        mmDragging = true;
        var pos = mmGetTouchPos(event);
        mmPanTo(pos.x, pos.y);
    }, { passive: false });

    mmCanvas.addEventListener('touchmove', function(event) {
        if (!mmDragging) return;
        event.stopPropagation();
        event.preventDefault();
        var pos = mmGetTouchPos(event);
        mmPanTo(pos.x, pos.y);
    }, { passive: false });

    mmCanvas.addEventListener('touchend', function(event) {
        mmDragging = false;
        event.stopPropagation();
    });

    mmCanvas.addEventListener('touchcancel', function() {
        mmDragging = false;
    });

    // Prevent mini-map clicks from triggering main canvas zoom
    mmCanvas.addEventListener('wheel', function(event) {
        event.stopPropagation();
    });

    mmCanvas.style.cursor = 'crosshair';

    // === Path Finder ===
    // BFS shortest path between two companies (treating edges as undirected)
    function bfsShortestPath(fromTicker, toTicker) {
        if (fromTicker === toTicker) return { nodes: [fromTicker], edges: [] };
        var visited = new Set();
        var parent = {}; // ticker → { from: ticker, edgeDir: 'out'|'in' }
        var queue = [fromTicker];
        visited.add(fromTicker);

        while (queue.length > 0) {
            var current = queue.shift();
            var adj = adjacency[current];
            if (!adj) continue;

            // Check outbound neighbors
            for (var oi = 0; oi < adj.out.length; oi++) {
                var outN = adj.out[oi];
                if (!visited.has(outN)) {
                    visited.add(outN);
                    parent[outN] = { from: current, dir: 'out' };
                    if (outN === toTicker) break;
                    queue.push(outN);
                }
            }
            if (parent[toTicker]) break;

            // Check inbound neighbors (treat as undirected)
            for (var ii = 0; ii < adj.in.length; ii++) {
                var inN = adj.in[ii];
                if (!visited.has(inN)) {
                    visited.add(inN);
                    parent[inN] = { from: current, dir: 'in' };
                    if (inN === toTicker) break;
                    queue.push(inN);
                }
            }
            if (parent[toTicker]) break;
        }

        if (!parent[toTicker]) return null; // No path

        // Reconstruct path
        var pathNodes = [];
        var pathEdges = [];
        var cur = toTicker;
        while (cur !== fromTicker) {
            pathNodes.unshift(cur);
            var p = parent[cur];
            // Edge direction: if dir='out', parent selected cur as peer (parent→cur)
            // if dir='in', cur selected parent as peer (cur→parent)
            if (p.dir === 'out') {
                pathEdges.unshift({ source: p.from, target: cur });
            } else {
                pathEdges.unshift({ source: cur, target: p.from });
            }
            cur = p.from;
        }
        pathNodes.unshift(fromTicker);
        return { nodes: pathNodes, edges: pathEdges };
    }

    // Path finder UI
    var pfToggle = document.getElementById('path-finder-toggle');
    var pfBar = document.getElementById('path-finder-bar');
    var pfResult = document.getElementById('path-finder-result');
    var pfFromInput = document.getElementById('path-from-input');
    var pfToInput = document.getElementById('path-to-input');
    var pfFromResults = document.getElementById('path-from-results');
    var pfToResults = document.getElementById('path-to-results');
    var pfGoBtn = document.getElementById('path-finder-go');
    var pfClearBtn = document.getElementById('path-finder-clear');

    var pfFromTicker = null;
    var pfToTicker = null;

    function pfMatchNodes(query) {
        var q = query.trim().toLowerCase();
        if (q.length === 0) return [];
        var matches = nodes.filter(function(n) {
            return n.ticker.toLowerCase().indexOf(q) >= 0 || n.name.toLowerCase().indexOf(q) >= 0;
        });
        matches.sort(function(a, b) {
            var at = a.ticker.toLowerCase(), bt = b.ticker.toLowerCase();
            if (at === q && bt !== q) return -1;
            if (bt === q && at !== q) return 1;
            var aS = at.indexOf(q) === 0 ? 0 : 1;
            var bS = bt.indexOf(q) === 0 ? 0 : 1;
            return aS !== bS ? aS - bS : (at < bt ? -1 : at > bt ? 1 : 0);
        });
        return matches.slice(0, 6);
    }

    function pfRenderDropdown(matches, container, onSelect) {
        container.innerHTML = '';
        if (matches.length === 0) { container.classList.remove('visible'); return; }
        matches.forEach(function(n) {
            var div = document.createElement('div');
            div.className = 'network-search-result';
            // Contextual color dot — heatmap color in heatmap mode, sector color otherwise
            var dotColor = getNodeColor(n.ticker, n.sector);
            var dotHtml = '<span class="nsr-dot" style="background:' + dotColor + '"></span>';
            var comp = _compLookup[n.ticker];
            var payHtml = '';
            if (comp && comp.total != null && comp.total > 0) {
                payHtml = '<span class="nsr-pay">' + _fmtComp(comp.total) + '</span>';
            }
            div.innerHTML = dotHtml +
                '<span class="nsr-ticker">' + n.ticker + '</span>' +
                '<span class="nsr-name">' + n.name + '</span>' +
                payHtml +
                '<span class="nsr-sector">' + (n.sector || '') + '</span>';
            div.addEventListener('mousedown', function(e) {
                e.preventDefault();
                onSelect(n);
            });
            container.appendChild(div);
        });
        container.classList.add('visible');
    }

    function pfUpdateGoState() {
        if (pfGoBtn) pfGoBtn.disabled = !(pfFromTicker && pfToTicker && pfFromTicker !== pfToTicker);
    }

    function pfClearPath() {
        activePath = null;
        pfFromTicker = null;
        pfToTicker = null;
        if (pfFromInput) pfFromInput.value = '';
        if (pfToInput) pfToInput.value = '';
        if (pfResult) pfResult.classList.remove('visible');
        pfUpdateGoState();
        draw();
    }

    function pfZoomToPath(pathResult) {
        // Compute bounding box of path nodes and zoom to fit
        var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        pathResult.nodes.forEach(function(ticker) {
            var n = nodeMap[ticker];
            if (!n) return;
            var r = getRadius(n);
            if (n.x - r < minX) minX = n.x - r;
            if (n.x + r > maxX) maxX = n.x + r;
            if (n.y - r < minY) minY = n.y - r;
            if (n.y + r > maxY) maxY = n.y + r;
        });
        // Add padding
        var pad = 80;
        minX -= pad; minY -= pad; maxX += pad; maxY += pad;
        var bw = maxX - minX || 100;
        var bh = maxY - minY || 100;
        var scaleX = width / bw;
        var scaleY = height / bh;
        var sc = Math.min(scaleX, scaleY, 3); // cap zoom
        var cx = (minX + maxX) / 2;
        var cy = (minY + maxY) / 2;
        var tx = width / 2 - cx * sc;
        var ty = height / 2 - cy * sc;
        var newTransform = d3.zoomIdentity.translate(tx, ty).scale(sc);
        d3.select(canvas)
            .transition()
            .duration(prefersReducedMotion() ? 0 : 800)
            .call(zoom.transform, newTransform);
    }

    function pfShowResult(pathResult) {
        if (!pfResult) return;
        if (!pathResult) {
            pfResult.innerHTML = '<div class="path-no-result">No peer connection path found between these companies.</div>';
            pfResult.classList.add('visible');
            return;
        }
        var hops = pathResult.nodes.length - 1;
        var html = '<div class="path-result-header">' + hops + '-hop path found</div>';
        html += '<div class="path-result-chain">';

        // Collect compensation values for path analysis
        var pathCompVals = [];
        pathResult.nodes.forEach(function(ticker, idx) {
            var n = nodeMap[ticker];
            // Use heatmap color in heatmap mode, sector color otherwise
            var color;
            if (compHeatmapMode || prHeatmapMode || ccHeatmapMode) {
                color = getNodeColor(ticker, n ? n.sector : '');
            } else {
                color = n ? (SECTOR_COLORS[n.sector] || '#94a3b8') : '#94a3b8';
            }
            var name = n ? n.name : ticker;

            // CEO compensation badge for this path node
            var comp = _compLookup[ticker];
            var compVal = (comp && comp.total != null && comp.total > 0) ? comp.total : null;
            if (compVal !== null) pathCompVals.push(compVal);
            var compBadge = compVal !== null ? '<span class="pnc-comp">' + _fmtComp(compVal) + '</span>' : '';

            html += '<span class="path-node-chip" data-ticker="' + ticker + '" style="background:' + color + '20;color:' + color + ';border-color:' + color + '40">';
            html += '<span class="pnc-dot" style="background:' + color + '"></span>';
            html += ticker;
            html += compBadge;
            html += '<span class="pnc-name">' + name + '</span>';
            html += '</span>';

            if (idx < pathResult.edges.length) {
                var edge = pathResult.edges[idx];
                // Determine direction relative to path flow
                var isForward = edge.source === ticker;
                // Check if edge is mutual
                var adjCheck = adjacency[edge.source];
                var edgeIsMutual = adjCheck && adjCheck.in.indexOf(edge.target) >= 0;
                html += '<span class="path-edge-arrow' + (edgeIsMutual ? ' path-edge-mutual' : '') + '">';
                if (edgeIsMutual) {
                    html += '⇄';
                } else {
                    html += isForward ? '→' : '←';
                }
                html += '</span>';
            }
        });

        html += '</div>';

        // Stats line
        var sectors = new Set();
        pathResult.nodes.forEach(function(t) {
            var n = nodeMap[t];
            if (n && n.sector) sectors.add(n.sector);
        });
        html += '<div class="path-result-stats">';
        html += hops + ' hop' + (hops !== 1 ? 's' : '') + ' · ' + sectors.size + ' sector' + (sectors.size !== 1 ? 's' : '') + ' crossed';
        var mutualCount = 0;
        pathResult.edges.forEach(function(e) {
            // Check if edge is mutual (both companies select each other)
            var adj = adjacency[e.source];
            if (adj && adj.in.indexOf(e.target) >= 0) mutualCount++;
        });
        if (mutualCount > 0) {
            html += ' · <span class="path-mutual-badge">' + mutualCount + ' mutual ⇄</span>';
        }
        html += '</div>';

        // Compensation flow analysis line
        if (pathCompVals.length >= 2) {
            var startComp = _compLookup[pathResult.nodes[0]];
            var endComp = _compLookup[pathResult.nodes[pathResult.nodes.length - 1]];
            var startVal = (startComp && startComp.total > 0) ? startComp.total : null;
            var endVal = (endComp && endComp.total > 0) ? endComp.total : null;

            html += '<div class="path-comp-flow">';
            // Pay range across path
            var minComp = Math.min.apply(null, pathCompVals);
            var maxComp = Math.max.apply(null, pathCompVals);
            html += '<span class="pcf-range">Pay range: ' + _fmtComp(minComp) + ' – ' + _fmtComp(maxComp) + '</span>';

            // Pay delta from start to end
            if (startVal && endVal) {
                var delta = ((endVal - startVal) / startVal * 100);
                var deltaSign = delta >= 0 ? '+' : '';
                var deltaClass = delta >= 10 ? 'pcf-delta-up' : delta <= -10 ? 'pcf-delta-down' : 'pcf-delta-flat';
                html += '<span class="pcf-sep">·</span>';
                html += '<span class="pcf-delta ' + deltaClass + '">' + deltaSign + delta.toFixed(0) + '% end-to-end</span>';
            }

            // Compensation spread ratio (max/min) — indicates peer group homogeneity
            if (maxComp > 0 && minComp > 0) {
                var spread = (maxComp / minComp).toFixed(1);
                html += '<span class="pcf-sep">·</span>';
                html += '<span class="pcf-spread">' + spread + '× spread</span>';
            }
            html += '</div>';
        }

        pfResult.innerHTML = html;
        pfResult.classList.add('visible');

        // Click handlers on chips
        pfResult.querySelectorAll('.path-node-chip').forEach(function(chip) {
            chip.addEventListener('click', function() {
                var ticker = chip.getAttribute('data-ticker');
                if (window.findCompanyInTable) window.findCompanyInTable(ticker);
            });
        });
    }

    function pfPrefill(ticker, slot) {
        // Open path finder bar if not already open
        if (pfToggle && pfBar && !pfBar.classList.contains('visible')) {
            pfBar.classList.add('visible');
            pfToggle.classList.add('active');
        }
        if (slot === 'from') {
            pfFromTicker = ticker;
            if (pfFromInput) pfFromInput.value = ticker;
            // Focus the "To" input so user can type the destination
            if (pfToInput) setTimeout(function() { pfToInput.focus(); }, 100);
        } else {
            pfToTicker = ticker;
            if (pfToInput) pfToInput.value = ticker;
            // Focus the "From" input so user can type the origin
            if (pfFromInput) setTimeout(function() { pfFromInput.focus(); }, 100);
        }
        pfUpdateGoState();
        // If both are set, auto-execute
        if (pfFromTicker && pfToTicker && pfFromTicker !== pfToTicker) {
            pfExecute();
        }
    }

    function pfExecute() {
        if (!pfFromTicker || !pfToTicker || pfFromTicker === pfToTicker) return;
        var result = bfsShortestPath(pfFromTicker, pfToTicker);
        activePath = result;
        pfShowResult(result);
        if (result) pfZoomToPath(result);
        draw();
    }

    if (pfToggle) {
        pfToggle.addEventListener('click', function() {
            var isOpen = pfBar && pfBar.classList.contains('visible');
            if (isOpen) {
                pfBar.classList.remove('visible');
                pfToggle.classList.remove('active');
                pfClearPath();
            } else {
                pfBar.classList.add('visible');
                pfToggle.classList.add('active');
                if (pfFromInput) pfFromInput.focus();
            }
        });
    }

    function pfSetupInput(input, resultsEl, setTicker) {
        if (!input) return;
        input.addEventListener('input', function() {
            var matches = pfMatchNodes(input.value);
            pfRenderDropdown(matches, resultsEl, function(n) {
                input.value = n.ticker;
                resultsEl.classList.remove('visible');
                setTicker(n.ticker);
                pfUpdateGoState();
            });
        });
        input.addEventListener('blur', function() {
            setTimeout(function() { resultsEl.classList.remove('visible'); }, 150);
        });
        input.addEventListener('focus', function() {
            if (input.value.trim().length > 0) input.dispatchEvent(new Event('input'));
        });
        input.addEventListener('keydown', function(e) {
            var items = resultsEl.querySelectorAll('.network-search-result');
            if (e.key === 'Enter') {
                e.preventDefault();
                var active = resultsEl.querySelector('.network-search-result.active');
                if (active) {
                    active.dispatchEvent(new MouseEvent('mousedown'));
                } else if (items.length > 0) {
                    items[0].dispatchEvent(new MouseEvent('mousedown'));
                } else if (pfFromTicker && pfToTicker) {
                    pfExecute();
                }
            } else if (e.key === 'Escape') {
                resultsEl.classList.remove('visible');
                input.blur();
            } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                var curIdx = -1;
                items.forEach(function(el, i) { if (el.classList.contains('active')) curIdx = i; });
                var newIdx = e.key === 'ArrowDown' ? Math.min(curIdx + 1, items.length - 1) : Math.max(curIdx - 1, 0);
                items.forEach(function(el, i) {
                    el.classList.toggle('active', i === newIdx);
                    el.style.backgroundColor = '';
                });
                if ((compHeatmapMode || prHeatmapMode || ccHeatmapMode) && newIdx >= 0 && newIdx < items.length) {
                    var dot = items[newIdx].querySelector('.nsr-dot');
                    if (dot) items[newIdx].style.backgroundColor = _dotBgTint(dot);
                }
            }
        });
    }

    pfSetupInput(pfFromInput, pfFromResults, function(t) { pfFromTicker = t; });
    pfSetupInput(pfToInput, pfToResults, function(t) { pfToTicker = t; });

    if (pfGoBtn) {
        pfGoBtn.addEventListener('click', function() { pfExecute(); });
    }

    if (pfClearBtn) {
        pfClearBtn.addEventListener('click', function() { pfClearPath(); });
    }

    // Expose path finder API for external use (e.g., from detail panel)
    window.findNetworkPath = function(fromTicker, toTicker) {
        if (!pfToggle || !pfBar) return false;
        pfToggle.classList.add('active');
        pfBar.classList.add('visible');
        pfFromTicker = fromTicker;
        pfToTicker = toTicker;
        if (pfFromInput) pfFromInput.value = fromTicker;
        if (pfToInput) pfToInput.value = toTicker;
        pfUpdateGoState();
        pfExecute();
        // Scroll to network section
        var section = document.getElementById('peer-network-section');
        if (section) section.scrollIntoView({ behavior: (typeof getScrollBehavior === 'function' ? getScrollBehavior() : 'smooth'), block: 'start' });
        return true;
    };
}
