"""
JIRA Cache Module

Provides file-based caching for JIRA issues and search results to improve performance
and enable testing without API access.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import hashlib


class JiraCache:
    """File-based cache for JIRA issues and search results."""
    
    def __init__(self, cache_dir: str = "cache", default_ttl: int = 3600):
        """
        Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default time-to-live in seconds (1 hour by default)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        
        # Separate directories for different cache types
        self.issues_dir = self.cache_dir / "issues"
        self.searches_dir = self.cache_dir / "searches"
        
        self.issues_dir.mkdir(exist_ok=True)
        self.searches_dir.mkdir(exist_ok=True)
    
    def _get_cache_path(self, cache_type: str, key: str) -> Path:
        """Get the cache file path for a given key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        if cache_type == "issue":
            return self.issues_dir / f"{safe_key}.json"
        elif cache_type == "search":
            return self.searches_dir / f"{safe_key}.json"
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")
    
    def _is_expired(self, cache_data: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        if "expires_at" not in cache_data:
            return True
        
        expires_at = datetime.fromisoformat(cache_data["expires_at"])
        return datetime.now() > expires_at
    
    def _create_cache_entry(self, data: Any, ttl: Optional[int] = None) -> Dict[str, Any]:
        """Create a cache entry with expiration time."""
        expires_at = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
        return {
            "data": data,
            "cached_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat()
        }
    
    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached issue data.
        
        Args:
            issue_key: JIRA issue key (e.g., "PROJ-123")
            
        Returns:
            Cached issue data or None if not found/expired
        """
        cache_path = self._get_cache_path("issue", issue_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            if self._is_expired(cache_data):
                # Clean up expired cache file
                try:
                    cache_path.unlink()
                except OSError:
                    pass
                return None
            
            return cache_data["data"]
        except (json.JSONDecodeError, KeyError, OSError):
            # Invalid cache file, remove it
            try:
                cache_path.unlink()
            except OSError:
                pass
            return None
    
    def set_issue(self, issue_key: str, issue_data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        Cache issue data.
        
        Args:
            issue_key: JIRA issue key
            issue_data: Issue data to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        cache_path = self._get_cache_path("issue", issue_key)
        cache_entry = self._create_cache_entry(issue_data, ttl)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2, default=str)
        except OSError as e:
            # Log error but don't fail the request
            print(f"Warning: Failed to write cache for issue {issue_key}: {e}")
    
    def get_search(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get cached search results.
        
        Args:
            query_hash: Hash of the search query parameters
            
        Returns:
            Cached search results or None if not found/expired
        """
        cache_path = self._get_cache_path("search", query_hash)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            if self._is_expired(cache_data):
                # Clean up expired cache file
                try:
                    cache_path.unlink()
                except OSError:
                    pass
                return None
            
            return cache_data["data"]
        except (json.JSONDecodeError, KeyError, OSError):
            # Invalid cache file, remove it
            try:
                cache_path.unlink()
            except OSError:
                pass
            return None
    
    def set_search(self, query_hash: str, search_results: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        Cache search results.
        
        Args:
            query_hash: Hash of the search query parameters
            search_results: Search results to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        cache_path = self._get_cache_path("search", query_hash)
        cache_entry = self._create_cache_entry(search_results, ttl)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2, default=str)
        except OSError as e:
            # Log error but don't fail the request
            print(f"Warning: Failed to write cache for search {query_hash}: {e}")
    
    def create_search_hash(self, jql: str, highlight_jql: Optional[str] = None, 
                          max_results: int = 50, child_as_blocking: bool = False,
                          show_dependency_tree: bool = False) -> str:
        """
        Create a hash for search parameters to use as cache key.
        
        Args:
            jql: Main JQL query
            highlight_jql: Highlight JQL query
            max_results: Maximum results
            child_as_blocking: Show child relationship as blocking
            show_dependency_tree: Show full dependency tree
            
        Returns:
            Hash string for the search parameters
        """
        params = {
            "jql": jql or "",
            "highlight_jql": highlight_jql or "",
            "max_results": max_results,
            "child_as_blocking": child_as_blocking,
            "show_dependency_tree": show_dependency_tree
        }
        params_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(params_str.encode()).hexdigest()
    
    def clear_all(self) -> int:
        """
        Clear all cached data.
        
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        
        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                cache_file.unlink()
                deleted_count += 1
            except OSError:
                pass  # Ignore errors during cleanup
        
        return deleted_count
    
    def clear_expired(self) -> int:
        """
        Clear only expired cache entries.
        
        Returns:
            Number of expired files deleted
        """
        deleted_count = 0
        
        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                if self._is_expired(cache_data):
                    try:
                        cache_file.unlink()
                        deleted_count += 1
                    except OSError:
                        pass
            except (json.JSONDecodeError, KeyError, OSError):
                # Invalid cache file, remove it
                try:
                    cache_file.unlink()
                    deleted_count += 1
                except OSError:
                    pass
        
        return deleted_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "total_issues": 0,
            "total_searches": 0,
            "expired_issues": 0,
            "expired_searches": 0,
            "cache_size_mb": 0
        }
        
        total_size = 0
        
        # Count issues
        for cache_file in self.issues_dir.glob("*.json"):
            try:
                file_size = cache_file.stat().st_size
                stats["total_issues"] += 1
                total_size += file_size
                
                if file_size > 0:  # Only read non-empty files
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    if self._is_expired(cache_data):
                        stats["expired_issues"] += 1
            except (json.JSONDecodeError, KeyError, OSError):
                stats["expired_issues"] += 1
        
        # Count searches
        for cache_file in self.searches_dir.glob("*.json"):
            try:
                file_size = cache_file.stat().st_size
                stats["total_searches"] += 1
                total_size += file_size
                
                if file_size > 0:  # Only read non-empty files
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    if self._is_expired(cache_data):
                        stats["expired_searches"] += 1
            except (json.JSONDecodeError, KeyError, OSError):
                stats["expired_searches"] += 1
        
        stats["cache_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        return stats


# Global cache instance
_cache_instance: Optional[JiraCache] = None


def get_cache() -> JiraCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = JiraCache()
    return _cache_instance