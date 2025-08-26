"""Tests for the plugin system."""

import pytest
import tempfile
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Type
from unittest.mock import Mock, patch

from plugins import (
    PluginManager, PluginInterface, AgentPlugin, CriteriaPlugin,
    PluginInfo, PluginRegistry, PluginDiscovery, DependencyResolver,
    VersionComparator, PluginError, PluginLoadError, PluginDependencyError
)
from core.base_agent import BaseAgent
from core.criteria_evaluator import CriteriaEvaluator
from models.data_models import AgentResult, TriggerData
from models.config_models import WorkflowConfig, Condition


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        return AgentResult(
            success=True,
            output={'test': 'result'},
            notes=['test note'],
            requires_human_review=False,
            execution_time=0.1
        )
    
    def get_workflow_config(self) -> WorkflowConfig:
        return WorkflowConfig(
            name="test_workflow",
            description="Test workflow",
            max_retries=3,
            timeout=30,
            workflow_type="simple"
        )


class MockEvaluator(CriteriaEvaluator):
    """Mock criteria evaluator for testing."""
    
    def __init__(self):
        super().__init__('mock')
    
    def evaluate(self, condition: Condition, trigger_data: TriggerData) -> bool:
        return True
    
    def validate_condition(self, condition: Condition) -> bool:
        return True


class MockAgentPlugin(AgentPlugin):
    """Mock agent plugin for testing."""
    
    def get_plugin_info(self) -> PluginInfo:
        return PluginInfo(
            name="mock_agent_plugin",
            version="1.0.0",
            description="Mock agent plugin",
            author="Test",
            plugin_type="agent",
            dependencies=[],
            entry_point="mock"
        )
    
    def initialize(self, config: Dict[str, Any] = None) -> None:
        pass
    
    def cleanup(self) -> None:
        pass
    
    def get_agent_classes(self) -> Dict[str, Type[BaseAgent]]:
        return {'mock': MockAgent}
    
    def create_agent(self, agent_type: str, name: str, config: Dict[str, Any] = None) -> BaseAgent:
        if agent_type == 'mock':
            return MockAgent(name, config)
        raise ValueError(f"Unknown agent type: {agent_type}")


class MockCriteriaPlugin(CriteriaPlugin):
    """Mock criteria plugin for testing."""
    
    def get_plugin_info(self) -> PluginInfo:
        return PluginInfo(
            name="mock_criteria_plugin",
            version="1.0.0",
            description="Mock criteria plugin",
            author="Test",
            plugin_type="criteria",
            dependencies=[],
            entry_point="mock"
        )
    
    def initialize(self, config: Dict[str, Any] = None) -> None:
        pass
    
    def cleanup(self) -> None:
        pass
    
    def get_evaluator_classes(self) -> Dict[str, Type[CriteriaEvaluator]]:
        return {'mock': MockEvaluator}
    
    def create_evaluator(self, evaluator_type: str) -> CriteriaEvaluator:
        if evaluator_type == 'mock':
            return MockEvaluator()
        raise ValueError(f"Unknown evaluator type: {evaluator_type}")


class TestVersionComparator:
    """Test version comparison functionality."""
    
    def test_parse_version(self):
        """Test version parsing."""
        assert VersionComparator.parse_version("1.2.3") == (1, 2, 3)
        assert VersionComparator.parse_version("0.1.0") == (0, 1, 0)
        assert VersionComparator.parse_version("10.20.30") == (10, 20, 30)
    
    def test_parse_version_with_prerelease(self):
        """Test version parsing with pre-release info."""
        assert VersionComparator.parse_version("1.2.3-alpha") == (1, 2, 3)
        assert VersionComparator.parse_version("1.2.3+build.1") == (1, 2, 3)
    
    def test_parse_version_invalid(self):
        """Test invalid version parsing."""
        with pytest.raises(ValueError):
            VersionComparator.parse_version("1.2")
        with pytest.raises(ValueError):
            VersionComparator.parse_version("1.2.3.4")
        with pytest.raises(ValueError):
            VersionComparator.parse_version("a.b.c")
    
    def test_compare_versions(self):
        """Test version comparison."""
        assert VersionComparator.compare_versions("1.0.0", "1.0.0") == 0
        assert VersionComparator.compare_versions("1.0.0", "1.0.1") == -1
        assert VersionComparator.compare_versions("1.0.1", "1.0.0") == 1
        assert VersionComparator.compare_versions("2.0.0", "1.9.9") == 1
    
    def test_satisfies_requirement(self):
        """Test requirement satisfaction."""
        assert VersionComparator.satisfies_requirement("1.0.0", "==1.0.0")
        assert VersionComparator.satisfies_requirement("1.0.1", ">=1.0.0")
        assert VersionComparator.satisfies_requirement("1.0.0", "<=1.0.1")
        assert VersionComparator.satisfies_requirement("1.0.1", ">1.0.0")
        assert VersionComparator.satisfies_requirement("1.0.0", "<1.0.1")
        assert not VersionComparator.satisfies_requirement("1.0.0", "!=1.0.0")
        
        # Test tilde operator (compatible within minor version)
        assert VersionComparator.satisfies_requirement("1.2.3", "~1.2.0")
        assert VersionComparator.satisfies_requirement("1.2.5", "~1.2.0")
        assert not VersionComparator.satisfies_requirement("1.3.0", "~1.2.0")
        
        # Test caret operator (compatible within major version)
        assert VersionComparator.satisfies_requirement("1.2.3", "^1.0.0")
        assert VersionComparator.satisfies_requirement("1.5.0", "^1.0.0")
        assert not VersionComparator.satisfies_requirement("2.0.0", "^1.0.0")


class TestPluginRegistry:
    """Test plugin registry functionality."""
    
    def test_register_agent_plugin(self):
        """Test registering an agent plugin."""
        registry = PluginRegistry()
        plugin = MockAgentPlugin()
        
        registry.register_plugin(plugin)
        
        assert "mock_agent_plugin" in registry.plugins
        assert "mock_agent_plugin" in registry.agent_plugins
        assert "mock" in registry.agent_types
    
    def test_register_criteria_plugin(self):
        """Test registering a criteria plugin."""
        registry = PluginRegistry()
        plugin = MockCriteriaPlugin()
        
        registry.register_plugin(plugin)
        
        assert "mock_criteria_plugin" in registry.plugins
        assert "mock_criteria_plugin" in registry.criteria_plugins
        assert "mock" in registry.evaluator_types
    
    def test_register_duplicate_plugin(self):
        """Test registering duplicate plugin names."""
        registry = PluginRegistry()
        plugin1 = MockAgentPlugin()
        plugin2 = MockAgentPlugin()
        
        registry.register_plugin(plugin1)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register_plugin(plugin2)
    
    def test_create_agent(self):
        """Test creating agent through registry."""
        registry = PluginRegistry()
        plugin = MockAgentPlugin()
        registry.register_plugin(plugin)
        
        agent = registry.create_agent("mock", "test_agent")
        
        assert isinstance(agent, MockAgent)
        assert agent.name == "test_agent"
    
    def test_create_evaluator(self):
        """Test creating evaluator through registry."""
        registry = PluginRegistry()
        plugin = MockCriteriaPlugin()
        registry.register_plugin(plugin)
        
        evaluator = registry.create_evaluator("mock")
        
        assert isinstance(evaluator, MockEvaluator)
        assert evaluator.evaluator_type == "mock"
    
    def test_unregister_plugin(self):
        """Test unregistering a plugin."""
        registry = PluginRegistry()
        plugin = MockAgentPlugin()
        registry.register_plugin(plugin)
        
        assert "mock_agent_plugin" in registry.plugins
        
        registry.unregister_plugin("mock_agent_plugin")
        
        assert "mock_agent_plugin" not in registry.plugins
        assert "mock" not in registry.agent_types


class TestDependencyResolver:
    """Test dependency resolution functionality."""
    
    def test_simple_dependency_resolution(self):
        """Test resolving simple dependencies."""
        resolver = DependencyResolver()
        
        # Plugin A depends on Plugin B
        plugin_a = PluginInfo("plugin_a", "1.0.0", "Plugin A", "Test", "agent", ["plugin_b"], "a")
        plugin_b = PluginInfo("plugin_b", "1.0.0", "Plugin B", "Test", "agent", [], "b")
        
        resolver.add_plugin(plugin_a)
        resolver.add_plugin(plugin_b)
        
        load_order = resolver.resolve_dependencies(["plugin_a"])
        
        # plugin_b should be loaded before plugin_a
        assert load_order == ["plugin_b", "plugin_a"]
    
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        resolver = DependencyResolver()
        
        # Plugin A depends on Plugin B, Plugin B depends on Plugin A
        plugin_a = PluginInfo("plugin_a", "1.0.0", "Plugin A", "Test", "agent", ["plugin_b"], "a")
        plugin_b = PluginInfo("plugin_b", "1.0.0", "Plugin B", "Test", "agent", ["plugin_a"], "b")
        
        resolver.add_plugin(plugin_a)
        resolver.add_plugin(plugin_b)
        
        with pytest.raises(PluginDependencyError, match="Circular dependency"):
            resolver.resolve_dependencies(["plugin_a", "plugin_b"])
    
    def test_missing_dependency(self):
        """Test handling of missing dependencies."""
        resolver = DependencyResolver()
        
        # Plugin A depends on non-existent Plugin B
        plugin_a = PluginInfo("plugin_a", "1.0.0", "Plugin A", "Test", "agent", ["plugin_b"], "a")
        
        resolver.add_plugin(plugin_a)
        
        with pytest.raises(PluginDependencyError, match="Dependency validation failed"):
            resolver.resolve_dependencies(["plugin_a"])
    
    def test_version_requirement_validation(self):
        """Test version requirement validation."""
        resolver = DependencyResolver()
        
        # Plugin A requires Plugin B >= 2.0.0, but Plugin B is 1.0.0
        plugin_a = PluginInfo("plugin_a", "1.0.0", "Plugin A", "Test", "agent", ["plugin_b>=2.0.0"], "a")
        plugin_b = PluginInfo("plugin_b", "1.0.0", "Plugin B", "Test", "agent", [], "b")
        
        resolver.add_plugin(plugin_a)
        resolver.add_plugin(plugin_b)
        
        with pytest.raises(PluginDependencyError, match="version"):
            resolver.resolve_dependencies(["plugin_a"])


class TestPluginDiscovery:
    """Test plugin discovery functionality."""
    
    def test_discover_from_directory_empty(self):
        """Test discovery from empty directory."""
        discovery = PluginDiscovery()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            discovered = discovery.discover_from_directory(temp_dir)
            assert discovered == []
    
    def test_discover_from_directory_with_metadata(self):
        """Test discovery from directory with plugin metadata."""
        discovery = PluginDiscovery()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a plugin directory with metadata
            plugin_dir = Path(temp_dir) / "test_plugin"
            plugin_dir.mkdir()
            
            # Create __init__.py
            (plugin_dir / "__init__.py").write_text("")
            
            # Create plugin.json metadata
            metadata = {
                "name": "test_plugin",
                "version": "1.0.0",
                "description": "Test plugin",
                "author": "Test Author",
                "plugin_type": "agent",
                "dependencies": [],
                "entry_point": "test_plugin"
            }
            (plugin_dir / "plugin.json").write_text(json.dumps(metadata))
            
            discovered = discovery.discover_from_directory(temp_dir)
            
            assert len(discovered) == 1
            assert discovered[0]["name"] == "test_plugin"
            assert discovered[0]["version"] == "1.0.0"
    
    def test_discover_from_config(self):
        """Test discovery from configuration file."""
        discovery = PluginDiscovery()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "plugins": [
                    {
                        "name": "config_plugin",
                        "version": "1.0.0",
                        "description": "Plugin from config",
                        "author": "Test",
                        "plugin_type": "agent",
                        "dependencies": [],
                        "entry_point": "config_plugin:ConfigPlugin"
                    }
                ]
            }
            json.dump(config, f)
            config_file = f.name
        
        try:
            discovered = discovery.discover_from_config(config_file)
            
            assert len(discovered) == 1
            assert discovered[0]["name"] == "config_plugin"
            assert discovered[0]["type"] == "config"
        finally:
            os.unlink(config_file)
    
    def test_validate_plugin(self):
        """Test plugin validation."""
        discovery = PluginDiscovery()
        plugin = MockAgentPlugin()
        
        errors = discovery.validate_plugin(plugin)
        
        assert errors == []  # Should be valid
    
    def test_validate_invalid_plugin(self):
        """Test validation of invalid plugin."""
        discovery = PluginDiscovery()
        
        # Create a mock plugin missing required methods
        invalid_plugin = Mock()
        invalid_plugin.get_plugin_info = Mock(side_effect=Exception("Test error"))
        
        errors = discovery.validate_plugin(invalid_plugin)
        
        assert len(errors) > 0
        assert any("get_plugin_info" in error for error in errors)


class TestPluginManager:
    """Test plugin manager functionality."""
    
    def test_plugin_manager_initialization(self):
        """Test plugin manager initialization."""
        manager = PluginManager()
        
        assert isinstance(manager.registry, PluginRegistry)
        assert isinstance(manager.discovery, PluginDiscovery)
        assert isinstance(manager.dependency_resolver, DependencyResolver)
        assert manager.loaded_plugins == set()
    
    def test_add_plugin_directory(self):
        """Test adding plugin directory."""
        manager = PluginManager()
        initial_count = len(manager.plugin_directories)
        
        manager.add_plugin_directory("/test/path")
        
        assert len(manager.plugin_directories) == initial_count + 1
        assert "/test/path" in manager.plugin_directories
    
    @patch('ai_agent_framework.plugins.discovery.PluginDiscovery.discover_from_directory')
    def test_discover_plugins(self, mock_discover):
        """Test plugin discovery."""
        manager = PluginManager(["/test/path"])
        mock_discover.return_value = [
            {"name": "test_plugin", "version": "1.0.0", "plugin_type": "agent"}
        ]
        
        discovered = manager.discover_plugins()
        
        assert len(discovered) == 1
        assert discovered[0]["name"] == "test_plugin"
        mock_discover.assert_called_once_with("/test/path")
    
    def test_set_get_plugin_config(self):
        """Test setting and getting plugin configuration."""
        manager = PluginManager()
        config = {"key": "value"}
        
        manager.set_plugin_config("test_plugin", config)
        retrieved_config = manager.get_plugin_config("test_plugin")
        
        assert retrieved_config == config
    
    def test_get_plugin_status(self):
        """Test getting plugin status."""
        manager = PluginManager()
        
        # Add some mock discovered plugins
        manager.discovery.discovered_plugins = {
            "test_plugin": {
                "name": "test_plugin",
                "version": "1.0.0",
                "plugin_type": "agent"
            }
        }
        
        status = manager.get_plugin_status()
        
        assert status["discovered"] == 1
        assert status["loaded"] == 0
        assert "test_plugin" in status["plugins"]
    
    def test_cleanup(self):
        """Test plugin manager cleanup."""
        manager = PluginManager()
        
        # Add some mock data
        manager.loaded_plugins.add("test_plugin")
        manager.plugin_configs["test_plugin"] = {"key": "value"}
        manager.discovery.discovered_plugins["test_plugin"] = {"name": "test_plugin"}
        
        manager.cleanup()
        
        assert len(manager.loaded_plugins) == 0
        assert len(manager.plugin_configs) == 0
        assert len(manager.discovery.discovered_plugins) == 0


class TestPluginIntegration:
    """Integration tests for the plugin system."""
    
    def test_full_plugin_lifecycle(self):
        """Test complete plugin lifecycle: discover, load, use, unload."""
        manager = PluginManager()
        
        # Mock discovery to return our test plugin
        test_plugin_metadata = {
            "name": "test_plugin",
            "version": "1.0.0",
            "description": "Test plugin",
            "author": "Test",
            "plugin_type": "agent",
            "dependencies": [],
            "entry_point": "test_plugin",
            "type": "mock"
        }
        
        manager.discovery.discovered_plugins["test_plugin"] = test_plugin_metadata
        
        # Mock the plugin loading to return our mock plugin
        with patch.object(manager.discovery, 'load_plugin', return_value=MockAgentPlugin()):
            # Load the plugin
            loaded = manager.load_plugins(["test_plugin"])
            
            assert "test_plugin" in loaded
            assert manager.is_plugin_loaded("test_plugin")
            
            # Use the plugin to create an agent
            agent = manager.create_agent("mock", "test_agent")
            assert isinstance(agent, MockAgent)
            
            # Check supported types
            agent_types = manager.get_supported_agent_types()
            assert "mock" in agent_types
            
            # Unload the plugin
            unloaded = manager.unload_plugins(["test_plugin"])
            assert "test_plugin" in unloaded
            assert not manager.is_plugin_loaded("test_plugin")
    
    def test_plugin_dependency_resolution_integration(self):
        """Test plugin loading with dependencies."""
        manager = PluginManager()
        
        # Create plugins with dependencies
        plugin_a_metadata = {
            "name": "plugin_a",
            "version": "1.0.0",
            "description": "Plugin A",
            "author": "Test",
            "plugin_type": "agent",
            "dependencies": ["plugin_b"],
            "entry_point": "plugin_a",
            "type": "mock"
        }
        
        plugin_b_metadata = {
            "name": "plugin_b",
            "version": "1.0.0",
            "description": "Plugin B",
            "author": "Test",
            "plugin_type": "agent",
            "dependencies": [],
            "entry_point": "plugin_b",
            "type": "mock"
        }
        
        manager.discovery.discovered_plugins["plugin_a"] = plugin_a_metadata
        manager.discovery.discovered_plugins["plugin_b"] = plugin_b_metadata
        
        # Mock plugin loading
        def mock_load_plugin(metadata):
            if metadata["name"] == "plugin_a":
                plugin = MockAgentPlugin()
                plugin.get_plugin_info = lambda: PluginInfo(
                    "plugin_a", "1.0.0", "Plugin A", "Test", "agent", ["plugin_b"], "plugin_a"
                )
                # Override to provide different agent type
                plugin.get_agent_classes = lambda: {'mock_a': MockAgent}
                plugin.get_supported_agent_types = lambda: ['mock_a']
                plugin.create_agent = lambda agent_type, name, config=None: MockAgent(name, config) if agent_type == 'mock_a' else None
                return plugin
            elif metadata["name"] == "plugin_b":
                plugin = MockAgentPlugin()
                plugin.get_plugin_info = lambda: PluginInfo(
                    "plugin_b", "1.0.0", "Plugin B", "Test", "agent", [], "plugin_b"
                )
                # Override to provide different agent type
                plugin.get_agent_classes = lambda: {'mock_b': MockAgent}
                plugin.get_supported_agent_types = lambda: ['mock_b']
                plugin.create_agent = lambda agent_type, name, config=None: MockAgent(name, config) if agent_type == 'mock_b' else None
                return plugin
        
        with patch.object(manager.discovery, 'load_plugin', side_effect=mock_load_plugin):
            # Load plugin A (should automatically load plugin B first)
            loaded = manager.load_plugins(["plugin_a", "plugin_b"])
            
            # Both plugins should be loaded
            assert "plugin_a" in loaded
            assert "plugin_b" in loaded
            assert manager.is_plugin_loaded("plugin_a")
            assert manager.is_plugin_loaded("plugin_b")


if __name__ == "__main__":
    pytest.main([__file__])