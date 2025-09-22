# jira_helper.py
import sys
from typing import List, Optional, Set, Any
from jira import JIRA, Issue
from cache import get_cache


class JiraHelper:
    """Helper class for JIRA operations including caching and issue retrieval."""
    
    def __init__(self, jira_server: str, jira_email: str, jira_api_token: str, jira_fields: str):
        self.jira_server = jira_server
        self.jira_email = jira_email
        self.jira_api_token = jira_api_token
        self.jira_fields = jira_fields
        self._jira_client: Optional[JIRA] = None
    
    def get_client(self) -> JIRA:
        """Get JIRA client with lazy initialization."""
        if self._jira_client is None:
            self._jira_client = JIRA(
                options={"server": self.jira_server},
                basic_auth=(self.jira_email, self.jira_api_token),
                validate=True,
            )
        return self._jira_client

    def get_cached_issue(self, issue_key: str, fields: str = None) -> Issue | None:
        """
        Get issue data with caching.
        
        First checks cache, then falls back to API if not found.
        """
        if fields is None:
            fields = self.jira_fields
            
        cache = get_cache()
        client = self.get_client()

        # Try to get from cache first
        cached_issue = cache.get_issue(issue_key)
        if cached_issue is not None:
            sys.stderr.write(f"Cache hit for issue {issue_key}\n")

            # Deserialize back to Issue object
            return Issue(client._options, client._session, raw=cached_issue)
        
        # Cache miss, fetch from API
        sys.stderr.write(f"Cache miss for issue {issue_key}, fetching from API\n")
        try:
            issue = client.issue(issue_key, fields=fields)
            
            # Use the raw JSON data from JIRA API instead of manual serialization
            # This avoids serialization issues with non-scalar keys and complex objects
            issue_data = issue.raw
            
            # Cache the result
            cache.set_issue(issue_key, issue_data)
            return issue
            
        except Exception as e:
            sys.stderr.write(f"Failed to fetch issue {issue_key}: {e}\n")
            return None

    def search_issues_with_cache(self, jql: str, max_results: int = 50, fields: str = None) -> List[Any]:
        """
        Search for issues with caching support.
        
        This is a simple wrapper that doesn't cache search results individually,
        but could be extended to do so.
        """
        if fields is None:
            fields = self.jira_fields
            
        try:
            client = self.get_client()
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

    def fetch_dependency_tree(self, initial_keys: Set[str], original_keys: Set[str], max_depth: int = 10,
                              traverse_children: bool = False) -> Set[str]:
        """
        Recursively fetch the full dependency tree for blocking relationships using cache.

        Args:
            initial_keys: Starting set of issue keys to traverse
            original_keys: Set of original query result keys to avoid including
            max_depth: Maximum depth to traverse to prevent infinite loops
            traverse_children: Whether to include subtasks as blocking relationships

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
                issue = self.get_cached_issue(key)
                if issue is None:
                    continue
                    
                all_linked_keys.add(key)

                # Collect blocking dependencies from this issue
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
                        if other_key and (name == "blocks" or outward == "blocks") and other_key not in visited and other_key not in original_keys:
                            to_process.append(other_key)

                    # Check for inward blocking relationships
                    if hasattr(link, "inwardIssue") and link.inwardIssue:
                        other_key = link.inwardIssue.key
                        if other_key and (name == "blocks" or inward == "is blocked by") and other_key not in visited and other_key not in original_keys:
                            to_process.append(other_key)

                # Collect subtasks from this issue
                if traverse_children:
                    subtasks = getattr(issue.fields, "subtasks", []) or []
                    for subtask in subtasks:
                        if hasattr(subtask, "key"):
                            subtask_key = subtask.key
                            if subtask_key and subtask_key not in visited and subtask_key not in original_keys:
                                to_process.append(subtask_key)

        return all_linked_keys