"""Unit tests for base agent interface and agent registry."""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List
from datetime import datetime

from agents.base_agent import BaseAgent
from utils.agent_registry import (
    AgentRegistry, 
    get_global_registry, 
    set_global_registry,
    AgentRegistrationError,
    AgentNotFoundError
)
from models.data_models import AgentResult
from models.config_models import WorkflowConfig, AgentConfig


class MockAgent(BaseAgent):
    """Mock agent implementation for testing."""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.process_called = False
        self.process_input = None
        self.process_result = AgentResult(
            success=True,
            output={"message": "Mock processing complete"},
            agent_name=name
        )
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Mock process implementation."""
        self.process_called = True
        self.process_input = input_data
        return self.process_result
    
    def get_workflow_config(self) -> WorkflowConfig:
        """Mock workflow config."""
        return WorkflowConfig(
            agent_name=self.name,
            workflow_steps=["step1", "step2"],
            max_retries=3,
            timeout=30
        )


class FailingAgent(BaseAgent):
    """Agent that fails for testing error scenarios."""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Always fails."""
        raise Exception("Mock processing error")
    
    def get_workflow_config(self) -> WorkflowConfig:
        """Fails to get workflow config."""
        raise Exception("Mock workflow config error")


class TestBaseAgent:
    """Test cases for BaseAgent abstract class."""
    
    def test_base_agent_initialization(self):
        """Test BaseAgent initialization."""
        config = {"param1": "value1"}
        agent = MockAgent("test_agent", config)
        
        assert agent.name == "test_agent"
        assert agent.config == config
        assert isinstance(agent, BaseAgent)
    
    def test_base_agent_initialization_no_config(self):
        """Test BaseAgent initialization without config."""
        agent = MockAgent("test_agent")
        
        assert agent.name == "test_agent"
        assert agent.config == {}
    
    @pytest.mark.asyncio
    async def test_agent_process(self):
        """Test agent process method."""
        agent = MockAgent("test_agent")
        input_data = {"key": "value"}
        
        result = await agent.process(input_data)
        
        assert agent.process_called
        assert agent.process_input == input_data
        assert isinstance(result, AgentResult)
        assert result.success
        assert result.agent_name == "test_agent"
    
    def test_get_workflow_config(self):
        """Test get_workflow_config method."""
        agent = MockAgent("test_agent")
        
        config = agent.get_workflow_config()
        
        assert isinstance(config, WorkflowConfig)
        assert config.agent_name == "test_agent"
        assert config.workflow_steps == ["step1", "step2"]
        assert config.max_retries == 3
        assert config.timeout == 30
    
    def test_get_required_llm_capabilities_default(self):
        """Test default LLM capabilities."""
        agent = MockAgent("test_agent")
        
        capabilities = agent.get_required_llm_capabilities()
        
        assert capabilities == ['text_generation']
    
    def test_validate_input_valid(self):
        """Test input validation with valid data."""
        agent = MockAgent("test_agent")
        input_data = {"key": "value"}
        
        is_valid = agent.validate_input(input_data)
        
        assert is_valid
    
    def test_validate_input_invalid(self):
        """Test input validation with invalid data."""
        agent = MockAgent("test_agent")
        
        is_valid = agent.validate_input("not a dict")
        
        assert not is_valid
    
    def test_get_agent_info(self):
        """Test get_agent_info method."""
        config = {"param1": "value1"}
        agent = MockAgent("test_agent", config)
        
        info = agent.get_agent_info()
        
        assert info['name'] == "test_agent"
        assert info['type'] == "MockAgent"
        assert info['required_capabilities'] == ['text_generation']
        assert info['config'] == config


class TestAgentRegistry:
    """Test cases for AgentRegistry."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = AgentRegistry()
        self.mock_agent = MockAgent("test_agent")
        self.agent_config = AgentConfig(
            name="test_agent",
            agent_type="MockAgent",
            enabled=True
        )
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = AgentRegistry()
        
        assert len(registry.list_agents()) == 0
        assert len(registry.list_agent_types()) == 0
    
    def test_register_agent(self):
        """Test agent registration."""
        self.registry.register_agent(self.mock_agent, self.agent_config)
        
        assert self.registry.has_agent("test_agent")
        assert "test_agent" in self.registry.list_agents()
        
        retrieved_agent = self.registry.get_agent("test_agent")
        assert retrieved_agent is self.mock_agent
    
    def test_register_agent_without_config(self):
        """Test agent registration without config."""
        self.registry.register_agent(self.mock_agent)
        
        assert self.registry.has_agent("test_agent")
        assert self.registry.get_agent_config("test_agent") is None
    
    def test_register_agent_invalid_type(self):
        """Test registration with invalid agent type."""
        with pytest.raises(AgentRegistrationError, match="must be an instance of BaseAgent"):
            self.registry.register_agent("not an agent")
    
    def test_register_agent_empty_name(self):
        """Test registration with empty agent name."""
        agent = MockAgent("")
        
        with pytest.raises(AgentRegistrationError, match="Agent name cannot be empty"):
            self.registry.register_agent(agent)
    
    def test_register_agent_invalid_config(self):
        """Test registration with invalid config."""
        invalid_config = AgentConfig(name="", agent_type="MockAgent")
        
        with pytest.raises(AgentRegistrationError, match="Invalid agent config"):
            self.registry.register_agent(self.mock_agent, invalid_config)
    
    def test_register_agent_type(self):
        """Test agent type registration."""
        self.registry.register_agent_type(MockAgent, "mock_agent")
        
        assert self.registry.has_agent_type("mock_agent")
        assert "mock_agent" in self.registry.list_agent_types()
    
    def test_register_agent_type_invalid(self):
        """Test registration with invalid agent type."""
        with pytest.raises(AgentRegistrationError, match="must be a subclass of BaseAgent"):
            self.registry.register_agent_type(str, "invalid_type")
    
    def test_register_agent_type_empty_name(self):
        """Test agent type registration with empty name."""
        with pytest.raises(AgentRegistrationError, match="Agent type name cannot be empty"):
            self.registry.register_agent_type(MockAgent, "")
    
    def test_create_agent(self):
        """Test agent creation from registered type."""
        self.registry.register_agent_type(MockAgent, "mock_agent")
        
        agent = self.registry.create_agent("mock_agent", "created_agent", {"param": "value"})
        
        assert isinstance(agent, MockAgent)
        assert agent.name == "created_agent"
        assert agent.config == {"param": "value"}
    
    def test_create_agent_unregistered_type(self):
        """Test agent creation with unregistered type."""
        with pytest.raises(AgentNotFoundError, match="Agent type 'unknown' not registered"):
            self.registry.create_agent("unknown", "test_agent")
    
    def test_create_agent_creation_failure(self):
        """Test agent creation failure."""
        # Mock a failing agent class
        with patch.object(MockAgent, '__init__', side_effect=Exception("Creation failed")):
            self.registry.register_agent_type(MockAgent, "mock_agent")
            
            with pytest.raises(AgentRegistrationError, match="Failed to create agent"):
                self.registry.create_agent("mock_agent", "test_agent")
    
    def test_get_agent(self):
        """Test getting registered agent."""
        self.registry.register_agent(self.mock_agent)
        
        retrieved_agent = self.registry.get_agent("test_agent")
        
        assert retrieved_agent is self.mock_agent
    
    def test_get_agent_not_found(self):
        """Test getting non-existent agent."""
        with pytest.raises(AgentNotFoundError, match="Agent 'unknown' not found"):
            self.registry.get_agent("unknown")
    
    def test_get_agent_config(self):
        """Test getting agent configuration."""
        self.registry.register_agent(self.mock_agent, self.agent_config)
        
        config = self.registry.get_agent_config("test_agent")
        
        assert config is self.agent_config
    
    def test_get_agent_config_no_config(self):
        """Test getting config for agent without config."""
        self.registry.register_agent(self.mock_agent)
        
        config = self.registry.get_agent_config("test_agent")
        
        assert config is None
    
    def test_has_agent(self):
        """Test checking agent existence."""
        assert not self.registry.has_agent("test_agent")
        
        self.registry.register_agent(self.mock_agent)
        
        assert self.registry.has_agent("test_agent")
    
    def test_has_agent_type(self):
        """Test checking agent type existence."""
        assert not self.registry.has_agent_type("mock_agent")
        
        self.registry.register_agent_type(MockAgent, "mock_agent")
        
        assert self.registry.has_agent_type("mock_agent")
    
    def test_unregister_agent(self):
        """Test agent unregistration."""
        self.registry.register_agent(self.mock_agent, self.agent_config)
        
        result = self.registry.unregister_agent("test_agent")
        
        assert result
        assert not self.registry.has_agent("test_agent")
        assert self.registry.get_agent_config("test_agent") is None
    
    def test_unregister_agent_not_found(self):
        """Test unregistering non-existent agent."""
        result = self.registry.unregister_agent("unknown")
        
        assert not result
    
    def test_unregister_agent_type(self):
        """Test agent type unregistration."""
        self.registry.register_agent_type(MockAgent, "mock_agent")
        
        result = self.registry.unregister_agent_type("mock_agent")
        
        assert result
        assert not self.registry.has_agent_type("mock_agent")
    
    def test_unregister_agent_type_not_found(self):
        """Test unregistering non-existent agent type."""
        result = self.registry.unregister_agent_type("unknown")
        
        assert not result
    
    def test_list_agents(self):
        """Test listing registered agents."""
        agent1 = MockAgent("agent1")
        agent2 = MockAgent("agent2")
        
        self.registry.register_agent(agent1)
        self.registry.register_agent(agent2)
        
        agents = self.registry.list_agents()
        
        assert set(agents) == {"agent1", "agent2"}
    
    def test_list_agent_types(self):
        """Test listing registered agent types."""
        self.registry.register_agent_type(MockAgent, "mock_agent")
        self.registry.register_agent_type(FailingAgent, "failing_agent")
        
        types = self.registry.list_agent_types()
        
        assert set(types) == {"mock_agent", "failing_agent"}
    
    def test_get_agent_info(self):
        """Test getting agent information."""
        self.registry.register_agent(self.mock_agent, self.agent_config)
        
        info = self.registry.get_agent_info("test_agent")
        
        assert info['name'] == "test_agent"
        assert info['type'] == "MockAgent"
        assert info['registered']
        assert info['has_config']
        assert 'config_summary' in info
        assert info['config_summary']['enabled']
    
    def test_get_agent_info_no_config(self):
        """Test getting agent info without config."""
        self.registry.register_agent(self.mock_agent)
        
        info = self.registry.get_agent_info("test_agent")
        
        assert info['registered']
        assert not info['has_config']
        assert 'config_summary' not in info
    
    def test_get_agent_info_not_found(self):
        """Test getting info for non-existent agent."""
        with pytest.raises(AgentNotFoundError):
            self.registry.get_agent_info("unknown")
    
    def test_get_all_agent_info(self):
        """Test getting all agent information."""
        agent1 = MockAgent("agent1")
        agent2 = MockAgent("agent2")
        
        self.registry.register_agent(agent1)
        self.registry.register_agent(agent2)
        
        all_info = self.registry.get_all_agent_info()
        
        assert len(all_info) == 2
        assert "agent1" in all_info
        assert "agent2" in all_info
        assert all_info["agent1"]['name'] == "agent1"
        assert all_info["agent2"]['name'] == "agent2"
    
    def test_clear(self):
        """Test clearing all registrations."""
        self.registry.register_agent(self.mock_agent, self.agent_config)
        self.registry.register_agent_type(MockAgent, "mock_agent")
        
        self.registry.clear()
        
        assert len(self.registry.list_agents()) == 0
        assert len(self.registry.list_agent_types()) == 0
    
    def test_validate_all_agents(self):
        """Test validating all registered agents."""
        # Register valid agent
        self.registry.register_agent(self.mock_agent, self.agent_config)
        
        # Register failing agent without config (to avoid registration error)
        failing_agent = FailingAgent("failing_agent")
        self.registry.register_agent(failing_agent)
        
        validation_results = self.registry.validate_all_agents()
        
        assert len(validation_results) == 2
        assert len(validation_results["test_agent"]) == 0  # No errors
        assert len(validation_results["failing_agent"]) > 0  # Has errors
    
    def test_agent_replacement_warning(self, caplog):
        """Test warning when replacing existing agent."""
        self.registry.register_agent(self.mock_agent)
        
        # Register another agent with same name
        new_agent = MockAgent("test_agent")
        self.registry.register_agent(new_agent)
        
        assert "already registered, replacing" in caplog.text
        assert self.registry.get_agent("test_agent") is new_agent
    
    def test_agent_type_replacement_warning(self, caplog):
        """Test warning when replacing existing agent type."""
        self.registry.register_agent_type(MockAgent, "mock_agent")
        
        # Register another type with same name
        self.registry.register_agent_type(FailingAgent, "mock_agent")
        
        assert "already registered, replacing" in caplog.text


class TestGlobalRegistry:
    """Test cases for global registry functions."""
    
    def setup_method(self):
        """Reset global registry before each test."""
        set_global_registry(AgentRegistry())
    
    def test_get_global_registry(self):
        """Test getting global registry."""
        registry = get_global_registry()
        
        assert isinstance(registry, AgentRegistry)
        
        # Should return same instance on subsequent calls
        registry2 = get_global_registry()
        assert registry is registry2
    
    def test_set_global_registry(self):
        """Test setting global registry."""
        custom_registry = AgentRegistry()
        agent = MockAgent("test_agent")
        custom_registry.register_agent(agent)
        
        set_global_registry(custom_registry)
        
        retrieved_registry = get_global_registry()
        assert retrieved_registry is custom_registry
        assert retrieved_registry.has_agent("test_agent")


class TestAgentCapabilityChecking:
    """Test cases for agent capability checking methods."""
    
    def test_custom_llm_capabilities(self):
        """Test agent with custom LLM capabilities."""
        
        class CustomAgent(BaseAgent):
            async def process(self, input_data: Dict[str, Any]) -> AgentResult:
                return AgentResult(success=True, output={})
            
            def get_workflow_config(self) -> WorkflowConfig:
                return WorkflowConfig(agent_name=self.name)
            
            def get_required_llm_capabilities(self) -> List[str]:
                return ['text_generation', 'function_calling', 'image_analysis']
        
        agent = CustomAgent("custom_agent")
        capabilities = agent.get_required_llm_capabilities()
        
        assert capabilities == ['text_generation', 'function_calling', 'image_analysis']
    
    def test_custom_input_validation(self):
        """Test agent with custom input validation."""
        
        class ValidatingAgent(BaseAgent):
            async def process(self, input_data: Dict[str, Any]) -> AgentResult:
                return AgentResult(success=True, output={})
            
            def get_workflow_config(self) -> WorkflowConfig:
                return WorkflowConfig(agent_name=self.name)
            
            def validate_input(self, input_data: Dict[str, Any]) -> bool:
                return isinstance(input_data, dict) and 'required_field' in input_data
        
        agent = ValidatingAgent("validating_agent")
        
        assert not agent.validate_input({})
        assert not agent.validate_input({'other_field': 'value'})
        assert agent.validate_input({'required_field': 'value'})


if __name__ == "__main__":
    pytest.main([__file__])