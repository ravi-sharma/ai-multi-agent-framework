"""Example demonstrating the SalesAgent functionality with LangGraph workflow."""

import asyncio
from datetime import datetime
from typing import Dict, Any

from agents.sales_agent import SalesAgent
from utils.llm_provider import LLMManager
from models.data_models import AgentResult


async def main():
    """Demonstrate SalesAgent functionality."""
    print("=== Sales Agent with LangGraph Workflow Example ===\n")
    
    # Create sales agent without LLM for basic functionality
    sales_agent = SalesAgent(
        name="demo_sales_agent",
        config={"demo_mode": True}
    )
    
    print(f"Created sales agent: {sales_agent.name}")
    print(f"Required LLM capabilities: {sales_agent.get_required_llm_capabilities()}")
    print(f"Workflow steps: {sales_agent.get_workflow_config().workflow_steps}")
    print()
    
    # Test cases with different types of sales inquiries
    test_cases = [
        {
            "name": "High-Priority Purchase Inquiry",
            "data": {
                "source": "email",
                "email": {
                    "subject": "URGENT: Need to purchase enterprise solution immediately",
                    "sender": "ceo@bigcorp.com",
                    "recipient": "sales@company.com",
                    "body": "Hi, I'm the CEO of BigCorp and we need to purchase your enterprise solution immediately for our upcoming project. We have a budget of $100k and need this deployed within 2 weeks. Please contact me ASAP.",
                    "headers": {"Message-ID": "urgent001"},
                    "timestamp": datetime.now().isoformat()
                }
            }
        },
        {
            "name": "Pricing Request",
            "data": {
                "source": "email",
                "email": {
                    "subject": "Pricing information for premium package",
                    "sender": "procurement@techstartup.com",
                    "recipient": "sales@company.com",
                    "body": "Hello, we are a growing tech startup with 50 employees. We're interested in your premium package and would like to get pricing information. We're comparing different solutions and need to make a decision by next month.",
                    "headers": {"Message-ID": "pricing001"}
                }
            }
        },
        {
            "name": "Demo Request",
            "data": {
                "source": "email",
                "email": {
                    "subject": "Request for product demonstration",
                    "sender": "manager@consulting.com",
                    "recipient": "sales@company.com",
                    "body": "Hi, I'm a project manager at a consulting firm. We're evaluating different tools for our client projects and would like to schedule a demo of your platform. We're particularly interested in the reporting and analytics features.",
                    "headers": {"Message-ID": "demo001"}
                }
            }
        },
        {
            "name": "General Information Request",
            "data": {
                "source": "email",
                "email": {
                    "subject": "Questions about your services",
                    "sender": "info@smallbiz.com",
                    "recipient": "sales@company.com",
                    "body": "Hello, I represent a small business and I have some questions about your services. Can you provide more information about what you offer and how it might help our business?",
                    "headers": {"Message-ID": "info001"}
                }
            }
        }
    ]
    
    # Process each test case
    for i, test_case in enumerate(test_cases, 1):
        print(f"--- Test Case {i}: {test_case['name']} ---")
        
        # Validate input first
        is_valid = sales_agent.validate_input(test_case['data'])
        print(f"Input validation: {'✓ Valid' if is_valid else '✗ Invalid'}")
        
        if not is_valid:
            print("Skipping invalid input\n")
            continue
        
        # Process the email
        start_time = datetime.now()
        result = await sales_agent.process(test_case['data'])
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Display results
        print(f"Processing result:")
        print(f"  - Success: {'✓' if result.success else '✗'}")
        print(f"  - Processing time: {processing_time:.2f}s")
        print(f"  - Agent execution time: {result.execution_time:.2f}s")
        
        if result.success:
            output = result.output
            print(f"  - Customer: {output.get('customer_email', 'Unknown')}")
            print(f"  - Domain: {output.get('customer_domain', 'Unknown')}")
            print(f"  - Primary intent: {output.get('primary_intent', 'Unknown')}")
            print(f"  - Urgency level: {output.get('urgency_level', 'Unknown')}")
            print(f"  - Requires human review: {'Yes' if output.get('requires_human_review') else 'No'}")
            
            # Display sales notes
            sales_notes = output.get('sales_notes', {})
            if sales_notes:
                print(f"  - Customer problem: {sales_notes.get('customer_problem', 'N/A')[:100]}...")
                print(f"  - Proposed solution: {sales_notes.get('proposed_solution', 'N/A')[:100]}...")
                print(f"  - Follow-up required: {'Yes' if sales_notes.get('follow_up_required') else 'No'}")
                
                key_points = sales_notes.get('key_points', [])
                if key_points:
                    print(f"  - Key points ({len(key_points)}):")
                    for point in key_points[:3]:  # Show first 3 points
                        print(f"    * {point}")
                
                next_steps = sales_notes.get('next_steps', [])
                if next_steps:
                    print(f"  - Next steps ({len(next_steps)}):")
                    for step in next_steps:
                        print(f"    * {step}")
            
            # Display processing notes
            processing_notes = result.notes
            if processing_notes:
                print(f"  - Processing notes:")
                for note in processing_notes:
                    print(f"    * {note}")
        else:
            print(f"  - Error: {result.error_message}")
        
        print()
    
    # Demonstrate workflow configuration
    print("=== Workflow Configuration ===")
    workflow_config = sales_agent.get_workflow_config()
    print(f"Agent name: {workflow_config.agent_name}")
    print(f"Workflow type: {workflow_config.workflow_type}")
    print(f"Max retries: {workflow_config.max_retries}")
    print(f"Timeout: {workflow_config.timeout}s")
    print(f"Retry delay: {workflow_config.retry_delay}s")
    print(f"Enable state persistence: {workflow_config.enable_state_persistence}")
    print(f"Workflow steps ({len(workflow_config.workflow_steps)}):")
    for step in workflow_config.workflow_steps:
        step_config = workflow_config.step_configs.get(step, {})
        timeout = step_config.get('timeout', 'default')
        llm_required = step_config.get('llm_required', 'optional')
        print(f"  - {step} (timeout: {timeout}s, LLM: {llm_required})")
    print()
    
    # Demonstrate agent information
    print("=== Agent Information ===")
    agent_info = sales_agent.get_agent_info()
    print(f"Name: {agent_info['name']}")
    print(f"Type: {agent_info['type']}")
    print(f"Required capabilities: {', '.join(agent_info['required_capabilities'])}")
    print(f"Configuration: {agent_info['config']}")
    print()
    
    # Test concurrent processing
    print("=== Concurrent Processing Test ===")
    print("Processing multiple emails concurrently...")
    
    concurrent_data = []
    for i in range(3):
        data = {
            "source": "email",
            "email": {
                "subject": f"Concurrent test email {i+1}",
                "sender": f"customer{i+1}@example.com",
                "recipient": "sales@company.com",
                "body": f"This is test email {i+1} for concurrent processing."
            }
        }
        concurrent_data.append(data)
    
    # Process concurrently
    start_time = datetime.now()
    tasks = [sales_agent.process(data) for data in concurrent_data]
    results = await asyncio.gather(*tasks)
    concurrent_time = (datetime.now() - start_time).total_seconds()
    
    print(f"Processed {len(results)} emails concurrently in {concurrent_time:.2f}s")
    for i, result in enumerate(results):
        print(f"  - Email {i+1}: {'✓ Success' if result.success else '✗ Failed'} ({result.execution_time:.2f}s)")
    
    print("\n=== Sales Agent Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())