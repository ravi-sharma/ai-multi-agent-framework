"""FastAPI service for REST API interface."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TriggerRequest(BaseModel):
    """Request model for triggering agent processing."""
    source: str
    data: Dict[str, Any]
    agent_name: Optional[str] = None
    priority: Optional[int] = 5


class TriggerResponse(BaseModel):
    """Response model for trigger requests."""
    success: bool
    workflow_id: str
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str
    timestamp: str
    version: str
    components: Dict[str, str]


class APIService:
    """FastAPI service for the agent framework."""
    
    def __init__(self, framework_instance=None):
        """
        Initialize API service.
        
        Args:
            framework_instance: Instance of the main framework
        """
        self.framework = framework_instance
        self.app = FastAPI(
            title="AI Agent Framework API",
            description="REST API for the AI Agent Framework",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up API routes."""
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now().isoformat(),
                version="1.0.0",
                components={
                    "api": "healthy",
                    "framework": "healthy" if self.framework else "not_initialized"
                }
            )
        
        @self.app.post("/api/trigger", response_model=TriggerResponse)
        async def trigger_processing(request: TriggerRequest, background_tasks: BackgroundTasks):
            """Trigger agent processing."""
            try:
                if not self.framework:
                    raise HTTPException(status_code=503, detail="Framework not initialized")
                
                # Generate workflow ID
                workflow_id = f"api_{datetime.now().timestamp()}"
                
                # Prepare input data
                input_data = {
                    "source": request.source,
                    "data": request.data,
                    "workflow_id": workflow_id,
                    "priority": request.priority,
                    "requested_agent": request.agent_name
                }
                
                # Process request (this would integrate with your framework)
                # For now, return a mock response
                result = await self._process_request(input_data)
                
                return TriggerResponse(
                    success=True,
                    workflow_id=workflow_id,
                    message="Processing completed successfully",
                    result=result
                )
                
            except Exception as e:
                logger.error(f"API trigger processing failed: {e}")
                return TriggerResponse(
                    success=False,
                    workflow_id=workflow_id if 'workflow_id' in locals() else "unknown",
                    message="Processing failed",
                    error=str(e)
                )
        
        @self.app.get("/api/status/{workflow_id}")
        async def get_workflow_status(workflow_id: str):
            """Get workflow status."""
            try:
                if not self.framework:
                    raise HTTPException(status_code=503, detail="Framework not initialized")
                
                # This would integrate with your workflow status tracking
                status = await self._get_workflow_status(workflow_id)
                
                if not status:
                    raise HTTPException(status_code=404, detail="Workflow not found")
                
                return status
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting workflow status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/agents")
        async def list_agents():
            """List available agents."""
            try:
                if not self.framework:
                    raise HTTPException(status_code=503, detail="Framework not initialized")
                
                # This would integrate with your agent registry
                agents = await self._list_agents()
                
                return {
                    "agents": agents,
                    "count": len(agents),
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error listing agents: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/agents/{agent_name}/enable")
        async def enable_agent(agent_name: str):
            """Enable an agent."""
            try:
                if not self.framework:
                    raise HTTPException(status_code=503, detail="Framework not initialized")
                
                success = await self._enable_agent(agent_name)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Agent not found")
                
                return {
                    "success": True,
                    "message": f"Agent '{agent_name}' enabled",
                    "timestamp": datetime.now().isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error enabling agent: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/agents/{agent_name}/disable")
        async def disable_agent(agent_name: str):
            """Disable an agent."""
            try:
                if not self.framework:
                    raise HTTPException(status_code=503, detail="Framework not initialized")
                
                success = await self._disable_agent(agent_name)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Agent not found")
                
                return {
                    "success": True,
                    "message": f"Agent '{agent_name}' disabled",
                    "timestamp": datetime.now().isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error disabling agent: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _process_request(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process request through the framework.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Processing result
        """
        # This would integrate with your actual framework processing
        # For now, return a mock result
        return {
            "processed": True,
            "agent_used": "mock_agent",
            "processing_time": 0.5,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow status.
        
        Args:
            workflow_id: Workflow ID to check
            
        Returns:
            Workflow status or None if not found
        """
        # This would integrate with your workflow tracking
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "progress": 100,
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        }
    
    async def _list_agents(self) -> list:
        """
        List available agents.
        
        Returns:
            List of agent information
        """
        # This would integrate with your agent registry
        return [
            {
                "name": "default_agent",
                "type": "DefaultAgent",
                "enabled": True,
                "description": "Fallback agent for unmatched requests"
            },
            {
                "name": "sales_agent",
                "type": "SalesAgent", 
                "enabled": True,
                "description": "Specialized agent for sales inquiries"
            }
        ]
    
    async def _enable_agent(self, agent_name: str) -> bool:
        """
        Enable an agent.
        
        Args:
            agent_name: Name of agent to enable
            
        Returns:
            True if successful, False if agent not found
        """
        # This would integrate with your agent management
        logger.info(f"Enabling agent: {agent_name}")
        return True
    
    async def _disable_agent(self, agent_name: str) -> bool:
        """
        Disable an agent.
        
        Args:
            agent_name: Name of agent to disable
            
        Returns:
            True if successful, False if agent not found
        """
        # This would integrate with your agent management
        logger.info(f"Disabling agent: {agent_name}")
        return True
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self.app