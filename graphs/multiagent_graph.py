"""Multi-agent workflow orchestration using LangGraph with LangSmith tracing."""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.runnables import RunnableConfig

# Try to import LangSmith for tracing
try:
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    # Create a no-op decorator if LangSmith is not available
    def traceable(name=None):
        def decorator(func):
            return func
        return decorator
    LANGSMITH_AVAILABLE = False

logger = logging.getLogger(__name__)


class MultiAgentGraph:
    """
    Main orchestration graph that coordinates multiple agents.
    
    This graph handles the routing and coordination of requests between
    different specialized agents based on criteria and workflow requirements.
    """
    
    def __init__(self, agents: Dict[str, Any], routing_config: Dict[str, Any] = None):
        """
        Initialize the multi-agent graph.
        
        Args:
            agents: Dictionary of available agents
            routing_config: Configuration for routing logic
        """
        self.agents = agents
        self.routing_config = routing_config or {}
        self.workflow: Optional[CompiledStateGraph] = None
        self._setup_workflow()
    
    def _setup_workflow(self) -> None:
        """Set up the LangGraph workflow for multi-agent coordination."""
        # Create state graph
        workflow = StateGraph(dict)
        
        # Add workflow nodes
        workflow.add_node("route_request", self._route_request)
        workflow.add_node("process_with_agent", self._process_with_agent)
        workflow.add_node("validate_result", self._validate_result)
        workflow.add_node("finalize_response", self._finalize_response)
        
        # Define workflow edges
        workflow.add_edge("route_request", "process_with_agent")
        workflow.add_edge("process_with_agent", "validate_result")
        workflow.add_edge("validate_result", "finalize_response")
        workflow.add_edge("finalize_response", END)
        
        # Set entry point
        workflow.set_entry_point("route_request")
        
        # Compile workflow
        self.workflow = workflow.compile()
        logger.info("Multi-agent workflow compiled successfully")
    
    @traceable(name="multiagent_workflow")
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the multi-agent workflow.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Final processing result
        """
        if not self.workflow:
            raise RuntimeError("Workflow not initialized")
        
        # Create initial state
        initial_state = {
            "input_data": input_data,
            "selected_agent": None,
            "agent_result": None,
            "final_result": None,
            "errors": [],
            "metadata": {
                "start_time": datetime.now(),
                "workflow_id": f"multiagent_{datetime.now().timestamp()}"
            }
        }
        
        # Execute workflow
        final_state = await self.workflow.ainvoke(initial_state)
        
        return final_state.get("final_result", {})
    
    @traceable(name="route_request")
    async def _route_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route the request to the appropriate agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with selected agent
        """
        try:
            input_data = state["input_data"]
            
            # Simple routing logic - can be enhanced with criteria engine
            selected_agent = self._select_agent(input_data)
            
            state["selected_agent"] = selected_agent
            logger.info(f"Routed request to agent: {selected_agent}")
            
            return state
            
        except Exception as e:
            logger.error(f"Request routing failed: {e}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"Routing failed: {str(e)}")
            state["selected_agent"] = "default_agent"  # Fallback
            return state
    
    @traceable(name="process_with_agent")
    async def _process_with_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the request with the selected agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with agent result
        """
        try:
            selected_agent = state["selected_agent"]
            input_data = state["input_data"]
            
            if selected_agent not in self.agents:
                raise ValueError(f"Agent '{selected_agent}' not found")
            
            agent = self.agents[selected_agent]
            result = await agent.process(input_data)
            
            state["agent_result"] = result
            logger.info(f"Agent '{selected_agent}' processed request successfully")
            
            return state
            
        except Exception as e:
            logger.error(f"Agent processing failed: {e}")
            state["errors"].append(f"Agent processing failed: {str(e)}")
            return state
    
    async def _validate_result(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the agent result.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with validation status
        """
        try:
            agent_result = state.get("agent_result")
            
            if not agent_result:
                raise ValueError("No agent result to validate")
            
            # Basic validation - can be enhanced
            is_valid = hasattr(agent_result, 'success') and agent_result.success
            
            if not is_valid:
                state["errors"].append("Agent result validation failed")
            
            logger.info(f"Result validation: {'passed' if is_valid else 'failed'}")
            
            return state
            
        except Exception as e:
            logger.error(f"Result validation failed: {e}")
            state["errors"].append(f"Validation failed: {str(e)}")
            return state
    
    async def _finalize_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finalize the response.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with final result
        """
        try:
            agent_result = state.get("agent_result")
            errors = state.get("errors", [])
            metadata = state.get("metadata", {})
            
            # Calculate execution time
            start_time = metadata.get("start_time", datetime.now())
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create final result
            final_result = {
                "success": len(errors) == 0 and agent_result and agent_result.success,
                "agent_name": state.get("selected_agent"),
                "result": agent_result.output if agent_result else {},
                "errors": errors,
                "execution_time": execution_time,
                "workflow_id": metadata.get("workflow_id"),
                "timestamp": datetime.now().isoformat()
            }
            
            state["final_result"] = final_result
            logger.info(f"Finalized response with success: {final_result['success']}")
            
            return state
            
        except Exception as e:
            logger.error(f"Response finalization failed: {e}")
            state["errors"].append(f"Finalization failed: {str(e)}")
            
            # Create error result
            final_result = {
                "success": False,
                "agent_name": state.get("selected_agent"),
                "result": {},
                "errors": state.get("errors", []),
                "execution_time": 0.0,
                "workflow_id": state.get("metadata", {}).get("workflow_id"),
                "timestamp": datetime.now().isoformat()
            }
            
            state["final_result"] = final_result
            return state
    
    def _select_agent(self, input_data: Dict[str, Any]) -> str:
        """
        Select the appropriate agent based on input data.
        
        Args:
            input_data: Input data to analyze
            
        Returns:
            Name of the selected agent
        """
        # Simple routing logic - can be enhanced with criteria engine
        source = input_data.get("source", "unknown")
        
        # Check for email data
        if "data" in input_data and "email" in input_data["data"]:
            email_data = input_data["data"]["email"]
            subject = email_data.get("subject", "").lower()
            body = email_data.get("body", "").lower()
            
            # Sales keywords
            sales_keywords = ["buy", "purchase", "price", "quote", "sales", "demo", "pricing", "want"]
            if any(keyword in subject or keyword in body for keyword in sales_keywords):
                return "sales_agent"
        
        # Default fallback
        return "default_agent"
    
    def add_agent(self, name: str, agent: Any) -> None:
        """
        Add an agent to the graph.
        
        Args:
            name: Agent name
            agent: Agent instance
        """
        self.agents[name] = agent
        logger.info(f"Added agent '{name}' to multi-agent graph")
    
    def remove_agent(self, name: str) -> None:
        """
        Remove an agent from the graph.
        
        Args:
            name: Agent name to remove
        """
        if name in self.agents:
            del self.agents[name]
            logger.info(f"Removed agent '{name}' from multi-agent graph")
    
    def get_available_agents(self) -> List[str]:
        """
        Get list of available agent names.
        
        Returns:
            List of agent names
        """
        return list(self.agents.keys())


def create_graph(config: RunnableConfig):
    """
    Factory function to create a compiled LangGraph workflow for LangGraph CLI.
    
    This function is called by LangGraph CLI to create the graph instance.
    It takes a RunnableConfig as required by the CLI.
    
    Args:
        config: RunnableConfig from LangGraph CLI
        
    Returns:
        Compiled LangGraph workflow
    """
    # Import agents here to avoid circular imports
    from agents.sales_agent import SalesAgent
    from agents.default_agent import DefaultAgent
    
    # Create default agents
    agents = {
        "sales_agent": SalesAgent(),
        "default_agent": DefaultAgent()
    }
    
    # Create the graph and return the compiled workflow
    graph = MultiAgentGraph(agents)
    return graph.workflow