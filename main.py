"""Main entry point for the AI Agent Framework."""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Explicitly set LangSmith tracing
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGSMITH_PROJECT'] = 'ai-agent-framework'

# Attempt to set API key if available in .env
from dotenv import load_dotenv
load_dotenv()

from utils.logger import setup_logger
from configs.base_config import BaseConfig
from configs.dev_config import DevConfig
from configs.prod_config import ProdConfig
from services.api_service import APIService
from services.cli_service import CLIService
from agents.sales_agent import SalesAgent
from agents.default_agent import DefaultAgent
from graphs.multiagent_graph import MultiAgentGraph


class AgentFramework:
    """Main AI Agent Framework class."""
    
    def __init__(self, config=None):
        """
        Initialize the framework.
        
        Args:
            config: Configuration instance
        """
        self.config = config or BaseConfig()
        self.logger = setup_logger(
            name="ai_agent_framework",
            level=self.config.LOG_LEVEL
        )
        
        # Initialize services
        self.api_service = None
        self.cli_service = None
        
        # Initialize agents
        self.agents = {}
        self._initialize_agents()
        
        # Initialize multi-agent graph
        self.graph = None
        self._initialize_graph()
        
        self.logger.info("AI Agent Framework initialized")
    
    async def start_api_server(self, host: str = None, port: int = None):
        """
        Start the API server.
        
        Args:
            host: Host to bind to (defaults to config)
            port: Port to bind to (defaults to config)
        """
        try:
            import uvicorn
            
            self.api_service = APIService(framework_instance=self)
            app = self.api_service.get_app()
            
            host = host or self.config.API_HOST
            port = port or self.config.API_PORT
            
            self.logger.info(f"Starting API server on {host}:{port}")
            
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                workers=self.config.API_WORKERS,
                log_level=self.config.LOG_LEVEL.lower()
            )
            
            server = uvicorn.Server(config)
            await server.serve()
            
        except ImportError:
            self.logger.error("uvicorn not installed. Install with: pip install uvicorn")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Failed to start API server: {e}")
            sys.exit(1)
    
    def get_cli_service(self) -> CLIService:
        """Get CLI service instance."""
        if not self.cli_service:
            self.cli_service = CLIService(framework_instance=self)
        return self.cli_service
    
    def _initialize_agents(self):
        """Initialize available agents."""
        try:
            self.agents = {
                "sales_agent": SalesAgent(),
                "default_agent": DefaultAgent()
            }
            self.logger.info(f"Initialized {len(self.agents)} agents: {list(self.agents.keys())}")
        except Exception as e:
            self.logger.error(f"Failed to initialize agents: {e}")
            self.agents = {}
    
    def _initialize_graph(self):
        """Initialize the multi-agent graph."""
        try:
            if self.agents:
                self.graph = MultiAgentGraph(self.agents)
                self.logger.info("Multi-agent graph initialized successfully")
            else:
                self.logger.warning("No agents available for graph initialization")
        except Exception as e:
            self.logger.error(f"Failed to initialize multi-agent graph: {e}")
            self.graph = None

    async def process(self, input_data: dict) -> dict:
        """
        Process input data through the framework.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Processing result
        """
        try:
            self.logger.info(f"Processing request from source: {input_data.get('source', 'unknown')}")
            
            if self.graph:
                # Use the multi-agent graph for processing
                result = await self.graph.execute(input_data)
                self.logger.info(f"Request processed successfully by {result.get('agent_name', 'unknown')}")
                return result
            else:
                # Fallback to direct agent processing
                agent_name = input_data.get('requested_agent', 'default_agent')
                if agent_name in self.agents:
                    agent = self.agents[agent_name]
                    agent_result = await agent.process(input_data)
                    
                    return {
                        "success": agent_result.success,
                        "agent_name": agent_result.agent_name,
                        "result": agent_result.output,
                        "execution_time": agent_result.execution_time,
                        "errors": [agent_result.error_message] if agent_result.error_message else [],
                        "notes": agent_result.notes or []
                    }
                else:
                    raise ValueError(f"Agent '{agent_name}' not found")
                    
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            return {
                "success": False,
                "agent_name": "error",
                "result": {},
                "execution_time": 0.0,
                "errors": [str(e)]
            }
    
    async def list_agents(self) -> list:
        """
        List available agents.
        
        Returns:
            List of agent information
        """
        try:
            agents_info = []
            for name, agent in self.agents.items():
                agent_info = {
                    "name": name,
                    "type": agent.__class__.__name__,
                    "enabled": True,
                    "description": getattr(agent, '__doc__', 'No description available'),
                    "capabilities": getattr(agent, 'get_required_llm_capabilities', lambda: [])()
                }
                agents_info.append(agent_info)
            
            self.logger.info(f"Listed {len(agents_info)} available agents")
            return agents_info
            
        except Exception as e:
            self.logger.error(f"Failed to list agents: {e}")
            return []
    
    async def get_agent_info(self, agent_name: str) -> dict:
        """
        Get detailed information about a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent information dictionary
        """
        try:
            if agent_name not in self.agents:
                return None
            
            agent = self.agents[agent_name]
            
            agent_info = {
                "name": agent_name,
                "type": agent.__class__.__name__,
                "enabled": True,
                "description": getattr(agent, '__doc__', 'No description available'),
                "capabilities": getattr(agent, 'get_required_llm_capabilities', lambda: [])(),
                "workflow_config": getattr(agent, 'get_workflow_config', lambda: {})(),
                "config": getattr(agent, 'config', {})
            }
            
            self.logger.info(f"Retrieved info for agent: {agent_name}")
            return agent_info
            
        except Exception as e:
            self.logger.error(f"Failed to get agent info for {agent_name}: {e}")
            return None

    async def process_email(self, email_file_path: str, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Process an email file.
        
        Args:
            email_file_path: Path to the email file
            agent_name: Optional specific agent to use
            
        Returns:
            Processing result
        """
        try:
            # Read email file
            with open(email_file_path, 'r') as f:
                email_data = json.load(f)
            
            # Add source information
            email_data['source'] = 'email'
            
            # Optional: Override agent selection
            if agent_name:
                email_data['preferred_agent'] = agent_name
            
            # Execute workflow
            result = await self.graph.execute(email_data)
            
            # Prepare response
            return {
                'success': len(result.get('errors', [])) == 0,
                'email_file': email_file_path,
                'email_subject': email_data.get('data', {}).get('email', {}).get('subject', ''),
                'email_sender': email_data.get('data', {}).get('email', {}).get('sender', ''),
                'agent_used': result.get('agent', 'error'),
                'result': result,
                'processed_at': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Email processing error: {e}")
            return {
                'success': False,
                'email_file': email_file_path,
                'email_subject': '',
                'email_sender': '',
                'agent_used': 'error',
                'result': {
                    'success': False,
                    'agent_name': 'error',
                    'result': {},
                    'execution_time': 0.0,
                    'errors': [str(e)]
                },
                'processed_at': datetime.now().isoformat()
            }


async def run_cli_command(args, framework: AgentFramework):
    """Run CLI command."""
    cli = framework.get_cli_service()
    
    if args.command == "process-file":
        result = await cli.process_file(args.file_path, args.agent)
        print(f"File processing result: {result}")
    
    elif args.command == "process-text":
        result = await cli.process_text(args.text, args.source or "cli", args.agent)
        print(f"Text processing result: {result}")
    
    elif args.command == "list-agents":
        result = await cli.list_agents()
        print(f"Available agents: {result}")
    
    elif args.command == "agent-info":
        result = await cli.get_agent_info(args.agent_name)
        print(f"Agent info: {result}")
    
    elif args.command == "test-agent":
        result = await cli.test_agent(args.agent_name)
        print(f"Agent test result: {result}")
    
    elif args.command == "validate-config":
        result = await cli.validate_config(args.config_path)
        print(f"Config validation result: {result}")
    
    elif args.command == "process-email":
        result = await cli.process_email(args.email_file, args.agent)
        print(f"Email processing result: {result}")
    
    elif args.command == "process-webhook":
        import json
        try:
            webhook_data = json.loads(args.data)
            result = await cli.process_webhook(webhook_data, args.agent)
            print(f"Webhook processing result: {result}")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON data: {e}")
    
    else:
        print(f"Unknown command: {args.command}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI Agent Framework")
    parser.add_argument("--config", choices=["dev", "prod", "base"], default="base",
                       help="Configuration environment")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Override log level")
    
    subparsers = parser.add_subparsers(dest="mode", help="Operation mode")
    
    # API server mode
    api_parser = subparsers.add_parser("api", help="Start API server")
    api_parser.add_argument("--host", help="Host to bind to")
    api_parser.add_argument("--port", type=int, help="Port to bind to")
    
    # CLI mode
    cli_parser = subparsers.add_parser("cli", help="Run CLI commands")
    cli_subparsers = cli_parser.add_subparsers(dest="command", help="CLI commands")
    
    # CLI subcommands
    process_file_parser = cli_subparsers.add_parser("process-file", help="Process a file")
    process_file_parser.add_argument("file_path", help="Path to file to process")
    process_file_parser.add_argument("--agent", help="Specific agent to use")
    
    process_text_parser = cli_subparsers.add_parser("process-text", help="Process text input")
    process_text_parser.add_argument("text", help="Text to process")
    process_text_parser.add_argument("--source", help="Source identifier")
    process_text_parser.add_argument("--agent", help="Specific agent to use")
    
    cli_subparsers.add_parser("list-agents", help="List available agents")
    
    agent_info_parser = cli_subparsers.add_parser("agent-info", help="Get agent information")
    agent_info_parser.add_argument("agent_name", help="Name of the agent")
    
    test_agent_parser = cli_subparsers.add_parser("test-agent", help="Test an agent")
    test_agent_parser.add_argument("agent_name", help="Name of the agent to test")
    
    validate_config_parser = cli_subparsers.add_parser("validate-config", help="Validate configuration")
    validate_config_parser.add_argument("config_path", help="Path to configuration file")
    
    # Email processing command
    process_email_parser = cli_subparsers.add_parser("process-email", help="Process email file (supports .eml and .json)")
    process_email_parser.add_argument("email_file", help="Path to email file (.eml or .json format)")
    process_email_parser.add_argument("--agent", help="Specific agent to use")
    
    # Webhook processing command
    process_webhook_parser = cli_subparsers.add_parser("process-webhook", help="Process webhook data")
    process_webhook_parser.add_argument("--data", required=True, help="JSON webhook data")
    process_webhook_parser.add_argument("--agent", help="Specific agent to use")
    
    args = parser.parse_args()
    
    # Select configuration
    if args.config == "dev":
        config = DevConfig()
    elif args.config == "prod":
        config = ProdConfig()
    else:
        config = BaseConfig()
    
    # Override log level if specified
    if args.log_level:
        config.LOG_LEVEL = args.log_level
    
    # Initialize framework
    framework = AgentFramework(config)
    
    # Validate configuration
    validation = config.validate_config()
    if not validation["valid"]:
        framework.logger.error("Configuration validation failed:")
        for error in validation["errors"]:
            framework.logger.error(f"  - {error}")
        sys.exit(1)
    
    if validation["warnings"]:
        framework.logger.warning("Configuration warnings:")
        for warning in validation["warnings"]:
            framework.logger.warning(f"  - {warning}")
    
    # Run based on mode
    if args.mode == "api":
        asyncio.run(framework.start_api_server(args.host, args.port))
    elif args.mode == "cli":
        if not args.command:
            cli_parser.print_help()
            sys.exit(1)
        asyncio.run(run_cli_command(args, framework))
    else:
        # Default: show help
        parser.print_help()


if __name__ == "__main__":
    main()