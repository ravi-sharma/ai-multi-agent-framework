"""Multi-agent workflow orchestration using LangGraph with enhanced tracing."""

import logging
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Explicit imports with error handling
try:
    from langgraph.graph import StateGraph, END
    from typing_extensions import TypedDict
    from langchain_core.runnables import RunnableConfig
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you have installed langgraph and langchain-core")
    sys.exit(1)

# LangSmith tracing
try:
    from langsmith import traceable, Client
    
    # Configure LangSmith client
    client = Client()
    LANGSMITH_AVAILABLE = True
except ImportError:
    # Create no-op decorators if LangSmith is not available
    def traceable(name=None):
        def decorator(func):
            return func
        return decorator
    LANGSMITH_AVAILABLE = False

logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    """
    Represents the state of the multi-agent workflow.
    """
    input_data: Dict[str, Any]
    selected_agent: Optional[str]
    agent_result: Optional[Any]
    final_result: Optional[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]

class MultiAgentGraph:
    """
    Orchestrates multi-agent workflow using LangGraph.
    
    Manages routing, processing, and validation of requests 
    across different agents.
    """
    def __init__(self, agents: Dict[str, Any]):
        """
        Initialize the multi-agent workflow graph.
        
        Args:
            agents: Dictionary of available agents
        """
        self.agents = agents
        self.workflow = None
        self._build_graph()
    
    def _build_graph(self):
        """
        Construct the workflow graph with nodes and edges.
        """
        # Create a state graph
        graph = StateGraph(WorkflowState)
        
        # Add nodes for each workflow stage
        graph.add_node("start", self._start_workflow)
        graph.add_node("route_request", self._route_request)
        graph.add_node("process_with_agent", self._process_with_agent)
        graph.add_node("validate_result", self._validate_result)
        graph.add_node("finalize_response", self._finalize_response)
        graph.add_node("error_handler", self._error_handler)
        
        # Define edges
        graph.set_entry_point("start")
        graph.add_edge("start", "route_request")
        graph.add_edge("route_request", "process_with_agent")
        graph.add_edge("process_with_agent", "validate_result")
        
        # Conditional edges for result validation
        graph.add_conditional_edges(
            "validate_result",
            lambda state: "finalize_response" if state["agent_result"] and getattr(state["agent_result"], 'success', False) else "error_handler"
        )
        
        graph.add_edge("finalize_response", END)
        graph.add_edge("error_handler", END)
        
        # Compile the graph
        self.workflow = graph.compile()
    
    @traceable(name="start_workflow")
    def _start_workflow(self, state: WorkflowState) -> WorkflowState:
        """
        Initialize workflow metadata and prepare for routing.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with initialization metadata
        """
        state["metadata"]["start_time"] = datetime.now()
        state["metadata"]["workflow_id"] = f"workflow_{datetime.now().timestamp()}"
        
        # Log workflow start
        logger.info(f"Starting workflow: {state['metadata']['workflow_id']}")
        
        return state
    
    @traceable(name="route_request")
    def _route_request(self, state: WorkflowState) -> WorkflowState:
        """
        Route the request to the appropriate agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with selected agent
        """
        try:
            # Extract input data from state
            input_data = state["input_data"]
            
            # Default to default agent
            selected_agent = 'default_agent'
            
            # Determine routing based on input type
            if input_data.get('source') == 'email':
                email_data = input_data.get('data', {}).get('email', {})
                subject = email_data.get('subject', '').lower()
                body = email_data.get('body', '').lower()
                
                # Routing logic
                if any(keyword in subject or keyword in body for keyword in ['sales', 'pricing', 'enterprise', 'plan']):
                    selected_agent = 'sales_agent'
                elif any(keyword in subject or keyword in body for keyword in ['support', 'help', 'issue']):
                    selected_agent = 'default_agent'
            
            # Update state with selected agent
            state["selected_agent"] = selected_agent
            
            # Log routing decision
            logger.info(f"Routed request to agent: {selected_agent}")
            
            return state
        except Exception as e:
            logger.error(f"Error in routing request: {e}")
            state["errors"].append(str(e))
            return state
    
    @traceable(name="process_with_agent")
    async def _process_with_agent(self, state: WorkflowState) -> WorkflowState:
        """
        Process the request with the selected agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with agent result
        """
        try:
            # Ensure selected_agent is set
            if not state["selected_agent"]:
                state["selected_agent"] = 'default_agent'
            
            # Validate agent exists
            if state["selected_agent"] not in self.agents:
                raise ValueError(f"Agent '{state['selected_agent']}' not found")
            
            # Get the agent
            agent = self.agents[state["selected_agent"]]
            
            # Process with the agent
            result = await agent.process(state["input_data"])
            
            # Log processing result
            logger.info(f"Agent {state['selected_agent']} processed request successfully")
            
            # Update state with agent result
            state["agent_result"] = result
            return state
        except Exception as e:
            logger.error(f"Error processing with agent {state.get('selected_agent', 'unknown')}: {e}")
            state["errors"].append(str(e))
            state["agent_result"] = None
            return state
    
    @traceable(name="validate_result")
    def _validate_result(self, state: WorkflowState) -> WorkflowState:
        """
        Validate the agent's processing result.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with validation result
        """
        try:
            agent_result = state["agent_result"]
            if not agent_result or not getattr(agent_result, 'success', False):
                state["errors"].append("Agent processing failed")
                logger.warning("Result validation failed")
            else:
                logger.info("Result validation passed")
            
            return state
        except Exception as e:
            logger.error(f"Error validating result: {e}")
            state["errors"].append(str(e))
            return state
    
    @traceable(name="finalize_response")
    def _finalize_response(self, state: WorkflowState) -> WorkflowState:
        """
        Compile final workflow response.
        
        Args:
            state: Current workflow state
            
        Returns:
            Final workflow state with processed result
        """
        try:
            agent_result = state["agent_result"]
            state["final_result"] = {
                'agent': state["selected_agent"],
                'output': getattr(agent_result, 'output', {}) if agent_result else {},
                'metadata': state["metadata"],
                'errors': state["errors"]
            }
            
            # Log finalization details
            logger.info(f"Finalized response for workflow {state['metadata'].get('workflow_id')}")
            
            return state
        except Exception as e:
            logger.error(f"Error finalizing response: {e}")
            state["errors"].append(str(e))
            return state
    
    @traceable(name="error_handler")
    def _error_handler(self, state: WorkflowState) -> WorkflowState:
        """
        Handle workflow errors.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with error details
        """
        logger.error(f"Workflow errors: {state['errors']}")
        return state
    
    @traceable(name="multiagent_workflow")
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the multi-agent workflow using LangGraph.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Final processing result
        """
        if not self.workflow:
            raise RuntimeError("Workflow not initialized")
        
        # Create initial state
        initial_state: WorkflowState = {
            "input_data": input_data,
            "selected_agent": None,
            "agent_result": None,
            "final_result": None,
            "errors": [],
            "metadata": {
                "start_time": datetime.now(),
                "workflow_id": f"multiagent_{datetime.now().timestamp()}",
            }
        }
        
        # Execute the workflow using LangGraph
        try:
            # Use the compiled workflow with proper tracing
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Ensure final result is set
            if not final_state.get("final_result"):
                agent_result = final_state.get("agent_result")
                final_state["final_result"] = {
                    'agent': final_state.get("selected_agent") or 'error',
                    'output': getattr(agent_result, 'output', {}) if agent_result else {},
                    'metadata': final_state.get("metadata", {}),
                    'errors': final_state.get("errors", [])
                }
            
            return final_state["final_result"]
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                'agent': 'error_handler',
                'output': {},
                'metadata': initial_state["metadata"],
                'errors': [str(e)]
            }

def create_graph():
    """
    Create and return the compiled multi-agent workflow graph for LangGraph API.
    
    Returns:
        Compiled StateGraph for LangGraph API usage
    """
    # Import agents here to avoid circular imports
    import os
    
    # Set default environment variables for LangGraph dev server
    os.environ.setdefault('OPENAI_API_KEY', 'sk-test-key')
    os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key')
    
    from agents.sales_agent import SalesAgent
    from agents.default_agent import DefaultAgent
    from configs.base_config import BaseConfig
    
    # Initialize configuration and agents
    config = BaseConfig()
    agents = {
        'sales_agent': SalesAgent(config),
        'default_agent': DefaultAgent(config)
    }
    
    # Create the multi-agent graph
    graph_instance = MultiAgentGraph(agents)
    
    # Return the compiled workflow
    return graph_instance.workflow

# Export both the class and the create_graph function
__all__ = ['MultiAgentGraph', 'create_graph']