"""Unit tests for LLM providers."""

import pytest
import asyncio
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from core.llm_provider import LLMProvider, LLMManager, LLMResponse
from core.exceptions import (
    LLMProviderError, LLMConfigurationError, LLMAPIError
)
from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self, config: Dict[str, Any], should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        self.call_count = 0
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        self.call_count += 1
        if self.should_fail:
            raise LLMAPIError("Mock provider failure", provider="mock")
        
        return LLMResponse(
            content=f"Mock response to: {prompt}",
            usage={"total_tokens": 100},
            model="mock-model",
            provider="mock"
        )
    
    async def _create_connection(self):
        """Create a mock connection for the connection pool."""
        return "mock_connection"
    
    def get_capabilities(self) -> list:
        return ["text_generation"]
    
    def validate_config(self) -> bool:
        return "api_key" in self.config


class TestLLMProvider:
    """Test cases for base LLMProvider class."""
    
    def test_provider_initialization(self):
        """Test provider initialization."""
        config = {"api_key": "test-key", "model": "test-model"}
        provider = MockLLMProvider(config)
        
        assert provider.config == config
        assert provider.provider_name == "mockllm"
    
    def test_get_provider_info(self):
        """Test get_provider_info method."""
        config = {"api_key": "test-key"}
        provider = MockLLMProvider(config)
        
        info = provider.get_provider_info()
        
        assert info["name"] == "mockllm"
        assert info["capabilities"] == ["text_generation"]
        assert info["config_valid"] is True
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful text generation."""
        config = {"api_key": "test-key"}
        provider = MockLLMProvider(config)
        
        response = await provider.generate("Test prompt")
        
        assert response.content == "Mock response to: Test prompt"
        assert response.provider == "mock"
        assert response.usage["total_tokens"] == 100
    
    @pytest.mark.asyncio
    async def test_generate_failure(self):
        """Test text generation failure."""
        config = {"api_key": "test-key"}
        provider = MockLLMProvider(config, should_fail=True)
        
        with pytest.raises(LLMAPIError):
            await provider.generate("Test prompt")


class TestLLMManager:
    """Test cases for LLMManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = LLMManager()
        self.provider1 = MockLLMProvider({"api_key": "key1"})
        self.provider2 = MockLLMProvider({"api_key": "key2"})
    
    def test_register_provider(self):
        """Test provider registration."""
        self.manager.register_provider("provider1", self.provider1)
        
        assert "provider1" in self.manager.providers
        assert self.manager.default_provider == "provider1"
    
    def test_set_default_provider(self):
        """Test setting default provider."""
        self.manager.register_provider("provider1", self.provider1)
        self.manager.register_provider("provider2", self.provider2)
        
        self.manager.set_default_provider("provider2")
        assert self.manager.default_provider == "provider2"
    
    def test_set_default_provider_not_registered(self):
        """Test setting default provider that's not registered."""
        with pytest.raises(LLMConfigurationError):
            self.manager.set_default_provider("nonexistent")
    
    def test_set_fallback_order(self):
        """Test setting fallback order."""
        self.manager.register_provider("provider1", self.provider1)
        self.manager.register_provider("provider2", self.provider2)
        
        self.manager.set_fallback_order(["provider2", "provider1"])
        assert self.manager.fallback_order == ["provider2", "provider1"]
    
    def test_set_fallback_order_invalid_provider(self):
        """Test setting fallback order with invalid provider."""
        self.manager.register_provider("provider1", self.provider1)
        
        with pytest.raises(LLMConfigurationError):
            self.manager.set_fallback_order(["provider1", "nonexistent"])
    
    def test_get_provider(self):
        """Test getting a provider."""
        self.manager.register_provider("provider1", self.provider1)
        
        provider = self.manager.get_provider("provider1")
        assert provider == self.provider1
    
    def test_get_provider_default(self):
        """Test getting default provider."""
        self.manager.register_provider("provider1", self.provider1)
        
        provider = self.manager.get_provider()
        assert provider == self.provider1
    
    def test_get_provider_not_found(self):
        """Test getting non-existent provider."""
        with pytest.raises(LLMConfigurationError):
            self.manager.get_provider("nonexistent")
    
    @pytest.mark.asyncio
    async def test_generate_with_fallback_success(self):
        """Test successful generation with fallback."""
        self.manager.register_provider("provider1", self.provider1)
        
        response = await self.manager.generate_with_fallback("Test prompt")
        
        assert response.content == "Mock response to: Test prompt"
        assert self.provider1.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_with_fallback_primary_fails(self):
        """Test fallback when primary provider fails."""
        failing_provider = MockLLMProvider({"api_key": "key1"}, should_fail=True)
        
        self.manager.register_provider("failing", failing_provider)
        self.manager.register_provider("working", self.provider2)
        self.manager.set_fallback_order(["working"])
        
        response = await self.manager.generate_with_fallback("Test prompt", "failing")
        
        assert response.content == "Mock response to: Test prompt"
        assert failing_provider.call_count == 1
        assert self.provider2.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_with_fallback_all_fail(self):
        """Test when all providers fail."""
        failing_provider1 = MockLLMProvider({"api_key": "key1"}, should_fail=True)
        failing_provider2 = MockLLMProvider({"api_key": "key2"}, should_fail=True)
        
        self.manager.register_provider("failing1", failing_provider1)
        self.manager.register_provider("failing2", failing_provider2)
        self.manager.set_fallback_order(["failing2"])
        
        with pytest.raises(LLMProviderError):
            await self.manager.generate_with_fallback("Test prompt", "failing1")
    
    def test_get_available_providers(self):
        """Test getting available providers."""
        self.manager.register_provider("provider1", self.provider1)
        self.manager.register_provider("provider2", self.provider2)
        
        providers = self.manager.get_available_providers()
        assert set(providers) == {"provider1", "provider2"}
    
    def test_get_provider_capabilities(self):
        """Test getting provider capabilities."""
        self.manager.register_provider("provider1", self.provider1)
        
        capabilities = self.manager.get_provider_capabilities("provider1")
        assert capabilities == ["text_generation"]


class TestOpenAIProvider:
    """Test cases for OpenAI provider."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "api_key": "test-key",
            "model": "gpt-3.5-turbo",
            "max_tokens": 1000,
            "temperature": 0.7
        }
    
    def test_initialization(self):
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider(self.config)
        
        assert provider.api_key == "test-key"
        assert provider.model == "gpt-3.5-turbo"
        assert provider.max_tokens == 1000
        assert provider.temperature == 0.7
    
    def test_get_capabilities(self):
        """Test getting OpenAI capabilities."""
        provider = OpenAIProvider(self.config)
        capabilities = provider.get_capabilities()
        
        assert "text_generation" in capabilities
        assert "chat_completion" in capabilities
        assert "function_calling" in capabilities
    
    def test_validate_config_valid(self):
        """Test valid configuration validation."""
        provider = OpenAIProvider(self.config)
        assert provider.validate_config() is True
    
    def test_validate_config_missing_api_key(self):
        """Test configuration validation with missing API key."""
        config = self.config.copy()
        del config["api_key"]
        
        provider = OpenAIProvider(config)
        assert provider.validate_config() is False
    
    def test_validate_config_invalid_temperature(self):
        """Test configuration validation with invalid temperature."""
        config = self.config.copy()
        config["temperature"] = 3.0
        
        provider = OpenAIProvider(config)
        assert provider.validate_config() is False
    
    def test_get_model_info(self):
        """Test getting model information."""
        provider = OpenAIProvider(self.config)
        info = provider.get_model_info()
        
        assert info["model"] == "gpt-3.5-turbo"
        assert info["max_tokens"] == 1000
        assert info["temperature"] == 0.7
        assert info["supports_functions"] is True
        assert info["context_window"] == 4096
    
    @pytest.mark.asyncio
    async def test_generate_missing_client_library(self):
        """Test generation when OpenAI library is not installed."""
        provider = OpenAIProvider(self.config)
        
        with patch.dict('sys.modules', {'openai': None}):
            with pytest.raises(LLMConfigurationError):
                await provider.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful text generation."""
        provider = OpenAIProvider(self.config)
        
        # Mock OpenAI client and response
        mock_message = Mock()
        mock_message.content = "Generated response"
        mock_message.function_call = None  # No function call
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-3.5-turbo"
        mock_response.id = "test-id"
        mock_response.created = 1234567890
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('openai.AsyncOpenAI') as mock_openai_class:
            mock_openai_class.return_value = mock_client
            
            response = await provider.generate("Test prompt")
            
            assert response.content == "Generated response"
            assert response.provider == "openai"
            assert response.model == "gpt-3.5-turbo"
            assert response.usage["total_tokens"] == 30


class TestAnthropicProvider:
    """Test cases for Anthropic provider."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "api_key": "test-key",
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "temperature": 0.7
        }
    
    def test_initialization(self):
        """Test Anthropic provider initialization."""
        provider = AnthropicProvider(self.config)
        
        assert provider.api_key == "test-key"
        assert provider.model == "claude-3-sonnet-20240229"
        assert provider.max_tokens == 1000
        assert provider.temperature == 0.7
    
    def test_get_capabilities(self):
        """Test getting Anthropic capabilities."""
        provider = AnthropicProvider(self.config)
        capabilities = provider.get_capabilities()
        
        assert "text_generation" in capabilities
        assert "chat_completion" in capabilities
        assert "vision" in capabilities
        assert "long_context" in capabilities
    
    def test_validate_config_valid(self):
        """Test valid configuration validation."""
        provider = AnthropicProvider(self.config)
        assert provider.validate_config() is True
    
    def test_validate_config_missing_api_key(self):
        """Test configuration validation with missing API key."""
        config = self.config.copy()
        del config["api_key"]
        
        provider = AnthropicProvider(config)
        assert provider.validate_config() is False
    
    def test_validate_config_invalid_temperature(self):
        """Test configuration validation with invalid temperature."""
        config = self.config.copy()
        config["temperature"] = 2.0  # Anthropic max is 1.0
        
        provider = AnthropicProvider(config)
        assert provider.validate_config() is False
    
    def test_get_model_info(self):
        """Test getting model information."""
        provider = AnthropicProvider(self.config)
        info = provider.get_model_info()
        
        assert info["model"] == "claude-3-sonnet-20240229"
        assert info["max_tokens"] == 1000
        assert info["temperature"] == 0.7
        assert info["supports_vision"] is True
        assert info["context_window"] == 200000
        assert info["max_output_tokens"] == 4096
    
    @pytest.mark.asyncio
    async def test_generate_missing_client_library(self):
        """Test generation when Anthropic library is not installed."""
        provider = AnthropicProvider(self.config)
        
        with patch.dict('sys.modules', {'anthropic': None}):
            with pytest.raises(LLMConfigurationError):
                await provider.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful text generation."""
        provider = AnthropicProvider(self.config)
        
        # Mock Anthropic client and response
        mock_content_block = Mock()
        mock_content_block.text = "Generated response"
        
        mock_response = Mock()
        mock_response.content = [mock_content_block]
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.stop_reason = "end_turn"
        mock_response.stop_sequence = None
        mock_response.id = "test-id"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
        
        with patch('anthropic.AsyncAnthropic') as mock_anthropic_class:
            mock_anthropic_class.return_value = mock_client
            
            response = await provider.generate("Test prompt")
            
            assert response.content == "Generated response"
            assert response.provider == "anthropic"
            assert response.model == "claude-3-sonnet-20240229"
            assert response.usage["total_tokens"] == 30


if __name__ == "__main__":
    pytest.main([__file__])