"""Unit tests for data models and validation."""

import json
import pytest
from datetime import datetime
from typing import Dict, Any

from models import (
    TriggerData, EmailMessage, AgentResult, SalesNotes, Attachment,
    WorkflowContext, WorkflowResult, AgentMatch,
    DataValidator, ValidationError, validate_input_data,
    serialize_to_dict, deserialize_from_dict, SerializationError
)


class TestTriggerData:
    """Test TriggerData model and validation."""
    
    def test_create_trigger_data(self):
        """Test creating a valid TriggerData instance."""
        now = datetime.now()
        data = TriggerData(
            source="webhook",
            timestamp=now,
            data={"key": "value"},
            metadata={"source_ip": "127.0.0.1"}
        )
        
        assert data.source == "webhook"
        assert data.timestamp == now
        assert data.data == {"key": "value"}
        assert data.metadata == {"source_ip": "127.0.0.1"}
    
    def test_get_field_value(self):
        """Test getting field values using dot notation."""
        data = TriggerData(
            source="email",
            timestamp=datetime.now(),
            data={
                "email": {
                    "subject": "Test Subject",
                    "sender": "test@example.com"
                },
                "simple_field": "value"
            }
        )
        
        assert data.get_field_value("email.subject") == "Test Subject"
        assert data.get_field_value("email.sender") == "test@example.com"
        assert data.get_field_value("simple_field") == "value"
        assert data.get_field_value("nonexistent.field") is None
        assert data.get_field_value("email.nonexistent") is None
    
    def test_trigger_data_serialization(self):
        """Test TriggerData serialization and deserialization."""
        now = datetime.now()
        original = TriggerData(
            source="webhook",
            timestamp=now,
            data={"test": "data"},
            metadata={"meta": "value"}
        )
        
        # Test to_dict
        data_dict = original.to_dict()
        assert data_dict["source"] == "webhook"
        assert data_dict["timestamp"] == now.isoformat()
        assert data_dict["data"] == {"test": "data"}
        assert data_dict["metadata"] == {"meta": "value"}
        
        # Test from_dict
        restored = TriggerData.from_dict(data_dict)
        assert restored.source == original.source
        assert restored.timestamp == original.timestamp
        assert restored.data == original.data
        assert restored.metadata == original.metadata
        
        # Test JSON serialization
        json_str = original.to_json()
        restored_from_json = TriggerData.from_json(json_str)
        assert restored_from_json.source == original.source
        assert restored_from_json.data == original.data
    
    def test_trigger_data_validation(self):
        """Test TriggerData validation."""
        now = datetime.now()
        
        # Valid data should pass
        valid_data = TriggerData("webhook", now, {"key": "value"})
        DataValidator.validate_trigger_data(valid_data)  # Should not raise
        
        # Invalid source
        with pytest.raises(ValidationError) as exc_info:
            invalid_data = TriggerData("", now, {"key": "value"})
            DataValidator.validate_trigger_data(invalid_data)
        assert "Source must be a non-empty string" in str(exc_info.value)
        
        # Invalid source type
        with pytest.raises(ValidationError) as exc_info:
            invalid_data = TriggerData("invalid_source", now, {"key": "value"})
            DataValidator.validate_trigger_data(invalid_data)
        assert "Invalid source" in str(exc_info.value)
        
        # Invalid timestamp
        with pytest.raises(ValidationError) as exc_info:
            invalid_data = TriggerData("webhook", "not_datetime", {"key": "value"})
            DataValidator.validate_trigger_data(invalid_data)
        assert "Timestamp must be a datetime object" in str(exc_info.value)


class TestEmailMessage:
    """Test EmailMessage model and validation."""
    
    def test_create_email_message(self):
        """Test creating a valid EmailMessage instance."""
        email = EmailMessage(
            subject="Test Subject",
            sender="sender@example.com",
            recipient="recipient@example.com",
            body="Test body content",
            headers={"Message-ID": "123"},
            attachments=[],
            timestamp=datetime.now()
        )
        
        assert email.subject == "Test Subject"
        assert email.sender == "sender@example.com"
        assert email.recipient == "recipient@example.com"
        assert email.body == "Test body content"
    
    def test_email_message_serialization(self):
        """Test EmailMessage serialization and deserialization."""
        now = datetime.now()
        attachment = Attachment("test.txt", "text/plain", 100)
        
        original = EmailMessage(
            subject="Test",
            sender="sender@example.com",
            recipient="recipient@example.com",
            body="Body",
            headers={"X-Test": "value"},
            attachments=[attachment],
            timestamp=now
        )
        
        # Test to_dict
        data_dict = original.to_dict()
        assert data_dict["subject"] == "Test"
        assert data_dict["sender"] == "sender@example.com"
        assert len(data_dict["attachments"]) == 1
        
        # Test from_dict
        restored = EmailMessage.from_dict(data_dict)
        assert restored.subject == original.subject
        assert restored.sender == original.sender
        assert len(restored.attachments) == 1
        assert restored.attachments[0].filename == "test.txt"
    
    def test_email_validation(self):
        """Test EmailMessage validation."""
        # Valid email should pass
        valid_email = EmailMessage(
            subject="Test",
            sender="sender@example.com",
            recipient="recipient@example.com",
            body="Body"
        )
        DataValidator.validate_email_message(valid_email)  # Should not raise
        
        # Invalid sender email
        with pytest.raises(ValidationError) as exc_info:
            invalid_email = EmailMessage(
                subject="Test",
                sender="invalid-email",
                recipient="recipient@example.com",
                body="Body"
            )
            DataValidator.validate_email_message(invalid_email)
        assert "Invalid sender email format" in str(exc_info.value)
        
        # Empty recipient
        with pytest.raises(ValidationError) as exc_info:
            invalid_email = EmailMessage(
                subject="Test",
                sender="sender@example.com",
                recipient="",
                body="Body"
            )
            DataValidator.validate_email_message(invalid_email)
        assert "Recipient must be a non-empty string" in str(exc_info.value)


class TestAttachment:
    """Test Attachment model and validation."""
    
    def test_create_attachment(self):
        """Test creating a valid Attachment instance."""
        attachment = Attachment(
            filename="test.pdf",
            content_type="application/pdf",
            size=1024,
            content=b"fake pdf content"
        )
        
        assert attachment.filename == "test.pdf"
        assert attachment.content_type == "application/pdf"
        assert attachment.size == 1024
        assert attachment.content == b"fake pdf content"
    
    def test_attachment_serialization(self):
        """Test Attachment serialization."""
        attachment = Attachment("test.txt", "text/plain", 100, b"content")
        
        data_dict = attachment.to_dict()
        assert data_dict["filename"] == "test.txt"
        assert data_dict["content_type"] == "text/plain"
        assert data_dict["size"] == 100
        assert data_dict["has_content"] is True
        
        # Test from_dict (content is not restored for security)
        restored = Attachment.from_dict(data_dict)
        assert restored.filename == "test.txt"
        assert restored.content is None
    
    def test_attachment_validation(self):
        """Test Attachment validation."""
        # Valid attachment should pass
        valid_attachment = Attachment("test.txt", "text/plain", 100)
        DataValidator.validate_attachment(valid_attachment)  # Should not raise
        
        # Empty filename
        with pytest.raises(ValidationError) as exc_info:
            invalid_attachment = Attachment("", "text/plain", 100)
            DataValidator.validate_attachment(invalid_attachment)
        assert "Filename must be a non-empty string" in str(exc_info.value)
        
        # Negative size
        with pytest.raises(ValidationError) as exc_info:
            invalid_attachment = Attachment("test.txt", "text/plain", -1)
            DataValidator.validate_attachment(invalid_attachment)
        assert "Size must be a non-negative integer" in str(exc_info.value)


class TestAgentResult:
    """Test AgentResult model and validation."""
    
    def test_create_agent_result(self):
        """Test creating a valid AgentResult instance."""
        result = AgentResult(
            success=True,
            output={"result": "processed"},
            notes=["Processing completed"],
            requires_human_review=False,
            execution_time=1.5,
            agent_name="test_agent"
        )
        
        assert result.success is True
        assert result.output == {"result": "processed"}
        assert result.notes == ["Processing completed"]
        assert result.execution_time == 1.5
    
    def test_agent_result_methods(self):
        """Test AgentResult helper methods."""
        result = AgentResult(success=True, output={})
        
        # Test add_note
        result.add_note("First note")
        result.add_note("Second note")
        assert len(result.notes) == 2
        assert result.notes[0] == "First note"
        
        # Test set_error
        result.set_error("Something went wrong")
        assert result.success is False
        assert result.error_message == "Something went wrong"
    
    def test_agent_result_serialization(self):
        """Test AgentResult serialization and deserialization."""
        original = AgentResult(
            success=True,
            output={"key": "value"},
            notes=["note1", "note2"],
            requires_human_review=True,
            execution_time=2.5,
            agent_name="test_agent",
            metadata={"meta": "data"}
        )
        
        # Test serialization
        data_dict = original.to_dict()
        assert data_dict["success"] is True
        assert data_dict["output"] == {"key": "value"}
        assert data_dict["notes"] == ["note1", "note2"]
        
        # Test deserialization
        restored = AgentResult.from_dict(data_dict)
        assert restored.success == original.success
        assert restored.output == original.output
        assert restored.notes == original.notes
        assert restored.execution_time == original.execution_time
    
    def test_agent_result_validation(self):
        """Test AgentResult validation."""
        # Valid result should pass
        valid_result = AgentResult(success=True, output={})
        DataValidator.validate_agent_result(valid_result)  # Should not raise
        
        # Invalid success type
        with pytest.raises(ValidationError) as exc_info:
            invalid_result = AgentResult(success="true", output={})
            DataValidator.validate_agent_result(invalid_result)
        assert "Success must be a boolean" in str(exc_info.value)
        
        # Invalid execution time
        with pytest.raises(ValidationError) as exc_info:
            invalid_result = AgentResult(success=True, output={}, execution_time=-1)
            DataValidator.validate_agent_result(invalid_result)
        assert "Execution time must be a non-negative number" in str(exc_info.value)


class TestSalesNotes:
    """Test SalesNotes model and validation."""
    
    def test_create_sales_notes(self):
        """Test creating a valid SalesNotes instance."""
        notes = SalesNotes(
            customer_problem="Need better software",
            proposed_solution="Implement our AI solution",
            urgency_level="high",
            follow_up_required=True,
            key_points=["Budget approved", "Timeline: 3 months"],
            customer_info={"company": "Acme Corp"},
            estimated_value=50000.0,
            next_steps=["Schedule demo", "Send proposal"]
        )
        
        assert notes.customer_problem == "Need better software"
        assert notes.urgency_level == "high"
        assert notes.follow_up_required is True
        assert notes.estimated_value == 50000.0
    
    def test_sales_notes_serialization(self):
        """Test SalesNotes serialization and deserialization."""
        original = SalesNotes(
            customer_problem="Problem",
            proposed_solution="Solution",
            urgency_level="medium",
            follow_up_required=False,
            key_points=["point1"],
            next_steps=["step1"]
        )
        
        # Test serialization
        data_dict = original.to_dict()
        assert data_dict["customer_problem"] == "Problem"
        assert data_dict["urgency_level"] == "medium"
        
        # Test deserialization
        restored = SalesNotes.from_dict(data_dict)
        assert restored.customer_problem == original.customer_problem
        assert restored.urgency_level == original.urgency_level
        assert restored.follow_up_required == original.follow_up_required
    
    def test_sales_notes_validation(self):
        """Test SalesNotes validation."""
        # Valid notes should pass
        valid_notes = SalesNotes(
            customer_problem="Problem",
            proposed_solution="Solution",
            urgency_level="low",
            follow_up_required=False
        )
        DataValidator.validate_sales_notes(valid_notes)  # Should not raise
        
        # Empty customer problem
        with pytest.raises(ValidationError) as exc_info:
            invalid_notes = SalesNotes(
                customer_problem="",
                proposed_solution="Solution",
                urgency_level="low",
                follow_up_required=False
            )
            DataValidator.validate_sales_notes(invalid_notes)
        assert "Customer problem must be a non-empty string" in str(exc_info.value)
        
        # Invalid urgency level
        with pytest.raises(ValidationError) as exc_info:
            invalid_notes = SalesNotes(
                customer_problem="Problem",
                proposed_solution="Solution",
                urgency_level="invalid",
                follow_up_required=False
            )
            DataValidator.validate_sales_notes(invalid_notes)
        assert "Invalid urgency level" in str(exc_info.value)


class TestWorkflowContext:
    """Test WorkflowContext model and validation."""
    
    def test_create_workflow_context(self):
        """Test creating a valid WorkflowContext instance."""
        trigger_data = TriggerData("webhook", datetime.now(), {"key": "value"})
        context = WorkflowContext(
            workflow_id="wf-123",
            agent_name="test_agent",
            trigger_data=trigger_data,
            start_time=datetime.now()
        )
        
        assert context.workflow_id == "wf-123"
        assert context.agent_name == "test_agent"
        assert context.trigger_data == trigger_data
    
    def test_workflow_context_methods(self):
        """Test WorkflowContext helper methods."""
        trigger_data = TriggerData("webhook", datetime.now(), {"key": "value"})
        context = WorkflowContext(
            workflow_id="wf-123",
            agent_name="test_agent",
            trigger_data=trigger_data,
            start_time=datetime.now()
        )
        
        # Test add_step
        context.add_step("step1")
        assert context.current_step == "step1"
        assert len(context.step_history) == 0
        
        context.add_step("step2")
        assert context.current_step == "step2"
        assert context.step_history == ["step1"]
        
        # Test variables
        context.set_variable("key", "value")
        assert context.get_variable("key") == "value"
        assert context.get_variable("nonexistent", "default") == "default"


class TestValidationFunctions:
    """Test validation utility functions."""
    
    def test_validate_input_data(self):
        """Test generic validate_input_data function."""
        # Valid data should pass
        trigger_data = TriggerData("webhook", datetime.now(), {"key": "value"})
        validate_input_data(trigger_data, TriggerData)  # Should not raise
        
        # Wrong type should fail
        with pytest.raises(ValidationError) as exc_info:
            validate_input_data("not_trigger_data", TriggerData)
        assert "Expected TriggerData, got str" in str(exc_info.value)
    
    def test_email_address_validation(self):
        """Test email address validation."""
        # Valid emails
        assert DataValidator.validate_email_address("test@example.com") is True
        assert DataValidator.validate_email_address("user.name+tag@domain.co.uk") is True
        
        # Invalid emails
        assert DataValidator.validate_email_address("invalid-email") is False
        assert DataValidator.validate_email_address("@domain.com") is False
        assert DataValidator.validate_email_address("user@") is False
        assert DataValidator.validate_email_address("") is False
        assert DataValidator.validate_email_address(None) is False
    
    def test_urgency_level_validation(self):
        """Test urgency level validation."""
        # Valid levels
        assert DataValidator.validate_urgency_level("low") is True
        assert DataValidator.validate_urgency_level("medium") is True
        assert DataValidator.validate_urgency_level("high") is True
        assert DataValidator.validate_urgency_level("critical") is True
        assert DataValidator.validate_urgency_level("HIGH") is True  # Case insensitive
        
        # Invalid levels
        assert DataValidator.validate_urgency_level("invalid") is False
        assert DataValidator.validate_urgency_level("") is False
    
    def test_trigger_source_validation(self):
        """Test trigger source validation."""
        # Valid sources
        assert DataValidator.validate_trigger_source("webhook") is True
        assert DataValidator.validate_trigger_source("email") is True
        assert DataValidator.validate_trigger_source("api") is True
        assert DataValidator.validate_trigger_source("manual") is True
        assert DataValidator.validate_trigger_source("scheduled") is True
        assert DataValidator.validate_trigger_source("EMAIL") is True  # Case insensitive
        
        # Invalid sources
        assert DataValidator.validate_trigger_source("invalid") is False
        assert DataValidator.validate_trigger_source("") is False


class TestSerialization:
    """Test serialization utilities."""
    
    def test_serialize_to_dict(self):
        """Test serialize_to_dict utility function."""
        trigger_data = TriggerData("webhook", datetime.now(), {"key": "value"})
        result_dict = serialize_to_dict(trigger_data)
        
        assert isinstance(result_dict, dict)
        assert result_dict["source"] == "webhook"
        assert "timestamp" in result_dict
    
    def test_deserialize_from_dict(self):
        """Test deserialize_from_dict utility function."""
        data_dict = {
            "source": "webhook",
            "timestamp": datetime.now().isoformat(),
            "data": {"key": "value"},
            "metadata": {}
        }
        
        trigger_data = deserialize_from_dict(data_dict, TriggerData)
        assert isinstance(trigger_data, TriggerData)
        assert trigger_data.source == "webhook"
        assert trigger_data.data == {"key": "value"}
    
    def test_serialization_errors(self):
        """Test serialization error handling."""
        # Test unsupported type
        with pytest.raises(SerializationError) as exc_info:
            serialize_to_dict("unsupported_type")
        assert "No serializer found for type" in str(exc_info.value)
        
        # Test invalid data for deserialization
        with pytest.raises(SerializationError) as exc_info:
            deserialize_from_dict({"invalid": "data"}, TriggerData)
        assert "Missing required field" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])