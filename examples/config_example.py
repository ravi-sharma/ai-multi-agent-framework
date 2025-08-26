#!/usr/bin/env python3
"""
Example demonstrating the configuration management system.

This script shows how to:
1. Load configuration from YAML files
2. Handle environment variables
3. Validate configuration
4. Access specific configuration sections
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from configs.base_config import ConfigManager, ConfigurationError


def main():
    """Demonstrate configuration management features."""
    print("AI Agent Framework - Configuration Management Example")
    print("=" * 60)
    
    # Initialize the configuration manager
    manager = ConfigManager()
    
    # Example 1: Load the main configuration
    print("\n1. Loading main configuration...")
    try:
        config_path = "config/example_config.yaml"
        config = manager.load_framework_config(config_path)
        
        print(f"✓ Configuration loaded successfully!")
        print(f"  - Default LLM Provider: {config.default_llm_provider}")
        print(f"  - Number of LLM Providers: {len(config.llm_providers)}")
        print(f"  - Number of Agents: {len(config.agents)}")
        print(f"  - Number of Criteria: {len(config.criteria)}")
        print(f"  - Fallback Agent: {config.fallback_agent}")
        
    except ConfigurationError as e:
        print(f"✗ Configuration loading failed: {e}")
        return
    
    # Example 2: Access specific configurations
    print("\n2. Accessing specific configurations...")
    
    # Get LLM configuration
    openai_config = manager.get_llm_config("openai")
    if openai_config:
        print(f"✓ OpenAI Configuration:")
        print(f"  - Model: {openai_config.model}")
        print(f"  - Timeout: {openai_config.timeout}s")
        print(f"  - Max Retries: {openai_config.max_retries}")
        # Don't print API key for security
        api_key_status = "Set" if openai_config.api_key else "Not Set"
        print(f"  - API Key: {api_key_status}")
    
    # Get agent configuration
    sales_agent_config = manager.get_agent_config("sales_agent")
    if sales_agent_config:
        print(f"✓ Sales Agent Configuration:")
        print(f"  - Type: {sales_agent_config.agent_type}")
        print(f"  - Enabled: {sales_agent_config.enabled}")
        print(f"  - LLM Provider: {sales_agent_config.llm_provider}")
        if sales_agent_config.workflow_config:
            print(f"  - Workflow Steps: {len(sales_agent_config.workflow_config.workflow_steps)}")
    
    # Example 3: Environment variable demonstration
    print("\n3. Environment variable handling...")
    
    # Show how environment variables are handled
    print("Environment variables in configuration:")
    for provider_name, provider_config in config.llm_providers.items():
        if provider_config.api_key and "${" in str(provider_config.api_key):
            print(f"  - {provider_name}: {provider_config.api_key} (template)")
        elif provider_config.api_key:
            print(f"  - {provider_name}: API key resolved from environment")
        else:
            print(f"  - {provider_name}: No API key configured")
    
    # Example 4: Configuration validation
    print("\n4. Configuration validation...")
    
    validation_errors = manager.validate_config_file(config_path)
    if not validation_errors:
        print("✓ Configuration is valid!")
    else:
        print("✗ Configuration validation errors:")
        for error in validation_errors:
            print(f"  - {error}")
    
    # Example 5: Criteria configuration
    print("\n5. Criteria configuration...")
    
    criteria_configs = manager.get_criteria_configs()
    print(f"Found {len(criteria_configs)} routing criteria:")
    
    for criteria in criteria_configs:
        print(f"  - {criteria.name} (Priority: {criteria.priority})")
        print(f"    → Routes to: {criteria.agent}")
        print(f"    → Conditions: {len(criteria.conditions)}")
        for condition in criteria.conditions:
            print(f"      • {condition.field} {condition.operator} {condition.values}")
    
    # Example 6: Caching demonstration
    print("\n6. Configuration caching...")
    
    # Load the same config again - should use cache
    config2 = manager.load_framework_config(config_path)
    if config is config2:
        print("✓ Configuration was loaded from cache (same object reference)")
    else:
        print("✗ Configuration was reloaded (different object reference)")
    
    # Force reload
    config3 = manager.load_framework_config(config_path, force_reload=True)
    if config is not config3:
        print("✓ Force reload created new configuration object")
    else:
        print("✗ Force reload failed to create new object")
    
    print("\n" + "=" * 60)
    print("Configuration management example completed!")


if __name__ == "__main__":
    main()