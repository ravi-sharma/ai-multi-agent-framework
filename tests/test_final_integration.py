"""Final integration tests for the complete AI Agent Framework."""

import pytest
import asyncio
import json
import os
import tempfile
import yaml
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app
from core.llm_provider import LLMManager
from core.agent_registry import AgentRegistry
from routing.agent_router import AgentRouter
from core.criteria_evaluator import CriteriaEngine
from agents.sales_agent import SalesAgent
from agents.default_agent import DefaultAgent
from models.data_models import EmailMessage, TriggerData
from config.loader import ConfigLoader, ConfigManager
from tests.utils.test_data_manager import TestDataManager
from tests.utils.mock_providers import MockProviderFactory


class TestFinalIntegration:
    """Final integration tests for the complete AI Agent Framework."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def test_data_manager(self):
        """Create test data manager."""
        return TestDataManager()
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager with reliable provider."""
        manager = LLMManager()
        mock_provider = MockProviderFactory.create_reliable_provider()
        manager.register_provider("mock", mock_provider)
        manager.set_default_provider("mock")
        return manager
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary configuration directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample configuration files
            config_data = {
                "llm": {
                    "default_provider": "mock",
                    "providers": {
                        "mock": {
                            "model": "mock-model",
                            "api_key": "test-key"
                        }
                    }
                },
                "agents": {
                    "sales_agent": {
                        "enabled": True,
                        "llm_provider": "mock"
                    },
                    "default_agent": {
                        "enabled": True,
                        "llm_provider": "mock"
                    }
                }
            }
            
            criteria_data = {
                "criteria": [
                    {
                        "name": "sales_email",
                        "priority": 1,
                        "conditions": [
                            {
                                "field": "email.subject",
                                "operator": "contains",
                                "values": ["buy", "purchase", "sale", "quote", "pricing"]
                            }
                        ],
                        "agent": "sales_agent",
                        "enabled": True
                    },
                    {
                        "name": "support_email",
                        "priority": 2,
                        "conditions": [
                            {
                                "field": "email.subject",
                                "operator": "contains",
                                "values": ["help", "support", "issue", "problem"]
                            }
                        ],
                        "agent": "support_agent",
                        "enabled": True
                    }
                ]
            }
            
            # Write configuration files
            with open(os.path.join(temp_dir, "config.yaml"), "w") as f:
                yaml.dump(config_data, f)
            
            with open(os.path.join(temp_dir, "criteria.yaml"), "w") as f:
                yaml.dump(criteria_data, f)
            
            yield temp_dir
    
    @pytest.mark.asyncio
    async def test_complete_email_to_sales_agent_workflow(self, client, test_data_manager, mock_llm_manager, temp_config_dir):
        """Test complete email-to-sales-agent workflow with all components integrated."""
        
        # Patch the LLM manager and configuration
        with patch('ai_agent_framework.core.llm_provider.get_llm_manager', return_value=mock_llm_manager):
            with patch.dict(os.environ, {'CONFIG_DIR': temp_config_dir}):
                
                # Create sales email
                email = test_data_manager.create_sample_email("sales")
                email.subject = "Interested in purchasing your premium package"
                email.sender = "customer@bigcorp.com"
                email.body = "Hi, I'm interested in buying your premium package for our company. Can you provide pricing?"
                
                request_data = email.to_dict()
                
                # Send email trigger
                response = client.post("/api/trigger/email", json=request_data)
                
                # Verify response
                assert response.status_code == 200
                response_data = response.json()
                
                assert response_data["success"] is True
                assert "trigger_id" in response_data
                assert "processing_time" in response_data
                assert response_data["processing_time"] > 0
                
                # Verify the response indicates sales processing
                message = response_data["message"].lower()
                assert any(keyword in message for keyword in ["sales", "customer", "purchase", "processed"])
    
    @pytest.mark.asyncio
    async def test_agent_routing_with_criteria_evaluation(self, mock_llm_manager, temp_config_dir):
        """Test agent routing with criteria evaluation."""
        
        # Create components
        criteria_engine = CriteriaEngine()
        agent_registry = AgentRegistry()
        
        # Load criteria from config
        criteria_config_path = os.path.join(temp_config_dir, "criteria.yaml")
        with open(criteria_config_path, 'r') as f:
            criteria_data = yaml.safe_load(f)
        
        criteria_engine.load_criteria_from_dict(criteria_data)
        
        # Create and register agents
        sales_agent = SalesAgent(
            name="sales_agent",
            config={"test_mode": True},
            llm_manager=mock_llm_manager
        )
        
        default_agent = DefaultAgent(
            name="default_agent",
            config={"test_mode": True},
            llm_manager=mock_llm_manager
        )
        
        agent_registry.register_agent("sales_agent", sales_agent)
        agent_registry.register_agent("default_agent", default_agent)
        
        # Create router
        router = AgentRouter(
            criteria_engine=criteria_engine,
            agent_registry=agent_registry,
            default_agent_name="default_agent"
        )
        
        # Test different email types
        test_cases = [
            {
                "name": "Sales Email",
                "email": EmailMessage(
                    subject="Want to buy your product",
                    sender="buyer@company.com",
                    recipient="sales@ourcompany.com",
                    body="I'm interested in purchasing your premium package.",
                    headers={}
                ),
                "expected_agent": "sales_agent"
            },
            {
                "name": "Support Email", 
                "email": EmailMessage(
                    subject="Need help with installation",
                    sender="user@company.com",
                    recipient="support@ourcompany.com",
                    body="I'm having trouble installing the software.",
                    headers={}
                ),
                "expected_agent": "default_agent"  # No support agent registered, should fallback
            },
            {
                "name": "General Email",
                "email": EmailMessage(
                    subject="General inquiry about your company",
                    sender="info@somewhere.com",
                    recipient="info@ourcompany.com",
                    body="Can you tell me more about your company?",
                    headers={}
                ),
                "expected_agent": "default_agent"
            }
        ]
        
        for test_case in test_cases:
            # Create trigger data
            trigger_data = TriggerData(
                source="email",
                timestamp=datetime.now(),
                data={"email": test_case["email"].to_dict()}
            )
            
            # Route and process
            result = await router.route(trigger_data)
            
            # Verify routing
            assert result.success is True
            assert result.agent_name == test_case["expected_agent"]
            assert result.execution_time > 0
            
            # Verify output structure
            assert "agent_type" in result.output
            if test_case["expected_agent"] == "sales_agent":
                assert "sales_notes" in result.output
                assert "customer_email" in result.output
                assert "urgency_level" in result.output
    
    @pytest.mark.asyncio
    async def test_configuration_loading_and_validation(self, temp_config_dir):
        """Test configuration loading and validation."""
        
        # Test configuration loading
        config_manager = ConfigManager()
        config = config_manager.load_framework_config(os.path.join(temp_config_dir, "config.yaml"))
        
        # Verify configuration structure
        assert hasattr(config, 'llm_config')
        assert hasattr(config, 'agent_configs')
        assert config.llm_config.default_provider == "mock"
        assert "mock" in config.llm_config.providers
        assert "sales_agent" in config.agent_configs
        
        # Test criteria loading
        criteria_config_path = os.path.join(temp_config_dir, "criteria.yaml")
        with open(criteria_config_path, 'r') as f:
            criteria_data = yaml.safe_load(f)
        
        assert "criteria" in criteria_data
        assert len(criteria_data["criteria"]) >= 2
        
        # Verify criteria structure
        sales_criteria = next(c for c in criteria_data["criteria"] if c["name"] == "sales_email")
        assert sales_criteria["agent"] == "sales_agent"
        assert sales_criteria["priority"] == 1
        assert len(sales_criteria["conditions"]) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, client, test_data_manager):
        """Test error handling and recovery in the complete workflow."""
        
        # Test with failing LLM provider
        failing_manager = LLMManager()
        failing_provider = MockProviderFactory.create_failing_provider()
        failing_manager.register_provider("failing", failing_provider)
        failing_manager.set_default_provider("failing")
        
        with patch('ai_agent_framework.core.llm_provider.get_llm_manager', return_value=failing_manager):
            
            # Create email data
            email = test_data_manager.create_sample_email("sales")
            request_data = email.to_dict()
            
            # Send request - should handle LLM failure gracefully
            response = client.post("/api/trigger/email", json=request_data)
            
            # Should still return 200 with graceful degradation
            assert response.status_code == 200
            response_data = response.json()
            
            # Should have basic processing even with LLM failure
            assert "trigger_id" in response_data
            assert "processing_time" in response_data
            
            # May succeed with fallback or fail gracefully
            if response_data["success"]:
                # Successful fallback processing
                assert "processed" in response_data["message"].lower()
            else:
                # Graceful failure
                assert "failed" in response_data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_integration(self, client, test_data_manager, mock_llm_manager):
        """Test concurrent processing of multiple requests."""
        
        with patch('ai_agent_framework.core.llm_provider.get_llm_manager', return_value=mock_llm_manager):
            
            # Create multiple different email types
            emails = [
                test_data_manager.create_sample_email("sales"),
                test_data_manager.create_sample_email("support"),
                test_data_manager.create_sample_email("general"),
                test_data_manager.create_sample_email("sales"),
                test_data_manager.create_sample_email("support")
            ]
            
            # Customize emails for uniqueness
            for i, email in enumerate(emails):
                email.sender = f"concurrent{i}@example.com"
                email.subject = f"Concurrent Test {i}: {email.subject}"
            
            # Send concurrent requests
            import concurrent.futures
            
            def make_request(email_data):
                return client.post("/api/trigger/email", json=email_data.to_dict())
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request, email) for email in emails]
                responses = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Verify all responses
            assert len(responses) == 5
            trigger_ids = []
            
            for response in responses:
                assert response.status_code == 200
                response_data = response.json()
                assert response_data["success"] is True
                assert "trigger_id" in response_data
                trigger_ids.append(response_data["trigger_id"])
            
            # Verify all trigger IDs are unique
            assert len(set(trigger_ids)) == len(trigger_ids)
    
    @pytest.mark.asyncio
    async def test_monitoring_and_health_checks(self, client):
        """Test monitoring and health check integration."""
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert "components" in health_data
        
        # Test monitoring endpoints
        response = client.get("/api/monitoring/health")
        assert response.status_code == 200
        
        response = client.get("/api/monitoring/metrics")
        assert response.status_code == 200
        
        response = client.get("/api/monitoring/status")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_email_service_integration(self, mock_llm_manager):
        """Test email service integration (without actual email server)."""
        
        from email.service import EmailService
        from models.config_models import EmailConfig
        
        # Create email service with test configuration
        email_config = EmailConfig(
            enabled=False,  # Disabled for testing
            server="test.example.com",
            port=993,
            username="test@example.com",
            password="test_password",
            use_ssl=True,
            poll_interval=60
        )
        
        email_service = EmailService()
        email_service.configure(email_config)
        
        # Verify configuration
        assert email_service.is_configured() is True
        assert email_service.is_running() is False  # Not started
        
        # Test email processing (without actual polling)
        test_email = EmailMessage(
            subject="Test Email Processing",
            sender="test@example.com",
            recipient="agent@ourcompany.com",
            body="This is a test email for processing.",
            headers={"Message-ID": "<test@example.com>"}
        )
        
        # Process email through service
        result = await email_service.process_email(test_email)
        
        # Verify processing result
        assert result is not None
        assert "trigger_id" in result
    
    @pytest.mark.asyncio
    async def test_plugin_system_integration(self):
        """Test plugin system integration."""
        
        from plugins.plugin_manager import PluginManager
        
        # Create plugin manager
        plugin_manager = PluginManager()
        
        # Test plugin discovery (should work even with no plugins)
        available_plugins = plugin_manager.get_available_plugins()
        assert isinstance(available_plugins, list)
        
        # Test plugin loading (should handle empty plugin directory)
        loaded_plugins = plugin_manager.load_plugins("nonexistent_plugin_dir")
        assert isinstance(loaded_plugins, list)
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, client, test_data_manager, mock_llm_manager):
        """Test system performance under moderate load."""
        
        with patch('ai_agent_framework.core.llm_provider.get_llm_manager', return_value=mock_llm_manager):
            
            # Create test email
            email = test_data_manager.create_sample_email("sales")
            request_data = email.to_dict()
            
            # Measure performance for sequential requests
            start_time = datetime.now()
            response_times = []
            
            for i in range(20):  # Increased load
                request_start = datetime.now()
                response = client.post("/api/trigger/email", json=request_data)
                request_end = datetime.now()
                
                assert response.status_code == 200
                response_data = response.json()
                assert response_data["success"] is True
                
                response_times.append((request_end - request_start).total_seconds())
            
            total_time = (datetime.now() - start_time).total_seconds()
            avg_response_time = sum(response_times) / len(response_times)
            
            # Performance assertions
            assert avg_response_time < 3.0  # Average response time under 3 seconds
            assert max(response_times) < 10.0  # No single request over 10 seconds
            assert total_time < 60.0  # Total time for 20 requests under 60 seconds
            
            print(f"Performance metrics:")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  Max response time: {max(response_times):.3f}s")
            print(f"  Total time: {total_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_data_validation_and_serialization(self, test_data_manager):
        """Test data validation and serialization throughout the system."""
        
        from models.validation import validate_email_message, validate_trigger_data
        from models.serialization import serialize_agent_result, deserialize_agent_result
        
        # Test email validation
        email = test_data_manager.create_sample_email("sales")
        validation_result = validate_email_message(email)
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0
        
        # Test trigger data validation
        trigger_data = TriggerData(
            source="email",
            timestamp=datetime.now(),
            data={"email": email.to_dict()}
        )
        
        validation_result = validate_trigger_data(trigger_data)
        assert validation_result.is_valid is True
        
        # Test serialization/deserialization
        from models.data_models import AgentResult
        
        agent_result = AgentResult(
            success=True,
            output={"test": "data"},
            notes=["Test note"],
            execution_time=1.5,
            agent_name="test_agent"
        )
        
        # Serialize
        serialized = serialize_agent_result(agent_result)
        assert isinstance(serialized, dict)
        assert serialized["success"] is True
        assert serialized["agent_name"] == "test_agent"
        
        # Deserialize
        deserialized = deserialize_agent_result(serialized)
        assert deserialized.success is True
        assert deserialized.agent_name == "test_agent"
        assert deserialized.execution_time == 1.5


class TestDeploymentValidation:
    """Test deployment-related functionality."""
    
    @pytest.mark.asyncio
    async def test_application_startup_and_shutdown(self):
        """Test application startup and shutdown sequence."""
        
        # Test that the application can start up
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        
        root_data = response.json()
        assert "message" in root_data
        assert "version" in root_data
        assert "endpoints" in root_data
        
        # Verify all expected endpoints are listed
        expected_endpoints = [
            "webhook_trigger",
            "email_trigger", 
            "generic_trigger",
            "health",
            "metrics",
            "dashboard"
        ]
        
        for endpoint in expected_endpoints:
            assert endpoint in root_data["endpoints"]
    
    @pytest.mark.asyncio
    async def test_docker_compatibility(self):
        """Test Docker deployment compatibility."""
        
        # Test environment variable handling
        test_env_vars = {
            "OPENAI_API_KEY": "test-key",
            "ANTHROPIC_API_KEY": "test-key",
            "LOG_LEVEL": "INFO",
            "CONFIG_DIR": "/app/config"
        }
        
        with patch.dict(os.environ, test_env_vars):
            # Test that the application can handle Docker-style environment variables
            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_configuration_file_formats(self, temp_config_dir):
        """Test different configuration file formats."""
        
        # Test YAML configuration
        yaml_config = {
            "llm": {
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "model": "gpt-3.5-turbo",
                        "api_key": "${OPENAI_API_KEY}"
                    }
                }
            }
        }
        
        yaml_path = os.path.join(temp_config_dir, "test_config.yaml")
        with open(yaml_path, "w") as f:
            yaml.dump(yaml_config, f)
        
        # Test JSON configuration
        json_config = {
            "criteria": [
                {
                    "name": "test_criteria",
                    "priority": 1,
                    "conditions": [
                        {
                            "field": "email.subject",
                            "operator": "contains",
                            "values": ["test"]
                        }
                    ],
                    "agent": "test_agent"
                }
            ]
        }
        
        json_path = os.path.join(temp_config_dir, "test_criteria.json")
        with open(json_path, "w") as f:
            json.dump(json_config, f)
        
        # Verify files can be loaded
        assert os.path.exists(yaml_path)
        assert os.path.exists(json_path)
        
        # Test loading
        with open(yaml_path, 'r') as f:
            loaded_yaml = yaml.safe_load(f)
            assert loaded_yaml["llm"]["default_provider"] == "openai"
        
        with open(json_path, 'r') as f:
            loaded_json = json.load(f)
            assert loaded_json["criteria"][0]["name"] == "test_criteria"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])