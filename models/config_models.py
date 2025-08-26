"""Configuration models for the AI Agent Framework."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30


@dataclass
class AgentConfig:
    """Configuration for individual agents."""
    name: str
    class_name: str
    llm_config: LLMConfig
    prompts: Dict[str, str]
    enabled: bool = True
    timeout: int = 60


@dataclass
class Condition:
    """Configuration for criteria conditions."""
    field: str
    operator: str
    value: Any
    case_sensitive: bool = True


@dataclass
class CriteriaConfig:
    """Configuration for criteria evaluation."""
    name: str
    conditions: List[Condition]
    logic: str = "AND"  # AND, OR


@dataclass
class WorkflowConfig:
    """Configuration for workflow execution."""
    name: str
    agents: List[AgentConfig]
    criteria: List[CriteriaConfig]
    timeout: int = 300
    retry_count: int = 3


@dataclass
class FrameworkConfig:
    """Main framework configuration."""
    workflows: List[WorkflowConfig]
    default_llm: LLMConfig
    logging_level: str = "INFO"
    monitoring_enabled: bool = True