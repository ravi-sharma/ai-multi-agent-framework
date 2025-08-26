"""Example demonstrating concurrent processing capabilities."""

import asyncio
import time
import logging
from typing import Dict, Any

from utils.concurrent_processor import (
    ConcurrentProcessor, ConcurrencyConfig, RateLimitConfig,
    initialize_concurrent_processor, get_concurrent_processor
)
from agents.base_agent import BaseAgent
from models.data_models import AgentResult, TriggerData
from models.config_models import WorkflowConfig
from utils.openai_provider import OpenAIProvider
from utils.llm_provider import LLMManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExampleAgent(BaseAgent):
    """Example agent for demonstrating concurrent processing."""
    
    def __init__(self, name: str, processing_time: float = 0.1):
        super().__init__(name)
        self.processing_time = processing_time
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process input data with simulated work."""
        logger.info(f"Agent {self.name} starting processing...")
        
        # Simulate processing time
        await asyncio.sleep(self.processing_time)
        
        # Generate result
        result = {
            "agent": self.name,
            "input_received": input_data,
            "processed_at": time.time(),
            "processing_time": self.processing_time
        }
        
        logger.info(f"Agent {self.name} completed processing")
        
        return AgentResult(
            success=True,
            output=result,
            agent_name=self.name,
            notes=[f"Processed in {self.processing_time}s"]
        )
    
    def get_workflow_config(self) -> WorkflowConfig:
        """Get workflow configuration."""
        return WorkflowConfig(agent_name=self.name)


async def demonstrate_basic_concurrent_processing():
    """Demonstrate basic concurrent processing."""
    print("\n=== Basic Concurrent Processing Demo ===")
    
    # Configure concurrent processing
    config = ConcurrencyConfig(
        max_concurrent_requests=5,
        max_concurrent_per_agent=2,
        request_timeout=10.0
    )
    
    rate_config = RateLimitConfig(
        requests_per_minute=100,
        burst_limit=20
    )
    
    # Initialize processor
    await initialize_concurrent_processor(config, rate_config)
    processor = get_concurrent_processor()
    
    # Create test agents
    fast_agent = ExampleAgent("fast_agent", processing_time=0.1)
    slow_agent = ExampleAgent("slow_agent", processing_time=0.5)
    
    # Process multiple requests concurrently
    tasks = []
    start_time = time.time()
    
    for i in range(10):
        agent = fast_agent if i % 2 == 0 else slow_agent
        
        task = asyncio.create_task(
            agent.process_concurrent(
                input_data={"request_id": i, "data": f"test_data_{i}"},
                request_id=f"demo_request_{i}"
            )
        )
        tasks.append(task)
    
    # Wait for all requests to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    # Analyze results
    successful_results = [r for r in results if isinstance(r, AgentResult) and r.success]
    failed_results = [r for r in results if not (isinstance(r, AgentResult) and r.success)]
    
    print(f"Processed {len(successful_results)} requests successfully")
    print(f"Failed requests: {len(failed_results)}")
    print(f"Total time: {end_time - start_time:.2f}s")
    
    # Show metrics
    metrics = processor.get_metrics()
    print(f"Metrics: {metrics.successful_requests} successful, {metrics.failed_requests} failed")
    print(f"Average response time: {metrics.average_response_time:.3f}s")
    
    return processor


async def demonstrate_rate_limiting():
    """Demonstrate rate limiting functionality."""
    print("\n=== Rate Limiting Demo ===")
    
    # Create a processor with strict rate limits
    config = ConcurrencyConfig(max_concurrent_requests=10)
    rate_config = RateLimitConfig(
        requests_per_minute=5,  # Very low limit for demo
        burst_limit=2
    )
    
    processor = ConcurrentProcessor(config, rate_config)
    await processor.start()
    
    agent = ExampleAgent("rate_limited_agent", processing_time=0.1)
    
    # Try to make many requests quickly
    print("Attempting 8 requests with rate limit of 5/minute, burst 2...")
    
    successful_requests = 0
    rate_limited_requests = 0
    
    for i in range(8):
        try:
            result = await agent.process_concurrent(
                input_data={"request": i},
                request_id=f"rate_test_{i}"
            )
            successful_requests += 1
            print(f"Request {i}: SUCCESS")
        except Exception as e:
            if "rate limit" in str(e).lower():
                rate_limited_requests += 1
                print(f"Request {i}: RATE LIMITED")
            else:
                print(f"Request {i}: ERROR - {e}")
    
    print(f"Results: {successful_requests} successful, {rate_limited_requests} rate limited")
    
    await processor.stop()


async def demonstrate_llm_connection_pooling():
    """Demonstrate LLM provider connection pooling."""
    print("\n=== LLM Connection Pooling Demo ===")
    
    # Note: This requires actual API keys to work fully
    # For demo purposes, we'll simulate the behavior
    
    config = ConcurrencyConfig(
        max_concurrent_requests=10,
        max_concurrent_per_llm_provider=3
    )
    
    await initialize_concurrent_processor(config)
    processor = get_concurrent_processor()
    
    # Create mock LLM provider (would be real in production)
    class MockLLMProvider:
        def __init__(self):
            self.provider_name = "mock_openai"
            self._concurrent_processor = processor
        
        async def generate(self, prompt: str, **kwargs):
            # Simulate LLM API call
            await asyncio.sleep(0.2)
            return {
                "content": f"Mock response to: {prompt}",
                "usage": {"tokens": 50},
                "model": "mock-gpt-3.5",
                "provider": "mock_openai"
            }
        
        async def generate_concurrent(self, prompt: str, request_id: str = None, **kwargs):
            import uuid
            if not request_id:
                request_id = str(uuid.uuid4())
            
            return await processor.process_llm_request(
                request_id=request_id,
                provider_name=self.provider_name,
                processor_func=self.generate,
                prompt=prompt,
                **kwargs
            )
    
    llm_provider = MockLLMProvider()
    
    # Make concurrent LLM requests
    prompts = [
        "What is artificial intelligence?",
        "Explain machine learning",
        "What are neural networks?",
        "How does deep learning work?",
        "What is natural language processing?"
    ]
    
    tasks = []
    start_time = time.time()
    
    for i, prompt in enumerate(prompts):
        task = asyncio.create_task(
            llm_provider.generate_concurrent(
                prompt=prompt,
                request_id=f"llm_request_{i}"
            )
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    successful_results = [r for r in results if not isinstance(r, Exception)]
    print(f"Processed {len(successful_results)} LLM requests in {end_time - start_time:.2f}s")
    
    for i, result in enumerate(successful_results):
        if isinstance(result, dict) and "content" in result:
            print(f"Response {i}: {result['content'][:50]}...")


async def demonstrate_batch_processing():
    """Demonstrate batch processing capabilities."""
    print("\n=== Batch Processing Demo ===")
    
    config = ConcurrencyConfig(
        enable_request_batching=True,
        batch_size=3,
        batch_timeout=1.0
    )
    
    processor = ConcurrentProcessor(config)
    await processor.start()
    
    # Create batch processor function
    async def batch_text_processor(text_list):
        """Process a batch of text inputs."""
        print(f"Processing batch of {len(text_list)} items")
        await asyncio.sleep(0.5)  # Simulate batch processing time
        
        results = []
        for text in text_list:
            results.append({
                "original": text,
                "processed": text.upper(),
                "length": len(text),
                "batch_processed": True
            })
        
        return results
    
    # Create individual request functions
    texts = ["hello world", "batch processing", "concurrent execution", "rate limiting", "connection pooling"]
    
    requests = []
    for i, text in enumerate(texts):
        async def make_request(text=text):
            return text
        
        requests.append((f"batch_req_{i}", make_request))
    
    # Process as batch
    start_time = time.time()
    results = await processor.batch_process(requests, batch_text_processor)
    end_time = time.time()
    
    print(f"Batch processed {len(results)} items in {end_time - start_time:.2f}s")
    for result in results:
        print(f"  {result['original']} -> {result['processed']}")
    
    await processor.stop()


async def demonstrate_performance_monitoring():
    """Demonstrate performance monitoring and metrics."""
    print("\n=== Performance Monitoring Demo ===")
    
    config = ConcurrencyConfig(max_concurrent_requests=8)
    processor = ConcurrentProcessor(config)
    await processor.start()
    
    agent = ExampleAgent("monitored_agent", processing_time=0.1)
    
    # Process requests with some failures
    async def sometimes_failing_processor(input_data):
        if input_data.get("should_fail", False):
            raise Exception("Simulated failure")
        
        await asyncio.sleep(0.1)
        return AgentResult(
            success=True,
            output={"processed": input_data},
            agent_name="monitored_agent"
        )
    
    tasks = []
    for i in range(20):
        # Make every 5th request fail
        should_fail = (i % 5 == 0)
        
        task = asyncio.create_task(
            processor.process_request(
                request_id=f"monitor_test_{i}",
                agent_name="monitored_agent",
                processor_func=sometimes_failing_processor,
                input_data={"request_id": i, "should_fail": should_fail}
            )
        )
        tasks.append(task)
    
    # Process all requests
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Show detailed metrics
    metrics = processor.get_metrics()
    status = processor.get_status()
    
    print("Performance Metrics:")
    print(f"  Total requests: {metrics.total_requests}")
    print(f"  Successful: {metrics.successful_requests}")
    print(f"  Failed: {metrics.failed_requests}")
    print(f"  Success rate: {status['success_rate']:.2%}")
    print(f"  Average response time: {metrics.average_response_time:.3f}s")
    print(f"  Peak concurrent requests: {metrics.peak_concurrent_requests}")
    print(f"  Rate limit hits: {metrics.rate_limit_hits}")
    print(f"  Timeout errors: {metrics.timeout_errors}")
    
    await processor.stop()


async def main():
    """Run all concurrent processing demonstrations."""
    print("AI Agent Framework - Concurrent Processing Examples")
    print("=" * 60)
    
    try:
        # Run demonstrations
        processor = await demonstrate_basic_concurrent_processing()
        await demonstrate_rate_limiting()
        await demonstrate_llm_connection_pooling()
        await demonstrate_batch_processing()
        await demonstrate_performance_monitoring()
        
        print("\n=== Final System Status ===")
        final_status = processor.get_status()
        print(f"Total requests processed: {final_status['total_requests']}")
        print(f"Overall success rate: {final_status['success_rate']:.2%}")
        print(f"Average response time: {final_status['average_response_time']:.3f}s")
        
    except Exception as e:
        logger.error(f"Error in demonstration: {e}", exc_info=True)
    
    finally:
        # Cleanup
        from utils.concurrent_processor import shutdown_concurrent_processor
        await shutdown_concurrent_processor()
        print("\nConcurrent processor shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())