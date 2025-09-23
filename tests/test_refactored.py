"""
Unit tests for the refactored JIRA helper and graph builder classes.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from jira_helper import JiraHelper
from graph_builder import GraphBuilder


class TestJiraHelper(unittest.TestCase):
    """Test cases for JiraHelper class."""

    def setUp(self):
        """Set up test fixtures."""
        self.jira_helper = JiraHelper(
            jira_server="https://test.atlassian.net",
            jira_email="test@example.com", 
            jira_api_token="test_token",
            jira_fields="summary,status,issuelinks"
        )

    @patch('jira_helper.JIRA')
    def test_get_client(self, mock_jira):
        """Test JIRA client initialization."""
        mock_client = Mock()
        mock_jira.return_value = mock_client
        
        # First call should create client
        client1 = self.jira_helper.get_client()
        self.assertEqual(client1, mock_client)
        
        # Second call should return same client (lazy initialization)
        client2 = self.jira_helper.get_client()
        self.assertEqual(client1, client2)
        
        # JIRA constructor should be called only once
        mock_jira.assert_called_once()

    @patch('jira_helper.get_cache')
    @patch.object(JiraHelper, 'get_client')
    def test_get_cached_issue_cache_hit(self, mock_get_client, mock_get_cache):
        """Test getting issue from cache (cache hit)."""
        # Setup mocks
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Mock cache hit
        mock_issue_data = {"key": "TEST-123", "fields": {"summary": "Test issue"}}
        mock_cache.get_issue.return_value = mock_issue_data
        
        # Test cache hit
        result = self.jira_helper.get_cached_issue("TEST-123")
        
        # Verify cache was checked
        mock_cache.get_issue.assert_called_once_with("TEST-123")
        # API should not be called on cache hit
        mock_client.issue.assert_not_called()

    @patch('jira_helper.get_cache')
    @patch.object(JiraHelper, 'get_client')
    def test_get_cached_issue_cache_miss(self, mock_get_client, mock_get_cache):
        """Test getting issue from API (cache miss)."""
        # Setup mocks
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Mock cache miss
        mock_cache.get_issue.return_value = None
        
        # Mock API response
        mock_issue = Mock()
        mock_issue.raw = {"key": "TEST-123", "fields": {"summary": "Test issue"}}
        mock_client.issue.return_value = mock_issue
        
        # Test cache miss
        result = self.jira_helper.get_cached_issue("TEST-123")
        
        # Verify cache was checked
        mock_cache.get_issue.assert_called_once_with("TEST-123")
        # API should be called on cache miss
        mock_client.issue.assert_called_once_with("TEST-123", fields="summary,status,issuelinks")
        # Result should be cached
        mock_cache.set_issue.assert_called_once_with("TEST-123", mock_issue.raw)

    @patch.object(JiraHelper, 'get_client')
    def test_search_issues_with_cache(self, mock_get_client):
        """Test searching issues with caching."""
        # Setup mock client
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Mock search results
        mock_issues = [Mock(), Mock()]
        mock_client.enhanced_search_issues.return_value = mock_issues
        
        # Test search
        result = self.jira_helper.search_issues_with_cache("project = TEST", max_results=2)
        
        # Verify API call
        mock_client.enhanced_search_issues.assert_called_once_with(
            jql_str="project = TEST",
            maxResults=2,
            fields="summary,status,issuelinks",
            nextPageToken=None
        )
        self.assertEqual(result, mock_issues)


class TestGraphBuilder(unittest.TestCase):
    """Test cases for GraphBuilder class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_jira_helper = Mock()
        self.graph_builder = GraphBuilder(
            jira_helper=self.mock_jira_helper,
            jira_server="https://test.atlassian.net",
            start_date_field="customfield_10015",
            end_date_field="customfield_10016",
            story_points_field="customfield_10005"
        )

    def test_build_graph_data_basic(self):
        """Test basic graph data building."""
        # Create mock issues
        mock_issue = Mock()
        mock_issue.key = "TEST-123"
        mock_issue.fields = Mock()
        mock_issue.fields.summary = "Test issue"
        mock_issue.fields.status = Mock()
        mock_issue.fields.status.name = "In Progress"
        setattr(mock_issue.fields, "customfield_10015", "2024-01-01")
        setattr(mock_issue.fields, "customfield_10016", "2024-01-31")
        setattr(mock_issue.fields, "customfield_10005", 5)
        setattr(mock_issue.fields, "issuelinks", [])
        
        fetched_issues = [mock_issue]
        highlighted_keys = set()
        
        # Mock helper methods
        self.mock_jira_helper.fetch_dependency_tree.return_value = set()
        
        # Test graph building
        result = self.graph_builder.build_graph_data(
            fetched_issues, highlighted_keys, False, False
        )
        
        # Verify result structure
        self.assertIn("nodes", result)
        self.assertIn("edges", result)
        self.assertEqual(len(result["nodes"]), 1)
        
        # Verify node data
        node = result["nodes"][0]
        self.assertEqual(node["key"], "TEST-123")
        self.assertEqual(node["summary"], "Test issue")
        self.assertEqual(node["status"], "In Progress")
        self.assertTrue(node["isOriginal"])
        self.assertFalse(node["isHighlighted"])

    def test_build_graph_data_with_highlighting(self):
        """Test graph data building with highlighted issues."""
        # Create mock issue
        mock_issue = Mock()
        mock_issue.key = "TEST-123"
        mock_issue.fields = Mock()
        mock_issue.fields.summary = "Test issue"
        mock_issue.fields.status = Mock()
        mock_issue.fields.status.name = "In Progress"
        setattr(mock_issue.fields, "customfield_10015", None)
        setattr(mock_issue.fields, "customfield_10016", None)
        setattr(mock_issue.fields, "customfield_10005", None)
        setattr(mock_issue.fields, "issuelinks", [])
        
        fetched_issues = [mock_issue]
        highlighted_keys = {"TEST-123"}  # Highlight this issue
        
        # Mock helper methods
        self.mock_jira_helper.fetch_dependency_tree.return_value = set()
        
        # Test graph building
        result = self.graph_builder.build_graph_data(
            fetched_issues, highlighted_keys, False, False
        )
        
        # Verify highlighting
        node = result["nodes"][0]
        self.assertTrue(node["isHighlighted"])


if __name__ == "__main__":
    unittest.main()