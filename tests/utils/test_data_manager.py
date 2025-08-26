"""Test data management utilities for creating consistent test data."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from models.data_models import (
    EmailMessage, TriggerData, AgentResult, SalesNotes
)


@dataclass
class TestCase:
    """Represents a test case with input data and expected outcomes."""
    name: str
    input_data: Dict[str, Any]
    expected_success: bool
    expected_agent: Optional[str] = None
    expected_output_keys: Optional[List[str]] = None
    description: Optional[str] = None


class TestDataManager:
    """Manages test data creation and validation for consistent testing."""
    
    def __init__(self):
        """Initialize test data manager."""
        self.test_counter = 0
    
    def get_unique_id(self) -> str:
        """Generate unique test ID."""
        self.test_counter += 1
        return f"test_{self.test_counter}_{uuid.uuid4().hex[:8]}"
    
    def create_sample_email(self, email_type: str = "sales") -> EmailMessage:
        """Create sample email message for testing.
        
        Args:
            email_type: Type of email ('sales', 'support', 'general', 'spam')
            
        Returns:
            EmailMessage instance
        """
        email_templates = {
            "sales": {
                "subject": "Interested in purchasing your premium package",
                "sender": "customer@example.com",
                "recipient": "sales@company.com",
                "body": "Hi, I am interested in purchasing your premium package for my company. We need it urgently for our upcoming project. Can you provide pricing information and schedule a demo?",
                "headers": {
                    "Message-ID": f"<{self.get_unique_id()}@example.com>",
                    "X-Priority": "3",
                    "Content-Type": "text/plain"
                }
            },
            "support": {
                "subject": "Need help with installation issues",
                "sender": "user@company.com", 
                "recipient": "support@company.com",
                "body": "I am having trouble installing your software on Windows 11. The installation keeps failing at step 3. Can you please help me resolve this issue?",
                "headers": {
                    "Message-ID": f"<{self.get_unique_id()}@company.com>",
                    "X-Priority": "2",
                    "Content-Type": "text/plain"
                }
            },
            "general": {
                "subject": "General inquiry about your services",
                "sender": "info@business.com",
                "recipient": "info@company.com", 
                "body": "Hello, I would like to learn more about your company and the services you offer. Could you send me some information?",
                "headers": {
                    "Message-ID": f"<{self.get_unique_id()}@business.com>",
                    "X-Priority": "3",
                    "Content-Type": "text/plain"
                }
            },
            "spam": {
                "subject": "URGENT: Claim your prize now!!!",
                "sender": "noreply@suspicious.com",
                "recipient": "victim@company.com",
                "body": "Congratulations! You have won $1,000,000! Click here to claim your prize immediately. This offer expires in 24 hours!",
                "headers": {
                    "Message-ID": f"<{self.get_unique_id()}@suspicious.com>",
                    "X-Priority": "1",
                    "Content-Type": "text/html"
                }
            }
        }
        
        template = email_templates.get(email_type, email_templates["general"])
        
        return EmailMessage(
            subject=template["subject"],
            sender=template["sender"],
            recipient=template["recipient"],
            body=template["body"],
            headers=template["headers"],
            timestamp=datetime.now()
        )
    
    def create_webhook_payload(self, webhook_type: str = "github") -> Dict[str, Any]:
        """Create sample webhook payload for testing.
        
        Args:
            webhook_type: Type of webhook ('github', 'gitlab', 'slack', 'custom')
            
        Returns:
            Dictionary with webhook payload
        """
        webhook_templates = {
            "github": {
                "source": "github",
                "data": {
                    "action": "push",
                    "repository": {
                        "name": "test-repo",
                        "full_name": "user/test-repo",
                        "private": False
                    },
                    "commits": [
                        {
                            "id": "abc123def456",
                            "message": "Fix critical bug in authentication",
                            "author": {
                                "name": "John Developer",
                                "email": "john@example.com"
                            },
                            "timestamp": datetime.now().isoformat()
                        }
                    ],
                    "pusher": {
                        "name": "john-dev",
                        "email": "john@example.com"
                    }
                },
                "metadata": {
                    "webhook_id": self.get_unique_id(),
                    "delivery_id": str(uuid.uuid4()),
                    "event": "push",
                    "signature": "sha256=test_signature"
                }
            },
            "gitlab": {
                "source": "gitlab",
                "data": {
                    "object_kind": "push",
                    "project": {
                        "name": "test-project",
                        "path_with_namespace": "group/test-project"
                    },
                    "commits": [
                        {
                            "id": "def456abc789",
                            "message": "Update documentation",
                            "author": {
                                "name": "Jane Developer",
                                "email": "jane@example.com"
                            }
                        }
                    ]
                },
                "metadata": {
                    "webhook_id": self.get_unique_id(),
                    "event": "Push Hook"
                }
            },
            "slack": {
                "source": "slack",
                "data": {
                    "type": "message",
                    "channel": "C1234567890",
                    "user": "U0987654321",
                    "text": "Hey team, we need to review the latest deployment",
                    "ts": str(datetime.now().timestamp())
                },
                "metadata": {
                    "webhook_id": self.get_unique_id(),
                    "team_id": "T1234567890",
                    "api_app_id": "A0987654321"
                }
            },
            "custom": {
                "source": "custom_system",
                "data": {
                    "event_type": "user_action",
                    "user_id": "user_123",
                    "action": "account_created",
                    "details": {
                        "email": "newuser@example.com",
                        "plan": "premium",
                        "referrer": "google"
                    }
                },
                "metadata": {
                    "webhook_id": self.get_unique_id(),
                    "source_ip": "192.168.1.100",
                    "user_agent": "CustomApp/1.0"
                }
            }
        }
        
        return webhook_templates.get(webhook_type, webhook_templates["custom"])
    
    def create_trigger_data(self, source: str = "email", data: Optional[Dict[str, Any]] = None) -> TriggerData:
        """Create TriggerData instance for testing.
        
        Args:
            source: Source of the trigger
            data: Optional data payload
            
        Returns:
            TriggerData instance
        """
        if data is None:
            if source == "email":
                email = self.create_sample_email()
                data = {"email": email.to_dict()}
            else:
                data = self.create_webhook_payload(source)
        
        return TriggerData(
            source=source,
            timestamp=datetime.now(),
            data=data,
            metadata={
                "test_id": self.get_unique_id(),
                "created_by": "test_data_manager"
            }
        )
    
    def create_agent_test_cases(self, agent_name: str) -> List[TestCase]:
        """Create test cases for specific agent types.
        
        Args:
            agent_name: Name of the agent to create test cases for
            
        Returns:
            List of TestCase instances
        """
        if agent_name == "sales_agent":
            return self._create_sales_agent_test_cases()
        elif agent_name == "support_agent":
            return self._create_support_agent_test_cases()
        else:
            return self._create_generic_agent_test_cases(agent_name)
    
    def _create_sales_agent_test_cases(self) -> List[TestCase]:
        """Create test cases specific to sales agent."""
        return [
            TestCase(
                name="sales_inquiry_high_urgency",
                input_data={
                    "source": "email",
                    "email": self.create_sample_email("sales").to_dict()
                },
                expected_success=True,
                expected_agent="sales_agent",
                expected_output_keys=["sales_notes", "urgency_level", "customer_info"],
                description="High urgency sales inquiry with purchase intent"
            ),
            TestCase(
                name="pricing_request",
                input_data={
                    "source": "email", 
                    "email": EmailMessage(
                        subject="Pricing information needed",
                        sender="procurement@bigcorp.com",
                        recipient="sales@company.com",
                        body="We need pricing for 100 licenses of your enterprise solution. Please send quote ASAP.",
                        headers={"Message-ID": f"<{self.get_unique_id()}@bigcorp.com>"}
                    ).to_dict()
                },
                expected_success=True,
                expected_agent="sales_agent",
                expected_output_keys=["sales_notes", "urgency_level"],
                description="Pricing request from enterprise customer"
            ),
            TestCase(
                name="demo_request",
                input_data={
                    "source": "email",
                    "email": EmailMessage(
                        subject="Schedule product demo",
                        sender="manager@startup.com",
                        recipient="sales@company.com", 
                        body="Hi, we're evaluating solutions and would like to schedule a demo of your product next week.",
                        headers={"Message-ID": f"<{self.get_unique_id()}@startup.com>"}
                    ).to_dict()
                },
                expected_success=True,
                expected_agent="sales_agent",
                expected_output_keys=["sales_notes", "follow_up_required"],
                description="Demo request from potential customer"
            ),
            TestCase(
                name="invalid_sales_email",
                input_data={
                    "source": "email",
                    "email": {
                        "subject": "",
                        "sender": "invalid-email",
                        "recipient": "sales@company.com",
                        "body": ""
                    }
                },
                expected_success=False,
                description="Invalid email data should fail validation"
            )
        ]
    
    def _create_support_agent_test_cases(self) -> List[TestCase]:
        """Create test cases specific to support agent."""
        return [
            TestCase(
                name="technical_issue",
                input_data={
                    "source": "email",
                    "email": self.create_sample_email("support").to_dict()
                },
                expected_success=True,
                expected_agent="support_agent",
                expected_output_keys=["issue_category", "priority", "resolution_steps"],
                description="Technical support issue"
            ),
            TestCase(
                name="account_problem",
                input_data={
                    "source": "email",
                    "email": EmailMessage(
                        subject="Cannot access my account",
                        sender="user@customer.com",
                        recipient="support@company.com",
                        body="I've been locked out of my account since yesterday. I tried resetting my password but didn't receive the email.",
                        headers={"Message-ID": f"<{self.get_unique_id()}@customer.com>"}
                    ).to_dict()
                },
                expected_success=True,
                expected_agent="support_agent",
                expected_output_keys=["issue_category", "priority"],
                description="Account access issue"
            )
        ]
    
    def _create_generic_agent_test_cases(self, agent_name: str) -> List[TestCase]:
        """Create generic test cases for any agent."""
        return [
            TestCase(
                name=f"{agent_name}_basic_test",
                input_data={
                    "source": "email",
                    "email": self.create_sample_email("general").to_dict()
                },
                expected_success=True,
                expected_agent=agent_name,
                description=f"Basic test case for {agent_name}"
            ),
            TestCase(
                name=f"{agent_name}_invalid_input",
                input_data={"invalid": "data"},
                expected_success=False,
                description=f"Invalid input test for {agent_name}"
            )
        ]
    
    def create_performance_test_data(self, count: int, email_type: str = "sales") -> List[Dict[str, Any]]:
        """Create multiple test data items for performance testing.
        
        Args:
            count: Number of test data items to create
            email_type: Type of email to create
            
        Returns:
            List of test data dictionaries
        """
        test_data = []
        for i in range(count):
            email = self.create_sample_email(email_type)
            # Vary the content slightly for each item
            email.subject = f"{email.subject} - Test {i+1}"
            email.sender = f"test{i+1}@example.com"
            
            test_data.append({
                "source": "email",
                "email": email.to_dict(),
                "test_index": i
            })
        
        return test_data
    
    def create_concurrent_test_scenarios(self) -> List[Dict[str, Any]]:
        """Create test scenarios for concurrent processing tests."""
        scenarios = []
        
        # Mixed email types scenario
        email_types = ["sales", "support", "general"]
        for i, email_type in enumerate(email_types * 3):  # 9 emails total
            email = self.create_sample_email(email_type)
            email.sender = f"concurrent{i+1}@example.com"
            scenarios.append({
                "source": "email",
                "email": email.to_dict(),
                "scenario": "mixed_types",
                "index": i
            })
        
        # High volume sales scenario
        for i in range(10):
            email = self.create_sample_email("sales")
            email.sender = f"sales{i+1}@customer.com"
            email.subject = f"Sales Inquiry #{i+1} - Urgent"
            scenarios.append({
                "source": "email", 
                "email": email.to_dict(),
                "scenario": "high_volume_sales",
                "index": i
            })
        
        return scenarios
    
    def validate_agent_result(self, result: AgentResult, test_case: TestCase) -> List[str]:
        """Validate agent result against test case expectations.
        
        Args:
            result: AgentResult to validate
            test_case: TestCase with expectations
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check success expectation
        if result.success != test_case.expected_success:
            errors.append(f"Expected success={test_case.expected_success}, got {result.success}")
        
        # Check expected output keys
        if test_case.expected_output_keys and result.success:
            missing_keys = []
            for key in test_case.expected_output_keys:
                if key not in result.output:
                    missing_keys.append(key)
            if missing_keys:
                errors.append(f"Missing expected output keys: {missing_keys}")
        
        # Check agent name if specified
        if test_case.expected_agent and result.agent_name != test_case.expected_agent:
            errors.append(f"Expected agent={test_case.expected_agent}, got {result.agent_name}")
        
        return errors
    
    def create_load_test_config(self, 
                               concurrent_users: int = 10,
                               requests_per_user: int = 5,
                               ramp_up_time: int = 10) -> Dict[str, Any]:
        """Create configuration for load testing.
        
        Args:
            concurrent_users: Number of concurrent users to simulate
            requests_per_user: Number of requests each user makes
            ramp_up_time: Time in seconds to ramp up to full load
            
        Returns:
            Load test configuration dictionary
        """
        return {
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "ramp_up_time": ramp_up_time,
            "total_requests": concurrent_users * requests_per_user,
            "test_duration": ramp_up_time + 30,  # Extra time for completion
            "endpoints": [
                "/api/trigger/email",
                "/api/trigger/webhook", 
                "/api/trigger"
            ],
            "test_data_generator": self.create_performance_test_data
        }