#!/usr/bin/env python3
"""
Example script demonstrating the LLM abstraction layer usage.

This script shows how to:
1. Create and configure LLM providers
2. Use the LLMManager for provider management and fallback
3. Generate text using different providers
"""

import asyncio
import os
from utils.llm_provider import LLMManager
from utils.openai_provider import OpenAIProvider
from utils.anthropic_provider import AnthropicProvider
from utils.llm_utils import create_llm_manager_from_file


async def basic_provider_example():
    """Example of using providers directly."""
    print("=== Basic Provider Example ===")
    
    # Create OpenAI provider
    openai_config = {
        "api_key": os.getenv("OPENAI_API_KEY", "demo-key"),
        "model": "gpt-3.5-turbo",
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    openai_provider = OpenAIProvider(openai_config)
    print(f"OpenAI Provider Info: {openai_provider.get_provider_info()}")
    
    # Create Anthropic provider
    anthropic_config = {
        "api_key": os.getenv("ANTHROPIC_API_KEY", "demo-key"),
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    anthropic_provider = AnthropicProvider(anthropic_config)
    print(f"Anthropic Provider Info: {anthropic_provider.get_provider_info()}")
    
    # Note: These would fail without real API keys, so we just show the setup
    print("Providers configured successfully!")


async def manager_example():
    """Example of using LLMManager for provider management."""
    print("\n=== LLM Manager Example ===")
    
    # Create manager and register providers
    manager = LLMManager()
    
    # Register OpenAI provider
    openai_config = {
        "api_key": os.getenv("OPENAI_API_KEY", "demo-key"),
        "model": "gpt-3.5-turbo",
        "max_tokens": 100,
        "temperature": 0.7
    }
    openai_provider = OpenAIProvider(openai_config)
    manager.register_provider("openai", openai_provider)
    
    # Register Anthropic provider
    anthropic_config = {
        "api_key": os.getenv("ANTHROPIC_API_KEY", "demo-key"),
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 100,
        "temperature": 0.7
    }
    anthropic_provider = AnthropicProvider(anthropic_config)
    manager.register_provider("anthropic", anthropic_provider)
    
    # Configure fallback order
    manager.set_fallback_order(["anthropic", "openai"])
    
    print(f"Available providers: {manager.get_available_providers()}")
    print(f"Default provider: {manager.default_provider}")
    print(f"Fallback order: {manager.fallback_order}")
    
    # Get provider capabilities
    for provider_name in manager.get_available_providers():
        capabilities = manager.get_provider_capabilities(provider_name)
        print(f"{provider_name} capabilities: {capabilities}")


async def config_file_example():
    """Example of loading configuration from file."""
    print("\n=== Configuration File Example ===")
    
    try:
        # This would load from config/llm_config.yaml
        # manager = create_llm_manager_from_file("config/llm_config.yaml")
        # print(f"Loaded providers from config: {manager.get_available_providers()}")
        print("Configuration file loading available (requires valid config file)")
    except Exception as e:
        print(f"Config loading example (would need valid config): {e}")


def provider_recommendations_example():
    """Example of getting provider recommendations."""
    print("\n=== Provider Recommendations Example ===")
    
    from utils.llm_utils import get_provider_recommendations
    
    use_cases = ["general", "coding", "analysis", "creative"]
    
    for use_case in use_cases:
        rec = get_provider_recommendations(use_case)
        print(f"{use_case.capitalize()} use case:")
        print(f"  Primary: {rec['primary']} ({rec['model']})")
        print(f"  Fallback: {rec['fallback']} ({rec['fallback_model']})")


async def main():
    """Run all examples."""
    print("LLM Abstraction Layer Examples")
    print("=" * 50)
    
    await basic_provider_example()
    await manager_example()
    await config_file_example()
    provider_recommendations_example()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo use with real API keys, set environment variables:")
    print("export OPENAI_API_KEY='your-openai-key'")
    print("export ANTHROPIC_API_KEY='your-anthropic-key'")


if __name__ == "__main__":
    asyncio.run(main())