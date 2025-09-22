# Jira Dependency Viewer

A web-based tool for visualizing Jira issue dependencies as interactive graphs. This application helps teams understand the relationships between issues and identify potential bottlenecks in their project workflows.

## Features

- **Interactive Dependency Graphs**: Visualize Jira issues and their "blocks" relationships using Cytoscape.js
- **Multiple Search Options**: Search by project key, text, status, or custom JQL queries
- **Flexible Layouts**: Choose between grid, flow (left-to-right), and Gantt chart layouts for optimal visualization
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
- **Gantt Chart**: Timeline view showing tasks with durations based on story points and dependency relationships

### Interacting with the Graph

- **Zoom**: Use mouse wheel to zoom in/out
- **Pan**: Click and drag to move around the graph
- **Open Issues**: Click any issue card to open it in Jira
- **Hover Effects**: Hover over issues for visual feedback

### Gantt Chart Features

The Gantt chart view provides timeline-based project visualization:

- **Story Point Duration Mapping**:
  - 1 point = 1 day
  - 2 points = 2 days  
  - 3 points = 3 days
  - 5 points = 5 days
  - 8 points = 10 days
  - 13 points = 20 days
- **Dependency Visualization**: Shows blocking relationships between tasks
- **Progress Indicators**: Visual progress based on ticket status (Done=100%, In Progress=50%, others=0%)
- **Timeline View**: Displays tasks along a calendar timeline with proper scheduling

## Caching

The application includes a local file-based cache to improve performance and enable testing without API access.

### Cache Features

- **Automatic Caching**: Issue details and search results are automatically cached
- **Performance Improvement**: Avoids redundant API calls for recently fetched data  
- **TTL Support**: Cache entries expire after 1 hour by default
- **Testing Support**: Enables functional testing with mock data
- **Cache Management**: Clear cache via UI button or API endpoint

### Cache Management

- **Clear Cache Button**: Available in the main interface to clear all cached data
- **API Endpoints**:
  - `POST /api/cache/clear` - Clear all cache entries
  - `GET /api/cache/stats` - Get cache statistics

### Using Cache for Testing

1. **Populate Test Data**: Use the `demo_cache.py` script to create sample data:
   ```bash
   python demo_cache.py
   ```

2. **Test Without JIRA API**: The app will use cached data instead of making API calls

3. **Reset Cache**: Use the "Clear Cache" button to return to live API mode

### Cache Storage

- Cache files are stored in the `cache/` directory (excluded from git)
- Issues and search results are stored separately for optimal organization
- JSON format for human-readable cache files
- Automatic cleanup of expired and corrupted cache entries

## Testing

The project includes unit tests to ensure functionality and reliability of the caching system.

### Running Unit Tests

You can run the unit tests in several ways:

#### Using Python's unittest module (recommended):
```bash
python -m unittest test_cache.py -v
```

#### Using test discovery to run all tests:
```bash
python -m unittest discover -v
```

#### Running the test file directly:
```bash
python test_cache.py
```

### Test Coverage

The current test suite includes:
- Cache initialization and directory structure
- Issue caching (set/get operations)
- Search result caching
- Cache expiration and TTL handling
- Cache statistics and management
- Search hash generation
- Cache clearing functionality
- Error handling for invalid cache files
- Path safety and security
- Fixture data loading for testing

### Running Tests Before Contributing

Before submitting any changes, please ensure all tests pass:

```bash
# Run all tests with verbose output
python -m unittest test_cache.py -v

# Ensure all 11 tests pass
```

All tests should complete successfully with an "OK" status.

## Architecture

### Backend (FastAPI)

- **`app.py`**: Main FastAPI application with REST API endpoints
- **`jirautils.py`**: Utility functions for Jira data processing (sprint changes, time-in-status calculations)
- **API Endpoint**: `/api/search` - Returns graph data as JSON with nodes and edges

### Frontend (HTML/JavaScript)

- **`index.html`**: Main HTML page with form controls and layout structure
- **`styles.css`**: CSS styling for the application layout and components
- **`script.js`**: JavaScript application logic for graph interaction and data fetching
- **Cytoscape.js**: Graph visualization library
- **dhtmlxGantt**: Gantt chart visualization library for timeline views
- **Dagre**: Layout algorithm for hierarchical graphs
- **HTML Labels**: Custom rendering for issue cards

### Data Flow

1. User enters search criteria in the web interface
2. Frontend sends AJAX request to `/api/search` endpoint
3. Backend queries Jira API using provided credentials
4. Issue data is processed to create nodes and dependency edges
5. Graph data is returned as JSON to the frontend
6. Cytoscape.js or dhtmlxGantt renders the interactive visualization

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

### POST /api/cache/clear

Clear all cached data.

**Response:**
```json
{
  "message": "Cache cleared successfully. Deleted 5 files.",
  "deleted_count": 5
}
```

### GET /api/cache/stats

Get cache statistics.

**Response:**
```json
{
  "total_issues": 10,
  "total_searches": 3,
  "expired_issues": 2,
  "expired_searches": 0,
  "cache_size_mb": 0.15
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
4. Test thoroughly (see [Testing](#testing) section for running unit tests)
5. Submit a pull request

## License

This project is open source. Please check the repository for license details.