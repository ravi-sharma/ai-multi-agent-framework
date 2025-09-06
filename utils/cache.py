"""Caching utilities for the AI Agent Framework."""

import os
import json
import pickle
import hashlib
import time
from functools import lru_cache, wraps
from typing import Any, Dict, Optional, Callable, Union
from pathlib import Path
from datetime import datetime, timedelta

from .paths import get_cache_path


class CacheManager:
    """Manager for file-based caching with TTL support."""
    
    def __init__(self, cache_dir: Optional[Path] = None, default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files (uses default if None)
            default_ttl: Default time-to-live in seconds
        """
        self.cache_dir = cache_dir or Path(get_cache_path(""))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._memory_cache = {}
    
    def _get_cache_file_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Create a safe filename from the key
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"
    
    def _get_metadata_path(self, key: str) -> Path:
        """Get the metadata file path for a cache key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.meta"
    
    def _is_expired(self, metadata: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        if 'expires_at' not in metadata:
            return False
        
        expires_at = datetime.fromisoformat(metadata['expires_at'])
        return datetime.now() > expires_at
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, use_pickle: bool = True) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
            use_pickle: Whether to use pickle for serialization
            
        Returns:
            True if successful, False otherwise
        """
        try:
            ttl = ttl or self.default_ttl
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            # Store in memory cache
            self._memory_cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.now()
            }
            
            # Store in file cache
            cache_file = self._get_cache_file_path(key)
            metadata_file = self._get_metadata_path(key)
            
            # Write metadata
            metadata = {
                'key': key,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat(),
                'ttl': ttl,
                'use_pickle': use_pickle
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f)
            
            # Write data
            if use_pickle:
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)
            else:
                with open(cache_file, 'w') as f:
                    json.dump(value, f)
            
            return True
            
        except Exception:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            default: Default value if not found or expired
            
        Returns:
            Cached value or default
        """
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if datetime.now() <= entry['expires_at']:
                return entry['value']
            else:
                # Expired, remove from memory cache
                del self._memory_cache[key]
        
        # Check file cache
        try:
            metadata_file = self._get_metadata_path(key)
            cache_file = self._get_cache_file_path(key)
            
            if not metadata_file.exists() or not cache_file.exists():
                return default
            
            # Read metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check if expired
            if self._is_expired(metadata):
                self.delete(key)
                return default
            
            # Read data
            if metadata.get('use_pickle', True):
                with open(cache_file, 'rb') as f:
                    value = pickle.load(f)
            else:
                with open(cache_file, 'r') as f:
                    value = json.load(f)
            
            # Store in memory cache for faster access
            expires_at = datetime.fromisoformat(metadata['expires_at'])
            self._memory_cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.fromisoformat(metadata['created_at'])
            }
            
            return value
            
        except Exception:
            return default
    
    def delete(self, key: str) -> bool:
        """
        Delete a cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from memory cache
            self._memory_cache.pop(key, None)
            
            # Remove files
            cache_file = self._get_cache_file_path(key)
            metadata_file = self._get_metadata_path(key)
            
            cache_file.unlink(missing_ok=True)
            metadata_file.unlink(missing_ok=True)
            
            return True
            
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists and not expired, False otherwise
        """
        return self.get(key, None) is not None
    
    def clear(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear memory cache
            self._memory_cache.clear()
            
            # Clear file cache
            for file_path in self.cache_dir.glob("*.cache"):
                file_path.unlink(missing_ok=True)
            
            for file_path in self.cache_dir.glob("*.meta"):
                file_path.unlink(missing_ok=True)
            
            return True
            
        except Exception:
            return False
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        cleaned_count = 0
        
        try:
            # Clean memory cache
            expired_keys = []
            for key, entry in self._memory_cache.items():
                if datetime.now() > entry['expires_at']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._memory_cache[key]
                cleaned_count += 1
            
            # Clean file cache
            for metadata_file in self.cache_dir.glob("*.meta"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    if self._is_expired(metadata):
                        # Remove both metadata and cache files
                        cache_file = self._get_cache_file_path(metadata['key'])
                        metadata_file.unlink(missing_ok=True)
                        cache_file.unlink(missing_ok=True)
                        cleaned_count += 1
                        
                except Exception:
                    # If we can't read metadata, remove the file
                    metadata_file.unlink(missing_ok=True)
                    cleaned_count += 1
            
        except Exception:
            pass
        
        return cleaned_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            memory_entries = len(self._memory_cache)
            file_entries = len(list(self.cache_dir.glob("*.meta")))
            
            total_size = sum(
                f.stat().st_size 
                for f in self.cache_dir.glob("*") 
                if f.is_file()
            )
            
            return {
                'memory_entries': memory_entries,
                'file_entries': file_entries,
                'total_size_bytes': total_size,
                'cache_dir': str(self.cache_dir)
            }
            
        except Exception:
            return {
                'memory_entries': 0,
                'file_entries': 0,
                'total_size_bytes': 0,
                'cache_dir': str(self.cache_dir)
            }


# Global cache manager instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# Configuration caching utilities
@lru_cache(maxsize=128)
def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a configuration value with LRU caching.
    
    Args:
        key: Configuration key
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    return os.getenv(key, default)


def cached_config(ttl: int = 3600):
    """
    Decorator for caching configuration values.
    
    Args:
        ttl: Time-to-live in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = f"config:{':'.join(key_parts)}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def cached_function(ttl: int = 3600, key_prefix: str = "func"):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Create cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str = None):
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        pattern: Pattern to match (if None, clears all)
    """
    cache = get_cache_manager()
    
    if pattern is None:
        cache.clear()
    else:
        # For now, we don't support pattern matching in file cache
        # This would require iterating through all cache files
        pass


def cache_cleanup():
    """Clean up expired cache entries."""
    cache = get_cache_manager()
    return cache.cleanup_expired()


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    cache = get_cache_manager()
    return cache.get_stats()


# Convenience functions
def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set a value in the cache."""
    return get_cache_manager().set(key, value, ttl)


def cache_get(key: str, default: Any = None) -> Any:
    """Get a value from the cache."""
    return get_cache_manager().get(key, default)


def cache_delete(key: str) -> bool:
    """Delete a cache entry."""
    return get_cache_manager().delete(key)


def cache_exists(key: str) -> bool:
    """Check if a cache key exists."""
    return get_cache_manager().exists(key)
