"""Performance testing utilities for load and stress testing."""

import asyncio
import time
import statistics
from dataclasses import dataclass, field
from typing import Dict, Any, List, Callable, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import json

from .test_data_manager import TestDataManager


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    concurrent_users: int = 10
    requests_per_user: int = 5
    ramp_up_time: int = 10
    test_duration: int = 60
    base_url: str = "http://localhost:8000"
    endpoints: List[str] = field(default_factory=lambda: ["/api/trigger/email"])
    request_timeout: int = 30
    think_time: float = 1.0  # Time between requests per user


@dataclass
class PerformanceMetrics:
    """Performance test results."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = field(default_factory=list)
    error_rates: Dict[str, int] = field(default_factory=dict)
    throughput: float = 0.0  # Requests per second
    avg_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    concurrent_users: int = 0
    test_duration: float = 0.0
    
    def calculate_statistics(self):
        """Calculate statistical metrics from response times."""
        if self.response_times:
            self.avg_response_time = statistics.mean(self.response_times)
            self.min_response_time = min(self.response_times)
            self.max_response_time = max(self.response_times)
            
            sorted_times = sorted(self.response_times)
            n = len(sorted_times)
            self.p95_response_time = sorted_times[int(0.95 * n)] if n > 0 else 0.0
            self.p99_response_time = sorted_times[int(0.99 * n)] if n > 0 else 0.0
        
        if self.test_duration > 0:
            self.throughput = self.successful_requests / self.test_duration


@dataclass
class RequestResult:
    """Result of a single request."""
    success: bool
    response_time: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    response_size: int = 0


class PerformanceTestRunner:
    """Runner for performance and load tests."""
    
    def __init__(self, test_data_manager: Optional[TestDataManager] = None):
        """Initialize performance test runner.
        
        Args:
            test_data_manager: Test data manager for generating test data
        """
        self.test_data_manager = test_data_manager or TestDataManager()
        self.session = None
    
    async def run_load_test(self, config: LoadTestConfig) -> PerformanceMetrics:
        """Run load test with specified configuration.
        
        Args:
            config: Load test configuration
            
        Returns:
            Performance metrics
        """
        print(f"Starting load test: {config.concurrent_users} users, "
              f"{config.requests_per_user} requests each")
        
        metrics = PerformanceMetrics(concurrent_users=config.concurrent_users)
        start_time = time.time()
        
        # Create HTTP session
        connector = aiohttp.TCPConnector(limit=config.concurrent_users * 2)
        timeout = aiohttp.ClientTimeout(total=config.request_timeout)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            self.session = session
            
            # Create user tasks with staggered start times
            user_tasks = []
            for user_id in range(config.concurrent_users):
                start_delay = (user_id * config.ramp_up_time) / config.concurrent_users
                task = asyncio.create_task(
                    self._simulate_user(user_id, config, start_delay)
                )
                user_tasks.append(task)
            
            # Wait for all users to complete
            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            # Aggregate results
            for result in user_results:
                if isinstance(result, Exception):
                    print(f"User task failed: {result}")
                    continue
                
                if isinstance(result, list):
                    for request_result in result:
                        metrics.total_requests += 1
                        if request_result.success:
                            metrics.successful_requests += 1
                            metrics.response_times.append(request_result.response_time)
                        else:
                            metrics.failed_requests += 1
                            error_key = request_result.error_message or "unknown_error"
                            metrics.error_rates[error_key] = metrics.error_rates.get(error_key, 0) + 1
        
        metrics.test_duration = time.time() - start_time
        metrics.calculate_statistics()
        
        return metrics
    
    async def _simulate_user(self, user_id: int, config: LoadTestConfig, 
                           start_delay: float) -> List[RequestResult]:
        """Simulate a single user making requests.
        
        Args:
            user_id: Unique user identifier
            config: Load test configuration
            start_delay: Delay before starting requests
            
        Returns:
            List of request results
        """
        # Wait for staggered start
        if start_delay > 0:
            await asyncio.sleep(start_delay)
        
        results = []
        
        for request_num in range(config.requests_per_user):
            # Select endpoint and generate test data
            endpoint = config.endpoints[request_num % len(config.endpoints)]
            test_data = self._generate_request_data(endpoint, user_id, request_num)
            
            # Make request
            result = await self._make_request(
                f"{config.base_url}{endpoint}",
                test_data
            )
            results.append(result)
            
            # Think time between requests
            if request_num < config.requests_per_user - 1:
                await asyncio.sleep(config.think_time)
        
        return results
    
    def _generate_request_data(self, endpoint: str, user_id: int, request_num: int) -> Dict[str, Any]:
        """Generate test data for a specific endpoint.
        
        Args:
            endpoint: API endpoint
            user_id: User identifier
            request_num: Request number
            
        Returns:
            Request data dictionary
        """
        if "/email" in endpoint:
            email = self.test_data_manager.create_sample_email("sales")
            email.sender = f"loadtest{user_id}_{request_num}@example.com"
            email.subject = f"Load Test {user_id}-{request_num}: {email.subject}"
            return email.to_dict()
        
        elif "/webhook" in endpoint:
            webhook_data = self.test_data_manager.create_webhook_payload("github")
            webhook_data["metadata"]["user_id"] = user_id
            webhook_data["metadata"]["request_num"] = request_num
            return webhook_data
        
        else:
            return {
                "trigger_type": "load_test",
                "data": {
                    "user_id": user_id,
                    "request_num": request_num,
                    "timestamp": time.time()
                }
            }
    
    async def _make_request(self, url: str, data: Dict[str, Any]) -> RequestResult:
        """Make HTTP request and measure performance.
        
        Args:
            url: Request URL
            data: Request data
            
        Returns:
            Request result
        """
        start_time = time.time()
        
        try:
            async with self.session.post(url, json=data) as response:
                response_text = await response.text()
                response_time = time.time() - start_time
                
                return RequestResult(
                    success=response.status == 200,
                    response_time=response_time,
                    status_code=response.status,
                    response_size=len(response_text),
                    error_message=None if response.status == 200 else f"HTTP {response.status}"
                )
        
        except asyncio.TimeoutError:
            return RequestResult(
                success=False,
                response_time=time.time() - start_time,
                error_message="timeout"
            )
        
        except Exception as e:
            return RequestResult(
                success=False,
                response_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def run_stress_test(self, config: LoadTestConfig, 
                            stress_multiplier: float = 2.0) -> PerformanceMetrics:
        """Run stress test by gradually increasing load.
        
        Args:
            config: Base load test configuration
            stress_multiplier: Multiplier for stress testing
            
        Returns:
            Performance metrics at breaking point
        """
        print("Starting stress test...")
        
        current_users = config.concurrent_users
        best_metrics = None
        
        while True:
            stress_config = LoadTestConfig(
                concurrent_users=current_users,
                requests_per_user=config.requests_per_user,
                ramp_up_time=config.ramp_up_time,
                test_duration=config.test_duration // 2,  # Shorter duration for stress test
                base_url=config.base_url,
                endpoints=config.endpoints,
                request_timeout=config.request_timeout,
                think_time=config.think_time
            )
            
            metrics = await self.run_load_test(stress_config)
            
            # Check if system is still performing well
            error_rate = metrics.failed_requests / max(metrics.total_requests, 1)
            avg_response_time = metrics.avg_response_time
            
            print(f"Users: {current_users}, Error Rate: {error_rate:.2%}, "
                  f"Avg Response Time: {avg_response_time:.2f}s")
            
            # Stop if error rate is too high or response time is too slow
            if error_rate > 0.05 or avg_response_time > 5.0:  # 5% error rate or 5s response time
                print(f"Breaking point reached at {current_users} users")
                break
            
            best_metrics = metrics
            current_users = int(current_users * stress_multiplier)
            
            # Safety limit
            if current_users > 1000:
                print("Reached safety limit of 1000 users")
                break
        
        return best_metrics or metrics
    
    def run_memory_test(self, test_function: Callable, iterations: int = 100) -> Dict[str, Any]:
        """Run memory usage test.
        
        Args:
            test_function: Function to test for memory leaks
            iterations: Number of iterations to run
            
        Returns:
            Memory usage statistics
        """
        try:
            import psutil
            import gc
        except ImportError:
            return {"error": "psutil not available for memory testing"}
        
        process = psutil.Process()
        memory_usage = []
        
        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        for i in range(iterations):
            test_function()
            
            if i % 10 == 0:  # Sample every 10 iterations
                gc.collect()
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_usage.append(current_memory)
        
        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            "baseline_memory_mb": baseline_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": final_memory - baseline_memory,
            "peak_memory_mb": max(memory_usage) if memory_usage else final_memory,
            "memory_samples": memory_usage,
            "iterations": iterations
        }
    
    def print_performance_report(self, metrics: PerformanceMetrics):
        """Print formatted performance test report.
        
        Args:
            metrics: Performance metrics to report
        """
        print("\n" + "="*60)
        print("PERFORMANCE TEST REPORT")
        print("="*60)
        print(f"Test Duration: {metrics.test_duration:.2f} seconds")
        print(f"Concurrent Users: {metrics.concurrent_users}")
        print(f"Total Requests: {metrics.total_requests}")
        print(f"Successful Requests: {metrics.successful_requests}")
        print(f"Failed Requests: {metrics.failed_requests}")
        print(f"Success Rate: {(metrics.successful_requests/max(metrics.total_requests,1))*100:.2f}%")
        print(f"Throughput: {metrics.throughput:.2f} requests/second")
        print()
        print("Response Time Statistics:")
        print(f"  Average: {metrics.avg_response_time:.3f}s")
        print(f"  Minimum: {metrics.min_response_time:.3f}s")
        print(f"  Maximum: {metrics.max_response_time:.3f}s")
        print(f"  95th Percentile: {metrics.p95_response_time:.3f}s")
        print(f"  99th Percentile: {metrics.p99_response_time:.3f}s")
        
        if metrics.error_rates:
            print("\nError Breakdown:")
            for error, count in metrics.error_rates.items():
                print(f"  {error}: {count} ({(count/max(metrics.total_requests,1))*100:.2f}%)")
        
        print("="*60)


class ConcurrencyTestRunner:
    """Runner for concurrency-specific tests."""
    
    def __init__(self, test_data_manager: Optional[TestDataManager] = None):
        """Initialize concurrency test runner."""
        self.test_data_manager = test_data_manager or TestDataManager()
    
    async def test_concurrent_agent_processing(self, 
                                             agent_process_func: Callable,
                                             concurrent_requests: int = 10) -> Dict[str, Any]:
        """Test concurrent agent processing.
        
        Args:
            agent_process_func: Agent processing function to test
            concurrent_requests: Number of concurrent requests
            
        Returns:
            Concurrency test results
        """
        test_data = self.test_data_manager.create_concurrent_test_scenarios()[:concurrent_requests]
        
        start_time = time.time()
        
        # Run concurrent processing
        tasks = [agent_process_func(data) for data in test_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        # Analyze results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        processing_time = end_time - start_time
        
        return {
            "concurrent_requests": concurrent_requests,
            "successful": successful,
            "failed": failed,
            "total_time": processing_time,
            "avg_time_per_request": processing_time / len(results),
            "requests_per_second": len(results) / processing_time,
            "success_rate": successful / len(results),
            "errors": [str(r) for r in results if isinstance(r, Exception)]
        }
    
    def test_thread_safety(self, test_function: Callable, 
                          thread_count: int = 10, 
                          iterations_per_thread: int = 100) -> Dict[str, Any]:
        """Test thread safety of a function.
        
        Args:
            test_function: Function to test for thread safety
            thread_count: Number of threads to use
            iterations_per_thread: Iterations per thread
            
        Returns:
            Thread safety test results
        """
        results = []
        errors = []
        
        def worker():
            """Worker function for thread testing."""
            thread_results = []
            thread_errors = []
            
            for _ in range(iterations_per_thread):
                try:
                    result = test_function()
                    thread_results.append(result)
                except Exception as e:
                    thread_errors.append(str(e))
            
            return thread_results, thread_errors
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(worker) for _ in range(thread_count)]
            
            for future in futures:
                thread_results, thread_errors = future.result()
                results.extend(thread_results)
                errors.extend(thread_errors)
        
        end_time = time.time()
        
        return {
            "thread_count": thread_count,
            "iterations_per_thread": iterations_per_thread,
            "total_iterations": len(results) + len(errors),
            "successful_iterations": len(results),
            "failed_iterations": len(errors),
            "success_rate": len(results) / (len(results) + len(errors)),
            "total_time": end_time - start_time,
            "errors": errors[:10]  # First 10 errors for analysis
        }