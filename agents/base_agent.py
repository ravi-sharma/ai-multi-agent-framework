"""Base agent interface and abstract class for all agents in the framework."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the AI Agent Framework.
    
    This class defines the standard interface that all agents must implement,
    ensuring consistency and interoperability across different agent types.
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        Initialize the base agent.
        
        Args:
            name: Unique identifier for the agent
            config: Optional configuration dictionary for the agent
        """
        self.name = name
        self.config = config or {}
        self.created_at = datetime.now()
        self.is_enabled = self.config.get('enabled', True)
        
        logger.info(f"Initialized agent '{self.name}' with config keys: {list(self.config.keys())}")
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]):
        """
        Process input data and return agent result.
        
        This is the main entry point for agent execution. All agents must
        implement this method to define their specific processing logic.
        
        Args:
            input_data: Dictionary containing the data to be processed
            
        Returns:
            AgentResult containing the processing outcome and any generated data
            
        Raises:
            AgentProcessingError: If processing fails
        """
        pass
    
    async def process_concurrent(self, input_data: Dict[str, Any], request_id: str = None):
        """
        Process input data with concurrent processing support.
        
        Args:
            input_data: Dictionary containing the data to be processed
            request_id: Optional request ID for tracking
            
        Returns:
            AgentResult containing the processing outcome and any generated data
        """
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # For now, just call process directly - concurrent processor will be added later
        return await self.process(input_data)
    
    @abstractmethod
    def get_workflow_config(self):
        """
        Get the workflow configuration for this agent.
        
        Returns:
            WorkflowConfig object defining how this agent should be orchestrated
        """
        pass
    
    def get_required_llm_capabilities(self) -> List[str]:
        """
        Get the list of LLM capabilities required by this agent.
        
        Returns:
            List of capability strings (e.g., ['text_generation', 'function_calling'])
        """
        return ['text_generation']
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before processing.
        
        Args:
            input_data: Dictionary containing the data to validate
            
        Returns:
            True if input is valid, False otherwise
        """
        return isinstance(input_data, dict)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about this agent.
        
        Returns:
            Dictionary containing agent metadata
        """
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'enabled': self.is_enabled,
            'created_at': self.created_at.isoformat(),
            'required_capabilities': self.get_required_llm_capabilities(),
            'config': self.config
        }
    
    def enable(self):
        """Enable this agent."""
        self.is_enabled = True
        logger.info(f"Agent '{self.name}' enabled")
    
    def disable(self):
        """Disable this agent."""
        self.is_enabled = False
        logger.info(f"Agent '{self.name}' disabled")
    
    def update_config(self, new_config: Dict[str, Any]):
        """
        Update agent configuration.
        
        Args:
            new_config: New configuration dictionary
        """
        self.config.update(new_config)
        logger.info(f"Updated config for agent '{self.name}'")