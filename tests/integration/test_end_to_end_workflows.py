"""End-to-end integration tests for complete workflows."""

import pytest
import asyncio
import json
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app
from core.llm_provider import LLMManager
from core.agent_registry import AgentRegistry
from agents.sales_agent import SalesAgent
from models.data_models import EmailMessage, TriggerData
from tests.utils.test_data_manager import TestDataManager
from tests.utils.mock_providers import MockProviderFactory


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows from trigger to response."""
    
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
    async def setup_test_environment(self, mock_llm_manager):
        """Set up test environment with mock components."""
        # Patch LLM manager in the application
        with patch('ai_agent_framework.core.llm_provider.get_llm_manager', return_value=mock_llm_manager):
            yield mock_llm_manager
    
    @pytest.mark.asyncio
    async def test_email_to_sales_agent_workflow(self, client, test_data_manager, setup_test_environment):
        """Test complete email-to-sales-agent workflow."""
        # Create sales email
        email_data = test_data_manager.create_sample_email("sales")
        request_data = email_data.to_dict()
        
        # Send email trigger
        response = client.post("/api/trigger/email", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["success"] is True
        assert "trigger_id" in response_data
        assert "processing_time" in response_data
        assert response_data["processing_time"] > 0
        
        # Verify the response contains expected sales processing indicators
        assert "sales" in response_data["message"].lower() or "customer" in response_data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_webhook_to_agent_workflow(self, client, test_data_manager, setup_test_environment):
        """Test webhook trigger to agent workflow."""
        # Create webhook payload
        webhook_data = test_data_manager.create_webhook_payload("github")
        
        # Send webhook trigger
        response = client.post("/api/trigger/webhook", json=webhook_data)
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["success"] is True
        assert "trigger_id" in response_data
        assert "github" in response_data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_sales_agent_complete_workflow(self, test_data_manager, setup_test_environment):
        """Test complete sales agent workflow with LLM integration."""
        llm_manager = setup_test_environment
        
        # Create sales agent
        sales_agent = SalesAgent(
            name="test_sales_agent",
            config={"test_mode": True},
            llm_manager=llm_manager
        )
        
        # Create test email data
        email_data = {
            "source": "email",
            "email": test_data_manager.create_sample_email("sales").to_dict()
        }
        
        # Process through sales agent
        result = await sales_agent.process(email_data)
        
        # Verify result
        assert result.success is True
        assert result.agent_name == "test_sales_agent"
        assert result.execution_time > 0
        assert "sales_notes" in result.output
        assert "customer_email" in result.output
        assert "urgency_level" in result.output
        
        # Verify sales notes structure
        sales_notes = result.output["sales_notes"]
        assert isinstance(sales_notes, dict)
        assert "customer_problem" in sales_notes
        assert "proposed_solution" in sales_notes
        assert "urgency_level" in sales_notes
    
    @pytest.mark.asyncio
    async def test_multiple_agent_types_workflow(self, client, test_data_manager, setup_test_environment):
        """Test workflow with multiple different agent types."""
        test_cases = [
            ("sales", test_data_manager.create_sample_email("sales")),
            ("support", test_data_manager.create_sample_email("support")),
            ("general", test_data_manager.create_sample_email("general"))
        ]
        
        results = []
        
        for email_type, email_data in test_cases:
            request_data = email_data.to_dict()
            response = client.post("/api/trigger/email", json=request_data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] is True
            
            results.append({
                "email_type": email_type,
                "response": response_data,
                "processing_time": response_data["processing_time"]
            })
        
        # Verify all requests were processed successfully
        assert len(results) == 3
        assert all(r["response"]["success"] for r in results)
        
        # Verify processing times are reasonable
        avg_processing_time = sum(r["processing_time"] for r in results) / len(results)
        assert avg_processing_time < 5.0  # Should process within 5 seconds on average
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, client, test_data_manager):
        """Test error recovery in end-to-end workflow."""
        # Create failing LLM manager
        failing_manager = LLMManager()
        failing_provider = MockProviderFactory.create_failing_provider()
        failing_manager.register_provider("failing", failing_provider)
        failing_manager.set_default_provider("failing")
        
        with patch('ai_agent_framework.core.llm_provider.get_llm_manager', return_value=failing_manager):
            # Create email data
            email_data = test_data_manager.create_sample_email("sales")
            request_data = email_data.to_dict()
            
            # Send request - should handle LLM failure gracefully
            response = client.post("/api/trigger/email", json=request_data)
            
            # Should still return 200 with graceful degradation
            assert response.status_code == 200
            response_data = response.json()
            
            # May succeed with fallback processing or fail gracefully
            assert "trigger_id" in response_data
            assert "processing_time" in response_data
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_processing(self, client, test_data_manager, setup_test_environment):
        """Test concurrent processing of multiple workflows."""
        # Create multiple email requests
        email_requests = []
        for i in range(5):
            email = test_data_manager.create_sample_email("sales")
            email.sender = f"concurrent{i}@example.com"
            email.subject = f"Concurrent Test {i}: {email.subject}"
            email_requests.append(email.to_dict())
        
        # Send concurrent requests
        import concurrent.futures
        import threading
        
        def make_request(email_data):
            return client.post("/api/trigger/email", json=email_data)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, email_data) for email_data in email_requests]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all responses
        assert len(responses) == 5
        for response in responses:
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] is True
            assert "trigger_id" in response_data
        
        # Verify all trigger IDs are unique
        trigger_ids = [response.json()["trigger_id"] for response in responses]
        assert len(set(trigger_ids)) == len(trigger_ids)
    
    @pytest.mark.asyncio
    async def test_workflow_with_invalid_data_recovery(self, client, test_data_manager, setup_test_environment):
        """Test workflow recovery with invalid input data."""
        # Test with various invalid data scenarios
        invalid_scenarios = [
            # Missing required fields
            {"subject": "Test", "body": "Test body"},  # Missing sender/recipient
            
            # Invalid email addresses
            {
                "subject": "Test",
                "sender": "invalid-email",
                "recipient": "also-invalid",
                "body": "Test body"
            },
            
            # Empty content
            {
                "subject": "",
                "sender": "test@example.com",
                "recipient": "recipient@example.com",
                "body": ""
            }
        ]
        
        for i, invalid_data in enumerate(invalid_scenarios):
            response = client.post("/api/trigger/email", json=invalid_data)
            
            # Should return validation error
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data  # FastAPI validation error format
    
    @pytest.mark.asyncio
    async def test_workflow_performance_under_load(self, client, test_data_manager, setup_test_environment):
        """Test workflow performance under moderate load."""
        # Create test data
        email_data = test_data_manager.create_sample_email("sales").to_dict()
        
        # Measure performance for sequential requests
        start_time = datetime.now()
        response_times = []
        
        for i in range(10):
            request_start = datetime.now()
            response = client.post("/api/trigger/email", json=email_data)
            request_end = datetime.now()
            
            assert response.status_code == 200
            response_times.append((request_end - request_start).total_seconds())
        
        total_time = (datetime.now() - start_time).total_seconds()
        avg_response_time = sum(response_times) / len(response_times)
        
        # Performance assertions
        assert avg_response_time < 2.0  # Average response time under 2 seconds
        assert max(response_times) < 5.0  # No single request over 5 seconds
        assert total_time < 25.0  # Total time for 10 requests under 25 seconds
    
    @pytest.mark.asyncio
    async def test_workflow_data_consistency(self, client, test_data_manager, setup_test_environment):
        """Test data consistency throughout the workflow."""
        # Create email with specific identifiable content
        email = test_data_manager.create_sample_email("sales")
        email.subject = "UNIQUE_TEST_SUBJECT_12345"
        email.sender = "unique_sender@testdomain.com"
        email.body = "This is a unique test message with specific content for validation."
        
        request_data = email.to_dict()
        
        # Send request
        response = client.post("/api/trigger/email", json=request_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        
        # Verify that the unique identifiers are preserved in processing
        # (This would require access to internal processing logs or state)
        # For now, we verify the request was processed successfully
        assert "trigger_id" in response_data
        assert response_data["processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self, client, test_data_manager):
        """Test workflow handling of timeouts."""
        # Create slow LLM manager
        slow_manager = LLMManager()
        slow_provider = MockProviderFactory.create_slow_provider(delay=10.0)  # 10 second delay
        slow_manager.register_provider("slow", slow_provider)
        slow_manager.set_default_provider("slow")
        
        with patch('ai_agent_framework.core.llm_provider.get_llm_manager', return_value=slow_manager):
            email_data = test_data_manager.create_sample_email("sales").to_dict()
            
            # This should either timeout gracefully or fall back to basic processing
            response = client.post("/api/trigger/email", json=email_data)
            
            # Should handle timeout gracefully
            assert response.status_code in [200, 408, 500]  # Success, timeout, or server error
            
            if response.status_code == 200:
                response_data = response.json()
                assert "trigger_id" in response_data
    
    @pytest.mark.asyncio
    async def test_workflow_state_management(self, test_data_manager, setup_test_environment):
        """Test workflow state management and persistence."""
        llm_manager = setup_test_environment
        
        # Create sales agent
        sales_agent = SalesAgent(
            name="state_test_agent",
            config={"test_mode": True},
            llm_manager=llm_manager
        )
        
        # Process multiple emails to test state isolation
        email_data_sets = []
        for i in range(3):
            email = test_data_manager.create_sample_email("sales")
            email.sender = f"state_test_{i}@example.com"
            email.subject = f"State Test {i}: {email.subject}"
            email_data_sets.append({
                "source": "email",
                "email": email.to_dict()
            })
        
        # Process emails sequentially
        results = []
        for email_data in email_data_sets:
            result = await sales_agent.process(email_data)
            results.append(result)
        
        # Verify state isolation - each result should be independent
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.success is True
            assert result.output["customer_email"] == f"state_test_{i}@example.com"
            
            # Verify no state bleeding between requests
            if i > 0:
                prev_result = results[i-1]
                assert result.output["customer_email"] != prev_result.output["customer_email"]


class TestWorkflowIntegrationScenarios:
    """Test specific integration scenarios and edge cases."""
    
    @pytest.fixture
    def test_data_manager(self):
        """Create test data manager."""
        return TestDataManager()
    
    @pytest.mark.asyncio
    async def test_email_parsing_integration(self, test_data_manager):
        """Test email parsing integration with various email formats."""
        from utils.email_parser import EmailParser
        
        parser = EmailParser()
        
        # Test different email formats
        email_formats = [
            # Standard format
            test_data_manager.create_sample_email("sales"),
            
            # Complex sender format
            EmailMessage(
                subject="Complex Email Test",
                sender="John Doe <john.doe@company.com>",
                recipient="Sales Team <sales@ourcompany.com>",
                body="This is a test with complex email addresses.",
                headers={"Message-ID": "<test@example.com>"}
            ),
            
            # HTML content
            EmailMessage(
                subject="HTML Email Test",
                sender="html@example.com",
                recipient="recipient@company.com",
                body="<html><body><p>This is <b>HTML</b> content.</p></body></html>",
                headers={"Content-Type": "text/html"}
            )
        ]
        
        for email in email_formats:
            parsed_data = parser.parse_email_message(email)
            
            assert "sender_email" in parsed_data
            assert "recipient_email" in parsed_data
            assert "subject_clean" in parsed_data
            assert "body_clean" in parsed_data
            assert parsed_data["sender_email"]  # Should extract clean email
            assert parsed_data["subject_clean"]  # Should have clean subject
    
    @pytest.mark.asyncio
    async def test_criteria_engine_integration(self, test_data_manager):
        """Test criteria engine integration with various trigger types."""
        from core.criteria_evaluator import CriteriaEngine
        from models.data_models import TriggerData
        
        # Create criteria engine with test criteria
        criteria_config = {
            "criteria": [
                {
                    "name": "sales_email",
                    "priority": 1,
                    "conditions": [
                        {
                            "field": "email.subject",
                            "operator": "contains",
                            "values": ["purchase", "buy", "pricing"]
                        }
                    ],
                    "agent": "sales_agent"
                },
                {
                    "name": "support_email", 
                    "priority": 2,
                    "conditions": [
                        {
                            "field": "email.subject",
                            "operator": "contains",
                            "values": ["help", "support", "issue"]
                        }
                    ],
                    "agent": "support_agent"
                }
            ]
        }
        
        engine = CriteriaEngine()
        engine.load_criteria_from_dict(criteria_config)
        
        # Test different email types
        test_cases = [
            (test_data_manager.create_sample_email("sales"), "sales_agent"),
            (test_data_manager.create_sample_email("support"), "support_agent"),
            (test_data_manager.create_sample_email("general"), None)  # Should not match
        ]
        
        for email, expected_agent in test_cases:
            trigger_data = TriggerData(
                source="email",
                timestamp=datetime.now(),
                data={"email": email.to_dict()}
            )
            
            matches = engine.evaluate(trigger_data)
            
            if expected_agent:
                assert len(matches) > 0
                assert matches[0].agent_name == expected_agent
            else:
                # General email might not match any criteria
                pass  # This is acceptable
    
    @pytest.mark.asyncio
    async def test_agent_registry_integration(self, test_data_manager):
        """Test agent registry integration and routing."""
        from core.agent_registry import AgentRegistry
        from agents.sales_agent import SalesAgent
        
        # Create agent registry
        registry = AgentRegistry()
        
        # Register test agents
        mock_llm_manager = MockProviderFactory.create_reliable_provider()
        sales_agent = SalesAgent(
            name="test_sales_agent",
            config={"test_mode": True},
            llm_manager=mock_llm_manager
        )
        
        registry.register_agent("sales_agent", sales_agent)
        
        # Test agent retrieval
        retrieved_agent = registry.get_agent("sales_agent")
        assert retrieved_agent is not None
        assert retrieved_agent.name == "test_sales_agent"
        
        # Test agent listing
        available_agents = registry.list_agents()
        assert "sales_agent" in available_agents
        
        # Test agent processing through registry
        email_data = {
            "source": "email",
            "email": test_data_manager.create_sample_email("sales").to_dict()
        }
        
        result = await retrieved_agent.process(email_data)
        assert result.success is True
        assert result.agent_name == "test_sales_agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])