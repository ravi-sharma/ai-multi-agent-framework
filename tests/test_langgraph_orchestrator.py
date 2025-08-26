"""Tests for LangGraph orchestrator."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from orchestration.langgraph_orchestrator import (
    LangGraphOrchestrator, WorkflowState, create_workflow_state, 
    add_error_to_state, set_step_result_in_state, get_step_result_from_state
)
from models.data_models import (
    TriggerData, WorkflowContext, AgentResult, WorkflowResult
)
from models.config_models import (
    AgentConfig, WorkflowConfig
)
from core.exceptions import (
    WorkflowError, WorkflowTimeoutError, WorkflowRetryError
)


@pytest.fixture
def orchestrator():
    """Create a LangGraph orchestrator instance."""
    return LangGraphOrchestrator()


@pytest.fixture
def sample_trigger_data():
    """Create sample trigger data."""
    return TriggerData(
        source="test",
        timestamp=datetime.now(),
        data={"message": "test message"},
        metadata={"test": True}
    )


@pytest.fixture
def sample_agent_config():
    """Create sample agent configuration."""
    workflow_config = WorkflowConfig(
        agent_name="test_agent",
        max_retries=2,
        timeout=30,
        retry_delay=0.1,
        workflow_steps=["validate_input", "process_data", "generate_output"]
    )
    
    return AgentConfig(
        name="test_agent",
        agent_type="test",
        workflow_config=workflow_config
    )


class TestWorkflowState:
    """Test WorkflowState class."""
    
    def test_workflow_state_initialization(self, sample_trigger_data):
        """Test WorkflowState initialization."""
        context = WorkflowContext(
            workflow_id="test-id",
            agent_name="test_agent",
            trigger_data=sample_trigger_data,
            start_time=datetime.now()
        )
        
        state = create_workflow_state(sample_trigger_data, context)
        
        assert state["trigger_data"] == sample_trigger_data
        assert state["context"] == context
        assert state["current_output"] == {}
        assert state["errors"] == []
        assert state["retry_count"] == 0
        assert state["step_results"] == {}
    
    def test_add_error(self, sample_trigger_data):
        """Test adding errors to workflow state."""
        context = WorkflowContext(
            workflow_id="test-id",
            agent_name="test_agent",
            trigger_data=sample_trigger_data,
            start_time=datetime.now()
        )
        
        state = create_workflow_state(sample_trigger_data, context)
        state = add_error_to_state(state, "Test error")
        
        assert len(state["errors"]) == 1
        assert state["errors"][0] == "Test error"
    
    def test_step_results(self, sample_trigger_data):
        """Test step result management."""
        context = WorkflowContext(
            workflow_id="test-id",
            agent_name="test_agent",
            trigger_data=sample_trigger_data,
            start_time=datetime.now()
        )
        
        state = create_workflow_state(sample_trigger_data, context)
        
        # Set and get step result
        state = set_step_result_in_state(state, "test_step", {"result": "success"})
        result = get_step_result_from_state(state, "test_step")
        
        assert result == {"result": "success"}
        
        # Test default value
        default_result = get_step_result_from_state(state, "nonexistent", "default")
        assert default_result == "default"


class TestLangGraphOrchestrator:
    """Test LangGraphOrchestrator class."""
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.workflows == {}
        assert orchestrator.active_contexts == {}
        assert orchestrator.workflow_builders == {}
        assert orchestrator.step_functions == {}
    
    def test_create_workflow(self, orchestrator, sample_agent_config):
        """Test workflow creation."""
        workflow = orchestrator.create_workflow(sample_agent_config)
        
        assert workflow is not None
        # The workflow should be a compiled StateGraph
        assert hasattr(workflow, 'invoke')
    
    def test_create_workflow_with_default_config(self, orchestrator):
        """Test workflow creation with default configuration."""
        agent_config = AgentConfig(name="test_agent", agent_type="test")
        workflow = orchestrator.create_workflow(agent_config)
        
        assert workflow is not None
    
    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, orchestrator, sample_trigger_data, sample_agent_config):
        """Test successful workflow execution."""
        result = await orchestrator.execute_workflow(
            "test_agent", 
            sample_trigger_data, 
            sample_agent_config
        )
        
        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.result.success is True
        assert result.result.agent_name == "test_agent"
        assert result.execution_time > 0
        assert len(result.steps_completed) > 0
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_custom_step_function(self, orchestrator, sample_trigger_data, sample_agent_config):
        """Test workflow execution with custom step function."""
        # Register custom step function
        async def custom_validate_input(state: WorkflowState) -> WorkflowState:
            state["context"].add_step("validate_input")
            state = set_step_result_in_state(state, "validate_input", {"custom": True})
            return state
        
        orchestrator.register_step_function("validate_input", custom_validate_input)
        
        result = await orchestrator.execute_workflow(
            "test_agent",
            sample_trigger_data,
            sample_agent_config
        )
        
        assert result.success is True
        # Check that custom step was executed
        assert "validate_input" in result.steps_completed
    
    @pytest.mark.asyncio
    async def test_execute_workflow_timeout(self, orchestrator, sample_trigger_data):
        """Test workflow execution timeout."""
        # Create config with very short timeout
        workflow_config = WorkflowConfig(
            agent_name="test_agent",
            timeout=0.001,  # Very short timeout
            max_retries=0
        )
        agent_config = AgentConfig(
            name="test_agent",
            agent_type="test",
            workflow_config=workflow_config
        )
        
        # Register a slow step function
        async def slow_step(state: WorkflowState) -> WorkflowState:
            await asyncio.sleep(1)  # Sleep longer than timeout
            return state
        
        orchestrator.register_step_function("validate_input", slow_step)
        
        result = await orchestrator.execute_workflow(
            "test_agent",
            sample_trigger_data,
            agent_config
        )
        
        assert result.success is False
        assert "timed out" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_retry(self, orchestrator, sample_trigger_data):
        """Test workflow execution with retry logic."""
        workflow_config = WorkflowConfig(
            agent_name="test_agent",
            max_retries=2,
            retry_delay=0.01
        )
        agent_config = AgentConfig(
            name="test_agent",
            agent_type="test",
            workflow_config=workflow_config
        )
        
        call_count = 0
        
        # Register a step function that fails first time, succeeds second time
        async def flaky_step(state: WorkflowState) -> WorkflowState:
            nonlocal call_count
            call_count += 1
            state["context"].add_step("validate_input")
            
            if call_count == 1:
                raise WorkflowError("First attempt fails")
            
            state = set_step_result_in_state(state, "validate_input", {"attempt": call_count})
            return state
        
        orchestrator.register_step_function("validate_input", flaky_step)
        
        result = await orchestrator.execute_workflow(
            "test_agent",
            sample_trigger_data,
            agent_config
        )
        
        # Should succeed on retry
        assert result.success is True
        assert call_count > 1
    
    def test_register_workflow_builder(self, orchestrator):
        """Test registering custom workflow builder."""
        def custom_builder(agent_config):
            return Mock()
        
        orchestrator.register_workflow_builder("custom_agent", custom_builder)
        
        assert "custom_agent" in orchestrator.workflow_builders
        assert orchestrator.workflow_builders["custom_agent"] == custom_builder
    
    def test_register_step_function(self, orchestrator):
        """Test registering step functions."""
        def custom_step():
            pass
        
        # Register generic step function
        orchestrator.register_step_function("custom_step", custom_step)
        assert "custom_step" in orchestrator.step_functions
        
        # Register agent-specific step function
        orchestrator.register_step_function("custom_step", custom_step, "test_agent")
        assert "test_agent_custom_step" in orchestrator.step_functions
    
    def test_get_workflow_status(self, orchestrator, sample_trigger_data):
        """Test getting workflow status."""
        context = WorkflowContext(
            workflow_id="test-id",
            agent_name="test_agent",
            trigger_data=sample_trigger_data,
            start_time=datetime.now()
        )
        context.add_step("test_step")
        
        orchestrator.active_contexts["test-id"] = context
        
        status = orchestrator.get_workflow_status("test-id")
        
        assert status is not None
        assert status["workflow_id"] == "test-id"
        assert status["agent_name"] == "test_agent"
        assert status["current_step"] == "test_step"
        assert status["steps_completed"] == 0  # Current step not in history yet
        assert "start_time" in status
        assert "running_time" in status
    
    def test_get_workflow_status_not_found(self, orchestrator):
        """Test getting status for non-existent workflow."""
        status = orchestrator.get_workflow_status("nonexistent")
        assert status is None
    
    def test_cancel_workflow(self, orchestrator, sample_trigger_data):
        """Test cancelling a workflow."""
        context = WorkflowContext(
            workflow_id="test-id",
            agent_name="test_agent",
            trigger_data=sample_trigger_data,
            start_time=datetime.now()
        )
        
        orchestrator.active_contexts["test-id"] = context
        
        # Cancel workflow
        result = orchestrator.cancel_workflow("test-id")
        assert result is True
        assert "test-id" not in orchestrator.active_contexts
        
        # Try to cancel non-existent workflow
        result = orchestrator.cancel_workflow("nonexistent")
        assert result is False
    
    def test_handle_workflow_error(self, orchestrator, sample_trigger_data):
        """Test workflow error handling."""
        context = WorkflowContext(
            workflow_id="test-id",
            agent_name="test_agent",
            trigger_data=sample_trigger_data,
            start_time=datetime.now()
        )
        context.add_step("test_step")
        
        error = WorkflowError("Test error")
        
        # Should not raise exception
        orchestrator.handle_workflow_error(error, context)
        
        # Check that error info was stored
        assert context.get_variable("last_error") is not None
        error_info = context.get_variable("last_error")
        assert error_info["error"] == "Test error"
        assert error_info["workflow_id"] == "test-id"
    
    def test_get_active_workflows(self, orchestrator, sample_trigger_data):
        """Test getting active workflows."""
        context1 = WorkflowContext(
            workflow_id="test-id-1",
            agent_name="agent1",
            trigger_data=sample_trigger_data,
            start_time=datetime.now()
        )
        context2 = WorkflowContext(
            workflow_id="test-id-2",
            agent_name="agent2",
            trigger_data=sample_trigger_data,
            start_time=datetime.now()
        )
        
        orchestrator.active_contexts["test-id-1"] = context1
        orchestrator.active_contexts["test-id-2"] = context2
        
        active_workflows = orchestrator.get_active_workflows()
        
        assert len(active_workflows) == 2
        workflow_ids = [w["workflow_id"] for w in active_workflows]
        assert "test-id-1" in workflow_ids
        assert "test-id-2" in workflow_ids
    
    def test_clear_workflows(self, orchestrator, sample_agent_config):
        """Test clearing cached workflows."""
        # Create a workflow
        workflow = orchestrator.create_workflow(sample_agent_config)
        orchestrator.workflows["test_agent"] = workflow
        
        assert len(orchestrator.workflows) == 1
        
        # Clear workflows
        orchestrator.clear_workflows()
        
        assert len(orchestrator.workflows) == 0
    
    @pytest.mark.asyncio
    async def test_workflow_context_manager(self, orchestrator, sample_trigger_data):
        """Test workflow context manager."""
        context = WorkflowContext(
            workflow_id="test-id",
            agent_name="test_agent",
            trigger_data=sample_trigger_data,
            start_time=datetime.now()
        )
        
        orchestrator.active_contexts["test-id"] = context
        
        async with orchestrator.workflow_context("test-id") as ctx:
            assert ctx == context
        
        # Context should still exist after context manager
        assert "test-id" in orchestrator.active_contexts
    
    def test_should_retry_logic(self, orchestrator, sample_trigger_data):
        """Test retry decision logic."""
        context = WorkflowContext(
            workflow_id="test-id",
            agent_name="test_agent",
            trigger_data=sample_trigger_data,
            start_time=datetime.now()
        )
        
        state = create_workflow_state(sample_trigger_data, context)
        
        # No errors, should end
        result = orchestrator._should_retry(state)
        assert result == "end"
        
        # Has errors but no retries yet, should retry
        state = add_error_to_state(state, "Test error")
        result = orchestrator._should_retry(state)
        assert result == "retry"
        
        # Has errors and max retries reached, should end
        state = {**state, "retry_count": 3}
        result = orchestrator._should_retry(state)
        assert result == "end"


class TestWorkflowIntegration:
    """Integration tests for workflow execution."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, orchestrator, sample_trigger_data):
        """Test complete end-to-end workflow execution."""
        # Create agent config with custom steps
        workflow_config = WorkflowConfig(
            agent_name="integration_agent",
            workflow_steps=["parse_input", "validate_data", "process_request", "generate_response"]
        )
        agent_config = AgentConfig(
            name="integration_agent",
            agent_type="integration",
            workflow_config=workflow_config
        )
        
        # Register custom step functions
        async def parse_input(state: WorkflowState) -> WorkflowState:
            state["context"].add_step("parse_input")
            parsed_data = {
                "source": state["trigger_data"].source,
                "message": state["trigger_data"].data.get("message", "")
            }
            state = set_step_result_in_state(state, "parse_input", parsed_data)
            return state
        
        async def validate_data(state: WorkflowState) -> WorkflowState:
            state["context"].add_step("validate_data")
            parsed_data = get_step_result_from_state(state, "parse_input", {})
            
            if not parsed_data.get("message"):
                raise WorkflowError("No message provided")
            
            state = set_step_result_in_state(state, "validate_data", {"valid": True})
            return state
        
        async def process_request(state: WorkflowState) -> WorkflowState:
            state["context"].add_step("process_request")
            parsed_data = get_step_result_from_state(state, "parse_input", {})
            
            processed = {
                "original_message": parsed_data.get("message", ""),
                "processed_at": datetime.now().isoformat(),
                "word_count": len(parsed_data.get("message", "").split())
            }
            state = set_step_result_in_state(state, "process_request", processed)
            return state
        
        async def generate_response(state: WorkflowState) -> WorkflowState:
            state["context"].add_step("generate_response")
            processed_data = get_step_result_from_state(state, "process_request", {})
            
            response = {
                "status": "success",
                "processed_data": processed_data,
                "workflow_id": state["context"].workflow_id
            }
            state = {**state, "current_output": response}
            return state
        
        # Register all step functions
        orchestrator.register_step_function("parse_input", parse_input)
        orchestrator.register_step_function("validate_data", validate_data)
        orchestrator.register_step_function("process_request", process_request)
        orchestrator.register_step_function("generate_response", generate_response)
        
        # Execute workflow
        result = await orchestrator.execute_workflow(
            "integration_agent",
            sample_trigger_data,
            agent_config
        )
        
        # Verify results
        assert result.success is True
        assert result.result.success is True
        assert len(result.steps_completed) == 4
        assert "parse_input" in result.steps_completed
        assert "validate_data" in result.steps_completed
        assert "process_request" in result.steps_completed
        assert "generate_response" in result.steps_completed
        
        # Check output
        output = result.result.output
        assert output["status"] == "success"
        assert "processed_data" in output
        assert "workflow_id" in output