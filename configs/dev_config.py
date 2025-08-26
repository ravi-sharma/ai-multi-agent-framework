"""Development environment configuration."""

from .base_config import BaseConfig


class DevConfig(BaseConfig):
    """Development environment configuration."""
    
    def __init__(self):
        """Initialize development configuration."""
        super().__init__()
    
    # Override base settings for development
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    
    # Development API settings
    API_HOST = "127.0.0.1"
    API_PORT = 8000
    API_WORKERS = 1
    
    # Development LLM settings (use cheaper/faster models)
    OPENAI_MODEL = "gpt-3.5-turbo"
    OPENAI_MAX_TOKENS = 1000
    OPENAI_TEMPERATURE = 0.5
    
    ANTHROPIC_MODEL = "claude-3-haiku-20240307"
    ANTHROPIC_MAX_TOKENS = 1000
    
    # Development email settings (disabled by default)
    EMAIL_ENABLED = False
    EMAIL_POLLING_INTERVAL = 30  # More frequent polling for testing
    
    # Development monitoring
    MONITORING_ENABLED = True
    MONITORING_PORT = 9091  # Different port to avoid conflicts
    HEALTH_CHECK_INTERVAL = 10  # More frequent health checks
    
    # Development memory settings
    MEMORY_BACKEND = "memory"  # Use in-memory for faster development
    MEMORY_TTL = 1800  # 30 minutes (shorter for development)
    
    # Development processing settings
    MAX_CONCURRENT_REQUESTS = 5  # Lower for development
    REQUEST_TIMEOUT = 120  # Shorter timeout for development
    DEFAULT_AGENT_TIMEOUT = 60  # Shorter agent timeout
    MAX_RETRIES = 2  # Fewer retries for faster feedback
    RETRY_DELAY = 0.5  # Shorter retry delay
    
    # Development-specific LangSmith settings
    LANGSMITH_PROJECT = "ai-agent-framework-dev"
    LANGCHAIN_TRACING_V2 = True  # Enable tracing in development
    
    def get_agent_configs(self):
        """Get development-specific agent configurations."""
        return {
            "default_agent": {
                "enabled": True,
                "timeout": 30,
                "enable_llm_enhancement": True,
                "log_unmatched_requests": True
            },
            "sales_agent": {
                "enabled": True,
                "timeout": 60,
                "enable_detailed_logging": True,
                "mock_external_apis": True  # Mock external APIs in development
            }
        }
    
    def get_routing_config(self):
        """Get development-specific routing configuration."""
        return {
            "default_route": "default_agent",
            "enable_fallback": True,
            "log_routing_decisions": True,
            "criteria": [
                {
                    "name": "sales_emails_dev",
                    "priority": 9,
                    "conditions": [
                        {
                            "field": "email.subject",
                            "operator": "contains",
                            "values": ["test", "demo", "price", "buy"]
                        }
                    ],
                    "agent": "sales_agent"
                }
            ]
        }
    
    def validate_config(self):
        """Validate development configuration."""
        validation = super().validate_config()
        
        # Add development-specific validations
        dev_warnings = []
        
        if not self.LANGCHAIN_TRACING_V2:
            dev_warnings.append("Consider enabling LangSmith tracing in development")
        
        if self.MEMORY_BACKEND != "memory":
            dev_warnings.append("Consider using in-memory storage for faster development")
        
        validation["warnings"].extend(dev_warnings)
        
        return validation