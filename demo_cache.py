#!/usr/bin/env python3
"""
Demo script showing how to use the JIRA cache for functional testing.

This script demonstrates how to populate the cache with test data
that can be used for testing the application without needing access
to a live JIRA instance.
"""

import json
from cache import get_cache

def create_demo_data():
    """Create sample JIRA data for demonstration/testing purposes."""
    cache = get_cache()
    
    # Sample issues that might be returned from a JIRA search
    issues = [
        {
            "key": "DEMO-001",
            "fields": {
                "summary": "Implement user authentication system",
                "status": {"name": "In Progress"},
                "issuetype": {"name": "Story"},
                "customfield_10005": 8,  # Story points
                "customfield_10015": "2024-01-15",  # Start date
                "customfield_10016": "2024-02-15",  # End date
                "issuelinks": [
                    {
                        "type": {"name": "Blocks", "outward": "blocks", "inward": "is blocked by"},
                        "outwardIssue": {"key": "DEMO-002"}
                    }
                ]
            }
        },
        {
            "key": "DEMO-002", 
            "fields": {
                "summary": "Design user interface mockups",
                "status": {"name": "To Do"},
                "issuetype": {"name": "Task"},
                "customfield_10005": 5,
                "customfield_10015": "2024-02-01",
                "customfield_10016": "2024-02-28",
                "issuelinks": [
                    {
                        "type": {"name": "Blocks", "outward": "blocks", "inward": "is blocked by"},
                        "inwardIssue": {"key": "DEMO-001"}
                    }
                ]
            }
        },
        {
            "key": "DEMO-003",
            "fields": {
                "summary": "Set up CI/CD pipeline",
                "status": {"name": "Done"},
                "issuetype": {"name": "Epic"},
                "customfield_10005": 13,
                "customfield_10015": "2024-01-01",
                "customfield_10016": "2024-01-31",
                "issuelinks": []
            }
        }
    ]
    
    # Cache individual issues
    for issue in issues:
        cache.set_issue(issue["key"], issue)
        print(f"Cached issue: {issue['key']} - {issue['fields']['summary']}")
    
    # Cache a search result
    search_result = {
        "nodes": [
            {
                "id": issue["key"],
                "key": issue["key"], 
                "summary": issue["fields"]["summary"],
                "status": issue["fields"]["status"]["name"],
                "start": issue["fields"].get("customfield_10015", "-"),
                "end": issue["fields"].get("customfield_10016", "-"),
                "story_points": issue["fields"].get("customfield_10005"),
                "url": f"https://demo.atlassian.net/browse/{issue['key']}",
                "isOriginal": True,
                "isHighlighted": False
            }
            for issue in issues
        ],
        "edges": [
            {"source": "DEMO-001", "target": "DEMO-002", "label": "blocks"}
        ]
    }
    
    # Cache search with a common query
    search_hash = cache.create_search_hash("project = DEMO")
    cache.set_search(search_hash, search_result)
    print(f"Cached search result for 'project = DEMO' query")
    
    # Cache another search for "In Progress" status
    in_progress_result = {
        "nodes": [search_result["nodes"][0]],  # Only DEMO-001 is "In Progress"
        "edges": []
    }
    status_search_hash = cache.create_search_hash('status = "In Progress"')
    cache.set_search(status_search_hash, in_progress_result)
    print(f"Cached search result for status = 'In Progress' query")
    
    return len(issues)

def show_cache_stats():
    """Display current cache statistics."""
    cache = get_cache()
    stats = cache.get_cache_stats()
    
    print("\n--- Cache Statistics ---")
    print(f"Total issues cached: {stats['total_issues']}")
    print(f"Total searches cached: {stats['total_searches']}")
    print(f"Expired issues: {stats['expired_issues']}")
    print(f"Expired searches: {stats['expired_searches']}")
    print(f"Cache size: {stats['cache_size_mb']} MB")

def demonstrate_cache_lookup():
    """Demonstrate how to look up cached data."""
    cache = get_cache()
    
    print("\n--- Cache Lookup Demo ---")
    
    # Look up a specific issue
    issue = cache.get_issue("DEMO-001")
    if issue:
        print(f"Found cached issue DEMO-001: {issue['fields']['summary']}")
    else:
        print("Issue DEMO-001 not found in cache")
    
    # Look up a search result
    search_hash = cache.create_search_hash("project = DEMO")
    search_result = cache.get_search(search_hash)
    if search_result:
        print(f"Found cached search result with {len(search_result['nodes'])} nodes")
    else:
        print("Search result not found in cache")

if __name__ == "__main__":
    print("JIRA Cache Demo Script")
    print("=" * 50)
    
    # Create demo data
    num_issues = create_demo_data()
    print(f"\nCreated {num_issues} demo issues")
    
    # Show stats
    show_cache_stats()
    
    # Demonstrate lookup
    demonstrate_cache_lookup()
    
    print("\n--- How to use this for testing ---")
    print("1. Run this script to populate cache with test data")
    print("2. Start the app: python app.py")
    print("3. Search for 'project = DEMO' - should return cached results instantly")
    print("4. Individual issue lookups will also use cached data")
    print("5. Use 'Clear Cache' button to reset and test with live API")
    
    print("\nDemo complete! Cache is now populated with test data.")