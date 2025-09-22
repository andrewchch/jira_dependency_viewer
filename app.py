# app.py
import os
import sys

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from cache import get_cache
from jira_helper import JiraHelper
from graph_builder import GraphBuilder

# ---------------------------
# Config via environment vars
# ---------------------------
JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# "Start date" / "End date" are often custom fields in Jira.
START_DATE_FIELD = "customfield_10015"
END_DATE_FIELD   = "customfield_10016"
# Story points is typically a custom field in Jira
STORY_POINTS_FIELD = "customfield_10005"

# Fields we’ll ask Jira for (add as needed)
JIRA_FIELDS = ",".join([
    "summary",
    "status",
    "issuetype",
    "issuelinks",
    "subtasks",
    START_DATE_FIELD,
    END_DATE_FIELD,
    "duedate",
    STORY_POINTS_FIELD
])

# -------------
# FastAPI app
# -------------
app = FastAPI(title="Jira Dependency Graph")

# Initialize helper classes
jira_helper = JiraHelper(JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_FIELDS)
graph_builder = GraphBuilder(jira_helper, JIRA_SERVER, START_DATE_FIELD, END_DATE_FIELD, STORY_POINTS_FIELD)

# Serve static files
@app.get("/styles.css")
def get_styles():
    styles_path = os.path.join(os.path.dirname(__file__), "styles.css")
    return FileResponse(styles_path, media_type="text/css")

@app.get("/script.js")
def get_script():
    script_path = os.path.join(os.path.dirname(__file__), "script.js")
    return FileResponse(script_path, media_type="application/javascript")

@app.get("/demo")
def get_demo():
    demo_path = os.path.join(os.path.dirname(__file__), "demo.html")
    return FileResponse(demo_path, media_type="text/html")

# -------------------
# API response models
# -------------------
class Graph(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

# ----------------------
# API: Cache Management
# ----------------------
@app.post("/api/cache/clear")
def clear_cache():
    """Clear all cached data."""
    cache = get_cache()
    deleted_count = cache.clear_all()
    return JSONResponse({
        "message": f"Cache cleared successfully. Deleted {deleted_count} files.",
        "deleted_count": deleted_count
    })

@app.get("/api/cache/stats")
def get_cache_stats():
    """Get cache statistics."""
    cache = get_cache()
    stats = cache.get_cache_stats()
    return JSONResponse(stats)

@app.get("/api/cache/keys")
def list_cache_keys():
    """List all cached issue keys."""
    cache = get_cache()
    keys = cache.list_cached_issue_and_search_keys()
    return JSONResponse({"cached_keys": keys})

@app.get("/api/cache/issue/{issue_key}")
def get_cached_issue_endpoint(issue_key: str):
    """Get cached data for a specific issue key."""
    cache = get_cache()
    cached_data = cache.get_issue(issue_key)
    if cached_data is None:
        return JSONResponse({"error": "Issue not found in cache"}, status_code=404)
    return JSONResponse(cached_data)

# ----------------
# API: /api/search
# ----------------
@app.get("/api/search", response_model=Graph)
def api_search(
    jql: Optional[str] = Query(None, description="Main JQL query"),
    highlight_jql: Optional[str] = Query(None, description="Highlight JQL query (tickets matching this will be highlighted)"),
    max_results: int = Query(50, ge=1, le=500),
    child_as_blocking: bool = Query(False, description="Show child relationship as blocking link"),
    show_dependency_tree: bool = Query(False, description="Show full dependency tree instead of just immediate blockers"),
) -> JSONResponse:
    cache = get_cache()
    
    # Create cache key for this search
    search_hash = cache.create_search_hash(
        jql=jql or "",
        highlight_jql=highlight_jql,
        max_results=max_results,
        child_as_blocking=child_as_blocking,
        show_dependency_tree=show_dependency_tree
    )
    
    # Try to get cached search results
    cached_result = cache.get_search(search_hash)
    if cached_result is not None:
        sys.stderr.write(f"Cache hit for search query\n")
        return JSONResponse(cached_result)
    
    sys.stderr.write(f"Cache miss for search query, executing...\n")
    
    # Build JQL - now we only use the main jql parameter
    query_jql = jql if jql else "ORDER BY rank DESC"

    sys.stderr.write(f"Main JQL: {query_jql}\n")

    # Query Jira using the helper
    fetched = jira_helper.search_issues_with_cache(query_jql, max_results, JIRA_FIELDS)

    # Execute highlight JQL query if provided to get highlighted ticket keys
    highlighted_keys = set()
    if highlight_jql:
        try:
            sys.stderr.write(f"Highlight JQL: {highlight_jql}\n")
            highlight_results = jira_helper.search_issues_with_cache(highlight_jql, 1000, "key")
            highlighted_keys = {issue.key for issue in highlight_results}
            sys.stderr.write(f"Found {len(highlighted_keys)} tickets to highlight\n")
        except Exception as e:
            sys.stderr.write(f"Error executing highlight JQL: {e}\n")
            # Continue without highlighting if the query fails

    # Build graph data using the graph builder
    graph_data = graph_builder.build_graph_data(fetched, highlighted_keys, show_dependency_tree, child_as_blocking)
    
    # Create the result
    result = {"nodes": graph_data["nodes"], "edges": graph_data["edges"], "jql": query_jql}
    
    # Cache the search result
    cache.set_search(search_hash, result)
    
    return JSONResponse(result)

# -------------
# Single-page UI
# -------------


@app.get("/", response_class=HTMLResponse)
def index():
    # Load the index.html file
    index_html = ""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if not os.path.exists(index_path):
        return JSONResponse({"error": "index.html not found"}, status_code=404)

    with open(index_path, "r", encoding="utf-8") as f:
        index_html = f.read()

    return HTMLResponse(index_html)


# So we can debug with `uvicorn app:app --reload`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)