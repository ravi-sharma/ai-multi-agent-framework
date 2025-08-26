"""LLM Provider base classes and utilities."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config.get('model', 'default')
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the provider configuration."""
        pass


class LLMManager:
    """Manager for LLM providers."""
    
    def __init__(self):
        self.providers = {}
        self.default_provider = None
    
    def add_provider(self, name: str, provider: LLMProvider):
        """Add a provider to the manager."""
        self.providers[name] = provider
        if self.default_provider is None:
            self.default_provider = name
    
    def get_provider(self, name: Optional[str] = None) -> LLMProvider:
        """Get a provider by name."""
        provider_name = name or self.default_provider
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not found")
        return self.providers[provider_name]
    
    async def generate(self, prompt: str, provider: Optional[str] = None, **kwargs) -> LLMResponse:
        """Generate using a specific provider."""
        provider_instance = self.get_provider(provider)
        return await provider_instance.generate(prompt, **kwargs)