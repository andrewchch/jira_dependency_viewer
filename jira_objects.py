"""
JIRA Object Wrappers

This module provides wrapper classes that convert cached JSON data back into
objects that behave like the JIRA library's objects. This allows cached data
to be used seamlessly with existing code that expects JIRA library objects.
"""

from typing import Dict, Any, List, Optional


class JiraFieldWrapper:
    """Wrapper for JIRA field objects that converts dict data to attribute access."""
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize wrapper with field data."""
        self._data = data or {}
        
        # Set attributes for direct access
        for key, value in self._data.items():
            if isinstance(value, dict):
                # Convert nested dicts to wrapper objects for attribute access
                setattr(self, key, type('obj', (object,), value)())
            elif isinstance(value, list):
                # Handle lists of objects (like issuelinks, subtasks)
                setattr(self, key, [
                    type('obj', (object,), item)() if isinstance(item, dict) else item
                    for item in value
                ])
            else:
                setattr(self, key, value)


class JiraIssueLinkWrapper:
    """Wrapper for JIRA issue link objects."""
    
    def __init__(self, link_data: Dict[str, Any]):
        """Initialize wrapper with link data."""
        self._data = link_data or {}
        
        # Handle link type
        if 'type' in link_data:
            self.type = type('obj', (object,), link_data['type'])()
        
        # Handle outward and inward issues
        if 'outwardIssue' in link_data:
            self.outwardIssue = type('obj', (object,), link_data['outwardIssue'])()
        
        if 'inwardIssue' in link_data:
            self.inwardIssue = type('obj', (object,), link_data['inwardIssue'])()


class JiraSubtaskWrapper:
    """Wrapper for JIRA subtask objects."""
    
    def __init__(self, subtask_data: Dict[str, Any]):
        """Initialize wrapper with subtask data."""
        self._data = subtask_data or {}
        
        # Set basic attributes
        for key, value in self._data.items():
            setattr(self, key, value)


class JiraIssueFieldsWrapper:
    """Wrapper for JIRA issue fields that handles nested structures properly."""
    
    def __init__(self, fields_data: Dict[str, Any]):
        """Initialize wrapper with fields data."""
        self._data = fields_data or {}
        
        # Handle standard fields with special processing
        for key, value in self._data.items():
            if key == 'status' and isinstance(value, dict):
                # Status object with name attribute
                self.status = type('obj', (object,), value)()
            elif key == 'issuetype' and isinstance(value, dict):
                # Issue type object with name attribute
                self.issuetype = type('obj', (object,), value)()
            elif key == 'issuelinks' and isinstance(value, list):
                # Issue links - convert to wrapper objects
                self.issuelinks = [JiraIssueLinkWrapper(link) for link in value]
            elif key == 'subtasks' and isinstance(value, list):
                # Subtasks - convert to wrapper objects
                self.subtasks = [JiraSubtaskWrapper(subtask) for subtask in value]
            elif isinstance(value, dict):
                # Other nested objects
                setattr(self, key, type('obj', (object,), value)())
            elif isinstance(value, list):
                # Lists of simple objects
                setattr(self, key, [
                    type('obj', (object,), item)() if isinstance(item, dict) else item
                    for item in value
                ])
            else:
                # Simple values
                setattr(self, key, value)


class JiraIssueWrapper:
    """
    Wrapper that converts cached JIRA issue JSON data back into an object
    that behaves like a JIRA library Issue object.
    
    This allows cached data to be used seamlessly with existing code
    that expects JIRA library objects.
    """
    
    def __init__(self, issue_data: Dict[str, Any]):
        """
        Initialize wrapper with cached issue data.
        
        Args:
            issue_data: Dictionary containing the cached JIRA issue data
        """
        self._data = issue_data or {}
        
        # Set basic attributes
        self.key = self._data.get('key', '')
        self.id = self._data.get('id', self.key)
        
        # Handle fields - this is the most important part
        fields_data = self._data.get('fields', {})
        self.fields = JiraIssueFieldsWrapper(fields_data)
        
        # Set any other top-level attributes
        for key, value in self._data.items():
            if key not in ['key', 'id', 'fields']:
                setattr(self, key, value)
    
    def __getattr__(self, name: str) -> Any:
        """
        Fallback attribute access for any missing attributes.
        This ensures compatibility with various access patterns.
        """
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __str__(self) -> str:
        """String representation."""
        return f"JiraIssueWrapper({self.key})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"JiraIssueWrapper(key='{self.key}', summary='{getattr(self.fields, 'summary', 'N/A')}')"


def create_jira_issue_from_cache(issue_data: Dict[str, Any]) -> JiraIssueWrapper:
    """
    Create a JIRA issue wrapper from cached data.
    
    This is the main function to use when converting cached JSON data
    back into a JIRA-compatible object.
    
    Args:
        issue_data: Dictionary containing the cached JIRA issue data
        
    Returns:
        JiraIssueWrapper object that behaves like a JIRA library Issue
    """
    return JiraIssueWrapper(issue_data)