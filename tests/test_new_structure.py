"""Test the new project structure."""

import pytest
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents import DefaultAgent, SalesAgent
from models.data_models import AgentResult, EmailMessage, SalesNotes
from graphs.multiagent_graph import MultiAgentGraph
from tools.email_tools import EmailTools
from tools.search_tools import SearchTools
from memory.state_manager import StateManager
from configs.dev_config import DevConfig
from configs.prod_config import ProdConfig
from utils.logger import setup_logger
from utils.validators import validate_email, validate_config


class TestNewStructure:
    """Test the new project structure."""
    
    @pytest.mark.asyncio
    async def test_default_agent(self):
        """Test default agent functionality."""
        agent = DefaultAgent()
        
        input_data = {
            "source": "test",
            "data": {
                "message": "This is a test message"
            }
        }
        
        result = await agent.process(input_data)
        
        assert isinstance(result, AgentResult)
        assert result.success
        assert result.agent_name == "default_agent"
        assert "agent_type" in result.output
        assert result.output["agent_type"] == "default"
    
    @pytest.mark.asyncio
    async def test_sales_agent(self):
        """Test sales agent functionality."""
        agent = SalesAgent()
        
        input_data = {
            "source": "email",
            "data": {
                "email": {
                    "subject": "Interested in pricing",
                    "sender": "customer@example.com",
                    "recipient": "sales@company.com",
                    "body": "Hi, I need a quote for your product."
                }
            }
        }
        
        result = await agent.process(input_data)
        
        assert isinstance(result, AgentResult)
        assert result.success
        assert result.agent_name == "sales_agent"
        assert "sales_notes" in result.output
        assert result.output["primary_intent"] == "pricing"
    
    @pytest.mark.asyncio
    async def test_multiagent_graph(self):
        """Test multi-agent graph functionality."""
        # Create agents
        default_agent = DefaultAgent()
        sales_agent = SalesAgent()
        
        agents = {
            "default_agent": default_agent,
            "sales_agent": sales_agent
        }
        
        # Create graph
        graph = MultiAgentGraph(agents)
        
        # Test with sales input
        input_data = {
            "source": "email",
            "data": {
                "email": {
                    "subject": "Need pricing information",
                    "sender": "customer@example.com",
                    "body": "I want to buy your product"
                }
            }
        }
        
        result = await graph.execute(input_data)
        
        assert result["success"]
        assert result["agent_name"] == "sales_agent"
    
    def test_email_tools(self):
        """Test email tools functionality."""
        email_data = {
            "sender": "test@example.com",
            "recipient": "sales@company.com",
            "subject": "Urgent: Need pricing ASAP",
            "body": "Please call me at 123-456-7890. I need pricing for our company XYZ Corp."
        }
        
        # Test metadata extraction
        metadata = EmailTools.extract_email_metadata(email_data)
        assert metadata["sender_domain"] == "example.com"
        assert metadata["recipient_domain"] == "company.com"
        assert "urgent" in metadata["urgency_indicators"]
        
        # Test contact info extraction
        contact_info = EmailTools.extract_contact_info(email_data)
        assert "123-456-7890" in contact_info["phone_numbers"]
        
        # Test email classification
        classification = EmailTools.classify_email_type(email_data)
        assert classification["primary_type"] in ["sales", "general"]
    
    def test_search_tools(self):
        """Test search tools functionality."""
        text = "This is a test message with some keywords like pricing and demo."
        keywords = ["pricing", "demo", "test"]
        
        # Test keyword search
        results = SearchTools.search_keywords(text, keywords)
        assert len(results["found_keywords"]) == 3
        assert results["total_matches"] == 3
        
        # Test entity extraction
        text_with_entities = "Contact us at info@example.com or visit https://example.com"
        entities = SearchTools.extract_entities(text_with_entities)
        assert "info@example.com" in entities["emails"]
        assert "https://example.com" in entities["urls"]
        
        # Test text statistics
        stats = SearchTools.get_text_statistics(text)
        assert stats["word_count"] > 0
        assert stats["character_count"] > 0
    
    @pytest.mark.asyncio
    async def test_state_manager(self):
        """Test state manager functionality."""
        state_manager = StateManager()
        
        # Test workflow state
        workflow_id = "test_workflow_123"
        state_data = {
            "current_step": "process_email",
            "step_results": {"parse_email": {"success": True}},
            "context": {"agent_name": "sales_agent"}
        }
        
        # Save state
        success = await state_manager.save_workflow_state(workflow_id, state_data)
        assert success
        
        # Load state
        loaded_state = await state_manager.load_workflow_state(workflow_id)
        assert loaded_state is not None
        assert loaded_state["current_step"] == "process_email"
        
        # List active workflows
        active_workflows = await state_manager.list_active_workflows()
        assert workflow_id in active_workflows
        
        # Delete state
        success = await state_manager.delete_workflow_state(workflow_id)
        assert success
    
    def test_configurations(self):
        """Test configuration classes."""
        # Test dev config
        dev_config = DevConfig()
        assert dev_config.DEBUG is True
        assert dev_config.LOG_LEVEL == "DEBUG"
        
        validation = dev_config.validate_config()
        # Should have warnings about missing API keys but not fail
        assert len(validation["errors"]) > 0  # Missing API keys
        
        # Test prod config
        prod_config = ProdConfig()
        assert prod_config.DEBUG is False
        assert prod_config.LOG_LEVEL == "INFO"
        
        # Test config methods
        llm_config = prod_config.get_llm_config("openai")
        assert "api_key" in llm_config
        assert "model" in llm_config
        
        email_config = prod_config.get_email_config()
        assert "enabled" in email_config
        assert "host" in email_config
    
    def test_utilities(self):
        """Test utility functions."""
        # Test logger setup
        logger = setup_logger("test_logger", "INFO")
        assert logger.name == "test_logger"
        
        # Test email validation
        assert validate_email("test@example.com") is True
        assert validate_email("invalid-email") is False
        
        # Test config validation
        valid_config = {
            "agents": {
                "test_agent": {
                    "agent_type": "TestAgent",
                    "enabled": True
                }
            },
            "llm_providers": {
                "openai": {
                    "api_key": "test-key",
                    "model": "gpt-3.5-turbo"
                }
            }
        }
        
        validation = validate_config(valid_config)
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
    
    def test_data_models(self):
        """Test data model functionality."""
        # Test EmailMessage
        email = EmailMessage(
            subject="Test Subject",
            sender="sender@example.com",
            recipient="recipient@example.com",
            body="Test body content"
        )
        
        email_dict = email.to_dict()
        assert email_dict["subject"] == "Test Subject"
        assert email_dict["sender"] == "sender@example.com"
        
        # Test SalesNotes
        sales_notes = SalesNotes(
            customer_problem="Customer needs pricing information",
            proposed_solution="Send pricing sheet and schedule call",
            urgency_level="medium",
            follow_up_required=True,
            key_points=["Pricing inquiry", "Potential customer"]
        )
        
        notes_dict = sales_notes.to_dict()
        assert notes_dict["urgency_level"] == "medium"
        assert notes_dict["follow_up_required"] is True
        
        # Test AgentResult
        result = AgentResult(
            success=True,
            output={"message": "Processing completed"},
            agent_name="test_agent",
            execution_time=1.5
        )
        
        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["agent_name"] == "test_agent"
        assert result_dict["execution_time"] == 1.5