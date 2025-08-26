"""Example script demonstrating the AI Agent Framework API endpoints."""

import asyncio
import json
import httpx
from datetime import datetime


async def test_api_endpoints():
    """Test all API endpoints with sample data."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("🚀 Testing AI Agent Framework API Endpoints\n")
        
        # Test root endpoint
        print("1. Testing root endpoint...")
        response = await client.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
        
        # Test health endpoint
        print("2. Testing health endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
        
        # Test webhook endpoint
        print("3. Testing webhook endpoint...")
        webhook_data = {
            "source": "github",
            "data": {
                "action": "push",
                "repository": "ai-agent-framework",
                "commits": [
                    {"id": "abc123", "message": "Add new feature"}
                ]
            },
            "metadata": {
                "webhook_id": "wh_123",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        response = await client.post(f"{base_url}/api/trigger/webhook", json=webhook_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
        
        # Test email endpoint
        print("4. Testing email endpoint...")
        email_data = {
            "subject": "Sales Inquiry - Need Quote",
            "sender": "customer@example.com",
            "recipient": "sales@company.com",
            "body": "Hi, I'm interested in your product and would like to get a quote for 100 units. Please let me know the pricing and delivery timeline.",
            "headers": {
                "Message-ID": "<test123@example.com>",
                "X-Priority": "3"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        response = await client.post(f"{base_url}/api/trigger/email", json=email_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
        
        # Test generic trigger endpoint
        print("5. Testing generic trigger endpoint...")
        generic_data = {
            "trigger_type": "user_signup",
            "data": {
                "user_id": "user_123",
                "email": "newuser@example.com",
                "plan": "premium",
                "signup_source": "website"
            },
            "metadata": {
                "source_ip": "192.168.1.1",
                "user_agent": "Mozilla/5.0"
            }
        }
        response = await client.post(f"{base_url}/api/trigger", json=generic_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
        
        # Test error handling
        print("6. Testing error handling...")
        invalid_data = {
            "source": "",  # Invalid empty source
            "data": {}
        }
        response = await client.post(f"{base_url}/api/trigger/webhook", json=invalid_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
        
        print("✅ All API endpoint tests completed!")


def run_sync_example():
    """Run synchronous example using requests."""
    import requests
    
    base_url = "http://localhost:8000"
    
    print("🚀 Testing AI Agent Framework API (Synchronous)\n")
    
    # Test webhook endpoint
    print("Testing webhook endpoint...")
    webhook_data = {
        "source": "slack",
        "data": {
            "channel": "#general",
            "user": "john.doe",
            "message": "Deploy to production",
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    try:
        response = requests.post(f"{base_url}/api/trigger/webhook", json=webhook_data, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed - make sure the server is running with: python main.py\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")


if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Async test (requires running server)")
    print("2. Sync test (requires running server)")
    print("3. Just show example data")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        print("\n📝 Make sure to start the server first:")
        print("   python main.py")
        print("\nPress Enter to continue...")
        input()
        asyncio.run(test_api_endpoints())
    elif choice == "2":
        print("\n📝 Make sure to start the server first:")
        print("   python main.py")
        print("\nPress Enter to continue...")
        input()
        run_sync_example()
    else:
        print("\n📋 Example API Usage:\n")
        
        print("Webhook Request:")
        webhook_example = {
            "source": "github",
            "data": {"action": "push", "repository": "my-repo"},
            "metadata": {"webhook_id": "wh_123"}
        }
        print(f"POST /api/trigger/webhook")
        print(json.dumps(webhook_example, indent=2))
        
        print("\nEmail Request:")
        email_example = {
            "subject": "Customer Inquiry",
            "sender": "customer@example.com",
            "recipient": "support@company.com",
            "body": "I need help with my order."
        }
        print(f"POST /api/trigger/email")
        print(json.dumps(email_example, indent=2))
        
        print("\nGeneric Trigger Request:")
        generic_example = {
            "trigger_type": "api_call",
            "data": {"action": "process_payment", "amount": 100}
        }
        print(f"POST /api/trigger")
        print(json.dumps(generic_example, indent=2))