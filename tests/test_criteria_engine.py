"""Unit tests for the criteria engine and evaluators."""

import pytest
import tempfile
import os
from datetime import datetime
from typing import Dict, Any

from core.criteria_evaluator import CriteriaEngine
from core.evaluators import (
    ContainsEvaluator,
    EqualsEvaluator,
    RegexEvaluator,
    GreaterThanEvaluator,
    LessThanEvaluator,
    StartsWithEvaluator,
    EndsWithEvaluator
)
from core.criteria_factory import (
    create_default_criteria_engine,
    create_criteria_engine_from_yaml
)
from models.data_models import TriggerData, EmailMessage
from models.config_models import Condition, CriteriaConfig


class TestBasicEvaluators:
    """Test basic criteria evaluators."""
    
    def setup_method(self):
        """Set up test data."""
        self.email_data = {
            'email': {
                'subject': 'Urgent: Need help with purchase',
                'sender': 'customer@vip.com',
                'body': 'I need help with order #123456. This is urgent!',
                'recipient': 'support@company.com'
            },
            'transaction': {
                'amount': 15000.50,
                'currency': 'USD'
            },
            'alert': {
                'severity': 'critical',
                'source': 'production-server-01',
                'downtime': 450
            }
        }
        
        self.trigger_data = TriggerData(
            source='email',
            timestamp=datetime.now(),
            data=self.email_data
        )
    
    def test_contains_evaluator(self):
        """Test ContainsEvaluator functionality."""
        evaluator = ContainsEvaluator()
        
        # Test case-insensitive contains
        condition = Condition(
            field='email.subject',
            operator='contains',
            values=['urgent', 'help'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition, self.trigger_data) is True
        
        # Test case-sensitive contains
        condition_sensitive = Condition(
            field='email.subject',
            operator='contains',
            values=['URGENT'],
            case_sensitive=True
        )
        assert evaluator.evaluate(condition_sensitive, self.trigger_data) is False
        
        # Test no match
        condition_no_match = Condition(
            field='email.subject',
            operator='contains',
            values=['refund', 'cancel'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_no_match, self.trigger_data) is False
        
        # Test missing field
        condition_missing = Condition(
            field='email.missing_field',
            operator='contains',
            values=['test'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_missing, self.trigger_data) is False
    
    def test_equals_evaluator(self):
        """Test EqualsEvaluator functionality."""
        evaluator = EqualsEvaluator()
        
        # Test string equality (case-insensitive)
        condition = Condition(
            field='alert.severity',
            operator='equals',
            values=['critical', 'high'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition, self.trigger_data) is True
        
        # Test numeric equality
        condition_numeric = Condition(
            field='transaction.amount',
            operator='equals',
            values=[15000.50, 20000],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_numeric, self.trigger_data) is True
        
        # Test case-sensitive string equality
        condition_sensitive = Condition(
            field='alert.severity',
            operator='equals',
            values=['Critical'],
            case_sensitive=True
        )
        assert evaluator.evaluate(condition_sensitive, self.trigger_data) is False
        
        # Test no match
        condition_no_match = Condition(
            field='alert.severity',
            operator='equals',
            values=['low', 'medium'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_no_match, self.trigger_data) is False
    
    def test_regex_evaluator(self):
        """Test RegexEvaluator functionality."""
        evaluator = RegexEvaluator()
        
        # Test order number pattern
        condition = Condition(
            field='email.body',
            operator='regex',
            values=[r'order\s*#?\s*\d{6}'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition, self.trigger_data) is True
        
        # Test email pattern
        condition_email = Condition(
            field='email.sender',
            operator='regex',
            values=[r'[\w\.-]+@[\w\.-]+\.\w+'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_email, self.trigger_data) is True
        
        # Test case-sensitive regex
        condition_sensitive = Condition(
            field='email.body',
            operator='regex',
            values=[r'ORDER'],
            case_sensitive=True
        )
        assert evaluator.evaluate(condition_sensitive, self.trigger_data) is False
        
        # Test invalid regex (should not match)
        condition_invalid = Condition(
            field='email.body',
            operator='regex',
            values=['[invalid regex'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_invalid, self.trigger_data) is False
    
    def test_greater_than_evaluator(self):
        """Test GreaterThanEvaluator functionality."""
        evaluator = GreaterThanEvaluator()
        
        # Test numeric comparison
        condition = Condition(
            field='transaction.amount',
            operator='greater_than',
            values=[10000, 20000],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition, self.trigger_data) is True
        
        # Test string numeric comparison
        condition_string = Condition(
            field='alert.downtime',
            operator='greater_than',
            values=[300, 600],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_string, self.trigger_data) is True
        
        # Test no match
        condition_no_match = Condition(
            field='transaction.amount',
            operator='greater_than',
            values=[20000, 30000],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_no_match, self.trigger_data) is False
    
    def test_less_than_evaluator(self):
        """Test LessThanEvaluator functionality."""
        evaluator = LessThanEvaluator()
        
        # Test numeric comparison
        condition = Condition(
            field='transaction.amount',
            operator='less_than',
            values=[20000, 30000],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition, self.trigger_data) is True
        
        # Test no match
        condition_no_match = Condition(
            field='transaction.amount',
            operator='less_than',
            values=[10000, 5000],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_no_match, self.trigger_data) is False
    
    def test_starts_with_evaluator(self):
        """Test StartsWithEvaluator functionality."""
        evaluator = StartsWithEvaluator()
        
        # Test starts with
        condition = Condition(
            field='email.subject',
            operator='starts_with',
            values=['Urgent:', 'Important:'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition, self.trigger_data) is True
        
        # Test case-sensitive
        condition_sensitive = Condition(
            field='email.subject',
            operator='starts_with',
            values=['urgent:'],
            case_sensitive=True
        )
        assert evaluator.evaluate(condition_sensitive, self.trigger_data) is False
        
        # Test no match
        condition_no_match = Condition(
            field='email.subject',
            operator='starts_with',
            values=['Info:', 'FYI:'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_no_match, self.trigger_data) is False
    
    def test_ends_with_evaluator(self):
        """Test EndsWithEvaluator functionality."""
        evaluator = EndsWithEvaluator()
        
        # Test ends with
        condition = Condition(
            field='email.subject',
            operator='ends_with',
            values=['purchase', 'with purchase'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition, self.trigger_data) is True
        
        # Test no match
        condition_no_match = Condition(
            field='email.subject',
            operator='ends_with',
            values=['refund', 'cancel'],
            case_sensitive=False
        )
        assert evaluator.evaluate(condition_no_match, self.trigger_data) is False


class TestCriteriaEngine:
    """Test CriteriaEngine functionality."""
    
    def setup_method(self):
        """Set up test data."""
        self.engine = create_default_criteria_engine()
        
        self.email_data = {
            'email': {
                'subject': 'Urgent: Need help with purchase',
                'sender': 'customer@vip.com',
                'body': 'I need help with order #123456. This is urgent!',
                'recipient': 'support@company.com'
            }
        }
        
        self.trigger_data = TriggerData(
            source='email',
            timestamp=datetime.now(),
            data=self.email_data
        )
    
    def test_register_evaluator(self):
        """Test evaluator registration."""
        engine = CriteriaEngine()
        evaluator = ContainsEvaluator()
        
        engine.register_evaluator(evaluator)
        assert 'contains' in engine.evaluators
        assert engine.evaluators['contains'] == evaluator
    
    def test_load_criteria_from_dict(self):
        """Test loading criteria from dictionary."""
        criteria_configs = [
            {
                'name': 'test_criteria',
                'priority': 5,
                'agent': 'test_agent',
                'conditions': [
                    {
                        'field': 'email.subject',
                        'operator': 'contains',
                        'values': ['urgent'],
                        'case_sensitive': False
                    }
                ]
            }
        ]
        
        self.engine.load_criteria(criteria_configs)
        assert len(self.engine.criteria_configs) == 1
        assert self.engine.criteria_configs[0].name == 'test_criteria'
        assert self.engine.criteria_configs[0].agent == 'test_agent'
    
    def test_evaluate_single_criteria(self):
        """Test evaluation of single criteria."""
        criteria_configs = [
            {
                'name': 'urgent_sales',
                'priority': 10,
                'agent': 'sales_agent',
                'conditions': [
                    {
                        'field': 'email.subject',
                        'operator': 'contains',
                        'values': ['urgent'],
                        'case_sensitive': False
                    }
                ]
            }
        ]
        
        self.engine.load_criteria(criteria_configs)
        matches = self.engine.evaluate(self.trigger_data)
        
        assert len(matches) == 1
        assert matches[0].agent_name == 'sales_agent'
        assert matches[0].criteria_name == 'urgent_sales'
        assert matches[0].priority == 10
    
    def test_evaluate_multiple_criteria(self):
        """Test evaluation with multiple criteria."""
        criteria_configs = [
            {
                'name': 'urgent_emails',
                'priority': 10,
                'agent': 'urgent_agent',
                'conditions': [
                    {
                        'field': 'email.subject',
                        'operator': 'contains',
                        'values': ['urgent'],
                        'case_sensitive': False
                    }
                ]
            },
            {
                'name': 'help_emails',
                'priority': 5,
                'agent': 'help_agent',
                'conditions': [
                    {
                        'field': 'email.subject',
                        'operator': 'contains',
                        'values': ['help'],
                        'case_sensitive': False
                    }
                ]
            },
            {
                'name': 'refund_emails',
                'priority': 8,
                'agent': 'refund_agent',
                'conditions': [
                    {
                        'field': 'email.subject',
                        'operator': 'contains',
                        'values': ['refund'],
                        'case_sensitive': False
                    }
                ]
            }
        ]
        
        self.engine.load_criteria(criteria_configs)
        matches = self.engine.evaluate(self.trigger_data)
        
        # Should match urgent_emails and help_emails, sorted by priority
        assert len(matches) == 2
        assert matches[0].agent_name == 'urgent_agent'  # Higher priority first
        assert matches[0].priority == 10
        assert matches[1].agent_name == 'help_agent'
        assert matches[1].priority == 5
    
    def test_evaluate_and_logic(self):
        """Test AND logic evaluation (all conditions must match)."""
        criteria_configs = [
            {
                'name': 'urgent_purchase',
                'priority': 10,
                'agent': 'sales_agent',
                'conditions': [
                    {
                        'field': 'email.subject',
                        'operator': 'contains',
                        'values': ['urgent'],
                        'case_sensitive': False
                    },
                    {
                        'field': 'email.subject',
                        'operator': 'contains',
                        'values': ['purchase'],
                        'case_sensitive': False
                    }
                ]
            }
        ]
        
        self.engine.load_criteria(criteria_configs)
        matches = self.engine.evaluate(self.trigger_data)
        
        assert len(matches) == 1
        assert matches[0].agent_name == 'sales_agent'
    
    def test_evaluate_no_matches(self):
        """Test evaluation with no matching criteria."""
        criteria_configs = [
            {
                'name': 'refund_emails',
                'priority': 10,
                'agent': 'refund_agent',
                'conditions': [
                    {
                        'field': 'email.subject',
                        'operator': 'contains',
                        'values': ['refund'],
                        'case_sensitive': False
                    }
                ]
            }
        ]
        
        self.engine.load_criteria(criteria_configs)
        matches = self.engine.evaluate(self.trigger_data)
        
        assert len(matches) == 0
    
    def test_disabled_criteria(self):
        """Test that disabled criteria are not evaluated."""
        criteria_configs = [
            {
                'name': 'disabled_criteria',
                'priority': 10,
                'agent': 'test_agent',
                'enabled': False,
                'conditions': [
                    {
                        'field': 'email.subject',
                        'operator': 'contains',
                        'values': ['urgent'],
                        'case_sensitive': False
                    }
                ]
            }
        ]
        
        self.engine.load_criteria(criteria_configs)
        matches = self.engine.evaluate(self.trigger_data)
        
        assert len(matches) == 0
    
    def test_unknown_operator(self):
        """Test handling of unknown operators."""
        criteria_configs = [
            {
                'name': 'unknown_operator',
                'priority': 10,
                'agent': 'test_agent',
                'conditions': [
                    {
                        'field': 'email.subject',
                        'operator': 'unknown_op',
                        'values': ['urgent'],
                        'case_sensitive': False
                    }
                ]
            }
        ]
        
        self.engine.load_criteria(criteria_configs)
        matches = self.engine.evaluate(self.trigger_data)
        
        assert len(matches) == 0
    
    def test_complex_criteria_evaluation(self):
        """Test complex criteria evaluation with boolean logic."""
        # Test AND expression
        and_expression = {
            "and": [
                {"field": "email.subject", "operator": "contains", "values": ["urgent"]},
                {"field": "email.subject", "operator": "contains", "values": ["purchase"]}
            ]
        }
        
        result = self.engine.evaluate_complex_criteria(and_expression, self.trigger_data)
        assert result is True
        
        # Test OR expression
        or_expression = {
            "or": [
                {"field": "email.subject", "operator": "contains", "values": ["refund"]},
                {"field": "email.subject", "operator": "contains", "values": ["urgent"]}
            ]
        }
        
        result = self.engine.evaluate_complex_criteria(or_expression, self.trigger_data)
        assert result is True
        
        # Test NOT expression
        not_expression = {
            "not": {"field": "email.subject", "operator": "contains", "values": ["refund"]}
        }
        
        result = self.engine.evaluate_complex_criteria(not_expression, self.trigger_data)
        assert result is True
        
        # Test nested expression
        nested_expression = {
            "and": [
                {"field": "email.subject", "operator": "contains", "values": ["urgent"]},
                {
                    "or": [
                        {"field": "email.sender", "operator": "contains", "values": ["@vip.com"]},
                        {"field": "email.body", "operator": "contains", "values": ["priority"]}
                    ]
                }
            ]
        }
        
        result = self.engine.evaluate_complex_criteria(nested_expression, self.trigger_data)
        assert result is True


class TestYAMLConfiguration:
    """Test YAML configuration loading."""
    
    def test_load_criteria_from_yaml(self):
        """Test loading criteria from YAML file."""
        yaml_content = """
criteria:
  - name: "test_criteria"
    description: "Test criteria for unit tests"
    priority: 5
    enabled: true
    agent: "test_agent"
    conditions:
      - field: "email.subject"
        operator: "contains"
        values: ["test", "urgent"]
        case_sensitive: false
      - field: "email.sender"
        operator: "equals"
        values: ["test@example.com"]
        case_sensitive: false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            engine = create_criteria_engine_from_yaml(yaml_path)
            
            assert len(engine.criteria_configs) == 1
            criteria = engine.criteria_configs[0]
            assert criteria.name == "test_criteria"
            assert criteria.priority == 5
            assert criteria.agent == "test_agent"
            assert len(criteria.conditions) == 2
            
        finally:
            os.unlink(yaml_path)
    
    def test_invalid_yaml_file(self):
        """Test handling of invalid YAML files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            yaml_path = f.name
        
        try:
            with pytest.raises(Exception):  # Should raise YAML error
                create_criteria_engine_from_yaml(yaml_path)
        finally:
            os.unlink(yaml_path)
    
    def test_missing_yaml_file(self):
        """Test handling of missing YAML files."""
        with pytest.raises(FileNotFoundError):
            create_criteria_engine_from_yaml("/nonexistent/file.yaml")
    
    def test_invalid_criteria_config(self):
        """Test handling of invalid criteria configuration."""
        yaml_content = """
criteria:
  - name: ""  # Invalid: empty name
    priority: 5
    agent: "test_agent"
    conditions: []  # Invalid: no conditions
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            with pytest.raises(ValueError):
                create_criteria_engine_from_yaml(yaml_path)
        finally:
            os.unlink(yaml_path)


class TestValidation:
    """Test validation functionality."""
    
    def test_validate_criteria_config(self):
        """Test criteria configuration validation."""
        engine = create_default_criteria_engine()  # Use factory to get evaluators
        
        # Valid configuration
        valid_config = {
            'name': 'test_criteria',
            'agent': 'test_agent',
            'conditions': [
                {
                    'field': 'email.subject',
                    'operator': 'contains',
                    'values': ['test']
                }
            ]
        }
        
        errors = engine.validate_criteria_config(valid_config)
        assert len(errors) == 0
        
        # Invalid configuration - missing name
        invalid_config = {
            'agent': 'test_agent',
            'conditions': [
                {
                    'field': 'email.subject',
                    'operator': 'contains',
                    'values': ['test']
                }
            ]
        }
        
        errors = engine.validate_criteria_config(invalid_config)
        assert len(errors) > 0
        assert any('name' in error for error in errors)
        
        # Invalid configuration - no conditions
        no_conditions_config = {
            'name': 'test_criteria',
            'agent': 'test_agent',
            'conditions': []
        }
        
        errors = engine.validate_criteria_config(no_conditions_config)
        assert len(errors) > 0
        assert any('condition' in error.lower() for error in errors)
    
    def test_evaluator_validation(self):
        """Test individual evaluator validation."""
        # Test ContainsEvaluator validation
        evaluator = ContainsEvaluator()
        
        valid_condition = Condition(
            field='email.subject',
            operator='contains',
            values=['test'],
            case_sensitive=False
        )
        assert evaluator.validate_condition(valid_condition) is True
        
        invalid_condition = Condition(
            field='',  # Empty field
            operator='contains',
            values=['test'],
            case_sensitive=False
        )
        assert evaluator.validate_condition(invalid_condition) is False
        
        # Test RegexEvaluator validation
        regex_evaluator = RegexEvaluator()
        
        valid_regex_condition = Condition(
            field='email.subject',
            operator='regex',
            values=[r'\d+'],
            case_sensitive=False
        )
        assert regex_evaluator.validate_condition(valid_regex_condition) is True
        
        invalid_regex_condition = Condition(
            field='email.subject',
            operator='regex',
            values=['[invalid regex'],
            case_sensitive=False
        )
        assert regex_evaluator.validate_condition(invalid_regex_condition) is False


if __name__ == '__main__':
    pytest.main([__file__])