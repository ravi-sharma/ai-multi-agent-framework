"""Unit tests for the DefaultAgent implementation."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from agents.default_agent import DefaultAgent
from core.llm_provider import LLMManager, LLMResponse
from models.data_models import AgentResult
from models.config_models import WorkflowConfig


class TestDefaultAgent:
    """Test cases for DefaultAgent."""
    
    @pytest.fixture
    def default_agent(self):
        """Create a default agent instance for testing."""
        return DefaultAgent(name="test_default_agent")
    
    @pytest.fixture
    def default_agent_with_config(self):
        """Create a default agent with custom configuration."""
        config = {
            'response_template': 'Custom response template',
            'enable_llm_enhancement': False,
            'log_unmatched_requests': True,
            'include_request_summary': True
        }
        return DefaultAgent(name="test_default_agent", config=config)
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create a mock LLM manager."""
        llm_manager = Mock(spec=LLMManager)
        llm_response = LLMResponse(
            content='{"suggested_action": "route_to_human", "urgency_level": "medium", "category": "general", "response_message": "Thank you for your inquiry", "next_steps": ["Review manually"], "confidence": 0.8}',
            model="test-model",
            usage={"tokens": 100}
        )
        llm_manager.generate_with_fallback = AsyncMock(return_value=llm_response)
        return llm_manager
    
    @pytest.fixture
    def sample_email_input(self):
        """Create sample email input data."""
        return {
            'source': 'email',
            'email': {
                'subject': 'General inquiry about your services',
                'sender': 'customer@example.com',
                'recipient': 'info@company.com',
                'body': 'I would like to know more about your services and pricing.',
                'headers': {'Message-ID': 'test123'}
            },
            'timestamp': datetime.now().isoformat()
        }
    
    @pytest.fixture
    def sample_webhook_input(self):
        """Create sample webhook input data."""
        return {
            'source': 'webhook',
            'webhook': {
                'event': 'contact_form_submission',
                'data': {
                    'name': 'John Doe',
                    'email': 'john@example.com',
                    'message': 'I need help with your product'
                }
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def test_initialization_default_config(self, default_agent):
        """Test default agent initialization with default configuration."""
        assert default_agent.name == "test_default_agent"
        assert default_agent.response_template == "Thank you for your message. We have received your request and will respond appropriately."
        assert default_agent.enable_llm_enhancement is True
        assert default_agent.log_unmatched_requests is True
        assert default_agent.include_request_summary is True
        assert default_agent.llm_manager is None
    
    def test_initialization_custom_config(self, default_agent_with_config):
        """Test default agent initialization with custom configuration."""
        assert default_agent_with_config.name == "test_default_agent"
        assert default_agent_with_config.response_template == "Custom response template"
        assert default_agent_with_config.enable_llm_enhancement is False
        assert default_agent_with_config.log_unmatched_requests is True
        assert default_agent_with_config.include_request_summary is True
    
    def test_initialization_with_llm_manager(self, mock_llm_manager):
        """Test default agent initialization with LLM manager."""
        agent = DefaultAgent(name="test_agent", llm_manager=mock_llm_manager)
        assert agent.llm_manager is mock_llm_manager
    
    @pytest.mark.asyncio
    async def test_process_basic_email_input(self, default_agent_with_config, sample_email_input):
        """Test processing basic email input without LLM enhancement."""
        result = await default_agent_with_config.process(sample_email_input)
        
        assert isinstance(result, AgentResult)
        assert result.success is True
        assert result.agent_name == "test_default_agent"
        assert result.execution_time > 0
        assert result.requires_human_review is True
        
        # Check output structure
        assert 'agent_type' in result.output
        assert result.output['agent_type'] == 'default'
        assert result.output['response_type'] == 'fallback'
        assert result.output['message'] == 'Custom response template'
        assert result.output['source'] == 'email'
        assert 'processed_at' in result.output
        assert result.output['llm_enhanced'] is False
        
        # Check request summary
        assert 'request_summary' in result.output
        summary = result.output['request_summary']
        assert summary['source'] == 'email'
        assert summary['has_email_data'] is True
        assert 'email_summary' in summary
        assert summary['email_summary']['sender'] == 'customer@example.com'
        
        # Check notes
        assert len(result.notes) >= 3
        assert "Processed by default fallback agent" in result.notes
        assert "Request source: email" in result.notes
        assert "LLM enhancement: disabled" in result.notes
    
    @pytest.mark.asyncio
    async def test_process_webhook_input(self, default_agent, sample_webhook_input):
        """Test processing webhook input."""
        result = await default_agent.process(sample_webhook_input)
        
        assert result.success is True
        assert result.output['source'] == 'webhook'
        
        # Check request summary
        summary = result.output['request_summary']
        assert summary['has_webhook_data'] is True
        assert 'webhook_summary' in summary
    
    @pytest.mark.asyncio
    async def test_process_with_llm_enhancement(self, mock_llm_manager, sample_email_input):
        """Test processing with LLM enhancement enabled."""
        agent = DefaultAgent(name="test_agent", llm_manager=mock_llm_manager)
        result = await agent.process(sample_email_input)
        
        assert result.success is True
        assert result.output['llm_enhanced'] is True
        
        # Check enhanced fields
        assert 'suggested_action' in result.output
        assert 'urgency_level' in result.output
        assert 'category' in result.output
        assert 'confidence' in result.output
        
        # Verify LLM was called
        mock_llm_manager.generate_with_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_llm_enhancement_failure(self, sample_email_input):
        """Test processing when LLM enhancement fails."""
        # Create mock LLM manager that raises an exception
        mock_llm_manager = Mock(spec=LLMManager)
        mock_llm_manager.generate_with_fallback = AsyncMock(side_effect=Exception("LLM error"))
        
        agent = DefaultAgent(name="test_agent", llm_manager=mock_llm_manager)
        result = await agent.process(sample_email_input)
        
        assert result.success is True  # Should still succeed with basic response
        assert result.output['llm_enhanced'] is False
        assert 'llm_error' in result.output
        assert result.output['llm_error'] == "LLM error"
    
    @pytest.mark.asyncio
    async def test_process_invalid_input(self, default_agent):
        """Test processing with invalid input data."""
        # Test with non-dict input
        result = await default_agent.process("invalid input")
        assert result.success is False
        assert "Invalid input data" in result.error_message
        
        # Test with empty dict
        result = await default_agent.process({})
        assert result.success is False
        assert "Invalid input data" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_exception_handling(self, default_agent):
        """Test exception handling during processing."""
        # Mock the _generate_response method to raise an exception
        with patch.object(default_agent, '_generate_response', side_effect=Exception("Test error")):
            result = await default_agent.process({'source': 'test', 'data': 'test'})
            
            assert result.success is False
            assert result.error_message == "Test error"
            assert result.execution_time > 0
            assert "Default agent processing failed" in result.notes
    
    def test_create_request_summary_email(self, default_agent, sample_email_input):
        """Test request summary creation for email input."""
        summary = default_agent._create_request_summary(sample_email_input)
        
        assert summary['source'] == 'email'
        assert summary['has_email_data'] is True
        assert summary['has_webhook_data'] is False
        assert 'email_summary' in summary
        
        email_summary = summary['email_summary']
        assert email_summary['has_subject'] is True
        assert email_summary['has_body'] is True
        assert email_summary['sender'] == 'customer@example.com'
        assert email_summary['subject_length'] > 0
        assert email_summary['body_length'] > 0
    
    def test_create_request_summary_webhook(self, default_agent, sample_webhook_input):
        """Test request summary creation for webhook input."""
        summary = default_agent._create_request_summary(sample_webhook_input)
        
        assert summary['source'] == 'webhook'
        assert summary['has_email_data'] is False
        assert summary['has_webhook_data'] is True
        assert 'webhook_summary' in summary
        
        webhook_summary = summary['webhook_summary']
        assert 'payload_keys' in webhook_summary
        assert 'payload_size' in webhook_summary
    
    def test_create_enhancement_prompt(self, default_agent, sample_email_input):
        """Test LLM enhancement prompt creation."""
        request_summary = default_agent._create_request_summary(sample_email_input)
        prompt = default_agent._create_enhancement_prompt(sample_email_input, request_summary)
        
        assert "default fallback agent" in prompt
        assert "Email Subject:" in prompt
        assert "Email Body:" in prompt
        assert "From:" in prompt
        assert "JSON format" in prompt
        assert "suggested_action" in prompt
    
    def test_parse_enhancement_response_valid_json(self, default_agent):
        """Test parsing valid JSON response from LLM."""
        response = '{"suggested_action": "create_ticket", "urgency_level": "high", "category": "support", "response_message": "We will help you", "next_steps": ["Create ticket"], "confidence": 0.9}'
        
        parsed = default_agent._parse_enhancement_response(response)
        
        assert parsed['suggested_action'] == 'create_ticket'
        assert parsed['urgency_level'] == 'high'
        assert parsed['category'] == 'support'
        assert parsed['response_message'] == 'We will help you'
        assert parsed['next_steps'] == ['Create ticket']
        assert parsed['confidence'] == 0.9
    
    def test_parse_enhancement_response_invalid_json(self, default_agent):
        """Test parsing invalid JSON response from LLM."""
        response = 'This is not valid JSON'
        
        parsed = default_agent._parse_enhancement_response(response)
        
        # Should return default values
        assert parsed['suggested_action'] == 'route_to_human'
        assert parsed['urgency_level'] == 'medium'
        assert parsed['category'] == 'general'
        assert parsed['confidence'] == 0.0
    
    def test_parse_enhancement_response_partial_json(self, default_agent):
        """Test parsing response with embedded JSON."""
        response = 'Here is the analysis: {"suggested_action": "send_acknowledgment", "urgency_level": "low"} and some more text'
        
        parsed = default_agent._parse_enhancement_response(response)
        
        assert parsed['suggested_action'] == 'send_acknowledgment'
        assert parsed['urgency_level'] == 'low'
        # Missing fields should get defaults
        assert parsed['category'] == 'general'
        assert parsed['confidence'] == 0.5
    
    @patch('ai_agent_framework.agents.default_agent.logger')
    def test_log_fallback_scenario_email(self, mock_logger, default_agent, sample_email_input):
        """Test logging fallback scenario for email input."""
        default_agent._log_fallback_scenario(sample_email_input)
        
        # Check that info and warning logs were called
        assert mock_logger.info.called
        assert mock_logger.warning.called
        
        # Check log content
        info_call = mock_logger.info.call_args[0][0]
        assert "Default agent handling unmatched request" in info_call
        
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Unmatched request routed to default agent from email" in warning_call
    
    @patch('ai_agent_framework.agents.default_agent.logger')
    def test_log_fallback_scenario_webhook(self, mock_logger, default_agent, sample_webhook_input):
        """Test logging fallback scenario for webhook input."""
        default_agent._log_fallback_scenario(sample_webhook_input)
        
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Unmatched request routed to default agent from webhook" in warning_call
    
    def test_get_workflow_config(self, default_agent):
        """Test workflow configuration retrieval."""
        config = default_agent.get_workflow_config()
        
        assert isinstance(config, WorkflowConfig)
        assert config.agent_name == "test_default_agent"
        assert config.workflow_type == "simple"
        assert config.max_retries == 1
        assert config.timeout == 60
        assert config.enable_state_persistence is False
        assert len(config.workflow_steps) == 3
        assert "process_request" in config.workflow_steps
        assert "generate_response" in config.workflow_steps
        assert "log_result" in config.workflow_steps
    
    def test_get_required_llm_capabilities_with_enhancement(self, mock_llm_manager):
        """Test LLM capabilities when enhancement is enabled."""
        agent = DefaultAgent(name="test_agent", llm_manager=mock_llm_manager)
        capabilities = agent.get_required_llm_capabilities()
        
        assert 'text_generation' in capabilities
        assert 'json_output' in capabilities
    
    def test_get_required_llm_capabilities_without_enhancement(self):
        """Test LLM capabilities when enhancement is disabled."""
        config = {'enable_llm_enhancement': False}
        agent = DefaultAgent(name="test_agent", config=config)
        capabilities = agent.get_required_llm_capabilities()
        
        assert capabilities == []
    
    def test_validate_input_valid_data(self, default_agent):
        """Test input validation with valid data."""
        valid_inputs = [
            {'source': 'email', 'data': 'test'},
            {'webhook': {'event': 'test'}},
            {'source': 'api', 'payload': {'key': 'value'}}
        ]
        
        for input_data in valid_inputs:
            assert default_agent.validate_input(input_data) is True
    
    def test_validate_input_invalid_data(self, default_agent):
        """Test input validation with invalid data."""
        invalid_inputs = [
            "string input",
            123,
            None,
            [],
            {}  # Empty dict
        ]
        
        for input_data in invalid_inputs:
            assert default_agent.validate_input(input_data) is False


class TestDefaultAgentIntegration:
    """Integration tests for DefaultAgent."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing_without_llm(self):
        """Test end-to-end processing without LLM enhancement."""
        agent = DefaultAgent(
            name="integration_test_agent",
            config={'enable_llm_enhancement': False}
        )
        
        input_data = {
            'source': 'email',
            'email': {
                'subject': 'Test inquiry',
                'sender': 'test@example.com',
                'body': 'This is a test message'
            }
        }
        
        result = await agent.process(input_data)
        
        assert result.success is True
        assert result.agent_name == "integration_test_agent"
        assert result.requires_human_review is True
        assert result.output['agent_type'] == 'default'
        assert result.output['llm_enhanced'] is False
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing_with_llm(self):
        """Test end-to-end processing with LLM enhancement."""
        # Create a mock LLM manager
        mock_llm_manager = Mock(spec=LLMManager)
        llm_response = LLMResponse(
            content='{"suggested_action": "route_to_human", "urgency_level": "medium", "category": "general", "response_message": "Thank you", "next_steps": ["Review"], "confidence": 0.7}',
            model="test-model",
            usage={"tokens": 50}
        )
        mock_llm_manager.generate_with_fallback = AsyncMock(return_value=llm_response)
        
        agent = DefaultAgent(
            name="integration_test_agent",
            llm_manager=mock_llm_manager
        )
        
        input_data = {
            'source': 'webhook',
            'webhook': {
                'event': 'contact_form',
                'data': {'message': 'Need help with billing'}
            }
        }
        
        result = await agent.process(input_data)
        
        assert result.success is True
        assert result.output['llm_enhanced'] is True
        assert result.output['suggested_action'] == 'route_to_human'
        assert result.output['urgency_level'] == 'medium'
        assert result.output['category'] == 'general'
        assert result.output['confidence'] == 0.7
        
        # Verify LLM was called
        mock_llm_manager.generate_with_fallback.assert_called_once()