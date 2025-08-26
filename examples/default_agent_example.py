#!/usr/bin/env python3
"""
Example demonstrating the DefaultAgent functionality.

This example shows how to use the DefaultAgent for handling unmatched requests
that don't fit any specific criteria.
"""

import asyncio
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '.')

from agents.default_agent import DefaultAgent
from utils.llm_provider import LLMManager
from models.data_models import AgentResult


async def basic_default_agent_example():
    """Demonstrate basic DefaultAgent usage without LLM enhancement."""
    print("🔧 Basic DefaultAgent Example")
    print("=" * 50)
    
    # Create a default agent with basic configuration
    config = {
        'response_template': 'Thank you for your inquiry. We will review your request and respond soon.',
        'enable_llm_enhancement': False,  # Disable LLM for this example
        'log_unmatched_requests': True,
        'include_request_summary': True
    }
    
    agent = DefaultAgent(name="basic_default_agent", config=config)
    
    # Example 1: Handle an email that doesn't match any criteria
    print("\n📧 Processing unmatched email...")
    email_input = {
        'source': 'email',
        'email': {
            'subject': 'Random question about your company',
            'sender': 'curious@example.com',
            'recipient': 'info@company.com',
            'body': 'I was wondering about your company history and founding story.',
            'headers': {'Message-ID': 'random123'}
        },
        'timestamp': datetime.now().isoformat()
    }
    
    result = await agent.process(email_input)
    
    print(f"✅ Processing successful: {result.success}")
    print(f"📝 Agent: {result.agent_name}")
    print(f"⏱️  Execution time: {result.execution_time:.3f}s")
    print(f"🔍 Requires human review: {result.requires_human_review}")
    print(f"💬 Response message: {result.output['message']}")
    print(f"🤖 LLM enhanced: {result.output['llm_enhanced']}")
    
    # Show request summary
    if 'request_summary' in result.output:
        summary = result.output['request_summary']
        print(f"📊 Request summary:")
        print(f"   - Source: {summary['source']}")
        print(f"   - Has email data: {summary['has_email_data']}")
        if 'email_summary' in summary:
            email_summary = summary['email_summary']
            print(f"   - Email from: {email_summary['sender']}")
            print(f"   - Subject length: {email_summary['subject_length']} chars")
    
    print(f"📋 Notes: {', '.join(result.notes)}")


async def webhook_default_agent_example():
    """Demonstrate DefaultAgent with webhook input."""
    print("\n\n🌐 Webhook DefaultAgent Example")
    print("=" * 50)
    
    agent = DefaultAgent(name="webhook_default_agent")
    
    # Example 2: Handle a webhook that doesn't match any criteria
    print("\n🔗 Processing unmatched webhook...")
    webhook_input = {
        'source': 'webhook',
        'webhook': {
            'event': 'unknown_event',
            'data': {
                'user_id': '12345',
                'action': 'mysterious_action',
                'metadata': {
                    'ip': '192.168.1.1',
                    'user_agent': 'CustomBot/1.0'
                }
            }
        },
        'timestamp': datetime.now().isoformat()
    }
    
    result = await agent.process(webhook_input)
    
    print(f"✅ Processing successful: {result.success}")
    print(f"📝 Agent: {result.agent_name}")
    print(f"⏱️  Execution time: {result.execution_time:.3f}s")
    print(f"💬 Response message: {result.output['message']}")
    
    # Show webhook summary
    if 'request_summary' in result.output:
        summary = result.output['request_summary']
        if 'webhook_summary' in summary:
            webhook_summary = summary['webhook_summary']
            print(f"📊 Webhook summary:")
            print(f"   - Payload keys: {webhook_summary['payload_keys']}")
            print(f"   - Payload size: {webhook_summary['payload_size']} chars")


async def enhanced_default_agent_example():
    """Demonstrate DefaultAgent with LLM enhancement (mock)."""
    print("\n\n🧠 Enhanced DefaultAgent Example")
    print("=" * 50)
    
    # Create a mock LLM manager for demonstration
    class MockLLMManager:
        async def generate_with_fallback(self, prompt, **kwargs):
            # Mock LLM response
            class MockResponse:
                content = '{"suggested_action": "create_support_ticket", "urgency_level": "medium", "category": "general_inquiry", "response_message": "Thank you for your inquiry. We will create a support ticket for you.", "next_steps": ["Create support ticket", "Assign to general support team"], "confidence": 0.8}'
            return MockResponse()
    
    # Create agent with LLM enhancement
    config = {
        'response_template': 'Default response template',
        'enable_llm_enhancement': True,
        'log_unmatched_requests': True,
        'include_request_summary': True
    }
    
    agent = DefaultAgent(
        name="enhanced_default_agent", 
        config=config, 
        llm_manager=MockLLMManager()
    )
    
    # Example 3: Handle a complex inquiry with LLM enhancement
    print("\n🤖 Processing with LLM enhancement...")
    complex_input = {
        'source': 'email',
        'email': {
            'subject': 'Urgent: Need help with integration issues',
            'sender': 'developer@startup.com',
            'recipient': 'support@company.com',
            'body': 'Hi, we are having trouble integrating your API with our system. The authentication keeps failing and we have a deadline tomorrow. Can someone help us urgently?',
            'headers': {'Message-ID': 'urgent456'}
        },
        'timestamp': datetime.now().isoformat()
    }
    
    result = await agent.process(complex_input)
    
    print(f"✅ Processing successful: {result.success}")
    print(f"📝 Agent: {result.agent_name}")
    print(f"⏱️  Execution time: {result.execution_time:.3f}s")
    print(f"🤖 LLM enhanced: {result.output['llm_enhanced']}")
    
    if result.output['llm_enhanced']:
        print(f"🎯 Suggested action: {result.output['suggested_action']}")
        print(f"🚨 Urgency level: {result.output['urgency_level']}")
        print(f"📂 Category: {result.output['category']}")
        print(f"💬 Enhanced message: {result.output['response_message']}")
        print(f"📋 Next steps: {', '.join(result.output['next_steps'])}")
        print(f"🎲 Confidence: {result.output['confidence']}")


async def error_handling_example():
    """Demonstrate DefaultAgent error handling."""
    print("\n\n❌ Error Handling Example")
    print("=" * 50)
    
    agent = DefaultAgent(name="error_handling_agent")
    
    # Example 4: Invalid input handling
    print("\n🚫 Testing invalid input handling...")
    
    invalid_inputs = [
        "string input",
        123,
        None,
        {},  # Empty dict
        []   # List instead of dict
    ]
    
    for i, invalid_input in enumerate(invalid_inputs, 1):
        print(f"\n   Test {i}: {type(invalid_input).__name__} input")
        result = await agent.process(invalid_input)
        print(f"   ✅ Handled gracefully: success={result.success}")
        if not result.success:
            print(f"   📝 Error: {result.error_message}")


def configuration_examples():
    """Show different configuration options for DefaultAgent."""
    print("\n\n⚙️  Configuration Examples")
    print("=" * 50)
    
    # Example 5: Different configuration options
    configs = [
        {
            'name': 'Minimal Config',
            'config': {}
        },
        {
            'name': 'Custom Response Template',
            'config': {
                'response_template': 'We have received your message and will get back to you within 24 hours.',
                'enable_llm_enhancement': False
            }
        },
        {
            'name': 'Silent Mode',
            'config': {
                'log_unmatched_requests': False,
                'include_request_summary': False,
                'enable_llm_enhancement': False
            }
        },
        {
            'name': 'LLM Enhanced',
            'config': {
                'enable_llm_enhancement': True,
                'response_template': 'Analyzing your request...'
            }
        }
    ]
    
    for config_example in configs:
        print(f"\n📋 {config_example['name']}:")
        agent = DefaultAgent(
            name=f"agent_{config_example['name'].lower().replace(' ', '_')}", 
            config=config_example['config']
        )
        
        print(f"   - Response template: {agent.response_template[:50]}...")
        print(f"   - LLM enhancement: {agent.enable_llm_enhancement}")
        print(f"   - Log unmatched: {agent.log_unmatched_requests}")
        print(f"   - Include summary: {agent.include_request_summary}")
        
        # Show workflow config
        workflow_config = agent.get_workflow_config()
        print(f"   - Workflow type: {workflow_config.workflow_type}")
        print(f"   - Max retries: {workflow_config.max_retries}")
        print(f"   - Timeout: {workflow_config.timeout}s")
        
        # Show LLM capabilities
        capabilities = agent.get_required_llm_capabilities()
        print(f"   - LLM capabilities: {capabilities if capabilities else 'None'}")


async def main():
    """Run all examples."""
    print("🚀 DefaultAgent Examples")
    print("=" * 70)
    print("This example demonstrates the DefaultAgent functionality for handling")
    print("unmatched requests that don't fit specific criteria.")
    print("=" * 70)
    
    try:
        # Run async examples
        await basic_default_agent_example()
        await webhook_default_agent_example()
        await enhanced_default_agent_example()
        await error_handling_example()
        
        # Run sync examples
        configuration_examples()
        
        print("\n\n🎉 All DefaultAgent examples completed successfully!")
        print("\n📚 Key Takeaways:")
        print("  • DefaultAgent handles requests that don't match specific criteria")
        print("  • It provides basic response generation and logging")
        print("  • LLM enhancement can be enabled for more intelligent responses")
        print("  • It supports various input types (email, webhook, etc.)")
        print("  • Configuration options allow customization of behavior")
        print("  • All results are marked as requiring human review")
        print("  • Robust error handling ensures no request goes unprocessed")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())