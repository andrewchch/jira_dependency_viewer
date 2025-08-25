let cy;
let ganttInitialized = false;

// Story points to duration mapping (in days)
function storyPointsToDuration(storyPoints) {
  if (storyPoints == null || storyPoints === 0) return 1; // Default to 1 day if no story points
  
  const mapping = {
    1: 1,
    2: 2, 
    3: 3,
    5: 5,
    8: 10,
    13: 20
  };
  
  return mapping[storyPoints] || storyPoints; // Use direct mapping if available, otherwise use the value itself
}

function buildCy() {
  // Check if cytoscape is available
  if (typeof cytoscape === 'undefined') {
    console.warn('Cytoscape library not loaded. Graph functionality will be limited.');
    document.getElementById('cy').innerHTML = `
      <div class="gantt-placeholder">
        <h2>Graph View</h2>
        <p>The Cytoscape.js library is required for graph visualization.</p>
        <p>Please ensure all dependencies are loaded properly.</p>
      </div>
    `;
    return;
  }
  
  cy = cytoscape({
    container: document.getElementById('cy'),
    elements: [],
    style: [
      {
        selector: 'node',
        style: {
          width: '240px', height: '120px', shape: 'roundrectangle',
          'background-opacity': 0, 'border-width': 0,
          label: ' ', 'text-opacity': 0
        }
      },
      {
        selector: 'edge',
        style: {
          width: 3,
          'curve-style': 'unbundled-bezier',
          'control-point-distance': 40,
          'target-arrow-shape': 'triangle',
          'target-arrow-color': '#1d70b8',
          'line-color': '#1d70b8',
          'edge-text-rotation': 'autorotate',
          'font-size': 11,
          'color': '#1d70b8',
          'text-background-color': '#fff',
          'text-background-opacity': 1,
          'text-background-padding': 2,
          label: 'data(label)'
        }
      },
      { selector: 'node:hover', style: { 'overlay-opacity': 0, 'cursor': 'pointer' } }
    ],
    wheelSensitivity: 0.2
  });

  cy.nodeHtmlLabel([{
    query: 'node',
    halign: 'center', valign: 'center', halignBox: 'center', valignBox: 'center',
    tpl: (d) => `
      <div class="ticket${d.isOriginal ? ' original' : ''}">
        <div class="key">${d.key}</div>
        <div class="summary">${d.summary || ""}</div>
        <div class="dates">Start: ${d.start || '-'} &nbsp;&nbsp; End: ${d.end || '-'}</div>
        <span class="status">${d.status || '-'}</span>
      </div>`
  }]);

  // Click → open JIRA
  cy.on('tap', 'node', (evt) => {
    const n = evt.target;
    const url = n.data('url');
    if (url) window.open(url, '_blank', 'noopener,noreferrer');
  });
}

async function fetchGraph(params) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`/api/search?${qs}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function runLayout(name) {
  if (name === 'gantt') {
    showGanttChart();
  } else {
    showCytoscapeChart();
    
    // Only run cytoscape layouts if cytoscape is available
    if (typeof cy !== 'undefined' && cy) {
      if (name === 'dagre') {
        cy.layout({ name: 'dagre', rankDir: 'LR', nodeSep: 60, rankSep: 140, edgeSep: 30 }).run();
      } else {
        cy.layout({ name: 'grid', fit: true, avoidOverlap: true }).run();
      }
      cy.fit(cy.elements(), 40);
    } else {
      console.warn('Cytoscape not available. Layout changes will not be applied.');
    }
  }
}

function showCytoscapeChart() {
  document.getElementById('cy').style.display = 'block';
  document.getElementById('gantt_here').style.display = 'none';
}

function showGanttChart() {
  document.getElementById('cy').style.display = 'none';
  document.getElementById('gantt_here').style.display = 'block';
  
  if (!ganttInitialized) {
    initializeGantt();
    ganttInitialized = true;
  }
  
  renderGanttChart();
}

function initializeGantt() {
  // Check if gantt library is available
  if (typeof gantt === 'undefined') {
    console.warn('dhtmlxGantt library not loaded. Gantt chart functionality will be limited.');
    // Create a placeholder message
    document.getElementById('gantt_here').innerHTML = `
      <div class="gantt-placeholder">
        <h2>Gantt Chart View</h2>
        <p>The dhtmlxGantt library is required for this feature.</p>
        <p>In a production environment, this would display an interactive Gantt chart with:</p>
        <ul>
          <li>Tasks based on JIRA tickets with story point durations</li>
          <li>Dependency relationships between tickets</li>
          <li>Progress indicators based on ticket status</li>
          <li>Story point to duration mapping (1pt=1day, 2pt=2days, etc.)</li>
        </ul>
      </div>
    `;
    return;
  }
  
  // Configure gantt chart
  gantt.config.date_format = "%Y-%m-%d %H:%i:%s";
  gantt.config.scale_unit = "day";
  gantt.config.date_scale = "%M %d";
  gantt.config.subscales = [
    {unit:"day", step:1, date:"%j, %D"}
  ];
  
  // Enable auto-scheduling and dependencies
  gantt.config.auto_scheduling = true;
  gantt.config.auto_scheduling_strict = true;
  
  // Initialize the gantt chart
  gantt.init("gantt_here");
}

function transformDataForGantt(nodes, edges) {
  const today = new Date();
  const tasks = [];
  const links = [];
  
  nodes.forEach((node, index) => {
    const duration = storyPointsToDuration(node.story_points);
    
    // Calculate start date - use provided start date or default to today
    let startDate = today;
    if (node.start && node.start !== '-') {
      const parsedStart = new Date(node.start);
      if (!isNaN(parsedStart.getTime())) {
        startDate = parsedStart;
      }
    }
    
    // Calculate end date based on duration
    const endDate = new Date(startDate);
    endDate.setDate(endDate.getDate() + duration);
    
    tasks.push({
      id: node.id,
      text: `${node.key}: ${node.summary}`,
      start_date: startDate,
      duration: duration,
      progress: node.status === 'Done' ? 1 : (node.status === 'In Progress' ? 0.5 : 0),
      $open: true,
      color: node.isOriginal ? '#0052cc' : '#666666'
    });
  });
  
  // Add dependency links
  edges.forEach((edge, index) => {
    links.push({
      id: index + 1,
      source: edge.source,
      target: edge.target,
      type: "0" // finish-to-start dependency
    });
  });
  
  return { data: tasks, links: links };
}

function renderGanttChart() {
  // Check if gantt library is available
  if (typeof gantt === 'undefined') {
    // Gantt is not available, placeholder is already shown
    return;
  }
  
  const elements = cy.elements();
  const nodes = elements.nodes().map(node => node.data());
  const edges = elements.edges().map(edge => edge.data());
  
  const ganttData = transformDataForGantt(nodes, edges);
  
  // Clear and load new data
  gantt.clearAll();
  gantt.parse(ganttData);
}

async function doSearch() {
  const spinner = document.getElementById('spinner');
  spinner.style.display = 'flex';  // show spinner

  try {
    const project = document.getElementById('project').value.trim();
    const text = document.getElementById('text').value.trim();
    const statuses = document.getElementById('statuses').value.trim();
    const jql = document.getElementById('jql').value.trim();
    const maxResults = document.getElementById('maxResults').value || '50';
    const layoutName = document.getElementById('layout').value;

    const graph = await fetchGraph({ project, text, statuses, jql, max_results: maxResults });

    // Reset graph
    cy.elements().remove();

    // Convert API shape to Cytoscape elements
    const elements = [
      ...graph.nodes.map(n => ({ data: n, group: 'nodes' })),
      ...graph.edges.map(e => ({ data: e, group: 'edges' }))
    ];
    cy.add(elements);
    runLayout(layoutName);
  } catch (err) {
    console.error("Search failed:", err);
    alert("Search failed: " + err.message);
  } finally {
    spinner.style.display = 'none';  // hide spinner
  }
}

// UI wiring
document.getElementById('searchBtn').addEventListener('click', doSearch);
document.getElementById('layout').addEventListener('change', () => runLayout(document.getElementById('layout').value));

// Boot
buildCy();
// Optional: set some defaults so first search works quickly
// document.getElementById('project').value = 'NSE';
// doSearch();