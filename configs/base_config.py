"""Base configuration class with common settings."""

import os
from typing import Dict, Any, Optional
from pathlib import Path


class BaseConfig:
    """Base configuration class with common settings."""
    
    def __init__(self):
        """Initialize base configuration."""
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "configs"
        self.data_dir = self.project_root / "data"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
    
    # Environment
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_WORKERS = int(os.getenv("API_WORKERS", "1"))
    
    # LLM Provider Configuration
    DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    
    # Anthropic Configuration
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
    ANTHROPIC_MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "2000"))
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    # Email Configuration
    EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "imap.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "993"))
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "true").lower() == "true"
    EMAIL_POLLING_INTERVAL = int(os.getenv("EMAIL_POLLING_INTERVAL", "60"))
    
    # Monitoring Configuration
    MONITORING_ENABLED = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
    MONITORING_PORT = int(os.getenv("MONITORING_PORT", "9090"))
    HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
    
    # LangSmith Configuration
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "ai-agent-framework")
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    
    # Memory/Storage Configuration
    MEMORY_BACKEND = os.getenv("MEMORY_BACKEND", "file")  # file, memory, redis
    MEMORY_TTL = int(os.getenv("MEMORY_TTL", "3600"))  # 1 hour default
    
    # Redis Configuration (if using Redis backend)
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    
    # Concurrent Processing
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))  # 5 minutes
    
    # Agent Configuration
    DEFAULT_AGENT_TIMEOUT = int(os.getenv("DEFAULT_AGENT_TIMEOUT", "180"))  # 3 minutes
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))
    
    def get_llm_config(self, provider: str = None) -> Dict[str, Any]:
        """
        Get LLM configuration for a specific provider.
        
        Args:
            provider: LLM provider name (defaults to DEFAULT_LLM_PROVIDER)
            
        Returns:
            Dictionary containing provider configuration
        """
        provider = provider or self.DEFAULT_LLM_PROVIDER
        
        configs = {
            "openai": {
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_MODEL,
                "max_tokens": self.OPENAI_MAX_TOKENS,
                "temperature": self.OPENAI_TEMPERATURE
            },
            "anthropic": {
                "api_key": self.ANTHROPIC_API_KEY,
                "model": self.ANTHROPIC_MODEL,
                "max_tokens": self.ANTHROPIC_MAX_TOKENS
            },
            "azure_openai": {
                "api_key": self.AZURE_OPENAI_API_KEY,
                "endpoint": self.AZURE_OPENAI_ENDPOINT,
                "api_version": self.AZURE_OPENAI_API_VERSION,
                "deployment": self.AZURE_OPENAI_DEPLOYMENT
            }
        }
        
        return configs.get(provider, {})
    
    def get_email_config(self) -> Dict[str, Any]:
        """
        Get email configuration.
        
        Returns:
            Dictionary containing email configuration
        """
        return {
            "enabled": self.EMAIL_ENABLED,
            "host": self.EMAIL_HOST,
            "port": self.EMAIL_PORT,
            "username": self.EMAIL_USERNAME,
            "password": self.EMAIL_PASSWORD,
            "use_ssl": self.EMAIL_USE_SSL,
            "polling_interval": self.EMAIL_POLLING_INTERVAL
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """
        Get monitoring configuration.
        
        Returns:
            Dictionary containing monitoring configuration
        """
        return {
            "enabled": self.MONITORING_ENABLED,
            "port": self.MONITORING_PORT,
            "health_check_interval": self.HEALTH_CHECK_INTERVAL
        }
    
    def get_memory_config(self) -> Dict[str, Any]:
        """
        Get memory/storage configuration.
        
        Returns:
            Dictionary containing memory configuration
        """
        config = {
            "backend": self.MEMORY_BACKEND,
            "ttl": self.MEMORY_TTL
        }
        
        if self.MEMORY_BACKEND == "redis":
            config.update({
                "redis_host": self.REDIS_HOST,
                "redis_port": self.REDIS_PORT,
                "redis_db": self.REDIS_DB,
                "redis_password": self.REDIS_PASSWORD
            })
        elif self.MEMORY_BACKEND == "file":
            config.update({
                "storage_dir": str(self.data_dir / "memory")
            })
        
        return config
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate configuration and return validation results.
        
        Returns:
            Dictionary containing validation results
        """
        errors = []
        warnings = []
        
        # Check required API keys
        if not self.OPENAI_API_KEY and self.DEFAULT_LLM_PROVIDER == "openai":
            errors.append("OPENAI_API_KEY is required when using OpenAI provider")
        
        if not self.ANTHROPIC_API_KEY and self.DEFAULT_LLM_PROVIDER == "anthropic":
            errors.append("ANTHROPIC_API_KEY is required when using Anthropic provider")
        
        if self.DEFAULT_LLM_PROVIDER == "azure_openai":
            if not self.AZURE_OPENAI_API_KEY:
                errors.append("AZURE_OPENAI_API_KEY is required for Azure OpenAI")
            if not self.AZURE_OPENAI_ENDPOINT:
                errors.append("AZURE_OPENAI_ENDPOINT is required for Azure OpenAI")
            if not self.AZURE_OPENAI_DEPLOYMENT:
                errors.append("AZURE_OPENAI_DEPLOYMENT is required for Azure OpenAI")
        
        # Check email configuration
        if self.EMAIL_ENABLED:
            if not self.EMAIL_USERNAME:
                errors.append("EMAIL_USERNAME is required when email is enabled")
            if not self.EMAIL_PASSWORD:
                errors.append("EMAIL_PASSWORD is required when email is enabled")
        
        # Check Redis configuration
        if self.MEMORY_BACKEND == "redis":
            if not self.REDIS_HOST:
                warnings.append("REDIS_HOST not specified, using default 'localhost'")
        
        # Check LangSmith configuration
        if self.LANGCHAIN_TRACING_V2 and not self.LANGSMITH_API_KEY:
            warnings.append("LANGSMITH_API_KEY not set but tracing is enabled")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "debug": self.DEBUG,
            "log_level": self.LOG_LEVEL,
            "api": {
                "host": self.API_HOST,
                "port": self.API_PORT,
                "workers": self.API_WORKERS
            },
            "llm": {
                "default_provider": self.DEFAULT_LLM_PROVIDER,
                "openai": self.get_llm_config("openai"),
                "anthropic": self.get_llm_config("anthropic"),
                "azure_openai": self.get_llm_config("azure_openai")
            },
            "email": self.get_email_config(),
            "monitoring": self.get_monitoring_config(),
            "memory": self.get_memory_config(),
            "langsmith": {
                "api_key": self.LANGSMITH_API_KEY,
                "project": self.LANGSMITH_PROJECT,
                "tracing_enabled": self.LANGCHAIN_TRACING_V2
            },
            "processing": {
                "max_concurrent_requests": self.MAX_CONCURRENT_REQUESTS,
                "request_timeout": self.REQUEST_TIMEOUT,
                "default_agent_timeout": self.DEFAULT_AGENT_TIMEOUT,
                "max_retries": self.MAX_RETRIES,
                "retry_delay": self.RETRY_DELAY
            }
        }