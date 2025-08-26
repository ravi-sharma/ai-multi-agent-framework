#!/usr/bin/env python3
"""
Example showing how to integrate the criteria engine with the AI agent framework.

This demonstrates how the criteria engine would be used in a real application
to route incoming triggers to appropriate agents.
"""

import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import the framework
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.criteria_factory import create_default_criteria_engine
from models.data_models import TriggerData, EmailMessage
from models.config_models import CriteriaConfig, Condition


class SimpleAgentRouter:
    """Simple agent router using the criteria engine."""
    
    def __init__(self):
        self.criteria_engine = create_default_criteria_engine()
        self.agents = {}
        self._setup_sample_criteria()
    
    def _setup_sample_criteria(self):
        """Set up sample criteria for demonstration."""
        criteria_configs = [
            CriteriaConfig(
                name="urgent_sales",
                priority=10,
                agent="sales_agent",
                conditions=[
                    Condition(
                        field="email.subject",
                        operator="contains",
                        values=["urgent", "ASAP", "immediate"],
                        case_sensitive=False
                    ),
                    Condition(
                        field="email.subject",
                        operator="contains",
                        values=["buy", "purchase", "sale", "quote"],
                        case_sensitive=False
                    )
                ]
            ),
            CriteriaConfig(
                name="support_requests",
                priority=8,
                agent="support_agent",
                conditions=[
                    Condition(
                        field="email.subject",
                        operator="contains",
                        values=["help", "support", "issue", "problem"],
                        case_sensitive=False
                    )
                ]
            ),
            CriteriaConfig(
                name="vip_customers",
                priority=15,
                agent="vip_agent",
                conditions=[
                    Condition(
                        field="email.sender",
                        operator="contains",
                        values=["@vip.com", "@premium.com"],
                        case_sensitive=False
                    )
                ]
            )
        ]
        
        self.criteria_engine.load_criteria(criteria_configs)
    
    def register_agent(self, name: str, agent_handler):
        """Register an agent handler."""
        self.agents[name] = agent_handler
    
    def route_trigger(self, trigger_data: TriggerData):
        """Route a trigger to the appropriate agent."""
        print(f"\n--- Routing Trigger from {trigger_data.source} ---")
        
        # Evaluate criteria
        matches = self.criteria_engine.evaluate(trigger_data)
        
        if not matches:
            print("No matching criteria found, using default agent")
            return self._handle_default(trigger_data)
        
        # Use the highest priority match
        best_match = matches[0]
        print(f"Best match: {best_match.criteria_name} -> {best_match.agent_name} (priority: {best_match.priority})")
        
        # Get the agent handler
        agent_handler = self.agents.get(best_match.agent_name)
        if not agent_handler:
            print(f"Warning: No handler registered for agent '{best_match.agent_name}'")
            return self._handle_default(trigger_data)
        
        # Route to the agent
        return agent_handler(trigger_data, best_match)
    
    def _handle_default(self, trigger_data: TriggerData):
        """Handle triggers that don't match any criteria."""
        return {
            'agent': 'default_agent',
            'action': 'log_and_queue',
            'notes': 'Trigger queued for manual review'
        }


# Sample agent handlers
def sales_agent_handler(trigger_data: TriggerData, match):
    """Handle sales-related triggers."""
    print(f"🛒 Sales Agent Processing:")
    if 'email' in trigger_data.data:
        email = trigger_data.data['email']
        print(f"   Subject: {email.get('subject', 'N/A')}")
        print(f"   Sender: {email.get('sender', 'N/A')}")
        print(f"   Action: Analyzing customer intent and generating sales notes")
    
    return {
        'agent': 'sales_agent',
        'action': 'process_sales_inquiry',
        'priority': match.priority,
        'notes': 'Sales inquiry processed and forwarded to sales team'
    }


def support_agent_handler(trigger_data: TriggerData, match):
    """Handle support-related triggers."""
    print(f"🛠️  Support Agent Processing:")
    if 'email' in trigger_data.data:
        email = trigger_data.data['email']
        print(f"   Subject: {email.get('subject', 'N/A')}")
        print(f"   Action: Creating support ticket and analyzing issue")
    
    return {
        'agent': 'support_agent',
        'action': 'create_support_ticket',
        'priority': match.priority,
        'notes': 'Support ticket created and assigned to appropriate team'
    }


def vip_agent_handler(trigger_data: TriggerData, match):
    """Handle VIP customer triggers."""
    print(f"⭐ VIP Agent Processing:")
    if 'email' in trigger_data.data:
        email = trigger_data.data['email']
        print(f"   VIP Customer: {email.get('sender', 'N/A')}")
        print(f"   Action: Escalating to VIP support team with high priority")
    
    return {
        'agent': 'vip_agent',
        'action': 'escalate_to_vip_support',
        'priority': match.priority,
        'notes': 'VIP customer request escalated with highest priority'
    }


def demonstrate_routing():
    """Demonstrate the agent routing system."""
    print("=== AI Agent Framework - Routing Integration Demo ===")
    
    # Create router and register agents
    router = SimpleAgentRouter()
    router.register_agent('sales_agent', sales_agent_handler)
    router.register_agent('support_agent', support_agent_handler)
    router.register_agent('vip_agent', vip_agent_handler)
    
    # Test scenarios
    test_scenarios = [
        {
            'name': 'Urgent Sales Inquiry from VIP Customer',
            'data': TriggerData(
                source='email',
                timestamp=datetime.now(),
                data={
                    'email': {
                        'subject': 'Urgent: Need quote for bulk purchase ASAP',
                        'sender': 'ceo@vip.com',
                        'body': 'We need pricing for 1000 units immediately.',
                        'recipient': 'sales@company.com'
                    }
                }
            )
        },
        {
            'name': 'Support Request',
            'data': TriggerData(
                source='email',
                timestamp=datetime.now(),
                data={
                    'email': {
                        'subject': 'Help needed with login issue',
                        'sender': 'user@customer.com',
                        'body': 'I cannot log into my account.',
                        'recipient': 'support@company.com'
                    }
                }
            )
        },
        {
            'name': 'General Inquiry (No Match)',
            'data': TriggerData(
                source='email',
                timestamp=datetime.now(),
                data={
                    'email': {
                        'subject': 'Newsletter subscription',
                        'sender': 'user@example.com',
                        'body': 'Please add me to your newsletter.',
                        'recipient': 'info@company.com'
                    }
                }
            )
        }
    ]
    
    # Process each scenario
    for scenario in test_scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario['name']}")
        print(f"{'='*60}")
        
        result = router.route_trigger(scenario['data'])
        
        print(f"\nResult:")
        print(f"  Agent: {result['agent']}")
        print(f"  Action: {result['action']}")
        if 'priority' in result:
            print(f"  Priority: {result['priority']}")
        print(f"  Notes: {result['notes']}")


if __name__ == '__main__':
    demonstrate_routing()