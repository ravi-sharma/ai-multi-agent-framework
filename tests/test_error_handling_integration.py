"""Integration tests for error handling system without complex mocking."""

import pytest
import asyncio
from unittest.mock import Mock, patch

from utils.error_handler import error_handler, ErrorContext
from core.exceptions import (
    LLMAPIError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMTimeoutError,
    AgentProcessingError
)
from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider


class TestErrorHandlingIntegration:
    """Integration tests for error handling system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset error handler state
        error_handler.reset_statistics()
    
    def test_openai_error_categorization(self):
        """Test OpenAI error categorization logic."""
        provider = OpenAIProvider({'api_key': 'test', 'model': 'gpt-3.5-turbo'})
        
        # Test authentication error
        auth_error = Mock()
        auth_error.status_code = 401
        auth_error.__str__ = Mock(return_value="Invalid API key")
        
        categorized = provider._categorize_openai_error(auth_error)
        assert isinstance(categorized, LLMAuthenticationError)
        assert categorized.provider == "openai"
        assert categorized.error_code == "OPENAI_AUTH_ERROR"
        
        # Test rate limit error
        rate_limit_error = Mock()
        rate_limit_error.status_code = 429
        rate_limit_error.retry_after = 60
        rate_limit_error.__str__ = Mock(return_value="Rate limit exceeded")
        
        categorized = provider._categorize_openai_error(rate_limit_error)
        assert isinstance(categorized, LLMRateLimitError)
        assert categorized.provider == "openai"
        assert categorized.error_code == "OPENAI_RATE_LIMIT"
        
        # Test server error
        server_error = Mock()
        server_error.status_code = 500
        server_error.__str__ = Mock(return_value="Internal server error")
        
        categorized = provider._categorize_openai_error(server_error)
        assert isinstance(categorized, LLMAPIError)
        assert categorized.provider == "openai"
        assert categorized.error_code == "OPENAI_SERVER_ERROR"
        
        # Test timeout error
        timeout_error = Exception("Request timed out")
        categorized = provider._categorize_openai_error(timeout_error)
        assert isinstance(categorized, LLMTimeoutError)
        assert categorized.provider == "openai"
        assert categorized.error_code == "OPENAI_TIMEOUT"
        
        # Test connection error
        connection_error = Exception("Connection failed")
        categorized = provider._categorize_openai_error(connection_error)
        assert isinstance(categorized, LLMAPIError)
        assert categorized.provider == "openai"
        assert categorized.error_code == "OPENAI_CONNECTION_ERROR"
        
        # Test generic error
        generic_error = Exception("Unknown error")
        categorized = provider._categorize_openai_error(generic_error)
        assert isinstance(categorized, LLMAPIError)
        assert categorized.provider == "openai"
        assert categorized.error_code == "OPENAI_GENERIC_ERROR"
    
    def test_anthropic_error_categorization(self):
        """Test Anthropic error categorization logic."""
        provider = AnthropicProvider({'api_key': 'test', 'model': 'claude-3-sonnet-20240229'})
        
        # Test authentication error
        auth_error = Mock()
        auth_error.status_code = 401
        auth_error.__str__ = Mock(return_value="Invalid API key")
        
        categorized = provider._categorize_anthropic_error(auth_error)
        assert isinstance(categorized, LLMAuthenticationError)
        assert categorized.provider == "anthropic"
        assert categorized.error_code == "ANTHROPIC_AUTH_ERROR"
        
        # Test rate limit error
        rate_limit_error = Mock()
        rate_limit_error.status_code = 429
        rate_limit_error.retry_after = 120
        rate_limit_error.__str__ = Mock(return_value="Rate limit exceeded")
        
        categorized = provider._categorize_anthropic_error(rate_limit_error)
        assert isinstance(categorized, LLMRateLimitError)
        assert categorized.provider == "anthropic"
        assert categorized.error_code == "ANTHROPIC_RATE_LIMIT"
        
        # Test server error
        server_error = Mock()
        server_error.status_code = 503
        server_error.__str__ = Mock(return_value="Service unavailable")
        
        categorized = provider._categorize_anthropic_error(server_error)
        assert isinstance(categorized, LLMAPIError)
        assert categorized.provider == "anthropic"
        assert categorized.error_code == "ANTHROPIC_SERVER_ERROR"
        
        # Test timeout error
        timeout_error = Exception("Connection timeout")
        categorized = provider._categorize_anthropic_error(timeout_error)
        assert isinstance(categorized, LLMTimeoutError)
        assert categorized.provider == "anthropic"
        assert categorized.error_code == "ANTHROPIC_TIMEOUT"
        
        # Test connection error
        connection_error = Exception("Network connection failed")
        categorized = provider._categorize_anthropic_error(connection_error)
        assert isinstance(categorized, LLMAPIError)
        assert categorized.provider == "anthropic"
        assert categorized.error_code == "ANTHROPIC_CONNECTION_ERROR"
        
        # Test generic error
        generic_error = Exception("Unknown error")
        categorized = provider._categorize_anthropic_error(generic_error)
        assert isinstance(categorized, LLMAPIError)
        assert categorized.provider == "anthropic"
        assert categorized.error_code == "ANTHROPIC_GENERIC_ERROR"
    
    @pytest.mark.asyncio
    async def test_error_handler_with_different_providers(self):
        """Test error handler with different provider errors."""
        context_openai = ErrorContext(
            operation="generate",
            component="openai_provider",
            metadata={"model": "gpt-3.5-turbo"}
        )
        
        context_anthropic = ErrorContext(
            operation="generate",
            component="anthropic_provider",
            metadata={"model": "claude-3-sonnet-20240229"}
        )
        
        # Test OpenAI rate limit error
        openai_error = LLMRateLimitError(
            "OpenAI rate limit exceeded",
            provider="openai",
            error_code="OPENAI_RATE_LIMIT",
            retry_after=60
        )
        
        response = await error_handler.handle_error(openai_error, context_openai)
        assert not response.success
        assert response.error_category.value == "rate_limit"
        assert response.error_code == "OPENAI_RATE_LIMIT"
        assert response.retry_after == 60
        assert response.fallback_used
        
        # Test Anthropic authentication error
        anthropic_error = LLMAuthenticationError(
            "Anthropic authentication failed",
            provider="anthropic",
            error_code="ANTHROPIC_AUTH_ERROR"
        )
        
        response = await error_handler.handle_error(anthropic_error, context_anthropic)
        assert not response.success
        assert response.error_category.value == "authentication"
        assert response.error_code == "ANTHROPIC_AUTH_ERROR"
        assert response.fallback_used
        
        # Check error statistics
        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] == 2
        assert "openai_provider:rate_limit" in stats["error_counts"]
        assert "anthropic_provider:authentication" in stats["error_counts"]
    
    def test_circuit_breaker_registration(self):
        """Test circuit breaker registration for providers."""
        openai_provider = OpenAIProvider({'api_key': 'test', 'model': 'gpt-3.5-turbo'})
        anthropic_provider = AnthropicProvider({'api_key': 'test', 'model': 'claude-3-sonnet-20240229'})
        
        # Check that circuit breakers were registered during provider initialization
        openai_cb = error_handler.get_circuit_breaker("openai_gpt-3.5-turbo")
        anthropic_cb = error_handler.get_circuit_breaker("anthropic_claude-3-sonnet-20240229")
        
        assert openai_cb is not None
        assert anthropic_cb is not None
        assert openai_cb is not anthropic_cb
    
    @pytest.mark.asyncio
    async def test_error_fallback_responses(self):
        """Test error fallback responses for different error types."""
        context = ErrorContext(operation="test", component="test")
        
        # Test rate limit fallback
        rate_limit_error = LLMRateLimitError("Rate limit", retry_after=120)
        response = await error_handler.handle_error(rate_limit_error, context)
        
        assert response.fallback_used
        assert "fallback_result" in response.metadata
        assert response.metadata["fallback_result"]["suggested_action"] == "retry_with_backoff"
        assert response.metadata["fallback_result"]["retry_after"] == 120
        
        # Test authentication fallback
        auth_error = LLMAuthenticationError("Auth failed")
        response = await error_handler.handle_error(auth_error, context)
        
        assert response.fallback_used
        assert response.metadata["fallback_result"]["suggested_action"] == "check_credentials"
        
        # Test timeout fallback
        timeout_error = LLMTimeoutError("Timeout")
        response = await error_handler.handle_error(timeout_error, context)
        
        assert response.fallback_used
        assert response.metadata["fallback_result"]["suggested_action"] == "retry_with_shorter_timeout"
        
        # Test processing fallback
        processing_error = AgentProcessingError("Processing failed")
        response = await error_handler.handle_error(processing_error, context)
        
        assert response.fallback_used
        assert response.metadata["fallback_result"]["suggested_action"] == "validate_input"
    
    def test_error_code_generation(self):
        """Test error code generation for different error types."""
        # Test with custom error code
        error_with_code = LLMAPIError("Test error", error_code="CUSTOM_ERROR")
        category = error_handler.categorize_error(error_with_code)
        code = error_handler._get_error_code(error_with_code, category)
        assert code == "CUSTOM_ERROR"
        
        # Test without custom error code
        error_without_code = LLMAPIError("Test error")
        category = error_handler.categorize_error(error_without_code)
        code = error_handler._get_error_code(error_without_code, category)
        assert code == "NETWORK_LLMAPIERROR"
        
        # Test with different error types
        timeout_error = LLMTimeoutError("Timeout")
        category = error_handler.categorize_error(timeout_error)
        code = error_handler._get_error_code(timeout_error, category)
        assert code == "TIMEOUT_LLMTIMEOUTERROR"
        
        auth_error = LLMAuthenticationError("Auth failed")
        category = error_handler.categorize_error(auth_error)
        code = error_handler._get_error_code(auth_error, category)
        assert code == "AUTHENTICATION_LLMAUTHENTICATIONERROR"
    
    @pytest.mark.asyncio
    async def test_error_statistics_accumulation(self):
        """Test error statistics accumulation over multiple errors."""
        context1 = ErrorContext(operation="op1", component="comp1")
        context2 = ErrorContext(operation="op2", component="comp2")
        
        # Generate multiple errors of different types
        errors = [
            (LLMRateLimitError("Rate limit 1"), context1),
            (LLMRateLimitError("Rate limit 2"), context1),
            (LLMTimeoutError("Timeout 1"), context1),
            (LLMAPIError("API error 1"), context2),
            (LLMAuthenticationError("Auth error 1"), context2),
        ]
        
        for error, context in errors:
            await error_handler.handle_error(error, context)
        
        stats = error_handler.get_error_statistics()
        
        assert stats["total_errors"] == 5
        assert stats["error_counts"]["comp1:rate_limit"] == 2
        assert stats["error_counts"]["comp1:timeout"] == 1
        assert stats["error_counts"]["comp2:network"] == 1
        assert stats["error_counts"]["comp2:authentication"] == 1
        
        # Test statistics reset
        error_handler.reset_statistics()
        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] == 0
        assert len(stats["error_counts"]) == 0


if __name__ == "__main__":
    pytest.main([__file__])