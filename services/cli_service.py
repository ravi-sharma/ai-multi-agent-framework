"""Command-line interface for the agent framework."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class CLIService:
    """Command-line interface for the agent framework."""
    
    def __init__(self, framework_instance=None):
        """
        Initialize CLI service.
        
        Args:
            framework_instance: Instance of the main framework
        """
        self.framework = framework_instance
    
    async def process_file(self, file_path: str, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a file through the framework.
        
        Args:
            file_path: Path to file to process
            agent_name: Optional specific agent to use
            
        Returns:
            Processing result
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Read file content
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Determine file type and create appropriate input data
            input_data = {
                "source": "file",
                "data": {
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "content": content,
                    "file_size": len(content)
                }
            }
            
            if agent_name:
                input_data["requested_agent"] = agent_name
            
            # Process through framework
            if self.framework:
                result = await self.framework.process(input_data)
            else:
                result = await self._mock_process(input_data)
            
            return {
                "success": True,
                "file_path": str(file_path),
                "agent_used": result.get("agent_name", "unknown"),
                "result": result,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return {
                "success": False,
                "file_path": str(file_path) if 'file_path' in locals() else "unknown",
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
    
    async def process_text(self, text: str, source: str = "cli", 
                          agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Process text input through the framework.
        
        Args:
            text: Text to process
            source: Source identifier
            agent_name: Optional specific agent to use
            
        Returns:
            Processing result
        """
        try:
            input_data = {
                "source": source,
                "data": {
                    "text": text,
                    "length": len(text)
                }
            }
            
            if agent_name:
                input_data["requested_agent"] = agent_name
            
            # Process through framework
            if self.framework:
                result = await self.framework.process(input_data)
            else:
                result = await self._mock_process(input_data)
            
            return {
                "success": True,
                "text_length": len(text),
                "agent_used": result.get("agent_name", "unknown"),
                "result": result,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
    
    async def list_agents(self) -> Dict[str, Any]:
        """
        List available agents.
        
        Returns:
            Dictionary containing agent information
        """
        try:
            if self.framework:
                agents = await self.framework.list_agents()
            else:
                agents = self._mock_agents()
            
            return {
                "success": True,
                "agents": agents,
                "count": len(agents),
                "listed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            return {
                "success": False,
                "error": str(e),
                "listed_at": datetime.now().isoformat()
            }
    
    async def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """
        Get information about a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent information
        """
        try:
            if self.framework:
                agent_info = await self.framework.get_agent_info(agent_name)
            else:
                agent_info = self._mock_agent_info(agent_name)
            
            if not agent_info:
                return {
                    "success": False,
                    "error": f"Agent '{agent_name}' not found",
                    "queried_at": datetime.now().isoformat()
                }
            
            return {
                "success": True,
                "agent_name": agent_name,
                "info": agent_info,
                "queried_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting agent info for {agent_name}: {e}")
            return {
                "success": False,
                "agent_name": agent_name,
                "error": str(e),
                "queried_at": datetime.now().isoformat()
            }
    
    async def test_agent(self, agent_name: str, test_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Test an agent with sample data.
        
        Args:
            agent_name: Name of the agent to test
            test_data: Optional test data (uses default if not provided)
            
        Returns:
            Test result
        """
        try:
            if not test_data:
                test_data = self._get_default_test_data(agent_name)
            
            input_data = {
                "source": "test",
                "data": test_data,
                "requested_agent": agent_name
            }
            
            # Process through framework
            if self.framework:
                result = await self.framework.process(input_data)
            else:
                result = await self._mock_process(input_data)
            
            return {
                "success": True,
                "agent_name": agent_name,
                "test_data": test_data,
                "result": result,
                "tested_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error testing agent {agent_name}: {e}")
            return {
                "success": False,
                "agent_name": agent_name,
                "error": str(e),
                "tested_at": datetime.now().isoformat()
            }
    
    async def validate_config(self, config_path: str) -> Dict[str, Any]:
        """
        Validate a configuration file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Validation result
        """
        try:
            config_path = Path(config_path)
            
            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")
            
            # Load and validate config
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() == '.json':
                    config = json.load(f)
                elif config_path.suffix.lower() in ['.yaml', '.yml']:
                    import yaml
                    config = yaml.safe_load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
            
            # Basic validation (can be enhanced)
            validation_errors = []
            
            # Check required sections
            required_sections = ['agents', 'llm_providers']
            for section in required_sections:
                if section not in config:
                    validation_errors.append(f"Missing required section: {section}")
            
            # Validate agents section
            if 'agents' in config:
                for agent_name, agent_config in config['agents'].items():
                    if not isinstance(agent_config, dict):
                        validation_errors.append(f"Agent '{agent_name}' config must be a dictionary")
                    elif 'agent_type' not in agent_config:
                        validation_errors.append(f"Agent '{agent_name}' missing 'agent_type'")
            
            return {
                "success": len(validation_errors) == 0,
                "config_path": str(config_path),
                "validation_errors": validation_errors,
                "config_sections": list(config.keys()) if isinstance(config, dict) else [],
                "validated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validating config {config_path}: {e}")
            return {
                "success": False,
                "config_path": str(config_path) if 'config_path' in locals() else "unknown",
                "error": str(e),
                "validated_at": datetime.now().isoformat()
            }
    
    def _get_default_test_data(self, agent_name: str) -> Dict[str, Any]:
        """Get default test data for an agent."""
        test_data_map = {
            "sales_agent": {
                "email": {
                    "subject": "Interested in your product",
                    "sender": "test@example.com",
                    "body": "Hi, I'm interested in learning more about your product and pricing."
                }
            },
            "default_agent": {
                "message": "This is a test message for the default agent."
            }
        }
        
        return test_data_map.get(agent_name, {"message": "Generic test message"})
    
    async def _mock_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock processing for when framework is not available."""
        return {
            "agent_name": input_data.get("requested_agent", "mock_agent"),
            "success": True,
            "output": {"message": "Mock processing completed"},
            "execution_time": 0.1,
            "processed_at": datetime.now().isoformat()
        }
    
    def _mock_agents(self) -> list:
        """Mock agent list for when framework is not available."""
        return [
            {
                "name": "default_agent",
                "type": "DefaultAgent",
                "enabled": True,
                "description": "Fallback agent for unmatched requests"
            },
            {
                "name": "sales_agent",
                "type": "SalesAgent",
                "enabled": True,
                "description": "Specialized agent for sales inquiries"
            }
        ]
    
    def _mock_agent_info(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Mock agent info for when framework is not available."""
        agents = {
            "default_agent": {
                "name": "default_agent",
                "type": "DefaultAgent",
                "enabled": True,
                "capabilities": ["text_processing", "fallback_handling"],
                "description": "Fallback agent for unmatched requests"
            },
            "sales_agent": {
                "name": "sales_agent",
                "type": "SalesAgent",
                "enabled": True,
                "capabilities": ["email_processing", "sales_analysis", "lead_qualification"],
                "description": "Specialized agent for sales inquiries"
            }
        }
        
        return agents.get(agent_name)