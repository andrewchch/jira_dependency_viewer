# JIRA Dependency Viewer

JIRA Dependency Viewer is a Python FastAPI web application that visualizes JIRA issue dependencies and relationships using an interactive graph interface powered by Cytoscape.js.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Dependencies
- Install required Python dependencies:
  ```bash
  pip3 install fastapi uvicorn jira pydantic
  ```
  Takes ~30 seconds normally. NEVER CANCEL - can take up to 5 minutes with slow network. Set timeout to 300+ seconds.
  
- If pip install fails due to network timeouts, try:
  ```bash
  pip3 install --timeout 300 --retries 3 fastapi uvicorn jira pydantic
  ```
  
- If network issues persist, install packages individually:
  ```bash
  pip3 install fastapi
  pip3 install uvicorn
  pip3 install jira
  pip3 install pydantic
  ```

- Optionally install development tools:
  ```bash
  pip3 install flake8 black
  ```

### Environment Configuration
- Set required JIRA credentials as environment variables:
  ```bash
  export JIRA_SERVER="https://your-domain.atlassian.net"
  export JIRA_EMAIL="your-email@domain.com"
  export JIRA_API_TOKEN="your-api-token"
  ```
- The application will fail to search JIRA issues without these credentials, but the UI will still load.

### Running the Application
- Start the development server:
  ```bash
  python3 app.py
  ```
  OR
  ```bash
  uvicorn app:app --host 127.0.0.1 --port 8000
  ```
- Server starts in ~2 seconds. Access at http://127.0.0.1:8000
- NEVER CANCEL: Server startup is very fast (2-3 seconds), but wait for "Application startup complete" message.

### Code Quality and Validation
- Run linting (recommended before committing):
  ```bash
  flake8 --max-line-length=120 *.py
  ```
- Format code (optional):
  ```bash
  black *.py
  ```
- Validate Python syntax:
  ```bash
  python3 -m py_compile app.py jirautils.py
  ```

## Validation

### Functional Testing
After making changes, ALWAYS test the following scenarios:

1. **Server Startup Test**:
   ```bash
   python3 app.py
   ```
   Verify you see "Application startup complete" in ~2 seconds.

2. **UI Loading Test**:
   - Navigate to http://127.0.0.1:8000
   - Verify the search form loads with fields: Project, Text search, Statuses, JQL, Layout, Max results
   - Verify the "Search" button is present and clickable

3. **API Endpoint Test**:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/api/search?jql=ORDER%20BY%20updated%20DESC"
   ```
   - Returns 200 if JIRA credentials are valid
   - Returns 500 if JIRA credentials are missing/invalid (expected behavior)

4. **Import Test**:
   ```bash
   python3 -c "import app; print('App imports successfully')"
   ```
   Should complete in <1 second with no errors.

### Manual User Scenario Testing
When JIRA credentials are available, test a complete user workflow:
1. Open http://127.0.0.1:8000
2. Enter a project key (e.g., "TEST")
3. Click "Search"
4. Verify dependency graph renders with nodes and edges
5. Click on a node to verify it opens JIRA issue in new tab
6. Test layout switching between "Grid" and "Flow (L→R)"

## Architecture and Code Navigation

### Key Files
- **`app.py`** (187 lines): Main FastAPI application
  - REST API endpoints: `/` (UI), `/api/search` (JIRA data)
  - JIRA client configuration and JQL query building
  - Node/edge graph construction from JIRA issue links
  
- **`index.html`** (203 lines): Single-page frontend
  - Cytoscape.js graph visualization
  - Search form and layout controls
  - Responsive design with CSS Grid

- **`jirautils.py`** (99 lines): JIRA data processing utilities
  - `get_sprint_changes()`: Extract sprint change history
  - `calculate_time_in_status()`: Time tracking calculations

### Application Flow
1. User loads `/` → `app.py:index()` serves `index.html`
2. User submits search → JavaScript calls `/api/search`
3. API builds JQL query → queries JIRA → processes links → returns graph JSON
4. Frontend renders nodes/edges with Cytoscape.js

### Dependencies and External Services
- **Python packages**: fastapi, uvicorn, jira, pydantic
- **JavaScript CDNs**: Cytoscape.js, Dagre layout, HTML labels
- **External service**: JIRA instance (requires valid credentials)

## Common Development Tasks

### Adding New Search Filters
1. Modify `build_jql()` in `app.py` to add new JQL conditions
2. Update `api_search()` parameters to accept new filter
3. Add corresponding input field in `index.html` search form
4. Update JavaScript `doSearch()` to pass new parameter

### Modifying Graph Visualization
1. Node styling: Update CSS `.ticket` class in `index.html`
2. Layout options: Modify `runLayout()` function
3. Node data: Update node construction in `app.py:api_search()`
4. Link types: Modify edge detection logic in issue links processing

### Environment Variables and Configuration
- `JIRA_SERVER`: JIRA instance URL
- `JIRA_EMAIL`: User email for authentication  
- `JIRA_API_TOKEN`: API token for authentication
- `START_DATE_FIELD`, `END_DATE_FIELD`: Custom field IDs (currently "customfield_10015/16")

## Troubleshooting

### Common Issues
- **Import errors**: Run `pip3 install fastapi uvicorn jira pydantic`
- **JIRA authentication fails**: Verify JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN environment variables
- **Empty search results**: Check JQL syntax, verify project exists, ensure user has read permissions
- **Graph not rendering**: Check browser console for JavaScript errors (CDN blocking)

### Development Setup Verification
Run this complete verification sequence:
```bash
# 1. Install dependencies (may fail due to network issues)
pip3 install fastapi uvicorn jira pydantic flake8
# If network issues: pip3 install --timeout 300 --retries 3 fastapi uvicorn jira pydantic

# 2. Verify Python file structure without dependencies
python3 -m py_compile app.py jirautils.py

# 3. Test import availability (will fail if step 1 failed)
python3 -c "import app; print('Success')"

# 4. Check code quality (only if flake8 installed)
flake8 --max-line-length=120 *.py

# 5. Start server (only if dependencies available)
python3 app.py
# Wait for "Application startup complete"

# 6. Test endpoints (in another terminal, only if server running)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/  # Should return 200
curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/api/search?jql=ORDER%20BY%20updated%20DESC"  # 200 or 500
```

**Note**: If pip install fails due to network timeouts, the application structure is still valid and can be analyzed without external dependencies.