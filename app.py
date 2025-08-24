# app.py
import os
import sys

from typing import List, Optional, Dict, Any, Set, Tuple
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jira import JIRA

# ---------------------------
# Config via environment vars
# ---------------------------
JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# "Start date" / "End date" are often custom fields in Jira.
START_DATE_FIELD = "customfield_10015"
END_DATE_FIELD   = "customfield_10016"

# Fields we’ll ask Jira for (add as needed)
JIRA_FIELDS = ",".join([
    "summary",
    "status",
    "issuetype",
    "issuelinks",
    START_DATE_FIELD,
    END_DATE_FIELD,
    "duedate"
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

# -------------------
# JQL builder helper
# -------------------
def build_jql(
    project: Optional[str],
    text: Optional[str],
    statuses: Optional[List[str]],
) -> str:
    parts: List[str] = []
    if project:
        parts.append(f'project = "{project}"')
    if text:
        # Search summary/description (adjust to taste)
        # phrase search if spaces
        q = text.replace('"', '\\"')
        parts.append(f'text ~ "{q}"')
    if statuses:
        quoted = ", ".join([f'"{s}"' for s in statuses if s.strip()])
        if quoted:
            parts.append(f"status in ({quoted})")
    # Only include issues you can browse; add any extra constraints you need
    return " AND ".join(parts) if parts else "ORDER BY updated DESC"

# --------------------
# API response models
# --------------------
class Graph(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

# ----------------
# API: /api/search
# ----------------
@app.get("/api/search", response_model=Graph)
def api_search(
    project: Optional[str] = Query(None, description="Jira project key, e.g. NSE"),
    text: Optional[str] = Query(None, description="Free text search"),
    statuses: Optional[str] = Query(None, description='Comma-separated statuses, e.g. "In Progress,Analysis"'),
    jql: Optional[str] = Query(None, description="Raw JQL (overrides other filters)"),
    max_results: int = Query(50, ge=1, le=500),
) -> JSONResponse:
    # Build JQL
    status_list = [s.strip() for s in (statuses or "").split(",")] if statuses else None
    query_jql = jql if jql else build_jql(project, text, status_list)

    sys.stderr.write("%s\n" % query_jql)

    # Query Jira (paginate if needed)
    client = jira_client()
    start_at = 0
    fetched = []
    while True:
        batch = client.enhanced_search_issues(
            jql_str=query_jql,
            maxResults=min(50, max_results - len(fetched)),
            fields=JIRA_FIELDS,
        )
        fetched.extend(batch)
        if len(fetched) >= max_results or len(batch) == 0:
            break
        start_at += len(batch)

    # Build nodes from original query results
    nodes_by_key: Dict[str, Dict[str, Any]] = {}
    original_keys = set()
    
    for issue in fetched:
        fields = issue.fields
        key = issue.key
        start = getattr(fields, START_DATE_FIELD, None)
        end = getattr(fields, END_DATE_FIELD, None)
        status = fields.status.name if getattr(fields, "status", None) else None

        nodes_by_key[key] = {
            "id": key,  # use key as id so edges can refer to it
            "key": key,
            "summary": fields.summary,
            "status": status or "-",
            "start": start or "-",
            "end": end or "-",
            "url": f"{JIRA_SERVER.rstrip('/')}/browse/{key}",
            "isOriginal": True,  # Mark as original query result
        }
        original_keys.add(key)
    
    # Collect linked issue keys that have blocking relationships
    linked_keys = set()
    for issue in fetched:
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

            # Check for outward blocking relationships
            if hasattr(link, "outwardIssue") and link.outwardIssue:
                other_key = link.outwardIssue.key
                if (name == "blocks" or outward == "blocks") and other_key not in original_keys:
                    linked_keys.add(other_key)

            # Check for inward blocking relationships  
            if hasattr(link, "inwardIssue") and link.inwardIssue:
                other_key = link.inwardIssue.key
                if (name == "blocks" or inward == "is blocked by") and other_key not in original_keys:
                    linked_keys.add(other_key)
    
    # Fetch details for linked issues
    linked_issues = []
    if linked_keys:
        for linked_key in linked_keys:
            try:
                linked_issue = client.issue(linked_key, fields=JIRA_FIELDS)
                linked_issues.append(linked_issue)
            except Exception as e:
                # Skip issues we can't access
                sys.stderr.write(f"Could not fetch linked issue {linked_key}: {e}\n")
                continue
        
        # Add linked issues as nodes
        for issue in linked_issues:
            fields = issue.fields
            key = issue.key
            start = getattr(fields, START_DATE_FIELD, None)
            end = getattr(fields, END_DATE_FIELD, None)
            status = fields.status.name if getattr(fields, "status", None) else None

            nodes_by_key[key] = {
                "id": key,
                "key": key,
                "summary": fields.summary,
                "status": status or "-",
                "start": start or "-",
                "end": end or "-",
                "url": f"{JIRA_SERVER.rstrip('/')}/browse/{key}",
                "isOriginal": False,  # Mark as linked issue
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

    edges = [{"source": s, "target": t, "label": lbl} for (s, t, lbl) in edges_set]

    return JSONResponse({"nodes": list(nodes_by_key.values()), "edges": edges})

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