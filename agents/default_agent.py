"""Simplified default agent implementation."""

from typing import Dict, Any, List
from datetime import datetime

from agents.base_agent import BaseAgent
from models.data_models import AgentResult


class DefaultAgent(BaseAgent):
    """
    Default fallback agent for handling requests that don't match any specific criteria.
    
    This agent provides basic response generation and logging for unmatched requests.
    """
    
    def __init__(self, name: str = "default_agent", config: Dict[str, Any] = None):
        """
        Initialize the default agent.
        
        Args:
            name: Agent name
            config: Agent configuration
        """
        super().__init__(name, config)
        
        # Configuration options for default behavior
        self.response_template = self.get_config_value('response_template', 
            "Thank you for your message. We have received your request and will respond appropriately.")
        self.log_unmatched_requests = self.get_config_value('log_unmatched_requests', True)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process input data with basic fallback handling.
        
        Args:
            input_data: Dictionary containing the data to be processed
            
        Returns:
            AgentResult with basic response and logging
        """
        start_time = datetime.now()
        
        try:
            # Validate input
            if not self.validate_input(input_data):
                return AgentResult(
                    success=False,
                    output={},
                    agent_name=self.name,
                    error_message="Invalid input data for default agent",
                    execution_time=0.0
                )
            
            # Log fallback scenario
            if self.log_unmatched_requests:
                self._log_fallback_scenario(input_data)
            
            # Generate basic response
            response_data = self._generate_response(input_data)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = AgentResult(
                success=True,
                output=response_data,
                agent_name=self.name,
                execution_time=execution_time,
                notes=[
                    "Processed by default fallback agent",
                    f"Request source: {input_data.get('source', 'unknown')}"
                ],
                requires_human_review=True  # Default agent results typically need human review
            )
            
            self.log_info(f"Default agent processed request in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.log_error("Default agent processing failed", error=e)
            return AgentResult(
                success=False,
                output={},
                agent_name=self.name,
                error_message=str(e),
                execution_time=execution_time,
                notes=["Default agent processing failed"]
            )
    
    def _generate_response(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate response for the unmatched request.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Dictionary containing response data
        """
        # Extract basic information about the request
        source = input_data.get('source', 'unknown')
        
        # Start with basic response
        response_data = {
            'agent_type': 'default',
            'response_type': 'fallback',
            'message': self.response_template,
            'source': source,
            'processed_at': datetime.now().isoformat(),
            'requires_human_review': True
        }
        
        return response_data
    
    def _log_fallback_scenario(self, input_data: Dict[str, Any]) -> None:
        """
        Log information about the fallback scenario.
        
        Args:
            input_data: Input data that triggered fallback
        """
        source = input_data.get('source', 'unknown')
        
        # Create log message with relevant details
        log_details = {
            'agent': self.name,
            'source': source,
            'timestamp': datetime.now().isoformat(),
            'data_keys': list(input_data.keys()) if isinstance(input_data, dict) else []
        }
        
        self.log_info("Default agent handling unmatched request", **log_details)
        self.log_warning(f"Unmatched request routed to default agent from {source}")
    
    def get_workflow_config(self):
        """Get the workflow configuration for this agent."""
        return {
            "agent_name": self.name,
            "workflow_type": "simple",
            "max_retries": 1,
            "timeout": 60,
            "retry_delay": 1.0
        }
    
    def get_required_llm_capabilities(self) -> List[str]:
        """Get the list of LLM capabilities required by this agent."""
        return []  # No LLM capabilities required for basic operation
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before processing.
        
        Args:
            input_data: Dictionary containing the data to validate
            
        Returns:
            True if input is valid, False otherwise
        """
        # Default agent is very permissive with input validation
        if not isinstance(input_data, dict):
            return False
        
        # Must have at least some data
        if not input_data:
            return False
        
        return True