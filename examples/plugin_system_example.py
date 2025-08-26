#!/usr/bin/env python3
"""
Example demonstrating the plugin system functionality.

This example shows how to:
1. Initialize the plugin manager
2. Discover and load plugins
3. Create agents and evaluators from plugins
4. Use plugin-provided functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.plugin_manager import PluginManager
from models.data_models import TriggerData
from models.config_models import Condition


async def main():
    """Main example function."""
    print("=== AI Agent Framework Plugin System Example ===\n")
    
    # Initialize the plugin manager
    print("1. Initializing Plugin Manager...")
    plugin_manager = PluginManager()
    
    # Add the examples directory as a plugin directory
    examples_dir = str(project_root / "ai_agent_framework" / "plugins" / "examples")
    plugin_manager.add_plugin_directory(examples_dir)
    print(f"   Added plugin directory: {examples_dir}")
    
    # Discover available plugins from configuration
    print("\n2. Discovering Plugins...")
    config_file = str(project_root / "examples" / "plugins_config.json")
    try:
        config_plugins = plugin_manager.discovery.discover_from_config(config_file)
        for plugin_metadata in config_plugins:
            plugin_manager.discovery.discovered_plugins[plugin_metadata['name']] = plugin_metadata
        
        discovered_plugins = list(plugin_manager.discovery.discovered_plugins.values())
        print(f"   Discovered {len(discovered_plugins)} plugins:")
        for plugin_metadata in discovered_plugins:
            print(f"   - {plugin_metadata['name']} v{plugin_metadata['version']} ({plugin_metadata['plugin_type']})")
    except Exception as e:
        print(f"   Error discovering plugins: {e}")
        discovered_plugins = []
    
    # Load all discovered plugins
    print("\n3. Loading Plugins...")
    try:
        loaded_plugins = plugin_manager.load_plugins()
        print(f"   Successfully loaded {len(loaded_plugins)} plugins:")
        for plugin_name in loaded_plugins:
            print(f"   - {plugin_name}")
    except Exception as e:
        print(f"   Error loading plugins: {e}")
        return
    
    # Show plugin status
    print("\n4. Plugin Status:")
    status = plugin_manager.get_plugin_status()
    print(f"   Total discovered: {status['discovered']}")
    print(f"   Total loaded: {status['loaded']}")
    print(f"   Available agent types: {status['agent_types']}")
    print(f"   Available evaluator types: {status['evaluator_types']}")
    
    # Show supported types
    print("\n5. Supported Types:")
    agent_types = plugin_manager.get_supported_agent_types()
    evaluator_types = plugin_manager.get_supported_evaluator_types()
    print(f"   Agent types: {agent_types}")
    print(f"   Evaluator types: {evaluator_types}")
    
    # Create and use agents from plugins
    print("\n6. Creating and Using Agents...")
    
    # Create example agents if available
    if 'example' in agent_types:
        print("   Creating 'example' agent...")
        example_agent = plugin_manager.create_agent('example', 'demo_example_agent', {'greeting': 'Hi there'})
        
        # Use the agent
        input_data = {'message': 'Plugin System'}
        result = await example_agent.process(input_data)
        print(f"   Agent result: {result.output}")
    
    if 'echo' in agent_types:
        print("   Creating 'echo' agent...")
        echo_agent = plugin_manager.create_agent('echo', 'demo_echo_agent', {'prefix': 'ECHO:'})
        
        # Use the agent
        input_data = {'test': 'data', 'number': 42}
        result = await echo_agent.process(input_data)
        print(f"   Agent result: {result.output}")
    
    # Create and use evaluators from plugins
    print("\n7. Creating and Using Evaluators...")
    
    # Create sample trigger data
    trigger_data = TriggerData(
        source='test',
        timestamp=None,
        data={
            'email': {
                'subject': 'Hello World',
                'body': 'This is a test message with some content.'
            }
        },
        metadata={}
    )
    
    # Test evaluators if available
    if 'starts_with' in evaluator_types:
        print("   Testing 'starts_with' evaluator...")
        evaluator = plugin_manager.create_evaluator('starts_with')
        
        condition = Condition(
            field='email.subject',
            operator='starts_with',
            values=['Hello'],
            case_sensitive=False
        )
        
        result = evaluator.evaluate(condition, trigger_data)
        print(f"   Evaluation result: {result}")
    
    if 'length' in evaluator_types:
        print("   Testing 'length' evaluator...")
        evaluator = plugin_manager.create_evaluator('length')
        
        condition = Condition(
            field='email.body',
            operator='length',
            values=['>', 20],
            case_sensitive=False
        )
        
        result = evaluator.evaluate(condition, trigger_data)
        print(f"   Evaluation result: {result}")
    
    # Show loaded plugin information
    print("\n8. Loaded Plugin Details:")
    loaded_plugin_infos = plugin_manager.get_loaded_plugins()
    for plugin_info in loaded_plugin_infos:
        print(f"   Plugin: {plugin_info.name}")
        print(f"     Version: {plugin_info.version}")
        print(f"     Type: {plugin_info.plugin_type}")
        print(f"     Description: {plugin_info.description}")
        print(f"     Dependencies: {plugin_info.dependencies}")
        print()
    
    # Demonstrate plugin unloading
    print("9. Unloading Plugins...")
    if loaded_plugins:
        plugin_to_unload = loaded_plugins[0]
        print(f"   Unloading plugin: {plugin_to_unload}")
        unloaded = plugin_manager.unload_plugins([plugin_to_unload])
        print(f"   Successfully unloaded: {unloaded}")
    
    # Clean up
    print("\n10. Cleaning Up...")
    plugin_manager.cleanup()
    print("   Plugin manager cleaned up.")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())