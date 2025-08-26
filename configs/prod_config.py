"""Production environment configuration."""

from .base_config import BaseConfig


class ProdConfig(BaseConfig):
    """Production environment configuration."""
    
    def __init__(self):
        """Initialize production configuration."""
        super().__init__()
    
    # Override base settings for production
    DEBUG = False
    LOG_LEVEL = "INFO"
    
    # Production API settings
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    API_WORKERS = 4  # More workers for production
    
    # Production LLM settings (use more capable models)
    OPENAI_MODEL = "gpt-4"
    OPENAI_MAX_TOKENS = 2000
    OPENAI_TEMPERATURE = 0.3
    
    ANTHROPIC_MODEL = "claude-3-sonnet-20240229"
    ANTHROPIC_MAX_TOKENS = 2000
    
    # Production email settings
    EMAIL_ENABLED = True
    EMAIL_POLLING_INTERVAL = 60  # Standard polling interval
    
    # Production monitoring
    MONITORING_ENABLED = True
    MONITORING_PORT = 9090
    HEALTH_CHECK_INTERVAL = 30
    
    # Production memory settings
    MEMORY_BACKEND = "redis"  # Use Redis for production persistence
    MEMORY_TTL = 7200  # 2 hours
    
    # Production processing settings
    MAX_CONCURRENT_REQUESTS = 20  # Higher for production load
    REQUEST_TIMEOUT = 300  # 5 minutes
    DEFAULT_AGENT_TIMEOUT = 180  # 3 minutes
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # Longer retry delay for stability
    
    # Production LangSmith settings
    LANGSMITH_PROJECT = "ai-agent-framework-prod"
    LANGCHAIN_TRACING_V2 = False  # Disable tracing in production for performance
    
    def get_agent_configs(self):
        """Get production-specific agent configurations."""
        return {
            "default_agent": {
                "enabled": True,
                "timeout": 120,
                "enable_llm_enhancement": True,
                "log_unmatched_requests": True,
                "response_template": "Thank you for contacting us. We have received your message and will respond within 24 hours."
            },
            "sales_agent": {
                "enabled": True,
                "timeout": 180,
                "enable_detailed_logging": False,  # Reduce logging in production
                "mock_external_apis": False,
                "enable_crm_integration": True,
                "enable_email_notifications": True
            }
        }
    
    def get_routing_config(self):
        """Get production-specific routing configuration."""
        return {
            "default_route": "default_agent",
            "enable_fallback": True,
            "log_routing_decisions": False,  # Reduce logging in production
            "criteria": [
                {
                    "name": "sales_inquiries",
                    "priority": 10,
                    "conditions": [
                        {
                            "field": "email.subject",
                            "operator": "contains",
                            "values": ["purchase", "buy", "quote", "pricing", "demo", "trial"]
                        }
                    ],
                    "agent": "sales_agent"
                },
                {
                    "name": "sales_body_keywords",
                    "priority": 8,
                    "conditions": [
                        {
                            "field": "email.body",
                            "operator": "contains",
                            "values": ["interested in", "want to buy", "need pricing", "schedule demo"]
                        }
                    ],
                    "agent": "sales_agent"
                },
                {
                    "name": "high_priority_domains",
                    "priority": 9,
                    "conditions": [
                        {
                            "field": "email.sender",
                            "operator": "domain_in",
                            "values": ["enterprise.com", "bigcorp.com", "fortune500.com"]
                        }
                    ],
                    "agent": "sales_agent"
                }
            ]
        }
    
    def get_security_config(self):
        """Get production security configuration."""
        return {
            "enable_rate_limiting": True,
            "rate_limit_requests_per_minute": 100,
            "enable_api_key_auth": True,
            "enable_cors": True,
            "allowed_origins": ["https://yourdomain.com"],
            "enable_request_logging": True,
            "log_sensitive_data": False,
            "enable_encryption_at_rest": True,
            "enable_ssl_verification": True
        }
    
    def get_performance_config(self):
        """Get production performance configuration."""
        return {
            "enable_caching": True,
            "cache_ttl": 3600,  # 1 hour
            "enable_connection_pooling": True,
            "max_pool_size": 20,
            "enable_request_batching": True,
            "batch_size": 10,
            "batch_timeout": 5.0,
            "enable_circuit_breaker": True,
            "circuit_breaker_failure_threshold": 5,
            "circuit_breaker_recovery_timeout": 60
        }
    
    def get_alerting_config(self):
        """Get production alerting configuration."""
        return {
            "enable_alerts": True,
            "alert_channels": ["email", "slack"],
            "email_recipients": ["ops@company.com", "dev@company.com"],
            "slack_webhook_url": "https://hooks.slack.com/services/...",
            "alert_thresholds": {
                "error_rate": 0.05,  # 5%
                "response_time_p95": 10.0,  # 10 seconds
                "memory_usage": 0.85,  # 85%
                "cpu_usage": 0.80,  # 80%
                "disk_usage": 0.90  # 90%
            }
        }
    
    def validate_config(self):
        """Validate production configuration."""
        validation = super().validate_config()
        
        # Add production-specific validations
        prod_errors = []
        prod_warnings = []
        
        # Check critical production settings
        if self.DEBUG:
            prod_errors.append("DEBUG should be False in production")
        
        if self.LOG_LEVEL == "DEBUG":
            prod_warnings.append("Consider using INFO or WARNING log level in production")
        
        if self.MEMORY_BACKEND == "memory":
            prod_warnings.append("Consider using Redis or file storage in production")
        
        if self.API_WORKERS < 2:
            prod_warnings.append("Consider using more API workers in production")
        
        if self.LANGCHAIN_TRACING_V2:
            prod_warnings.append("Consider disabling LangSmith tracing in production for performance")
        
        # Check security settings
        if not self.EMAIL_USE_SSL and self.EMAIL_ENABLED:
            prod_errors.append("SSL should be enabled for email in production")
        
        validation["errors"].extend(prod_errors)
        validation["warnings"].extend(prod_warnings)
        
        return validation