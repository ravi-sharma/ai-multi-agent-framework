#!/usr/bin/env python3
"""
Example demonstrating the criteria engine functionality.

This script shows how to:
1. Create a criteria engine with basic evaluators
2. Load criteria from YAML configuration
3. Evaluate trigger data against criteria
4. Handle different types of matching scenarios
"""

import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import the framework
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.criteria_factory import create_criteria_engine_from_yaml
from models.data_models import TriggerData, EmailMessage


def create_sample_email_data() -> TriggerData:
    """Create sample email data for testing."""
    email_message = EmailMessage(
        subject="Urgent: Need help with purchase order #123456",
        sender="customer@vip.com",
        recipient="support@company.com",
        body="Hello, I need immediate assistance with my recent purchase. "
             "Order #123456 has some issues and I need this resolved ASAP. "
             "This is a high-priority request.",
        timestamp=datetime.now()
    )
    
    return TriggerData(
        source='email',
        timestamp=datetime.now(),
        data={'email': email_message.to_dict()}
    )


def create_sample_webhook_data() -> TriggerData:
    """Create sample webhook data for testing."""
    return TriggerData(
        source='webhook',
        timestamp=datetime.now(),
        data={
            'transaction': {
                'amount': 25000.00,
                'currency': 'USD',
                'type': 'purchase'
            },
            'alert': {
                'severity': 'critical',
                'source': 'production-server-01',
                'downtime': 600,
                'message': 'Database connection failed'
            }
        }
    )


def demonstrate_criteria_engine():
    """Demonstrate the criteria engine functionality."""
    print("=== AI Agent Framework - Criteria Engine Demo ===\n")
    
    # Load criteria engine from YAML configuration
    try:
        criteria_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'example_criteria.yaml')
        engine = create_criteria_engine_from_yaml(criteria_file)
        print(f"✓ Loaded criteria engine with {len(engine.criteria_configs)} criteria")
        print(f"✓ Available evaluators: {', '.join(engine.get_available_evaluators())}\n")
    except Exception as e:
        print(f"✗ Failed to load criteria engine: {e}")
        return
    
    # Test with email data
    print("--- Testing Email Data ---")
    email_data = create_sample_email_data()
    print(f"Email Subject: {email_data.data['email']['subject']}")
    print(f"Email Sender: {email_data.data['email']['sender']}")
    print(f"Email Body: {email_data.data['email']['body'][:100]}...\n")
    
    matches = engine.evaluate(email_data)
    print(f"Found {len(matches)} matching criteria:")
    for match in matches:
        print(f"  - {match.criteria_name} -> {match.agent_name} (priority: {match.priority})")
    print()
    
    # Test with webhook data
    print("--- Testing Webhook Data ---")
    webhook_data = create_sample_webhook_data()
    print(f"Transaction Amount: ${webhook_data.data['transaction']['amount']}")
    print(f"Alert Severity: {webhook_data.data['alert']['severity']}")
    print(f"Alert Downtime: {webhook_data.data['alert']['downtime']} seconds\n")
    
    matches = engine.evaluate(webhook_data)
    print(f"Found {len(matches)} matching criteria:")
    for match in matches:
        print(f"  - {match.criteria_name} -> {match.agent_name} (priority: {match.priority})")
    print()
    
    # Demonstrate complex criteria evaluation
    print("--- Testing Complex Boolean Logic ---")
    complex_expression = {
        "and": [
            {"field": "email.subject", "operator": "contains", "values": ["urgent"]},
            {
                "or": [
                    {"field": "email.sender", "operator": "contains", "values": ["@vip.com"]},
                    {"field": "email.body", "operator": "contains", "values": ["high-priority"]}
                ]
            }
        ]
    }
    
    result = engine.evaluate_complex_criteria(complex_expression, email_data)
    print(f"Complex criteria evaluation result: {result}")
    print("Expression: (subject contains 'urgent') AND ((sender contains '@vip.com') OR (body contains 'high-priority'))")
    print()
    
    # Test validation
    print("--- Testing Validation ---")
    test_config = {
        'name': 'test_validation',
        'agent': 'test_agent',
        'conditions': [
            {
                'field': 'email.subject',
                'operator': 'contains',
                'values': ['test']
            }
        ]
    }
    
    errors = engine.validate_criteria_config(test_config)
    if errors:
        print(f"✗ Validation errors: {errors}")
    else:
        print("✓ Configuration is valid")
    
    # Test with invalid configuration
    invalid_config = {
        'name': '',  # Invalid: empty name
        'agent': 'test_agent',
        'conditions': []  # Invalid: no conditions
    }
    
    errors = engine.validate_criteria_config(invalid_config)
    print(f"✓ Invalid config detected {len(errors)} errors: {errors}")


if __name__ == '__main__':
    demonstrate_criteria_engine()