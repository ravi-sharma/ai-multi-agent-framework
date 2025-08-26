"""Logging utilities and configuration."""

import logging
import sys
from typing import Optional
from pathlib import Path
from datetime import datetime


def setup_logger(
    name: str = "ai_agent_framework",
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with console and optional file output.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        format_string: Optional custom format string
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Default format
    if not format_string:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "ai_agent_framework") -> logging.Logger:
    """
    Get an existing logger or create a new one with default settings.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set it up with defaults
    if not logger.handlers:
        return setup_logger(name)
    
    return logger


class StructuredLogger:
    """Structured logging utility for better log analysis."""
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize structured logger.
        
        Args:
            logger: Base logger instance
        """
        self.logger = logger
    
    def log_agent_processing(self, agent_name: str, input_data: dict, 
                           result: dict, execution_time: float, success: bool):
        """
        Log agent processing with structured data.
        
        Args:
            agent_name: Name of the agent
            input_data: Input data (sanitized)
            result: Processing result (sanitized)
            execution_time: Execution time in seconds
            success: Whether processing was successful
        """
        log_data = {
            "event": "agent_processing",
            "agent_name": agent_name,
            "execution_time": execution_time,
            "success": success,
            "input_size": len(str(input_data)),
            "result_size": len(str(result)),
            "timestamp": datetime.now().isoformat()
        }
        
        if success:
            self.logger.info(f"Agent processing completed: {log_data}")
        else:
            self.logger.error(f"Agent processing failed: {log_data}")
    
    def log_workflow_step(self, workflow_id: str, step_name: str, 
                         step_result: dict, step_time: float):
        """
        Log workflow step execution.
        
        Args:
            workflow_id: Workflow identifier
            step_name: Name of the workflow step
            step_result: Step execution result
            step_time: Step execution time
        """
        log_data = {
            "event": "workflow_step",
            "workflow_id": workflow_id,
            "step_name": step_name,
            "step_time": step_time,
            "success": step_result.get("success", False),
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"Workflow step executed: {log_data}")
    
    def log_llm_request(self, provider: str, model: str, prompt_length: int,
                       response_length: int, tokens_used: int, cost: float,
                       response_time: float):
        """
        Log LLM API request for cost and performance tracking.
        
        Args:
            provider: LLM provider name
            model: Model name
            prompt_length: Length of prompt
            response_length: Length of response
            tokens_used: Number of tokens used
            cost: Estimated cost
            response_time: Response time in seconds
        """
        log_data = {
            "event": "llm_request",
            "provider": provider,
            "model": model,
            "prompt_length": prompt_length,
            "response_length": response_length,
            "tokens_used": tokens_used,
            "cost": cost,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"LLM request completed: {log_data}")
    
    def log_error(self, error_type: str, error_message: str, context: dict = None):
        """
        Log error with structured context.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Additional context information
        """
        log_data = {
            "event": "error",
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.error(f"Error occurred: {log_data}")


def sanitize_log_data(data: dict, sensitive_keys: list = None) -> dict:
    """
    Sanitize log data by removing or masking sensitive information.
    
    Args:
        data: Data to sanitize
        sensitive_keys: List of keys to sanitize
        
    Returns:
        Sanitized data dictionary
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "password", "api_key", "token", "secret", "credential",
            "email_password", "openai_api_key", "anthropic_api_key"
        ]
    
    sanitized = {}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Check if key contains sensitive information
        if any(sensitive_key in key_lower for sensitive_key in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value, sensitive_keys)
        elif isinstance(value, str) and len(value) > 1000:
            # Truncate very long strings
            sanitized[key] = value[:1000] + "...[truncated]"
        else:
            sanitized[key] = value
    
    return sanitized


class LoggingContext:
    """Context manager for adding context to log messages."""
    
    def __init__(self, logger: logging.Logger, context: dict):
        """
        Initialize logging context.
        
        Args:
            logger: Logger instance
            context: Context information to add to logs
        """
        self.logger = logger
        self.context = context
        self.original_factory = logging.getLogRecordFactory()
    
    def __enter__(self):
        """Enter context manager."""
        def record_factory(*args, **kwargs):
            record = self.original_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        logging.setLogRecordFactory(self.original_factory)