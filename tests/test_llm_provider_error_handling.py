"""Integration tests for LLM provider error handling."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider
from core.exceptions import (
    LLMAPIError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMConfigurationError
)
from core.error_handler import error_handler, CircuitBreakerState


class TestOpenAIProviderErrorHandling:
    """Test error handling in OpenAI provider."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'api_key': 'test-key',
            'model': 'gpt-3.5-turbo',
            'timeout': 30
        }
        self.provider = OpenAIProvider(self.config)
    
    @pytest.mark.asyncio
    async def test_openai_authentication_error(self):
        """Test OpenAI authentication error handling."""
        mock_error = Mock()
        mock_error.status_code = 401
        mock_error.__str__ = Mock(return_value="Invalid API key")
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = mock_error
            mock_get_client.return_value = mock_client
            
            with pytest.raises(LLMAuthenticationError) as exc_info:
                await self.provider._generate_with_error_handling("test prompt")
            
            assert "authentication failed" in str(exc_info.value).lower()
            assert exc_info.value.provider == "openai"
            assert exc_info.value.error_code == "OPENAI_AUTH_ERROR"
    
    @pytest.mark.asyncio
    async def test_openai_rate_limit_error(self):
        """Test OpenAI rate limit error handling."""
        mock_error = Mock()
        mock_error.status_code = 429
        mock_error.retry_after = 60
        mock_error.__str__ = Mock(return_value="Rate limit exceeded")
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = mock_error
            mock_get_client.return_value = mock_client
            
            with pytest.raises(LLMRateLimitError) as exc_info:
                await self.provider._generate_with_error_handling("test prompt")
            
            assert "rate limit exceeded" in str(exc_info.value).lower()
            assert exc_info.value.provider == "openai"
            assert exc_info.value.error_code == "OPENAI_RATE_LIMIT"
    
    @pytest.mark.asyncio
    async def test_openai_server_error(self):
        """Test OpenAI server error handling."""
        mock_error = Mock()
        mock_error.status_code = 500
        mock_error.__str__ = Mock(return_value="Internal server error")
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = mock_error
            mock_get_client.return_value = mock_client
            
            with pytest.raises(LLMAPIError) as exc_info:
                await self.provider._generate_with_error_handling("test prompt")
            
            assert "server error" in str(exc_info.value).lower()
            assert exc_info.value.provider == "openai"
            assert exc_info.value.error_code == "OPENAI_SERVER_ERROR"
    
    @pytest.mark.asyncio
    async def test_openai_timeout_error(self):
        """Test OpenAI timeout error handling."""
        mock_error = Exception("Request timed out")
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = mock_error
            mock_get_client.return_value = mock_client
            
            with pytest.raises(LLMTimeoutError) as exc_info:
                await self.provider._generate_with_error_handling("test prompt")
            
            assert "timeout" in str(exc_info.value).lower()
            assert exc_info.value.provider == "openai"
            assert exc_info.value.error_code == "OPENAI_TIMEOUT"
    
    @pytest.mark.asyncio
    async def test_openai_connection_error(self):
        """Test OpenAI connection error handling."""
        mock_error = Exception("Connection failed")
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = mock_error
            mock_get_client.return_value = mock_client
            
            with pytest.raises(LLMAPIError) as exc_info:
                await self.provider._generate_with_error_handling("test prompt")
            
            assert "connection error" in str(exc_info.value).lower()
            assert exc_info.value.provider == "openai"
            assert exc_info.value.error_code == "OPENAI_CONNECTION_ERROR"
    
    @pytest.mark.asyncio
    async def test_openai_circuit_breaker_integration(self):
        """Test circuit breaker integration with OpenAI provider."""
        # Reset error handler state
        error_handler.reset_statistics()
        
        # Mock repeated failures
        mock_error = Mock()
        mock_error.status_code = 500
        mock_error.__str__ = Mock(return_value="Server error")
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = mock_error
            mock_get_client.return_value = mock_client
            
            # Get the circuit breaker
            cb_name = "openai_api"
            circuit_breaker = error_handler.get_circuit_breaker(cb_name)
            
            if circuit_breaker:
                # Force circuit breaker to closed state for testing
                circuit_breaker.state = CircuitBreakerState.CLOSED
                circuit_breaker.failure_count = 0
                
                # Make multiple failing calls to trigger circuit breaker
                for i in range(6):  # More than failure threshold
                    with pytest.raises((LLMAPIError, Exception)):
                        await self.provider.generate("test prompt")
                
                # Check if circuit breaker opened
                assert circuit_breaker.failure_count >= 5
    
    @pytest.mark.asyncio
    async def test_openai_successful_generation(self):
        """Test successful OpenAI generation with error handling."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Generated response"
        mock_response.choices[0].message.function_call = None
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_response.model = "gpt-3.5-turbo"
        mock_response.id = "test-id"
        mock_response.created = 1234567890
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = await self.provider.generate("test prompt")
            
            assert result.content == "Generated response"
            assert result.provider == "openai"
            assert result.usage["total_tokens"] == 30


class TestAnthropicProviderErrorHandling:
    """Test error handling in Anthropic provider."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'api_key': 'test-key',
            'model': 'claude-3-sonnet-20240229',
            'timeout': 30
        }
        self.provider = AnthropicProvider(self.config)
    
    @pytest.mark.asyncio
    async def test_anthropic_authentication_error(self):
        """Test Anthropic authentication error handling."""
        mock_error = Mock()
        mock_error.status_code = 401
        mock_error.__str__ = Mock(return_value="Invalid API key")
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create.side_effect = mock_error
            mock_get_client.return_value = mock_client
            
            with pytest.raises(LLMAuthenticationError) as exc_info:
                await self.provider._generate_with_error_handling("test prompt")
            
            assert "authentication failed" in str(exc_info.value).lower()
            assert exc_info.value.provider == "anthropic"
            assert exc_info.value.error_code == "ANTHROPIC_AUTH_ERROR"
    
    @pytest.mark.asyncio
    async def test_anthropic_rate_limit_error(self):
        """Test Anthropic rate limit error handling."""
        mock_error = Mock()
        mock_error.status_code = 429
        mock_error.retry_after = 120
        mock_error.__str__ = Mock(return_value="Rate limit exceeded")
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create.side_effect = mock_error
            mock_get_client.return_value = mock_client
            
            with pytest.raises(LLMRateLimitError) as exc_info:
                await self.provider._generate_with_error_handling("test prompt")
            
            assert "rate limit exceeded" in str(exc_info.value).lower()
            assert exc_info.value.provider == "anthropic"
            assert exc_info.value.error_code == "ANTHROPIC_RATE_LIMIT"
    
    @pytest.mark.asyncio
    async def test_anthropic_server_error(self):
        """Test Anthropic server error handling."""
        mock_error = Mock()
        mock_error.status_code = 503
        mock_error.__str__ = Mock(return_value="Service unavailable")
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create.side_effect = mock_error
            mock_get_client.return_value = mock_client
            
            with pytest.raises(LLMAPIError) as exc_info:
                await self.provider._generate_with_error_handling("test prompt")
            
            assert "server error" in str(exc_info.value).lower()
            assert exc_info.value.provider == "anthropic"
            assert exc_info.value.error_code == "ANTHROPIC_SERVER_ERROR"
    
    @pytest.mark.asyncio
    async def test_anthropic_timeout_error(self):
        """Test Anthropic timeout error handling."""
        mock_error = Exception("Connection timeout")
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create.side_effect = mock_error
            mock_get_client.return_value = mock_client
            
            with pytest.raises(LLMTimeoutError) as exc_info:
                await self.provider._generate_with_error_handling("test prompt")
            
            assert "timeout" in str(exc_info.value).lower()
            assert exc_info.value.provider == "anthropic"
            assert exc_info.value.error_code == "ANTHROPIC_TIMEOUT"
    
    @pytest.mark.asyncio
    async def test_anthropic_successful_generation(self):
        """Test successful Anthropic generation with error handling."""
        mock_content_block = Mock()
        mock_content_block.text = "Generated response from Claude"
        
        mock_response = Mock()
        mock_response.content = [mock_content_block]
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.stop_reason = "end_turn"
        mock_response.stop_sequence = None
        mock_response.id = "test-id"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 15
        mock_response.usage.output_tokens = 25
        
        with patch.object(self.provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = await self.provider.generate("test prompt")
            
            assert result.content == "Generated response from Claude"
            assert result.provider == "anthropic"
            assert result.usage["total_tokens"] == 40


class TestProviderErrorHandlingIntegration:
    """Integration tests for provider error handling."""
    
    @pytest.mark.asyncio
    async def test_error_statistics_across_providers(self):
        """Test error statistics tracking across different providers."""
        # Reset error handler state
        error_handler.reset_statistics()
        
        openai_config = {'api_key': 'test-key', 'model': 'gpt-3.5-turbo'}
        anthropic_config = {'api_key': 'test-key', 'model': 'claude-3-sonnet-20240229'}
        
        openai_provider = OpenAIProvider(openai_config)
        anthropic_provider = AnthropicProvider(anthropic_config)
        
        # Mock errors for both providers
        mock_error = Mock()
        mock_error.status_code = 429
        mock_error.__str__ = Mock(return_value="Rate limit")
        
        with patch.object(openai_provider, '_get_client') as mock_openai_client, \
             patch.object(anthropic_provider, '_get_client') as mock_anthropic_client:
            
            mock_openai_client.return_value.chat.completions.create.side_effect = mock_error
            mock_anthropic_client.return_value.messages.create.side_effect = mock_error
            
            # Generate errors from both providers
            with pytest.raises(LLMRateLimitError):
                await openai_provider._generate_with_error_handling("test")
            
            with pytest.raises(LLMRateLimitError):
                await anthropic_provider._generate_with_error_handling("test")
            
            # Check error statistics
            stats = error_handler.get_error_statistics()
            assert stats["total_errors"] >= 2
            
            # Should have errors from both providers
            error_keys = list(stats["error_counts"].keys())
            assert any("openai_provider" in key for key in error_keys)
            assert any("anthropic_provider" in key for key in error_keys)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_isolation(self):
        """Test that circuit breakers are isolated between providers."""
        openai_config = {'api_key': 'test-key', 'model': 'gpt-3.5-turbo'}
        anthropic_config = {'api_key': 'test-key', 'model': 'claude-3-sonnet-20240229'}
        
        openai_provider = OpenAIProvider(openai_config)
        anthropic_provider = AnthropicProvider(anthropic_config)
        
        # Get circuit breakers for both providers
        openai_cb = error_handler.get_circuit_breaker("openai_api")
        anthropic_cb = error_handler.get_circuit_breaker("anthropic_api")
        
        # They should be different instances
        if openai_cb and anthropic_cb:
            assert openai_cb is not anthropic_cb
            assert openai_cb.config.name != anthropic_cb.config.name
    
    def test_provider_error_categorization_consistency(self):
        """Test that error categorization is consistent across providers."""
        openai_provider = OpenAIProvider({'api_key': 'test', 'model': 'gpt-3.5-turbo'})
        anthropic_provider = AnthropicProvider({'api_key': 'test', 'model': 'claude-3-sonnet-20240229'})
        
        # Test authentication errors
        auth_error = Exception("Invalid API key")
        openai_auth_error = openai_provider._categorize_openai_error(auth_error)
        anthropic_auth_error = anthropic_provider._categorize_anthropic_error(auth_error)
        
        # Both should be generic API errors for this case
        assert isinstance(openai_auth_error, LLMAPIError)
        assert isinstance(anthropic_auth_error, LLMAPIError)
        
        # Test timeout errors
        timeout_error = Exception("Request timed out")
        openai_timeout_error = openai_provider._categorize_openai_error(timeout_error)
        anthropic_timeout_error = anthropic_provider._categorize_anthropic_error(timeout_error)
        
        # Both should be timeout errors
        assert isinstance(openai_timeout_error, LLMTimeoutError)
        assert isinstance(anthropic_timeout_error, LLMTimeoutError)


if __name__ == "__main__":
    pytest.main([__file__])