"""Base memory interface for different storage backends."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class MemoryBase(ABC):
    """Abstract base class for memory storage backends."""
    
    @abstractmethod
    async def store(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Store data with optional TTL.
        
        Args:
            key: Storage key
            data: Data to store
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data by key.
        
        Args:
            key: Storage key
            
        Returns:
            Stored data or None if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete data by key.
        
        Args:
            key: Storage key
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Storage key
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def list_keys(self, pattern: str = "*") -> List[str]:
        """
        List keys matching pattern.
        
        Args:
            pattern: Key pattern (default: all keys)
            
        Returns:
            List of matching keys
        """
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """
        Clear all stored data.
        
        Returns:
            True if successful, False otherwise
        """
        pass