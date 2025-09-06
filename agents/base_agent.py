"""Base agent interface and abstract class for all agents in the framework."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import uuid

from utils.common_mixins import AgentMixin


class BaseAgent(AgentMixin, ABC):
    """
    Abstract base class for all agents in the AI Agent Framework.
    
    This class defines the standard interface that all agents must implement,
    ensuring consistency and interoperability across different agent types.
    """
    
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
        info = super().get_agent_info()
        info['required_capabilities'] = self.get_required_llm_capabilities()
        return info