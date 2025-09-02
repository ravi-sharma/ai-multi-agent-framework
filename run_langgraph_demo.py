#!/usr/bin/env python3
"""
Demo script to run and visualize LangGraph workflows.

This script demonstrates how to:
1. Set up LangSmith tracing for visualization
2. Run the multi-agent graph
3. View the workflow in LangGraph Studio
4. Debug workflow execution
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Set up LangSmith tracing BEFORE importing LangGraph components
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "ai-agent-framework-demo"

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from graphs.multiagent_graph import MultiAgentGraph
from agents.default_agent import DefaultAgent
from agents.sales_agent import SalesAgent
from models.data_models import AgentResult


def setup_langsmith_tracing():
    """Setup LangSmith tracing for visualization."""
    print("🔧 Setting up LangSmith tracing...")
    
    # Check if LangSmith API key is set
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("⚠️  LANGSMITH_API_KEY not set. Tracing will be disabled.")
        print("   To enable tracing:")
        print("   1. Sign up at https://smith.langchain.com/")
        print("   2. Get your API key")
        print("   3. Set: export LANGSMITH_API_KEY='your-key-here'")
        return False
    
    # Set up tracing environment
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "ai-agent-framework-demo"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    
    print(f"✅ LangSmith tracing enabled for project: ai-agent-framework-demo")
    return True


def create_sample_inputs() -> list[Dict[str, Any]]:
    """Create sample inputs for testing different routing scenarios."""
    return [
        {
            "name": "Sales Inquiry",
            "data": {
                "source": "email",
                "data": {
                    "email": {
                        "subject": "Interested in pricing for enterprise plan",
                        "sender": "cto@startup.com",
                        "recipient": "sales@company.com",
                        "body": "Hi, we're a growing startup and need pricing information for your enterprise plan. We have about 50 employees and need advanced features."
                    }
                }
            }
        },
        {
            "name": "General Support",
            "data": {
                "source": "email", 
                "data": {
                    "email": {
                        "subject": "How to reset my password",
                        "sender": "user@example.com",
                        "recipient": "support@company.com",
                        "body": "I forgot my password and can't log in. Can you help me reset it?"
                    }
                }
            }
        },
        {
            "name": "Product Demo Request",
            "data": {
                "source": "webhook",
                "data": {
                    "form_data": {
                        "name": "John Smith",
                        "email": "john@company.com",
                        "company": "TechCorp",
                        "message": "We'd like to schedule a demo of your product for our team of 25 developers."
                    }
                }
            }
        }
    ]


async def run_workflow_demo():
    """Run the multi-agent workflow demo."""
    print("\n🚀 AI Agent Framework - LangGraph Demo")
    print("=" * 60)
    
    # Setup tracing
    tracing_enabled = setup_langsmith_tracing()
    
    # Create agents
    print("\n📦 Creating agents...")
    agents = {
        "default_agent": DefaultAgent(),
        "sales_agent": SalesAgent()
    }
    print(f"✅ Created {len(agents)} agents: {list(agents.keys())}")
    
    # Create multi-agent graph
    print("\n🔗 Creating multi-agent graph...")
    graph = MultiAgentGraph(agents)
    print("✅ Multi-agent graph created and compiled")
    
    # Get sample inputs
    sample_inputs = create_sample_inputs()
    
    print(f"\n🧪 Running {len(sample_inputs)} test scenarios...")
    print("=" * 60)
    
    results = []
    
    for i, sample in enumerate(sample_inputs, 1):
        print(f"\n📋 Scenario {i}: {sample['name']}")
        print("-" * 40)
        
        try:
            # Execute workflow
            start_time = datetime.now()
            result = await graph.execute(sample['data'])
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Display results
            print(f"✅ Success: {result.get('success', False)}")
            print(f"🤖 Agent: {result.get('agent_name', 'unknown')}")
            print(f"⏱️  Execution time: {execution_time:.3f}s")
            
            if 'output' in result:
                output = result['output']
                if isinstance(output, dict):
                    for key, value in output.items():
                        if key in ['primary_intent', 'urgency_level', 'agent_type']:
                            print(f"📊 {key.replace('_', ' ').title()}: {value}")
            
            results.append({
                "scenario": sample['name'],
                "success": result.get('success', False),
                "agent": result.get('agent_name', 'unknown'),
                "execution_time": execution_time
            })
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results.append({
                "scenario": sample['name'],
                "success": False,
                "agent": "error",
                "execution_time": 0,
                "error": str(e)
            })
    
    # Summary
    print(f"\n📊 Execution Summary")
    print("=" * 60)
    successful = sum(1 for r in results if r['success'])
    total_time = sum(r['execution_time'] for r in results)
    
    print(f"Total scenarios: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"Total execution time: {total_time:.3f}s")
    print(f"Average execution time: {total_time/len(results):.3f}s")
    
    # Tracing information
    if tracing_enabled:
        print(f"\n🔍 Debugging Information")
        print("=" * 60)
        print("✅ All workflows have been traced in LangSmith")
        print("📊 View traces at: https://smith.langchain.com/")
        print("🎯 Project: ai-agent-framework-demo")
        print("\n🎨 To view workflows visually:")
        print("1. Download LangGraph Studio: ./setup_langgraph_studio.sh")
        print("2. Install and launch the desktop app")
        print("3. Connect with your LangSmith API key")
        print("4. Select project: ai-agent-framework-demo")
        print("5. Open: http://localhost:3005")
    else:
        print(f"\n⚠️  Tracing Disabled")
        print("=" * 60)
        print("To enable visual debugging:")
        print("1. Get LangSmith API key from https://smith.langchain.com/")
        print("2. Set: export LANGSMITH_API_KEY='your-key'")
        print("3. Re-run this script")
    
    return results


async def interactive_demo():
    """Run an interactive demo where users can input custom scenarios."""
    print("\n🎮 Interactive Demo Mode")
    print("=" * 60)
    print("Enter custom inputs to test the multi-agent workflow")
    print("Type 'quit' to exit")
    
    # Create agents and graph
    agents = {
        "default_agent": DefaultAgent(),
        "sales_agent": SalesAgent()
    }
    graph = MultiAgentGraph(agents)
    
    while True:
        print("\n" + "-" * 40)
        user_input = input("Enter your message (or 'quit'): ").strip()
        
        if user_input.lower() == 'quit':
            break
        
        if not user_input:
            continue
        
        # Create input data
        input_data = {
            "source": "interactive",
            "data": {
                "message": user_input,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            start_time = datetime.now()
            result = await graph.execute(input_data)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            print(f"\n📊 Result:")
            print(f"  Agent: {result.get('agent_name', 'unknown')}")
            print(f"  Success: {result.get('success', False)}")
            print(f"  Time: {execution_time:.3f}s")
            
            if 'output' in result and isinstance(result['output'], dict):
                for key, value in result['output'].items():
                    if key not in ['raw_output', 'metadata']:
                        print(f"  {key.replace('_', ' ').title()}: {value}")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")


def print_setup_instructions():
    """Print setup instructions for LangGraph Studio."""
    print("\n🎨 LangGraph Studio Setup")
    print("=" * 60)
    print("To visualize workflows in LangGraph Studio:")
    print("")
    print("1. Install LangGraph CLI:")
    print("   ./setup_langgraph_studio.sh")
    print("   # Or manually: pip install -U \"langgraph-cli[inmem]\"")
    print("")
    print("2. Start LangGraph development server:")
    print("   langgraph dev --port 3005")
    print("")
    print("3. Open in browser:")
    print("   http://localhost:3005")
    print("")
    print("4. Connect with LangSmith (optional):")
    print("   - Enter your LangSmith API key")
    print("   - Select project: ai-agent-framework-demo")
    print("")
    print("5. View your workflows:")
    print("   - See real-time execution")
    print("   - Debug step by step")
    print("   - Analyze performance")
    print("")
    print("📖 LangGraph Documentation: https://langchain-ai.github.io/langgraph/")


async def main():
    """Main demo function."""
    print("🤖 AI Agent Framework - LangGraph Visualization Demo")
    print("=" * 70)
    
    # Check if we're in the right directory
    if not os.path.exists("graphs/multiagent_graph.py"):
        print("❌ Error: Please run this script from the ai-agent project root directory")
        sys.exit(1)
    
    print("Choose demo mode:")
    print("1. Automated demo (run predefined scenarios)")
    print("2. Interactive demo (enter custom inputs)")
    print("3. Setup instructions only")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            await run_workflow_demo()
        elif choice == "2":
            await interactive_demo()
        elif choice == "3":
            print_setup_instructions()
        else:
            print("Invalid choice. Running automated demo...")
            await run_workflow_demo()
        
        print_setup_instructions()
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
