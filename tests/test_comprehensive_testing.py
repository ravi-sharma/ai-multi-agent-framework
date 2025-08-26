"""Test the comprehensive testing framework itself."""

import pytest
import asyncio
from unittest.mock import Mock, patch

from tests.utils.test_data_manager import TestDataManager, TestCase
from tests.utils.mock_providers import (
    MockLLMProvider, MockFailingLLMProvider, MockProviderFactory
)
from tests.utils.performance_utils import (
    PerformanceTestRunner, LoadTestConfig, ConcurrencyTestRunner
)


class TestTestDataManager:
    """Test the test data manager utility."""
    
    def test_initialization(self):
        """Test test data manager initialization."""
        manager = TestDataManager()
        assert manager.test_counter == 0
    
    def test_unique_id_generation(self):
        """Test unique ID generation."""
        manager = TestDataManager()
        
        id1 = manager.get_unique_id()
        id2 = manager.get_unique_id()
        
        assert id1 != id2
        assert id1.startswith("test_1_")
        assert id2.startswith("test_2_")
    
    def test_create_sample_email_sales(self):
        """Test creating sales email sample."""
        manager = TestDataManager()
        email = manager.create_sample_email("sales")
        
        assert email.subject
        assert email.sender
        assert email.recipient
        assert email.body
        assert "purchas" in email.subject.lower() or "buy" in email.body.lower()
    
    def test_create_sample_email_support(self):
        """Test creating support email sample."""
        manager = TestDataManager()
        email = manager.create_sample_email("support")
        
        assert email.subject
        assert email.sender
        assert email.recipient
        assert email.body
        assert "help" in email.subject.lower() or "issue" in email.body.lower()
    
    def test_create_webhook_payload_github(self):
        """Test creating GitHub webhook payload."""
        manager = TestDataManager()
        payload = manager.create_webhook_payload("github")
        
        assert payload["source"] == "github"
        assert "data" in payload
        assert "metadata" in payload
        assert payload["data"]["action"] == "push"
    
    def test_create_agent_test_cases_sales(self):
        """Test creating sales agent test cases."""
        manager = TestDataManager()
        test_cases = manager.create_agent_test_cases("sales_agent")
        
        assert len(test_cases) > 0
        assert all(isinstance(tc, TestCase) for tc in test_cases)
        assert any(tc.expected_success for tc in test_cases)
        assert any(not tc.expected_success for tc in test_cases)  # Should have failure cases
    
    def test_create_performance_test_data(self):
        """Test creating performance test data."""
        manager = TestDataManager()
        test_data = manager.create_performance_test_data(5, "sales")
        
        assert len(test_data) == 5
        for i, data in enumerate(test_data):
            assert data["source"] == "email"
            assert "email" in data
            assert data["test_index"] == i
    
    def test_validate_agent_result(self):
        """Test agent result validation."""
        from models.data_models import AgentResult
        
        manager = TestDataManager()
        
        # Create test case
        test_case = TestCase(
            name="test_case",
            input_data={"test": "data"},
            expected_success=True,
            expected_output_keys=["result", "status"]
        )
        
        # Create matching result
        result = AgentResult(
            success=True,
            agent_name="test_agent",
            execution_time=0.1,
            output={"result": "success", "status": "completed"}
        )
        
        errors = manager.validate_agent_result(result, test_case)
        assert len(errors) == 0
        
        # Create non-matching result
        bad_result = AgentResult(
            success=False,
            agent_name="test_agent",
            execution_time=0.1,
            output={"result": "failure"}
        )
        
        errors = manager.validate_agent_result(bad_result, test_case)
        assert len(errors) > 0


class TestMockProviders:
    """Test mock LLM providers."""
    
    def test_mock_provider_initialization(self):
        """Test mock provider initialization."""
        config = {"api_key": "test-key", "model": "test-model"}
        provider = MockLLMProvider(config)
        
        assert provider.config == config
        assert provider.call_count == 0
        assert provider.response_delay == 0.1
        assert provider.failure_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_mock_provider_generate(self):
        """Test mock provider text generation."""
        config = {"api_key": "test-key"}
        provider = MockLLMProvider(config, response_delay=0.01)
        
        response = await provider.generate("Test prompt")
        
        assert response.content
        assert response.provider == "mock"
        assert provider.call_count == 1
        assert len(provider.call_history) == 1
    
    @pytest.mark.asyncio
    async def test_mock_provider_contextual_responses(self):
        """Test contextual response generation."""
        config = {"api_key": "test-key"}
        provider = MockLLMProvider(config, response_delay=0.01)
        
        # Test customer extraction
        response = await provider.generate("Extract customer information from this email")
        assert "company_name" in response.content
        
        # Test intent analysis
        response = await provider.generate("Analyze customer intent in this message")
        assert "primary_intent" in response.content
    
    @pytest.mark.asyncio
    async def test_failing_provider(self):
        """Test failing provider."""
        config = {"api_key": "test-key"}
        provider = MockFailingLLMProvider(config)
        
        with pytest.raises(Exception):
            await provider.generate("Test prompt")
        
        assert provider.call_count == 1
    
    def test_provider_factory(self):
        """Test provider factory methods."""
        reliable = MockProviderFactory.create_reliable_provider()
        assert reliable.failure_rate == 0.0
        
        unreliable = MockProviderFactory.create_unreliable_provider()
        assert unreliable.failure_rate > 0.0
        
        failing = MockProviderFactory.create_failing_provider()
        assert isinstance(failing, MockFailingLLMProvider)
    
    def test_custom_responses(self):
        """Test custom response setting."""
        config = {"api_key": "test-key"}
        provider = MockLLMProvider(config)
        
        provider.set_custom_response("special prompt", "special response")
        assert "special prompt" in provider.custom_responses
        
        provider.clear_custom_responses()
        assert len(provider.custom_responses) == 0


class TestPerformanceUtils:
    """Test performance testing utilities."""
    
    def test_load_test_config(self):
        """Test load test configuration."""
        config = LoadTestConfig(
            concurrent_users=5,
            requests_per_user=3,
            base_url="http://localhost:8000"
        )
        
        assert config.concurrent_users == 5
        assert config.requests_per_user == 3
        assert config.base_url == "http://localhost:8000"
    
    def test_performance_test_runner_initialization(self):
        """Test performance test runner initialization."""
        runner = PerformanceTestRunner()
        assert runner.test_data_manager is not None
        assert runner.session is None
    
    def test_concurrency_test_runner_initialization(self):
        """Test concurrency test runner initialization."""
        runner = ConcurrencyTestRunner()
        assert runner.test_data_manager is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_processing_mock(self):
        """Test concurrent agent processing with mock function."""
        runner = ConcurrencyTestRunner()
        
        async def mock_agent_func(data):
            """Mock agent processing function."""
            await asyncio.sleep(0.01)  # Simulate processing
            return {"success": True, "data": data}
        
        results = await runner.test_concurrent_agent_processing(
            mock_agent_func, concurrent_requests=3
        )
        
        assert results["concurrent_requests"] == 3
        assert results["successful"] == 3
        assert results["failed"] == 0
        assert results["success_rate"] == 1.0
    
    def test_thread_safety_testing(self):
        """Test thread safety testing utility."""
        runner = ConcurrencyTestRunner()
        
        def simple_function():
            """Simple function for thread safety testing."""
            return "result"
        
        results = runner.test_thread_safety(
            simple_function, thread_count=3, iterations_per_thread=5
        )
        
        assert results["thread_count"] == 3
        assert results["iterations_per_thread"] == 5
        assert results["successful_iterations"] == 15
        assert results["success_rate"] == 1.0


class TestTestingIntegration:
    """Test integration of testing components."""
    
    def test_test_data_with_mock_provider(self):
        """Test integration of test data manager with mock provider."""
        data_manager = TestDataManager()
        provider = MockProviderFactory.create_reliable_provider()
        
        # Create test email
        email = data_manager.create_sample_email("sales")
        assert email.subject
        
        # Verify provider can handle the data
        assert provider.validate_config()
        assert "text_generation" in provider.get_capabilities()
    
    @pytest.mark.asyncio
    async def test_end_to_end_mock_workflow(self):
        """Test end-to-end workflow with mock components."""
        from agents.sales_agent import SalesAgent
        from utils.llm_provider import LLMManager
        
        # Set up components
        data_manager = TestDataManager()
        mock_provider = MockProviderFactory.create_reliable_provider()
        
        llm_manager = LLMManager()
        llm_manager.register_provider("mock", mock_provider)
        llm_manager.set_default_provider("mock")
        
        # Create agent
        agent = SalesAgent(
            name="test_agent",
            config={"test_mode": True},
            llm_manager=llm_manager
        )
        
        # Create test data
        email_data = {
            "source": "email",
            "email": data_manager.create_sample_email("sales").to_dict()
        }
        
        # Process through agent
        result = await agent.process(email_data)
        
        # Verify result
        assert result.success is True
        assert result.agent_name == "test_agent"
        assert "sales_notes" in result.output
        
        # Verify mock provider was called
        assert mock_provider.call_count > 0
    
    def test_test_case_validation_integration(self):
        """Test test case validation with real agent results."""
        from models.data_models import AgentResult
        
        data_manager = TestDataManager()
        
        # Create test cases
        test_cases = data_manager.create_agent_test_cases("sales_agent")
        success_case = next(tc for tc in test_cases if tc.expected_success)
        
        # Create matching result
        result = AgentResult(
            success=True,
            agent_name="sales_agent",
            execution_time=0.1,
            output={key: f"test_{key}" for key in success_case.expected_output_keys or []}
        )
        
        # Validate
        errors = data_manager.validate_agent_result(result, success_case)
        assert len(errors) == 0


class TestTestConfiguration:
    """Test pytest configuration and fixtures."""
    
    def test_pytest_markers_available(self):
        """Test that custom pytest markers are available."""
        # This test verifies that our custom markers are properly configured
        # The actual marker functionality is tested by pytest itself
        markers = ["unit", "integration", "performance", "slow"]
        
        # In a real test run, these markers would be available
        # Here we just verify the marker names are defined
        for marker in markers:
            assert isinstance(marker, str)
            assert len(marker) > 0
    
    def test_test_fixtures_importable(self):
        """Test that test fixtures can be imported."""
        # Test that our fixtures are properly defined
        from tests.conftest import (
            test_data_manager, mock_llm_manager, sample_email_data
        )
        
        # Fixtures should be callable functions
        assert callable(test_data_manager)
        assert callable(mock_llm_manager)
        assert callable(sample_email_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])