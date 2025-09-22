# app.py
import os
import sys

from typing import List, Optional, Dict, Any, Set, Tuple
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jira import JIRA
from cache import get_cache

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

# Lazy Jira client
_jira_client: Optional[JIRA] = None
def jira_client() -> JIRA:
    global _jira_client
    if _jira_client is None:
        _jira_client = JIRA(
            options={"server": JIRA_SERVER},
            basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN),
            validate=True,
        )
    return _jira_client

def get_cached_issue(issue_key: str, fields: str = JIRA_FIELDS) -> Optional[Dict[str, Any]]:
    """
    Get issue data with caching.
    
    First checks cache, then falls back to API if not found.
    """
    cache = get_cache()
    
    # Try to get from cache first
    cached_issue = cache.get_issue(issue_key)
    if cached_issue is not None:
        sys.stderr.write(f"Cache hit for issue {issue_key}\n")
        return cached_issue
    
    # Cache miss, fetch from API
    sys.stderr.write(f"Cache miss for issue {issue_key}, fetching from API\n")
    try:
        client = jira_client()
        issue = client.issue(issue_key, fields=fields)
        
        # Use the raw JSON data from JIRA API instead of manual serialization
        # This avoids serialization issues with non-scalar keys and complex objects
        issue_data = issue.raw
        
        # Cache the result
        cache.set_issue(issue_key, issue_data)
        return issue_data
        
    except Exception as e:
        sys.stderr.write(f"Failed to fetch issue {issue_key}: {e}\n")
        return None

def search_issues_with_cache(jql: str, max_results: int = 50, fields: str = JIRA_FIELDS) -> List[Any]:
    """
    Search for issues with caching support.
    
    This is a simple wrapper that doesn't cache search results individually,
    but could be extended to do so.
    """
    try:
        client = jira_client()
        next_page_token = None
        fetched = []
        
        while True:
            batch = client.enhanced_search_issues(
                jql_str=jql,
                maxResults=min(50, max_results - len(fetched)),
                fields=fields,
                nextPageToken=next_page_token
            )
            next_page_token = getattr(batch, "nextPageToken", None)
            fetched.extend(batch)
            if len(fetched) >= max_results or not next_page_token:
                break
        
        return fetched
    except Exception as e:
        sys.stderr.write(f"Failed to search issues: {e}\n")
        return []

def fetch_dependency_tree(initial_keys: Set[str], original_keys: Set[str], max_depth: int = 10,
                          traverse_children: bool = False) -> Set[str]:
    """
    Recursively fetch the full dependency tree for blocking relationships using cache.

    Args:
        initial_keys: Starting set of issue keys to traverse
        original_keys: Set of original query result keys to avoid including
        max_depth: Maximum depth to traverse to prevent infinite loops

    Returns:
        Set of all issue keys in the dependency tree
    """
    all_linked_keys = set()
    visited = set()
    to_process = list(initial_keys)
    depth = 0

    while to_process and depth < max_depth:
        current_batch = to_process
        to_process = []
        depth += 1

        for key in current_batch:
            if key in visited or key in original_keys:
                continue

            visited.add(key)

            # Use cached issue lookup
            issue_data = get_cached_issue(key, "issuelinks,subtasks")
            if issue_data is None:
                continue
                
            all_linked_keys.add(key)

            # Collect blocking dependencies from this issue
            links = issue_data.get("fields", {}).get("issuelinks", []) or []
            for link in links:
                link_type = link.get("type", {})
                if not link_type:
                    continue

                # Normalize names
                name = (link_type.get("name", "") or "").lower()
                outward = (link_type.get("outward", "") or "").lower()
                inward = (link_type.get("inward", "") or "").lower()

                # Check for outward blocking relationships
                if "outwardIssue" in link and link["outwardIssue"]:
                    other_key = link["outwardIssue"].get("key")
                    if other_key and (name == "blocks" or outward == "blocks") and other_key not in visited and other_key not in original_keys:
                        to_process.append(other_key)

                # Check for inward blocking relationships
                if "inwardIssue" in link and link["inwardIssue"]:
                    other_key = link["inwardIssue"].get("key")
                    if other_key and (name == "blocks" or inward == "is blocked by") and other_key not in visited and other_key not in original_keys:
                        to_process.append(other_key)

            # Collect subtasks from this issue
            if traverse_children:
                subtasks = issue_data.get("fields", {}).get("subtasks", []) or []
                for subtask in subtasks:
                    subtask_key = subtask.get("key")
                    if subtask_key and subtask_key not in visited and subtask_key not in original_keys:
                        to_process.append(subtask_key)

    return all_linked_keys

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

    # Query Jira using the cached search function
    fetched = search_issues_with_cache(query_jql, max_results, JIRA_FIELDS)

    # Execute highlight JQL query if provided to get highlighted ticket keys
    highlighted_keys = set()
    if highlight_jql:
        try:
            sys.stderr.write(f"Highlight JQL: {highlight_jql}\n")
            highlight_results = search_issues_with_cache(highlight_jql, 1000, "key")
            highlighted_keys = {issue.key for issue in highlight_results}
            sys.stderr.write(f"Found {len(highlighted_keys)} tickets to highlight\n")
        except Exception as e:
            sys.stderr.write(f"Error executing highlight JQL: {e}\n")
            # Continue without highlighting if the query fails

    # Build nodes from original query results
    nodes_by_key: Dict[str, Dict[str, Any]] = {}
    original_keys = set()
    linked_keys = set()

    # We will use the recursive approach to traverse the tree but limit depth to 1 if we just want immediate blockers
    if show_dependency_tree:
        max_depth = 10  # Limit depth to prevent infinite loops
    else:
        max_depth = 1

    # Use recursive traversal to get full dependency tree (this adds child issues too)
    initial_linked_keys = set()
    for issue in fetched:
        key = issue.key
        links = getattr(issue.fields, "issuelinks", []) or []
        for link in links:
            lt = getattr(link, "type", None)
            if not lt:
                continue

            # Normalize names
            name = (lt.name or "").lower()
            outward = (lt.outward or "").lower()
            inward = (lt.inward or "").lower()

            # Check for outward blocking relationships
            if hasattr(link, "outwardIssue") and link.outwardIssue:
                other_key = link.outwardIssue.key
                if (name == "blocks" or outward == "blocks") and other_key not in original_keys:
                    initial_linked_keys.add(other_key)

            # Check for inward blocking relationships
            if hasattr(link, "inwardIssue") and link.inwardIssue:
                other_key = link.inwardIssue.key
                if (name == "blocks" or inward == "is blocked by") and other_key not in original_keys:
                    initial_linked_keys.add(other_key)

        # Recursively fetch the full dependency tree
        linked_keys = fetch_dependency_tree(initial_linked_keys, original_keys,
                                            traverse_children=child_as_blocking, max_depth=max_depth)
        sys.stderr.write(f"Fetched {len(linked_keys)} issues in dependency tree\n")

    # Fetch details for linked issues using cache
    linked_issues = []
    if linked_keys:
        for linked_key in linked_keys:
            issue_data = get_cached_issue(linked_key, JIRA_FIELDS)
            if issue_data is not None:
                # Convert back to object-like structure for compatibility
                class MockIssue:
                    def __init__(self, data):
                        self.key = data["key"]
                        self.fields = type('obj', (object,), data["fields"])()
                        # Add special handling for status
                        if "status" in data["fields"] and isinstance(data["fields"]["status"], dict):
                            self.fields.status = type('obj', (object,), data["fields"]["status"])()
                
                mock_issue = MockIssue(issue_data)
                linked_issues.append(mock_issue)
            else:
                sys.stderr.write(f"Could not fetch linked issue {linked_key}\n")
        
        # Add linked issues as nodes
        for issue in linked_issues:
            fields = issue.fields
            key = issue.key
            start = getattr(fields, START_DATE_FIELD, None)
            end = getattr(fields, END_DATE_FIELD, None)
            story_points = getattr(fields, STORY_POINTS_FIELD, None)
            status = fields.status.name if getattr(fields, "status", None) else None

            nodes_by_key[key] = {
                "id": key,
                "key": key,
                "summary": fields.summary,
                "status": status or "-",
                "start": start or "-",
                "end": end or "-",
                "story_points": story_points,
                "url": f"{JIRA_SERVER.rstrip('/')}/browse/{key}",
                "isOriginal": False,  # Mark as linked issue
                "isHighlighted": key in highlighted_keys,  # Mark if ticket should be highlighted
            }

    # Build edges from "blocks" links (current → other means current blocks other)
    # Now we need to check all issues (original + linked) for their relationships
    edges_set: Set[Tuple[str, str, str]] = set()
    all_issues = fetched + linked_issues
    
    for issue in all_issues:
        key = issue.key
        links = getattr(issue.fields, "issuelinks", []) or []
        for link in links:
            lt = getattr(link, "type", None)
            if not lt:
                continue

            # Normalize names, Jira typically has name="Blocks", outward="blocks", inward="is blocked by"
            name = (lt.name or "").lower()
            outward = (lt.outward or "").lower()
            inward = (lt.inward or "").lower()

            # link.outwardIssue exists -> this issue -> outwardIssue (e.g., "blocks")
            if hasattr(link, "outwardIssue") and link.outwardIssue:
                other_key = link.outwardIssue.key
                if name == "blocks" or outward == "blocks":
                    if key in nodes_by_key and other_key in nodes_by_key:
                        edges_set.add((key, other_key, "blocks"))

            # link.inwardIssue exists -> inwardIssue -> this issue (e.g., "is blocked by")
            if hasattr(link, "inwardIssue") and link.inwardIssue:
                other_key = link.inwardIssue.key
                # Create an edge from blocker to current issue
                if name == "blocks" or inward == "is blocked by":
                    if key in nodes_by_key and other_key in nodes_by_key:
                        edges_set.add((other_key, key, "blocks"))

        # Build edges from subtasks (subtask -> parent means subtask blocks parent)
        if child_as_blocking:
            subtasks = getattr(issue.fields, "subtasks", []) or []
            for subtask in subtasks:
                if hasattr(subtask, "key"):
                    subtask_key = subtask.key
                    if key in nodes_by_key and subtask_key in nodes_by_key:
                        edges_set.add((subtask_key, key, "subtask"))

    edges = [{"source": s, "target": t, "label": lbl} for (s, t, lbl) in edges_set]

    sys.stdout.write(f"Edges: {edges}\n")

    # Create the result
    result = {"nodes": list(nodes_by_key.values()), "edges": edges}
    
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