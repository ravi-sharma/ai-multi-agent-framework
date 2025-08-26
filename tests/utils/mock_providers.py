"""Mock LLM providers for testing purposes."""

import asyncio
import json
import random
from typing import Dict, Any, List, Optional
from unittest.mock import Mock

from utils.llm_provider import LLMProvider, LLMResponse
from utils.exceptions import LLMAPIError, LLMConfigurationError


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing that simulates real provider behavior."""
    
    def __init__(self, config: Dict[str, Any], 
                 response_delay: float = 0.1,
                 failure_rate: float = 0.0):
        """Initialize mock provider.
        
        Args:
            config: Provider configuration
            response_delay: Simulated response delay in seconds
            failure_rate: Probability of failure (0.0 to 1.0)
        """
        super().__init__(config)
        self.response_delay = response_delay
        self.failure_rate = failure_rate
        self.call_count = 0
        self.call_history = []
        self.custom_responses = {}
        
        # Default response templates
        self.response_templates = {
            "customer_extraction": {
                "company_name": "Test Company",
                "industry": "Technology", 
                "company_size": "medium",
                "urgency_indicators": ["urgent", "asap"],
                "customer_name": "John Doe"
            },
            "intent_analysis": {
                "primary_intent": "purchase",
                "urgency_level": "high",
                "customer_problems": ["need pricing information"],
                "confidence_score": 0.85
            },
            "sales_notes": {
                "customer_problem": "Customer needs pricing for premium package",
                "proposed_solution": "Provide detailed pricing and schedule demo",
                "urgency_level": "high",
                "follow_up_required": True,
                "estimated_value": 25000,
                "next_steps": ["Send pricing", "Schedule call"]
            },
            "support_analysis": {
                "issue_category": "technical",
                "priority": "medium",
                "resolution_steps": ["Check logs", "Restart service", "Contact user"],
                "estimated_resolution_time": "2 hours"
            },
            "default": {
                "response": "This is a mock response",
                "confidence": 0.8,
                "processing_time": 0.1
            }
        }
    
    async def _create_connection(self):
        """Create connection (not needed for mock)."""
        return Mock()  # Return a mock connection object
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate mock response based on prompt content."""
        self.call_count += 1
        
        # Record call for analysis
        call_record = {
            "prompt": prompt,
            "kwargs": kwargs,
            "timestamp": asyncio.get_event_loop().time()
        }
        self.call_history.append(call_record)
        
        # Simulate processing delay
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        # Simulate random failures
        if random.random() < self.failure_rate:
            raise LLMAPIError(f"Mock provider failure (call #{self.call_count})", provider="mock")
        
        # Check for custom responses first
        for pattern, response in self.custom_responses.items():
            if pattern.lower() in prompt.lower():
                return self._create_response(response)
        
        # Generate response based on prompt content
        response_content = self._generate_contextual_response(prompt)
        
        return self._create_response(response_content)
    
    def _generate_contextual_response(self, prompt: str) -> str:
        """Generate contextual response based on prompt content."""
        prompt_lower = prompt.lower()
        
        # Customer extraction prompts
        if "extract customer" in prompt_lower or "company information" in prompt_lower:
            template = self.response_templates["customer_extraction"].copy()
            # Vary response based on prompt content
            if "acme" in prompt_lower:
                template["company_name"] = "Acme Corporation"
                template["industry"] = "Manufacturing"
            elif "tech" in prompt_lower:
                template["company_name"] = "TechStart Inc"
                template["industry"] = "Software"
            return json.dumps(template)
        
        # Intent analysis prompts
        elif "analyze intent" in prompt_lower or "customer intent" in prompt_lower:
            template = self.response_templates["intent_analysis"].copy()
            if "pricing" in prompt_lower:
                template["primary_intent"] = "pricing"
                template["customer_problems"] = ["need pricing information"]
            elif "demo" in prompt_lower:
                template["primary_intent"] = "demo"
                template["customer_problems"] = ["want to see product demo"]
            elif "support" in prompt_lower:
                template["primary_intent"] = "support"
                template["customer_problems"] = ["technical issue"]
            return json.dumps(template)
        
        # Sales notes generation
        elif "generate sales notes" in prompt_lower or "sales summary" in prompt_lower:
            template = self.response_templates["sales_notes"].copy()
            if "urgent" in prompt_lower:
                template["urgency_level"] = "high"
                template["estimated_value"] = 50000
            elif "demo" in prompt_lower:
                template["proposed_solution"] = "Schedule product demonstration"
                template["next_steps"] = ["Schedule demo", "Prepare demo environment"]
            return json.dumps(template)
        
        # Support analysis
        elif "support" in prompt_lower or "technical issue" in prompt_lower:
            template = self.response_templates["support_analysis"].copy()
            if "critical" in prompt_lower or "urgent" in prompt_lower:
                template["priority"] = "high"
                template["estimated_resolution_time"] = "1 hour"
            return json.dumps(template)
        
        # Default response
        else:
            return json.dumps(self.response_templates["default"])
    
    def _create_response(self, content: str) -> LLMResponse:
        """Create LLMResponse object."""
        if isinstance(content, dict):
            content = json.dumps(content)
        
        return LLMResponse(
            content=content,
            usage={
                "prompt_tokens": len(content.split()) * 2,  # Rough estimate
                "completion_tokens": len(content.split()),
                "total_tokens": len(content.split()) * 3
            },
            model=self.config.get("model", "mock-model"),
            provider="mock",
            metadata={
                "call_count": self.call_count,
                "response_delay": self.response_delay
            }
        )
    
    def get_capabilities(self) -> List[str]:
        """Return mock capabilities."""
        return [
            "text_generation",
            "json_output", 
            "structured_analysis",
            "chat_completion"
        ]
    
    def validate_config(self) -> bool:
        """Validate mock configuration."""
        return "api_key" in self.config or self.config.get("mock_mode", False)
    
    def set_custom_response(self, pattern: str, response: str):
        """Set custom response for specific prompt patterns.
        
        Args:
            pattern: Text pattern to match in prompts
            response: Response to return when pattern is found
        """
        self.custom_responses[pattern] = response
    
    def clear_custom_responses(self):
        """Clear all custom responses."""
        self.custom_responses.clear()
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all calls made to this provider."""
        return self.call_history.copy()
    
    def reset_stats(self):
        """Reset call count and history."""
        self.call_count = 0
        self.call_history.clear()


class MockFailingLLMProvider(MockLLMProvider):
    """Mock LLM provider that always fails - useful for testing error handling."""
    
    def __init__(self, config: Dict[str, Any], error_message: str = "Mock provider failure"):
        """Initialize failing provider.
        
        Args:
            config: Provider configuration
            error_message: Error message to raise
        """
        super().__init__(config, failure_rate=1.0)
        self.error_message = error_message
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Always raise an error."""
        self.call_count += 1
        await asyncio.sleep(0.01)  # Small delay to simulate network call
        raise LLMAPIError(self.error_message, provider="mock_failing")


class MockSlowLLMProvider(MockLLMProvider):
    """Mock LLM provider with configurable slow responses - useful for timeout testing."""
    
    def __init__(self, config: Dict[str, Any], response_delay: float = 5.0):
        """Initialize slow provider.
        
        Args:
            config: Provider configuration
            response_delay: Response delay in seconds
        """
        super().__init__(config, response_delay=response_delay)


class MockRateLimitedProvider(MockLLMProvider):
    """Mock provider that simulates rate limiting."""
    
    def __init__(self, config: Dict[str, Any], 
                 rate_limit: int = 5,
                 rate_window: float = 60.0):
        """Initialize rate limited provider.
        
        Args:
            config: Provider configuration
            rate_limit: Number of requests allowed per window
            rate_window: Time window in seconds
        """
        super().__init__(config)
        self.rate_limit = rate_limit
        self.rate_window = rate_window
        self.request_times = []
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response with rate limiting."""
        current_time = asyncio.get_event_loop().time()
        
        # Clean old requests outside the window
        self.request_times = [
            t for t in self.request_times 
            if current_time - t < self.rate_window
        ]
        
        # Check rate limit
        if len(self.request_times) >= self.rate_limit:
            raise LLMAPIError(
                f"Rate limit exceeded: {self.rate_limit} requests per {self.rate_window}s",
                provider="mock_rate_limited"
            )
        
        # Record this request
        self.request_times.append(current_time)
        
        return await super().generate(prompt, **kwargs)


class MockProviderFactory:
    """Factory for creating different types of mock providers."""
    
    @staticmethod
    def create_reliable_provider(config: Optional[Dict[str, Any]] = None) -> MockLLMProvider:
        """Create a reliable mock provider with fast responses."""
        if config is None:
            config = {"api_key": "mock-key", "model": "mock-model"}
        return MockLLMProvider(config, response_delay=0.01, failure_rate=0.0)
    
    @staticmethod
    def create_unreliable_provider(config: Optional[Dict[str, Any]] = None,
                                 failure_rate: float = 0.3) -> MockLLMProvider:
        """Create an unreliable mock provider with random failures."""
        if config is None:
            config = {"api_key": "mock-key", "model": "mock-model"}
        return MockLLMProvider(config, response_delay=0.1, failure_rate=failure_rate)
    
    @staticmethod
    def create_slow_provider(config: Optional[Dict[str, Any]] = None,
                           delay: float = 2.0) -> MockSlowLLMProvider:
        """Create a slow mock provider."""
        if config is None:
            config = {"api_key": "mock-key", "model": "mock-model"}
        return MockSlowLLMProvider(config, response_delay=delay)
    
    @staticmethod
    def create_failing_provider(config: Optional[Dict[str, Any]] = None,
                              error_message: str = "Provider unavailable") -> MockFailingLLMProvider:
        """Create a provider that always fails."""
        if config is None:
            config = {"api_key": "mock-key", "model": "mock-model"}
        return MockFailingLLMProvider(config, error_message)
    
    @staticmethod
    def create_rate_limited_provider(config: Optional[Dict[str, Any]] = None,
                                   rate_limit: int = 3) -> MockRateLimitedProvider:
        """Create a rate-limited mock provider."""
        if config is None:
            config = {"api_key": "mock-key", "model": "mock-model"}
        return MockRateLimitedProvider(config, rate_limit=rate_limit)


# Convenience instances for common testing scenarios
reliable_mock_provider = MockProviderFactory.create_reliable_provider()
unreliable_mock_provider = MockProviderFactory.create_unreliable_provider()
slow_mock_provider = MockProviderFactory.create_slow_provider()
failing_mock_provider = MockProviderFactory.create_failing_provider()