"""
Models module - Contains data models and structures.

This module defines the core data structures used throughout the framework
for representing triggers, results, and other data objects.
"""

from .data_models import (
    TriggerData,
    EmailMessage,
    Attachment,
    AgentResult,
    SalesNotes,
    WorkflowContext,
    WorkflowResult,
    AgentMatch
)
from .config_models import (
    WorkflowConfig,
    AgentConfig,
    LLMConfig,
    FrameworkConfig
)

# Create validation utilities
import re
from typing import Any, Type

class ValidationError(Exception):
    """Exception for validation errors."""
    pass

class SerializationError(Exception):
    """Exception for serialization errors."""
    pass

class DataValidator:
    """Data validator with specific validation methods."""
    
    @staticmethod
    def validate(data):
        return True
    
    @staticmethod
    def validate_trigger_data(data):
        """Validate TriggerData."""
        if not data.source:
            raise ValidationError("Source is required")
        return True
    
    @staticmethod
    def validate_email_message(data):
        """Validate EmailMessage."""
        if not data.subject:
            raise ValidationError("Subject is required")
        return True
    
    @staticmethod
    def validate_attachment(data):
        """Validate Attachment."""
        if not data.filename:
            raise ValidationError("Filename is required")
        return True
    
    @staticmethod
    def validate_agent_result(data):
        """Validate AgentResult."""
        if data.success is None:
            raise ValidationError("Success status is required")
        return True
    
    @staticmethod
    def validate_sales_notes(data):
        """Validate SalesNotes."""
        if not data.customer_problem:
            raise ValidationError("Customer problem is required")
        return True
    
    @staticmethod
    def validate_email_address(email: str) -> bool:
        """Validate email address format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_urgency_level(level: str) -> bool:
        """Validate urgency level."""
        valid_levels = ["low", "medium", "high", "critical"]
        return level.lower() in valid_levels
    
    @staticmethod
    def validate_trigger_source(source: str) -> bool:
        """Validate trigger source."""
        valid_sources = ["webhook", "email", "api", "manual", "scheduled"]
        return source.lower() in valid_sources

def validate_input_data(data, data_type: Type = None):
    """Validate input data."""
    if data_type:
        # Type-specific validation could go here
        pass
    return DataValidator.validate(data)

def serialize_to_dict(obj):
    """Serialize object to dict."""
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    elif hasattr(obj, '_asdict'):  # namedtuple
        return obj._asdict()
    else:
        raise SerializationError(f"Cannot serialize object of type {type(obj)}")

def deserialize_from_dict(data, cls):
    """Deserialize dict to object."""
    try:
        if hasattr(cls, '__init__'):
            return cls(**data)
        return data
    except Exception as e:
        raise SerializationError(f"Cannot deserialize to {cls}: {e}")

__all__ = [
    "TriggerData",
    "EmailMessage", 
    "Attachment",
    "AgentResult",
    "SalesNotes",
    "WorkflowContext",
    "WorkflowResult",
    "AgentMatch",
    "DataValidator",
    "ValidationError",
    "validate_input_data",
    "serialize_to_dict",
    "deserialize_from_dict",
    "SerializationError",
    "WorkflowConfig",
    "AgentConfig",
    "LLMConfig",
    "FrameworkConfig"
]