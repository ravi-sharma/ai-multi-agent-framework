"""Common mixins for reducing code duplication across the framework."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime


class LoggerMixin:
    """Mixin to provide consistent logging across classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get a logger instance for this class."""
        if not hasattr(self, '_logger'):
            module_name = self.__class__.__module__
            class_name = self.__class__.__name__
            self._logger = logging.getLogger(f"{module_name}.{class_name}")
        return self._logger
    
    def log_info(self, message: str, **kwargs):
        """Log an info message with optional context."""
        if kwargs:
            message = f"{message} - Context: {kwargs}"
        self.logger.info(message)
    
    def log_error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log an error message with optional exception and context."""
        if error:
            message = f"{message} - Error: {str(error)}"
        if kwargs:
            message = f"{message} - Context: {kwargs}"
        self.logger.error(message, exc_info=error is not None)
    
    def log_warning(self, message: str, **kwargs):
        """Log a warning message with optional context."""
        if kwargs:
            message = f"{message} - Context: {kwargs}"
        self.logger.warning(message)
    
    def log_debug(self, message: str, **kwargs):
        """Log a debug message with optional context."""
        if kwargs:
            message = f"{message} - Context: {kwargs}"
        self.logger.debug(message)


class ConfigValidationMixin:
    """Mixin to provide common configuration validation methods."""
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration dictionary.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid, False otherwise
        """
        if not isinstance(config, dict):
            return False
        
        # Check for required fields if defined
        required_fields = getattr(self, 'REQUIRED_CONFIG_FIELDS', [])
        for field in required_fields:
            if field not in config:
                return False
        
        return True
    
    def get_config_value(self, key: str, default: Any = None, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Get a configuration value with fallback to default.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            config: Configuration dictionary (uses self.config if not provided)
            
        Returns:
            Configuration value or default
        """
        if config is None:
            config = getattr(self, 'config', {})
        
        return config.get(key, default)
    
    def validate_required_fields(self, config: Dict[str, Any], required_fields: list) -> tuple[bool, list]:
        """
        Validate that all required fields are present in config.
        
        Args:
            config: Configuration dictionary
            required_fields: List of required field names
            
        Returns:
            Tuple of (is_valid, missing_fields)
        """
        missing_fields = []
        for field in required_fields:
            if field not in config or config[field] is None:
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields


class TimestampMixin:
    """Mixin to provide timestamp tracking functionality."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def touch(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()
    
    def get_age_seconds(self) -> float:
        """Get the age of this object in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_time_since_update_seconds(self) -> float:
        """Get seconds since last update."""
        return (datetime.now() - self.updated_at).total_seconds()


class ValidationMixin:
    """Mixin to provide common validation methods."""
    
    def validate_email(self, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email is valid, False otherwise
        """
        import re
        
        if not email or not isinstance(email, str):
            return False
        
        # Basic email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_non_empty_string(self, value: Any, field_name: str = "field") -> bool:
        """
        Validate that a value is a non-empty string.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(value, str):
            return False
        
        return len(value.strip()) > 0
    
    def validate_dict_structure(self, data: Any, required_keys: list) -> tuple[bool, list]:
        """
        Validate dictionary structure.
        
        Args:
            data: Data to validate
            required_keys: List of required keys
            
        Returns:
            Tuple of (is_valid, missing_keys)
        """
        if not isinstance(data, dict):
            return False, required_keys
        
        missing_keys = [key for key in required_keys if key not in data]
        return len(missing_keys) == 0, missing_keys


class AgentMixin(LoggerMixin, ConfigValidationMixin, TimestampMixin):
    """
    Combined mixin for agent classes providing logging, config validation, and timestamps.
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None, *args, **kwargs):
        """
        Initialize agent with common functionality.
        
        Args:
            name: Agent name
            config: Agent configuration
        """
        super().__init__(*args, **kwargs)
        self.name = name
        self.config = config or {}
        self.is_enabled = self.get_config_value('enabled', True)
        
        # Validate configuration if validation is defined
        if hasattr(self, 'REQUIRED_CONFIG_FIELDS'):
            is_valid, missing = self.validate_required_fields(
                self.config, self.REQUIRED_CONFIG_FIELDS
            )
            if not is_valid:
                self.log_warning(f"Missing required config fields: {missing}")
        
        self.log_info(f"Initialized agent '{self.name}'", 
                     config_keys=list(self.config.keys()))
    
    def enable(self):
        """Enable this agent."""
        self.is_enabled = True
        self.touch()
        self.log_info(f"Agent '{self.name}' enabled")
    
    def disable(self):
        """Disable this agent."""
        self.is_enabled = False
        self.touch()
        self.log_info(f"Agent '{self.name}' disabled")
    
    def update_config(self, new_config: Dict[str, Any]):
        """
        Update agent configuration.
        
        Args:
            new_config: New configuration dictionary
        """
        self.config.update(new_config)
        self.touch()
        self.log_info(f"Updated config for agent '{self.name}'",
                     new_keys=list(new_config.keys()))
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about this agent.
        
        Returns:
            Dictionary containing agent metadata
        """
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'enabled': self.is_enabled,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'age_seconds': self.get_age_seconds(),
            'config': self.config
        }
