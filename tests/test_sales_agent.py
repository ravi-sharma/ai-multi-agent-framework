"""Unit tests for the SalesAgent implementation."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from agents.sales_agent import SalesAgent
from core.llm_provider import LLMManager, LLMResponse
from models.data_models import AgentResult, EmailMessage, SalesNotes
from models.config_models import WorkflowConfig


class TestSalesAgent:
    """Test cases for SalesAgent functionality."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create a mock LLM manager for testing."""
        manager = Mock(spec=LLMManager)
        manager.generate_with_fallback = AsyncMock()
        return manager
    
    @pytest.fixture
    def sales_agent(self, mock_llm_manager):
        """Create a SalesAgent instance for testing."""
        return SalesAgent(
            name="test_sales_agent",
            config={"test_mode": True},
            llm_manager=mock_llm_manager
        )
    
    @pytest.fixture
    def sales_agent_no_llm(self):
        """Create a SalesAgent instance without LLM for testing basic functionality."""
        return SalesAgent(
            name="test_sales_agent_no_llm",
            config={"test_mode": True},
            llm_manager=None
        )
    
    @pytest.fixture
    def sample_email_data(self):
        """Sample email data for testing."""
        return {
            'source': 'email',
            'email': {
                'subject': 'Interested in purchasing your premium package',
                'sender': 'customer@example.com',
                'recipient': 'sales@company.com',
                'body': 'Hi, I am interested in purchasing your premium package for my company. We need it urgently for our upcoming project. Can you provide pricing information?',
                'headers': {'Message-ID': 'test123'},
                'timestamp': datetime.now().isoformat()
            }
        }
    
    @pytest.fixture
    def sample_support_email_data(self):
        """Sample support email data for testing."""
        return {
            'source': 'email',
            'email': {
                'subject': 'Need help with installation',
                'sender': 'user@company.com',
                'recipient': 'support@company.com',
                'body': 'I am having trouble installing your software. Can you help me?',
                'headers': {'Message-ID': 'test456'}
            }
        }
    
    def test_sales_agent_initialization(self, mock_llm_manager):
        """Test SalesAgent initialization."""
        agent = SalesAgent(
            name="test_agent",
            config={"test": True},
            llm_manager=mock_llm_manager
        )
        
        assert agent.name == "test_agent"
        assert agent.config == {"test": True}
        assert agent.llm_manager == mock_llm_manager
        assert agent.workflow is not None
    
    def test_sales_agent_initialization_no_llm(self):
        """Test SalesAgent initialization without LLM manager."""
        agent = SalesAgent(name="test_agent")
        
        assert agent.name == "test_agent"
        assert agent.llm_manager is None
        assert agent.workflow is not None
    
    def test_get_workflow_config(self, sales_agent):
        """Test workflow configuration retrieval."""
        config = sales_agent.get_workflow_config()
        
        assert isinstance(config, WorkflowConfig)
        assert config.agent_name == sales_agent.name
        assert config.workflow_type == "langgraph"
        assert config.max_retries == 3
        assert config.timeout == 300
        assert len(config.workflow_steps) == 5
        assert "parse_email" in config.workflow_steps
        assert "generate_notes" in config.workflow_steps
    
    def test_get_required_llm_capabilities(self, sales_agent):
        """Test LLM capabilities requirement."""
        capabilities = sales_agent.get_required_llm_capabilities()
        
        assert isinstance(capabilities, list)
        assert 'text_generation' in capabilities
        assert 'json_output' in capabilities
        assert 'structured_analysis' in capabilities
    
    def test_validate_input_valid_email(self, sales_agent, sample_email_data):
        """Test input validation with valid email data."""
        assert sales_agent.validate_input(sample_email_data) is True
    
    def test_validate_input_missing_email(self, sales_agent):
        """Test input validation with missing email data."""
        invalid_data = {'source': 'webhook', 'data': {}}
        assert sales_agent.validate_input(invalid_data) is False
    
    def test_validate_input_empty_email(self, sales_agent):
        """Test input validation with empty email content."""
        invalid_data = {
            'email': {
                'subject': '',
                'body': '',
                'sender': 'test@example.com'
            }
        }
        assert sales_agent.validate_input(invalid_data) is False
    
    def test_validate_input_invalid_sender(self, sales_agent):
        """Test input validation with invalid sender."""
        invalid_data = {
            'email': {
                'subject': 'Test',
                'body': 'Test body',
                'sender': 'invalid-email'
            }
        }
        assert sales_agent.validate_input(invalid_data) is False
    
    def test_validate_input_non_dict(self, sales_agent):
        """Test input validation with non-dictionary input."""
        assert sales_agent.validate_input("invalid") is False
        assert sales_agent.validate_input(None) is False
        assert sales_agent.validate_input([]) is False
    
    @pytest.mark.asyncio
    async def test_process_valid_email_no_llm(self, sales_agent_no_llm, sample_email_data):
        """Test processing valid email without LLM enhancement."""
        result = await sales_agent_no_llm.process(sample_email_data)
        
        assert isinstance(result, AgentResult)
        assert result.success is True
        assert result.agent_name == sales_agent_no_llm.name
        assert result.execution_time > 0
        assert 'agent_type' in result.output
        assert result.output['agent_type'] == 'sales'
        assert 'customer_email' in result.output
        assert result.output['customer_email'] == 'customer@example.com'
        assert 'sales_notes' in result.output
        assert isinstance(result.output['sales_notes'], dict)
    
    @pytest.mark.asyncio
    async def test_process_valid_email_with_llm(self, sales_agent, sample_email_data):
        """Test processing valid email with LLM enhancement."""
        # Mock LLM responses
        mock_responses = [
            LLMResponse(
                content='{"company_name": "Example Corp", "industry": "Technology", "urgency_indicators": ["urgently"]}',
                usage={'tokens': 100},
                model='gpt-3.5-turbo',
                provider='openai'
            ),
            LLMResponse(
                content='{"primary_intent": "purchase", "urgency_level": "high", "customer_problems": ["need premium package"]}',
                usage={'tokens': 150},
                model='gpt-3.5-turbo',
                provider='openai'
            ),
            LLMResponse(
                content='{"customer_problem": "Customer needs premium package urgently", "proposed_solution": "Provide immediate pricing and setup call", "urgency_level": "high", "follow_up_required": true}',
                usage={'tokens': 200},
                model='gpt-3.5-turbo',
                provider='openai'
            )
        ]
        
        sales_agent.llm_manager.generate_with_fallback.side_effect = mock_responses
        
        result = await sales_agent.process(sample_email_data)
        
        assert isinstance(result, AgentResult)
        assert result.success is True
        assert result.agent_name == sales_agent.name
        assert result.execution_time > 0
        assert 'agent_type' in result.output
        assert result.output['agent_type'] == 'sales'
        assert result.output['urgency_level'] == 'high'
        assert result.output['requires_human_review'] is True
        
        # Verify LLM was called
        assert sales_agent.llm_manager.generate_with_fallback.call_count == 3
    
    @pytest.mark.asyncio
    async def test_process_invalid_input(self, sales_agent):
        """Test processing with invalid input data."""
        invalid_data = {'invalid': 'data'}
        
        result = await sales_agent.process(invalid_data)
        
        assert isinstance(result, AgentResult)
        assert result.success is False
        assert result.error_message == "Invalid input data for sales agent"
        assert result.execution_time == 0.0
    
    @pytest.mark.asyncio
    async def test_process_llm_failure_fallback(self, sales_agent, sample_email_data):
        """Test processing with LLM failure, should fallback to basic processing."""
        # Mock LLM to raise exception
        sales_agent.llm_manager.generate_with_fallback.side_effect = Exception("LLM API error")
        
        result = await sales_agent.process(sample_email_data)
        
        # Should still succeed with basic processing
        assert isinstance(result, AgentResult)
        assert result.success is True
        assert result.agent_name == sales_agent.name
        assert 'sales_notes' in result.output
    
    def test_analyze_intent_keywords_purchase(self, sales_agent_no_llm):
        """Test keyword-based intent analysis for purchase intent."""
        email = EmailMessage(
            subject="Want to buy your product",
            sender="customer@example.com",
            recipient="sales@company.com",
            body="I need to purchase your premium package urgently"
        )
        
        analysis = sales_agent_no_llm._analyze_intent_keywords(email)
        
        assert analysis['primary_intent'] == 'purchase'
        assert analysis['urgency_level'] == 'high'  # Due to "urgently"
        assert 'purchase' in analysis['intent_scores']
        assert analysis['intent_scores']['purchase'] > 0
    
    def test_analyze_intent_keywords_pricing(self, sales_agent_no_llm):
        """Test keyword-based intent analysis for pricing intent."""
        email = EmailMessage(
            subject="Need pricing information",
            sender="customer@example.com",
            recipient="sales@company.com",
            body="Can you provide cost details and quote for your service?"
        )
        
        analysis = sales_agent_no_llm._analyze_intent_keywords(email)
        
        assert analysis['primary_intent'] == 'pricing'
        assert 'pricing' in analysis['intent_scores']
        assert analysis['intent_scores']['pricing'] > 0
    
    def test_analyze_intent_keywords_demo(self, sales_agent_no_llm):
        """Test keyword-based intent analysis for demo intent."""
        email = EmailMessage(
            subject="Request for product demo",
            sender="customer@example.com",
            recipient="sales@company.com",
            body="I would like to see a demonstration of your software"
        )
        
        analysis = sales_agent_no_llm._analyze_intent_keywords(email)
        
        assert analysis['primary_intent'] == 'demo'
        assert 'demo' in analysis['intent_scores']
    
    def test_analyze_intent_keywords_general(self, sales_agent_no_llm):
        """Test keyword-based intent analysis for general inquiry."""
        email = EmailMessage(
            subject="General question",
            sender="customer@example.com",
            recipient="sales@company.com",
            body="I have some questions about your company"
        )
        
        analysis = sales_agent_no_llm._analyze_intent_keywords(email)
        
        # The analysis correctly identifies "information" intent due to "questions about"
        assert analysis['primary_intent'] == 'information'
        assert analysis['urgency_level'] == 'low'
    
    def test_create_basic_sales_notes(self, sales_agent_no_llm):
        """Test creation of basic sales notes."""
        email = EmailMessage(
            subject="Need pricing for premium package",
            sender="customer@example.com",
            recipient="sales@company.com",
            body="We need pricing information for your premium package"
        )
        
        customer_info = {
            'email': 'customer@example.com',
            'domain': 'example.com',
            'company_name': 'Example Corp'
        }
        
        intent_analysis = {
            'primary_intent': 'pricing',
            'urgency_level': 'medium',
            'customer_problems': ['need pricing information']
        }
        
        notes = sales_agent_no_llm._create_basic_sales_notes(email, customer_info, intent_analysis)
        
        assert isinstance(notes, SalesNotes)
        assert notes.urgency_level == 'medium'
        assert notes.follow_up_required is True  # Pricing inquiries require follow-up
        assert 'pricing' in notes.customer_problem.lower()
        assert 'pricing information' in notes.proposed_solution.lower()
        assert len(notes.key_points) > 0
        assert notes.customer_info == customer_info
    
    def test_create_customer_extraction_prompt(self, sales_agent):
        """Test customer extraction prompt creation."""
        email = EmailMessage(
            subject="Business inquiry from Acme Corp",
            sender="john@acme.com",
            recipient="sales@company.com",
            body="Hi, I'm John from Acme Corp. We're a large manufacturing company looking for your enterprise solution."
        )
        
        prompt = sales_agent._create_customer_extraction_prompt(email)
        
        assert isinstance(prompt, str)
        assert "Acme Corp" in prompt
        assert "john@acme.com" in prompt
        assert "JSON format" in prompt
        assert "company_name" in prompt
        assert "customer_name" in prompt
    
    def test_parse_customer_extraction_response_valid_json(self, sales_agent):
        """Test parsing valid JSON response from customer extraction."""
        response = '{"company_name": "Acme Corp", "industry": "Manufacturing", "company_size": "large"}'
        
        result = sales_agent._parse_customer_extraction_response(response)
        
        assert isinstance(result, dict)
        assert result['company_name'] == 'Acme Corp'
        assert result['industry'] == 'Manufacturing'
        assert result['company_size'] == 'large'
    
    def test_parse_customer_extraction_response_invalid_json(self, sales_agent):
        """Test parsing invalid JSON response from customer extraction."""
        response = 'This is not valid JSON'
        
        result = sales_agent._parse_customer_extraction_response(response)
        
        assert isinstance(result, dict)
        assert len(result) == 0  # Should return empty dict
    
    def test_parse_customer_extraction_response_partial_json(self, sales_agent):
        """Test parsing response with JSON embedded in text."""
        response = 'Here is the extracted information: {"company_name": "Test Corp", "industry": "Tech"} as requested.'
        
        result = sales_agent._parse_customer_extraction_response(response)
        
        assert isinstance(result, dict)
        assert result['company_name'] == 'Test Corp'
        assert result['industry'] == 'Tech'
    
    def test_merge_sales_notes_with_enhancement(self, sales_agent):
        """Test merging basic sales notes with LLM enhancement."""
        basic_notes = SalesNotes(
            customer_problem="Basic problem",
            proposed_solution="Basic solution",
            urgency_level="low",
            follow_up_required=False,
            key_points=["basic point"],
            customer_info={"email": "test@example.com"}
        )
        
        enhanced_data = {
            "customer_problem": "Enhanced problem description",
            "urgency_level": "high",
            "estimated_value": 50000,
            "next_steps": ["Call customer", "Send proposal"]
        }
        
        merged_notes = sales_agent._merge_sales_notes(basic_notes, enhanced_data)
        
        assert isinstance(merged_notes, SalesNotes)
        assert merged_notes.customer_problem == "Enhanced problem description"
        assert merged_notes.urgency_level == "high"
        assert merged_notes.estimated_value == 50000
        assert merged_notes.next_steps == ["Call customer", "Send proposal"]
        assert merged_notes.customer_info == {"email": "test@example.com"}  # Preserved
    
    def test_merge_sales_notes_empty_enhancement(self, sales_agent):
        """Test merging sales notes with empty enhancement data."""
        basic_notes = SalesNotes(
            customer_problem="Basic problem",
            proposed_solution="Basic solution",
            urgency_level="low",
            follow_up_required=False,
            key_points=["basic point"],
            customer_info={"email": "test@example.com"}
        )
        
        merged_notes = sales_agent._merge_sales_notes(basic_notes, {})
        
        # Should return the original notes unchanged
        assert merged_notes == basic_notes
    
    @pytest.mark.asyncio
    async def test_workflow_step_parse_email(self, sales_agent_no_llm, sample_email_data):
        """Test the parse_email workflow step."""
        from models.data_models import TriggerData
        from orchestration.langgraph_orchestrator import create_workflow_state
        from models.data_models import WorkflowContext
        
        # Create workflow state
        trigger_data = TriggerData(
            source='email',
            timestamp=datetime.now(),
            data=sample_email_data
        )
        
        context = WorkflowContext(
            workflow_id="test_workflow",
            agent_name=sales_agent_no_llm.name,
            trigger_data=trigger_data,
            start_time=datetime.now()
        )
        
        state = create_workflow_state(trigger_data, context)
        
        # Execute parse_email step
        result_state = await sales_agent_no_llm._parse_email_content(state)
        
        assert "parse_email" in result_state["step_results"]
        parsed_data = result_state["step_results"]["parse_email"]
        assert "email_message" in parsed_data
        assert parsed_data["subject_length"] > 0
        assert parsed_data["body_length"] > 0
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, sales_agent_no_llm):
        """Test workflow error handling with invalid data."""
        invalid_data = {
            'source': 'email',
            'email': {
                'subject': '',
                'body': '',
                'sender': ''  # Invalid sender
            }
        }
        
        result = await sales_agent_no_llm.process(invalid_data)
        
        assert isinstance(result, AgentResult)
        assert result.success is False
        assert result.error_message is not None
    
    def test_workflow_config_validation(self, sales_agent):
        """Test that workflow configuration is valid."""
        config = sales_agent.get_workflow_config()
        errors = config.validate()
        
        assert len(errors) == 0, f"Workflow config validation errors: {errors}"
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, sales_agent_no_llm, sample_email_data):
        """Test concurrent processing of multiple emails."""
        # Create multiple email data sets
        email_data_sets = []
        for i in range(3):
            data = sample_email_data.copy()
            data['email'] = data['email'].copy()
            data['email']['sender'] = f'customer{i}@example.com'
            data['email']['subject'] = f'Inquiry {i}: {data["email"]["subject"]}'
            email_data_sets.append(data)
        
        # Process concurrently
        tasks = [sales_agent_no_llm.process(data) for data in email_data_sets]
        results = await asyncio.gather(*tasks)
        
        # Verify all results
        assert len(results) == 3
        for i, result in enumerate(results):
            assert isinstance(result, AgentResult)
            assert result.success is True
            assert result.output['customer_email'] == f'customer{i}@example.com'
    
    def test_agent_info(self, sales_agent):
        """Test agent information retrieval."""
        info = sales_agent.get_agent_info()
        
        assert isinstance(info, dict)
        assert info['name'] == sales_agent.name
        assert info['type'] == 'SalesAgent'
        assert 'required_capabilities' in info
        assert 'config' in info


if __name__ == "__main__":
    pytest.main([__file__])