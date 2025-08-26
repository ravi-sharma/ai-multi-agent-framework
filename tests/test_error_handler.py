"""Unit tests for the error handling system."""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch

from utils.error_handler import (
    ErrorHandler,
    ErrorCategory,
    ErrorContext,
    ErrorResponse,
    RetryConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    error_handler
)
from utils.exceptions import (
    LLMAPIError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMTimeoutError,
    AgentProcessingError,
    ConfigurationError,
    WorkflowRetryError
)


class TestErrorHandler:
    """Test cases for ErrorHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
        self.context = ErrorContext(
            operation="test_operation",
            component="test_component",
            user_id="test_user",
            request_id="test_request"
        )
    
    def test_categorize_error_rate_limit(self):
        """Test error categorization for rate limit errors."""
        error = LLMRateLimitError("Rate limit exceeded")
        category = self.error_handler.categorize_error(error)
        assert category == ErrorCategory.RATE_LIMIT
    
    def test_categorize_error_authentication(self):
        """Test error categorization for authentication errors."""
        error = LLMAuthenticationError("Invalid API key")
        category = self.error_handler.categorize_error(error)
        assert category == ErrorCategory.AUTHENTICATION
    
    def test_categorize_error_timeout(self):
        """Test error categorization for timeout errors."""
        error = LLMTimeoutError("Request timeout")
        category = self.error_handler.categorize_error(error)
        assert category == ErrorCategory.TIMEOUT
    
    def test_categorize_error_network(self):
        """Test error categorization for network errors."""
        error = ConnectionError("Network connection failed")
        category = self.error_handler.categorize_error(error)
        assert category == ErrorCategory.NETWORK
    
    def test_categorize_error_configuration(self):
        """Test error categorization for configuration errors."""
        error = ConfigurationError("Invalid configuration")
        category = self.error_handler.categorize_error(error)
        assert category == ErrorCategory.CONFIGURATION
    
    def test_categorize_error_processing(self):
        """Test error categorization for processing errors."""
        error = AgentProcessingError("Agent processing failed")
        category = self.error_handler.categorize_error(error)
        assert category == ErrorCategory.PROCESSING
    
    def test_categorize_error_validation(self):
        """Test error categorization for validation errors."""
        error = ValueError("Invalid input value")
        category = self.error_handler.categorize_error(error)
        assert category == ErrorCategory.VALIDATION
    
    def test_categorize_error_unknown(self):
        """Test error categorization for unknown errors."""
        error = RuntimeError("Unknown error")
        category = self.error_handler.categorize_error(error)
        assert category == ErrorCategory.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_handle_error_basic(self):
        """Test basic error handling."""
        error = LLMAPIError("API error")
        response = await self.error_handler.handle_error(error, self.context)
        
        assert not response.success
        assert response.error_code == "NETWORK_LLMAPIERROR"
        assert response.error_message == "API error"
        assert response.error_category == ErrorCategory.NETWORK
        assert response.metadata["component"] == "test_component"
        assert response.metadata["operation"] == "test_operation"
    
    @pytest.mark.asyncio
    async def test_handle_error_with_fallback(self):
        """Test error handling with fallback response."""
        error = LLMRateLimitError("Rate limit exceeded")
        response = await self.error_handler.handle_error(error, self.context, use_fallback=True)
        
        assert not response.success
        assert response.fallback_used
        assert "fallback_result" in response.metadata
        assert response.metadata["fallback_result"]["suggested_action"] == "retry_with_backoff"
    
    @pytest.mark.asyncio
    async def test_handle_error_without_fallback(self):
        """Test error handling without fallback response."""
        error = LLMRateLimitError("Rate limit exceeded")
        response = await self.error_handler.handle_error(error, self.context, use_fallback=False)
        
        assert not response.success
        assert not response.fallback_used
        assert "fallback_result" not in response.metadata
    
    def test_register_circuit_breaker(self):
        """Test circuit breaker registration."""
        config = CircuitBreakerConfig(name="test_breaker")
        breaker = self.error_handler.register_circuit_breaker("test_breaker", config)
        
        assert isinstance(breaker, CircuitBreaker)
        assert self.error_handler.get_circuit_breaker("test_breaker") is breaker
    
    def test_get_error_statistics(self):
        """Test error statistics retrieval."""
        # Simulate some errors
        self.error_handler.error_counts["test_component:rate_limit"] = 5
        self.error_handler.error_counts["test_component:timeout"] = 3
        
        stats = self.error_handler.get_error_statistics()
        
        assert stats["total_errors"] == 8
        assert stats["error_counts"]["test_component:rate_limit"] == 5
        assert stats["error_counts"]["test_component:timeout"] == 3
    
    def test_reset_statistics(self):
        """Test error statistics reset."""
        # Add some error counts
        self.error_handler.error_counts["test_error"] = 10
        
        # Reset statistics
        self.error_handler.reset_statistics()
        
        assert len(self.error_handler.error_counts) == 0


class TestCircuitBreaker:
    """Test cases for CircuitBreaker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(
            name="test_breaker",
            failure_threshold=3,
            recovery_timeout=1.0,
            expected_exception=Exception
        )
        self.circuit_breaker = CircuitBreaker(self.config)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        async def success_func():
            return "success"
        
        result = await self.circuit_breaker.call(success_func)
        assert result == "success"
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_counting(self):
        """Test circuit breaker failure counting."""
        async def failing_func():
            raise Exception("Test failure")
        
        # Fail multiple times to trigger circuit breaker
        for i in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(failing_func)
        
        # Circuit breaker should now be open
        assert self.circuit_breaker.state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(self):
        """Test circuit breaker in open state."""
        # Force circuit breaker to open state
        self.circuit_breaker.state = CircuitBreakerState.OPEN
        self.circuit_breaker.last_failure_time = time.time()
        
        async def any_func():
            return "should not execute"
        
        # Should raise circuit breaker error
        with pytest.raises(LLMAPIError) as exc_info:
            await self.circuit_breaker.call(any_func)
        
        assert "Circuit breaker" in str(exc_info.value)
        assert "OPEN" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery from open to closed state."""
        # Force circuit breaker to open state
        self.circuit_breaker.state = CircuitBreakerState.OPEN
        self.circuit_breaker.last_failure_time = time.time() - 2.0  # Past recovery timeout
        
        async def success_func():
            return "success"
        
        # First call should move to half-open
        result = await self.circuit_breaker.call(success_func)
        assert result == "success"
        assert self.circuit_breaker.state == CircuitBreakerState.HALF_OPEN
        
        # Additional successful calls should close the circuit
        for _ in range(2):  # Need 3 total successes
            await self.circuit_breaker.call(success_func)
        
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED
    
    def test_circuit_breaker_get_state(self):
        """Test circuit breaker state retrieval."""
        state = self.circuit_breaker.get_state()
        
        assert state["name"] == "test_breaker"
        assert state["state"] == CircuitBreakerState.CLOSED.value
        assert state["failure_count"] == 0
        assert "last_failure_time" in state
        assert "success_count" in state


class TestRetryDecorator:
    """Test cases for retry decorator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
        self.call_count = 0
    
    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test retry decorator with success on first attempt."""
        @self.error_handler.with_retry(RetryConfig(max_attempts=3))
        async def success_func():
            return "success"
        
        result = await success_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test retry decorator with success after initial failures."""
        @self.error_handler.with_retry(RetryConfig(max_attempts=3, base_delay=0.1))
        async def eventually_success_func():
            self.call_count += 1
            if self.call_count < 3:
                raise LLMAPIError("Temporary failure")
            return "success"
        
        result = await eventually_success_func()
        assert result == "success"
        assert self.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self):
        """Test retry decorator when max attempts are exceeded."""
        @self.error_handler.with_retry(RetryConfig(max_attempts=2, base_delay=0.1))
        async def always_fail_func():
            raise LLMAPIError("Persistent failure")
        
        with pytest.raises(WorkflowRetryError) as exc_info:
            await always_fail_func()
        
        assert "failed after 2 attempts" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_retry_non_retryable_exception(self):
        """Test retry decorator with non-retryable exception."""
        @self.error_handler.with_retry(RetryConfig(
            max_attempts=3,
            retryable_exceptions=[LLMAPIError]
        ))
        async def non_retryable_func():
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError):
            await non_retryable_func()
    
    def test_retry_sync_function(self):
        """Test retry decorator with synchronous function."""
        @self.error_handler.with_retry(RetryConfig(max_attempts=3, base_delay=0.1))
        def sync_eventually_success_func():
            self.call_count += 1
            if self.call_count < 2:
                raise LLMAPIError("Temporary failure")
            return "sync_success"
        
        result = sync_eventually_success_func()
        assert result == "sync_success"
        assert self.call_count >= 2


class TestCircuitBreakerDecorator:
    """Test cases for circuit breaker decorator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator_success(self):
        """Test circuit breaker decorator with successful calls."""
        @self.error_handler.with_circuit_breaker("test_cb", CircuitBreakerConfig(name="test_cb"))
        async def success_func():
            return "success"
        
        result = await success_func()
        assert result == "success"
        
        # Verify circuit breaker was registered
        cb = self.error_handler.get_circuit_breaker("test_cb")
        assert cb is not None
        assert cb.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator_failure(self):
        """Test circuit breaker decorator with failures."""
        config = CircuitBreakerConfig(name="test_cb_fail", failure_threshold=2)
        
        @self.error_handler.with_circuit_breaker("test_cb_fail", config)
        async def failing_func():
            raise Exception("Test failure")
        
        # Fail enough times to open circuit breaker
        for _ in range(2):
            with pytest.raises(Exception):
                await failing_func()
        
        # Next call should be blocked by circuit breaker
        with pytest.raises(LLMAPIError) as exc_info:
            await failing_func()
        
        assert "Circuit breaker" in str(exc_info.value)


class TestFallbackHandlers:
    """Test cases for fallback handlers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
        self.context = ErrorContext(operation="test", component="test")
    
    @pytest.mark.asyncio
    async def test_rate_limit_fallback(self):
        """Test rate limit fallback handler."""
        error = LLMRateLimitError("Rate limit exceeded")
        error.retry_after = 120
        
        result = await self.error_handler._rate_limit_fallback(error, self.context)
        
        assert result["suggested_action"] == "retry_with_backoff"
        assert result["retry_after"] == 120
    
    @pytest.mark.asyncio
    async def test_timeout_fallback(self):
        """Test timeout fallback handler."""
        error = LLMTimeoutError("Request timeout")
        
        result = await self.error_handler._timeout_fallback(error, self.context)
        
        assert result["suggested_action"] == "retry_with_shorter_timeout"
        assert "timeout" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_auth_fallback(self):
        """Test authentication fallback handler."""
        error = LLMAuthenticationError("Invalid API key")
        
        result = await self.error_handler._auth_fallback(error, self.context)
        
        assert result["suggested_action"] == "check_credentials"
        assert "authentication" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_network_fallback(self):
        """Test network fallback handler."""
        error = ConnectionError("Network error")
        
        result = await self.error_handler._network_fallback(error, self.context)
        
        assert result["suggested_action"] == "check_network"
        assert "network" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_processing_fallback(self):
        """Test processing fallback handler."""
        error = AgentProcessingError("Processing failed")
        
        result = await self.error_handler._processing_fallback(error, self.context)
        
        assert result["suggested_action"] == "validate_input"
        assert "processing" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_config_fallback(self):
        """Test configuration fallback handler."""
        error = ConfigurationError("Config error")
        
        result = await self.error_handler._config_fallback(error, self.context)
        
        assert result["suggested_action"] == "check_configuration"
        assert "configuration" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_validation_fallback(self):
        """Test validation fallback handler."""
        error = ValueError("Invalid value")
        
        result = await self.error_handler._validation_fallback(error, self.context)
        
        assert result["suggested_action"] == "validate_input"
        assert "validation" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_system_fallback(self):
        """Test system fallback handler."""
        error = SystemError("System error")
        
        result = await self.error_handler._system_fallback(error, self.context)
        
        assert result["suggested_action"] == "contact_support"
        assert "system" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_unknown_fallback(self):
        """Test unknown fallback handler."""
        error = RuntimeError("Unknown error")
        
        result = await self.error_handler._unknown_fallback(error, self.context)
        
        assert result["suggested_action"] == "retry_or_contact_support"
        assert "unexpected" in result["message"].lower()


class TestIntegration:
    """Integration tests for error handling system."""
    
    @pytest.mark.asyncio
    async def test_combined_retry_and_circuit_breaker(self):
        """Test combination of retry logic and circuit breaker."""
        error_handler_instance = ErrorHandler()
        call_count = 0
        
        @error_handler_instance.with_circuit_breaker(
            "integration_test",
            CircuitBreakerConfig(name="integration_test", failure_threshold=10)
        )
        @error_handler_instance.with_retry(RetryConfig(max_attempts=5, base_delay=0.01))
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LLMAPIError("Temporary failure")
            return "success"
        
        result = await flaky_function()
        assert result == "success"
        assert call_count == 3  # Should succeed on third attempt
    
    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self):
        """Test error statistics tracking across multiple operations."""
        error_handler_instance = ErrorHandler()
        context1 = ErrorContext(operation="op1", component="comp1")
        context2 = ErrorContext(operation="op2", component="comp2")
        
        # Generate some errors
        await error_handler_instance.handle_error(LLMRateLimitError("Rate limit"), context1)
        await error_handler_instance.handle_error(LLMTimeoutError("Timeout"), context1)
        await error_handler_instance.handle_error(LLMAPIError("API error"), context2)
        
        stats = error_handler_instance.get_error_statistics()
        
        assert stats["total_errors"] == 3
        assert "comp1:rate_limit" in stats["error_counts"]
        assert "comp1:timeout" in stats["error_counts"]
        assert "comp2:network" in stats["error_counts"]


if __name__ == "__main__":
    pytest.main([__file__])