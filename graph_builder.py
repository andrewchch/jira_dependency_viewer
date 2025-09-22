# graph_builder.py
import sys
from typing import List, Dict, Any, Set, Tuple
from jira_helper import JiraHelper


class GraphBuilder:
    """Builder class for creating graph data (nodes and edges) for the presentation layer."""
    
    def __init__(self, jira_helper: JiraHelper, jira_server: str, start_date_field: str, end_date_field: str, story_points_field: str):
        self.jira_helper = jira_helper
        self.jira_server = jira_server
        self.start_date_field = start_date_field
        self.end_date_field = end_date_field
        self.story_points_field = story_points_field
    
    def build_graph_data(self, fetched_issues: List[Any], highlighted_keys: Set[str], 
                        show_dependency_tree: bool, child_as_blocking: bool) -> Dict[str, Any]:
        """
        Build nodes and edges for the graph visualization.
        
        Args:
            fetched_issues: List of issues from the main search query
            highlighted_keys: Set of issue keys that should be highlighted
            show_dependency_tree: Whether to show full dependency tree or just immediate blockers
            child_as_blocking: Whether to show child relationships as blocking links
            
        Returns:
            Dictionary containing nodes and edges for the graph
        """
        # Build nodes from original query results
        nodes_by_key: Dict[str, Dict[str, Any]] = {}
        original_keys = set()
        
        # First add all original query results as nodes
        for issue in fetched_issues:
            key = issue.key
            original_keys.add(key)
            
            fields = issue.fields
            start = getattr(fields, self.start_date_field, None)
            end = getattr(fields, self.end_date_field, None)
            story_points = getattr(fields, self.story_points_field, None)
            status = fields.status.name if getattr(fields, "status", None) else None

            nodes_by_key[key] = {
                "id": key,
                "key": key,
                "summary": fields.summary,
                "status": status or "-",
                "start": start or "-",
                "end": end or "-",
                "story_points": story_points,
                "url": f"{self.jira_server.rstrip('/')}/browse/{key}",
                "isOriginal": True,  # Mark as original query result
                "isHighlighted": key in highlighted_keys,  # Mark if ticket should be highlighted
            }

        # Determine dependency tree depth
        if show_dependency_tree:
            max_depth = 10  # Limit depth to prevent infinite loops
        else:
            max_depth = 1

        # Collect linked issues from dependency tree
        linked_keys = self._collect_linked_issues(fetched_issues, original_keys, max_depth, child_as_blocking)
        
        # Add linked issues as nodes
        self._add_linked_issues_as_nodes(linked_keys, highlighted_keys, nodes_by_key)
        
        # Build edges
        edges = self._build_edges(fetched_issues, linked_keys, nodes_by_key, child_as_blocking)
        
        sys.stdout.write(f"Edges: {edges}\n")
        
        return {"nodes": list(nodes_by_key.values()), "edges": edges}
    
    def _collect_linked_issues(self, fetched_issues: List[Any], original_keys: Set[str], 
                              max_depth: int, child_as_blocking: bool) -> Set[str]:
        """Collect all linked issues from the dependency tree."""
        # Use recursive traversal to get full dependency tree
        initial_linked_keys = set()
        for issue in fetched_issues:
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
        linked_keys = self.jira_helper.fetch_dependency_tree(
            initial_linked_keys, original_keys,
            traverse_children=child_as_blocking, max_depth=max_depth
        )
        sys.stderr.write(f"Fetched {len(linked_keys)} issues in dependency tree\n")
        
        return linked_keys
    
    def _add_linked_issues_as_nodes(self, linked_keys: Set[str], highlighted_keys: Set[str], 
                                   nodes_by_key: Dict[str, Dict[str, Any]]):
        """Add linked issues as nodes to the graph."""
        if not linked_keys:
            return
            
        for linked_key in linked_keys:
            issue = self.jira_helper.get_cached_issue(linked_key)
            if issue is not None:
                fields = issue.fields
                key = issue.key
                start = getattr(fields, self.start_date_field, None)
                end = getattr(fields, self.end_date_field, None)
                story_points = getattr(fields, self.story_points_field, None)
                status = fields.status.name if getattr(fields, "status", None) else None

                nodes_by_key[key] = {
                    "id": key,
                    "key": key,
                    "summary": fields.summary,
                    "status": status or "-",
                    "start": start or "-",
                    "end": end or "-",
                    "story_points": story_points,
                    "url": f"{self.jira_server.rstrip('/')}/browse/{key}",
                    "isOriginal": False,  # Mark as linked issue
                    "isHighlighted": key in highlighted_keys,  # Mark if ticket should be highlighted
                }
            else:
                sys.stderr.write(f"Could not fetch linked issue {linked_key}\n")
    
    def _build_edges(self, fetched_issues: List[Any], linked_keys: Set[str], 
                    nodes_by_key: Dict[str, Dict[str, Any]], child_as_blocking: bool) -> List[Dict[str, str]]:
        """Build edges from issue relationships."""
        # Get all linked issues
        linked_issues = []
        for linked_key in linked_keys:
            issue = self.jira_helper.get_cached_issue(linked_key)
            if issue is not None:
                linked_issues.append(issue)
        
        # Build edges from "blocks" links (current → other means current blocks other)
        edges_set: Set[Tuple[str, str, str]] = set()
        all_issues = fetched_issues + linked_issues
        
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

        return [{"source": s, "target": t, "label": lbl} for (s, t, lbl) in edges_set]