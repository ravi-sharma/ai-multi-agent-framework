"""Global pytest configuration and fixtures."""

import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.utils.test_data_manager import TestDataManager
from tests.utils.mock_providers import MockProviderFactory
from utils.llm_provider import LLMManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_manager():
    """Provide test data manager for all tests."""
    return TestDataManager()


@pytest.fixture
def mock_llm_manager():
    """Provide mock LLM manager with reliable provider."""
    manager = LLMManager()
    mock_provider = MockProviderFactory.create_reliable_provider()
    manager.register_provider("mock", mock_provider)
    manager.set_default_provider("mock")
    return manager


@pytest.fixture
def unreliable_llm_manager():
    """Provide mock LLM manager with unreliable provider for error testing."""
    manager = LLMManager()
    unreliable_provider = MockProviderFactory.create_unreliable_provider(failure_rate=0.3)
    manager.register_provider("unreliable", unreliable_provider)
    manager.set_default_provider("unreliable")
    return manager


@pytest.fixture
def failing_llm_manager():
    """Provide mock LLM manager with failing provider for error testing."""
    manager = LLMManager()
    failing_provider = MockProviderFactory.create_failing_provider()
    manager.register_provider("failing", failing_provider)
    manager.set_default_provider("failing")
    return manager


@pytest.fixture
def sample_email_data(test_data_manager):
    """Provide sample email data for testing."""
    return {
        'source': 'email',
        'email': test_data_manager.create_sample_email("sales").to_dict()
    }


@pytest.fixture
def sample_webhook_data(test_data_manager):
    """Provide sample webhook data for testing."""
    return test_data_manager.create_webhook_payload("github")


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        "test_mode": True,
        "llm": {
            "provider": "mock",
            "model": "mock-model",
            "api_key": "mock-key"
        },
        "agents": {
            "sales_agent": {
                "enabled": True,
                "config": {"test_mode": True}
            }
        }
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "ERROR"  # Reduce log noise during testing
    
    yield
    
    # Clean up after test
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
    if "LOG_LEVEL" in os.environ:
        del os.environ["LOG_LEVEL"]


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "test_" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


@pytest.fixture
def mock_agent_result():
    """Provide mock agent result for testing."""
    from models.data_models import AgentResult
    
    return AgentResult(
        success=True,
        agent_name="test_agent",
        execution_time=0.1,
        output={
            "agent_type": "test",
            "processed": True,
            "test_data": "mock_result"
        },
        notes=["Test processing completed"],
        requires_human_review=False
    )


@pytest.fixture
def mock_sales_notes():
    """Provide mock sales notes for testing."""
    from models.data_models import SalesNotes
    
    return SalesNotes(
        customer_problem="Customer needs pricing information",
        proposed_solution="Provide detailed pricing and schedule demo",
        urgency_level="high",
        follow_up_required=True,
        key_points=["Urgent request", "Enterprise customer", "High value opportunity"],
        customer_info={
            "email": "customer@example.com",
            "company": "Test Company",
            "industry": "Technology"
        },
        estimated_value=25000,
        next_steps=["Send pricing", "Schedule demo call"]
    )


# Performance test fixtures
@pytest.fixture
def performance_test_config():
    """Provide configuration for performance tests."""
    return {
        "concurrent_users": 5,
        "requests_per_user": 3,
        "ramp_up_time": 5,
        "test_duration": 30,
        "base_url": "http://localhost:8000",
        "request_timeout": 10
    }


# Skip markers for conditional tests
def pytest_runtest_setup(item):
    """Set up individual test runs with conditional skipping."""
    # Skip performance tests unless explicitly requested
    if "performance" in item.keywords and not item.config.getoption("--run-performance", default=False):
        pytest.skip("Performance tests skipped (use --run-performance to run)")
    
    # Skip slow tests unless explicitly requested
    if "slow" in item.keywords and not item.config.getoption("--run-slow", default=False):
        pytest.skip("Slow tests skipped (use --run-slow to run)")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-performance",
        action="store_true",
        default=False,
        help="Run performance tests"
    )
    parser.addoption(
        "--run-slow",
        action="store_true", 
        default=False,
        help="Run slow tests"
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests"
    )


# Test result reporting
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Make test reports available to fixtures."""
    outcome = yield
    rep = outcome.get_result()
    
    # Store test result in item for use by other fixtures
    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture
def test_result(request):
    """Provide access to test result in fixtures."""
    return {
        "setup": getattr(request.node, "rep_setup", None),
        "call": getattr(request.node, "rep_call", None),
        "teardown": getattr(request.node, "rep_teardown", None)
    }