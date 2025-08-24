# Jira Dependency Viewer

A web-based tool for visualizing Jira issue dependencies as interactive graphs. This application helps teams understand the relationships between issues and identify potential bottlenecks in their project workflows.

## Features

- **Interactive Dependency Graphs**: Visualize Jira issues and their "blocks" relationships using Cytoscape.js
- **Multiple Search Options**: Search by project key, text, status, or custom JQL queries
- **Flexible Layouts**: Choose between grid and flow (left-to-right) layouts for optimal visualization
- **Issue Details**: Each issue displays key, summary, start/end dates, and current status
- **Direct Jira Integration**: Click any issue card to open it directly in Jira
- **Real-time Data**: Fetches live data from your Jira instance via REST API
- **Customizable Results**: Limit search results (1-500 issues) to manage performance

## Quick Start

### Prerequisites

- Python 3.7+
- Access to a Jira instance with API token authentication
- Required Python packages: `fastapi`, `jira`, `pydantic`, `uvicorn`

### Installation

1. Clone the repository:
```bash
git clone https://github.com/andrewchch/jira_dependency_viewer.git
cd jira_dependency_viewer
```

2. Install dependencies:
```bash
pip install fastapi jira pydantic uvicorn
```

3. Set up environment variables:
```bash
export JIRA_SERVER="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@example.com"
export JIRA_API_TOKEN="your-api-token"
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and go to `http://localhost:8000`

## Configuration

### Environment Variables

The following environment variables are required:

| Variable | Description | Example |
|----------|-------------|---------|
| `JIRA_SERVER` | Your Jira instance URL | `https://company.atlassian.net` |
| `JIRA_EMAIL` | Your Jira account email | `user@company.com` |
| `JIRA_API_TOKEN` | Jira API token for authentication | `ATT3xFfGF0nYma...` |

### Getting a Jira API Token

1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Give it a label (e.g., "Dependency Viewer")
4. Copy the generated token and use it as `JIRA_API_TOKEN`

### Custom Fields

The application looks for start and end dates in these custom fields:
- Start Date: `customfield_10015`
- End Date: `customfield_10016`

To use different custom fields, modify the `START_DATE_FIELD` and `END_DATE_FIELD` constants in `app.py`.

## Usage

### Search Options

1. **Project Search**: Enter a Jira project key (e.g., "PROJ") to see all issues in that project
2. **Text Search**: Search issue summaries and descriptions for specific keywords
3. **Status Filter**: Filter by issue statuses using comma-separated values (e.g., "In Progress,Analysis")
4. **JQL Query**: Use advanced Jira Query Language for complex searches
5. **Max Results**: Limit the number of results (1-500) to manage performance

### Layout Options

- **Grid Layout**: Arranges issues in a regular grid pattern
- **Flow Layout (L→R)**: Displays dependencies in a left-to-right flow diagram showing dependency chains

### Interacting with the Graph

- **Zoom**: Use mouse wheel to zoom in/out
- **Pan**: Click and drag to move around the graph
- **Open Issues**: Click any issue card to open it in Jira
- **Hover Effects**: Hover over issues for visual feedback

## Architecture

### Backend (FastAPI)

- **`app.py`**: Main FastAPI application with REST API endpoints
- **`jirautils.py`**: Utility functions for Jira data processing (sprint changes, time-in-status calculations)
- **API Endpoint**: `/api/search` - Returns graph data as JSON with nodes and edges

### Frontend (HTML/JavaScript)

- **`index.html`**: Single-page application with embedded CSS and JavaScript
- **Cytoscape.js**: Graph visualization library
- **Dagre**: Layout algorithm for hierarchical graphs
- **HTML Labels**: Custom rendering for issue cards

### Data Flow

1. User enters search criteria in the web interface
2. Frontend sends AJAX request to `/api/search` endpoint
3. Backend queries Jira API using provided credentials
4. Issue data is processed to create nodes and dependency edges
5. Graph data is returned as JSON to the frontend
6. Cytoscape.js renders the interactive graph

## API Reference

### GET /api/search

Search for Jira issues and return dependency graph data.

**Parameters:**
- `project` (optional): Jira project key
- `text` (optional): Text search in summaries/descriptions
- `statuses` (optional): Comma-separated list of statuses
- `jql` (optional): Custom JQL query (overrides other filters)
- `max_results` (optional): Maximum number of results (1-500, default: 50)

**Response:**
```json
{
  "nodes": [
    {
      "id": "PROJ-123",
      "key": "PROJ-123", 
      "summary": "Issue title",
      "status": "In Progress",
      "start": "2024-01-15",
      "end": "2024-01-30",
      "url": "https://company.atlassian.net/browse/PROJ-123"
    }
  ],
  "edges": [
    {
      "source": "PROJ-123",
      "target": "PROJ-124", 
      "label": "blocks"
    }
  ]
}
```

## Troubleshooting

### Common Issues

**"Authentication failed"**
- Verify your `JIRA_EMAIL` and `JIRA_API_TOKEN` are correct
- Ensure your API token hasn't expired
- Check that your account has access to the Jira projects you're searching

**"No issues found"**
- Verify the project key exists and you have access to it
- Check your search criteria and filters
- Try a broader search or remove status filters

**"Custom field not found"**
- The start/end date fields may be different in your Jira instance
- Update `START_DATE_FIELD` and `END_DATE_FIELD` in `app.py`
- Contact your Jira admin to confirm custom field IDs

**Performance Issues**
- Reduce `max_results` for large result sets
- Use more specific search criteria
- Consider filtering by project or status

### Getting Custom Field IDs

To find custom field IDs in your Jira instance:
1. Go to Jira Administration → Issues → Custom Fields
2. Click on the field you want to use
3. Look for the ID in the URL: `customfield_XXXXX`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Please check the repository for license details.