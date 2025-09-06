"""Shared test fixtures to reduce duplication across test modules."""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

from tests.utils.test_data_manager import TestDataManager
from tests.utils.mock_providers import MockProviderFactory
from utils.llm_provider import LLMManager
from agents.sales_agent import SalesAgent
from agents.default_agent import DefaultAgent
from models.data_models import EmailMessage, TriggerData, AgentResult
from configs.base_config import BaseConfig


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_data_manager():
    """Shared test data manager for all tests."""
    return TestDataManager()


@pytest.fixture(scope="session")
def mock_llm_manager():
    """Shared mock LLM manager with reliable provider."""
    manager = LLMManager()
    mock_provider = MockProviderFactory.create_reliable_provider()
    manager.register_provider("mock", mock_provider)
    manager.set_default_provider("mock")
    return manager


@pytest.fixture
def temp_config_dir():
    """Create temporary configuration directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield config_dir


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        yield data_dir


@pytest.fixture
def base_test_config():
    """Base test configuration."""
    return {
        "enabled": True,
        "log_level": "ERROR",
        "test_mode": True,
        "timeout": 30,
        "max_retries": 2
    }


@pytest.fixture
def sample_email_message(test_data_manager):
    """Sample email message for testing."""
    return test_data_manager.create_sample_email("sales")


@pytest.fixture
def sample_trigger_data(sample_email_message):
    """Sample trigger data for testing."""
    return TriggerData(
        source="email",
        timestamp=datetime.now(),
        data={
            "email": {
                "subject": sample_email_message.subject,
                "sender": sample_email_message.sender,
                "recipient": sample_email_message.recipient,
                "body": sample_email_message.body,
                "headers": sample_email_message.headers
            }
        },
        metadata={"test": True}
    )


@pytest.fixture
def sales_agent_config():
    """Configuration for sales agent testing."""
    return {
        "enabled": True,
        "test_mode": True,
        "log_level": "ERROR",
        "timeout": 30
    }


@pytest.fixture
def default_agent_config():
    """Configuration for default agent testing."""
    return {
        "enabled": True,
        "test_mode": True,
        "log_level": "ERROR",
        "response_template": "Test response template",
        "log_unmatched_requests": False
    }


@pytest.fixture
def mock_sales_agent(sales_agent_config, mock_llm_manager):
    """Mock sales agent for testing."""
    with patch('agents.sales_agent.LLMManager', return_value=mock_llm_manager):
        agent = SalesAgent("test_sales_agent", sales_agent_config)
        return agent


@pytest.fixture
def mock_default_agent(default_agent_config):
    """Mock default agent for testing."""
    return DefaultAgent("test_default_agent", default_agent_config)


@pytest.fixture
def mock_agent_result():
    """Mock agent result for testing."""
    return AgentResult(
        success=True,
        output={"test": "result"},
        agent_name="test_agent",
        execution_time=0.1,
        notes=["Test note"]
    )


@pytest.fixture
def mock_failed_agent_result():
    """Mock failed agent result for testing."""
    return AgentResult(
        success=False,
        output={},
        agent_name="test_agent",
        error_message="Test error",
        execution_time=0.1
    )


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Set test environment variables
    original_env = {}
    test_env_vars = {
        "TESTING": "true",
        "LOG_LEVEL": "ERROR",
        "DEBUG": "false"
    }
    
    # Store original values and set test values
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock(spec=BaseConfig)
    config.LOG_LEVEL = "ERROR"
    config.DEBUG = False
    config.API_HOST = "localhost"
    config.API_PORT = 8000
    config.API_WORKERS = 1
    config.DEFAULT_LLM_PROVIDER = "mock"
    return config


@pytest.fixture
def async_mock():
    """Create an AsyncMock for testing async functions."""
    return AsyncMock()


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing."""
    test_datetime = datetime(2024, 1, 1, 12, 0, 0)
    with patch('datetime.datetime') as mock_dt:
        mock_dt.now.return_value = test_datetime
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        yield test_datetime


@pytest.fixture
def performance_test_config():
    """Configuration for performance testing."""
    return {
        "concurrent_users": 10,
        "requests_per_user": 5,
        "ramp_up_time": 2,
        "test_duration": 10,
        "request_timeout": 5
    }


@pytest.fixture
def integration_test_data(test_data_manager):
    """Comprehensive test data for integration tests."""
    return {
        "sales_emails": [
            test_data_manager.create_sample_email("sales") for _ in range(3)
        ],
        "support_emails": [
            test_data_manager.create_sample_email("support") for _ in range(3)
        ],
        "general_emails": [
            test_data_manager.create_sample_email("general") for _ in range(2)
        ]
    }


@pytest.fixture
def mock_http_session():
    """Mock HTTP session for testing external API calls."""
    session_mock = AsyncMock()
    
    # Mock successful response
    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.json = AsyncMock(return_value={"success": True})
    response_mock.text = AsyncMock(return_value="Success")
    
    session_mock.get = AsyncMock(return_value=response_mock)
    session_mock.post = AsyncMock(return_value=response_mock)
    session_mock.put = AsyncMock(return_value=response_mock)
    session_mock.delete = AsyncMock(return_value=response_mock)
    
    return session_mock


@pytest.fixture
def error_scenarios():
    """Common error scenarios for testing."""
    return {
        "network_error": Exception("Network connection failed"),
        "timeout_error": asyncio.TimeoutError("Request timed out"),
        "validation_error": ValueError("Invalid input data"),
        "processing_error": RuntimeError("Processing failed"),
        "config_error": KeyError("Missing configuration key")
    }


class TestHelpers:
    """Helper methods for testing."""
    
    @staticmethod
    def assert_agent_result_success(result: AgentResult):
        """Assert that an agent result indicates success."""
        assert result.success is True
        assert result.error_message is None
        assert result.output is not None
        assert result.execution_time >= 0
    
    @staticmethod
    def assert_agent_result_failure(result: AgentResult, expected_error: str = None):
        """Assert that an agent result indicates failure."""
        assert result.success is False
        assert result.error_message is not None
        if expected_error:
            assert expected_error in result.error_message
        assert result.execution_time >= 0
    
    @staticmethod
    def assert_email_structure(email: EmailMessage):
        """Assert that an email has the required structure."""
        assert email.subject is not None
        assert email.sender is not None
        assert email.recipient is not None
        assert email.body is not None
        assert email.timestamp is not None
        assert isinstance(email.headers, dict)
    
    @staticmethod
    def assert_trigger_data_structure(trigger: TriggerData):
        """Assert that trigger data has the required structure."""
        assert trigger.source is not None
        assert trigger.timestamp is not None
        assert isinstance(trigger.data, dict)
        assert isinstance(trigger.metadata, dict)
    
    @staticmethod
    async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
        """Wait for a condition to become true."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
                return True
            await asyncio.sleep(interval)
        
        return False


@pytest.fixture
def test_helpers():
    """Test helper methods."""
    return TestHelpers


# Performance testing utilities
@pytest.fixture
def performance_monitor():
    """Monitor for performance testing."""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.metrics = {}
        
        def start(self):
            self.start_time = datetime.now()
        
        def stop(self):
            self.end_time = datetime.now()
        
        def get_duration(self) -> float:
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds()
            return 0.0
        
        def add_metric(self, name: str, value: Any):
            self.metrics[name] = value
        
        def get_metrics(self) -> Dict[str, Any]:
            return {
                **self.metrics,
                "duration": self.get_duration(),
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None
            }
    
    return PerformanceMonitor()


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test."""
    yield
    
    # Clean up any temporary files or resources
    # This runs after each test
    pass


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_session():
    """Cleanup after test session."""
    yield
    
    # Clean up session-wide resources
    # This runs after all tests in the session
    pass
