"""Agent registry for managing agent instances."""

from typing import Dict, Type, Optional
from agents.base_agent import BaseAgent


class AgentRegistrationError(Exception):
    """Exception raised when agent registration fails."""
    pass


class AgentNotFoundError(Exception):
    """Exception raised when requested agent is not found."""
    pass


class AgentRegistry:
    """Registry for managing agent instances."""
    
    def __init__(self):
        self._agents: Dict[str, Type[BaseAgent]] = {}
    
    def register(self, name: str, agent_class: Type[BaseAgent]):
        """Register an agent class."""
        if not issubclass(agent_class, BaseAgent):
            raise AgentRegistrationError(f"Agent {name} must inherit from BaseAgent")
        self._agents[name] = agent_class
    
    def get(self, name: str) -> Type[BaseAgent]:
        """Get an agent class by name."""
        if name not in self._agents:
            raise AgentNotFoundError(f"Agent {name} not found")
        return self._agents[name]
    
    def list_agents(self) -> list:
        """List all registered agent names."""
        return list(self._agents.keys())
    
    def unregister(self, name: str):
        """Unregister an agent."""
        if name in self._agents:
            del self._agents[name]


# Global registry instance
_global_registry = AgentRegistry()


def get_global_registry() -> AgentRegistry:
    """Get the global agent registry."""
    return _global_registry


def set_global_registry(registry: AgentRegistry):
    """Set the global agent registry."""
    global _global_registry
    _global_registry = registry