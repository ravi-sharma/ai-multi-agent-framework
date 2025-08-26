"""Custom exceptions for the AI Agent Framework."""


class FrameworkError(Exception):
    """Base exception for framework errors."""
    pass


class LLMError(FrameworkError):
    """Base exception for LLM-related errors."""
    pass


class LLMAPIError(LLMError):
    """Exception for LLM API errors."""
    pass


class LLMRateLimitError(LLMError):
    """Exception for LLM rate limit errors."""
    pass


class LLMAuthenticationError(LLMError):
    """Exception for LLM authentication errors."""
    pass


class LLMTimeoutError(LLMError):
    """Exception for LLM timeout errors."""
    pass


class LLMProviderError(LLMError):
    """Exception for LLM provider errors."""
    pass


class LLMConfigurationError(LLMError):
    """Exception for LLM configuration errors."""
    pass


class AgentProcessingError(FrameworkError):
    """Exception for agent processing errors."""
    pass


class ConfigurationError(FrameworkError):
    """Exception for configuration errors."""
    pass


class WorkflowError(FrameworkError):
    """Exception for workflow errors."""
    pass


class ValidationError(FrameworkError):
    """Exception for validation errors."""
    pass