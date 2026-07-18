/* ===== Peer Network Force-Directed Graph ===== */

const SECTOR_COLORS = {
  'Information Technology': '#58a6ff',
  'Communication Services': '#ff7b72',
  'Consumer Discretionary': '#f778ba',
  'Consumer Staples': '#79c0ff',
  'Health Care': '#3fb950',
  'Financials': '#d29922',
  'Industrials': '#8b8ce6',
  'Real Estate': '#56d4dd',
  'Energy': '#ffa657',
  'Materials': '#a5d6ff',
  'Utilities': '#7ee787'
};

// Normalize alternative sector names to our canonical keys
const SECTOR_ALIASES = {
  'Technology': 'Information Technology',
  'Healthcare': 'Health Care',
  'Consumer Cyclical': 'Consumer Discretionary',
  'Consumer Defensive': 'Consumer Staples',
  'Financial Services': 'Financials',
  'Basic Materials': 'Materials'
};

function getSectorColor(sector) {
  const canonical = SECTOR_ALIASES[sector] || sector;
  return SECTOR_COLORS[canonical] || '#8b949e';
}

function initNetwork(peerData) {
  const container = document.getElementById('network-container');
  if (!container) return;

  const tooltip = document.getElementById('network-tooltip');
  const width = container.clientWidth;
  const height = Math.min(600, Math.max(400, width * 0.5));

  const svg = d3.select('#network-svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');

  svg.selectAll('*').remove();

  const defs = svg.append('defs');

  // Arrowhead marker
  defs.append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '0 -3 6 6')
    .attr('refX', 20)
    .attr('refY', 0)
    .attr('markerWidth', 5)
    .attr('markerHeight', 5)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-3L6,0L0,3')
    .attr('fill', 'rgba(255,255,255,0.15)');

  const g = svg.append('g');

  // Zoom
  const zoom = d3.zoom()
    .scaleExtent([0.3, 4])
    .on('zoom', (event) => g.attr('transform', event.transform));

  svg.call(zoom);

  const nodes = peerData.nodes.map(d => ({ ...d }));
  const edges = peerData.edges.map(d => ({ ...d }));

  // Map ticker to node
  const nodeMap = {};
  nodes.forEach(n => { nodeMap[n.ticker] = n; });

  // Build links - only include edges where both nodes exist
  const links = edges
    .filter(e => nodeMap[e.source] && nodeMap[e.target])
    .map(e => ({
      source: e.source,
      target: e.target,
      group_type: e.group_type
    }));

  // Scale node radius by in_degree
  const maxInDegree = d3.max(nodes, d => d.in_degree) || 1;
  const radiusScale = d3.scaleSqrt().domain([0, maxInDegree]).range([6, 22]);

  // Force simulation
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.ticker).distance(90).strength(0.3))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => radiusScale(d.in_degree) + 6))
    .force('x', d3.forceX(width / 2).strength(0.05))
    .force('y', d3.forceY(height / 2).strength(0.05));

  // Draw links
  const link = g.append('g')
    .attr('class', 'links')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', d => d.group_type === 'primary' ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.06)')
    .attr('stroke-width', d => d.group_type === 'primary' ? 1.5 : 0.8)
    .attr('stroke-dasharray', d => d.group_type === 'secondary' ? '3,3' : null)
    .attr('marker-end', 'url(#arrowhead)');

  // Draw nodes
  const node = g.append('g')
    .attr('class', 'nodes')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('cursor', 'pointer')
    .call(d3.drag()
      .on('start', dragStarted)
      .on('drag', dragged)
      .on('end', dragEnded));

  // Node circle
  node.append('circle')
    .attr('r', d => radiusScale(d.in_degree))
    .attr('fill', d => getSectorColor(d.sector))
    .attr('stroke', 'rgba(0,0,0,0.4)')
    .attr('stroke-width', 1.5)
    .attr('opacity', 0.9);

  // Node label (show for high in-degree or source nodes)
  node.filter(d => d.in_degree >= 2 || d.out_degree > 0)
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', d => radiusScale(d.in_degree) + 14)
    .attr('font-size', '10px')
    .attr('font-weight', '600')
    .attr('fill', 'rgba(230,237,243,0.7)')
    .attr('font-family', 'var(--font-mono)')
    .text(d => d.ticker);

  // Interaction: hover
  node.on('mouseover', function (event, d) {
    // Highlight connected links
    link.attr('stroke', l => {
      const src = typeof l.source === 'object' ? l.source.ticker : l.source;
      const tgt = typeof l.target === 'object' ? l.target.ticker : l.target;
      if (src === d.ticker || tgt === d.ticker) return getSectorColor(d.sector);
      return 'rgba(255,255,255,0.04)';
    }).attr('stroke-width', l => {
      const src = typeof l.source === 'object' ? l.source.ticker : l.source;
      const tgt = typeof l.target === 'object' ? l.target.ticker : l.target;
      if (src === d.ticker || tgt === d.ticker) return 2.5;
      return 0.5;
    });

    // Dim other nodes
    node.select('circle').attr('opacity', n => {
      if (n.ticker === d.ticker) return 1;
      const connected = links.some(l => {
        const src = typeof l.source === 'object' ? l.source.ticker : l.source;
        const tgt = typeof l.target === 'object' ? l.target.ticker : l.target;
        return (src === d.ticker && tgt === n.ticker) || (tgt === d.ticker && src === n.ticker);
      });
      return connected ? 0.9 : 0.2;
    });

    // Tooltip
    tooltip.innerHTML = `
      <div class="tooltip-ticker">${d.ticker}</div>
      <div class="tooltip-name">${d.name}</div>
      <div class="tooltip-stats">
        <div>
          <div class="tooltip-stat-label">Cited as peer</div>
          <div class="tooltip-stat-value">${d.in_degree}×</div>
        </div>
        <div>
          <div class="tooltip-stat-label">Peers selected</div>
          <div class="tooltip-stat-value">${d.out_degree}</div>
        </div>
        <div>
          <div class="tooltip-stat-label">Sector</div>
          <div class="tooltip-stat-value" style="color:${getSectorColor(d.sector)}">${d.sector}</div>
        </div>
      </div>
    `;
    tooltip.classList.add('visible');
  })
  .on('mousemove', function (event) {
    tooltip.style.left = (event.clientX + 16) + 'px';
    tooltip.style.top = (event.clientY - 10) + 'px';
  })
  .on('mouseout', function () {
    link.attr('stroke', d => d.group_type === 'primary' ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.06)')
      .attr('stroke-width', d => d.group_type === 'primary' ? 1.5 : 0.8);
    node.select('circle').attr('opacity', 0.9);
    tooltip.classList.remove('visible');
  });

  // Click to lock highlight
  node.on('click', function (event, d) {
    event.stopPropagation();
    const connected = new Set([d.ticker]);
    links.forEach(l => {
      const src = typeof l.source === 'object' ? l.source.ticker : l.source;
      const tgt = typeof l.target === 'object' ? l.target.ticker : l.target;
      if (src === d.ticker) connected.add(tgt);
      if (tgt === d.ticker) connected.add(src);
    });

    node.select('circle')
      .attr('opacity', n => connected.has(n.ticker) ? 1 : 0.15);

    link.attr('stroke', l => {
      const src = typeof l.source === 'object' ? l.source.ticker : l.source;
      const tgt = typeof l.target === 'object' ? l.target.ticker : l.target;
      return (src === d.ticker || tgt === d.ticker) ? getSectorColor(d.sector) : 'rgba(255,255,255,0.03)';
    }).attr('stroke-width', l => {
      const src = typeof l.source === 'object' ? l.source.ticker : l.source;
      const tgt = typeof l.target === 'object' ? l.target.ticker : l.target;
      return (src === d.ticker || tgt === d.ticker) ? 2.5 : 0.4;
    });
  });

  // Click background to reset
  svg.on('click', () => {
    node.select('circle').attr('opacity', 0.9);
    link.attr('stroke', d => d.group_type === 'primary' ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.06)')
      .attr('stroke-width', d => d.group_type === 'primary' ? 1.5 : 0.8);
  });

  // Tick
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  function dragStarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragEnded(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }

  // Build legend
  buildNetworkLegend(nodes);
}

function buildNetworkLegend(nodes) {
  const legendEl = document.getElementById('network-legend');
  if (!legendEl) return;

  const sectors = [...new Set(nodes.map(n => n.sector))].sort();
  const counts = {};
  nodes.forEach(n => { counts[n.sector] = (counts[n.sector] || 0) + 1; });

  legendEl.innerHTML = `
    <div class="legend-title">Sectors</div>
    ${sectors.map(s => `
      <div class="legend-item">
        <span class="legend-dot" style="background:${getSectorColor(s)}"></span>
        <span>${s} (${counts[s]})</span>
      </div>
    `).join('')}
    <div style="margin-top:8px;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px">
      <div class="legend-item" style="font-size:10px;color:var(--text-muted)">
        <span style="display:inline-block;width:16px;height:2px;background:rgba(255,255,255,0.12);border-radius:1px"></span>
        Primary peer
      </div>
      <div class="legend-item" style="font-size:10px;color:var(--text-muted)">
        <span style="display:inline-block;width:16px;height:2px;background:rgba(255,255,255,0.06);border-radius:1px;border:none;border-top:2px dashed rgba(255,255,255,0.1)"></span>
        Secondary peer
      </div>
    </div>
  `;
}

window.initNetwork = initNetwork;
window.getSectorColor = getSectorColor;
window.SECTOR_COLORS = SECTOR_COLORS;
