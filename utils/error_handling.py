"""Centralized error handling utilities for the AI Agent Framework."""

import traceback
import functools
from typing import Dict, Any, Optional, Callable, Type, Union, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .common_mixins import LoggerMixin
from .exceptions import AgentFrameworkError


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    PROCESSING = "processing"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    agent_name: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    operation: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'agent_name': self.agent_name,
            'request_id': self.request_id,
            'user_id': self.user_id,
            'operation': self.operation,
            'input_data': self.input_data,
            'metadata': self.metadata
        }


@dataclass
class ErrorInfo:
    """Structured error information."""
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: datetime
    context: Optional[ErrorContext] = None
    traceback_str: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 0
    is_recoverable: bool = False
    suggested_action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'error_type': self.error_type,
            'message': self.message,
            'severity': self.severity.value,
            'category': self.category.value,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context.to_dict() if self.context else None,
            'traceback': self.traceback_str,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'is_recoverable': self.is_recoverable,
            'suggested_action': self.suggested_action
        }


class ErrorHandler(LoggerMixin):
    """Centralized error handler with classification and recovery strategies."""
    
    def __init__(self):
        """Initialize error handler."""
        self.error_mappings: Dict[Type[Exception], ErrorCategory] = {
            ValueError: ErrorCategory.VALIDATION,
            KeyError: ErrorCategory.CONFIGURATION,
            ConnectionError: ErrorCategory.NETWORK,
            TimeoutError: ErrorCategory.TIMEOUT,
            PermissionError: ErrorCategory.AUTHORIZATION,
            FileNotFoundError: ErrorCategory.RESOURCE,
        }
        
        self.severity_mappings: Dict[ErrorCategory, ErrorSeverity] = {
            ErrorCategory.VALIDATION: ErrorSeverity.MEDIUM,
            ErrorCategory.CONFIGURATION: ErrorSeverity.HIGH,
            ErrorCategory.NETWORK: ErrorSeverity.MEDIUM,
            ErrorCategory.PROCESSING: ErrorSeverity.MEDIUM,
            ErrorCategory.AUTHENTICATION: ErrorSeverity.HIGH,
            ErrorCategory.AUTHORIZATION: ErrorSeverity.HIGH,
            ErrorCategory.RATE_LIMIT: ErrorSeverity.LOW,
            ErrorCategory.TIMEOUT: ErrorSeverity.MEDIUM,
            ErrorCategory.RESOURCE: ErrorSeverity.HIGH,
            ErrorCategory.UNKNOWN: ErrorSeverity.MEDIUM,
        }
        
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {
            ErrorCategory.NETWORK: self._retry_strategy,
            ErrorCategory.RATE_LIMIT: self._backoff_strategy,
            ErrorCategory.TIMEOUT: self._retry_strategy,
        }
    
    def classify_error(self, error: Exception) -> ErrorCategory:
        """
        Classify an error into a category.
        
        Args:
            error: Exception to classify
            
        Returns:
            Error category
        """
        error_type = type(error)
        
        # Direct mapping
        if error_type in self.error_mappings:
            return self.error_mappings[error_type]
        
        # Check inheritance
        for mapped_type, category in self.error_mappings.items():
            if isinstance(error, mapped_type):
                return category
        
        # Check error message for clues
        error_msg = str(error).lower()
        
        if any(keyword in error_msg for keyword in ['timeout', 'timed out']):
            return ErrorCategory.TIMEOUT
        elif any(keyword in error_msg for keyword in ['network', 'connection', 'dns']):
            return ErrorCategory.NETWORK
        elif any(keyword in error_msg for keyword in ['rate limit', 'too many requests']):
            return ErrorCategory.RATE_LIMIT
        elif any(keyword in error_msg for keyword in ['auth', 'permission', 'forbidden']):
            return ErrorCategory.AUTHORIZATION
        elif any(keyword in error_msg for keyword in ['validation', 'invalid', 'malformed']):
            return ErrorCategory.VALIDATION
        
        return ErrorCategory.UNKNOWN
    
    def get_severity(self, category: ErrorCategory) -> ErrorSeverity:
        """
        Get severity level for an error category.
        
        Args:
            category: Error category
            
        Returns:
            Error severity
        """
        return self.severity_mappings.get(category, ErrorSeverity.MEDIUM)
    
    def create_error_info(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        include_traceback: bool = True
    ) -> ErrorInfo:
        """
        Create structured error information.
        
        Args:
            error: Exception that occurred
            context: Optional error context
            include_traceback: Whether to include traceback
            
        Returns:
            ErrorInfo object
        """
        category = self.classify_error(error)
        severity = self.get_severity(category)
        
        error_info = ErrorInfo(
            error_type=type(error).__name__,
            message=str(error),
            severity=severity,
            category=category,
            timestamp=datetime.now(),
            context=context,
            traceback_str=traceback.format_exc() if include_traceback else None,
            is_recoverable=category in self.recovery_strategies
        )
        
        # Add suggested action based on category
        error_info.suggested_action = self._get_suggested_action(category)
        
        return error_info
    
    def _get_suggested_action(self, category: ErrorCategory) -> str:
        """Get suggested action for error category."""
        suggestions = {
            ErrorCategory.VALIDATION: "Check input data format and required fields",
            ErrorCategory.CONFIGURATION: "Verify configuration settings and required keys",
            ErrorCategory.NETWORK: "Check network connectivity and retry",
            ErrorCategory.PROCESSING: "Review processing logic and input data",
            ErrorCategory.AUTHENTICATION: "Verify API keys and authentication credentials",
            ErrorCategory.AUTHORIZATION: "Check user permissions and access rights",
            ErrorCategory.RATE_LIMIT: "Implement backoff strategy and reduce request rate",
            ErrorCategory.TIMEOUT: "Increase timeout values or optimize processing",
            ErrorCategory.RESOURCE: "Check file paths and resource availability",
            ErrorCategory.UNKNOWN: "Review error details and contact support if needed"
        }
        
        return suggestions.get(category, "Review error details and logs")
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        should_raise: bool = True
    ) -> ErrorInfo:
        """
        Handle an error with logging and classification.
        
        Args:
            error: Exception that occurred
            context: Optional error context
            should_raise: Whether to re-raise the exception
            
        Returns:
            ErrorInfo object
            
        Raises:
            Exception: Re-raises the original exception if should_raise is True
        """
        error_info = self.create_error_info(error, context)
        
        # Log based on severity
        log_context = {
            'error_type': error_info.error_type,
            'category': error_info.category.value,
            'severity': error_info.severity.value,
        }
        
        if context:
            log_context.update(context.to_dict())
        
        if error_info.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            self.log_error(f"Error occurred: {error_info.message}", error=error, **log_context)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.log_warning(f"Error occurred: {error_info.message}", **log_context)
        else:
            self.log_info(f"Error occurred: {error_info.message}", **log_context)
        
        if should_raise:
            raise error
        
        return error_info
    
    def _retry_strategy(self, error_info: ErrorInfo, max_retries: int = 3) -> bool:
        """
        Retry strategy for recoverable errors.
        
        Args:
            error_info: Error information
            max_retries: Maximum number of retries
            
        Returns:
            True if should retry, False otherwise
        """
        return error_info.retry_count < max_retries
    
    def _backoff_strategy(self, error_info: ErrorInfo, max_retries: int = 5) -> bool:
        """
        Backoff strategy for rate limit errors.
        
        Args:
            error_info: Error information
            max_retries: Maximum number of retries
            
        Returns:
            True if should retry, False otherwise
        """
        return error_info.retry_count < max_retries


# Global error handler instance
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_error(
    error: Exception,
    context: Optional[ErrorContext] = None,
    should_raise: bool = True
) -> ErrorInfo:
    """Handle an error using the global error handler."""
    handler = get_error_handler()
    return handler.handle_error(error, context, should_raise)


def create_error_context(
    agent_name: Optional[str] = None,
    request_id: Optional[str] = None,
    operation: Optional[str] = None,
    **kwargs
) -> ErrorContext:
    """Create an error context with the given parameters."""
    return ErrorContext(
        agent_name=agent_name,
        request_id=request_id,
        operation=operation,
        metadata=kwargs
    )


def error_handler_decorator(
    context: Optional[ErrorContext] = None,
    should_raise: bool = True,
    return_on_error: Any = None
):
    """
    Decorator for automatic error handling.
    
    Args:
        context: Optional error context
        should_raise: Whether to re-raise exceptions
        return_on_error: Value to return if error occurs and should_raise is False
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = handle_error(e, context, should_raise=False)
                
                if should_raise:
                    raise e
                else:
                    return return_on_error
        
        return wrapper
    return decorator


def async_error_handler_decorator(
    context: Optional[ErrorContext] = None,
    should_raise: bool = True,
    return_on_error: Any = None
):
    """
    Async decorator for automatic error handling.
    
    Args:
        context: Optional error context
        should_raise: Whether to re-raise exceptions
        return_on_error: Value to return if error occurs and should_raise is False
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_info = handle_error(e, context, should_raise=False)
                
                if should_raise:
                    raise e
                else:
                    return return_on_error
        
        return wrapper
    return decorator


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception
):
    """
    Decorator for retrying functions on specific exceptions.
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff: Backoff multiplier for delay
        exceptions: Exception types to retry on
        
    Returns:
        Decorator function
    """
    if not isinstance(exceptions, (list, tuple)):
        exceptions = [exceptions]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception type should be retried
                    if not any(isinstance(e, exc_type) for exc_type in exceptions):
                        raise e
                    
                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        break
                    
                    # Wait before retry
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            # All retries exhausted, raise the last exception
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator
