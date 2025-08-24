let cy;

function buildCy() {
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
  if (name === 'dagre') {
    cy.layout({ name: 'dagre', rankDir: 'LR', nodeSep: 60, rankSep: 140, edgeSep: 30 }).run();
  } else {
    cy.layout({ name: 'grid', fit: true, avoidOverlap: true }).run();
  }
  cy.fit(cy.elements(), 40);
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