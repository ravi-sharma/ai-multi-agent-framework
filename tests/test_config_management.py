"""Unit tests for configuration management system."""

import os
import tempfile
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

from configs.base_config import ConfigLoader, ConfigManager, ConfigurationError
from models.config_models import (
    FrameworkConfig, AgentConfig, LLMConfig, CriteriaConfig, 
    Condition, WorkflowConfig
)


class TestConfigLoader:
    """Test cases for ConfigLoader."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.loader = ConfigLoader()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_config_file(self, config_data: dict, filename: str = "config.yaml") -> str:
        """Create a temporary configuration file."""
        config_path = os.path.join(self.temp_dir, filename)
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        return config_path
    
    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_data = {
            'default_llm_provider': 'openai',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'test-key',
                    'timeout': 30,
                    'max_retries': 3
                }
            },
            'agents': {
                'test_agent': {
                    'name': 'test_agent',
                    'agent_type': 'TestAgent',
                    'enabled': True,
                    'llm_provider': 'openai'
                }
            },
            'criteria': [
                {
                    'name': 'test_criteria',
                    'priority': 1,
                    'agent': 'test_agent',
                    'conditions': [
                        {
                            'field': 'email.subject',
                            'operator': 'contains',
                            'values': ['test']
                        }
                    ]
                }
            ]
        }
        
        config_path = self.create_temp_config_file(config_data)
        config = self.loader.load_config(config_path)
        
        assert isinstance(config, FrameworkConfig)
        assert config.default_llm_provider == 'openai'
        assert 'openai' in config.llm_providers
        assert 'test_agent' in config.agents
        assert len(config.criteria) == 1
    
    def test_load_config_with_env_vars(self):
        """Test loading configuration with environment variable substitution."""
        config_data = {
            'default_llm_provider': 'openai',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'api_key': '${TEST_API_KEY}',
                    'base_url': '${TEST_BASE_URL:https://api.openai.com}'
                }
            }
        }
        
        config_path = self.create_temp_config_file(config_data)
        
        with patch.dict(os.environ, {'TEST_API_KEY': 'secret-key'}):
            config = self.loader.load_config(config_path)
            
            openai_config = config.llm_providers['openai']
            assert openai_config.api_key == 'secret-key'
            assert openai_config.base_url == 'https://api.openai.com'  # default value
    
    def test_load_config_missing_file(self):
        """Test loading configuration from non-existent file."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            self.loader.load_config("/non/existent/file.yaml")
    
    def test_load_config_invalid_yaml(self):
        """Test loading configuration with invalid YAML."""
        config_path = os.path.join(self.temp_dir, "invalid.yaml")
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(ConfigurationError, match="Failed to parse YAML file"):
            self.loader.load_config(config_path)
    
    def test_load_config_validation_error(self):
        """Test loading configuration that fails validation."""
        config_data = {
            'default_llm_provider': '',  # Invalid: empty provider
            'llm_providers': {}
        }
        
        config_path = self.create_temp_config_file(config_data)
        
        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            self.loader.load_config(config_path)
    
    def test_load_criteria_config(self):
        """Test loading criteria configuration."""
        criteria_data = {
            'criteria': [
                {
                    'name': 'sales_email',
                    'priority': 1,
                    'agent': 'sales_agent',
                    'conditions': [
                        {
                            'field': 'email.subject',
                            'operator': 'contains',
                            'values': ['buy', 'sale'],
                            'case_sensitive': False
                        }
                    ]
                }
            ]
        }
        
        criteria_path = self.create_temp_config_file(criteria_data, "criteria.yaml")
        criteria_list = self.loader.load_criteria_config(criteria_path)
        
        assert len(criteria_list) == 1
        assert criteria_list[0].name == 'sales_email'
        assert criteria_list[0].priority == 1
        assert len(criteria_list[0].conditions) == 1
    
    def test_load_criteria_config_missing_key(self):
        """Test loading criteria configuration without 'criteria' key."""
        criteria_data = {'invalid': 'structure'}
        
        criteria_path = self.create_temp_config_file(criteria_data, "criteria.yaml")
        
        with pytest.raises(ConfigurationError, match="Criteria file must contain 'criteria' key"):
            self.loader.load_criteria_config(criteria_path)
    
    def test_save_config(self):
        """Test saving configuration to file."""
        config = FrameworkConfig(
            default_llm_provider='openai',
            llm_providers={
                'openai': LLMConfig(
                    provider='openai',
                    model='gpt-3.5-turbo',
                    api_key='test-key'
                )
            }
        )
        
        config_path = os.path.join(self.temp_dir, "saved_config.yaml")
        self.loader.save_config(config, config_path)
        
        assert os.path.exists(config_path)
        
        # Load and verify
        loaded_config = self.loader.load_config(config_path)
        assert loaded_config.default_llm_provider == 'openai'
    
    def test_env_var_substitution_with_defaults(self):
        """Test environment variable substitution with default values."""
        test_data = {
            'key1': '${EXISTING_VAR}',
            'key2': '${NON_EXISTING_VAR:default_value}',
            'key3': '${ANOTHER_NON_EXISTING:}',  # empty default
            'nested': {
                'key4': '${NESTED_VAR:nested_default}'
            }
        }
        
        with patch.dict(os.environ, {'EXISTING_VAR': 'existing_value'}):
            result = self.loader._substitute_env_vars(test_data)
            
            assert result['key1'] == 'existing_value'
            assert result['key2'] == 'default_value'
            assert result['key3'] == ''
            assert result['nested']['key4'] == 'nested_default'
    
    def test_parse_workflow_config(self):
        """Test parsing workflow configuration."""
        agent_data = {
            'name': 'test_agent',
            'agent_type': 'TestAgent',
            'workflow_config': {
                'max_retries': 5,
                'timeout': 600,
                'workflow_steps': ['step1', 'step2'],
                'step_configs': {
                    'step1': {'param': 'value'}
                }
            }
        }
        
        agent_config = self.loader._parse_agent_config(agent_data)
        
        assert agent_config.workflow_config is not None
        assert agent_config.workflow_config.max_retries == 5
        assert agent_config.workflow_config.timeout == 600
        assert agent_config.workflow_config.workflow_steps == ['step1', 'step2']
    
    def test_load_llm_config_nested_format(self):
        """Test loading LLM configuration with nested format."""
        llm_data = {
            'llm': {
                'providers': {
                    'openai': {
                        'model': 'gpt-4',
                        'api_key': 'test-key',
                        'timeout': 60
                    }
                }
            }
        }
        
        llm_path = self.create_temp_config_file(llm_data, "llm_nested.yaml")
        llm_providers = self.loader.load_llm_config(llm_path)
        
        assert len(llm_providers) == 1
        assert 'openai' in llm_providers
        assert llm_providers['openai'].provider == 'openai'
        assert llm_providers['openai'].model == 'gpt-4'
    
    def test_load_llm_config_flat_format(self):
        """Test loading LLM configuration with flat format."""
        llm_data = {
            'providers': {
                'anthropic': {
                    'model': 'claude-3-sonnet',
                    'api_key': 'test-key-2',
                    'timeout': 45
                }
            }
        }
        
        llm_path = self.create_temp_config_file(llm_data, "llm_flat.yaml")
        llm_providers = self.loader.load_llm_config(llm_path)
        
        assert len(llm_providers) == 1
        assert 'anthropic' in llm_providers
        assert llm_providers['anthropic'].provider == 'anthropic'
        assert llm_providers['anthropic'].model == 'claude-3-sonnet'
    
    def test_load_llm_config_invalid_format(self):
        """Test loading LLM configuration with invalid format."""
        llm_data = {
            'invalid': 'structure'
        }
        
        llm_path = self.create_temp_config_file(llm_data, "llm_invalid.yaml")
        
        with pytest.raises(ConfigurationError, match="must contain.*providers"):
            self.loader.load_llm_config(llm_path)


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ConfigManager()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_config_file(self, config_data: dict) -> str:
        """Create a temporary configuration file."""
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        return config_path
    
    def test_load_framework_config_caching(self):
        """Test that configuration is cached properly."""
        config_data = {
            'default_llm_provider': 'openai',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'test-key'
                }
            }
        }
        
        config_path = self.create_temp_config_file(config_data)
        
        # First load
        config1 = self.manager.load_framework_config(config_path)
        
        # Second load should return cached version
        config2 = self.manager.load_framework_config(config_path)
        
        assert config1 is config2  # Same object reference
    
    def test_force_reload(self):
        """Test force reload functionality."""
        config_data = {
            'default_llm_provider': 'openai',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'test-key'
                }
            }
        }
        
        config_path = self.create_temp_config_file(config_data)
        
        # First load
        config1 = self.manager.load_framework_config(config_path)
        
        # Force reload should create new object
        config2 = self.manager.load_framework_config(config_path, force_reload=True)
        
        assert config1 is not config2  # Different object references
        assert config1.default_llm_provider == config2.default_llm_provider  # Same content
    
    def test_get_cached_config(self):
        """Test getting cached configuration."""
        assert self.manager.get_cached_config() is None
        
        config_data = {
            'default_llm_provider': 'openai',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'test-key'
                }
            }
        }
        
        config_path = self.create_temp_config_file(config_data)
        loaded_config = self.manager.load_framework_config(config_path)
        cached_config = self.manager.get_cached_config()
        
        assert cached_config is loaded_config
    
    def test_clear_cache(self):
        """Test clearing configuration cache."""
        config_data = {
            'default_llm_provider': 'openai',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'test-key'
                }
            }
        }
        
        config_path = self.create_temp_config_file(config_data)
        self.manager.load_framework_config(config_path)
        
        assert self.manager.get_cached_config() is not None
        
        self.manager.clear_cache()
        
        assert self.manager.get_cached_config() is None
    
    def test_validate_config_file(self):
        """Test configuration file validation."""
        # Valid config
        valid_config_data = {
            'default_llm_provider': 'openai',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'test-key'
                }
            }
        }
        
        valid_config_path = self.create_temp_config_file(valid_config_data)
        errors = self.manager.validate_config_file(valid_config_path)
        assert len(errors) == 0
        
        # Invalid config
        invalid_config_data = {
            'default_llm_provider': '',  # Invalid
            'llm_providers': {}
        }
        
        invalid_config_path = os.path.join(self.temp_dir, "invalid.yaml")
        with open(invalid_config_path, 'w') as f:
            yaml.dump(invalid_config_data, f)
        
        errors = self.manager.validate_config_file(invalid_config_path)
        assert len(errors) > 0
    
    def test_get_llm_config(self):
        """Test getting LLM configuration by provider name."""
        config_data = {
            'default_llm_provider': 'openai',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'test-key'
                },
                'anthropic': {
                    'provider': 'anthropic',
                    'model': 'claude-3-sonnet',
                    'api_key': 'test-key-2'
                }
            }
        }
        
        config_path = self.create_temp_config_file(config_data)
        self.manager.load_framework_config(config_path)
        
        openai_config = self.manager.get_llm_config('openai')
        assert openai_config is not None
        assert openai_config.provider == 'openai'
        assert openai_config.model == 'gpt-3.5-turbo'
        
        anthropic_config = self.manager.get_llm_config('anthropic')
        assert anthropic_config is not None
        assert anthropic_config.provider == 'anthropic'
        
        non_existent = self.manager.get_llm_config('non_existent')
        assert non_existent is None
    
    def test_get_agent_config(self):
        """Test getting agent configuration by name."""
        config_data = {
            'default_llm_provider': 'openai',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'test-key'
                }
            },
            'agents': {
                'sales_agent': {
                    'name': 'sales_agent',
                    'agent_type': 'SalesAgent',
                    'enabled': True,
                    'llm_provider': 'openai'
                }
            }
        }
        
        config_path = self.create_temp_config_file(config_data)
        self.manager.load_framework_config(config_path)
        
        agent_config = self.manager.get_agent_config('sales_agent')
        assert agent_config is not None
        assert agent_config.name == 'sales_agent'
        assert agent_config.agent_type == 'SalesAgent'
        
        non_existent = self.manager.get_agent_config('non_existent')
        assert non_existent is None
    
    def test_get_criteria_configs(self):
        """Test getting all criteria configurations."""
        config_data = {
            'default_llm_provider': 'openai',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'test-key'
                }
            },
            'criteria': [
                {
                    'name': 'sales_email',
                    'priority': 1,
                    'agent': 'sales_agent',
                    'conditions': [
                        {
                            'field': 'email.subject',
                            'operator': 'contains',
                            'values': ['buy']
                        }
                    ]
                },
                {
                    'name': 'support_email',
                    'priority': 2,
                    'agent': 'support_agent',
                    'conditions': [
                        {
                            'field': 'email.subject',
                            'operator': 'contains',
                            'values': ['help']
                        }
                    ]
                }
            ]
        }
        
        config_path = self.create_temp_config_file(config_data)
        self.manager.load_framework_config(config_path)
        
        criteria_configs = self.manager.get_criteria_configs()
        assert len(criteria_configs) == 2
        assert criteria_configs[0].name == 'sales_email'
        assert criteria_configs[1].name == 'support_email'
    
    def test_load_llm_providers(self):
        """Test loading LLM providers from separate file."""
        llm_data = {
            'llm': {
                'providers': {
                    'openai': {
                        'model': 'gpt-4',
                        'api_key': '${OPENAI_API_KEY}',
                        'timeout': 60
                    },
                    'anthropic': {
                        'model': 'claude-3-opus',
                        'api_key': '${ANTHROPIC_API_KEY}',
                        'timeout': 45
                    }
                }
            }
        }
        
        llm_path = os.path.join(self.temp_dir, "llm.yaml")
        with open(llm_path, 'w') as f:
            yaml.dump(llm_data, f)
        
        llm_providers = self.manager.load_llm_providers(llm_path)
        
        assert len(llm_providers) == 2
        assert 'openai' in llm_providers
        assert 'anthropic' in llm_providers
        assert llm_providers['openai'].model == 'gpt-4'
        assert llm_providers['anthropic'].model == 'claude-3-opus'


class TestConfigurationIntegration:
    """Integration tests for configuration management."""
    
    def test_real_config_file_loading(self):
        """Test loading actual configuration files from the project."""
        # Test with the example config file
        config_path = "config/example_config.yaml"
        
        if os.path.exists(config_path):
            manager = ConfigManager()
            
            # Should load without errors
            config = manager.load_framework_config(config_path)
            
            assert isinstance(config, FrameworkConfig)
            assert config.default_llm_provider
            assert len(config.llm_providers) > 0
            assert len(config.agents) > 0
    
    def test_criteria_file_loading(self):
        """Test loading actual criteria files from the project."""
        criteria_path = "config/example_criteria.yaml"
        
        if os.path.exists(criteria_path):
            loader = ConfigLoader()
            
            # Should load without errors
            criteria_list = loader.load_criteria_config(criteria_path)
            
            assert len(criteria_list) > 0
            for criteria in criteria_list:
                assert isinstance(criteria, CriteriaConfig)
                assert criteria.name
                assert criteria.agent
                assert len(criteria.conditions) > 0