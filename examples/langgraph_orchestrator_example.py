#!/usr/bin/env python3
"""
Example demonstrating LangGraph orchestrator functionality.

This example shows how to:
1. Create a LangGraph orchestrator
2. Register custom step functions
3. Execute workflows with different configurations
4. Handle workflow errors and retries
"""

import asyncio
from datetime import datetime

from graphs.multiagent_graph import (
    LangGraphOrchestrator, WorkflowState, set_step_result_in_state, get_step_result_from_state
)
from models.data_models import TriggerData
from models.config_models import AgentConfig, WorkflowConfig
from utils.exceptions import WorkflowError


async def main():
    """Main example function."""
    print("🚀 LangGraph Orchestrator Example")
    print("=" * 50)
    
    # Create orchestrator
    orchestrator = LangGraphOrchestrator()
    
    # Create sample trigger data
    trigger_data = TriggerData(
        source="example",
        timestamp=datetime.now(),
        data={
            "message": "Hello, this is a test message for processing!",
            "user_id": "user123",
            "priority": "high"
        },
        metadata={"example": True}
    )
    
    print(f"📨 Input data: {trigger_data.data}")
    print()
    
    # Example 1: Basic workflow with default steps
    print("Example 1: Basic Workflow")
    print("-" * 30)
    
    basic_config = AgentConfig(
        name="basic_agent",
        agent_type="example",
        workflow_config=WorkflowConfig(
            agent_name="basic_agent",
            workflow_steps=["validate_input", "process_data", "generate_output"]
        )
    )
    
    result = await orchestrator.execute_workflow("basic_agent", trigger_data, basic_config)
    print(f"✅ Success: {result.success}")
    print(f"📊 Output: {result.result.output}")
    print(f"⏱️  Execution time: {result.execution_time:.3f}s")
    print(f"📝 Steps completed: {result.steps_completed}")
    print()
    
    # Example 2: Custom workflow with specialized steps
    print("Example 2: Custom Workflow with Specialized Steps")
    print("-" * 50)
    
    # Register custom step functions
    async def parse_message(state: WorkflowState) -> WorkflowState:
        """Parse and extract information from the message."""
        state["context"].add_step("parse_message")
        
        message = state["trigger_data"].data.get("message", "")
        words = message.split()
        
        parsed_data = {
            "original_message": message,
            "word_count": len(words),
            "has_greeting": any(word.lower() in ["hello", "hi", "hey"] for word in words),
            "message_length": len(message),
            "user_id": state["trigger_data"].data.get("user_id")
        }
        
        state = set_step_result_in_state(state, "parse_message", parsed_data)
        print(f"  📝 Parsed message: {parsed_data['word_count']} words, greeting: {parsed_data['has_greeting']}")
        return state
    
    async def analyze_sentiment(state: WorkflowState) -> WorkflowState:
        """Analyze the sentiment of the message."""
        state["context"].add_step("analyze_sentiment")
        
        parsed_data = get_step_result_from_state(state, "parse_message", {})
        message = parsed_data.get("original_message", "")
        
        # Simple sentiment analysis (in real implementation, use ML model)
        positive_words = ["good", "great", "excellent", "happy", "love", "awesome"]
        negative_words = ["bad", "terrible", "hate", "awful", "horrible", "worst"]
        
        positive_count = sum(1 for word in positive_words if word in message.lower())
        negative_count = sum(1 for word in negative_words if word in message.lower())
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        sentiment_data = {
            "sentiment": sentiment,
            "positive_score": positive_count,
            "negative_score": negative_count,
            "confidence": abs(positive_count - negative_count) / max(1, positive_count + negative_count)
        }
        
        state = set_step_result_in_state(state, "analyze_sentiment", sentiment_data)
        print(f"  🎭 Sentiment: {sentiment} (confidence: {sentiment_data['confidence']:.2f})")
        return state
    
    async def generate_response(state: WorkflowState) -> WorkflowState:
        """Generate a response based on the analysis."""
        state["context"].add_step("generate_response")
        
        parsed_data = get_step_result_from_state(state, "parse_message", {})
        sentiment_data = get_step_result_from_state(state, "analyze_sentiment", {})
        
        response = {
            "status": "processed",
            "user_id": parsed_data.get("user_id"),
            "analysis": {
                "word_count": parsed_data.get("word_count"),
                "has_greeting": parsed_data.get("has_greeting"),
                "sentiment": sentiment_data.get("sentiment"),
                "sentiment_confidence": sentiment_data.get("confidence")
            },
            "suggested_action": "respond_friendly" if sentiment_data.get("sentiment") == "positive" else "handle_with_care",
            "processed_at": datetime.now().isoformat(),
            "workflow_id": state["context"].workflow_id
        }
        
        state = {**state, "current_output": response}
        print(f"  💬 Generated response with action: {response['suggested_action']}")
        return state
    
    # Register the custom step functions
    orchestrator.register_step_function("parse_message", parse_message)
    orchestrator.register_step_function("analyze_sentiment", analyze_sentiment)
    orchestrator.register_step_function("generate_response", generate_response)
    
    # Create custom workflow config
    custom_config = AgentConfig(
        name="message_analyzer",
        agent_type="analyzer",
        workflow_config=WorkflowConfig(
            agent_name="message_analyzer",
            workflow_steps=["parse_message", "analyze_sentiment", "generate_response"],
            max_retries=2,
            timeout=60
        )
    )
    
    result = await orchestrator.execute_workflow("message_analyzer", trigger_data, custom_config)
    print(f"✅ Success: {result.success}")
    print(f"📊 Analysis result: {result.result.output}")
    print(f"⏱️  Execution time: {result.execution_time:.3f}s")
    print()
    
    # Example 3: Error handling and retry
    print("Example 3: Error Handling and Retry")
    print("-" * 40)
    
    attempt_count = 0
    
    async def flaky_step(state: WorkflowState) -> WorkflowState:
        """A step that fails on first attempt but succeeds on retry."""
        nonlocal attempt_count
        attempt_count += 1
        
        state["context"].add_step("flaky_step")
        
        if attempt_count == 1:
            print(f"  ❌ Attempt {attempt_count}: Simulated failure")
            raise WorkflowError("Simulated network timeout")
        
        print(f"  ✅ Attempt {attempt_count}: Success!")
        state = set_step_result_in_state(state, "flaky_step", {"attempt": attempt_count, "status": "success"})
        return state
    
    async def final_step(state: WorkflowState) -> WorkflowState:
        """Final step that processes the result."""
        state["context"].add_step("final_step")
        
        flaky_result = get_step_result_from_state(state, "flaky_step", {})
        
        final_output = {
            "message": "Workflow completed successfully after retry",
            "attempts_needed": flaky_result.get("attempt", 0),
            "final_status": "completed"
        }
        
        state = {**state, "current_output": final_output}
        print(f"  🎯 Final step completed after {flaky_result.get('attempt', 0)} attempts")
        return state
    
    # Register retry example steps
    orchestrator.register_step_function("flaky_step", flaky_step)
    orchestrator.register_step_function("final_step", final_step)
    
    retry_config = AgentConfig(
        name="retry_agent",
        agent_type="retry_example",
        workflow_config=WorkflowConfig(
            agent_name="retry_agent",
            workflow_steps=["flaky_step", "final_step"],
            max_retries=3,
            retry_delay=0.1  # Short delay for demo
        )
    )
    
    result = await orchestrator.execute_workflow("retry_agent", trigger_data, retry_config)
    print(f"✅ Success: {result.success}")
    print(f"📊 Final result: {result.result.output}")
    print(f"⏱️  Execution time: {result.execution_time:.3f}s")
    print()
    
    # Example 4: Workflow status monitoring
    print("Example 4: Workflow Status Monitoring")
    print("-" * 40)
    
    # Show active workflows (should be empty now)
    active_workflows = orchestrator.get_active_workflows()
    print(f"📊 Active workflows: {len(active_workflows)}")
    
    # Show cached workflows
    print(f"💾 Cached workflows: {list(orchestrator.workflows.keys())}")
    
    print("\n🎉 All examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())