"""State management for workflow and agent persistence."""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from .memory_base import MemoryBase

logger = logging.getLogger(__name__)


class InMemoryStorage(MemoryBase):
    """Simple in-memory storage implementation."""
    
    def __init__(self):
        """Initialize in-memory storage."""
        self._storage: Dict[str, Dict[str, Any]] = {}
    
    async def store(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Store data in memory."""
        try:
            entry = {
                'data': data,
                'stored_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(seconds=ttl) if ttl else None
            }
            self._storage[key] = entry
            return True
        except Exception as e:
            logger.error(f"Error storing data for key {key}: {e}")
            return False
    
    async def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from memory."""
        try:
            if key not in self._storage:
                return None
            
            entry = self._storage[key]
            
            # Check expiration
            if entry['expires_at'] and datetime.now() > entry['expires_at']:
                del self._storage[key]
                return None
            
            return entry['data']
        except Exception as e:
            logger.error(f"Error retrieving data for key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete data from memory."""
        try:
            if key in self._storage:
                del self._storage[key]
            return True
        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory."""
        return key in self._storage
    
    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys in memory."""
        if pattern == "*":
            return list(self._storage.keys())
        
        # Simple pattern matching
        import fnmatch
        return [key for key in self._storage.keys() if fnmatch.fnmatch(key, pattern)]
    
    async def clear(self) -> bool:
        """Clear all data from memory."""
        try:
            self._storage.clear()
            return True
        except Exception as e:
            logger.error(f"Error clearing storage: {e}")
            return False


class FileStorage(MemoryBase):
    """File-based storage implementation."""
    
    def __init__(self, storage_dir: str = "data/memory"):
        """Initialize file storage."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for key."""
        # Replace invalid filename characters
        safe_key = key.replace('/', '_').replace('\\', '_').replace(':', '_')
        return self.storage_dir / f"{safe_key}.json"
    
    async def store(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Store data to file."""
        try:
            entry = {
                'data': data,
                'stored_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=ttl)).isoformat() if ttl else None
            }
            
            file_path = self._get_file_path(key)
            with open(file_path, 'w') as f:
                json.dump(entry, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error storing data to file for key {key}: {e}")
            return False
    
    async def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from file."""
        try:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r') as f:
                entry = json.load(f)
            
            # Check expiration
            if entry['expires_at']:
                expires_at = datetime.fromisoformat(entry['expires_at'])
                if datetime.now() > expires_at:
                    file_path.unlink()  # Delete expired file
                    return None
            
            return entry['data']
        except Exception as e:
            logger.error(f"Error retrieving data from file for key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete data file."""
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Error deleting file for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        file_path = self._get_file_path(key)
        return file_path.exists()
    
    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys from files."""
        try:
            files = list(self.storage_dir.glob("*.json"))
            keys = [f.stem for f in files]
            
            if pattern == "*":
                return keys
            
            import fnmatch
            return [key for key in keys if fnmatch.fnmatch(key, pattern)]
        except Exception as e:
            logger.error(f"Error listing keys: {e}")
            return []
    
    async def clear(self) -> bool:
        """Clear all files."""
        try:
            for file_path in self.storage_dir.glob("*.json"):
                file_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Error clearing files: {e}")
            return False


class StateManager:
    """Manages workflow and agent state persistence."""
    
    def __init__(self, storage_backend: Optional[MemoryBase] = None):
        """
        Initialize state manager.
        
        Args:
            storage_backend: Storage backend to use (defaults to in-memory)
        """
        self.storage = storage_backend or InMemoryStorage()
    
    async def save_workflow_state(self, workflow_id: str, state: Dict[str, Any], 
                                ttl: Optional[int] = None) -> bool:
        """
        Save workflow state.
        
        Args:
            workflow_id: Unique workflow identifier
            state: Workflow state data
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        key = f"workflow:{workflow_id}"
        return await self.storage.store(key, state, ttl)
    
    async def load_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Load workflow state.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            Workflow state data or None if not found
        """
        key = f"workflow:{workflow_id}"
        return await self.storage.retrieve(key)
    
    async def delete_workflow_state(self, workflow_id: str) -> bool:
        """
        Delete workflow state.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            True if successful, False otherwise
        """
        key = f"workflow:{workflow_id}"
        return await self.storage.delete(key)
    
    async def save_agent_state(self, agent_name: str, state: Dict[str, Any],
                             ttl: Optional[int] = None) -> bool:
        """
        Save agent state.
        
        Args:
            agent_name: Agent name
            state: Agent state data
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        key = f"agent:{agent_name}"
        return await self.storage.store(key, state, ttl)
    
    async def load_agent_state(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Load agent state.
        
        Args:
            agent_name: Agent name
            
        Returns:
            Agent state data or None if not found
        """
        key = f"agent:{agent_name}"
        return await self.storage.retrieve(key)
    
    async def save_conversation_history(self, conversation_id: str, 
                                      history: List[Dict[str, Any]],
                                      ttl: Optional[int] = None) -> bool:
        """
        Save conversation history.
        
        Args:
            conversation_id: Unique conversation identifier
            history: List of conversation messages
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        key = f"conversation:{conversation_id}"
        return await self.storage.store(key, {'history': history}, ttl)
    
    async def load_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Load conversation history.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            List of conversation messages
        """
        key = f"conversation:{conversation_id}"
        data = await self.storage.retrieve(key)
        return data.get('history', []) if data else []
    
    async def list_active_workflows(self) -> List[str]:
        """
        List active workflow IDs.
        
        Returns:
            List of workflow IDs
        """
        keys = await self.storage.list_keys("workflow:*")
        return [key.replace("workflow:", "") for key in keys]
    
    async def cleanup_expired_states(self) -> int:
        """
        Clean up expired states (for storage backends that don't auto-expire).
        
        Returns:
            Number of states cleaned up
        """
        # This is handled automatically by the storage backends
        # but can be implemented for manual cleanup if needed
        return 0