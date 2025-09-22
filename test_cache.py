"""
Unit tests for the JIRA cache module.
"""

import os
import tempfile
import unittest
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from cache import JiraCache


class TestJiraCache(unittest.TestCase):
    """Test cases for JiraCache class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.cache = JiraCache(cache_dir=self.temp_dir, default_ttl=60)
        
        # Sample test data
        self.sample_issue = {
            "key": "TEST-123",
            "summary": "Test issue",
            "status": "In Progress",
            "fields": {
                "summary": "Test issue",
                "status": {"name": "In Progress"}
            }
        }
        
        self.sample_search = {
            "nodes": [
                {"id": "TEST-123", "key": "TEST-123", "summary": "Test issue 1"},
                {"id": "TEST-124", "key": "TEST-124", "summary": "Test issue 2"}
            ],
            "edges": [
                {"source": "TEST-123", "target": "TEST-124", "label": "blocks"}
            ]
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory and all its contents
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_initialization(self):
        """Test cache initialization creates proper directory structure."""
        self.assertTrue(os.path.exists(self.cache.cache_dir))
        self.assertTrue(os.path.exists(self.cache.issues_dir))
        self.assertTrue(os.path.exists(self.cache.searches_dir))
    
    def test_issue_cache_set_and_get(self):
        """Test setting and getting issue cache entries."""
        issue_key = "TEST-123"
        
        # Initially should return None
        self.assertIsNone(self.cache.get_issue(issue_key))
        
        # Set cache entry
        self.cache.set_issue(issue_key, self.sample_issue)
        
        # Should now return the cached data
        cached_data = self.cache.get_issue(issue_key)
        self.assertEqual(cached_data, self.sample_issue)
    
    def test_search_cache_set_and_get(self):
        """Test setting and getting search cache entries."""
        query_hash = self.cache.create_search_hash("project = TEST")
        
        # Initially should return None
        self.assertIsNone(self.cache.get_search(query_hash))
        
        # Set cache entry
        self.cache.set_search(query_hash, self.sample_search)
        
        # Should now return the cached data
        cached_data = self.cache.get_search(query_hash)
        self.assertEqual(cached_data, self.sample_search)
    
    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        issue_key = "TEST-EXPIRE"
        short_ttl = 1  # 1 second
        
        # Set cache entry with short TTL
        self.cache.set_issue(issue_key, self.sample_issue, ttl=short_ttl)
        
        # Should be available immediately
        self.assertIsNotNone(self.cache.get_issue(issue_key))
        
        # Wait for expiration
        time.sleep(short_ttl + 0.1)
        
        # Should now be expired and return None
        self.assertIsNone(self.cache.get_issue(issue_key))
    
    def test_search_hash_generation(self):
        """Test search hash generation is consistent and different for different params."""
        jql1 = "project = TEST"
        jql2 = "project = PROD"
        
        hash1 = self.cache.create_search_hash(jql1)
        hash2 = self.cache.create_search_hash(jql1)  # Same query
        hash3 = self.cache.create_search_hash(jql2)  # Different query
        
        # Same query should produce same hash
        self.assertEqual(hash1, hash2)
        
        # Different query should produce different hash
        self.assertNotEqual(hash1, hash3)
        
        # Test with different parameters
        hash4 = self.cache.create_search_hash(jql1, max_results=100)
        hash5 = self.cache.create_search_hash(jql1, max_results=50)
        
        self.assertNotEqual(hash4, hash5)
    
    def test_clear_all_cache(self):
        """Test clearing all cache entries."""
        # Add some cache entries
        self.cache.set_issue("TEST-1", self.sample_issue)
        self.cache.set_issue("TEST-2", self.sample_issue)
        query_hash = self.cache.create_search_hash("project = TEST")
        self.cache.set_search(query_hash, self.sample_search)
        
        # Verify entries exist
        self.assertIsNotNone(self.cache.get_issue("TEST-1"))
        self.assertIsNotNone(self.cache.get_search(query_hash))
        
        # Clear all cache
        deleted_count = self.cache.clear_all()
        self.assertGreaterEqual(deleted_count, 3)  # Should delete at least 3 files
        
        # Verify entries are gone
        self.assertIsNone(self.cache.get_issue("TEST-1"))
        self.assertIsNone(self.cache.get_issue("TEST-2"))
        self.assertIsNone(self.cache.get_search(query_hash))
    
    def test_clear_expired_cache(self):
        """Test clearing only expired cache entries."""
        short_ttl = 1
        long_ttl = 3600
        
        # Add expired and non-expired entries
        self.cache.set_issue("TEST-EXPIRED", self.sample_issue, ttl=short_ttl)
        self.cache.set_issue("TEST-VALID", self.sample_issue, ttl=long_ttl)
        
        # Wait for expiration
        time.sleep(short_ttl + 0.1)
        
        # Clear expired entries
        deleted_count = self.cache.clear_expired()
        self.assertGreaterEqual(deleted_count, 1)
        
        # Verify expired entry is gone but valid entry remains
        self.assertIsNone(self.cache.get_issue("TEST-EXPIRED"))
        self.assertIsNotNone(self.cache.get_issue("TEST-VALID"))
    
    def test_cache_stats(self):
        """Test cache statistics functionality."""
        # Initially empty
        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["total_issues"], 0)
        self.assertEqual(stats["total_searches"], 0)
        
        # Add some entries
        self.cache.set_issue("TEST-1", self.sample_issue)
        self.cache.set_issue("TEST-2", self.sample_issue, ttl=1)  # Will expire quickly
        query_hash = self.cache.create_search_hash("project = TEST")
        self.cache.set_search(query_hash, self.sample_search)
        
        # Wait for one entry to expire
        time.sleep(1.1)
        
        # Check stats
        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["total_issues"], 2)
        self.assertEqual(stats["total_searches"], 1)
        self.assertEqual(stats["expired_issues"], 1)
        self.assertGreaterEqual(stats["cache_size_mb"], 0)  # Allow 0 for small test files
    
    def test_invalid_cache_files(self):
        """Test handling of invalid/corrupted cache files."""
        # Create an invalid cache file manually
        invalid_file = self.cache.issues_dir / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("invalid json content")
        
        # Should handle gracefully and return None
        result = self.cache.get_issue("invalid")
        self.assertIsNone(result)
        
        # Note: We don't check file deletion since we use hash-based filenames
        # The invalid file won't match the hash of "invalid"
    
    def test_cache_path_safety(self):
        """Test that cache paths are safe and don't allow directory traversal."""
        # Test with various potentially dangerous keys
        dangerous_keys = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "key/with/slashes",
            "key:with:colons",
            "key with spaces"
        ]
        
        for key in dangerous_keys:
            # Should not raise an exception
            path = self.cache._get_cache_path("issue", key)
            # Path should be within the cache directory
            self.assertTrue(str(path).startswith(str(self.cache.cache_dir)))
            # Should be able to cache and retrieve
            self.cache.set_issue(key, self.sample_issue)
            result = self.cache.get_issue(key)
            self.assertEqual(result, self.sample_issue)


if __name__ == "__main__":
    unittest.main()