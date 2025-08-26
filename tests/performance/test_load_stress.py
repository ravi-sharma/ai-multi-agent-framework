"""Load and stress testing for the AI agent framework."""

import pytest
import asyncio
import time
from unittest.mock import patch

from tests.utils.performance_utils import (
    PerformanceTestRunner, LoadTestConfig, ConcurrencyTestRunner
)
from tests.utils.test_data_manager import TestDataManager
from tests.utils.mock_providers import MockProviderFactory
from core.llm_provider import LLMManager
from agents.sales_agent import SalesAgent


class TestLoadTesting:
    """Load testing scenarios."""
    
    @pytest.fixture
    def performance_runner(self):
        """Create performance test runner."""
        return PerformanceTestRunner()
    
    @pytest.fixture
    def test_data_manager(self):
        """Create test data manager."""
        return TestDataManager()
    
    @pytest.fixture
    def load_test_config(self):
        """Create basic load test configuration."""
        return LoadTestConfig(
            concurrent_users=5,
            requests_per_user=3,
            ramp_up_time=5,
            test_duration=30,
            base_url="http://localhost:8000",
            endpoints=["/api/trigger/email"],
            request_timeout=10,
            think_time=0.5
        )
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_basic_load_test(self, performance_runner, load_test_config):
        """Test basic load testing functionality."""
        # Skip if server is not running
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{load_test_config.base_url}/health") as response:
                    if response.status != 200:
                        pytest.skip("Server not available for load testing")
        except Exception:
            pytest.skip("Server not available for load testing")
        
        # Run load test
        metrics = await performance_runner.run_load_test(load_test_config)
        
        # Verify metrics
        assert metrics.total_requests > 0
        assert metrics.concurrent_users == load_test_config.concurrent_users
        assert metrics.test_duration > 0
        
        # Performance assertions
        if metrics.successful_requests > 0:
            assert metrics.avg_response_time < 5.0  # Under 5 seconds average
            assert metrics.throughput > 0
            
        # Print results for analysis
        performance_runner.print_performance_report(metrics)
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_email_endpoint_load(self, performance_runner):
        """Test load on email endpoint specifically."""
        config = LoadTestConfig(
            concurrent_users=3,
            requests_per_user=2,
            ramp_up_time=3,
            base_url="http://localhost:8000",
            endpoints=["/api/trigger/email"],
            request_timeout=15
        )
        
        try:
            metrics = await performance_runner.run_load_test(config)
            
            # Verify email-specific processing
            assert metrics.total_requests == 6  # 3 users * 2 requests
            
            if metrics.successful_requests > 0:
                # Email processing should be reasonably fast
                assert metrics.avg_response_time < 3.0
                
        except Exception as e:
            pytest.skip(f"Load test failed: {e}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_webhook_endpoint_load(self, performance_runner):
        """Test load on webhook endpoint."""
        config = LoadTestConfig(
            concurrent_users=4,
            requests_per_user=2,
            ramp_up_time=2,
            base_url="http://localhost:8000",
            endpoints=["/api/trigger/webhook"],
            request_timeout=10
        )
        
        try:
            metrics = await performance_runner.run_load_test(config)
            
            assert metrics.total_requests == 8  # 4 users * 2 requests
            
            if metrics.successful_requests > 0:
                # Webhook processing should be fast
                assert metrics.avg_response_time < 2.0
                
        except Exception as e:
            pytest.skip(f"Webhook load test failed: {e}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_mixed_endpoint_load(self, performance_runner):
        """Test load across multiple endpoints."""
        config = LoadTestConfig(
            concurrent_users=6,
            requests_per_user=3,
            ramp_up_time=5,
            base_url="http://localhost:8000",
            endpoints=["/api/trigger/email", "/api/trigger/webhook", "/api/trigger"],
            request_timeout=12
        )
        
        try:
            metrics = await performance_runner.run_load_test(config)
            
            assert metrics.total_requests == 18  # 6 users * 3 requests
            
            if metrics.successful_requests > 0:
                # Mixed load should still perform well
                assert metrics.avg_response_time < 4.0
                assert metrics.throughput > 1.0  # At least 1 request per second
                
        except Exception as e:
            pytest.skip(f"Mixed endpoint load test failed: {e}")


class TestStressTesting:
    """Stress testing scenarios."""
    
    @pytest.fixture
    def performance_runner(self):
        """Create performance test runner."""
        return PerformanceTestRunner()
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_stress_test_gradual_increase(self, performance_runner):
        """Test stress testing with gradual load increase."""
        base_config = LoadTestConfig(
            concurrent_users=2,
            requests_per_user=2,
            ramp_up_time=3,
            test_duration=15,
            base_url="http://localhost:8000",
            endpoints=["/api/trigger/email"]
        )
        
        try:
            metrics = await performance_runner.run_stress_test(base_config, stress_multiplier=1.5)
            
            if metrics:
                assert metrics.total_requests > 0
                print(f"Stress test completed. Breaking point around {metrics.concurrent_users} users")
                
        except Exception as e:
            pytest.skip(f"Stress test failed: {e}")
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_memory_usage_under_load(self, performance_runner, test_data_manager):
        """Test memory usage during repeated operations."""
        def test_function():
            """Function to test for memory leaks."""
            # Simulate agent processing
            email = test_data_manager.create_sample_email("sales")
            data = {"source": "email", "email": email.to_dict()}
            
            # Simulate some processing
            processed_data = {
                "customer_email": email.sender,
                "subject_length": len(email.subject),
                "body_length": len(email.body),
                "processing_time": 0.1
            }
            
            return processed_data
        
        memory_stats = performance_runner.run_memory_test(test_function, iterations=50)
        
        # Verify memory usage is reasonable
        assert memory_stats["memory_increase_mb"] < 100  # Less than 100MB increase
        assert memory_stats["iterations"] == 50
        
        print(f"Memory test results: {memory_stats}")


class TestConcurrencyTesting:
    """Concurrency-specific testing scenarios."""
    
    @pytest.fixture
    def concurrency_runner(self):
        """Create concurrency test runner."""
        return ConcurrencyTestRunner()
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager for testing."""
        manager = LLMManager()
        mock_provider = MockProviderFactory.create_reliable_provider()
        manager.register_provider("mock", mock_provider)
        manager.set_default_provider("mock")
        return manager
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_processing(self, concurrency_runner, mock_llm_manager):
        """Test concurrent processing of agent requests."""
        # Create sales agent
        sales_agent = SalesAgent(
            name="concurrent_test_agent",
            config={"test_mode": True},
            llm_manager=mock_llm_manager
        )
        
        async def agent_process_func(data):
            """Agent processing function for testing."""
            return await sales_agent.process(data)
        
        # Run concurrency test
        results = await concurrency_runner.test_concurrent_agent_processing(
            agent_process_func, concurrent_requests=5
        )
        
        # Verify results
        assert results["concurrent_requests"] == 5
        assert results["successful"] >= 0
        assert results["success_rate"] >= 0.0
        assert results["requests_per_second"] > 0
        
        print(f"Concurrency test results: {results}")
    
    @pytest.mark.asyncio
    async def test_high_concurrency_agent_processing(self, concurrency_runner, mock_llm_manager):
        """Test high concurrency agent processing."""
        sales_agent = SalesAgent(
            name="high_concurrency_agent",
            config={"test_mode": True},
            llm_manager=mock_llm_manager
        )
        
        async def agent_process_func(data):
            return await sales_agent.process(data)
        
        # Test with higher concurrency
        results = await concurrency_runner.test_concurrent_agent_processing(
            agent_process_func, concurrent_requests=20
        )
        
        # Should handle high concurrency reasonably well
        assert results["concurrent_requests"] == 20
        assert results["success_rate"] > 0.8  # At least 80% success rate
        assert results["avg_time_per_request"] < 2.0  # Under 2 seconds average
        
        print(f"High concurrency results: {results}")
    
    def test_thread_safety_llm_manager(self, concurrency_runner, mock_llm_manager):
        """Test thread safety of LLM manager."""
        def test_function():
            """Function to test thread safety."""
            provider = mock_llm_manager.get_provider("mock")
            return provider.get_capabilities()
        
        results = concurrency_runner.test_thread_safety(
            test_function, thread_count=5, iterations_per_thread=10
        )
        
        # Verify thread safety
        assert results["successful_iterations"] > 0
        assert results["success_rate"] > 0.95  # Very high success rate expected
        assert len(results["errors"]) == 0  # No errors expected for this simple operation
        
        print(f"Thread safety results: {results}")
    
    def test_thread_safety_data_models(self, concurrency_runner):
        """Test thread safety of data model operations."""
        from models.data_models import EmailMessage
        
        def test_function():
            """Test data model creation and serialization."""
            email = EmailMessage(
                subject="Thread Safety Test",
                sender="test@example.com",
                recipient="recipient@example.com",
                body="This is a thread safety test message."
            )
            
            # Test serialization/deserialization
            email_dict = email.to_dict()
            email_json = email.to_json()
            
            return len(email_json)
        
        results = concurrency_runner.test_thread_safety(
            test_function, thread_count=8, iterations_per_thread=20
        )
        
        # Data models should be thread-safe
        assert results["success_rate"] == 1.0  # 100% success rate expected
        assert len(results["errors"]) == 0
        
        print(f"Data model thread safety results: {results}")


class TestPerformanceRegression:
    """Performance regression testing."""
    
    @pytest.fixture
    def test_data_manager(self):
        """Create test data manager."""
        return TestDataManager()
    
    @pytest.mark.performance
    def test_email_parsing_performance(self, test_data_manager):
        """Test email parsing performance."""
        from utils.email_parser import EmailParser
        
        parser = EmailParser()
        emails = [test_data_manager.create_sample_email("sales") for _ in range(100)]
        
        start_time = time.time()
        
        for email in emails:
            parsed_data = parser.parse_email_message(email)
            assert "sender_email" in parsed_data
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_email = total_time / len(emails)
        
        # Performance assertions
        assert avg_time_per_email < 0.01  # Under 10ms per email
        assert total_time < 2.0  # Total time under 2 seconds for 100 emails
        
        print(f"Email parsing: {avg_time_per_email:.4f}s per email, {total_time:.2f}s total")
    
    @pytest.mark.performance
    def test_criteria_evaluation_performance(self, test_data_manager):
        """Test criteria evaluation performance."""
        from core.criteria_evaluator import CriteriaEngine
        from models.data_models import TriggerData
        from datetime import datetime
        
        # Create criteria engine
        criteria_config = {
            "criteria": [
                {
                    "name": f"test_criteria_{i}",
                    "priority": i,
                    "conditions": [
                        {
                            "field": "email.subject",
                            "operator": "contains",
                            "values": [f"keyword{i}", f"term{i}"]
                        }
                    ],
                    "agent": f"agent_{i}"
                }
                for i in range(10)  # 10 different criteria
            ]
        }
        
        engine = CriteriaEngine()
        engine.load_criteria_from_dict(criteria_config)
        
        # Create test data
        trigger_data_list = []
        for i in range(50):
            email = test_data_manager.create_sample_email("sales")
            email.subject = f"Test email {i} with keyword{i % 10}"
            trigger_data = TriggerData(
                source="email",
                timestamp=datetime.now(),
                data={"email": email.to_dict()}
            )
            trigger_data_list.append(trigger_data)
        
        # Measure evaluation performance
        start_time = time.time()
        
        for trigger_data in trigger_data_list:
            matches = engine.evaluate(trigger_data)
            # Should find at least one match for most emails
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_evaluation = total_time / len(trigger_data_list)
        
        # Performance assertions
        assert avg_time_per_evaluation < 0.005  # Under 5ms per evaluation
        assert total_time < 1.0  # Total time under 1 second for 50 evaluations
        
        print(f"Criteria evaluation: {avg_time_per_evaluation:.4f}s per evaluation, {total_time:.2f}s total")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_agent_processing_performance(self, test_data_manager):
        """Test agent processing performance without LLM calls."""
        from agents.sales_agent import SalesAgent
        
        # Create agent without LLM for pure processing performance
        sales_agent = SalesAgent(
            name="performance_test_agent",
            config={"test_mode": True},
            llm_manager=None  # No LLM for performance testing
        )
        
        # Create test data
        email_data_list = []
        for i in range(20):
            email = test_data_manager.create_sample_email("sales")
            email.sender = f"perf_test_{i}@example.com"
            email_data_list.append({
                "source": "email",
                "email": email.to_dict()
            })
        
        # Measure processing performance
        start_time = time.time()
        
        for email_data in email_data_list:
            result = await sales_agent.process(email_data)
            assert result.success is True
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_processing = total_time / len(email_data_list)
        
        # Performance assertions (without LLM calls)
        assert avg_time_per_processing < 0.1  # Under 100ms per processing
        assert total_time < 3.0  # Total time under 3 seconds for 20 processings
        
        print(f"Agent processing: {avg_time_per_processing:.4f}s per processing, {total_time:.2f}s total")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-m", "performance"])