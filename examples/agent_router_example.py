"""Example demonstrating the AgentRouter functionality."""

import asyncio
from datetime import datetime
from typing import Dict, Any

from utils.agent_router import AgentRouter
from agents.base_agent import BaseAgent
from utils.agent_registry import AgentRegistry
from utils.criteria_evaluator import CriteriaEngine
from utils.evaluators import ContainsEvaluator, EqualsEvaluator
from models.data_models import TriggerData, AgentResult
from models.config_models import WorkflowConfig


class SalesAgent(BaseAgent):
    """Example sales agent for handling sales-related requests."""
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process sales-related data."""
        email_data = input_data.get('email', {})
        subject = email_data.get('subject', '')
        sender = email_data.get('sender', '')
        body = email_data.get('body', '')
        
        # Simulate sales processing
        notes = [
            f"Sales inquiry from {sender}",
            f"Subject: {subject}",
            "Identified as potential sales opportunity",
            "Recommended follow-up within 24 hours"
        ]
        
        output = {
            'agent_type': 'sales',
            'customer_email': sender,
            'inquiry_type': 'sales',
            'priority': 'high',
            'notes': notes
        }
        
        return AgentResult(
            success=True,
            output=output,
            notes=notes,
            execution_time=0.5,
            agent_name=self.name
        )
    
    def get_workflow_config(self) -> WorkflowConfig:
        """Get workflow configuration."""
        return WorkflowConfig(
            agent_name=self.name,
            workflow_type="langgraph",
            max_retries=3,
            timeout=300
        )


class SupportAgent(BaseAgent):
    """Example support agent for handling support requests."""
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process support-related data."""
        email_data = input_data.get('email', {})
        subject = email_data.get('subject', '')
        sender = email_data.get('sender', '')
        body = email_data.get('body', '')
        
        # Simulate support processing
        notes = [
            f"Support request from {sender}",
            f"Subject: {subject}",
            "Categorized as technical support",
            "Assigned to support queue"
        ]
        
        output = {
            'agent_type': 'support',
            'customer_email': sender,
            'inquiry_type': 'support',
            'priority': 'medium',
            'notes': notes
        }
        
        return AgentResult(
            success=True,
            output=output,
            notes=notes,
            execution_time=0.3,
            agent_name=self.name
        )
    
    def get_workflow_config(self) -> WorkflowConfig:
        """Get workflow configuration."""
        return WorkflowConfig(
            agent_name=self.name,
            workflow_type="langgraph",
            max_retries=3,
            timeout=300
        )


class DefaultAgent(BaseAgent):
    """Default fallback agent for unmatched requests."""
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process unmatched data with default handling."""
        notes = [
            "Request processed by default agent",
            "No specific criteria matched",
            "Requires manual review"
        ]
        
        output = {
            'agent_type': 'default',
            'inquiry_type': 'general',
            'priority': 'low',
            'notes': notes,
            'requires_review': True
        }
        
        return AgentResult(
            success=True,
            output=output,
            notes=notes,
            requires_human_review=True,
            execution_time=0.1,
            agent_name=self.name
        )
    
    def get_workflow_config(self) -> WorkflowConfig:
        """Get workflow configuration."""
        return WorkflowConfig(
            agent_name=self.name,
            workflow_type="langgraph",
            max_retries=3,
            timeout=300
        )


async def main():
    """Demonstrate AgentRouter functionality."""
    print("=== Agent Router Example ===\n")
    
    # Create agents
    sales_agent = SalesAgent("sales_agent")
    support_agent = SupportAgent("support_agent")
    default_agent = DefaultAgent("default_agent")
    
    # Create and configure criteria engine
    criteria_engine = CriteriaEngine()
    criteria_engine.register_evaluator(ContainsEvaluator())
    criteria_engine.register_evaluator(EqualsEvaluator())
    
    # Define routing criteria
    criteria_configs = [
        {
            "name": "sales_criteria",
            "priority": 2,
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
            "name": "support_criteria", 
            "priority": 1,
            "conditions": [
                {
                    "field": "email.subject",
                    "operator": "contains",
                    "values": ["help", "support", "issue", "problem", "bug"]
                }
            ],
            "agent": "support_agent",
            "enabled": True
        }
    ]
    
    criteria_engine.load_criteria(criteria_configs)
    
    # Create agent registry and register agents
    agent_registry = AgentRegistry()
    agent_registry.register_agent(sales_agent)
    agent_registry.register_agent(support_agent)
    agent_registry.register_agent(default_agent)
    
    # Create router
    router = AgentRouter(
        criteria_engine=criteria_engine,
        agent_registry=agent_registry,
        default_agent_name="default_agent"
    )
    
    print("Registered agents:", router.list_agents())
    print("Default agent:", router.get_default_agent())
    print()
    
    # Test cases
    test_cases = [
        {
            "name": "Sales Inquiry",
            "data": {
                "email": {
                    "subject": "Interested in purchasing your product",
                    "sender": "customer@rvish.com",
                    "body": "I would like to buy your premium package"
                }
            }
        },
        {
            "name": "Support Request",
            "data": {
                "email": {
                    "subject": "Need help with installation",
                    "sender": "user@company.com", 
                    "body": "I'm having trouble installing the software"
                }
            }
        },
        {
            "name": "General Inquiry",
            "data": {
                "email": {
                    "subject": "General question about your company",
                    "sender": "info@somewhere.com",
                    "body": "Can you tell me more about your company history?"
                }
            }
        },
        {
            "name": "High Priority Sales",
            "data": {
                "email": {
                    "subject": "Urgent: Need pricing quote for enterprise solution",
                    "sender": "ceo@bigcorp.com",
                    "body": "We need an immediate quote for 1000 licenses"
                }
            }
        }
    ]
    
    # Process each test case
    for i, test_case in enumerate(test_cases, 1):
        print(f"--- Test Case {i}: {test_case['name']} ---")
        
        # Create trigger data
        trigger_data = TriggerData(
            source="email",
            timestamp=datetime.now(),
            data=test_case['data']
        )
        
        # Test routing (without execution)
        routing_test = await router.test_routing(trigger_data)
        print(f"Routing test result:")
        print(f"  - Matches found: {len(routing_test['matches'])}")
        for match in routing_test['matches']:
            print(f"    * {match['agent_name']} (priority: {match['priority']}, criteria: {match['criteria_name']})")
        print(f"  - Selected agent: {routing_test['selected_agent']}")
        print(f"  - Would use fallback: {routing_test['would_use_fallback']}")
        
        # Execute routing
        result = await router.route(trigger_data)
        print(f"Execution result:")
        print(f"  - Success: {result.success}")
        print(f"  - Agent: {result.agent_name}")
        print(f"  - Execution time: {result.execution_time:.2f}s")
        print(f"  - Output type: {result.output.get('agent_type', 'unknown')}")
        print(f"  - Priority: {result.output.get('priority', 'unknown')}")
        print(f"  - Requires review: {result.requires_human_review}")
        print()
    
    # Show routing statistics
    stats = router.get_routing_stats()
    print("=== Routing Statistics ===")
    print(f"Total requests: {stats['total_requests']}")
    print(f"Successful routes: {stats['successful_routes']}")
    print(f"Fallback routes: {stats['fallback_routes']}")
    print(f"Failed routes: {stats['failed_routes']}")
    print("Agent usage:")
    for agent_name, count in stats['agent_usage'].items():
        print(f"  - {agent_name}: {count}")
    print()
    
    # Validate configuration
    validation = router.validate_configuration()
    print("=== Configuration Validation ===")
    print(f"Agent errors: {len(validation['agents'])}")
    print(f"Criteria errors: {len(validation['criteria'])}")
    print(f"Routing errors: {len(validation['routing'])}")
    
    if validation['agents']:
        print("Agent validation errors:")
        for error in validation['agents']:
            print(f"  - {error}")
    
    if validation['routing']:
        print("Routing validation errors:")
        for error in validation['routing']:
            print(f"  - {error}")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())