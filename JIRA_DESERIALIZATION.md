# JIRA Issue Deserialization

This document explains how cached JIRA issue data is deserialized back into objects that behave like JIRA library objects.

## Problem

In PR #30, caching was implemented for JIRA issue details by storing the raw JSON from the JIRA API response (`issue.raw`). However, when retrieving this cached data via `cache.py:get_issue()`, the application needs to deserialize the JSON back into an object that has the same interface as the JIRA library's `Issue` objects.

## Solution

The `jira_objects.py` module provides wrapper classes that convert cached JSON data back into objects with the same attribute access patterns as JIRA library objects.

### Key Components

#### `JiraIssueWrapper`
Main wrapper class that recreates the full JIRA issue object interface:
- `issue.key` - Issue key (e.g., "PROJ-123")
- `issue.fields` - Fields object with all issue data
- `issue.id` - Issue ID

#### `JiraIssueFieldsWrapper`
Handles the complex `fields` object with all nested structures:
- `fields.summary` - Issue summary
- `fields.status.name` - Status name
- `fields.issuetype.name` - Issue type name
- `fields.issuelinks` - Array of issue link objects
- `fields.subtasks` - Array of subtask objects
- Custom fields (e.g., `fields.customfield_10005`)

#### `JiraIssueLinkWrapper`
Specialized wrapper for issue link objects:
- `link.type.name` - Link type name (e.g., "Blocks")
- `link.type.outward` - Outward relationship name (e.g., "blocks")
- `link.type.inward` - Inward relationship name (e.g., "is blocked by")
- `link.outwardIssue.key` - Key of outward linked issue
- `link.inwardIssue.key` - Key of inward linked issue

#### `JiraSubtaskWrapper`
Wrapper for subtask objects:
- `subtask.key` - Subtask key

### Usage

```python
from cache import get_cache
from jira_objects import create_jira_issue_from_cache

# Get cached issue data
cache = get_cache()
cached_data = cache.get_issue("PROJ-123")

# Convert to JIRA-compatible object
if cached_data:
    jira_issue = create_jira_issue_from_cache(cached_data)
    
    # Now you can use it like a normal JIRA issue object
    print(jira_issue.key)
    print(jira_issue.fields.summary)
    print(jira_issue.fields.status.name)
    
    # Access custom fields
    story_points = getattr(jira_issue.fields, "customfield_10005", None)
    
    # Iterate through issue links
    for link in jira_issue.fields.issuelinks or []:
        if hasattr(link, "outwardIssue") and link.outwardIssue:
            print(f"Blocks: {link.outwardIssue.key}")
```

### Integration with App

The `get_cached_issue()` function in `app.py` now automatically converts cached data using this wrapper system:

```python
def get_cached_issue(issue_key: str, fields: str = JIRA_FIELDS):
    cache = get_cache()
    cached_issue = cache.get_issue(issue_key)
    if cached_issue is not None:
        return cached_issue  # Returns raw JSON for caching
    # ... fetch from API if not cached
```

When used in the dependency tree traversal, the raw JSON is converted to wrapper objects:

```python
issue_data = get_cached_issue(linked_key, JIRA_FIELDS)
if issue_data is not None:
    jira_issue = create_jira_issue_from_cache(issue_data)
    linked_issues.append(jira_issue)
```

### Compatibility

The wrapper objects are designed to be 100% compatible with existing code that expects JIRA library objects. All access patterns used throughout the codebase continue to work:

- `issue.fields.status.name if getattr(issue.fields, "status", None) else None`
- `getattr(issue.fields, START_DATE_FIELD, None)`
- `getattr(issue.fields, "issuelinks", []) or []`
- `hasattr(link, "outwardIssue") and link.outwardIssue`

### Error Handling

The wrappers gracefully handle missing or malformed data:
- Missing fields return `None` when accessed with `getattr()`
- Empty arrays are properly handled
- Nested objects with missing data don't cause crashes
- Invalid or corrupted cache data is handled gracefully

### Testing

Comprehensive tests in `test_jira_objects.py` verify:
- All access patterns used in the application
- Edge cases with missing/None data
- Complex nested structures
- Compatibility with dependency tree traversal
- Custom field access patterns