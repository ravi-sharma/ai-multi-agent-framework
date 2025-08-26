"""Unit tests for the AgentRouter class."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from routing.agent_router import AgentRouter
from core.base_agent import BaseAgent
from core.agent_registry import AgentRegistry
from core.criteria_evaluator import CriteriaEngine
from models.data_models import TriggerData, AgentMatch, AgentResult
from models.config_models import WorkflowConfig
from core.exceptions import RoutingError, AgentNotFoundError


class MockAgent(BaseAgent):
    """Mock agent for testing purposes."""
    
    def __init__(self, name: str, should_validate: bool = True, should_succeed: bool = True):
        super().__init__(name)
        self.should_validate = should_validate
        self.should_succeed = should_succeed
        self.process_called = False
        self.last_input = None
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Mock process method."""
        self.process_called = True
        self.last_input = input_data
        
        if self.should_succeed:
            return AgentResult(
                success=True,
                output={'processed': True, 'agent': self.name},
                execution_time=0.1,
                agent_name=self.name
            )
        else:
            return AgentResult(
                success=False,
                output={},
                error_message="Mock agent failure",
                agent_name=self.name
            )
    
    def get_workflow_config(self) -> WorkflowConfig:
        """Mock workflow config."""
        return WorkflowConfig(
            agent_type="mock",
            llm_provider="test",
            enabled=True
        )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Mock input validation."""
        return self.should_validate


class TestAgentRouter:
    """Test cases for AgentRouter class."""
    
    @pytest.fixture
    def mock_criteria_engine(self):
        """Create a mock criteria engine."""
        engine = Mock(spec=CriteriaEngine)
        engine.evaluate = Mock(return_value=[])
        engine.load_criteria_from_yaml = Mock()
        engine.load_criteria = Mock()
        engine.get_available_evaluators = Mock(return_value=['contains', 'equals'])
        return engine
    
    @pytest.fixture
    def mock_agent_registry(self):
        """Create a mock agent registry."""
        registry = Mock(spec=AgentRegistry)
        registry.get_agent = Mock()
        registry.register_agent = Mock()
        registry.unregister_agent = Mock(return_value=True)
        registry.has_agent = Mock(return_value=True)
        registry.list_agents = Mock(return_value=[])
        registry.get_agent_info = Mock(return_value={})
        registry.get_all_agent_info = Mock(return_value={})
        registry.validate_all_agents = Mock(return_value={})
        return registry
    
    @pytest.fixture
    def sample_trigger_data(self):
        """Create sample trigger data."""
        return TriggerData(
            source="webhook",
            timestamp=datetime.now(),
            data={
                "email": {
                    "subject": "Need help with purchase",
                    "sender": "customer@example.com",
                    "body": "I want to buy your product"
                }
            },
            metadata={"request_id": "test-123"}
        )
    
    @pytest.fixture
    def agent_router(self, mock_criteria_engine, mock_agent_registry):
        """Create an AgentRouter instance with mocked dependencies."""
        router = AgentRouter(
            criteria_engine=mock_criteria_engine,
            agent_registry=mock_agent_registry,
            default_agent_name="default_agent"
        )
        # Reset stats for each test
        router.reset_routing_stats()
        return router
    
    def test_init_with_defaults(self):
        """Test AgentRouter initialization with default parameters."""
        router = AgentRouter()
        
        assert router.criteria_engine is not None
        assert router.agent_registry is not None
        assert router.default_agent_name is None
        assert router._routing_stats['total_requests'] == 0
    
    def test_init_with_custom_params(self, mock_criteria_engine, mock_agent_registry):
        """Test AgentRouter initialization with custom parameters."""
        router = AgentRouter(
            criteria_engine=mock_criteria_engine,
            agent_registry=mock_agent_registry,
            default_agent_name="custom_default"
        )
        
        assert router.criteria_engine == mock_criteria_engine
        assert router.agent_registry == mock_agent_registry
        assert router.default_agent_name == "custom_default"
    
    @pytest.mark.asyncio
    async def test_route_successful_match(self, agent_router, sample_trigger_data):
        """Test successful routing with criteria match."""
        # Setup mocks
        mock_agent = MockAgent("sales_agent")
        agent_match = AgentMatch(
            agent_name="sales_agent",
            criteria_name="sales_criteria",
            priority=1,
            confidence=0.9
        )
        
        agent_router.criteria_engine.evaluate.return_value = [agent_match]
        agent_router.agent_registry.get_agent.return_value = mock_agent
        
        # Execute routing
        result = await agent_router.route(sample_trigger_data)
        
        # Verify results
        assert result.success is True
        assert result.agent_name == "sales_agent"
        assert mock_agent.process_called is True
        assert agent_router._routing_stats['successful_routes'] == 1
        assert agent_router._routing_stats['total_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_route_multiple_matches_priority_selection(self, agent_router, sample_trigger_data):
        """Test routing with multiple matches selects highest priority."""
        # Setup multiple matches with different priorities
        low_priority_agent = MockAgent("low_priority_agent")
        high_priority_agent = MockAgent("high_priority_agent")
        
        matches = [
            AgentMatch("low_priority_agent", "low_criteria", priority=1, confidence=0.8),
            AgentMatch("high_priority_agent", "high_criteria", priority=5, confidence=0.7)
        ]
        
        agent_router.criteria_engine.evaluate.return_value = matches
        
        def mock_get_agent(name):
            if name == "low_priority_agent":
                return low_priority_agent
            elif name == "high_priority_agent":
                return high_priority_agent
            raise AgentNotFoundError(f"Agent {name} not found")
        
        agent_router.agent_registry.get_agent.side_effect = mock_get_agent
        
        # Execute routing
        result = await agent_router.route(sample_trigger_data)
        
        # Verify high priority agent was selected
        assert result.agent_name == "high_priority_agent"
        assert high_priority_agent.process_called is True
        assert low_priority_agent.process_called is False
    
    @pytest.mark.asyncio
    async def test_route_fallback_agent(self, agent_router, sample_trigger_data):
        """Test routing falls back to default agent when no matches."""
        # Setup no matches
        agent_router.criteria_engine.evaluate.return_value = []
        
        # Setup fallback agent
        fallback_agent = MockAgent("default_agent")
        agent_router.agent_registry.get_agent.return_value = fallback_agent
        
        # Execute routing
        result = await agent_router.route(sample_trigger_data)
        
        # Verify fallback was used
        assert result.agent_name == "default_agent"
        assert fallback_agent.process_called is True
        assert agent_router._routing_stats['fallback_routes'] == 1
    
    @pytest.mark.asyncio
    async def test_route_no_agent_found_error(self, agent_router, sample_trigger_data):
        """Test routing raises error when no agent found and no fallback."""
        # Setup no matches and no fallback
        agent_router.criteria_engine.evaluate.return_value = []
        agent_router.default_agent_name = None
        
        # Execute and verify error
        with pytest.raises(RoutingError, match="No suitable agent found"):
            await agent_router.route(sample_trigger_data)
        
        assert agent_router._routing_stats['failed_routes'] == 1
    
    @pytest.mark.asyncio
    async def test_route_agent_validation_failure(self, agent_router, sample_trigger_data):
        """Test routing skips agents that fail input validation."""
        # Setup agents with different validation results
        invalid_agent = MockAgent("invalid_agent", should_validate=False)
        valid_agent = MockAgent("valid_agent", should_validate=True)
        
        matches = [
            AgentMatch("invalid_agent", "criteria1", priority=2, confidence=0.9),
            AgentMatch("valid_agent", "criteria2", priority=1, confidence=0.8)
        ]
        
        agent_router.criteria_engine.evaluate.return_value = matches
        
        def mock_get_agent(name):
            if name == "invalid_agent":
                return invalid_agent
            elif name == "valid_agent":
                return valid_agent
            raise AgentNotFoundError(f"Agent {name} not found")
        
        agent_router.agent_registry.get_agent.side_effect = mock_get_agent
        
        # Execute routing
        result = await agent_router.route(sample_trigger_data)
        
        # Verify valid agent was selected despite lower priority
        assert result.agent_name == "valid_agent"
        assert valid_agent.process_called is True
        assert invalid_agent.process_called is False
    
    @pytest.mark.asyncio
    async def test_route_agent_not_found_in_registry(self, agent_router, sample_trigger_data):
        """Test routing handles agent not found in registry."""
        # Setup match for non-existent agent
        matches = [AgentMatch("nonexistent_agent", "criteria", priority=1, confidence=0.9)]
        agent_router.criteria_engine.evaluate.return_value = matches
        agent_router.agent_registry.get_agent.side_effect = AgentNotFoundError("Agent not found")
        
        # Setup fallback
        fallback_agent = MockAgent("default_agent")
        
        def mock_get_agent_with_fallback(name):
            if name == "default_agent":
                return fallback_agent
            raise AgentNotFoundError("Agent not found")
        
        agent_router.agent_registry.get_agent.side_effect = mock_get_agent_with_fallback
        
        # Execute routing
        result = await agent_router.route(sample_trigger_data)
        
        # Verify fallback was used
        assert result.agent_name == "default_agent"
        assert agent_router._routing_stats['fallback_routes'] == 1
    
    @pytest.mark.asyncio
    async def test_route_agent_execution_failure(self, agent_router, sample_trigger_data):
        """Test routing handles agent execution failure gracefully."""
        # Setup failing agent
        failing_agent = MockAgent("failing_agent", should_succeed=False)
        matches = [AgentMatch("failing_agent", "criteria", priority=1, confidence=0.9)]
        
        agent_router.criteria_engine.evaluate.return_value = matches
        agent_router.agent_registry.get_agent.return_value = failing_agent
        
        # Execute routing
        result = await agent_router.route(sample_trigger_data)
        
        # Verify failure is handled gracefully
        assert result.success is False
        assert result.agent_name == "failing_agent"
        assert "Mock agent failure" in result.error_message
    
    @pytest.mark.asyncio
    async def test_route_agent_execution_exception(self, agent_router, sample_trigger_data):
        """Test routing handles agent execution exceptions."""
        # Setup agent that raises exception
        mock_agent = MockAgent("exception_agent")
        mock_agent.process = AsyncMock(side_effect=Exception("Test exception"))
        
        matches = [AgentMatch("exception_agent", "criteria", priority=1, confidence=0.9)]
        agent_router.criteria_engine.evaluate.return_value = matches
        agent_router.agent_registry.get_agent.return_value = mock_agent
        
        # Execute routing
        result = await agent_router.route(sample_trigger_data)
        
        # Verify exception is handled
        assert result.success is False
        assert result.agent_name == "exception_agent"
        assert "Agent execution failed" in result.error_message
    
    def test_register_agent(self, agent_router):
        """Test agent registration."""
        mock_agent = MockAgent("test_agent")
        
        agent_router.register_agent(mock_agent)
        
        agent_router.agent_registry.register_agent.assert_called_once_with(mock_agent)
    
    def test_unregister_agent(self, agent_router):
        """Test agent unregistration."""
        result = agent_router.unregister_agent("test_agent")
        
        assert result is True
        agent_router.agent_registry.unregister_agent.assert_called_once_with("test_agent")
    
    def test_get_agent(self, agent_router):
        """Test getting agent by name."""
        mock_agent = MockAgent("test_agent")
        agent_router.agent_registry.get_agent.return_value = mock_agent
        
        result = agent_router.get_agent("test_agent")
        
        assert result == mock_agent
        agent_router.agent_registry.get_agent.assert_called_once_with("test_agent")
    
    def test_has_agent(self, agent_router):
        """Test checking if agent exists."""
        result = agent_router.has_agent("test_agent")
        
        assert result is True
        agent_router.agent_registry.has_agent.assert_called_once_with("test_agent")
    
    def test_list_agents(self, agent_router):
        """Test listing all agents."""
        agent_router.agent_registry.list_agents.return_value = ["agent1", "agent2"]
        
        result = agent_router.list_agents()
        
        assert result == ["agent1", "agent2"]
    
    def test_set_default_agent(self, agent_router):
        """Test setting default agent."""
        mock_agent = MockAgent("new_default")
        agent_router.agent_registry.get_agent.return_value = mock_agent
        
        agent_router.set_default_agent("new_default")
        
        assert agent_router.default_agent_name == "new_default"
        agent_router.agent_registry.get_agent.assert_called_once_with("new_default")
    
    def test_set_default_agent_not_found(self, agent_router):
        """Test setting default agent that doesn't exist."""
        agent_router.agent_registry.get_agent.side_effect = AgentNotFoundError("Not found")
        
        with pytest.raises(AgentNotFoundError):
            agent_router.set_default_agent("nonexistent")
    
    def test_get_default_agent(self, agent_router):
        """Test getting default agent name."""
        result = agent_router.get_default_agent()
        assert result == "default_agent"
    
    def test_load_criteria_from_file(self, agent_router):
        """Test loading criteria from file."""
        agent_router.load_criteria_from_file("test_criteria.yaml")
        
        agent_router.criteria_engine.load_criteria_from_yaml.assert_called_once_with("test_criteria.yaml")
    
    def test_add_criteria(self, agent_router):
        """Test adding criteria configurations."""
        criteria_configs = [{"name": "test", "agent": "test_agent"}]
        
        agent_router.add_criteria(criteria_configs)
        
        agent_router.criteria_engine.load_criteria.assert_called_once_with(criteria_configs)
    
    def test_get_routing_stats(self, agent_router):
        """Test getting routing statistics."""
        # Modify stats
        agent_router._routing_stats['total_requests'] = 10
        agent_router._routing_stats['successful_routes'] = 8
        
        stats = agent_router.get_routing_stats()
        
        assert stats['total_requests'] == 10
        assert stats['successful_routes'] == 8
        # Verify it's a copy
        stats['total_requests'] = 20
        assert agent_router._routing_stats['total_requests'] == 10
    
    def test_reset_routing_stats(self, agent_router):
        """Test resetting routing statistics."""
        # Set some stats
        agent_router._routing_stats['total_requests'] = 10
        agent_router._routing_stats['agent_usage']['test'] = 5
        
        agent_router.reset_routing_stats()
        
        assert agent_router._routing_stats['total_requests'] == 0
        assert agent_router._routing_stats['agent_usage'] == {}
    
    def test_validate_configuration(self, agent_router):
        """Test configuration validation."""
        agent_router.agent_registry.validate_all_agents.return_value = {
            "agent1": ["error1", "error2"],
            "agent2": []
        }
        
        result = agent_router.validate_configuration()
        
        assert "agent1: error1" in result['agents']
        assert "agent1: error2" in result['agents']
        assert len(result['criteria']) == 0  # No criteria errors expected
        assert len(result['routing']) == 0   # Default agent exists
    
    def test_validate_configuration_missing_default_agent(self, agent_router):
        """Test configuration validation with missing default agent."""
        agent_router.agent_registry.has_agent.return_value = False
        agent_router.agent_registry.validate_all_agents.return_value = {}
        
        result = agent_router.validate_configuration()
        
        assert any("Default agent 'default_agent' not registered" in error for error in result['routing'])
    
    @pytest.mark.asyncio
    async def test_test_routing(self, agent_router, sample_trigger_data):
        """Test routing test functionality."""
        # Setup matches
        matches = [AgentMatch("test_agent", "test_criteria", priority=1, confidence=0.9)]
        agent_router.criteria_engine.evaluate.return_value = matches
        
        mock_agent = MockAgent("test_agent")
        agent_router.agent_registry.get_agent.return_value = mock_agent
        
        # Execute test
        result = await agent_router.test_routing(sample_trigger_data)
        
        # Verify results
        assert result['success'] is True
        assert result['selected_agent'] == "test_agent"
        assert result['routing_possible'] is True
        assert len(result['matches']) == 1
        assert result['matches'][0]['agent_name'] == "test_agent"
    
    @pytest.mark.asyncio
    async def test_test_routing_with_fallback(self, agent_router, sample_trigger_data):
        """Test routing test with fallback scenario."""
        # Setup no matches
        agent_router.criteria_engine.evaluate.return_value = []
        
        # Setup fallback agent
        fallback_agent = MockAgent("default_agent")
        
        def mock_get_agent(name):
            if name == "default_agent":
                return fallback_agent
            raise AgentNotFoundError("Not found")
        
        agent_router.agent_registry.get_agent.side_effect = mock_get_agent
        
        # Execute test
        result = await agent_router.test_routing(sample_trigger_data)
        
        # Verify results
        assert result['success'] is True
        assert result['selected_agent'] is None
        assert result['fallback_agent'] == "default_agent"
        assert result['would_use_fallback'] is True
        assert result['routing_possible'] is True
    
    @pytest.mark.asyncio
    async def test_test_routing_error(self, agent_router, sample_trigger_data):
        """Test routing test with error."""
        agent_router.criteria_engine.evaluate.side_effect = Exception("Test error")
        
        result = await agent_router.test_routing(sample_trigger_data)
        
        assert result['success'] is False
        assert "Test error" in result['error']
        assert result['routing_possible'] is False


if __name__ == "__main__":
    pytest.main([__file__])