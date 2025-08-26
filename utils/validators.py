"""Validation utilities for data and configuration."""

import re
import json
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from email.utils import parseaddr


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Basic email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    except Exception:
        return False


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Basic URL regex pattern
        pattern = r'^https?://[^\s<>"{}|\\^`\[\]]+$'
        return bool(re.match(pattern, url.strip()))
    except Exception:
        return False


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format (basic validation).
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
        
        # Check if it's all digits and reasonable length
        return cleaned.isdigit() and 10 <= len(cleaned) <= 15
    except Exception:
        return False


def validate_json(json_string: str) -> tuple[bool, Optional[dict]]:
    """
    Validate JSON string and return parsed data.
    
    Args:
        json_string: JSON string to validate
        
    Returns:
        Tuple of (is_valid, parsed_data)
    """
    try:
        parsed = json.loads(json_string)
        return True, parsed
    except json.JSONDecodeError:
        return False, None


def validate_yaml(yaml_string: str) -> tuple[bool, Optional[dict]]:
    """
    Validate YAML string and return parsed data.
    
    Args:
        yaml_string: YAML string to validate
        
    Returns:
        Tuple of (is_valid, parsed_data)
    """
    try:
        parsed = yaml.safe_load(yaml_string)
        return True, parsed
    except yaml.YAMLError:
        return False, None


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate framework configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        Dictionary containing validation results
    """
    errors = []
    warnings = []
    
    # Required top-level sections
    required_sections = ['agents', 'llm_providers']
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
    
    # Validate agents section
    if 'agents' in config:
        agents_errors, agents_warnings = _validate_agents_config(config['agents'])
        errors.extend(agents_errors)
        warnings.extend(warnings)
    
    # Validate LLM providers section
    if 'llm_providers' in config:
        llm_errors, llm_warnings = _validate_llm_providers_config(config['llm_providers'])
        errors.extend(llm_errors)
        warnings.extend(llm_warnings)
    
    # Validate email section (if present)
    if 'email' in config:
        email_errors, email_warnings = _validate_email_config(config['email'])
        errors.extend(email_errors)
        warnings.extend(email_warnings)
    
    # Validate monitoring section (if present)
    if 'monitoring' in config:
        monitoring_errors, monitoring_warnings = _validate_monitoring_config(config['monitoring'])
        errors.extend(monitoring_errors)
        warnings.extend(monitoring_warnings)
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'sections_validated': list(config.keys())
    }


def _validate_agents_config(agents_config: Dict[str, Any]) -> tuple[List[str], List[str]]:
    """Validate agents configuration section."""
    errors = []
    warnings = []
    
    if not isinstance(agents_config, dict):
        errors.append("Agents config must be a dictionary")
        return errors, warnings
    
    for agent_name, agent_config in agents_config.items():
        if not isinstance(agent_config, dict):
            errors.append(f"Agent '{agent_name}' config must be a dictionary")
            continue
        
        # Required fields
        if 'agent_type' not in agent_config:
            errors.append(f"Agent '{agent_name}' missing required 'agent_type'")
        
        # Optional but recommended fields
        if 'enabled' not in agent_config:
            warnings.append(f"Agent '{agent_name}' missing 'enabled' field, defaulting to true")
        
        if 'llm_provider' not in agent_config:
            warnings.append(f"Agent '{agent_name}' missing 'llm_provider' field")
        
        # Validate workflow_config if present
        if 'workflow_config' in agent_config:
            workflow_config = agent_config['workflow_config']
            if not isinstance(workflow_config, dict):
                errors.append(f"Agent '{agent_name}' workflow_config must be a dictionary")
            else:
                # Validate workflow config fields
                if 'max_retries' in workflow_config:
                    if not isinstance(workflow_config['max_retries'], int) or workflow_config['max_retries'] < 0:
                        errors.append(f"Agent '{agent_name}' max_retries must be a non-negative integer")
                
                if 'timeout' in workflow_config:
                    if not isinstance(workflow_config['timeout'], (int, float)) or workflow_config['timeout'] <= 0:
                        errors.append(f"Agent '{agent_name}' timeout must be a positive number")
    
    return errors, warnings


def _validate_llm_providers_config(llm_config: Dict[str, Any]) -> tuple[List[str], List[str]]:
    """Validate LLM providers configuration section."""
    errors = []
    warnings = []
    
    if not isinstance(llm_config, dict):
        errors.append("LLM providers config must be a dictionary")
        return errors, warnings
    
    # Check for at least one provider
    if not llm_config:
        errors.append("At least one LLM provider must be configured")
        return errors, warnings
    
    for provider_name, provider_config in llm_config.items():
        if not isinstance(provider_config, dict):
            errors.append(f"LLM provider '{provider_name}' config must be a dictionary")
            continue
        
        # Validate common fields
        if 'api_key' not in provider_config:
            errors.append(f"LLM provider '{provider_name}' missing required 'api_key'")
        
        if 'model' not in provider_config:
            warnings.append(f"LLM provider '{provider_name}' missing 'model' field")
        
        # Provider-specific validation
        if provider_name == 'openai':
            if 'model' in provider_config:
                valid_models = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo-preview']
                if provider_config['model'] not in valid_models:
                    warnings.append(f"OpenAI model '{provider_config['model']}' may not be valid")
        
        elif provider_name == 'anthropic':
            if 'model' in provider_config:
                if not provider_config['model'].startswith('claude-'):
                    warnings.append(f"Anthropic model '{provider_config['model']}' may not be valid")
        
        elif provider_name == 'azure_openai':
            required_fields = ['endpoint', 'api_version', 'deployment']
            for field in required_fields:
                if field not in provider_config:
                    errors.append(f"Azure OpenAI provider missing required field: {field}")
        
        # Validate numeric parameters
        numeric_fields = ['max_tokens', 'temperature', 'top_p']
        for field in numeric_fields:
            if field in provider_config:
                value = provider_config[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"LLM provider '{provider_name}' {field} must be a number")
                elif field == 'max_tokens' and value <= 0:
                    errors.append(f"LLM provider '{provider_name}' max_tokens must be positive")
                elif field in ['temperature', 'top_p'] and not (0 <= value <= 2):
                    warnings.append(f"LLM provider '{provider_name}' {field} should be between 0 and 2")
    
    return errors, warnings


def _validate_email_config(email_config: Dict[str, Any]) -> tuple[List[str], List[str]]:
    """Validate email configuration section."""
    errors = []
    warnings = []
    
    if not isinstance(email_config, dict):
        errors.append("Email config must be a dictionary")
        return errors, warnings
    
    # Required fields when email is enabled
    if email_config.get('enabled', False):
        required_fields = ['host', 'username', 'password']
        for field in required_fields:
            if field not in email_config:
                errors.append(f"Email config missing required field: {field}")
        
        # Validate email address
        if 'username' in email_config:
            if not validate_email(email_config['username']):
                errors.append(f"Email username '{email_config['username']}' is not a valid email address")
        
        # Validate port
        if 'port' in email_config:
            port = email_config['port']
            if not isinstance(port, int) or not (1 <= port <= 65535):
                errors.append("Email port must be an integer between 1 and 65535")
        
        # Validate polling interval
        if 'polling_interval' in email_config:
            interval = email_config['polling_interval']
            if not isinstance(interval, int) or interval <= 0:
                errors.append("Email polling_interval must be a positive integer")
            elif interval < 30:
                warnings.append("Email polling_interval less than 30 seconds may cause rate limiting")
    
    return errors, warnings


def _validate_monitoring_config(monitoring_config: Dict[str, Any]) -> tuple[List[str], List[str]]:
    """Validate monitoring configuration section."""
    errors = []
    warnings = []
    
    if not isinstance(monitoring_config, dict):
        errors.append("Monitoring config must be a dictionary")
        return errors, warnings
    
    # Validate port
    if 'port' in monitoring_config:
        port = monitoring_config['port']
        if not isinstance(port, int) or not (1 <= port <= 65535):
            errors.append("Monitoring port must be an integer between 1 and 65535")
    
    # Validate health check interval
    if 'health_check_interval' in monitoring_config:
        interval = monitoring_config['health_check_interval']
        if not isinstance(interval, int) or interval <= 0:
            errors.append("Health check interval must be a positive integer")
        elif interval < 10:
            warnings.append("Health check interval less than 10 seconds may impact performance")
    
    return errors, warnings


def validate_agent_input(input_data: Dict[str, Any], agent_type: str = None) -> Dict[str, Any]:
    """
    Validate input data for agent processing.
    
    Args:
        input_data: Input data to validate
        agent_type: Optional agent type for specific validation
        
    Returns:
        Dictionary containing validation results
    """
    errors = []
    warnings = []
    
    # Basic structure validation
    if not isinstance(input_data, dict):
        errors.append("Input data must be a dictionary")
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    
    # Required fields
    if 'source' not in input_data:
        errors.append("Input data missing required 'source' field")
    
    if 'data' not in input_data:
        errors.append("Input data missing required 'data' field")
    elif not isinstance(input_data['data'], dict):
        errors.append("Input data 'data' field must be a dictionary")
    
    # Agent-specific validation
    if agent_type == 'sales_agent':
        if 'data' in input_data and 'email' in input_data['data']:
            email_data = input_data['data']['email']
            if not isinstance(email_data, dict):
                errors.append("Email data must be a dictionary")
            else:
                # Validate email fields
                if 'sender' in email_data and not validate_email(email_data['sender']):
                    errors.append(f"Invalid sender email: {email_data['sender']}")
                
                if not email_data.get('subject') and not email_data.get('body'):
                    warnings.append("Email has neither subject nor body content")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


def validate_file_path(file_path: Union[str, Path], must_exist: bool = True) -> bool:
    """
    Validate file path.
    
    Args:
        file_path: File path to validate
        must_exist: Whether file must exist
        
    Returns:
        True if valid, False otherwise
    """
    try:
        path = Path(file_path)
        
        if must_exist:
            return path.exists() and path.is_file()
        else:
            # Check if parent directory exists and is writable
            return path.parent.exists() and path.parent.is_dir()
    except Exception:
        return False