"""Tests for concurrent processing functionality."""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from core.concurrent_processor import (
    ConcurrentProcessor, ConcurrencyConfig, RateLimitConfig, 
    RateLimiter, ConnectionPool, ProcessingMetrics
)
from core.exceptions import RateLimitError, ConcurrencyError, ConnectionPoolError
from models.data_models import TriggerData, AgentResult


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""
        config = RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_limit=10
        )
        return RateLimiter(config)
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_within_limit(self, rate_limiter):
        """Test that rate limiter allows requests within limits."""
        # Should allow up to burst_limit requests immediately
        for i in range(10):
            assert await rate_limiter.acquire() == True
        
        # Next request should be denied (burst limit exceeded)
        assert await rate_limiter.acquire() == False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_refills_tokens(self, rate_limiter):
        """Test that rate limiter refills tokens over time."""
        # Exhaust burst limit
        for i in range(10):
            await rate_limiter.acquire()
        
        # Should be denied
        assert await rate_limiter.acquire() == False
        
        # Wait for token refill (simulate time passing)
        rate_limiter.last_refill = time.time() - 2  # 2 seconds ago
        
        # Should now allow request
        assert await rate_limiter.acquire() == True
    
    @pytest.mark.asyncio
    async def test_rate_limiter_hourly_limit(self, rate_limiter):
        """Test hourly rate limiting."""
        # Simulate many requests in the past hour
        now = time.time()
        rate_limiter.request_times = [now - i for i in range(1000)]
        
        # Should be denied due to hourly limit
        assert await rate_limiter.acquire() == False
    
    def test_rate_limiter_wait_time_calculation(self, rate_limiter):
        """Test wait time calculation."""
        # When tokens are available, wait time should be 0
        assert rate_limiter.get_wait_time() == 0.0
        
        # When blocked, should return positive wait time
        rate_limiter.blocked_until = time.time() + 30
        wait_time = rate_limiter.get_wait_time()
        assert wait_time > 0
        assert wait_time <= 30


class TestConnectionPool:
    """Test connection pool functionality."""
    
    @pytest.fixture
    def connection_factory(self):
        """Mock connection factory."""
        async def factory():
            mock_conn = MagicMock()
            mock_conn.close = AsyncMock()
            return mock_conn
        return factory
    
    @pytest.fixture
    def connection_pool(self, connection_factory):
        """Create a connection pool for testing."""
        return ConnectionPool(connection_factory, max_size=3)
    
    @pytest.mark.asyncio
    async def test_connection_pool_creates_connections(self, connection_pool):
        """Test that connection pool creates connections."""
        async with connection_pool.acquire() as conn:
            assert conn is not None
            assert connection_pool.active_connections == 1
    
    @pytest.mark.asyncio
    async def test_connection_pool_reuses_connections(self, connection_pool):
        """Test that connection pool reuses connections."""
        # Create and return a connection
        async with connection_pool.acquire() as conn1:
            first_conn = conn1
        
        # Next acquisition should reuse the same connection
        async with connection_pool.acquire() as conn2:
            assert conn2 == first_conn
    
    @pytest.mark.asyncio
    async def test_connection_pool_respects_max_size(self, connection_pool):
        """Test that connection pool respects maximum size."""
        connections = []
        
        # Acquire maximum number of connections
        for i in range(3):
            conn = await connection_pool._get_connection()
            connections.append(conn)
        
        assert connection_pool.active_connections == 3
        
        # Return connections
        for conn in connections:
            await connection_pool._return_connection(conn)
    
    @pytest.mark.asyncio
    async def test_connection_pool_expires_idle_connections(self, connection_pool):
        """Test that connection pool expires idle connections."""
        # Create a connection and return it
        async with connection_pool.acquire() as conn:
            pass
        
        # Simulate time passing beyond max_idle_time
        for conn, last_used in connection_pool.pool:
            connection_pool.pool = [(conn, time.time() - 400)]  # 400 seconds ago
        
        # Next acquisition should create a new connection
        async with connection_pool.acquire() as new_conn:
            assert len(connection_pool.pool) == 0  # Old connection should be expired
    
    @pytest.mark.asyncio
    async def test_connection_pool_close_all(self, connection_pool):
        """Test closing all connections in the pool."""
        # Create some connections
        async with connection_pool.acquire() as conn1:
            pass
        async with connection_pool.acquire() as conn2:
            pass
        
        assert len(connection_pool.pool) == 2
        
        # Close all connections
        await connection_pool.close_all()
        
        assert len(connection_pool.pool) == 0
        assert connection_pool.active_connections == 0


class TestConcurrentProcessor:
    """Test concurrent processor functionality."""
    
    @pytest.fixture
    def concurrency_config(self):
        """Create concurrency configuration for testing."""
        return ConcurrencyConfig(
            max_concurrent_requests=5,
            max_concurrent_per_agent=2,
            max_concurrent_per_llm_provider=3,
            request_timeout=1.0,
            enable_request_batching=True
        )
    
    @pytest.fixture
    def rate_limit_config(self):
        """Create rate limit configuration for testing."""
        return RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=1000,
            burst_limit=20
        )
    
    @pytest.fixture
    def concurrent_processor(self, concurrency_config, rate_limit_config):
        """Create concurrent processor for testing."""
        return ConcurrentProcessor(concurrency_config, rate_limit_config)
    
    @pytest.mark.asyncio
    async def test_concurrent_processor_initialization(self, concurrent_processor):
        """Test concurrent processor initialization."""
        await concurrent_processor.start()
        
        assert concurrent_processor.global_semaphore._value == 5
        assert len(concurrent_processor._background_tasks) > 0
        
        await concurrent_processor.stop()
    
    @pytest.mark.asyncio
    async def test_process_request_success(self, concurrent_processor):
        """Test successful request processing."""
        await concurrent_processor.start()
        
        async def mock_processor(data):
            await asyncio.sleep(0.1)
            return {"result": "success", "data": data}
        
        try:
            result = await concurrent_processor.process_request(
                request_id="test-1",
                agent_name="test_agent",
                processor_func=mock_processor,
                "test_data"
            )
            
            assert result["result"] == "success"
            assert result["data"] == "test_data"
            
            # Check metrics
            metrics = concurrent_processor.get_metrics()
            assert metrics.successful_requests == 1
            assert metrics.total_requests == 1
            
        finally:
            await concurrent_processor.stop()
    
    @pytest.mark.asyncio
    async def test_process_request_timeout(self, concurrent_processor):
        """Test request timeout handling."""
        await concurrent_processor.start()
        
        async def slow_processor(data):
            await asyncio.sleep(2.0)  # Longer than timeout
            return {"result": "success"}
        
        try:
            with pytest.raises(ConcurrencyError, match="timed out"):
                await concurrent_processor.process_request(
                    request_id="test-timeout",
                    agent_name="test_agent",
                    processor_func=slow_processor,
                    "test_data"
                )
            
            # Check metrics
            metrics = concurrent_processor.get_metrics()
            assert metrics.timeout_errors == 1
            assert metrics.failed_requests == 1
            
        finally:
            await concurrent_processor.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_request_limiting(self, concurrent_processor):
        """Test concurrent request limiting."""
        await concurrent_processor.start()
        
        async def slow_processor(data):
            await asyncio.sleep(0.5)
            return {"result": "success", "data": data}
        
        try:
            # Start more requests than the limit
            tasks = []
            for i in range(10):
                task = asyncio.create_task(
                    concurrent_processor.process_request(
                        request_id=f"test-{i}",
                        agent_name="test_agent",
                        processor_func=slow_processor,
                        f"data-{i}"
                    )
                )
                tasks.append(task)
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed (they'll be queued and processed)
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == 10
            
            # Check metrics
            metrics = concurrent_processor.get_metrics()
            assert metrics.successful_requests == 10
            assert metrics.peak_concurrent_requests <= 5  # Should respect limit
            
        finally:
            await concurrent_processor.stop()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, concurrent_processor):
        """Test rate limiting functionality."""
        # Create a very restrictive rate limiter
        restrictive_config = RateLimitConfig(
            requests_per_minute=2,
            burst_limit=1
        )
        processor = ConcurrentProcessor(
            concurrent_processor.config,
            restrictive_config
        )
        
        await processor.start()
        
        async def quick_processor(data):
            return {"result": "success"}
        
        try:
            # First request should succeed
            result1 = await processor.process_request(
                request_id="test-1",
                agent_name="test_agent",
                processor_func=quick_processor,
                "data1"
            )
            assert result1["result"] == "success"
            
            # Second request should be rate limited
            with pytest.raises(RateLimitError):
                await processor.process_request(
                    request_id="test-2",
                    agent_name="test_agent",
                    processor_func=quick_processor,
                    "data2"
                )
            
            # Check metrics
            metrics = processor.get_metrics()
            assert metrics.rate_limit_hits == 1
            
        finally:
            await processor.stop()
    
    @pytest.mark.asyncio
    async def test_llm_request_processing(self, concurrent_processor):
        """Test LLM-specific request processing."""
        await concurrent_processor.start()
        
        async def mock_llm_processor(prompt):
            await asyncio.sleep(0.1)
            return {"response": f"Generated response for: {prompt}"}
        
        try:
            result = await concurrent_processor.process_llm_request(
                request_id="llm-test-1",
                provider_name="openai",
                processor_func=mock_llm_processor,
                "Test prompt"
            )
            
            assert "Generated response for: Test prompt" in result["response"]
            
        finally:
            await concurrent_processor.stop()
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, concurrent_processor):
        """Test batch processing functionality."""
        await concurrent_processor.start()
        
        async def batch_processor(funcs):
            results = []
            for func in funcs:
                result = await func()
                results.append(result)
            return results
        
        async def make_request(data):
            return {"processed": data}
        
        try:
            requests = [
                ("req-1", lambda: make_request("data1")),
                ("req-2", lambda: make_request("data2")),
                ("req-3", lambda: make_request("data3"))
            ]
            
            results = await concurrent_processor.batch_process(requests, batch_processor)
            
            assert len(results) == 3
            assert results[0]["processed"] == "data1"
            assert results[1]["processed"] == "data2"
            assert results[2]["processed"] == "data3"
            
        finally:
            await concurrent_processor.stop()
    
    @pytest.mark.asyncio
    async def test_connection_pool_integration(self, concurrent_processor):
        """Test connection pool integration."""
        await concurrent_processor.start()
        
        async def connection_factory():
            mock_conn = MagicMock()
            mock_conn.close = AsyncMock()
            return mock_conn
        
        try:
            # Get connection pool
            pool = concurrent_processor.get_connection_pool(
                "test_pool",
                connection_factory,
                max_size=2
            )
            
            # Use connection pool
            async with pool.acquire() as conn:
                assert conn is not None
            
            # Check pool status
            status = concurrent_processor.get_status()
            assert "test_pool" in status["connection_pools"]
            assert status["connection_pools"]["test_pool"]["max_size"] == 2
            
        finally:
            await concurrent_processor.stop()
    
    def test_metrics_tracking(self, concurrent_processor):
        """Test metrics tracking functionality."""
        metrics = concurrent_processor.get_metrics()
        
        assert isinstance(metrics, ProcessingMetrics)
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.average_response_time == 0.0
    
    def test_status_reporting(self, concurrent_processor):
        """Test status reporting functionality."""
        status = concurrent_processor.get_status()
        
        assert "active_requests" in status
        assert "queued_requests" in status
        assert "total_requests" in status
        assert "success_rate" in status
        assert "average_response_time" in status
        assert "connection_pools" in status
        
        # Success rate should be 0 when no requests processed
        assert status["success_rate"] == 0.0


class TestPerformanceScenarios:
    """Test performance scenarios for concurrent processing."""
    
    @pytest.fixture
    def high_performance_config(self):
        """Configuration for high-performance testing."""
        return ConcurrencyConfig(
            max_concurrent_requests=50,
            max_concurrent_per_agent=10,
            max_concurrent_per_llm_provider=20,
            request_timeout=5.0,
            enable_request_batching=True,
            batch_size=10
        )
    
    @pytest.fixture
    def high_performance_processor(self, high_performance_config):
        """High-performance concurrent processor."""
        rate_config = RateLimitConfig(
            requests_per_minute=1000,
            requests_per_hour=10000,
            burst_limit=100
        )
        return ConcurrentProcessor(high_performance_config, rate_config)
    
    @pytest.mark.asyncio
    async def test_high_concurrency_load(self, high_performance_processor):
        """Test handling high concurrent load."""
        await high_performance_processor.start()
        
        async def fast_processor(data):
            await asyncio.sleep(0.01)  # Very fast processing
            return {"processed": data, "timestamp": time.time()}
        
        try:
            # Create 100 concurrent requests
            tasks = []
            start_time = time.time()
            
            for i in range(100):
                task = asyncio.create_task(
                    high_performance_processor.process_request(
                        request_id=f"load-test-{i}",
                        agent_name=f"agent-{i % 5}",  # 5 different agents
                        processor_func=fast_processor,
                        f"data-{i}"
                    )
                )
                tasks.append(task)
            
            # Wait for all requests to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Verify results
            successful_results = [r for r in results if not isinstance(r, Exception)]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            print(f"Processed {len(successful_results)} requests in {end_time - start_time:.2f}s")
            print(f"Failed requests: {len(failed_results)}")
            
            # Should process most requests successfully
            assert len(successful_results) >= 95  # Allow for some failures
            
            # Check metrics
            metrics = high_performance_processor.get_metrics()
            assert metrics.total_requests == 100
            assert metrics.successful_requests >= 95
            
            # Performance should be reasonable (less than 10 seconds for 100 requests)
            assert end_time - start_time < 10.0
            
        finally:
            await high_performance_processor.stop()
    
    @pytest.mark.asyncio
    async def test_mixed_workload_performance(self, high_performance_processor):
        """Test performance with mixed fast and slow requests."""
        await high_performance_processor.start()
        
        async def fast_processor(data):
            await asyncio.sleep(0.01)
            return {"type": "fast", "data": data}
        
        async def slow_processor(data):
            await asyncio.sleep(0.1)
            return {"type": "slow", "data": data}
        
        try:
            tasks = []
            start_time = time.time()
            
            # Mix of fast and slow requests
            for i in range(50):
                if i % 3 == 0:  # Every 3rd request is slow
                    processor_func = slow_processor
                else:
                    processor_func = fast_processor
                
                task = asyncio.create_task(
                    high_performance_processor.process_request(
                        request_id=f"mixed-{i}",
                        agent_name="mixed_agent",
                        processor_func=processor_func,
                        f"data-{i}"
                    )
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful_results = [r for r in results if not isinstance(r, Exception)]
            fast_results = [r for r in successful_results if r.get("type") == "fast"]
            slow_results = [r for r in successful_results if r.get("type") == "slow"]
            
            print(f"Mixed workload: {len(fast_results)} fast, {len(slow_results)} slow")
            print(f"Total time: {end_time - start_time:.2f}s")
            
            assert len(successful_results) >= 48  # Allow for some failures
            assert len(fast_results) >= 30  # Should have processed fast requests
            assert len(slow_results) >= 15   # Should have processed slow requests
            
        finally:
            await high_performance_processor.stop()
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, high_performance_processor):
        """Test memory usage doesn't grow excessively under load."""
        import psutil
        import os
        
        await high_performance_processor.start()
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        async def memory_test_processor(data):
            # Create some temporary data
            temp_data = [i for i in range(1000)]
            await asyncio.sleep(0.01)
            return {"processed": len(temp_data)}
        
        try:
            # Process many requests in batches
            for batch in range(5):
                tasks = []
                for i in range(20):
                    task = asyncio.create_task(
                        high_performance_processor.process_request(
                            request_id=f"memory-{batch}-{i}",
                            agent_name="memory_agent",
                            processor_func=memory_test_processor,
                            f"data-{batch}-{i}"
                        )
                    )
                    tasks.append(task)
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check memory usage
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_growth = current_memory - initial_memory
                
                print(f"Batch {batch}: Memory usage {current_memory:.1f}MB (+{memory_growth:.1f}MB)")
                
                # Memory growth should be reasonable (less than 100MB)
                assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.1f}MB"
            
        finally:
            await high_performance_processor.stop()


@pytest.mark.asyncio
async def test_concurrent_processor_integration():
    """Integration test for concurrent processor with real components."""
    from core.concurrent_processor import get_concurrent_processor, initialize_concurrent_processor
    
    # Initialize with test configuration
    config = ConcurrencyConfig(max_concurrent_requests=10)
    rate_config = RateLimitConfig(requests_per_minute=100)
    
    await initialize_concurrent_processor(config, rate_config)
    
    processor = get_concurrent_processor()
    
    async def test_agent_processor(input_data):
        await asyncio.sleep(0.1)
        return AgentResult(
            success=True,
            output={"processed": input_data},
            agent_name="test_agent"
        )
    
    # Test processing
    result = await processor.process_request(
        request_id="integration-test",
        agent_name="test_agent",
        processor_func=test_agent_processor,
        {"test": "data"}
    )
    
    assert result.success == True
    assert result.output["processed"]["test"] == "data"
    
    # Check status
    status = processor.get_status()
    assert status["total_requests"] >= 1
    assert status["success_rate"] > 0
    
    # Cleanup
    from core.concurrent_processor import shutdown_concurrent_processor
    await shutdown_concurrent_processor()


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])