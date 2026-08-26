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
    var gerHeatmapMode = false; // when true, nodes colored by governance erosion risk score
    var communityMode = false;  // when true, nodes colored by Louvain community
    var gerThreshold = 0; // min GER score for node visibility (0 = show all)
    var searchFocusedNode = null; // node focused by search — gets pulsing ring + neighbor highlight
    var searchFocusedTime = 0;   // timestamp when search focus was set (for pulse animation)
    var _hoveredCommunityId = null; // community id hovered in legend — highlights community nodes on graph
    var _hoveredCommunityTickers = null; // Set of tickers in hovered community
    var _pathBadgeAreas = []; // [{ticker, x, y, w, h} ...] for path badge hover detection
    var _pathBadgeHovered = null; // ticker of currently hovered path badge
    var _hoveredQuartileTickers = null; // Set of tickers in hovered box plot quartile zone
    var _hoveredQuartileColor = null; // community color for quartile highlight ring
    var _hoveredTrendTickers = null; // Map of ticker → 'up'|'down'|'stable' for trend sparkline hover
    var _hoveredTrendCommunityColor = null; // community color for trend sparkline hover

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

    // === Louvain Community Detection ===
    // Treats the directed peer network as undirected for modularity optimization.
    // Identifies natural peer clusters that cross sector boundaries.
    var communityOf = {}; // ticker → community id
    var communityColors = {}; // community id → color
    var communityStats = []; // [{id, size, tickers, sectors, topTicker}]

    (function louvainDetect() {
        // Build undirected adjacency with weights
        var tickers = nodes.map(function(n) { return n.ticker; });
        var idx = {}; // ticker → index
        tickers.forEach(function(t, i) { idx[t] = i; });
        var N = tickers.length;

        // Adjacency list (undirected, weight = number of directed edges between pair: 1 or 2)
        var adj = new Array(N);
        for (var i = 0; i < N; i++) adj[i] = {};
        var m2 = 0; // 2 * total edge weight
        allEdges.forEach(function(e) {
            var si = idx[e.source], ti = idx[e.target];
            if (si == null || ti == null || si === ti) return;
            adj[si][ti] = (adj[si][ti] || 0) + 1;
            adj[ti][si] = (adj[ti][si] || 0) + 1;
            m2 += 2;
        });

        // Degree (sum of weights) for each node
        var deg = new Array(N);
        for (var i = 0; i < N; i++) {
            var s = 0;
            for (var j in adj[i]) s += adj[i][j];
            deg[i] = s;
        }

        // Initial community = each node in its own community
        var comm = new Array(N);
        for (var i = 0; i < N; i++) comm[i] = i;

        // Sum of weights inside each community, sum of degrees per community
        var sIn = new Array(N).fill(0);
        var sTot = new Array(N);
        for (var i = 0; i < N; i++) sTot[i] = deg[i];

        // Phase 1: local moves
        var improved = true;
        var maxIter = 20;
        while (improved && maxIter-- > 0) {
            improved = false;
            for (var i = 0; i < N; i++) {
                var ci = comm[i];
                var ki = deg[i];

                // Compute weights to each neighbor community
                var neighborComms = {};
                for (var j in adj[i]) {
                    var cj = comm[j];
                    neighborComms[cj] = (neighborComms[cj] || 0) + adj[i][j];
                }

                // Weight to own community
                var kiIn = neighborComms[ci] || 0;

                // Remove node from its community
                sIn[ci] -= 2 * kiIn; // edges within community involving i
                sTot[ci] -= ki;

                // Find best community
                var bestComm = ci;
                var bestDQ = 0;
                for (var c in neighborComms) {
                    c = parseInt(c, 10);
                    var kiC = neighborComms[c];
                    // Modularity gain: kiC / m - (sTot[c] * ki) / (m*m) [simplified]
                    var dq = kiC - sTot[c] * ki / (m2 || 1);
                    if (dq > bestDQ) {
                        bestDQ = dq;
                        bestComm = c;
                    }
                }

                // Move to best community
                comm[i] = bestComm;
                sIn[bestComm] += 2 * (neighborComms[bestComm] || 0);
                sTot[bestComm] += ki;

                if (bestComm !== ci) improved = true;
            }
        }

        // Renumber communities to 0..K-1
        var commMap = {};
        var nextId = 0;
        for (var i = 0; i < N; i++) {
            if (commMap[comm[i]] == null) commMap[comm[i]] = nextId++;
            communityOf[tickers[i]] = commMap[comm[i]];
        }

        // Community palette (20 distinct colors, high saturation)
        var palette = [
            '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
            '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990',
            '#dcbeff', '#9A6324', '#fffac8', '#800000', '#aaffc3',
            '#808000', '#ffd8b1', '#000075', '#a9a9a9', '#e6beff'
        ];

        // Gather stats per community
        var commBuckets = {};
        for (var i = 0; i < N; i++) {
            var cid = communityOf[tickers[i]];
            if (!commBuckets[cid]) commBuckets[cid] = [];
            commBuckets[cid].push(tickers[i]);
        }

        // Sort by size descending, assign colors
        var sortedComms = Object.keys(commBuckets).map(function(cid) {
            return { id: parseInt(cid, 10), tickers: commBuckets[cid] };
        }).sort(function(a, b) { return b.tickers.length - a.tickers.length; });

        communityStats = [];
        sortedComms.forEach(function(c, idx) {
            communityColors[c.id] = palette[idx % palette.length];
            // Sector breakdown
            var sectorCounts = {};
            c.tickers.forEach(function(t) {
                var n = nodeMap[t];
                var sec = n ? n.sector : 'Unknown';
                sectorCounts[sec] = (sectorCounts[sec] || 0) + 1;
            });
            var sectors = Object.keys(sectorCounts).map(function(s) {
                return { name: s, count: sectorCounts[s] };
            }).sort(function(a, b) { return b.count - a.count; });

            // Top company by in_degree
            var topTicker = c.tickers.slice().sort(function(a, b) {
                return (nodeMap[b] ? nodeMap[b].in_degree || 0 : 0) - (nodeMap[a] ? nodeMap[a].in_degree || 0 : 0);
            })[0];

            communityStats.push({
                id: c.id,
                size: c.tickers.length,
                tickers: c.tickers,
                sectors: sectors,
                topTicker: topTicker,
                color: palette[idx % palette.length],
                label: '' // populated below
            });
        });

        // Expose community data for cross-section filtering
    window._communityOf = communityOf;
    window._communityStats = communityStats;

    // Auto-generate descriptive names for each community
        var _sectorShort = {
            'Information Technology': 'Tech',
            'Communication Services': 'Media & Comms',
            'Consumer Discretionary': 'Consumer',
            'Health Care': 'Healthcare',
            'Financials': 'Finance',
            'Consumer Staples': 'Staples',
            'Industrials': 'Industrial',
            'Real Estate': 'Real Estate',
            'Energy': 'Energy',
            'Materials': 'Materials',
            'Utilities': 'Utilities'
        };
        var _usedNames = {};
        communityStats.forEach(function(cs) {
            var total = cs.size;
            var s0 = cs.sectors[0] || { name: 'Unknown', count: 0 };
            var s1 = cs.sectors[1] || { name: 'Unknown', count: 0 };
            var pct0 = total > 0 ? s0.count / total : 0;
            var pct01 = total > 0 ? (s0.count + s1.count) / total : 0;
            var short0 = _sectorShort[s0.name] || s0.name;
            var short1 = _sectorShort[s1.name] || s1.name;
            var baseName;
            if (pct0 >= 0.55) {
                baseName = short0;
            } else if (pct01 >= 0.55) {
                baseName = short0 + ' & ' + short1;
            } else if (cs.sectors.length >= 4) {
                baseName = 'Diversified';
            } else {
                baseName = short0 + '-led';
            }
            // Deduplicate: append anchor ticker if name reused
            if (_usedNames[baseName]) {
                baseName = baseName + ' · ' + cs.topTicker;
            }
            _usedNames[baseName] = true;
            cs.label = baseName;
        });
    })();

    // Compute modularity score for the detected communities
    var communityModularity = (function() {
        var m = allEdges.length; // total directed edges
        if (m === 0) return 0;
        var q = 0;
        allEdges.forEach(function(e) {
            var ci = communityOf[e.source], cj = communityOf[e.target];
            if (ci === cj) {
                var ki = (adjacency[e.source] ? adjacency[e.source].in.length + adjacency[e.source].out.length : 0);
                var kj = (adjacency[e.target] ? adjacency[e.target].in.length + adjacency[e.target].out.length : 0);
                q += 1 - (ki * kj) / (2 * m);
            }
        });
        return q / m;
    })();

    function getCommunityColor(ticker) {
        var cid = communityOf[ticker];
        return communityColors[cid] || '#94a3b8';
    }

    // === Global Network Statistics (always-visible summary bar) ===
    // Pre-compute degree distribution data for the distribution panel
    var degreeDist = (function() {
        var inDegrees = nodes.map(function(n) { return n.in_degree || 0; }).sort(function(a, b) { return a - b; });
        var total = inDegrees.length;
        var median = total > 0 ? inDegrees[Math.floor(total * 0.5)] : 0;
        var p90 = total > 0 ? inDegrees[Math.floor(total * 0.9)] : 0;
        var p99 = total > 0 ? inDegrees[Math.floor(total * 0.99)] : 0;
        var maxDeg = total > 0 ? inDegrees[total - 1] : 0;

        // Buckets for histogram
        var buckets = [
            { label: '0', min: 0, max: 0, count: 0 },
            { label: '1–5', min: 1, max: 5, count: 0 },
            { label: '6–10', min: 6, max: 10, count: 0 },
            { label: '11–20', min: 11, max: 20, count: 0 },
            { label: '21–50', min: 21, max: 50, count: 0 },
            { label: '51–100', min: 51, max: 100, count: 0 },
            { label: '101+', min: 101, max: Infinity, count: 0 }
        ];
        inDegrees.forEach(function(d) {
            for (var i = 0; i < buckets.length; i++) {
                if (d >= buckets[i].min && d <= buckets[i].max) { buckets[i].count++; break; }
            }
        });
        var maxBucket = 0;
        buckets.forEach(function(b) { if (b.count > maxBucket) maxBucket = b.count; });

        // Top 8 most-selected companies (benchmark darlings)
        var sorted = nodes.slice().sort(function(a, b) { return (b.in_degree || 0) - (a.in_degree || 0); });
        var top8 = sorted.slice(0, 8).map(function(n) {
            return { ticker: n.ticker, sector: n.sector, inDeg: n.in_degree || 0 };
        });

        return { inDegrees: inDegrees, median: median, p90: p90, p99: p99, maxDeg: maxDeg, buckets: buckets, maxBucket: maxBucket, top8: top8, total: total };
    })();

    // Pre-compute clustering coefficient distribution data for the CC panel
    var ccDist = (function() {
        // Only include nodes with >= 2 neighbors (meaningful CC)
        var eligible = nodes.filter(function(n) { return adjSets[n.ticker] && adjSets[n.ticker].size >= 2; });
        var ccValues = eligible.map(function(n) { return clusteringCoeff[n.ticker]; }).sort(function(a, b) { return a - b; });
        var total = ccValues.length;
        var median = total > 0 ? ccValues[Math.floor(total * 0.5)] : 0;
        var p10 = total > 0 ? ccValues[Math.floor(total * 0.1)] : 0;
        var p90 = total > 0 ? ccValues[Math.floor(total * 0.9)] : 0;
        var maxVal = total > 0 ? ccValues[total - 1] : 0;
        var insufficient = nodes.length - eligible.length; // nodes with < 2 neighbors

        // Buckets (CC percentage ranges)
        var buckets = [
            { label: '0%', min: 0, max: 0, count: 0 },
            { label: '1–10%', min: 0.001, max: 0.10, count: 0 },
            { label: '11–20%', min: 0.101, max: 0.20, count: 0 },
            { label: '21–30%', min: 0.201, max: 0.30, count: 0 },
            { label: '31–50%', min: 0.301, max: 0.50, count: 0 },
            { label: '51%+', min: 0.501, max: Infinity, count: 0 }
        ];
        ccValues.forEach(function(cc) {
            for (var i = 0; i < buckets.length; i++) {
                if (cc >= buckets[i].min && cc <= buckets[i].max) { buckets[i].count++; break; }
            }
        });
        var maxBucket = 0;
        buckets.forEach(function(b) { if (b.count > maxBucket) maxBucket = b.count; });

        // Top 8 "Cluster Core" — highest CC (tightly interconnected peer groups)
        var sortedHigh = eligible.slice().sort(function(a, b) {
            return clusteringCoeff[b.ticker] - clusteringCoeff[a.ticker];
        });
        var clusterCores = sortedHigh.slice(0, 8).map(function(n) {
            return { ticker: n.ticker, sector: n.sector, cc: clusteringCoeff[n.ticker], neighbors: adjSets[n.ticker].size };
        });

        // Top 8 "Bridge Companies" — lowest nonzero CC with >= 5 neighbors (connecting disparate groups)
        var bridgeCandidates = eligible.filter(function(n) { return adjSets[n.ticker].size >= 5; });
        bridgeCandidates.sort(function(a, b) { return clusteringCoeff[a.ticker] - clusteringCoeff[b.ticker]; });
        var bridges = bridgeCandidates.slice(0, 8).map(function(n) {
            return { ticker: n.ticker, sector: n.sector, cc: clusteringCoeff[n.ticker], neighbors: adjSets[n.ticker].size };
        });

        return {
            ccValues: ccValues, total: total, insufficient: insufficient,
            median: median, p10: p10, p90: p90, maxVal: maxVal,
            buckets: buckets, maxBucket: maxBucket,
            clusterCores: clusterCores, bridges: bridges
        };
    })();

    var degreeDistPanelOpen = false;
    var ccDistPanelOpen = false;

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
            { label: 'Avg Clustering', value: (globalAvgCC * 100).toFixed(1) + '%', clickable: true, id: 'ngs-avg-cc', panelOpen: ccDistPanelOpen, title: 'Click to explore clustering coefficient distribution' },
            { label: 'Mutual Pairs', value: fmt(mutualPairs) },
            { label: 'Avg Degree', value: avgDegree.toFixed(1), clickable: true, id: 'ngs-avg-degree', panelOpen: degreeDistPanelOpen, title: 'Click to explore degree distribution' }
        ];

        var html = '';
        stats.forEach(function(s) {
            if (s.clickable) {
                html += '<span class="ngs-stat ngs-stat-clickable' + (s.panelOpen ? ' ngs-stat-active' : '') + '" id="' + s.id + '" title="' + s.title + '" role="button" tabindex="0">';
                html += '<span class="ngs-label">' + s.label + '</span> <span class="ngs-value">' + s.value + '</span>';
                html += '<span class="ngs-expand-icon">' + (s.panelOpen ? '▾' : '▸') + '</span>';
                html += '</span>';
            } else {
                html += '<span class="ngs-stat"><span class="ngs-label">' + s.label + '</span> <span class="ngs-value">' + s.value + '</span></span>';
            }
        });
        el.innerHTML = html;

        // Attach click handler to the clickable degree stat
        var degEl = document.getElementById('ngs-avg-degree');
        if (degEl) {
            degEl.addEventListener('click', function() {
                degreeDistPanelOpen = !degreeDistPanelOpen;
                if (degreeDistPanelOpen) ccDistPanelOpen = false; // close CC panel when opening degree
                renderGlobalStats();
                renderDegreeDistPanel();
                renderCCDistPanel();
            });
            degEl.addEventListener('keydown', function(ev) {
                if (ev.key === 'Enter' || ev.key === ' ') {
                    ev.preventDefault();
                    degreeDistPanelOpen = !degreeDistPanelOpen;
                    if (degreeDistPanelOpen) ccDistPanelOpen = false;
                    renderGlobalStats();
                    renderDegreeDistPanel();
                    renderCCDistPanel();
                }
            });
        }

        // Attach click handler to the clickable clustering stat
        var ccEl = document.getElementById('ngs-avg-cc');
        if (ccEl) {
            ccEl.addEventListener('click', function() {
                ccDistPanelOpen = !ccDistPanelOpen;
                if (ccDistPanelOpen) degreeDistPanelOpen = false; // close degree panel when opening CC
                renderGlobalStats();
                renderCCDistPanel();
                renderDegreeDistPanel();
            });
            ccEl.addEventListener('keydown', function(ev) {
                if (ev.key === 'Enter' || ev.key === ' ') {
                    ev.preventDefault();
                    ccDistPanelOpen = !ccDistPanelOpen;
                    if (ccDistPanelOpen) degreeDistPanelOpen = false;
                    renderGlobalStats();
                    renderCCDistPanel();
                    renderDegreeDistPanel();
                }
            });
        }

        renderDegreeDistPanel();
        renderCCDistPanel();
    }

    function renderDegreeDistPanel() {
        var existing = document.getElementById('ngs-degree-dist-panel');
        if (!degreeDistPanelOpen) {
            if (existing) existing.remove();
            return;
        }

        var _dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;

        var panel = existing;
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'ngs-degree-dist-panel';
            panel.className = 'ngs-degree-dist-panel';
            panel.setAttribute('role', 'region');
            panel.setAttribute('aria-label', 'In-degree distribution');
            var statsBar = document.getElementById('network-global-stats');
            if (statsBar && statsBar.parentNode) {
                statsBar.parentNode.insertBefore(panel, statsBar.nextSibling);
            }
        }

        var dd = degreeDist;
        var html = '<div class="ngs-ddp-inner">';

        // Left: histogram
        html += '<div class="ngs-ddp-hist-section">';
        html += '<div class="ngs-ddp-title">In-Degree Distribution <span class="ngs-ddp-subtitle">How many companies select each node as a peer</span></div>';
        html += '<div class="ngs-ddp-histogram">';
        dd.buckets.forEach(function(b) {
            var pct = dd.maxBucket > 0 ? (b.count / dd.maxBucket) * 100 : 0;
            var barColor = b.min >= 51 ? '#06d6a0' : b.min >= 11 ? '#00b4d8' : '#94a3b8';
            html += '<div class="ngs-ddp-bar-group">';
            html += '<div class="ngs-ddp-bar-track">';
            html += '<div class="ngs-ddp-bar" style="width:' + Math.max(2, pct) + '%;background:' + barColor + '" title="' + b.count + ' companies with ' + b.label + ' inbound peers"></div>';
            html += '</div>';
            html += '<span class="ngs-ddp-bar-label">' + b.label + '</span>';
            html += '<span class="ngs-ddp-bar-count">' + b.count + '</span>';
            html += '</div>';
        });
        html += '</div>';

        // Distribution stats
        html += '<div class="ngs-ddp-stats">';
        html += '<span class="ngs-ddp-stat"><span class="ngs-ddp-stat-label">Median</span> <span class="ngs-ddp-stat-val">' + dd.median + '</span></span>';
        html += '<span class="ngs-ddp-stat"><span class="ngs-ddp-stat-label">P90</span> <span class="ngs-ddp-stat-val">' + dd.p90 + '</span></span>';
        html += '<span class="ngs-ddp-stat"><span class="ngs-ddp-stat-label">P99</span> <span class="ngs-ddp-stat-val">' + dd.p99 + '</span></span>';
        html += '<span class="ngs-ddp-stat"><span class="ngs-ddp-stat-label">Max</span> <span class="ngs-ddp-stat-val">' + dd.maxDeg + '</span></span>';
        html += '</div>';
        html += '</div>';

        // Right: benchmark darlings
        html += '<div class="ngs-ddp-darlings-section">';
        html += '<div class="ngs-ddp-title">Benchmark Darlings <span class="ngs-ddp-subtitle">Most-selected peer companies</span></div>';
        html += '<div class="ngs-ddp-darlings">';
        dd.top8.forEach(function(d, i) {
            var sectorColor = SECTOR_COLORS[d.sector] || '#94a3b8';
            html += '<div class="ngs-ddp-darling">';
            html += '<span class="ngs-ddp-darling-rank">' + (i + 1) + '</span>';
            html += '<span class="ngs-ddp-darling-dot" style="background:' + sectorColor + '"></span>';
            html += '<span class="ngs-ddp-darling-ticker">' + d.ticker + '</span>';
            html += '<span class="ngs-ddp-darling-bar-track">';
            html += '<span class="ngs-ddp-darling-bar" style="width:' + (dd.maxDeg > 0 ? (d.inDeg / dd.maxDeg * 100) : 0) + '%;background:' + sectorColor + '"></span>';
            html += '</span>';
            html += '<span class="ngs-ddp-darling-count">' + d.inDeg + '</span>';
            html += '</div>';
        });
        html += '</div>';

        // Power law note
        var topPct = dd.total > 0 ? ((dd.top8.length / dd.total) * 100).toFixed(1) : '0';
        var topDegSum = 0;
        dd.top8.forEach(function(d) { topDegSum += d.inDeg; });
        var totalDegSum = 0;
        dd.inDegrees.forEach(function(d) { totalDegSum += d; });
        var topSharePct = totalDegSum > 0 ? ((topDegSum / totalDegSum) * 100).toFixed(0) : '0';
        html += '<div class="ngs-ddp-note">Top ' + dd.top8.length + ' (' + topPct + '%) account for ' + topSharePct + '% of all peer selections — a power-law distribution typical of benchmark networks.</div>';

        html += '</div>';
        html += '</div>';

        panel.innerHTML = html;

        // Make darling tickers clickable to find in network
        panel.querySelectorAll('.ngs-ddp-darling-ticker').forEach(function(el) {
            el.style.cursor = 'pointer';
            el.title = 'Click to find in network';
            el.addEventListener('click', function() {
                var ticker = el.textContent;
                if (typeof window.focusNetworkNode === 'function') {
                    window.focusNetworkNode(ticker);
                }
            });
        });
    }

    function renderCCDistPanel() {
        var existing = document.getElementById('ngs-cc-dist-panel');
        if (!ccDistPanelOpen) {
            if (existing) existing.remove();
            return;
        }

        var _dark = typeof isDarkTheme === 'function' ? isDarkTheme() : true;

        var panel = existing;
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'ngs-cc-dist-panel';
            panel.className = 'ngs-degree-dist-panel';
            panel.setAttribute('role', 'region');
            panel.setAttribute('aria-label', 'Clustering coefficient distribution');
            var statsBar = document.getElementById('network-global-stats');
            if (statsBar && statsBar.parentNode) {
                statsBar.parentNode.insertBefore(panel, statsBar.nextSibling);
            }
        }

        var cd = ccDist;
        var html = '<div class="ngs-ddp-inner">';

        // Left: histogram
        html += '<div class="ngs-ddp-hist-section">';
        html += '<div class="ngs-ddp-title">Clustering Coefficient Distribution <span class="ngs-ddp-subtitle">How interconnected each company\'s peer neighborhood is</span></div>';
        html += '<div class="ngs-ddp-histogram">';
        cd.buckets.forEach(function(b) {
            var pct = cd.maxBucket > 0 ? (b.count / cd.maxBucket) * 100 : 0;
            // Color: bridges (low CC) = cyan, moderate = gold, dense clusters (high CC) = green
            var barColor;
            if (b.min >= 0.301) barColor = '#06d6a0';
            else if (b.min >= 0.101) barColor = '#ffd166';
            else barColor = '#00b4d8';
            html += '<div class="ngs-ddp-bar-group">';
            html += '<div class="ngs-ddp-bar-track">';
            html += '<div class="ngs-ddp-bar" style="width:' + Math.max(2, pct) + '%;background:' + barColor + '" title="' + b.count + ' companies with CC ' + b.label + '"></div>';
            html += '</div>';
            html += '<span class="ngs-ddp-bar-label">' + b.label + '</span>';
            html += '<span class="ngs-ddp-bar-count">' + b.count + '</span>';
            html += '</div>';
        });
        html += '</div>';

        // Distribution stats
        html += '<div class="ngs-ddp-stats">';
        html += '<span class="ngs-ddp-stat"><span class="ngs-ddp-stat-label">Median</span> <span class="ngs-ddp-stat-val">' + (cd.median * 100).toFixed(1) + '%</span></span>';
        html += '<span class="ngs-ddp-stat"><span class="ngs-ddp-stat-label">P10</span> <span class="ngs-ddp-stat-val">' + (cd.p10 * 100).toFixed(1) + '%</span></span>';
        html += '<span class="ngs-ddp-stat"><span class="ngs-ddp-stat-label">P90</span> <span class="ngs-ddp-stat-val">' + (cd.p90 * 100).toFixed(1) + '%</span></span>';
        html += '<span class="ngs-ddp-stat"><span class="ngs-ddp-stat-label">Max</span> <span class="ngs-ddp-stat-val">' + (cd.maxVal * 100).toFixed(1) + '%</span></span>';
        if (cd.insufficient > 0) {
            html += '<span class="ngs-ddp-stat ngs-ddp-stat-muted"><span class="ngs-ddp-stat-label">&lt;2 peers</span> <span class="ngs-ddp-stat-val">' + cd.insufficient + '</span></span>';
        }
        html += '</div>';
        html += '</div>';

        // Right: two columns — cluster cores and bridges
        html += '<div class="ngs-ddp-darlings-section">';

        // Cluster cores (highest CC)
        html += '<div class="ngs-ddp-title">Cluster Cores <span class="ngs-ddp-subtitle">Tightest peer neighborhoods — all peers know each other</span></div>';
        html += '<div class="ngs-ddp-darlings">';
        cd.clusterCores.forEach(function(d, i) {
            var sectorColor = SECTOR_COLORS[d.sector] || '#94a3b8';
            var ccPct = (d.cc * 100).toFixed(1);
            html += '<div class="ngs-ddp-darling">';
            html += '<span class="ngs-ddp-darling-rank">' + (i + 1) + '</span>';
            html += '<span class="ngs-ddp-darling-dot" style="background:' + sectorColor + '"></span>';
            html += '<span class="ngs-ddp-darling-ticker">' + d.ticker + '</span>';
            html += '<span class="ngs-ddp-darling-bar-track">';
            html += '<span class="ngs-ddp-darling-bar" style="width:' + (cd.maxVal > 0 ? (d.cc / cd.maxVal * 100) : 0) + '%;background:#06d6a0"></span>';
            html += '</span>';
            html += '<span class="ngs-ddp-darling-count">' + ccPct + '%</span>';
            html += '</div>';
        });
        html += '</div>';

        // Bridge companies (lowest CC with >= 5 neighbors)
        if (cd.bridges.length > 0) {
            html += '<div class="ngs-ddp-title" style="margin-top:12px;">Bridge Companies <span class="ngs-ddp-subtitle">Connect disparate groups — low CC despite many peers</span></div>';
            html += '<div class="ngs-ddp-darlings">';
            cd.bridges.forEach(function(d, i) {
                var sectorColor = SECTOR_COLORS[d.sector] || '#94a3b8';
                var ccPct = (d.cc * 100).toFixed(1);
                html += '<div class="ngs-ddp-darling">';
                html += '<span class="ngs-ddp-darling-rank">' + (i + 1) + '</span>';
                html += '<span class="ngs-ddp-darling-dot" style="background:' + sectorColor + '"></span>';
                html += '<span class="ngs-ddp-darling-ticker">' + d.ticker + '</span>';
                html += '<span class="ngs-ddp-darling-bar-track">';
                // Invert scale — bridges have LOW CC so bar = neighbors count relative to max
                var maxN = 0;
                cd.bridges.forEach(function(b) { if (b.neighbors > maxN) maxN = b.neighbors; });
                html += '<span class="ngs-ddp-darling-bar" style="width:' + (maxN > 0 ? (d.neighbors / maxN * 100) : 0) + '%;background:#00b4d8"></span>';
                html += '</span>';
                html += '<span class="ngs-ddp-darling-count">' + ccPct + '% <span class="ngs-cc-neighbors">(' + d.neighbors + 'p)</span></span>';
                html += '</div>';
            });
            html += '</div>';
        }

        // Interpretive note
        var bridgePct = cd.total > 0 ? ((cd.buckets[0].count + cd.buckets[1].count) / cd.total * 100).toFixed(0) : '0';
        var densePct = cd.total > 0 ? (cd.buckets.filter(function(b) { return b.min >= 0.301; }).reduce(function(s, b) { return s + b.count; }, 0) / cd.total * 100).toFixed(0) : '0';
        html += '<div class="ngs-ddp-note">' + bridgePct + '% of companies occupy bridge positions (CC ≤ 10%) connecting disparate groups, while ' + densePct + '% sit in dense clusters (CC > 30%) where most peers benchmark against each other.</div>';

        html += '</div>';
        html += '</div>';

        panel.innerHTML = html;

        // Make tickers clickable to find in network
        panel.querySelectorAll('.ngs-ddp-darling-ticker').forEach(function(el) {
            el.style.cursor = 'pointer';
            el.title = 'Click to find in network';
            el.addEventListener('click', function() {
                var ticker = el.textContent;
                if (typeof window.focusNetworkNode === 'function') {
                    window.focusNetworkNode(ticker);
                }
            });
        });
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
                // Use quadratic curve for same-sector edges (consistent with default rendering)
                if (s.sector && t.sector && s.sector === t.sector) {
                    var mx = (s.x + t.x) / 2, my = (s.y + t.y) / 2;
                    var dx = t.x - s.x, dy = t.y - s.y;
                    var dist = Math.sqrt(dx * dx + dy * dy);
                    var curv = Math.min(dist * 0.12, 30);
                    var side = (src.charCodeAt(0) + tgt.charCodeAt(0)) % 2 === 0 ? 1 : -1;
                    ctx.quadraticCurveTo(mx + (-dy / (dist || 1) * curv * side), my + (dx / (dist || 1) * curv * side), t.x, t.y);
                } else {
                    ctx.lineTo(t.x, t.y);
                }
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
                // Use quadratic curve for same-sector edges (consistent with default rendering)
                if (s.sector && t.sector && s.sector === t.sector) {
                    var mx = (s.x + t.x) / 2, my = (s.y + t.y) / 2;
                    var dx = t.x - s.x, dy = t.y - s.y;
                    var dist = Math.sqrt(dx * dx + dy * dy);
                    var curv = Math.min(dist * 0.12, 30);
                    var side = (src.charCodeAt(0) + tgt.charCodeAt(0)) % 2 === 0 ? 1 : -1;
                    ctx.quadraticCurveTo(mx + (-dy / (dist || 1) * curv * side), my + (dx / (dist || 1) * curv * side), t.x, t.y);
                } else {
                    ctx.lineTo(t.x, t.y);
                }
                ctx.stroke();
                _drawArrow(s.x, s.y, t.x, t.y, getRadius(t), inColor);
            });

            // Edge direction labels on hover
            var adj = adjacency[hoveredNode.ticker];
            if (adj) {
                var outSet = {};
                var inSet = {};
                adj.out.forEach(function(t) { outSet[t] = true; });
                adj.in.forEach(function(t) { inSet[t] = true; });
                var labeledEdges = [];
                // Collect outbound
                adj.out.forEach(function(peer) {
                    var isMutual = !!inSet[peer];
                    labeledEdges.push({ peer: peer, dir: isMutual ? 'mutual' : 'out' });
                });
                // Collect inbound-only (not mutual)
                adj.in.forEach(function(peer) {
                    if (!outSet[peer]) {
                        labeledEdges.push({ peer: peer, dir: 'in' });
                    }
                });
                ctx.save();
                ctx.font = (9 / scale) + 'px "SF Mono", "Fira Code", monospace';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                labeledEdges.forEach(function(le) {
                    var hn = nodeMap[hoveredNode.ticker];
                    var pn = nodeMap[le.peer];
                    if (!hn || !pn) return;
                    var sx, sy, tx, ty;
                    if (le.dir === 'in') {
                        sx = pn.x; sy = pn.y; tx = hn.x; ty = hn.y;
                    } else {
                        sx = hn.x; sy = hn.y; tx = pn.x; ty = pn.y;
                    }
                    var lmx = (sx + tx) / 2;
                    var lmy = (sy + ty) / 2;
                    // Offset for same-sector curve
                    if (hn.sector && pn.sector && hn.sector === pn.sector) {
                        var ldx = tx - sx, ldy = ty - sy;
                        var ldist = Math.sqrt(ldx * ldx + ldy * ldy);
                        var lcurv = Math.min(ldist * 0.06, 15);
                        var src0 = le.dir === 'in' ? le.peer : hoveredNode.ticker;
                        var tgt0 = le.dir === 'in' ? hoveredNode.ticker : le.peer;
                        var lside = (src0.charCodeAt(0) + tgt0.charCodeAt(0)) % 2 === 0 ? 1 : -1;
                        lmx += (-ldy / (ldist || 1) * lcurv * lside);
                        lmy += (ldx / (ldist || 1) * lcurv * lside);
                    }
                    var sym, clr;
                    if (le.dir === 'mutual') {
                        sym = '\u27F7'; clr = '#f59e0b';
                    } else if (le.dir === 'out') {
                        sym = '\u2192'; clr = outColor;
                    } else {
                        sym = '\u2190'; clr = inColor;
                    }
                    // Draw background for readability
                    var tw = ctx.measureText(sym).width + 4 / scale;
                    ctx.fillStyle = 'rgba(15,23,42,0.75)';
                    ctx.fillRect(lmx - tw / 2, lmy - 5 / scale, tw, 10 / scale);
                    ctx.fillStyle = clr;
                    ctx.fillText(sym, lmx, lmy);
                });
                ctx.restore();
            }
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
        } else if (_hoveredCommunityTickers && !hoveredNode && !activePath) {
            // Community legend hover — dim edges not connecting community members, highlight intra-community
            ctx.strokeStyle = edgeSectorDimColor;
            ctx.lineWidth = (_hiContrast ? 0.5 : 0.3) / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (_hoveredCommunityTickers.has(src) || _hoveredCommunityTickers.has(tgt)) return;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();

            // Highlighted edges within or touching the hovered community
            var _commEdgeColor = _dark ? 'rgba(168,85,247,0.45)' : 'rgba(147,51,234,0.4)';
            ctx.strokeStyle = _hiContrast ? 'rgba(168,85,247,0.65)' : _commEdgeColor;
            ctx.lineWidth = (_hiContrast ? 1.2 : 0.8) / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (!_hoveredCommunityTickers.has(src) && !_hoveredCommunityTickers.has(tgt)) return;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();
        } else if (_hoveredFlowCell && communityMode && !hoveredNode && !activePath) {
            // Flow matrix cell hover — highlight edges between the two selected communities
            var _flowFromSet = new Set();
            var _flowToSet = new Set();
            var _flowFromCs = communityStats.find(function(cs) { return cs.id === _hoveredFlowCell.from; });
            var _flowToCs = communityStats.find(function(cs) { return cs.id === _hoveredFlowCell.to; });
            if (_flowFromCs) _flowFromCs.tickers.forEach(function(t) { _flowFromSet.add(t); });
            if (_flowToCs) _flowToCs.tickers.forEach(function(t) { _flowToSet.add(t); });
            var _flowIsDiag = _hoveredFlowCell.from === _hoveredFlowCell.to;

            // Dim all non-matching edges
            ctx.strokeStyle = edgeSectorDimColor;
            ctx.lineWidth = (_hiContrast ? 0.5 : 0.3) / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                // Check if this edge matches the flow cell
                var matches = _flowIsDiag
                    ? (_flowFromSet.has(src) && _flowFromSet.has(tgt))
                    : (_flowFromSet.has(src) && _flowToSet.has(tgt));
                if (matches) return; // skip — will draw highlighted below
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();

            // Highlighted edges matching the flow cell
            ctx.strokeStyle = _hiContrast ? 'rgba(255,180,0,0.8)' : (_dark ? 'rgba(255,180,0,0.55)' : 'rgba(220,140,0,0.5)');
            ctx.lineWidth = (_hiContrast ? 1.8 : 1.2) / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                var matches = _flowIsDiag
                    ? (_flowFromSet.has(src) && _flowFromSet.has(tgt))
                    : (_flowFromSet.has(src) && _flowToSet.has(tgt));
                if (!matches) return;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();
        } else if (_hoveredQuartileTickers && _hoveredQuartileTickers.size > 0 && !hoveredNode && !activePath) {
            // Box plot quartile hover — dim non-quartile edges, highlight edges connecting quartile members
            ctx.strokeStyle = edgeSectorDimColor;
            ctx.lineWidth = (_hiContrast ? 0.5 : 0.3) / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (_hoveredQuartileTickers.has(src) || _hoveredQuartileTickers.has(tgt)) return;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();

            var _qEdgeColor = _hoveredQuartileColor || '#a78bfa';
            ctx.strokeStyle = _hiContrast ? hexToRGBA(_qEdgeColor, 0.65) : hexToRGBA(_qEdgeColor, 0.45);
            ctx.lineWidth = (_hiContrast ? 1.2 : 0.8) / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (!_hoveredQuartileTickers.has(src) && !_hoveredQuartileTickers.has(tgt)) return;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();
        } else if (_hoveredTrendTickers && _hoveredTrendTickers.size > 0 && !hoveredNode && !activePath) {
            // Trend sparkline hover — dim non-community edges, highlight community member edges colored by direction
            var _trendTickerSet = new Set(_hoveredTrendTickers.keys());
            ctx.strokeStyle = edgeSectorDimColor;
            ctx.lineWidth = (_hiContrast ? 0.5 : 0.3) / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (_trendTickerSet.has(src) || _trendTickerSet.has(tgt)) return;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();
            // Highlighted edges connecting community members
            var _tcColor = _hoveredTrendCommunityColor || '#a78bfa';
            ctx.strokeStyle = _hiContrast ? hexToRGBA(_tcColor, 0.55) : hexToRGBA(_tcColor, 0.35);
            ctx.lineWidth = (_hiContrast ? 1.2 : 0.8) / scale;
            ctx.beginPath();
            edges.forEach(function(e) {
                var src = e.source.ticker || e.source;
                var tgt = e.target.ticker || e.target;
                if (!_trendTickerSet.has(src) && !_trendTickerSet.has(tgt)) return;
                var s = nodeMap[src] || nodeMap[e.source];
                var t = nodeMap[tgt] || nodeMap[e.target];
                if (!s || !t) return;
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();
        } else {
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
                // GER threshold — hide edges where both endpoints are below threshold
                if (gerHeatmapMode && gerThreshold > 0) {
                    var gs1 = _compLookup[s.ticker] ? _compLookup[s.ticker]._gerScore : null;
                    var gs2 = _compLookup[t.ticker] ? _compLookup[t.ticker]._gerScore : null;
                    if ((gs1 == null || gs1 < gerThreshold) && (gs2 == null || gs2 < gerThreshold)) return;
                }
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(t.x, t.y);
            });
            ctx.stroke();

            // Same-sector edges (brighter, slightly thicker, accent-tinted, curved to reduce overlap)
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
                // GER threshold — hide edges where both endpoints are below threshold
                if (gerHeatmapMode && gerThreshold > 0) {
                    var gs1 = _compLookup[s.ticker] ? _compLookup[s.ticker]._gerScore : null;
                    var gs2 = _compLookup[t.ticker] ? _compLookup[t.ticker]._gerScore : null;
                    if ((gs1 == null || gs1 < gerThreshold) && (gs2 == null || gs2 < gerThreshold)) return;
                }
                // Quadratic curve with control point offset perpendicular to the midpoint
                var mx = (s.x + t.x) / 2;
                var my = (s.y + t.y) / 2;
                var dx = t.x - s.x;
                var dy = t.y - s.y;
                var dist = Math.sqrt(dx * dx + dy * dy);
                // Offset proportional to distance, capped — perpendicular direction
                var curvature = Math.min(dist * 0.12, 30);
                // Use source ticker charcode parity to alternate curve direction
                var side = (src.charCodeAt(0) + tgt.charCodeAt(0)) % 2 === 0 ? 1 : -1;
                var nx = -dy / (dist || 1) * curvature * side;
                var ny =  dx / (dist || 1) * curvature * side;
                ctx.moveTo(s.x, s.y);
                ctx.quadraticCurveTo(mx + nx, my + ny, t.x, t.y);
            });
            ctx.stroke();
        }

        // Nodes
        nodes.forEach(function(d) {
            var r = getRadius(d);
            var color = getNodeColor(d.ticker, d.sector);
            var alpha = 0.85;

            // GER threshold filter — dim nodes below threshold when GER heatmap is active
            var belowGerThreshold = false;
            if (gerHeatmapMode && gerThreshold > 0) {
                var gerScore = _compLookup[d.ticker] ? _compLookup[d.ticker]._gerScore : null;
                if (gerScore == null || gerScore < gerThreshold) {
                    belowGerThreshold = true;
                    alpha = 0.04;
                }
            }

            if (!belowGerThreshold && hoveredNode) {
                if (d === hoveredNode) {
                    alpha = 1;
                } else if (connectedSet && connectedSet.has(d.ticker)) {
                    alpha = 0.9;
                } else {
                    alpha = _hiContrast ? 0.25 : 0.15;
                }
            } else if (!belowGerThreshold && activePath && activePath.nodes.length >= 2) {
                // When path is active, dim non-path nodes
                if (activePath.nodes.indexOf(d.ticker) >= 0) {
                    alpha = 1; // path nodes drawn again on top with glow
                } else {
                    alpha = _hiContrast ? 0.12 : 0.08;
                }
            } else if (!belowGerThreshold && activeLegendSector && sectorNodeSet) {
                if (sectorNodeSet.has(d.ticker)) {
                    alpha = 1;
                } else {
                    alpha = _hiContrast ? 0.18 : 0.1;
                }
            } else if (!belowGerThreshold && _hoveredCommunityTickers && !hoveredNode && !activePath) {
                // Community legend hover — highlight community members, dim the rest
                if (_hoveredCommunityTickers.has(d.ticker)) {
                    alpha = 1;
                } else {
                    alpha = _hiContrast ? 0.15 : 0.08;
                }
            } else if (!belowGerThreshold && _hoveredFlowCell && communityMode && !hoveredNode && !activePath) {
                // Flow matrix cell hover — highlight nodes in source and target communities
                var _inFrom = communityOf[d.ticker] === _hoveredFlowCell.from;
                var _inTo = communityOf[d.ticker] === _hoveredFlowCell.to;
                if (_inFrom || _inTo) {
                    alpha = 1;
                } else {
                    alpha = _hiContrast ? 0.12 : 0.06;
                }
            } else if (!belowGerThreshold && _hoveredQuartileTickers && _hoveredQuartileTickers.size > 0 && !hoveredNode && !activePath) {
                // Box plot quartile hover — highlight quartile members, dim rest
                if (_hoveredQuartileTickers.has(d.ticker)) {
                    alpha = 1;
                } else {
                    alpha = _hiContrast ? 0.12 : 0.06;
                }
            } else if (!belowGerThreshold && _hoveredTrendTickers && _hoveredTrendTickers.size > 0 && !hoveredNode && !activePath) {
                // Trend sparkline hover — highlight community members, dim rest
                if (_hoveredTrendTickers.has(d.ticker)) {
                    alpha = 1;
                } else {
                    alpha = _hiContrast ? 0.12 : 0.06;
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
            } else if (_hoveredCommunityTickers && _hoveredCommunityTickers.has(d.ticker) && !hoveredNode) {
                ctx.strokeStyle = hexToRGBA(color, _hiContrast ? 0.8 : 0.6);
                ctx.lineWidth = (_hiContrast ? 1.5 : 1) / scale;
                ctx.stroke();
            } else if (_hoveredFlowCell && communityMode && !hoveredNode) {
                var _ffInFrom = communityOf[d.ticker] === _hoveredFlowCell.from;
                var _ffInTo = communityOf[d.ticker] === _hoveredFlowCell.to;
                if (_ffInFrom || _ffInTo) {
                    ctx.strokeStyle = _ffInFrom ? 'rgba(255,180,0,0.7)' : 'rgba(255,220,100,0.5)';
                    ctx.lineWidth = (_hiContrast ? 1.5 : 1) / scale;
                    ctx.stroke();
                }
            } else if (_hoveredQuartileTickers && _hoveredQuartileTickers.has(d.ticker) && !hoveredNode) {
                ctx.strokeStyle = hexToRGBA(_hoveredQuartileColor || color, _hiContrast ? 0.85 : 0.7);
                ctx.lineWidth = (_hiContrast ? 2 : 1.5) / scale;
                ctx.stroke();
            } else if (_hoveredTrendTickers && _hoveredTrendTickers.has(d.ticker) && !hoveredNode) {
                // Direction-coded stroke: green=decrease, red=increase, amber=stable
                var _tDir = _hoveredTrendTickers.get(d.ticker);
                var _tStroke = _tDir === 'up' ? '#ef4444' : _tDir === 'down' ? '#34d399' : '#fbbf24';
                ctx.strokeStyle = hexToRGBA(_tStroke, _hiContrast ? 0.9 : 0.8);
                ctx.lineWidth = (_hiContrast ? 2.5 : 2) / scale;
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
        if (!hoveredNode && ((!compHeatmapMode && !prHeatmapMode && !ccHeatmapMode && !gerHeatmapMode && !communityMode) || activeLegendSector)) {
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

        // Community labels — floating community names at centroids when community mode is active
        if (!hoveredNode && communityMode) {
            var _commAlpha = 0;
            if (scale <= 0.6) {
                _commAlpha = 0.9;
            } else if (scale < 1.3) {
                _commAlpha = 0.9 * (1 - (scale - 0.6) / 0.7);
            }
            if (_commAlpha > 0.02) {
                // Compute centroids for each community
                var _commSums = {};
                nodes.forEach(function(n) {
                    var cid = communityOf[n.ticker];
                    if (cid == null) return;
                    if (!_commSums[cid]) _commSums[cid] = { x: 0, y: 0, c: 0 };
                    _commSums[cid].x += n.x;
                    _commSums[cid].y += n.y;
                    _commSums[cid].c++;
                });
                var commFontSize = Math.max(11, Math.min(20, 14 / scale));
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.font = '700 ' + commFontSize + 'px Inter, system-ui, sans-serif';
                communityStats.forEach(function(cs) {
                    var cd = _commSums[cs.id];
                    if (!cd || cd.c < 3) return; // skip tiny communities
                    var cx = cd.x / cd.c;
                    var cy = cd.y / cd.c;
                    ctx.shadowColor = _dark ? 'rgba(0,0,0,0.7)' : 'rgba(255,255,255,0.85)';
                    ctx.shadowBlur = 8 / scale;
                    ctx.fillStyle = hexToRGBA(cs.color, _commAlpha);
                    ctx.fillText(cs.label, cx, cy);
                });
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

            // Draw path edges — distinguish mutual vs one-directional, with compensation gradient
            // Build compensation color scale for gradient edges
            var _pathMinComp = Infinity, _pathMaxComp = -Infinity;
            activePath.nodes.forEach(function(ticker) {
                var comp = _compLookup[ticker];
                if (comp && comp.total > 0) {
                    if (comp.total < _pathMinComp) _pathMinComp = comp.total;
                    if (comp.total > _pathMaxComp) _pathMaxComp = comp.total;
                }
            });
            var _pathCompRange = _pathMaxComp - _pathMinComp;
            function _pathCompColor(ticker, alpha) {
                var comp = _compLookup[ticker];
                if (!comp || !comp.total || comp.total <= 0 || _pathCompRange <= 0) return 'rgba(168,85,247,' + alpha + ')';
                var t = (comp.total - _pathMinComp) / _pathCompRange; // 0=lowest, 1=highest
                // Gradient: green (low pay) → yellow (mid) → red (high pay)
                var r, g, b;
                if (t < 0.5) {
                    var s = t * 2;
                    r = Math.round(6 + s * 244);    // 6 → 250
                    g = Math.round(214 - s * 35);    // 214 → 179
                    b = Math.round(160 - s * 100);   // 160 → 60
                } else {
                    var s = (t - 0.5) * 2;
                    r = Math.round(250 - s * 11);    // 250 → 239
                    g = Math.round(179 - s * 111);   // 179 → 68
                    b = Math.round(60 + s * 51);     // 60 → 111
                }
                return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
            }

            activePath.edges.forEach(function(e) {
                var s = nodeMap[e.source];
                var t = nodeMap[e.target];
                if (!s || !t) return;

                // Check if edge is mutual (both companies select each other)
                var adjSrc = adjacency[e.source];
                var isMutual = adjSrc && adjSrc.in.indexOf(e.target) >= 0;

                if (isMutual) {
                    // Mutual edge: compensation gradient double-line with glow
                    var srcColor = _pathCompColor(e.source, 0.85);
                    var tgtColor = _pathCompColor(e.target, 0.85);
                    var grad = ctx.createLinearGradient(s.x, s.y, t.x, t.y);
                    grad.addColorStop(0, srcColor);
                    grad.addColorStop(1, tgtColor);

                    ctx.save();
                    ctx.shadowColor = 'rgba(255,209,102,0.3)';
                    ctx.shadowBlur = 6 / scale;

                    // Compute perpendicular offset for double-line
                    var dx = t.x - s.x, dy = t.y - s.y;
                    var dist = Math.sqrt(dx * dx + dy * dy);
                    var px = -dy / dist * 1.5 / scale; // perpendicular
                    var py = dx / dist * 1.5 / scale;

                    ctx.beginPath();
                    ctx.moveTo(s.x + px, s.y + py);
                    ctx.lineTo(t.x + px, t.y + py);
                    ctx.strokeStyle = grad;
                    ctx.lineWidth = 2.5 / scale;
                    ctx.stroke();

                    ctx.beginPath();
                    ctx.moveTo(s.x - px, s.y - py);
                    ctx.lineTo(t.x - px, t.y - py);
                    ctx.strokeStyle = grad;
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
                        ctx.fillStyle = tgtColor;
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
                        ctx.fillStyle = srcColor;
                        ctx.fill();
                    }
                } else {
                    // One-directional edge: compensation gradient
                    // Create gradient from source comp color to target comp color
                    var srcColor = _pathCompColor(e.source, 0.8);
                    var tgtColor = _pathCompColor(e.target, 0.8);
                    var grad = ctx.createLinearGradient(s.x, s.y, t.x, t.y);
                    grad.addColorStop(0, srcColor);
                    grad.addColorStop(1, tgtColor);

                    ctx.beginPath();
                    ctx.moveTo(s.x, s.y);
                    ctx.lineTo(t.x, t.y);
                    ctx.strokeStyle = grad;
                    ctx.lineWidth = 3 / scale;
                    ctx.stroke();

                    // Arrowhead at target — use target comp color
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
                        ctx.fillStyle = tgtColor;
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
            // GER threshold — hide labels for nodes below threshold
            if (gerHeatmapMode && gerThreshold > 0) {
                var _gerLabelScore = _compLookup[d.ticker] ? _compLookup[d.ticker]._gerScore : null;
                if (_gerLabelScore == null || _gerLabelScore < gerThreshold) return;
            }
            // When sector filter is active, show labels for sector nodes based on zoom
            if (activeLegendSector && sectorNodeSet && sectorNodeSet.has(d.ticker) && !hoveredNode) {
                if (!shouldShowLabel(d, scale * 1.5)) return; // more lenient threshold
            }
            var r = getRadius(d);
            ctx.fillStyle = d === hoveredNode ? labelHoverColor : labelColor;
            ctx.fillText(d.ticker, d.x, d.y + r + 3);
        });

        // === Path Node Pay Badges ===
        // Show compact CEO compensation badge below each path node's ticker label
        _pathBadgeAreas = []; // clear for this frame
        if (activePath && activePath.nodes.length >= 2 && !hoveredNode) {
            var _badgeMinComp = Infinity, _badgeMaxComp = -Infinity;
            activePath.nodes.forEach(function(ticker) {
                var comp = _compLookup[ticker];
                if (comp && comp.total > 0) {
                    if (comp.total < _badgeMinComp) _badgeMinComp = comp.total;
                    if (comp.total > _badgeMaxComp) _badgeMaxComp = comp.total;
                }
            });
            var _badgeCompRange = _badgeMaxComp - _badgeMinComp;

            activePath.nodes.forEach(function(ticker) {
                var n = nodeMap[ticker];
                if (!n) return;
                var comp = _compLookup[ticker];
                if (!comp || !comp.total || comp.total <= 0) return;

                var r = getRadius(n);
                var payText = _fmtComp(comp.total);
                var badgeFontSize = Math.max(8, Math.min(11, 10 / scale));
                ctx.font = '700 ' + badgeFontSize + 'px Inter, system-ui, sans-serif';
                var textWidth = ctx.measureText(payText).width;
                var padX = 5 / scale;
                var padY = 2.5 / scale;
                var badgeW = textWidth + padX * 2;
                var badgeH = badgeFontSize + padY * 2;

                // Position below ticker label (label is at y + r + 3, font ~11px)
                var labelFontSize = Math.max(9, Math.min(12, 11 / scale));
                var badgeX = n.x - badgeW / 2;
                var badgeY = n.y + r + 3 + labelFontSize + 2 / scale;

                // Compute badge background color using same gradient as path edges
                var bgColor;
                if (_badgeCompRange <= 0) {
                    bgColor = 'rgba(168,85,247,0.9)'; // fallback purple
                } else {
                    var t = (comp.total - _badgeMinComp) / _badgeCompRange;
                    var cr, cg, cb;
                    if (t < 0.5) {
                        var s = t * 2;
                        cr = Math.round(6 + s * 244);
                        cg = Math.round(214 - s * 35);
                        cb = Math.round(160 - s * 100);
                    } else {
                        var s = (t - 0.5) * 2;
                        cr = Math.round(250 - s * 11);
                        cg = Math.round(179 - s * 111);
                        cb = Math.round(60 + s * 51);
                    }
                    bgColor = 'rgba(' + cr + ',' + cg + ',' + cb + ',0.92)';
                }

                // Shadow for depth
                ctx.save();
                ctx.shadowColor = 'rgba(0,0,0,0.35)';
                ctx.shadowBlur = 3 / scale;
                ctx.shadowOffsetY = 1 / scale;

                // Draw rounded rectangle badge
                var cornerR = 3 / scale;
                ctx.beginPath();
                ctx.moveTo(badgeX + cornerR, badgeY);
                ctx.lineTo(badgeX + badgeW - cornerR, badgeY);
                ctx.arcTo(badgeX + badgeW, badgeY, badgeX + badgeW, badgeY + cornerR, cornerR);
                ctx.lineTo(badgeX + badgeW, badgeY + badgeH - cornerR);
                ctx.arcTo(badgeX + badgeW, badgeY + badgeH, badgeX + badgeW - cornerR, badgeY + badgeH, cornerR);
                ctx.lineTo(badgeX + cornerR, badgeY + badgeH);
                ctx.arcTo(badgeX, badgeY + badgeH, badgeX, badgeY + badgeH - cornerR, cornerR);
                ctx.lineTo(badgeX, badgeY + cornerR);
                ctx.arcTo(badgeX, badgeY, badgeX + cornerR, badgeY, cornerR);
                ctx.closePath();
                ctx.fillStyle = bgColor;
                ctx.fill();
                ctx.restore();

                // Thin border for crispness
                ctx.beginPath();
                ctx.moveTo(badgeX + cornerR, badgeY);
                ctx.lineTo(badgeX + badgeW - cornerR, badgeY);
                ctx.arcTo(badgeX + badgeW, badgeY, badgeX + badgeW, badgeY + cornerR, cornerR);
                ctx.lineTo(badgeX + badgeW, badgeY + badgeH - cornerR);
                ctx.arcTo(badgeX + badgeW, badgeY + badgeH, badgeX + badgeW - cornerR, badgeY + badgeH, cornerR);
                ctx.lineTo(badgeX + cornerR, badgeY + badgeH);
                ctx.arcTo(badgeX, badgeY + badgeH, badgeX, badgeY + badgeH - cornerR, cornerR);
                ctx.lineTo(badgeX, badgeY + cornerR);
                ctx.arcTo(badgeX, badgeY, badgeX + cornerR, badgeY, cornerR);
                ctx.closePath();
                ctx.strokeStyle = 'rgba(255,255,255,0.25)';
                ctx.lineWidth = 0.5 / scale;
                ctx.stroke();

                // White text for contrast against colored badge
                ctx.fillStyle = '#fff';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.font = '700 ' + badgeFontSize + 'px Inter, system-ui, sans-serif';
                ctx.fillText(payText, n.x, badgeY + badgeH / 2);

                // Store badge hit area (in graph coordinates) for hover detection
                _pathBadgeAreas.push({ ticker: ticker, x: badgeX, y: badgeY, w: badgeW, h: badgeH });
            });
        }

        // === Search Focus Pulsing Ring ===
        if (searchFocusedNode && hoveredNode === searchFocusedNode) {
            var _sfn = searchFocusedNode;
            var _sfr = getRadius(_sfn);
            var elapsed = (performance.now() - searchFocusedTime) / 1000; // seconds
            var pulsePhase = (elapsed % 1.5) / 1.5; // 0-1 over 1.5 seconds
            var pulseRadius = _sfr + (4 + pulsePhase * 12) / scale;
            var pulseAlpha = 0.7 * (1 - pulsePhase);
            if (pulseAlpha > 0.01) {
                ctx.beginPath();
                ctx.arc(_sfn.x, _sfn.y, pulseRadius, 0, 2 * Math.PI);
                ctx.strokeStyle = 'rgba(0, 180, 216, ' + pulseAlpha + ')';
                ctx.lineWidth = (2.5 - pulsePhase * 1.5) / scale;
                ctx.stroke();
            }
            // Static inner ring
            ctx.beginPath();
            ctx.arc(_sfn.x, _sfn.y, _sfr + 3 / scale, 0, 2 * Math.PI);
            ctx.strokeStyle = 'rgba(0, 180, 216, 0.6)';
            ctx.lineWidth = 2 / scale;
            ctx.stroke();
        }

        ctx.restore();

        // === Canvas Path Pay Gradient Legend Overlay ===
        // Render a compact gradient legend in bottom-left corner of canvas when path is active
        if (activePath && activePath.nodes.length >= 2) {
            var _lgMinComp = Infinity, _lgMaxComp = -Infinity;
            activePath.nodes.forEach(function(ticker) {
                var comp = _compLookup[ticker];
                if (comp && comp.total > 0) {
                    if (comp.total < _lgMinComp) _lgMinComp = comp.total;
                    if (comp.total > _lgMaxComp) _lgMaxComp = comp.total;
                }
            });
            if (_lgMaxComp > _lgMinComp) {
                var lgX = 12, lgY = height - 42;
                var lgW = 140, lgH = 32;
                var isDark = document.documentElement.getAttribute('data-theme') !== 'light';
                // Background with rounded corners
                ctx.save();
                ctx.beginPath();
                var lgR = 6;
                ctx.moveTo(lgX + lgR, lgY);
                ctx.lineTo(lgX + lgW - lgR, lgY);
                ctx.arcTo(lgX + lgW, lgY, lgX + lgW, lgY + lgR, lgR);
                ctx.lineTo(lgX + lgW, lgY + lgH - lgR);
                ctx.arcTo(lgX + lgW, lgY + lgH, lgX + lgW - lgR, lgY + lgH, lgR);
                ctx.lineTo(lgX + lgR, lgY + lgH);
                ctx.arcTo(lgX, lgY + lgH, lgX, lgY + lgH - lgR, lgR);
                ctx.lineTo(lgX, lgY + lgR);
                ctx.arcTo(lgX, lgY, lgX + lgR, lgY, lgR);
                ctx.closePath();
                ctx.fillStyle = isDark ? 'rgba(15,23,42,0.85)' : 'rgba(255,255,255,0.9)';
                ctx.fill();
                ctx.strokeStyle = isDark ? 'rgba(148,163,184,0.2)' : 'rgba(0,0,0,0.1)';
                ctx.lineWidth = 1;
                ctx.stroke();

                // Gradient bar
                var barX = lgX + 8, barY = lgY + 6;
                var barW = lgW - 16, barH = 6;
                var grad = ctx.createLinearGradient(barX, 0, barX + barW, 0);
                grad.addColorStop(0, '#06d6a0');
                grad.addColorStop(0.5, '#fabd2f');
                grad.addColorStop(1, '#ef476f');
                ctx.beginPath();
                ctx.roundRect(barX, barY, barW, barH, 3);
                ctx.fillStyle = grad;
                ctx.fill();

                // Min/max labels
                ctx.font = '500 9px Inter, system-ui, sans-serif';
                ctx.textBaseline = 'top';
                ctx.fillStyle = isDark ? 'rgba(226,232,240,0.75)' : 'rgba(30,41,59,0.7)';
                ctx.textAlign = 'left';
                ctx.fillText(_fmtComp(_lgMinComp), barX, barY + barH + 3);
                ctx.textAlign = 'right';
                ctx.fillText(_fmtComp(_lgMaxComp), barX + barW, barY + barH + 3);
                // Center label
                ctx.textAlign = 'center';
                ctx.font = '400 8px Inter, system-ui, sans-serif';
                ctx.fillStyle = isDark ? 'rgba(148,163,184,0.6)' : 'rgba(100,116,139,0.6)';
                ctx.fillText('CEO Pay', barX + barW / 2, barY + barH + 3);
                ctx.restore();
            }
        }
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
                // Find CEO executive record for compensation breakdown
                var ceoBreakdown = null;
                if (c.executives && c.executives.length > 0) {
                    var ceoExec = c.executives.find(function(e) {
                        return e.title && /chief executive|ceo/i.test(e.title);
                    });
                    if (!ceoExec) ceoExec = c.executives[0]; // fallback to first NEO
                    if (ceoExec) {
                        ceoBreakdown = {
                            salary: ceoExec.salary || 0,
                            bonus: ceoExec.bonus || 0,
                            stock: ceoExec.stock_awards || 0,
                            options: ceoExec.option_awards || 0,
                            incentive: ceoExec.non_equity_incentive || 0,
                            pension: ceoExec.pension_nqdc || 0,
                            other: ceoExec.all_other || 0
                        };
                    }
                }
                _compLookup[c.ticker] = {
                    ceo: c.ceo_name || null,
                    total: c.total_compensation || null,
                    ratio: c.pay_ratio || null,
                    worker: c.median_worker_pay || null,
                    sector: c.sector || null,
                    _gerScore: c._gerScore != null ? c._gerScore : null,
                    _gerRisk: c._gerRisk || null,
                    _gerComponents: c._gerComponents || null,
                    _govScore: c._govScore != null ? c._govScore : null,
                    _sopApproval: c._sopApproval != null ? c._sopApproval : null,
                    _breakdown: ceoBreakdown,
                    _ceoPayByYear: null // populated below
                };
                // Build multi-year CEO pay map for trend sparklines
                if (c.executives && c.executives.length > 0) {
                    var _cpby = {};
                    c.executives.forEach(function(e) {
                        if (e.title && /chief executive|ceo/i.test(e.title) && e.year && e.total > 0) {
                            if (!_cpby[e.year] || e.total > _cpby[e.year]) _cpby[e.year] = e.total;
                        }
                    });
                    if (Object.keys(_cpby).length > 0) _compLookup[c.ticker]._ceoPayByYear = _cpby;
                }
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

    // Governance Erosion Risk heatmap color — green→yellow→orange→red gradient
    // Low risk = green, moderate = yellow, high = orange, critical = red
    function getGERHeatmapColor(ticker) {
        var comp = _compLookup[ticker];
        if (!comp || comp._gerScore == null) return '#555';
        var score = comp._gerScore;
        // GER ranges from 0–100; normalize
        var t = Math.min(score / 100, 1);
        var r, g, b;
        if (t < 0.3) {
            // Green (low) → Yellow-green (moderate)
            var t2 = t / 0.3;
            r = Math.round(6 + t2 * (180 - 6));
            g = Math.round(214 + t2 * (209 - 214));
            b = Math.round(160 - t2 * 130);
        } else if (t < 0.6) {
            // Yellow-green → Orange (elevated/high)
            var t2 = (t - 0.3) / 0.3;
            r = Math.round(180 + t2 * (251 - 180));
            g = Math.round(209 - t2 * (209 - 146));
            b = Math.round(30 + t2 * (60 - 30));
        } else {
            // Orange → Red (critical)
            var t2 = (t - 0.6) / 0.4;
            r = Math.round(251 - t2 * (251 - 220));
            g = Math.round(146 - t2 * (146 - 38));
            b = Math.round(60 - t2 * 22);
        }
        return 'rgb(' + r + ',' + g + ',' + b + ')';
    }

    // Unified node color resolver: checks heatmap modes first, then sector
    function getNodeColor(ticker, sector) {
        if (communityMode) return getCommunityColor(ticker);
        if (gerHeatmapMode) return getGERHeatmapColor(ticker);
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
        // Show community info when community mode is active
        if (communityMode) {
            var cid = communityOf[d.ticker];
            var cStat = communityStats.find(function(cs) { return cs.id === cid; });
            if (cStat) {
                var cIdx = communityStats.indexOf(cStat) + 1;
                html += '<div class="tt-row"><span class="tt-label">Community</span><span class="tt-value" style="color:' + cStat.color + '">' + cStat.label + ' (' + cStat.size + ' companies)</span></div>';
                if (cStat.sectors.length > 0) {
                    html += '<div class="tt-row"><span class="tt-label">Top sectors</span><span class="tt-value">' + cStat.sectors.slice(0, 3).map(function(s) { return s.name.replace(/^(.{12}).+/, '$1…') + ' ' + s.count; }).join(', ') + '</span></div>';
                }
            }
        }
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
        // Governance Erosion Risk
        if (comp && comp._gerScore != null) {
            var gerVal = comp._gerScore;
            var gerRisk = comp._gerRisk || '';
            var gerCls = gerVal >= 75 ? 'tt-ger-critical' : gerVal >= 60 ? 'tt-ger-high' : gerVal >= 45 ? 'tt-ger-elevated' : gerVal >= 30 ? 'tt-ger-moderate' : 'tt-ger-low';
            html += '<div class="tt-row"><span class="tt-label">GER Risk</span><span class="tt-value ' + gerCls + '">' + gerVal + '/100 <span class="tt-cc-label">' + gerRisk + '</span></span></div>';
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

    // Path badge tooltip — shows CEO name + full compensation breakdown
    function _showPathBadgeTooltip(mx, my, ticker) {
        var comp = _compLookup[ticker];
        if (!comp) return;
        var n = nodeMap[ticker];
        var html = '<div class="tt-title">' + ticker + (n ? ' — ' + n.name : '') + '</div>';
        html += '<div class="tt-comp-section">';
        if (comp.ceo) {
            html += '<div class="tt-comp-ceo" style="margin-bottom:4px;font-weight:600">' + comp.ceo + '</div>';
        }
        html += '<div class="tt-row"><span class="tt-label">Total CEO Pay</span><span class="tt-value tt-comp-value">' + _fmtComp(comp.total) + '</span></div>';
        // Breakdown
        if (comp._breakdown) {
            var bd = comp._breakdown;
            var tot = comp.total || 1;
            var rows = [];
            if (bd.salary > 0) rows.push({ label: 'Salary', val: bd.salary });
            if (bd.bonus > 0) rows.push({ label: 'Bonus', val: bd.bonus });
            if (bd.stock > 0) rows.push({ label: 'Stock Awards', val: bd.stock });
            if (bd.options > 0) rows.push({ label: 'Option Awards', val: bd.options });
            if (bd.incentive > 0) rows.push({ label: 'Non-Equity Incentive', val: bd.incentive });
            if (bd.pension > 0) rows.push({ label: 'Pension/NQDC', val: bd.pension });
            if (bd.other > 0) rows.push({ label: 'All Other', val: bd.other });
            if (rows.length > 0) {
                html += '<div class="tt-badge-breakdown">';
                rows.forEach(function(r) {
                    var pct = (r.val / tot * 100).toFixed(0);
                    var barW = Math.max(2, Math.min(100, r.val / tot * 100));
                    html += '<div class="tt-bd-row">';
                    html += '<span class="tt-bd-label">' + r.label + '</span>';
                    html += '<span class="tt-bd-bar-wrap"><span class="tt-bd-bar" style="width:' + barW + '%"></span></span>';
                    html += '<span class="tt-bd-val">' + _fmtComp(r.val) + ' <span class="tt-bd-pct">(' + pct + '%)</span></span>';
                    html += '</div>';
                });
                html += '</div>';
            }
        }
        // Peer rank context on path
        if (activePath && activePath.nodes.length >= 2) {
            var pathComps = [];
            activePath.nodes.forEach(function(t) {
                var c = _compLookup[t];
                if (c && c.total > 0) pathComps.push({ ticker: t, total: c.total });
            });
            pathComps.sort(function(a, b) { return b.total - a.total; });
            var rank = pathComps.findIndex(function(p) { return p.ticker === ticker; }) + 1;
            if (rank > 0) {
                html += '<div class="tt-row" style="margin-top:4px"><span class="tt-label">Path rank</span><span class="tt-value">#' + rank + ' of ' + pathComps.length + '</span></div>';
            }
        }
        html += '</div>';
        tooltip.innerHTML = html;
        tooltip.classList.add('visible');
        tooltip.style.left = (mx + 12) + 'px';
        tooltip.style.top = (my - 10) + 'px';
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
            _pathBadgeHovered = null; // clear badge hover when node changes
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

        // Path badge hover detection — show rich tooltip on badge hover
        if (!found && !dragNode && _pathBadgeAreas.length > 0) {
            var pt = transform.invert([mx, my]);
            var gx = pt[0], gy = pt[1];
            var hitBadge = null;
            for (var bi = 0; bi < _pathBadgeAreas.length; bi++) {
                var ba = _pathBadgeAreas[bi];
                if (gx >= ba.x && gx <= ba.x + ba.w && gy >= ba.y && gy <= ba.y + ba.h) {
                    hitBadge = ba.ticker;
                    break;
                }
            }
            if (hitBadge !== _pathBadgeHovered) {
                _pathBadgeHovered = hitBadge;
                if (hitBadge) {
                    canvas.style.cursor = 'pointer';
                    _showPathBadgeTooltip(event.clientX, event.clientY, hitBadge);
                } else {
                    canvas.style.cursor = 'grab';
                    hideTooltip();
                }
            } else if (hitBadge) {
                tooltip.style.left = (event.clientX + 12) + 'px';
                tooltip.style.top = (event.clientY - 10) + 'px';
            }
        } else if (_pathBadgeHovered && found) {
            _pathBadgeHovered = null;
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

        // If this was a click (not a drag) on empty space, clear search focus
        if (!clickedNode && !wasDrag && searchFocusedNode) {
            _stopPulseAnimation();
            draw();
        }

        // If this was a click (not a drag) on a node, navigate to company detail
        if (clickedNode && !wasDrag && window.findCompanyInTable) {
            _stopPulseAnimation();
            hideTooltip();
            window.findCompanyInTable(clickedNode.ticker);
        }

        // If this was a click (not a drag) on a path badge, navigate to that company
        if (!clickedNode && !wasDrag && _pathBadgeHovered && window.findCompanyInTable) {
            hideTooltip();
            window.findCompanyInTable(_pathBadgeHovered);
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
        } else if (_pathBadgeAreas.length > 0) {
            // Touch on empty space — check for path badge tap
            var pt = transform.invert([mx, my]);
            var gx = pt[0], gy = pt[1];
            var hitBadge = null;
            for (var bi = 0; bi < _pathBadgeAreas.length; bi++) {
                var ba = _pathBadgeAreas[bi];
                if (gx >= ba.x && gx <= ba.x + ba.w && gy >= ba.y && gy <= ba.y + ba.h) {
                    hitBadge = ba.ticker;
                    break;
                }
            }
            if (hitBadge && window.findCompanyInTable) {
                window.findCompanyInTable(hitBadge);
                if (navigator.vibrate) navigator.vibrate(15);
            }
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
        searchFocusedNode = node;
        searchFocusedTime = performance.now();
        showTooltip(width / 2 + 12, height / 2 - 10, node);
        draw();
        // Start pulse animation loop
        _startPulseAnimation();
    }

    var _pulseAnimFrame = null;
    function _startPulseAnimation() {
        if (_pulseAnimFrame) cancelAnimationFrame(_pulseAnimFrame);
        var startTime = searchFocusedTime;
        function _pulseLoop() {
            if (!searchFocusedNode || searchFocusedTime !== startTime) return;
            draw();
            _pulseAnimFrame = requestAnimationFrame(_pulseLoop);
        }
        _pulseAnimFrame = requestAnimationFrame(_pulseLoop);
    }

    function _stopPulseAnimation() {
        searchFocusedNode = null;
        if (_pulseAnimFrame) {
            cancelAnimationFrame(_pulseAnimFrame);
            _pulseAnimFrame = null;
        }
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
                _stopPulseAnimation();
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
                if ((compHeatmapMode || prHeatmapMode || ccHeatmapMode || gerHeatmapMode || communityMode) && activeIdx >= 0 && activeIdx < items.length) {
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
                if ((compHeatmapMode || prHeatmapMode || ccHeatmapMode || gerHeatmapMode || communityMode) && activeIdx >= 0 && activeIdx < items.length) {
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
                searchInput.value = '';
                _stopPulseAnimation();
                hoveredNode = null;
                hideTooltip();
                draw();
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
    var gerHeatmapToggle = document.getElementById('ger-heatmap-toggle');
    var gerHeatmapLegendEl = document.getElementById('ger-heatmap-legend');

    if (compHeatmapToggle) {
        compHeatmapToggle.addEventListener('click', function() {
            compHeatmapMode = !compHeatmapMode;
            // Mutual exclusion: turn off PageRank, clustering, and community heatmaps
            if (compHeatmapMode) _clearCommunityMode();
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
            if (compHeatmapMode && gerHeatmapMode) {
                gerHeatmapMode = false;
                if (gerHeatmapToggle) gerHeatmapToggle.classList.remove('active');
                if (gerHeatmapLegendEl) gerHeatmapLegendEl.style.display = 'none';
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
            // Mutual exclusion: turn off comp, clustering, and community heatmaps
            if (prHeatmapMode) _clearCommunityMode();
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
            if (prHeatmapMode && gerHeatmapMode) {
                gerHeatmapMode = false;
                if (gerHeatmapToggle) gerHeatmapToggle.classList.remove('active');
                if (gerHeatmapLegendEl) gerHeatmapLegendEl.style.display = 'none';
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
            // Mutual exclusion: turn off comp, PageRank, and community heatmaps
            if (ccHeatmapMode) _clearCommunityMode();
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
            if (ccHeatmapMode && gerHeatmapMode) {
                gerHeatmapMode = false;
                if (gerHeatmapToggle) gerHeatmapToggle.classList.remove('active');
                if (gerHeatmapLegendEl) gerHeatmapLegendEl.style.display = 'none';
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

    // Governance Erosion Risk heatmap toggle
    if (gerHeatmapToggle) {
        gerHeatmapToggle.addEventListener('click', function() {
            gerHeatmapMode = !gerHeatmapMode;
            // Mutual exclusion: turn off comp, PageRank, clustering, and community heatmaps
            if (gerHeatmapMode) _clearCommunityMode();
            if (gerHeatmapMode && compHeatmapMode) {
                compHeatmapMode = false;
                if (compHeatmapToggle) compHeatmapToggle.classList.remove('active');
                if (compHeatmapLegendEl) compHeatmapLegendEl.style.display = 'none';
            }
            if (gerHeatmapMode && prHeatmapMode) {
                prHeatmapMode = false;
                if (prHeatmapToggle) prHeatmapToggle.classList.remove('active');
                if (prHeatmapLegendEl) prHeatmapLegendEl.style.display = 'none';
            }
            if (gerHeatmapMode && ccHeatmapMode) {
                ccHeatmapMode = false;
                if (ccHeatmapToggle) ccHeatmapToggle.classList.remove('active');
                if (ccHeatmapLegendEl) ccHeatmapLegendEl.style.display = 'none';
            }
            gerHeatmapToggle.classList.toggle('active', gerHeatmapMode);
            if (gerHeatmapLegendEl) gerHeatmapLegendEl.style.display = gerHeatmapMode ? 'flex' : 'none';
            // Reset threshold when turning off GER mode
            if (!gerHeatmapMode) {
                gerThreshold = 0;
                var _gSlider = document.getElementById('ger-threshold-slider');
                var _gVal = document.getElementById('ger-threshold-value');
                var _gCount = document.getElementById('ger-threshold-count');
                if (_gSlider) _gSlider.value = 0;
                if (_gVal) _gVal.textContent = '0';
                if (_gCount) _gCount.textContent = '';
            } else {
                _updateGerThresholdCount();
            }
            draw();
            announce(gerHeatmapMode ? 'Governance erosion risk heatmap enabled — green = low risk, red = critical' : 'Sector coloring restored');
            if (activeLegendSector) updateClusterStats(activeLegendSector);
        });
    }

    // GER threshold slider — filter network nodes by minimum GER score
    var gerThresholdSlider = document.getElementById('ger-threshold-slider');
    var gerThresholdValueEl = document.getElementById('ger-threshold-value');
    var gerThresholdCountEl = document.getElementById('ger-threshold-count');

    function _updateGerThresholdCount() {
        if (!gerThresholdCountEl) return;
        if (!gerHeatmapMode || gerThreshold === 0) {
            gerThresholdCountEl.textContent = '';
            return;
        }
        var aboveCount = 0;
        nodes.forEach(function(n) {
            var s = _compLookup[n.ticker] ? _compLookup[n.ticker]._gerScore : null;
            if (s != null && s >= gerThreshold) aboveCount++;
        });
        gerThresholdCountEl.textContent = '(' + aboveCount + ' of ' + nodes.length + ' visible)';
    }

    if (gerThresholdSlider) {
        gerThresholdSlider.addEventListener('input', function() {
            gerThreshold = parseInt(this.value, 10);
            if (gerThresholdValueEl) gerThresholdValueEl.textContent = gerThreshold;
            _updateGerThresholdCount();
            draw();
        });
        gerThresholdSlider.addEventListener('change', function() {
            if (typeof announce === 'function') {
                if (gerThreshold > 0) {
                    var count = 0;
                    nodes.forEach(function(n) {
                        var s = _compLookup[n.ticker] ? _compLookup[n.ticker]._gerScore : null;
                        if (s != null && s >= gerThreshold) count++;
                    });
                    announce('Network filtered to ' + count + ' companies with GER score ' + gerThreshold + ' or above');
                } else {
                    announce('Network filter cleared — showing all companies');
                }
            }
        });
    }

    // === Community Detection Toggle ===
    var communityToggle = document.getElementById('community-toggle');
    var communityLegendEl = document.getElementById('community-legend');

    if (communityToggle) {
        communityToggle.addEventListener('click', function() {
            communityMode = !communityMode;
            // Mutual exclusion: turn off all other heatmap modes
            if (communityMode) {
                if (compHeatmapMode) {
                    compHeatmapMode = false;
                    if (compHeatmapToggle) compHeatmapToggle.classList.remove('active');
                    if (compHeatmapLegendEl) compHeatmapLegendEl.style.display = 'none';
                }
                if (prHeatmapMode) {
                    prHeatmapMode = false;
                    if (prHeatmapToggle) prHeatmapToggle.classList.remove('active');
                    if (prHeatmapLegendEl) prHeatmapLegendEl.style.display = 'none';
                }
                if (ccHeatmapMode) {
                    ccHeatmapMode = false;
                    if (ccHeatmapToggle) ccHeatmapToggle.classList.remove('active');
                    if (ccHeatmapLegendEl) ccHeatmapLegendEl.style.display = 'none';
                }
                if (gerHeatmapMode) {
                    gerHeatmapMode = false;
                    if (gerHeatmapToggle) gerHeatmapToggle.classList.remove('active');
                    if (gerHeatmapLegendEl) gerHeatmapLegendEl.style.display = 'none';
                    gerThreshold = 0;
                    var _gs = document.getElementById('ger-threshold-slider');
                    if (_gs) _gs.value = 0;
                    var _gv = document.getElementById('ger-threshold-value');
                    if (_gv) _gv.textContent = '0';
                    var _gc = document.getElementById('ger-threshold-count');
                    if (_gc) _gc.textContent = '';
                }
            }
            communityToggle.classList.toggle('active', communityMode);
            if (communityLegendEl) {
                communityLegendEl.style.display = communityMode ? 'block' : 'none';
                if (communityMode) _populateCommunityLegend();
            }
            if (communityMode) {
                _renderCommunityMetrics();
                _renderCommunityFlowMatrix();
            } else {
                _removeCommunityMetrics();
            }
            draw();
            var annMsg = communityMode
                ? 'Community detection enabled — ' + communityStats.length + ' clusters detected (modularity ' + communityModularity.toFixed(2) + ')'
                : 'Sector coloring restored';
            announce(annMsg);
            if (activeLegendSector) updateClusterStats(activeLegendSector);
        });
    }

    // Also update mutual exclusion in existing toggles to turn off community mode
    function _clearCommunityMode() {
        if (communityMode) {
            communityMode = false;
            if (communityToggle) communityToggle.classList.remove('active');
            if (communityLegendEl) communityLegendEl.style.display = 'none';
            _removeCommunityMetrics();
        }
    }

    // Build community legend HTML: show top clusters with color, size, dominant sectors
    function _populateCommunityLegend() {
        if (!communityLegendEl) return;
        var maxShow = Math.min(communityStats.length, 12);
        var html = '<div class="community-legend-header">';
        html += '<span class="community-legend-title">Louvain Communities</span>';
        html += '<span class="community-legend-modularity">Q = ' + communityModularity.toFixed(3) + '</span>';
        html += '</div>';
        html += '<div class="community-legend-items">';
        for (var i = 0; i < maxShow; i++) {
            var cs = communityStats[i];
            var topSectors = cs.sectors.slice(0, 2).map(function(s) {
                // Abbreviate sector names
                var shortName = s.name.replace('Information Technology', 'IT')
                    .replace('Communication Services', 'Comm')
                    .replace('Consumer Discretionary', 'Cons Disc')
                    .replace('Consumer Staples', 'Cons Stap')
                    .replace('Health Care', 'Health')
                    .replace('Real Estate', 'Real Est');
                return shortName + ' ' + s.count;
            }).join(', ');
            html += '<span class="community-legend-item" data-community="' + cs.id + '" title="' + cs.size + ' companies — top sectors: ' + cs.sectors.slice(0, 3).map(function(s) { return s.name + ' (' + s.count + ')'; }).join(', ') + '">';
            html += '<span class="legend-dot" style="background:' + cs.color + '"></span>';
            html += '<span class="community-legend-label">' + cs.label + '</span>';
            html += '<span class="community-legend-size">' + cs.size + '</span>';
            html += '<span class="community-legend-sectors">' + topSectors + '</span>';
            html += '</span>';
        }
        if (communityStats.length > maxShow) {
            var remaining = communityStats.slice(maxShow).reduce(function(s, c) { return s + c.size; }, 0);
            html += '<span class="community-legend-item community-legend-more">+' + (communityStats.length - maxShow) + ' more (' + remaining + ' nodes)</span>';
        }
        html += '</div>';
        communityLegendEl.innerHTML = html;

        // Wire click handlers on community legend items to filter the compensation table
        communityLegendEl.querySelectorAll('.community-legend-item[data-community]').forEach(function(item) {
            item.style.cursor = 'pointer';
            item.addEventListener('click', function(e) {
                e.stopPropagation();
                var cid = parseInt(item.dataset.community);
                var cs = communityStats.find(function(s) { return s.id === cid; });
                if (!cs) return;

                // Toggle: if already filtering this community, clear
                var isActive = item.classList.contains('community-legend-active');
                communityLegendEl.querySelectorAll('.community-legend-item').forEach(function(el) {
                    el.classList.remove('community-legend-active');
                });

                if (isActive) {
                    // Clear community filter
                    window._activeCommunityFilter = null;
                    window._activeCommunityScatterTickers = null;
                    if (typeof renderTable === 'function') renderTable(window._chartData.companies);
                    // Redraw scatter to clear community highlight
                    var scEl = document.getElementById('scatter-chart');
                    if (scEl) scEl.innerHTML = '';
                    if (typeof drawScatterChart === 'function' && window._chartData) drawScatterChart(window._chartData.companies);
                    if (typeof announce === 'function') announce('Community filter cleared');
                } else {
                    // Set community filter
                    item.classList.add('community-legend-active');
                    window._activeCommunityFilter = { tickers: cs.tickers, label: cs.label, id: cid };
                    window._activeCommunityScatterTickers = new Set(cs.tickers);
                    if (typeof window._clearPersistentScatterHighlight === 'function') window._clearPersistentScatterHighlight();
                    if (typeof renderTable === 'function') renderTable(window._chartData.companies);
                    // Redraw scatter to highlight community tickers
                    var scEl2 = document.getElementById('scatter-chart');
                    if (scEl2) scEl2.innerHTML = '';
                    if (typeof drawScatterChart === 'function' && window._chartData) drawScatterChart(window._chartData.companies);
                    // Scroll to table
                    var tableSection = document.getElementById('compensation-table-section');
                    if (tableSection) {
                        var hdr = document.querySelector('.sticky-header, header');
                        var off = hdr ? hdr.offsetHeight : 0;
                        var top = tableSection.getBoundingClientRect().top + window.scrollY - off - 12;
                        window.scrollTo({ top: top, behavior: typeof getScrollBehavior === 'function' ? getScrollBehavior() : 'smooth' });
                    }
                    if (typeof announce === 'function') announce('Filtered to ' + cs.tickers.length + ' companies in ' + cs.label);
                }
            });

            // Hover handlers: highlight community nodes on the network graph + floating tooltip
            item.addEventListener('mouseenter', function() {
                var cid = parseInt(item.dataset.community);
                var cs = communityStats.find(function(s) { return s.id === cid; });
                if (!cs) return;
                _hoveredCommunityId = cid;
                _hoveredCommunityTickers = new Set(cs.tickers);
                item.classList.add('community-legend-hover');
                draw();
                _showCommunityTooltip(cs, item);
            });
            item.addEventListener('mouseleave', function() {
                _hoveredCommunityId = null;
                _hoveredCommunityTickers = null;
                item.classList.remove('community-legend-hover');
                draw();
                _hideCommunityTooltip();
            });
        });
    }

    // === Community Hover Floating Tooltip ===
    var _communityTooltipEl = null;

    function _ensureCommunityTooltip() {
        if (_communityTooltipEl) return _communityTooltipEl;
        _communityTooltipEl = document.createElement('div');
        _communityTooltipEl.className = 'community-hover-tooltip';
        _communityTooltipEl.setAttribute('role', 'tooltip');
        document.body.appendChild(_communityTooltipEl);
        return _communityTooltipEl;
    }

    function _showCommunityTooltip(cs, anchorEl) {
        var tip = _ensureCommunityTooltip();

        // Compute median CEO pay for this community
        var payVals = [];
        cs.tickers.forEach(function(t) {
            var c = _compLookup[t];
            if (c && c.total != null && c.total > 0) payVals.push(c.total);
        });
        payVals.sort(function(a, b) { return a - b; });
        var medianPay = null;
        if (payVals.length > 0) {
            var mid = Math.floor(payVals.length / 2);
            medianPay = payVals.length % 2 === 0
                ? (payVals[mid - 1] + payVals[mid]) / 2
                : payVals[mid];
        }

        // Compute average in-degree (connectivity) for this community
        var totalInDeg = 0;
        cs.tickers.forEach(function(t) {
            var n = nodeMap[t];
            if (n) totalInDeg += (n.in_degree || 0);
        });
        var avgInDeg = cs.size > 0 ? (totalInDeg / cs.size).toFixed(1) : '—';

        // Top company by in-degree
        var topNode = nodeMap[cs.topTicker];
        var topName = topNode ? topNode.name : cs.topTicker;
        var topComp = _compLookup[cs.topTicker];
        var topPay = topComp && topComp.total ? _fmtComp(topComp.total) : '—';

        // Intra-community edge density
        var intraEdges = 0;
        var tickerSet = new Set(cs.tickers);
        allEdges.forEach(function(e) {
            if (tickerSet.has(e.source) && tickerSet.has(e.target)) intraEdges++;
        });
        var maxEdges = cs.size * (cs.size - 1);
        var density = maxEdges > 0 ? (intraEdges / maxEdges * 100).toFixed(1) : '0';

        // Build tooltip HTML
        var html = '<div class="comm-tip-header">';
        html += '<span class="comm-tip-color" style="background:' + cs.color + '"></span>';
        html += '<span class="comm-tip-name">' + cs.label + '</span>';
        html += '<span class="comm-tip-size">' + cs.size + ' companies</span>';
        html += '</div>';

        // Sectors
        html += '<div class="comm-tip-section">';
        html += '<div class="comm-tip-section-label">Top Sectors</div>';
        var maxSectors = Math.min(cs.sectors.length, 3);
        for (var i = 0; i < maxSectors; i++) {
            var sec = cs.sectors[i];
            var secColor = SECTOR_COLORS[sec.name] || '#94a3b8';
            var pct = (sec.count / cs.size * 100).toFixed(0);
            html += '<div class="comm-tip-sector">';
            html += '<span class="comm-tip-sector-dot" style="background:' + secColor + '"></span>';
            html += '<span class="comm-tip-sector-name">' + sec.name + '</span>';
            html += '<span class="comm-tip-sector-count">' + sec.count + ' (' + pct + '%)</span>';
            html += '</div>';
        }
        html += '</div>';

        // Stats
        html += '<div class="comm-tip-stats">';
        if (medianPay != null) {
            html += '<div class="comm-tip-stat"><span class="comm-tip-stat-label">Median CEO Pay</span><span class="comm-tip-stat-value">' + _fmtComp(medianPay) + '</span></div>';
        }
        html += '<div class="comm-tip-stat"><span class="comm-tip-stat-label">Avg Connections</span><span class="comm-tip-stat-value">' + avgInDeg + '</span></div>';
        html += '<div class="comm-tip-stat"><span class="comm-tip-stat-label">Edge Density</span><span class="comm-tip-stat-value">' + density + '%</span></div>';
        html += '</div>';

        // Top company
        html += '<div class="comm-tip-top">';
        html += '<span class="comm-tip-top-label">Most Benchmarked</span>';
        html += '<span class="comm-tip-top-company">' + cs.topTicker + ' — ' + _truncName(topName, 22) + '</span>';
        html += '<span class="comm-tip-top-pay">' + topPay + '</span>';
        html += '</div>';

        tip.innerHTML = html;
        tip.style.display = 'block';

        // Position tooltip near the anchor element
        var rect = anchorEl.getBoundingClientRect();
        var tipW = tip.offsetWidth;
        var tipH = tip.offsetHeight;
        var left = rect.left + rect.width / 2 - tipW / 2;
        var top = rect.bottom + 8;

        // Keep within viewport
        if (left < 8) left = 8;
        if (left + tipW > window.innerWidth - 8) left = window.innerWidth - tipW - 8;
        if (top + tipH > window.innerHeight - 8) {
            top = rect.top - tipH - 8; // flip above
        }

        tip.style.left = left + 'px';
        tip.style.top = top + 'px';
    }

    function _hideCommunityTooltip() {
        if (_communityTooltipEl) {
            _communityTooltipEl.style.display = 'none';
        }
    }

    // === Community Aggregate Metrics Panel ===
    // Compact sortable table showing per-community compensation stats when community mode is active.
    var _communityMetricsEl = null;
    var _cmSortCol = 'medianPay';
    var _cmSortAsc = false;
    var _communityFlowEl = null;
    var _hoveredFlowCell = null; // {from: communityId, to: communityId} for edge highlight on canvas
    var _cfNormMode = 'raw'; // flow matrix normalize toggle: 'raw' | 'row' | 'col'
    var _cfCellEdgeDetails = null; // NxN array of {ticker: outCount} maps for tooltip
    var _cmPathFrom = null; // community id selected as path-finder "from" endpoint

    function _median(arr) {
        if (!arr || arr.length === 0) return null;
        var s = arr.slice().sort(function(a, b) { return a - b; });
        var m = Math.floor(s.length / 2);
        return s.length % 2 === 0 ? (s[m - 1] + s[m]) / 2 : s[m];
    }

    function _quartiles(arr) {
        if (!arr || arr.length === 0) return null;
        var s = arr.slice().sort(function(a, b) { return a - b; });
        var n = s.length;
        function q(p) {
            var idx = (n - 1) * p;
            var lo = Math.floor(idx), hi = Math.ceil(idx), frac = idx - lo;
            return lo === hi ? s[lo] : s[lo] * (1 - frac) + s[hi] * frac;
        }
        return { min: s[0], q1: q(0.25), median: q(0.5), q3: q(0.75), max: s[n - 1] };
    }

    function _renderCommunityMetrics() {
        // Remove old panel
        if (_communityMetricsEl && _communityMetricsEl.parentNode) {
            _communityMetricsEl.parentNode.removeChild(_communityMetricsEl);
        }
        if (!communityMode || !communityStats || communityStats.length === 0) return;

        var dark = document.documentElement.getAttribute('data-theme') !== 'light';

        // Compute aggregate stats for each community
        var rows = [];
        var maxShow = Math.min(communityStats.length, 12);
        for (var i = 0; i < maxShow; i++) {
            var cs = communityStats[i];
            var payVals = [], gerVals = [], govVals = [], sopVals = [];
            var sectorCounts = {};
            var intraEdges = 0;
            var tickerSet = new Set(cs.tickers);
            cs.tickers.forEach(function(t) {
                var c = _compLookup[t];
                if (!c) return;
                if (c.total != null && c.total > 0) payVals.push(c.total);
                if (c._gerScore != null) gerVals.push(c._gerScore);
                if (c._govScore != null) govVals.push(c._govScore);
                if (c._sopApproval != null) sopVals.push(c._sopApproval);
                if (c.sector) sectorCounts[c.sector] = (sectorCounts[c.sector] || 0) + 1;
            });
            allEdges.forEach(function(e) {
                if (tickerSet.has(e.source) && tickerSet.has(e.target)) intraEdges++;
            });
            var maxEdges = cs.size * (cs.size - 1);
            var density = maxEdges > 0 ? (intraEdges / maxEdges * 100) : 0;

            // Find dominant sector
            var topSector = null, topSectorCount = 0;
            for (var sec in sectorCounts) {
                if (sectorCounts[sec] > topSectorCount) { topSectorCount = sectorCounts[sec]; topSector = sec; }
            }
            var topSectorPct = cs.size > 0 ? (topSectorCount / cs.size * 100) : 0;

            // Compute multi-year CEO pay trend per community (median CEO pay per year)
            var _yearPayMap = {}; // year -> [payValues]
            cs.tickers.forEach(function(t) {
                var c = _compLookup[t];
                if (!c || !c._ceoPayByYear) return;
                for (var yr in c._ceoPayByYear) {
                    if (!_yearPayMap[yr]) _yearPayMap[yr] = [];
                    _yearPayMap[yr].push(c._ceoPayByYear[yr]);
                }
            });
            // Build sorted trend array: [{year, medianPay, count}]
            var _trendYears = Object.keys(_yearPayMap).map(Number).sort();
            var _trendData = [];
            _trendYears.forEach(function(yr) {
                var vals = _yearPayMap[yr];
                if (vals.length >= 3) { // only include years with enough data
                    _trendData.push({ year: yr, median: _median(vals), count: vals.length });
                }
            });
            // Compute 3-year delta (most recent vs oldest in trend)
            var _trendDelta = null;
            if (_trendData.length >= 2) {
                var oldest = _trendData[0].median;
                var newest = _trendData[_trendData.length - 1].median;
                if (oldest > 0) _trendDelta = ((newest - oldest) / oldest * 100);
            }

            rows.push({
                id: cs.id,
                label: cs.label,
                color: cs.color,
                size: cs.size,
                medianPay: _median(payVals),
                payDist: _quartiles(payVals),
                medianGov: _median(govVals),
                medianSop: _median(sopVals),
                medianGer: _median(gerVals),
                density: density,
                topSector: topSector,
                topSectorPct: topSectorPct,
                topSectorColor: SECTOR_COLORS[topSector] || '#94a3b8',
                tickers: cs.tickers,
                trend: _trendData,
                trendDelta: _trendDelta
            });
        }

        // Sort rows
        rows.sort(function(a, b) {
            var va, vb;
            switch (_cmSortCol) {
                case 'label': va = a.label; vb = b.label; return _cmSortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
                case 'size': va = a.size; vb = b.size; break;
                case 'medianPay': va = a.medianPay || 0; vb = b.medianPay || 0; break;
                case 'medianGov': va = a.medianGov || 0; vb = b.medianGov || 0; break;
                case 'medianSop': va = a.medianSop || 0; vb = b.medianSop || 0; break;
                case 'medianGer': va = a.medianGer || 0; vb = b.medianGer || 0; break;
                case 'density': va = a.density; vb = b.density; break;
                case 'payDist': va = a.payDist ? (a.payDist.q3 - a.payDist.q1) : 0; vb = b.payDist ? (b.payDist.q3 - b.payDist.q1) : 0; break;
                case 'trend': va = a.trendDelta != null ? a.trendDelta : -9999; vb = b.trendDelta != null ? b.trendDelta : -9999; break;
                default: va = a.medianPay || 0; vb = b.medianPay || 0;
            }
            return _cmSortAsc ? va - vb : vb - va;
        });

        // Build table
        _communityMetricsEl = document.createElement('div');
        _communityMetricsEl.className = 'community-metrics-panel';

        var cols = [
            { key: 'label', label: 'Community', align: 'left' },
            { key: 'size', label: '#', align: 'right' },
            { key: 'medianPay', label: 'Med Pay', align: 'right' },
            { key: 'trend', label: 'Trend', align: 'left' },
            { key: 'payDist', label: 'Spread', align: 'left' },
            { key: 'medianGov', label: 'Gov', align: 'right' },
            { key: 'medianSop', label: 'SoP%', align: 'right' },
            { key: 'medianGer', label: 'GER', align: 'right' },
            { key: 'density', label: 'Density', align: 'right' }
        ];

        var html = '<div class="cm-header">Community Compensation Comparison</div>';
        html += '<div class="cm-table"><div class="cm-row cm-head">';
        cols.forEach(function(col) {
            var isSorted = _cmSortCol === col.key;
            var arrow = isSorted ? (_cmSortAsc ? ' ▲' : ' ▼') : '';
            html += '<div class="cm-cell cm-th' + (col.align === 'right' ? ' cm-right' : '') + (isSorted ? ' cm-sorted' : '') + '" data-cm-sort="' + col.key + '" role="columnheader" tabindex="0" title="Sort by ' + col.label + '">' + col.label + arrow + '</div>';
        });
        html += '</div>';

        // Find max medianPay for bar scaling
        var maxPay = 0;
        rows.forEach(function(r) { if (r.medianPay && r.medianPay > maxPay) maxPay = r.medianPay; });

        // Find global max pay for box plot scale
        var globalMaxPay = 0;
        rows.forEach(function(r) { if (r.payDist && r.payDist.max > globalMaxPay) globalMaxPay = r.payDist.max; });

        rows.forEach(function(r, ri) {
            html += '<div class="cm-row cm-data" data-cm-community="' + r.id + '" data-cm-idx="' + ri + '">';
            // Community name cell with color dot + path button
            html += '<div class="cm-cell cm-name-cell">';
            html += '<span class="cm-dot" style="background:' + r.color + '"></span>';
            html += '<span class="cm-label">' + r.label + '</span>';
            html += '<button class="cm-path-btn" data-cm-path-cid="' + r.id + '" title="Find path to another community" aria-label="Find path from ' + r.label + '">⇄</button>';
            html += '</div>';
            // Size
            html += '<div class="cm-cell cm-right">' + r.size + '</div>';
            // Median pay with inline bar
            html += '<div class="cm-cell cm-right cm-pay-cell">';
            if (r.medianPay != null) {
                var barW = maxPay > 0 ? (r.medianPay / maxPay * 100) : 0;
                html += '<div class="cm-pay-bar" style="width:' + barW.toFixed(1) + '%;background:' + r.color + '"></div>';
                html += '<span class="cm-pay-val">' + _fmtComp(r.medianPay) + '</span>';
            } else {
                html += '<span class="cm-pay-val">—</span>';
            }
            html += '</div>';
            // 3-year CEO pay trend sparkline
            html += '<div class="cm-cell cm-trend-cell">';
            if (r.trend && r.trend.length >= 2) {
                var tMin = Infinity, tMax = 0;
                r.trend.forEach(function(t) { if (t.median < tMin) tMin = t.median; if (t.median > tMax) tMax = t.median; });
                var tRange = tMax - tMin || 1;
                var deltaSign = r.trendDelta >= 0 ? '+' : '';
                var deltaColor = r.trendDelta >= 10 ? '#ef4444' : r.trendDelta >= 0 ? '#fbbf24' : '#34d399';
                var tTip = r.trend.map(function(t) { return t.year + ': ' + _fmtComp(t.median) + ' (' + t.count + ' cos)'; }).join(' → ');
                html += '<div class="cm-sparkline" title="' + tTip + '">';
                // SVG sparkline (48x16)
                html += '<svg width="48" height="16" viewBox="0 0 48 16">';
                var pts = [];
                r.trend.forEach(function(t, idx) {
                    var x = r.trend.length > 1 ? (idx / (r.trend.length - 1)) * 44 + 2 : 24;
                    var y = 14 - ((t.median - tMin) / tRange) * 12;
                    pts.push(x.toFixed(1) + ',' + y.toFixed(1));
                });
                // Line
                html += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + r.color + '" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>';
                // Dots at endpoints
                var firstPt = pts[0].split(','), lastPt = pts[pts.length - 1].split(',');
                html += '<circle cx="' + firstPt[0] + '" cy="' + firstPt[1] + '" r="1.5" fill="' + r.color + '"/>';
                html += '<circle cx="' + lastPt[0] + '" cy="' + lastPt[1] + '" r="2" fill="' + deltaColor + '"/>';
                html += '</svg>';
                // Delta badge
                html += '<span class="cm-trend-delta" style="color:' + deltaColor + '">' + deltaSign + Math.round(r.trendDelta) + '%</span>';
                html += '</div>';
            } else {
                html += '—';
            }
            html += '</div>';
            // Pay distribution box plot
            html += '<div class="cm-cell cm-dist-cell">';
            if (r.payDist && globalMaxPay > 0) {
                var d = r.payDist;
                var scale = function(v) { return (v / globalMaxPay * 100).toFixed(1); };
                var whiskerL = scale(d.min), boxL = scale(d.q1), medL = scale(d.median), boxR = scale(d.q3), whiskerR = scale(d.max);
                var iqr = _fmtComp(d.q3 - d.q1);
                html += '<div class="cm-boxplot" title="Min ' + _fmtComp(d.min) + ' · Q1 ' + _fmtComp(d.q1) + ' · Med ' + _fmtComp(d.median) + ' · Q3 ' + _fmtComp(d.q3) + ' · Max ' + _fmtComp(d.max) + ' · IQR ' + iqr + '">';
                // Whisker line (min to max)
                html += '<div class="cm-bp-whisker" style="left:' + whiskerL + '%;width:' + (whiskerR - whiskerL) + '%"></div>';
                // Min/max caps
                html += '<div class="cm-bp-cap" style="left:' + whiskerL + '%"></div>';
                html += '<div class="cm-bp-cap" style="left:' + whiskerR + '%"></div>';
                // IQR box (Q1 to Q3)
                html += '<div class="cm-bp-box" style="left:' + boxL + '%;width:' + (boxR - boxL) + '%;background:' + r.color + '"></div>';
                // Median line
                html += '<div class="cm-bp-median" style="left:' + medL + '%"></div>';
                // Quartile hover zones (transparent overlays for interactive graph highlighting)
                var _qZones = [
                    { label: 'Bottom 25%', lo: d.min, hi: d.q1 },
                    { label: '25th\u201350th', lo: d.q1, hi: d.median },
                    { label: '50th\u201375th', lo: d.median, hi: d.q3 },
                    { label: 'Top 25%', lo: d.q3, hi: d.max }
                ];
                _qZones.forEach(function(z) {
                    var zLeft = z.lo / globalMaxPay * 100;
                    var zRight = z.hi / globalMaxPay * 100;
                    var zW = Math.max(zRight - zLeft, 1.5);
                    // Count companies in this quartile
                    var zCount = 0;
                    r.tickers.forEach(function(t) {
                        var c = _compLookup[t];
                        if (c && c.total != null && c.total >= z.lo && c.total <= z.hi) zCount++;
                    });
                    html += '<div class="cm-bp-zone" data-bp-cid="' + r.id + '" data-bp-lo="' + z.lo + '" data-bp-hi="' + z.hi + '" data-bp-color="' + r.color + '" title="' + z.label + ': ' + _fmtComp(z.lo) + ' \u2013 ' + _fmtComp(z.hi) + ' \u00b7 ' + zCount + ' companies" style="left:' + zLeft.toFixed(1) + '%;width:' + zW.toFixed(1) + '%"></div>';
                });
                html += '</div>';
            } else {
                html += '—';
            }
            html += '</div>';
            // Governance
            html += '<div class="cm-cell cm-right">';
            if (r.medianGov != null) {
                var govColor = r.medianGov >= 65 ? '#34d399' : r.medianGov >= 50 ? '#fbbf24' : '#ef4444';
                html += '<span style="color:' + govColor + '">' + Math.round(r.medianGov) + '</span>';
            } else { html += '—'; }
            html += '</div>';
            // SoP%
            html += '<div class="cm-cell cm-right">';
            if (r.medianSop != null) {
                var sopColor = r.medianSop >= 85 ? '#34d399' : r.medianSop >= 70 ? '#fbbf24' : '#ef4444';
                html += '<span style="color:' + sopColor + '">' + r.medianSop.toFixed(1) + '%</span>';
            } else { html += '—'; }
            html += '</div>';
            // GER
            html += '<div class="cm-cell cm-right">';
            if (r.medianGer != null) {
                var gerColor = r.medianGer >= 50 ? '#ef4444' : r.medianGer >= 30 ? '#fbbf24' : '#34d399';
                html += '<span style="color:' + gerColor + '">' + Math.round(r.medianGer) + '</span>';
            } else { html += '—'; }
            html += '</div>';
            // Density
            html += '<div class="cm-cell cm-right">' + r.density.toFixed(1) + '%</div>';
            html += '</div>';
        });
        html += '</div>';

        // Top sector breakdown row (compact)
        html += '<div class="cm-sector-row">';
        rows.forEach(function(r) {
            html += '<span class="cm-sector-tag" title="' + r.topSector + ' (' + r.topSectorPct.toFixed(0) + '%)">';
            html += '<span class="cm-dot" style="background:' + r.topSectorColor + ';width:5px;height:5px"></span>';
            html += r.topSector ? r.topSector.replace('Information Technology', 'IT').replace('Communication Services', 'Comm').replace('Consumer Discretionary', 'Cons Disc').replace('Consumer Staples', 'Cons Stap').replace('Health Care', 'Health').replace('Real Estate', 'Real Est') : '—';
            html += ' ' + r.topSectorPct.toFixed(0) + '%';
            html += '</span>';
        });
        html += '</div>';

        _communityMetricsEl.innerHTML = html;

        // Insert after community legend
        if (communityLegendEl && communityLegendEl.parentNode) {
            communityLegendEl.parentNode.insertBefore(_communityMetricsEl, communityLegendEl.nextSibling);
        }

        // Wire sort handlers
        _communityMetricsEl.querySelectorAll('.cm-th').forEach(function(th) {
            th.style.cursor = 'pointer';
            th.addEventListener('click', function() {
                var col = th.dataset.cmSort;
                if (_cmSortCol === col) { _cmSortAsc = !_cmSortAsc; }
                else { _cmSortCol = col; _cmSortAsc = col === 'label'; }
                _renderCommunityMetrics();
                _renderCommunityFlowMatrix();
            });
            th.addEventListener('keydown', function(ev) {
                if (ev.key === 'Enter' || ev.key === ' ') {
                    ev.preventDefault();
                    var col = th.dataset.cmSort;
                    if (_cmSortCol === col) { _cmSortAsc = !_cmSortAsc; }
                    else { _cmSortCol = col; _cmSortAsc = col === 'label'; }
                    _renderCommunityMetrics();
                    _renderCommunityFlowMatrix();
                }
            });
        });

        // Wire row click handlers — filter table to that community (same as legend click)
        _communityMetricsEl.querySelectorAll('.cm-data').forEach(function(row) {
            row.style.cursor = 'pointer';
            row.addEventListener('click', function() {
                var cid = parseInt(row.dataset.cmCommunity);
                var cs = communityStats.find(function(s) { return s.id === cid; });
                if (!cs) return;

                // Check if this community is already active
                var wasActive = window._activeCommunityFilter && window._activeCommunityFilter.id === cid;
                // Clear all legend active states
                if (communityLegendEl) {
                    communityLegendEl.querySelectorAll('.community-legend-item').forEach(function(el) {
                        el.classList.remove('community-legend-active');
                    });
                }

                if (wasActive) {
                    window._activeCommunityFilter = null;
                    window._activeCommunityScatterTickers = null;
                    if (typeof renderTable === 'function') renderTable(window._chartData.companies);
                    var scEl = document.getElementById('scatter-chart');
                    if (scEl) scEl.innerHTML = '';
                    if (typeof drawScatterChart === 'function' && window._chartData) drawScatterChart(window._chartData.companies);
                    if (typeof announce === 'function') announce('Community filter cleared');
                    // Update row highlight
                    _communityMetricsEl.querySelectorAll('.cm-data').forEach(function(r) { r.classList.remove('cm-active'); });
                } else {
                    // Set filter
                    window._activeCommunityFilter = { tickers: cs.tickers, label: cs.label, id: cid };
                    window._activeCommunityScatterTickers = new Set(cs.tickers);
                    if (typeof window._clearPersistentScatterHighlight === 'function') window._clearPersistentScatterHighlight();
                    if (typeof renderTable === 'function') renderTable(window._chartData.companies);
                    var scEl2 = document.getElementById('scatter-chart');
                    if (scEl2) scEl2.innerHTML = '';
                    if (typeof drawScatterChart === 'function' && window._chartData) drawScatterChart(window._chartData.companies);
                    // Also activate the matching legend item
                    if (communityLegendEl) {
                        var legendItem = communityLegendEl.querySelector('.community-legend-item[data-community="' + cid + '"]');
                        if (legendItem) legendItem.classList.add('community-legend-active');
                    }
                    if (typeof announce === 'function') announce('Filtered to ' + cs.tickers.length + ' companies in ' + cs.label);
                    // Update row highlight
                    _communityMetricsEl.querySelectorAll('.cm-data').forEach(function(r) { r.classList.remove('cm-active'); });
                    row.classList.add('cm-active');
                    // Scroll to table
                    var tableSection = document.getElementById('compensation-table-section');
                    if (tableSection) {
                        var hdr = document.querySelector('.sticky-header, header');
                        var off = hdr ? hdr.offsetHeight : 0;
                        var top = tableSection.getBoundingClientRect().top + window.scrollY - off - 12;
                        window.scrollTo({ top: top, behavior: typeof getScrollBehavior === 'function' ? getScrollBehavior() : 'smooth' });
                    }
                }
            });

            // Hover: highlight community on graph
            row.addEventListener('mouseenter', function() {
                var cid = parseInt(row.dataset.cmCommunity);
                var cs = communityStats.find(function(s) { return s.id === cid; });
                if (!cs) return;
                _hoveredCommunityId = cid;
                _hoveredCommunityTickers = new Set(cs.tickers);
                row.classList.add('cm-hover');
                draw();
            });
            row.addEventListener('mouseleave', function() {
                _hoveredCommunityId = null;
                _hoveredCommunityTickers = null;
                row.classList.remove('cm-hover');
                draw();
            });
        });

        // Wire box plot quartile hover zones — highlight matching companies on network graph
        _communityMetricsEl.querySelectorAll('.cm-bp-zone').forEach(function(zone) {
            zone.addEventListener('mouseenter', function(ev) {
                ev.stopPropagation(); // Don't trigger row hover
                var cid = parseInt(zone.dataset.bpCid);
                var lo = parseFloat(zone.dataset.bpLo);
                var hi = parseFloat(zone.dataset.bpHi);
                var zColor = zone.dataset.bpColor;
                var cs = communityStats.find(function(s) { return s.id === cid; });
                if (!cs) return;

                var tickers = new Set();
                cs.tickers.forEach(function(t) {
                    var c = _compLookup[t];
                    if (c && c.total != null && c.total >= lo && c.total <= hi) {
                        tickers.add(t);
                    }
                });

                _hoveredQuartileTickers = tickers;
                _hoveredQuartileColor = zColor;
                zone.classList.add('cm-bp-zone-active');
                draw();
                if (typeof announce === 'function') announce(tickers.size + ' companies in pay range ' + _fmtComp(lo) + ' to ' + _fmtComp(hi) + ' highlighted on graph');
            });
            zone.addEventListener('mouseleave', function() {
                _hoveredQuartileTickers = null;
                _hoveredQuartileColor = null;
                zone.classList.remove('cm-bp-zone-active');
                draw();
            });
            zone.addEventListener('click', function(ev) {
                ev.stopPropagation(); // Don't trigger row click
                var cid = parseInt(zone.dataset.bpCid);
                var lo = parseFloat(zone.dataset.bpLo);
                var hi = parseFloat(zone.dataset.bpHi);
                var cs = communityStats.find(function(s) { return s.id === cid; });
                if (!cs) return;

                // Collect tickers in this quartile range
                var tickers = [];
                cs.tickers.forEach(function(t) {
                    var c = _compLookup[t];
                    if (c && c.total != null && c.total >= lo && c.total <= hi) {
                        tickers.push(t);
                    }
                });

                // Toggle: if same quartile already filtered, clear it
                var wasActive = window._activeQuartileFilter &&
                    window._activeQuartileFilter.communityId === cid &&
                    window._activeQuartileFilter._lo === lo &&
                    window._activeQuartileFilter._hi === hi;

                // Clear all clicked states
                _communityMetricsEl.querySelectorAll('.cm-bp-zone-clicked').forEach(function(z) {
                    z.classList.remove('cm-bp-zone-clicked');
                });

                if (wasActive) {
                    window._activeQuartileFilter = null;
                    if (typeof renderTable === 'function') renderTable(window._chartData.companies);
                    var scEl = document.getElementById('scatter-chart');
                    if (scEl) scEl.innerHTML = '';
                    if (typeof drawScatterChart === 'function' && window._chartData) drawScatterChart(window._chartData.companies);
                    if (typeof announce === 'function') announce('Quartile filter cleared');
                } else {
                    // Build label
                    var zLabel = zone.title.split(':')[0] || 'Quartile';
                    var filterLabel = cs.label + ' ' + zLabel + ' (' + tickers.length + ')';
                    window._activeQuartileFilter = { tickers: tickers, label: filterLabel, communityId: cid, _lo: lo, _hi: hi };
                    zone.classList.add('cm-bp-zone-clicked');
                    if (typeof window._clearPersistentScatterHighlight === 'function') window._clearPersistentScatterHighlight();
                    if (typeof renderTable === 'function') renderTable(window._chartData.companies);
                    var scEl2 = document.getElementById('scatter-chart');
                    if (scEl2) scEl2.innerHTML = '';
                    if (typeof drawScatterChart === 'function' && window._chartData) drawScatterChart(window._chartData.companies);
                    if (typeof announce === 'function') announce('Filtered to ' + tickers.length + ' companies in ' + cs.label + ' ' + zLabel);
                    // Scroll to table
                    var tableSection = document.getElementById('compensation-table-section');
                    if (tableSection) {
                        var hdr = document.querySelector('.sticky-header, header');
                        var off = hdr ? hdr.offsetHeight : 0;
                        var top = tableSection.getBoundingClientRect().top + window.scrollY - off - 12;
                        window.scrollTo({ top: top, behavior: typeof getScrollBehavior === 'function' ? getScrollBehavior() : 'smooth' });
                    }
                }
            });
        });

        // Wire trend sparkline hover → highlight community companies on graph by YoY pay change direction
        _communityMetricsEl.querySelectorAll('.cm-sparkline').forEach(function(spark) {
            spark.addEventListener('mouseenter', function(ev) {
                ev.stopPropagation(); // Don't trigger row hover
                var row = spark.closest('.cm-data');
                if (!row) return;
                var cid = parseInt(row.dataset.cmCommunity);
                var cs = communityStats.find(function(s) { return s.id === cid; });
                if (!cs) return;
                // Get the two most recent years of CEO pay data for each company
                var tMap = new Map();
                var upCount = 0, downCount = 0, stableCount = 0;
                cs.tickers.forEach(function(t) {
                    var c = _compLookup[t];
                    if (!c || !c._ceoPayByYear) return;
                    var years = Object.keys(c._ceoPayByYear).map(Number).sort();
                    if (years.length < 2) {
                        tMap.set(t, 'stable');
                        stableCount++;
                        return;
                    }
                    var prev = c._ceoPayByYear[years[years.length - 2]];
                    var curr = c._ceoPayByYear[years[years.length - 1]];
                    if (!prev || prev === 0) { tMap.set(t, 'stable'); stableCount++; return; }
                    var pctChange = ((curr - prev) / prev) * 100;
                    if (pctChange > 5) { tMap.set(t, 'up'); upCount++; }
                    else if (pctChange < -5) { tMap.set(t, 'down'); downCount++; }
                    else { tMap.set(t, 'stable'); stableCount++; }
                });
                // Include companies without multi-year data as stable (dimmed less)
                cs.tickers.forEach(function(t) {
                    if (!tMap.has(t) && _compLookup[t]) { tMap.set(t, 'stable'); stableCount++; }
                });
                _hoveredTrendTickers = tMap;
                _hoveredTrendCommunityColor = cs.color;
                spark.classList.add('cm-sparkline-active');
                draw();
                if (typeof announce === 'function') announce(cs.label + ' trend: ' + upCount + ' up, ' + downCount + ' down, ' + stableCount + ' stable — highlighted on graph');
            });
            spark.addEventListener('mouseleave', function() {
                _hoveredTrendTickers = null;
                _hoveredTrendCommunityColor = null;
                spark.classList.remove('cm-sparkline-active');
                draw();
            });
        });

        // Wire path-finder bridge buttons (two-click: select from → select to → execute)
        _communityMetricsEl.querySelectorAll('.cm-path-btn').forEach(function(btn) {
            btn.addEventListener('click', function(ev) {
                ev.stopPropagation(); // Don't trigger row click (filter)
                var cid = parseInt(btn.dataset.cmPathCid);
                var cs = communityStats.find(function(s) { return s.id === cid; });
                if (!cs) return;

                if (_cmPathFrom === null || _cmPathFrom === cid) {
                    // First click — set this as "from" community
                    _cmPathFrom = cid;
                    // Highlight this button, clear others
                    _communityMetricsEl.querySelectorAll('.cm-path-btn').forEach(function(b) {
                        b.classList.remove('cm-path-from');
                    });
                    btn.classList.add('cm-path-from');
                    btn.textContent = '⇤';
                    btn.title = 'Source selected — click another community\'s ⇄ to find path';
                    // Show instruction
                    var inst = _communityMetricsEl.querySelector('.cm-path-instruction');
                    if (!inst) {
                        inst = document.createElement('div');
                        inst.className = 'cm-path-instruction';
                        _communityMetricsEl.appendChild(inst);
                    }
                    inst.textContent = 'Click ⇄ on another community to find the peer path from ' + cs.label;
                    if (typeof announce === 'function') announce('Path source: ' + cs.label + '. Click another community to set destination.');

                    // Pre-compute estimated hops from source community to all others
                    // Find source community's most-connected node
                    var srcTickerSet = new Set(cs.tickers);
                    var srcBestTicker = null, srcBestDeg = -1;
                    cs.tickers.forEach(function(tk) {
                        var adj = adjacency[tk];
                        if (!adj) return;
                        var deg = adj.out.length + adj.in.length;
                        if (deg > srcBestDeg) { srcBestDeg = deg; srcBestTicker = tk; }
                    });
                    if (srcBestTicker) {
                        // BFS from srcBestTicker to find distance to first node in each other community
                        var _hopVisited = new Set();
                        var _hopQueue = [{ ticker: srcBestTicker, depth: 0 }];
                        _hopVisited.add(srcBestTicker);
                        var _hopResults = {}; // communityId → hops
                        var _maxHopDepth = 8;
                        while (_hopQueue.length > 0) {
                            var _hq = _hopQueue.shift();
                            if (_hq.depth > _maxHopDepth) break;
                            // Check which community this node belongs to
                            for (var _hi = 0; _hi < communityStats.length; _hi++) {
                                var _hcs = communityStats[_hi];
                                if (_hcs.id !== cid && !_hopResults[_hcs.id] && _hcs.tickers.indexOf(_hq.ticker) >= 0) {
                                    _hopResults[_hcs.id] = _hq.depth;
                                }
                            }
                            var _hadj = adjacency[_hq.ticker];
                            if (!_hadj) continue;
                            var _hNeighbors = _hadj.out.concat(_hadj.in);
                            for (var _hni = 0; _hni < _hNeighbors.length; _hni++) {
                                if (!_hopVisited.has(_hNeighbors[_hni])) {
                                    _hopVisited.add(_hNeighbors[_hni]);
                                    _hopQueue.push({ ticker: _hNeighbors[_hni], depth: _hq.depth + 1 });
                                }
                            }
                        }
                        // Update other ⇄ buttons with hop badges
                        _communityMetricsEl.querySelectorAll('.cm-path-btn').forEach(function(b) {
                            var bCid = parseInt(b.dataset.cmPathCid);
                            if (bCid === cid) return; // Skip source
                            var hops = _hopResults[bCid];
                            // Remove old badge
                            var oldBadge = b.querySelector('.cm-hop-badge');
                            if (oldBadge) oldBadge.remove();
                            if (hops != null) {
                                var badge = document.createElement('span');
                                badge.className = 'cm-hop-badge';
                                badge.textContent = '~' + hops;
                                badge.title = 'Estimated ' + hops + ' hop' + (hops !== 1 ? 's' : '');
                                b.appendChild(badge);
                                b.title = '⇄ ' + hops + ' hop' + (hops !== 1 ? 's' : '') + ' estimated';
                            }
                        });
                    }
                } else {
                    // Second click on different community — execute path finder
                    var fromCs = communityStats.find(function(s) { return s.id === _cmPathFrom; });
                    var toCs = cs;
                    if (!fromCs || !toCs) return;

                    // Find most-connected node in fromCs to toCs, and vice versa
                    var fromTickerSet = new Set(fromCs.tickers);
                    var toTickerSet = new Set(toCs.tickers);
                    var fromScores = {}, toScores = {};
                    allEdges.forEach(function(e) {
                        if (fromTickerSet.has(e.source) && toTickerSet.has(e.target)) {
                            fromScores[e.source] = (fromScores[e.source] || 0) + 1;
                            toScores[e.target] = (toScores[e.target] || 0) + 1;
                        }
                        if (fromTickerSet.has(e.target) && toTickerSet.has(e.source)) {
                            fromScores[e.target] = (fromScores[e.target] || 0) + 1;
                            toScores[e.source] = (toScores[e.source] || 0) + 1;
                        }
                    });

                    var bestFrom = null, bestFromScore = -1;
                    for (var t in fromScores) { if (fromScores[t] > bestFromScore) { bestFromScore = fromScores[t]; bestFrom = t; } }
                    var bestTo = null, bestToScore = -1;
                    for (var t2 in toScores) { if (toScores[t2] > bestToScore) { bestToScore = toScores[t2]; bestTo = t2; } }

                    // Fallback to highest-paid in each community if no cross-edges
                    if (!bestFrom) {
                        var fromPay = fromCs.tickers.map(function(tk) { return { t: tk, p: _compLookup[tk] ? _compLookup[tk].total || 0 : 0 }; });
                        fromPay.sort(function(a, b) { return b.p - a.p; });
                        bestFrom = fromPay[0] ? fromPay[0].t : fromCs.tickers[0];
                    }
                    if (!bestTo) {
                        var toPay = toCs.tickers.map(function(tk) { return { t: tk, p: _compLookup[tk] ? _compLookup[tk].total || 0 : 0 }; });
                        toPay.sort(function(a, b) { return b.p - a.p; });
                        bestTo = toPay[0] ? toPay[0].t : toCs.tickers[0];
                    }

                    // Clear path-from state
                    _cmPathFrom = null;
                    _communityMetricsEl.querySelectorAll('.cm-path-btn').forEach(function(b) {
                        b.classList.remove('cm-path-from');
                        b.textContent = '⇄';
                        b.title = 'Find path to another community';
                        // Remove hop badges
                        var hb = b.querySelector('.cm-hop-badge');
                        if (hb) hb.remove();
                    });
                    var inst2 = _communityMetricsEl.querySelector('.cm-path-instruction');
                    if (inst2) inst2.remove();

                    // Launch path finder
                    if (bestFrom && bestTo && typeof window.findNetworkPath === 'function') {
                        window.findNetworkPath(bestFrom, bestTo);
                        if (typeof announce === 'function') announce('Finding path from ' + fromCs.label + ' (' + bestFrom + ') to ' + toCs.label + ' (' + bestTo + ')');
                    }
                }
            });
        });
    }

    // Cleanup community metrics when mode is toggled off
    function _removeCommunityMetrics() {
        if (_communityMetricsEl && _communityMetricsEl.parentNode) {
            _communityMetricsEl.parentNode.removeChild(_communityMetricsEl);
        }
        _communityMetricsEl = null;
        _cmPathFrom = null;
        _hoveredQuartileTickers = null;
        _hoveredQuartileColor = null;
        _hoveredTrendTickers = null;
        _hoveredTrendCommunityColor = null;
        // Clear quartile filter when community mode is toggled off
        if (window._activeQuartileFilter) {
            window._activeQuartileFilter = null;
            if (typeof renderTable === 'function' && window._chartData) renderTable(window._chartData.companies);
            var scEl = document.getElementById('scatter-chart');
            if (scEl) scEl.innerHTML = '';
            if (typeof drawScatterChart === 'function' && window._chartData) drawScatterChart(window._chartData.companies);
        }
        _removeCommunityFlowMatrix();
    }

    // === Community Edge Flow Matrix ===
    // Shows a compact NxN heatmap of directed peer edges between communities.
    // Answers "which clusters benchmark against which?"
    function _renderCommunityFlowMatrix() {
        _removeCommunityFlowMatrix();
        if (!communityMode || !communityStats || communityStats.length < 2) return;

        var dark = document.documentElement.getAttribute('data-theme') !== 'light';
        var maxShow = Math.min(communityStats.length, 10);
        var comms = communityStats.slice(0, maxShow);

        var commIdx = {};
        var commTickerSets = [];
        comms.forEach(function(cs, i) {
            commIdx[cs.id] = i;
            commTickerSets.push(new Set(cs.tickers));
        });

        // Build NxN flow matrix + per-cell edge detail (which source tickers contribute)
        var N = comms.length;
        var flowMatrix = [];
        _cfCellEdgeDetails = [];
        for (var i = 0; i < N; i++) {
            flowMatrix.push(new Array(N).fill(0));
            var detailRow = [];
            for (var j = 0; j < N; j++) detailRow.push({});
            _cfCellEdgeDetails.push(detailRow);
        }

        allEdges.forEach(function(e) {
            var sNode = nodeMap[e.source];
            var tNode = nodeMap[e.target];
            if (!sNode || !tNode) return;
            var sCid = communityOf[e.source];
            var tCid = communityOf[e.target];
            var si = commIdx[sCid];
            var ti = commIdx[tCid];
            if (si != null && ti != null) {
                flowMatrix[si][ti]++;
                var detail = _cfCellEdgeDetails[si][ti];
                detail[e.source] = (detail[e.source] || 0) + 1;
            }
        });

        // Row totals for normalize mode
        var rowTotals = [];
        for (var i = 0; i < N; i++) {
            var rt = 0;
            for (var j = 0; j < N; j++) rt += flowMatrix[i][j];
            rowTotals.push(rt);
        }

        // Pre-compute column totals for col-normalize mode
        var colTotals = new Array(N).fill(0);
        for (var ci2 = 0; ci2 < N; ci2++) {
            for (var cj2 = 0; cj2 < N; cj2++) colTotals[cj2] += flowMatrix[ci2][cj2];
        }

        var maxOff = 0, maxDiag = 0;
        for (var i = 0; i < N; i++) {
            for (var j = 0; j < N; j++) {
                if (i === j) { if (flowMatrix[i][j] > maxDiag) maxDiag = flowMatrix[i][j]; }
                else { if (flowMatrix[i][j] > maxOff) maxOff = flowMatrix[i][j]; }
            }
        }
        var maxVal = Math.max(maxOff, 1);

        _communityFlowEl = document.createElement('div');
        _communityFlowEl.className = 'community-flow-panel';

        var html = '<div class="cf-header-row"><div class="cf-header">Peer Flow Between Communities</div>';
        var normLabel = _cfNormMode === 'row' ? '% Row' : _cfNormMode === 'col' ? '% Col' : '# Raw';
        var normActiveClass = _cfNormMode !== 'raw' ? (' cf-norm-active' + (_cfNormMode === 'col' ? ' cf-norm-col' : '')) : '';
        html += '<button class="cf-normalize-btn' + normActiveClass + '" title="Cycle: raw counts → row % → column %">' + normLabel + '</button></div>';
        var descText = _cfNormMode === 'row' ? 'Values = % of row\u2019s outbound edges.' : _cfNormMode === 'col' ? 'Values = % of column\u2019s inbound edges.' : 'Diagonal = intra-community.';
        html += '<div class="cf-desc">Directed edges: row selects column as peer. ' + descText + ' Hover for top contributors.</div>';
        html += '<div class="cf-matrix" style="grid-template-columns: 64px repeat(' + N + ', 28px) 36px;">';

        html += '<div class="cf-row cf-head-row">';
        html += '<div class="cf-corner"></div>';
        comms.forEach(function(cs, j) {
            var shortLabel = cs.label.length > 8 ? cs.label.substring(0, 7) + '\u2026' : cs.label;
            html += '<div class="cf-col-label" title="' + cs.label + ' (' + cs.size + ' companies)" style="color:' + cs.color + '">' + shortLabel + '</div>';
        });
        html += '<div class="cf-row-total-label">Total</div>';
        html += '</div>';

        comms.forEach(function(csRow, i) {
            var shortLabel = csRow.label.length > 8 ? csRow.label.substring(0, 7) + '\u2026' : csRow.label;
            html += '<div class="cf-row">';
            html += '<div class="cf-row-label" title="' + csRow.label + ' (' + csRow.size + ' companies)" style="color:' + csRow.color + '">' + shortLabel + '</div>';

            var rowTotal = 0;
            comms.forEach(function(csCol, j) {
                var val = flowMatrix[i][j];
                rowTotal += val;
                var isDiag = (i === j);

                var displayVal = '';
                if (val > 0) {
                    if (_cfNormMode === 'row' && rowTotals[i] > 0) {
                        var pct = (val / rowTotals[i]) * 100;
                        displayVal = pct >= 10 ? Math.round(pct) + '' : pct.toFixed(1);
                    } else if (_cfNormMode === 'col' && colTotals[j] > 0) {
                        var pct = (val / colTotals[j]) * 100;
                        displayVal = pct >= 10 ? Math.round(pct) + '' : pct.toFixed(1);
                    } else {
                        displayVal = val + '';
                    }
                }

                var alpha = 0;
                if (val > 0) {
                    if (isDiag) {
                        alpha = maxDiag > 0 ? Math.max(0.15, val / maxDiag * 0.85) : 0.15;
                    } else {
                        alpha = Math.max(0.1, val / maxVal * 0.9);
                    }
                }

                var bgColor;
                if (val === 0) {
                    bgColor = dark ? 'rgba(30,30,40,0.5)' : 'rgba(240,240,245,0.5)';
                } else if (isDiag) {
                    bgColor = _hexToRgba(csRow.color, alpha);
                } else {
                    bgColor = _hexToRgba(_blendHex(csRow.color, csCol.color), alpha);
                }

                var textColor = val === 0 ? (dark ? '#4a4a5a' : '#b0b0b8') : (alpha > 0.5 ? '#fff' : (dark ? '#e4e4e7' : '#1a1a2e'));

                html += '<div class="cf-cell' + (isDiag ? ' cf-diag' : '') + '" '
                    + 'data-cf-from="' + csRow.id + '" data-cf-to="' + csCol.id + '" '
                    + 'data-cf-i="' + i + '" data-cf-j="' + j + '" '
                    + 'style="background:' + bgColor + ';color:' + textColor + '">'
                    + displayVal + '</div>';
            });

            var rowTotalDisplay = _cfNormMode === 'row' ? '100' : rowTotal;
            html += '<div class="cf-cell cf-total">' + rowTotalDisplay + '</div>';
            html += '</div>';
        });

        html += '<div class="cf-row cf-totals-row">';
        html += '<div class="cf-row-label cf-total-label">Total</div>';
        var grandTotal = 0;
        colTotals.forEach(function(ct) {
            grandTotal += ct;
            html += '<div class="cf-cell cf-total">' + (_cfNormMode === 'col' ? '100' : ct) + '</div>';
        });
        html += '<div class="cf-cell cf-total cf-grand-total">' + (_cfNormMode !== 'raw' ? '\u2014' : grandTotal) + '</div>';
        html += '</div>';

        html += '</div>';

        _communityFlowEl.innerHTML = html;

        var anchor = _communityMetricsEl || (communityLegendEl ? communityLegendEl : null);
        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(_communityFlowEl, anchor.nextSibling);
        }

        // Create/reuse flow tooltip element
        var flowTip = document.getElementById('cf-flow-tooltip');
        if (!flowTip) {
            flowTip = document.createElement('div');
            flowTip.id = 'cf-flow-tooltip';
            flowTip.className = 'cf-flow-tooltip';
            flowTip.setAttribute('role', 'tooltip');
            document.body.appendChild(flowTip);
        }

        // Wire normalize toggle (cycles: raw → row → col → raw)
        var normBtn = _communityFlowEl.querySelector('.cf-normalize-btn');
        if (normBtn) {
            normBtn.addEventListener('click', function() {
                _cfNormMode = _cfNormMode === 'raw' ? 'row' : _cfNormMode === 'row' ? 'col' : 'raw';
                _renderCommunityFlowMatrix();
            });
        }

        // Wire hover/click on cells
        _communityFlowEl.querySelectorAll('.cf-cell[data-cf-from]').forEach(function(cell) {
            cell.style.cursor = 'pointer';

            cell.addEventListener('mouseenter', function(ev) {
                var fromId = parseInt(cell.dataset.cfFrom);
                var toId = parseInt(cell.dataset.cfTo);
                var ci = parseInt(cell.dataset.cfI);
                var cj = parseInt(cell.dataset.cfJ);
                _hoveredFlowCell = { from: fromId, to: toId };
                cell.classList.add('cf-hover');

                // Build rich tooltip with top 3 contributing companies
                var detail = _cfCellEdgeDetails && _cfCellEdgeDetails[ci] ? _cfCellEdgeDetails[ci][cj] : null;
                if (detail && Object.keys(detail).length > 0) {
                    var fromCs = comms.find(function(cs) { return cs.id === fromId; });
                    var toCs = comms.find(function(cs) { return cs.id === toId; });
                    var fromLabel = fromCs ? fromCs.label : '?';
                    var toLabel = toCs ? toCs.label : '?';
                    var isDiag = fromId === toId;
                    var rawVal = flowMatrix[ci][cj];

                    var contribs = Object.keys(detail).map(function(tk) {
                        return { ticker: tk, count: detail[tk], name: (nodeMap[tk] && nodeMap[tk].name) || tk };
                    }).sort(function(a, b) { return b.count - a.count; });

                    var top3 = contribs.slice(0, 3);
                    var remaining = contribs.length - 3;

                    var tipHtml = '<div class="cf-tip-header">' + fromLabel + (isDiag ? ' (intra)' : ' \u2192 ' + toLabel) + '</div>';
                    tipHtml += '<div class="cf-tip-count">' + rawVal + ' edge' + (rawVal !== 1 ? 's' : '');
                    if (_cfNormMode === 'row' && rowTotals[ci] > 0) {
                        tipHtml += ' (' + ((rawVal / rowTotals[ci]) * 100).toFixed(1) + '% of row)';
                    } else if (_cfNormMode === 'col' && colTotals[cj] > 0) {
                        tipHtml += ' (' + ((rawVal / colTotals[cj]) * 100).toFixed(1) + '% of col)';
                    }
                    tipHtml += '</div>';
                    tipHtml += '<div class="cf-tip-label">Top contributors:</div>';
                    top3.forEach(function(c, idx) {
                        var barW = Math.max(8, Math.round((c.count / top3[0].count) * 100));
                        tipHtml += '<div class="cf-tip-row">'
                            + '<span class="cf-tip-rank">' + (idx + 1) + '.</span>'
                            + '<span class="cf-tip-ticker">' + c.ticker + '</span>'
                            + '<span class="cf-tip-bar-wrap"><span class="cf-tip-bar" style="width:' + barW + '%"></span></span>'
                            + '<span class="cf-tip-val">' + c.count + '</span>'
                            + '</div>';
                    });
                    if (remaining > 0) {
                        tipHtml += '<div class="cf-tip-more">+' + remaining + ' more</div>';
                    }
                    flowTip.innerHTML = tipHtml;
                    flowTip.style.display = 'block';
                    _positionFlowTip(flowTip, ev);
                }

                draw();
            });

            cell.addEventListener('mousemove', function(ev) {
                if (flowTip.style.display === 'block') _positionFlowTip(flowTip, ev);
            });

            cell.addEventListener('mouseleave', function() {
                _hoveredFlowCell = null;
                cell.classList.remove('cf-hover');
                flowTip.style.display = 'none';
                draw();
            });

            cell.addEventListener('click', function() {
                flowTip.style.display = 'none';
                var fromId = parseInt(cell.dataset.cfFrom);
                var toId = parseInt(cell.dataset.cfTo);
                var fromCs = communityStats.find(function(cs) { return cs.id === fromId; });
                var toCs = communityStats.find(function(cs) { return cs.id === toId; });
                if (!fromCs || !toCs) return;
                if (fromId === toId) {
                    window._activeCommunityFilter = { tickers: fromCs.tickers, label: fromCs.label, id: fromId };
                    window._activeCommunityScatterTickers = new Set(fromCs.tickers);
                    if (typeof window._clearPersistentScatterHighlight === 'function') window._clearPersistentScatterHighlight();
                    if (typeof renderTable === 'function') renderTable(window._chartData.companies);
                    var scEl = document.getElementById('scatter-chart');
                    if (scEl) scEl.innerHTML = '';
                    if (typeof drawScatterChart === 'function' && window._chartData) drawScatterChart(window._chartData.companies);
                    if (typeof announce === 'function') announce('Filtered to ' + fromCs.tickers.length + ' companies in ' + fromCs.label);
                } else {
                    var fromTickers = new Set(fromCs.tickers);
                    var toTickers = new Set(toCs.tickers);
                    var bestFrom = null, bestFromCount = 0;
                    var bestTo = null, bestToCount = 0;
                    fromCs.tickers.forEach(function(t) {
                        var adj2 = adjacency[t];
                        if (!adj2) return;
                        var ct = 0;
                        adj2.out.forEach(function(o) { if (toTickers.has(o)) ct++; });
                        if (ct > bestFromCount) { bestFromCount = ct; bestFrom = t; }
                    });
                    toCs.tickers.forEach(function(t) {
                        var adj2 = adjacency[t];
                        if (!adj2) return;
                        var ct = 0;
                        adj2.in.forEach(function(o) { if (fromTickers.has(o)) ct++; });
                        if (ct > bestToCount) { bestToCount = ct; bestTo = t; }
                    });
                    if (bestFrom && bestTo && typeof window.findNetworkPath === 'function') {
                        window.findNetworkPath(bestFrom, bestTo);
                        if (typeof announce === 'function') announce('Finding path from ' + fromCs.label + ' (' + bestFrom + ') to ' + toCs.label + ' (' + bestTo + ')');
                    }
                }
            });
        });
    }

    // Position flow tooltip near cursor
    function _positionFlowTip(el, ev) {
        var x = ev.clientX + 12;
        var y = ev.clientY - 10;
        var w = el.offsetWidth || 180;
        var h = el.offsetHeight || 100;
        if (x + w > window.innerWidth - 8) x = ev.clientX - w - 12;
        if (y + h > window.innerHeight - 8) y = window.innerHeight - h - 8;
        if (y < 4) y = 4;
        el.style.left = x + 'px';
        el.style.top = y + 'px';
    }

    // Helper: hex color to rgba string
    function _hexToRgba(hex, alpha) {
        hex = hex.replace('#', '');
        if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
        var r = parseInt(hex.substring(0, 2), 16);
        var g = parseInt(hex.substring(2, 4), 16);
        var b = parseInt(hex.substring(4, 6), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha.toFixed(2) + ')';
    }

    // Helper: blend two hex colors 50/50
    function _blendHex(hex1, hex2) {
        hex1 = hex1.replace('#', '');
        hex2 = hex2.replace('#', '');
        if (hex1.length === 3) hex1 = hex1[0]+hex1[0]+hex1[1]+hex1[1]+hex1[2]+hex1[2];
        if (hex2.length === 3) hex2 = hex2[0]+hex2[0]+hex2[1]+hex2[1]+hex2[2]+hex2[2];
        var r = Math.round((parseInt(hex1.substring(0, 2), 16) + parseInt(hex2.substring(0, 2), 16)) / 2);
        var g = Math.round((parseInt(hex1.substring(2, 4), 16) + parseInt(hex2.substring(2, 4), 16)) / 2);
        var b = Math.round((parseInt(hex1.substring(4, 6), 16) + parseInt(hex2.substring(4, 6), 16)) / 2);
        return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
    }

    function _removeCommunityFlowMatrix() {
        if (_communityFlowEl && _communityFlowEl.parentNode) {
            _communityFlowEl.parentNode.removeChild(_communityFlowEl);
        }
        _communityFlowEl = null;
        _hoveredFlowCell = null;
        _cfCellEdgeDetails = null;
        var flowTip = document.getElementById('cf-flow-tooltip');
        if (flowTip) flowTip.style.display = 'none';
    }

    function _truncName(name, maxLen) {
        if (!name || name.length <= maxLen) return name || '';
        return name.substring(0, maxLen - 1) + '\u2026';
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

        // GER risk stats section — shown when GER heatmap mode is active
        if (gerHeatmapMode) {
            var sectorGERVals = [];
            var highestGERNode = null, highestGERVal = -1;
            var lowestGERNode = null, lowestGERVal = Infinity;
            var criticalNodes = [], highRiskNodes = [];
            sectorNodes.forEach(function(n) {
                var c = _compLookup[n.ticker];
                if (!c || c._gerScore == null) return;
                sectorGERVals.push(c._gerScore);
                if (c._gerScore > highestGERVal) { highestGERVal = c._gerScore; highestGERNode = n; }
                if (c._gerScore < lowestGERVal) { lowestGERVal = c._gerScore; lowestGERNode = n; }
                if (c._gerScore >= 75) criticalNodes.push(n);
                else if (c._gerScore >= 60) highRiskNodes.push(n);
            });
            if (sectorGERVals.length > 1) {
                sectorGERVals.sort(function(a, b) { return a - b; });
                var gerMedian = sectorGERVals[Math.floor(sectorGERVals.length / 2)];
                html += '<div class="cs-comp-section">';
                html += '<div class="cs-comp-title">🛡️ Governance Erosion Risk</div>';
                html += '<div class="cluster-stats-grid">';
                html += '<div class="cs-stat"><span class="cs-stat-label">Median GER</span><span class="cs-stat-value">' + Math.round(gerMedian) + '/100</span></div>';
                html += '<div class="cs-stat"><span class="cs-stat-label">Critical (≥75)</span><span class="cs-stat-value" style="color:#dc2626">' + criticalNodes.length + '</span></div>';
                html += '<div class="cs-stat"><span class="cs-stat-label">High (≥60)</span><span class="cs-stat-value" style="color:#ef476f">' + highRiskNodes.length + '</span></div>';
                html += '</div>';
                html += '<div class="cs-node-list">';
                if (highestGERNode) {
                    var hComp = _compLookup[highestGERNode.ticker];
                    html += '<div class="cs-node-row">';
                    html += '<span><span class="cs-node-role">Highest risk </span><span class="cs-node-ticker" data-ticker="' + highestGERNode.ticker + '">' + highestGERNode.ticker + '</span></span>';
                    html += '<span class="cs-node-degree" style="color:' + getGERHeatmapColor(highestGERNode.ticker) + '">' + Math.round(highestGERVal) + '/100</span>';
                    html += '</div>';
                }
                if (lowestGERNode && lowestGERNode !== highestGERNode) {
                    html += '<div class="cs-node-row">';
                    html += '<span><span class="cs-node-role">Lowest risk </span><span class="cs-node-ticker" data-ticker="' + lowestGERNode.ticker + '">' + lowestGERNode.ticker + '</span></span>';
                    html += '<span class="cs-node-degree" style="color:' + getGERHeatmapColor(lowestGERNode.ticker) + '">' + Math.round(lowestGERVal) + '/100</span>';
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
        // Clear scatter path overlay
        window._activePathFinderNodes = null;
        if (typeof window._redrawScatterForPathOverlay === 'function') {
            window._redrawScatterForPathOverlay();
        }
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
        // Build scatter axis context for header
        var scXSel = document.getElementById('scatter-x-metric');
        var scYSel = document.getElementById('scatter-y-metric');
        var scXLabel = scXSel ? scXSel.options[scXSel.selectedIndex].text : '';
        var scYLabel = scYSel ? scYSel.options[scYSel.selectedIndex].text : '';
        var axisCtx = (scXLabel && scYLabel) ? scXLabel + ' vs ' + scYLabel : '';
        var html = '<div class="path-result-header">' + hops + '-hop path found';
        if (axisCtx) html += '<span class="pf-header-axis-ctx" title="Current scatter plot axes">📊 ' + axisCtx + '</span>';
        html += '</div>';
        html += '<div class="path-result-chain">';

        // Collect compensation values for path analysis
        var pathCompVals = [];
        pathResult.nodes.forEach(function(ticker, idx) {
            var n = nodeMap[ticker];
            // Use heatmap color in heatmap mode, sector color otherwise
            var color;
            if (compHeatmapMode || prHeatmapMode || ccHeatmapMode || gerHeatmapMode || communityMode) {
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

            // Pay gradient legend — shows scale of edge colors on graph
            html += '<div class="pf-gradient-legend">';
            html += '<span class="pf-gradient-label">' + _fmtComp(minComp) + '</span>';
            html += '<div class="pf-gradient-bar"></div>';
            html += '<span class="pf-gradient-label">' + _fmtComp(maxComp) + '</span>';
            html += '<span class="pf-gradient-label" style="margin-left:4px">Edge color = CEO pay</span>';
            html += '</div>';
        }

        // --- Community-Scoped Path Statistics ---
        if (pathResult.nodes.length >= 2 && communityOf) {
            var pathCommIds = [];
            var pathCommSet = new Set();
            pathResult.nodes.forEach(function(t) {
                var cid = communityOf[t];
                pathCommIds.push(cid);
                if (cid != null) pathCommSet.add(cid);
            });
            var crossCount = 0;
            for (var ci = 1; ci < pathCommIds.length; ci++) {
                if (pathCommIds[ci] != null && pathCommIds[ci - 1] != null && pathCommIds[ci] !== pathCommIds[ci - 1]) crossCount++;
            }
            // Get community labels
            var _commLabel = {};
            if (communityStats && communityStats.length > 0) {
                communityStats.forEach(function(cs) { _commLabel[cs.id] = cs.label || ('Cluster ' + cs.id); });
            }
            var startComm = pathCommIds[0];
            var endComm = pathCommIds[pathCommIds.length - 1];
            var startLabel = _commLabel[startComm] || ('Cluster ' + startComm);
            var endLabel = _commLabel[endComm] || ('Cluster ' + endComm);

            html += '<div class="pf-community-stats">';
            html += '<span class="pf-cs-icon">🏘</span>';
            if (startComm === endComm) {
                html += '<span class="pf-cs-text pf-cs-same">Same community: <strong>' + startLabel + '</strong></span>';
            } else {
                html += '<span class="pf-cs-text">' + startLabel + ' → ' + endLabel + '</span>';
                html += '<span class="pf-cs-sep">·</span>';
                html += '<span class="pf-cs-cross">' + crossCount + ' boundary crossing' + (crossCount !== 1 ? 's' : '') + '</span>';
            }
            html += '<span class="pf-cs-sep">·</span>';
            html += '<span class="pf-cs-communities">' + pathCommSet.size + ' communit' + (pathCommSet.size !== 1 ? 'ies' : 'y') + '</span>';

            // Compute average intra-community vs inter-community path length from sampled BFS
            // Use cached value to avoid repeated BFS (expensive for large graphs)
            if (!window._communityPathLenCache) {
                var _sampleSize = 80; // sample pairs
                var _intraLens = [], _interLens = [];
                var _allTickers = Object.keys(communityOf);
                for (var _si = 0; _si < _sampleSize && _allTickers.length >= 2; _si++) {
                    var _ia = Math.floor(Math.random() * _allTickers.length);
                    var _ib = Math.floor(Math.random() * _allTickers.length);
                    if (_ia === _ib) continue;
                    var _ta = _allTickers[_ia], _tb = _allTickers[_ib];
                    var _sameComm = communityOf[_ta] === communityOf[_tb];
                    // Quick BFS
                    var _vis = new Set([_ta]), _queue = [_ta], _par = {}, _found = false;
                    _par[_ta] = null;
                    var _maxDepth = 8, _depth = 0;
                    bfs_loop:
                    while (_queue.length > 0 && _depth < _maxDepth) {
                        var _nextQ = [];
                        _depth++;
                        for (var _qi = 0; _qi < _queue.length; _qi++) {
                            var _cur = _queue[_qi];
                            var _adj = adjacency[_cur];
                            if (!_adj) continue;
                            var _neighbors = _adj.out.concat(_adj.in);
                            for (var _ni = 0; _ni < _neighbors.length; _ni++) {
                                var _nb = _neighbors[_ni];
                                if (!_vis.has(_nb)) {
                                    _vis.add(_nb);
                                    _par[_nb] = _cur;
                                    if (_nb === _tb) { _found = true; break bfs_loop; }
                                    _nextQ.push(_nb);
                                }
                            }
                        }
                        _queue = _nextQ;
                    }
                    if (_found) {
                        // Count hops
                        var _hops = 0, _c = _tb;
                        while (_c !== _ta) { _hops++; _c = _par[_c]; }
                        if (_sameComm) _intraLens.push(_hops);
                        else _interLens.push(_hops);
                    }
                }
                var _avgIntra = _intraLens.length > 0 ? (_intraLens.reduce(function(a, b) { return a + b; }, 0) / _intraLens.length) : null;
                var _avgInter = _interLens.length > 0 ? (_interLens.reduce(function(a, b) { return a + b; }, 0) / _interLens.length) : null;
                window._communityPathLenCache = { intra: _avgIntra, inter: _avgInter, intraN: _intraLens.length, interN: _interLens.length };
            }
            var _cpl = window._communityPathLenCache;
            if (_cpl.intra != null || _cpl.inter != null) {
                html += '<span class="pf-cs-sep">·</span>';
                html += '<span class="pf-cs-avg" title="Average shortest path length within communities vs between communities (sampled ' + (_cpl.intraN + _cpl.interN) + ' pairs)">';
                if (_cpl.intra != null) html += 'Avg intra: ' + _cpl.intra.toFixed(1) + ' hops';
                if (_cpl.intra != null && _cpl.inter != null) html += ', ';
                if (_cpl.inter != null) html += 'inter: ' + _cpl.inter.toFixed(1) + ' hops';
                html += '</span>';
            }

            html += '</div>';
        }

        // --- Endpoint Pay Comparison Card ---
        if (pathResult.nodes.length >= 2) {
            var epA = pathResult.nodes[0];
            var epB = pathResult.nodes[pathResult.nodes.length - 1];
            var cA = _compLookup[epA];
            var cB = _compLookup[epB];
            if (cA && cB) {
                // Gather full company objects for richer data
                var fullA = null, fullB = null;
                if (typeof compData !== 'undefined' && compData && compData.companies) {
                    compData.companies.forEach(function(c) {
                        if (c.ticker === epA) fullA = c;
                        if (c.ticker === epB) fullB = c;
                    });
                }
                html += '<div class="pf-endpoint-compare">';
                html += '<div class="pf-epc-header">Endpoint Comparison</div>';
                html += '<div class="pf-epc-grid">';
                // Header row
                html += '<div class="pf-epc-label"></div>';
                html += '<div class="pf-epc-val pf-epc-col-header">' + epA + '</div>';
                html += '<div class="pf-epc-val pf-epc-col-header">' + epB + '</div>';
                html += '<div class="pf-epc-val pf-epc-col-header pf-epc-delta-hdr">\u0394</div>';

                // Build rows with value extraction + delta computation
                var rows = [];
                // CEO Pay
                var aTotal = (cA.total != null && cA.total > 0) ? cA.total : null;
                var bTotal = (cB.total != null && cB.total > 0) ? cB.total : null;
                rows.push({ label: 'CEO Pay', a: aTotal ? _fmtComp(aTotal) : '\u2014', b: bTotal ? _fmtComp(bTotal) : '\u2014',
                    delta: (aTotal && bTotal) ? (((bTotal - aTotal) / aTotal) * 100) : null, fmt: 'pct' });

                // Equity %
                var aEq = fullA ? fullA._ceoStockPct : null;
                var bEq = fullB ? fullB._ceoStockPct : null;
                rows.push({ label: 'Equity %', a: aEq != null ? Math.round(aEq) + '%' : '\u2014', b: bEq != null ? Math.round(bEq) + '%' : '\u2014',
                    delta: (aEq != null && bEq != null) ? (bEq - aEq) : null, fmt: 'pp' });

                // CEO Concentration
                var aConc = fullA ? fullA._ceoConcPct : null;
                var bConc = fullB ? fullB._ceoConcPct : null;
                rows.push({ label: 'Concentration', a: aConc != null ? aConc.toFixed(0) + '%' : '\u2014', b: bConc != null ? bConc.toFixed(0) + '%' : '\u2014',
                    delta: (aConc != null && bConc != null) ? (bConc - aConc) : null, fmt: 'pp' });

                // Pay Ratio
                var aRatio = cA.ratio;
                var bRatio = cB.ratio;
                rows.push({ label: 'Pay Ratio', a: aRatio ? aRatio + ':1' : '\u2014', b: bRatio ? bRatio + ':1' : '\u2014',
                    delta: (aRatio && bRatio) ? (((bRatio - aRatio) / aRatio) * 100) : null, fmt: 'pct' });

                // Governance Score
                var aGov = fullA ? fullA._govScore : null;
                var bGov = fullB ? fullB._govScore : null;
                rows.push({ label: 'Governance', a: aGov != null ? aGov + '/100' : '\u2014', b: bGov != null ? bGov + '/100' : '\u2014',
                    delta: (aGov != null && bGov != null) ? (bGov - aGov) : null, fmt: 'abs' });

                // Say-on-Pay
                var aSop = fullA && fullA._sopApproval != null ? fullA._sopApproval : null;
                var bSop = fullB && fullB._sopApproval != null ? fullB._sopApproval : null;
                rows.push({ label: 'Say-on-Pay', a: aSop != null ? aSop.toFixed(1) + '%' : '\u2014', b: bSop != null ? bSop.toFixed(1) + '%' : '\u2014',
                    delta: (aSop != null && bSop != null) ? (bSop - aSop) : null, fmt: 'pp' });

                // Worker Pay
                var aWorker = cA.worker;
                var bWorker = cB.worker;
                rows.push({ label: 'Worker Pay', a: aWorker ? _fmtComp(aWorker) : '\u2014', b: bWorker ? _fmtComp(bWorker) : '\u2014',
                    delta: (aWorker && bWorker) ? (((bWorker - aWorker) / aWorker) * 100) : null, fmt: 'pct' });

                rows.forEach(function(r) {
                    html += '<div class="pf-epc-label">' + r.label + '</div>';
                    html += '<div class="pf-epc-val">' + r.a + '</div>';
                    html += '<div class="pf-epc-val">' + r.b + '</div>';
                    if (r.delta != null) {
                        var sign = r.delta >= 0 ? '+' : '';
                        var cls = Math.abs(r.delta) < 3 ? 'pf-epc-flat' : (r.delta > 0 ? 'pf-epc-up' : 'pf-epc-down');
                        var suffix = r.fmt === 'pct' ? '%' : (r.fmt === 'pp' ? 'pp' : '');
                        html += '<div class="pf-epc-val pf-epc-delta ' + cls + '">' + sign + r.delta.toFixed(0) + suffix + '</div>';
                    } else {
                        html += '<div class="pf-epc-val pf-epc-delta">\u2014</div>';
                    }
                });
                html += '</div>'; // pf-epc-grid
                html += '<button class="pf-epc-compare-btn" data-ep-a="' + epA + '" data-ep-b="' + epB + '" title="Open full side-by-side comparison of ' + epA + ' and ' + epB + '">\u2696 Compare in Detail \u2192</button>';
                // "Compare all path nodes" button — only shown for 3-4 node paths
                if (pathResult.nodes.length >= 3 && pathResult.nodes.length <= 4) {
                    html += '<button class="pf-epc-compare-all-btn" data-path-tickers="' + pathResult.nodes.join(',') + '" title="Compare all ' + pathResult.nodes.length + ' companies in this path">\u{1F50D} Compare All ' + pathResult.nodes.length + ' Path Nodes \u2192</button>';
                }
                html += '</div>'; // pf-endpoint-compare
            }
        }

        // Export + Show on Scatter buttons
        html += '<div class="pf-export-group">';
        html += '<button class="pf-export-btn" id="pf-export-btn" title="Copy path summary to clipboard">';
        html += '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
        html += ' Export Text';
        html += '</button>';
        html += '<button class="pf-export-csv-btn" id="pf-export-csv-btn" title="Copy path as CSV to clipboard">';
        html += '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>';
        html += ' Export CSV';
        html += '</button>';
        // Show on Scatter button — scrolls to scatter chart with current axis context
        var scXSel = document.getElementById('scatter-x-metric');
        var scYSel = document.getElementById('scatter-y-metric');
        var scXLabel = scXSel ? scXSel.options[scXSel.selectedIndex].text : '';
        var scYLabel = scYSel ? scYSel.options[scYSel.selectedIndex].text : '';
        var scAxisHint = (scXLabel && scYLabel) ? scXLabel + ' vs ' + scYLabel : '';
        html += '<button class="pf-show-scatter-btn" id="pf-show-scatter-btn" title="View this path overlaid on the scatter plot' + (scAxisHint ? ' (' + scAxisHint + ')' : '') + '">';
        html += '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="7.5" cy="7.5" r="2"/><circle cx="16.5" cy="16.5" r="2"/><circle cx="17" cy="7" r="2"/><circle cx="7" cy="17" r="2"/><path d="M3 3v18h18"/></svg>';
        html += ' Show on Scatter';
        if (scAxisHint) html += '<span class="pf-scatter-axis-hint">' + scAxisHint + '</span>';
        html += '</button>';
        html += '</div>';

        pfResult.innerHTML = html;
        pfResult.classList.add('visible');

        // Click handlers on chips
        pfResult.querySelectorAll('.path-node-chip').forEach(function(chip) {
            chip.addEventListener('click', function() {
                var ticker = chip.getAttribute('data-ticker');
                if (window.findCompanyInTable) window.findCompanyInTable(ticker);
            });
        });

        // "Compare in Detail" button — bridges path finder to full comparison panel
        var epcBtn = pfResult.querySelector('.pf-epc-compare-btn');
        if (epcBtn) {
            epcBtn.addEventListener('click', function() {
                var a = epcBtn.getAttribute('data-ep-a');
                var b = epcBtn.getAttribute('data-ep-b');
                if (!a || !b || !window._compareSet || !window._toggleCompare) return;
                // Clear existing comparison set
                window._compareSet.length = 0;
                // Add both endpoints
                window._toggleCompare(a);
                window._toggleCompare(b);
                // Trigger comparison render and scroll to it
                if (window._triggerComparisonRender) window._triggerComparisonRender();
                var section = document.getElementById('comparison-section');
                if (section) section.scrollIntoView({ behavior: (typeof getScrollBehavior === 'function' ? getScrollBehavior() : 'smooth'), block: 'start' });
            });
        }

        // "Compare All Path Nodes" button handler
        var epcAllBtn = pfResult.querySelector('.pf-epc-compare-all-btn');
        if (epcAllBtn) {
            epcAllBtn.addEventListener('click', function() {
                var tickers = epcAllBtn.getAttribute('data-path-tickers');
                if (!tickers || !window._compareSet || !window._toggleCompare) return;
                var tickerList = tickers.split(',');
                // Clear existing comparison set
                window._compareSet.length = 0;
                // Add all path nodes
                tickerList.forEach(function(t) { window._toggleCompare(t); });
                // Trigger comparison render and scroll to it
                if (window._triggerComparisonRender) window._triggerComparisonRender();
                var section = document.getElementById('comparison-section');
                if (section) section.scrollIntoView({ behavior: (typeof getScrollBehavior === 'function' ? getScrollBehavior() : 'smooth'), block: 'start' });
                // ARIA announcement
                if (typeof announce === 'function') announce('Comparing ' + tickerList.length + ' path companies: ' + tickerList.join(', '));
            });
        }

        // "Export Path" button handler — builds formatted text and copies to clipboard
        var exportBtn = pfResult.querySelector('#pf-export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', function() {
                if (!pathResult || !pathResult.nodes || pathResult.nodes.length < 2) return;
                var pathTickers = pathResult.nodes;
                var arrows = pathTickers.join(' \u2192 ');
                var lines = [];
                lines.push('S&P 500 Peer Path: ' + arrows);
                lines.push('\u2500'.repeat(Math.min(60, arrows.length + 20)));
                lines.push('');
                pathTickers.forEach(function(ticker, idx) {
                    var n = nodeMap[ticker];
                    var comp = _compLookup[ticker];
                    var name = n ? n.name : '';
                    var sector = n ? n.sector : '';
                    var ceo = (comp && comp.ceo) ? comp.ceo : '';
                    var pay = (comp && comp.total > 0) ? _fmtComp(comp.total) : 'N/A';
                    lines.push((idx + 1) + '. ' + ticker + (name ? ' \u2014 ' + name : ''));
                    var details = [];
                    if (ceo) details.push('CEO: ' + ceo);
                    details.push('Total Pay: ' + pay);
                    if (sector) details.push('Sector: ' + sector);
                    lines.push('   ' + details.join(' | '));
                    if (comp && comp._breakdown) {
                        var bd = comp._breakdown;
                        var parts = [];
                        if (bd.salary > 0) parts.push('Salary ' + _fmtComp(bd.salary));
                        if (bd.stock > 0) parts.push('Stock ' + _fmtComp(bd.stock));
                        if (bd.options > 0) parts.push('Options ' + _fmtComp(bd.options));
                        if (bd.bonus > 0) parts.push('Bonus ' + _fmtComp(bd.bonus));
                        if (bd.incentive > 0) parts.push('Incentive ' + _fmtComp(bd.incentive));
                        if (parts.length > 0) lines.push('   ' + parts.join(', '));
                    }
                    lines.push('');
                });
                // Summary stats
                var hops = pathTickers.length - 1;
                var sectorSet = new Set();
                pathTickers.forEach(function(t) { var nd = nodeMap[t]; if (nd && nd.sector) sectorSet.add(nd.sector); });
                var pathVals = [];
                pathTickers.forEach(function(t) { var c = _compLookup[t]; if (c && c.total > 0) pathVals.push(c.total); });
                lines.push('\u2500'.repeat(Math.min(60, arrows.length + 20)));
                var summary = hops + ' hop' + (hops !== 1 ? 's' : '') + ' \u00b7 ' + sectorSet.size + ' sector' + (sectorSet.size !== 1 ? 's' : '');
                if (pathVals.length >= 2) {
                    var mn = Math.min.apply(null, pathVals);
                    var mx = Math.max.apply(null, pathVals);
                    summary += ' \u00b7 Pay range: ' + _fmtComp(mn) + '\u2013' + _fmtComp(mx);
                    if (mn > 0) summary += ' \u00b7 ' + (mx / mn).toFixed(1) + '\u00d7 spread';
                }
                lines.push(summary);
                lines.push('Source: SEC DEF 14A proxy statements | S&P 500 Executive Compensation Tracker');

                var text = lines.join('\n');
                navigator.clipboard.writeText(text).then(function() {
                    exportBtn.classList.add('pf-export-copied');
                    exportBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Copied!';
                    if (typeof announce === 'function') announce('Path summary copied to clipboard');
                    setTimeout(function() {
                        exportBtn.classList.remove('pf-export-copied');
                        exportBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Export Text';
                    }, 2000);
                }).catch(function() {
                    // Fallback: select text in a temporary textarea
                    var ta = document.createElement('textarea');
                    ta.value = text;
                    ta.style.position = 'fixed';
                    ta.style.left = '-9999px';
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                    exportBtn.classList.add('pf-export-copied');
                    exportBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Copied!';
                    setTimeout(function() {
                        exportBtn.classList.remove('pf-export-copied');
                        exportBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Export Text';
                    }, 2000);
                });
            });
        }

        // "Export CSV" button handler — builds CSV and copies to clipboard
        var csvBtn = pfResult.querySelector('#pf-export-csv-btn');
        if (csvBtn) {
            csvBtn.addEventListener('click', function() {
                if (!pathResult || !pathResult.nodes || pathResult.nodes.length < 2) return;
                var pathTickers = pathResult.nodes;
                var csvLines = [];
                csvLines.push('Step,Ticker,Company,CEO,Sector,Total Pay,Salary,Stock Awards,Option Awards,Bonus,Incentive,Pension/NQDC,Other');
                pathTickers.forEach(function(ticker, idx) {
                    var n = nodeMap[ticker];
                    var comp = _compLookup[ticker];
                    var name = n ? (n.name || '').replace(/,/g, ';') : '';
                    var sector = n ? (n.sector || '').replace(/,/g, ';') : '';
                    var ceo = (comp && comp.ceo) ? comp.ceo.replace(/,/g, ';') : '';
                    var pay = (comp && comp.total > 0) ? comp.total : '';
                    var bd = (comp && comp._breakdown) ? comp._breakdown : {};
                    csvLines.push([
                        idx + 1, ticker, '"' + name + '"', '"' + ceo + '"', '"' + sector + '"',
                        pay, bd.salary || '', bd.stock || '', bd.options || '',
                        bd.bonus || '', bd.incentive || '', bd.pension || '', bd.other || ''
                    ].join(','));
                });
                var csvText = csvLines.join('\n');
                navigator.clipboard.writeText(csvText).then(function() {
                    csvBtn.classList.add('pf-export-copied');
                    csvBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Copied!';
                    if (typeof announce === 'function') announce('Path CSV copied to clipboard');
                    setTimeout(function() {
                        csvBtn.classList.remove('pf-export-copied');
                        csvBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg> Export CSV';
                    }, 2000);
                }).catch(function() {
                    var ta = document.createElement('textarea');
                    ta.value = csvText;
                    ta.style.position = 'fixed';
                    ta.style.left = '-9999px';
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                    csvBtn.classList.add('pf-export-copied');
                    csvBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Copied!';
                    setTimeout(function() {
                        csvBtn.classList.remove('pf-export-copied');
                        csvBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg> Export CSV';
                    }, 2000);
                });
            });
        }

        // "Show on Scatter" button handler — scrolls to scatter chart panel
        var scatterBtn = pfResult.querySelector('#pf-show-scatter-btn');
        if (scatterBtn) {
            scatterBtn.addEventListener('click', function() {
                // Ensure scatter path overlay is active
                if (window._activePathFinderNodes && typeof window._redrawScatterForPathOverlay === 'function') {
                    window._redrawScatterForPathOverlay();
                }
                // Scroll to scatter chart panel
                var scPanel = document.getElementById('scatter-chart-panel');
                if (scPanel) {
                    var hdr = document.querySelector('.sticky-header, .section-nav');
                    var off = hdr ? hdr.offsetHeight : 0;
                    var top = scPanel.getBoundingClientRect().top + window.scrollY - off - 16;
                    window.scrollTo({ top: top, behavior: typeof getScrollBehavior === 'function' ? getScrollBehavior() : 'smooth' });
                }
                // Update section nav highlight
                var navLinks = document.querySelectorAll('.section-nav-link');
                navLinks.forEach(function(link) {
                    link.classList.toggle('active', link.getAttribute('data-section') === 'sector-chart-panel');
                });
                // ARIA announcement
                var axisCtx = '';
                var xSel = document.getElementById('scatter-x-metric');
                var ySel = document.getElementById('scatter-y-metric');
                if (xSel && ySel) {
                    axisCtx = ' (' + xSel.options[xSel.selectedIndex].text + ' vs ' + ySel.options[ySel.selectedIndex].text + ')';
                }
                if (typeof announce === 'function') announce('Showing peer path on scatter plot' + axisCtx);
            });
        }
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
        // Expose active path to scatter plot for path overlay
        if (result && result.nodes && result.nodes.length >= 2) {
            window._activePathFinderNodes = result.nodes.slice();
        } else {
            window._activePathFinderNodes = null;
        }
        // Trigger scatter redraw for path overlay
        if (typeof window._redrawScatterForPathOverlay === 'function') {
            window._redrawScatterForPathOverlay();
        }
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
                if ((compHeatmapMode || prHeatmapMode || ccHeatmapMode || gerHeatmapMode || communityMode) && newIdx >= 0 && newIdx < items.length) {
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
