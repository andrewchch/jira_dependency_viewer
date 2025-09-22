"""
Unit tests for JIRA object wrappers.

These tests verify that cached JIRA data can be properly deserialized
back into objects that behave like JIRA library objects.
"""

import unittest
from jira_objects import (
    JiraIssueWrapper, 
    JiraIssueFieldsWrapper,
    JiraIssueLinkWrapper,
    JiraSubtaskWrapper,
    create_jira_issue_from_cache
)


class TestJiraObjectWrappers(unittest.TestCase):
    """Test cases for JIRA object wrappers."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_issue_data = {
            "key": "TEST-123",
            "id": "12345",
            "fields": {
                "summary": "Test issue summary",
                "status": {
                    "name": "In Progress",
                    "id": "3"
                },
                "issuetype": {
                    "name": "Story",
                    "id": "10001"
                },
                "customfield_10005": 8,  # Story points
                "customfield_10015": "2024-01-15",  # Start date
                "customfield_10016": "2024-02-15",  # End date
                "issuelinks": [
                    {
                        "type": {
                            "name": "Blocks",
                            "outward": "blocks",
                            "inward": "is blocked by"
                        },
                        "outwardIssue": {
                            "key": "TEST-124",
                            "fields": {"summary": "Blocked issue"}
                        }
                    },
                    {
                        "type": {
                            "name": "Blocks",
                            "outward": "blocks", 
                            "inward": "is blocked by"
                        },
                        "inwardIssue": {
                            "key": "TEST-122",
                            "fields": {"summary": "Blocking issue"}
                        }
                    }
                ],
                "subtasks": [
                    {
                        "key": "TEST-125",
                        "fields": {"summary": "Subtask 1"}
                    },
                    {
                        "key": "TEST-126", 
                        "fields": {"summary": "Subtask 2"}
                    }
                ]
            }
        }
    
    def test_jira_issue_wrapper_basic_attributes(self):
        """Test basic issue attributes are accessible."""
        wrapper = JiraIssueWrapper(self.sample_issue_data)
        
        self.assertEqual(wrapper.key, "TEST-123")
        self.assertEqual(wrapper.id, "12345")
        self.assertIsNotNone(wrapper.fields)
    
    def test_jira_issue_wrapper_fields_access(self):
        """Test that issue fields are properly accessible."""
        wrapper = JiraIssueWrapper(self.sample_issue_data)
        
        # Test direct field access
        self.assertEqual(wrapper.fields.summary, "Test issue summary")
        self.assertEqual(wrapper.fields.customfield_10005, 8)
        self.assertEqual(wrapper.fields.customfield_10015, "2024-01-15")
        self.assertEqual(wrapper.fields.customfield_10016, "2024-02-15")
    
    def test_jira_issue_wrapper_status_access(self):
        """Test that status object is properly accessible."""
        wrapper = JiraIssueWrapper(self.sample_issue_data)
        
        # Test status access pattern used in app.py
        self.assertIsNotNone(wrapper.fields.status)
        self.assertEqual(wrapper.fields.status.name, "In Progress")
        self.assertEqual(wrapper.fields.status.id, "3")
    
    def test_jira_issue_wrapper_issuetype_access(self):
        """Test that issuetype object is properly accessible."""
        wrapper = JiraIssueWrapper(self.sample_issue_data)
        
        self.assertIsNotNone(wrapper.fields.issuetype)
        self.assertEqual(wrapper.fields.issuetype.name, "Story")
        self.assertEqual(wrapper.fields.issuetype.id, "10001")
    
    def test_jira_issue_wrapper_issuelinks_access(self):
        """Test that issue links are properly accessible."""
        wrapper = JiraIssueWrapper(self.sample_issue_data)
        
        # Test that issuelinks is a list
        self.assertIsInstance(wrapper.fields.issuelinks, list)
        self.assertEqual(len(wrapper.fields.issuelinks), 2)
        
        # Test first link (outward)
        first_link = wrapper.fields.issuelinks[0]
        self.assertIsNotNone(first_link.type)
        self.assertEqual(first_link.type.name, "Blocks")
        self.assertEqual(first_link.type.outward, "blocks")
        self.assertEqual(first_link.type.inward, "is blocked by")
        
        # Test outward issue access
        self.assertTrue(hasattr(first_link, "outwardIssue"))
        self.assertEqual(first_link.outwardIssue.key, "TEST-124")
        
        # Test second link (inward)
        second_link = wrapper.fields.issuelinks[1]
        self.assertTrue(hasattr(second_link, "inwardIssue"))
        self.assertEqual(second_link.inwardIssue.key, "TEST-122")
    
    def test_jira_issue_wrapper_subtasks_access(self):
        """Test that subtasks are properly accessible."""
        wrapper = JiraIssueWrapper(self.sample_issue_data)
        
        # Test that subtasks is a list
        self.assertIsInstance(wrapper.fields.subtasks, list)
        self.assertEqual(len(wrapper.fields.subtasks), 2)
        
        # Test subtask access pattern
        first_subtask = wrapper.fields.subtasks[0]
        self.assertTrue(hasattr(first_subtask, "key"))
        self.assertEqual(first_subtask.key, "TEST-125")
    
    def test_create_jira_issue_from_cache_function(self):
        """Test the main factory function."""
        issue = create_jira_issue_from_cache(self.sample_issue_data)
        
        self.assertIsInstance(issue, JiraIssueWrapper)
        self.assertEqual(issue.key, "TEST-123")
        self.assertEqual(issue.fields.summary, "Test issue summary")
        self.assertEqual(issue.fields.status.name, "In Progress")
    
    def test_jira_issue_wrapper_with_empty_data(self):
        """Test wrapper handles empty/missing data gracefully."""
        empty_data = {"key": "EMPTY-1", "fields": {}}
        wrapper = JiraIssueWrapper(empty_data)
        
        self.assertEqual(wrapper.key, "EMPTY-1")
        self.assertIsNotNone(wrapper.fields)
        
        # Test that accessing missing fields doesn't crash
        self.assertIsNone(getattr(wrapper.fields, "summary", None))
    
    def test_jira_issue_wrapper_with_none_fields(self):
        """Test wrapper handles None values gracefully."""
        data_with_nones = {
            "key": "NULL-1",
            "fields": {
                "summary": "Test",
                "status": None,
                "issuelinks": None,
                "subtasks": None
            }
        }
        wrapper = JiraIssueWrapper(data_with_nones)
        
        self.assertEqual(wrapper.key, "NULL-1")
        self.assertEqual(wrapper.fields.summary, "Test")
        self.assertIsNone(wrapper.fields.status)
        self.assertIsNone(wrapper.fields.issuelinks)
        self.assertIsNone(wrapper.fields.subtasks)
    
    def test_jira_issue_fields_wrapper_custom_fields(self):
        """Test handling of custom fields with various data types."""
        fields_data = {
            "customfield_10001": "text value",
            "customfield_10002": 42,
            "customfield_10003": ["item1", "item2"],
            "customfield_10004": {
                "name": "Custom Object",
                "value": "test"
            }
        }
        wrapper = JiraIssueFieldsWrapper(fields_data)
        
        # Test different custom field types
        self.assertEqual(wrapper.customfield_10001, "text value")
        self.assertEqual(wrapper.customfield_10002, 42)
        self.assertEqual(wrapper.customfield_10003, ["item1", "item2"])
        self.assertEqual(wrapper.customfield_10004.name, "Custom Object")
        self.assertEqual(wrapper.customfield_10004.value, "test")
    
    def test_jira_issue_wrapper_str_and_repr(self):
        """Test string representations of wrapper."""
        wrapper = JiraIssueWrapper(self.sample_issue_data)
        
        str_repr = str(wrapper)
        self.assertIn("TEST-123", str_repr)
        
        repr_str = repr(wrapper)
        self.assertIn("TEST-123", repr_str)
        self.assertIn("Test issue summary", repr_str)
    
    def test_compatibility_with_app_usage_patterns(self):
        """Test that the wrapper works with actual usage patterns from app.py."""
        wrapper = JiraIssueWrapper(self.sample_issue_data)
        
        # Test pattern: getattr(fields, "status", None)
        status = getattr(wrapper.fields, "status", None)
        self.assertIsNotNone(status)
        
        # Test pattern: fields.status.name if getattr(fields, "status", None) else None
        status_name = wrapper.fields.status.name if getattr(wrapper.fields, "status", None) else None
        self.assertEqual(status_name, "In Progress")
        
        # Test pattern: getattr(fields, START_DATE_FIELD, None)
        START_DATE_FIELD = "customfield_10015"
        start_date = getattr(wrapper.fields, START_DATE_FIELD, None)
        self.assertEqual(start_date, "2024-01-15")
        
        # Test pattern: getattr(issue.fields, "issuelinks", []) or []
        issuelinks = getattr(wrapper.fields, "issuelinks", []) or []
        self.assertEqual(len(issuelinks), 2)
        
        # Test pattern: hasattr(link, "outwardIssue") and link.outwardIssue
        first_link = issuelinks[0]
        self.assertTrue(hasattr(first_link, "outwardIssue"))
        self.assertIsNotNone(first_link.outwardIssue)
        self.assertEqual(first_link.outwardIssue.key, "TEST-124")


class TestJiraIssueLinkWrapper(unittest.TestCase):
    """Test JIRA issue link wrapper specifically."""
    
    def test_outward_link(self):
        """Test outward link handling."""
        link_data = {
            "type": {"name": "Blocks", "outward": "blocks", "inward": "is blocked by"},
            "outwardIssue": {"key": "OUT-123", "fields": {"summary": "Outward issue"}}
        }
        wrapper = JiraIssueLinkWrapper(link_data)
        
        self.assertEqual(wrapper.type.name, "Blocks")
        self.assertEqual(wrapper.type.outward, "blocks")
        self.assertTrue(hasattr(wrapper, "outwardIssue"))
        self.assertEqual(wrapper.outwardIssue.key, "OUT-123")
    
    def test_inward_link(self):
        """Test inward link handling."""
        link_data = {
            "type": {"name": "Blocks", "outward": "blocks", "inward": "is blocked by"},
            "inwardIssue": {"key": "IN-123", "fields": {"summary": "Inward issue"}}
        }
        wrapper = JiraIssueLinkWrapper(link_data)
        
        self.assertEqual(wrapper.type.name, "Blocks")
        self.assertEqual(wrapper.type.inward, "is blocked by")
        self.assertTrue(hasattr(wrapper, "inwardIssue"))
        self.assertEqual(wrapper.inwardIssue.key, "IN-123")


class TestJiraSubtaskWrapper(unittest.TestCase):
    """Test JIRA subtask wrapper specifically."""
    
    def test_subtask_wrapper(self):
        """Test subtask wrapper functionality."""
        subtask_data = {
            "key": "SUB-123",
            "fields": {"summary": "Subtask summary"}
        }
        wrapper = JiraSubtaskWrapper(subtask_data)
        
        self.assertEqual(wrapper.key, "SUB-123")
        # Note: fields are not wrapped in subtask wrapper as they're not typically accessed
        # If needed, this could be enhanced


if __name__ == "__main__":
    unittest.main()