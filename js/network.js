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
    var activeLegendSector = null; // sector legend click-to-filter state

    var nodeMap = {};
    nodes.forEach(function(n) { nodeMap[n.ticker] = n; });

    // Precompute adjacency for fast hover lookups
    var adjacency = {};
    nodes.forEach(function(n) { adjacency[n.ticker] = { in: [], out: [] }; });
    allEdges.forEach(function(e) {
        if (adjacency[e.source]) adjacency[e.source].out.push(e.target);
        if (adjacency[e.target]) adjacency[e.target].in.push(e.source);
    });

    // Node radius based on in-degree — area-proportional scaling
    // Range: 4px (0 peers) to 60px (max ~194 peers)
    // Uses area-proportional mapping so visual size reflects magnitude
    var maxInDegree = 1;
    nodes.forEach(function(n) { if ((n.in_degree || 0) > maxInDegree) maxInDegree = n.in_degree; });
    function getRadius(node) {
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
        var labelColor = _dark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.65)';
        var labelHoverColor = _dark ? '#fff' : '#000';
        var nodeHoverStroke = _dark ? '#fff' : '#000';
        var edgeDimColor = _dark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.03)';
        var edgeSectorDimColor = _dark ? 'rgba(255,255,255,0.015)' : 'rgba(0,0,0,0.025)';

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
        } else if (activeLegendSector && sectorNodeSet) {
            // Sector filter active — dim edges not involving the sector
            ctx.strokeStyle = edgeSectorDimColor;
            ctx.lineWidth = 0.3 / scale;
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
            ctx.strokeStyle = 'rgba(0,180,216,0.35)';
            ctx.lineWidth = 0.8 / scale;
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

            // Cross-sector edges (dimmer, thinner)
            ctx.strokeStyle = edgeCrossColor;
            ctx.lineWidth = 0.4 / scale;
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
            ctx.lineWidth = 0.7 / scale;
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
            } else if (activeLegendSector && sectorNodeSet) {
                if (sectorNodeSet.has(d.ticker)) {
                    alpha = 1;
                } else {
                    alpha = 0.1;
                }
            }

            ctx.beginPath();
            ctx.arc(d.x, d.y, r, 0, 2 * Math.PI);
            ctx.fillStyle = hexToRGBA(color, alpha);
            ctx.fill();

            if (d === hoveredNode) {
                ctx.strokeStyle = nodeHoverStroke;
                ctx.lineWidth = 2 / scale;
                ctx.stroke();
            } else if (activeLegendSector && sectorNodeSet && sectorNodeSet.has(d.ticker) && !hoveredNode) {
                ctx.strokeStyle = hexToRGBA(color, 0.5);
                ctx.lineWidth = 1 / scale;
                ctx.stroke();
            }
        });

        // Labels
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        var fontSize = Math.max(9, Math.min(12, 11 / scale));
        ctx.font = '600 ' + fontSize + 'px Inter, system-ui, sans-serif';

        nodes.forEach(function(d) {
            if (activeLegendSector && sectorNodeSet && !sectorNodeSet.has(d.ticker) && !hoveredNode) return;
            if (!activeLegendSector && !shouldShowLabel(d, scale)) return;
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

        var html = '<div class="tt-title">' + d.ticker + ' — ' + d.name + '</div>';
        html += '<div class="tt-row"><span class="tt-label">Sector</span><span class="tt-value">' + d.sector + '</span></div>';
        html += '<div class="tt-row"><span class="tt-label">Selected by</span><span class="tt-value">' + d.in_degree + ' companies</span></div>';
        if (inTotal > 0) {
            var inSamePct = Math.round(inSame / inTotal * 100);
            html += '<div class="tt-peer-bar"><div class="tt-peer-bar-fill tt-same" style="width:' + inSamePct + '%"></div><div class="tt-peer-bar-fill tt-cross" style="width:' + (100 - inSamePct) + '%"></div></div>';
            html += '<div class="tt-peer-detail"><span class="tt-peer-same">' + inSame + ' same-sector</span><span class="tt-peer-cross">' + inCross + ' cross-sector</span></div>';
        }
        html += '<div class="tt-row"><span class="tt-label">Selects</span><span class="tt-value">' + d.out_degree + ' peers</span></div>';
        if (outTotal > 0) {
            var outSamePct = Math.round(outSame / outTotal * 100);
            html += '<div class="tt-peer-bar"><div class="tt-peer-bar-fill tt-same" style="width:' + outSamePct + '%"></div><div class="tt-peer-bar-fill tt-cross" style="width:' + (100 - outSamePct) + '%"></div></div>';
            html += '<div class="tt-peer-detail"><span class="tt-peer-same">' + outSame + ' same-sector</span><span class="tt-peer-cross">' + outCross + ' cross-sector</span></div>';
        }
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

    // Long-press touch support for mobile node details
    // Tap = pan/zoom (handled by D3). Hold 400ms on a node = show tooltip.
    var _lpTimer = null;
    var _lpNode = null;
    var _lpActive = false; // true while a long-press tooltip is showing
    var _lpStartX = 0;
    var _lpStartY = 0;
    var LP_DELAY = 400; // ms hold before tooltip fires
    var LP_MOVE_THRESHOLD = 10; // px movement cancels long-press

    function cancelLongPress() {
        if (_lpTimer) { clearTimeout(_lpTimer); _lpTimer = null; }
        _lpNode = null;
    }

    canvas.addEventListener('touchstart', function(event) {
        // Multi-touch (pinch zoom) cancels long-press
        if (event.touches.length !== 1) {
            cancelLongPress();
            return;
        }

        // If a long-press tooltip is already visible, dismiss it on next tap
        if (_lpActive) {
            _lpActive = false;
            hoveredNode = null;
            hideTooltip();
            draw();
            cancelLongPress();
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
            var capturedX = touch.clientX;
            var capturedY = touch.clientY;
            _lpTimer = setTimeout(function() {
                if (_lpNode) {
                    hoveredNode = _lpNode;
                    showTooltip(capturedX, capturedY, _lpNode);
                    _lpActive = true;
                    draw();
                    // Haptic feedback if supported
                    if (navigator.vibrate) navigator.vibrate(30);
                }
                _lpTimer = null;
            }, LP_DELAY);
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
            div.innerHTML = '<span class="nsr-ticker">' + n.ticker + '</span>' +
                '<span class="nsr-name">' + n.name + '</span>' +
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
            .duration(750)
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
            section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        // Small delay to let scroll settle, then zoom
        setTimeout(function() {
            selectSearchNode(node);
        }, 400);

        return true;
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
                items.forEach(function(el, i) { el.classList.toggle('active', i === activeIdx); });
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIdx = Math.max(activeIdx - 1, 0);
                items.forEach(function(el, i) { el.classList.toggle('active', i === activeIdx); });
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

            draw();
        });
    });

    // Expose API for clearing sector filter externally
    window.clearNetworkSectorFilter = function() {
        activeLegendSector = null;
        legendItems.forEach(function(li) {
            li.classList.remove('legend-active', 'legend-dimmed');
        });
        draw();
    };

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
        mmCtx.clearRect(0, 0, MM_W, MM_H);

        // Background
        mmCtx.fillStyle = _dark ? 'rgba(15,15,26,0.88)' : 'rgba(244,245,247,0.92)';
        mmCtx.fillRect(0, 0, MM_W, MM_H);

        // Border
        mmCtx.strokeStyle = _dark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)';
        mmCtx.lineWidth = 1;
        mmCtx.strokeRect(0.5, 0.5, MM_W - 1, MM_H - 1);

        // Draw nodes as small dots
        nodes.forEach(function(n) {
            var mx = mmMapX(n.x);
            var my = mmMapY(n.y);
            var color = SECTOR_COLORS[n.sector] || '#94a3b8';
            var dotR = Math.max(1.2, getRadius(n) / 18);
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
            mmCtx.lineWidth = 1.5;
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
            .duration(mmDragging ? 0 : 300)
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
}
