#!/usr/bin/env python3
"""
Example demonstrating data models and validation in the AI Agent Framework.

This example shows how to:
1. Create and validate data models
2. Serialize and deserialize models
3. Handle validation errors
4. Use the models in a typical workflow
"""

import json
from datetime import datetime
from models import (
    TriggerData, EmailMessage, AgentResult, SalesNotes, Attachment,
    DataValidator, ValidationError, serialize_to_dict, deserialize_from_dict
)


def demonstrate_trigger_data():
    """Demonstrate TriggerData creation and validation."""
    print("=== TriggerData Example ===")
    
    # Create a valid TriggerData instance
    trigger_data = TriggerData(
        source="email",
        timestamp=datetime.now(),
        data={
            "email": {
                "subject": "Interested in your AI solution",
                "sender": "customer@company.com",
                "body": "We're looking for an AI solution to help with our sales process..."
            }
        },
        metadata={"priority": "high", "source_ip": "192.168.1.100"}
    )
    
    print(f"Created TriggerData: {trigger_data.source}")
    print(f"Email subject: {trigger_data.get_field_value('email.subject')}")
    
    # Validate the data
    try:
        DataValidator.validate_trigger_data(trigger_data)
        print("✓ TriggerData validation passed")
    except ValidationError as e:
        print(f"✗ Validation failed: {e}")
    
    # Serialize to JSON
    json_str = trigger_data.to_json(indent=2)
    print(f"JSON representation:\n{json_str}")
    
    # Deserialize from JSON
    restored = TriggerData.from_json(json_str)
    print(f"✓ Successfully restored from JSON: {restored.source}")
    print()


def demonstrate_email_message():
    """Demonstrate EmailMessage creation and validation."""
    print("=== EmailMessage Example ===")
    
    # Create an attachment
    attachment = Attachment(
        filename="proposal.pdf",
        content_type="application/pdf",
        size=1024000,
        content=b"fake pdf content"
    )
    
    # Create an email message
    email = EmailMessage(
        subject="Sales Inquiry - AI Solution",
        sender="John Doe <john.doe@company.com>",
        recipient="sales@ourcompany.com",
        body="Hello, we are interested in your AI agent framework...",
        headers={"Message-ID": "<123456@company.com>", "X-Priority": "1"},
        attachments=[attachment],
        timestamp=datetime.now()
    )
    
    print(f"Created EmailMessage: {email.subject}")
    print(f"From: {email.sender}")
    print(f"Attachments: {len(email.attachments)}")
    
    # Validate the email
    try:
        DataValidator.validate_email_message(email)
        print("✓ EmailMessage validation passed")
    except ValidationError as e:
        print(f"✗ Validation failed: {e}")
    
    # Serialize to dictionary
    email_dict = email.to_dict()
    print(f"Serialized email has {len(email_dict)} fields")
    
    # Deserialize from dictionary
    restored_email = EmailMessage.from_dict(email_dict)
    print(f"✓ Successfully restored email: {restored_email.subject}")
    print()


def demonstrate_agent_result():
    """Demonstrate AgentResult creation and methods."""
    print("=== AgentResult Example ===")
    
    # Create an agent result
    result = AgentResult(
        success=True,
        output={"processed_data": "customer inquiry analyzed"},
        agent_name="sales_agent",
        execution_time=2.5
    )
    
    # Add notes
    result.add_note("Successfully parsed email content")
    result.add_note("Identified customer intent: product inquiry")
    result.add_note("Generated sales notes")
    
    print(f"Agent result: {result.success}")
    print(f"Execution time: {result.execution_time}s")
    print(f"Notes: {len(result.notes)}")
    
    # Validate the result
    try:
        DataValidator.validate_agent_result(result)
        print("✓ AgentResult validation passed")
    except ValidationError as e:
        print(f"✗ Validation failed: {e}")
    
    # Demonstrate error handling
    error_result = AgentResult(success=True, output={})
    error_result.set_error("LLM API timeout")
    print(f"Error result success: {error_result.success}")
    print(f"Error message: {error_result.error_message}")
    print()


def demonstrate_sales_notes():
    """Demonstrate SalesNotes creation and validation."""
    print("=== SalesNotes Example ===")
    
    # Create sales notes
    notes = SalesNotes(
        customer_problem="Manual sales process is inefficient and error-prone",
        proposed_solution="Implement AI agent framework to automate lead qualification and response generation",
        urgency_level="high",
        follow_up_required=True,
        key_points=[
            "Customer has budget approved",
            "Timeline: Q1 2024 implementation",
            "Decision maker: CTO John Doe",
            "Competitor evaluation in progress"
        ],
        customer_info={
            "company": "TechCorp Inc",
            "industry": "Software",
            "size": "50-100 employees",
            "location": "San Francisco, CA"
        },
        estimated_value=75000.0,
        next_steps=[
            "Schedule technical demo",
            "Send detailed proposal",
            "Arrange call with CTO",
            "Provide ROI analysis"
        ]
    )
    
    print(f"Customer problem: {notes.customer_problem}")
    print(f"Urgency level: {notes.urgency_level}")
    print(f"Estimated value: ${notes.estimated_value:,.2f}")
    print(f"Key points: {len(notes.key_points)}")
    print(f"Next steps: {len(notes.next_steps)}")
    
    # Validate the notes
    try:
        DataValidator.validate_sales_notes(notes)
        print("✓ SalesNotes validation passed")
    except ValidationError as e:
        print(f"✗ Validation failed: {e}")
    
    # Serialize to JSON
    notes_json = notes.to_json(indent=2)
    print(f"JSON length: {len(notes_json)} characters")
    
    # Deserialize from JSON
    restored_notes = SalesNotes.from_json(notes_json)
    print(f"✓ Successfully restored notes: {restored_notes.urgency_level}")
    print()


def demonstrate_validation_errors():
    """Demonstrate validation error handling."""
    print("=== Validation Error Handling ===")
    
    # Test invalid email address
    try:
        invalid_email = EmailMessage(
            subject="Test",
            sender="invalid-email-format",
            recipient="valid@example.com",
            body="Test body"
        )
        DataValidator.validate_email_message(invalid_email)
    except ValidationError as e:
        print(f"✓ Caught expected validation error: {e.message}")
        print(f"  Field: {e.field}")
    
    # Test invalid urgency level
    try:
        invalid_notes = SalesNotes(
            customer_problem="Problem",
            proposed_solution="Solution",
            urgency_level="super_urgent",  # Invalid level
            follow_up_required=False
        )
        DataValidator.validate_sales_notes(invalid_notes)
    except ValidationError as e:
        print(f"✓ Caught expected validation error: {e.message}")
        print(f"  Field: {e.field}")
    
    # Test invalid trigger source
    try:
        invalid_trigger = TriggerData(
            source="invalid_source",
            timestamp=datetime.now(),
            data={}
        )
        DataValidator.validate_trigger_data(invalid_trigger)
    except ValidationError as e:
        print(f"✓ Caught expected validation error: {e.message}")
        print(f"  Field: {e.field}")
    
    print()


def demonstrate_serialization_utilities():
    """Demonstrate serialization utility functions."""
    print("=== Serialization Utilities ===")
    
    # Create a sample model
    trigger_data = TriggerData(
        source="webhook",
        timestamp=datetime.now(),
        data={"test": "data"}
    )
    
    # Use utility functions
    data_dict = serialize_to_dict(trigger_data)
    print(f"Serialized to dict: {len(data_dict)} fields")
    
    restored = deserialize_from_dict(data_dict, TriggerData)
    print(f"✓ Deserialized successfully: {restored.source}")
    
    # Test with different model types
    sales_notes = SalesNotes(
        customer_problem="Test problem",
        proposed_solution="Test solution",
        urgency_level="medium",
        follow_up_required=True
    )
    
    notes_dict = serialize_to_dict(sales_notes)
    restored_notes = deserialize_from_dict(notes_dict, SalesNotes)
    print(f"✓ SalesNotes serialization works: {restored_notes.urgency_level}")
    print()


def main():
    """Run all demonstrations."""
    print("AI Agent Framework - Data Models and Validation Examples")
    print("=" * 60)
    print()
    
    demonstrate_trigger_data()
    demonstrate_email_message()
    demonstrate_agent_result()
    demonstrate_sales_notes()
    demonstrate_validation_errors()
    demonstrate_serialization_utilities()
    
    print("All examples completed successfully! ✓")


if __name__ == "__main__":
    main()