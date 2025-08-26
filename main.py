"""Main entry point for the AI Agent Framework."""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import setup_logger
from configs.base_config import BaseConfig
from configs.dev_config import DevConfig
from configs.prod_config import ProdConfig
from services.api_service import APIService
from services.cli_service import CLIService


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
    
    async def process(self, input_data: dict) -> dict:
        """
        Process input data through the framework.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Processing result
        """
        # This is a placeholder - would integrate with actual framework logic
        self.logger.info(f"Processing request from source: {input_data.get('source', 'unknown')}")
        
        return {
            "success": True,
            "agent_name": "mock_agent",
            "result": {"message": "Processing completed"},
            "execution_time": 0.1
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