"""Example demonstrating email integration functionality."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from tools.email_tools import (
    EmailService, EmailPoller, EmailProcessor,
    create_email_client, create_email_trigger_handler
)
from models.config_models import EmailConfig
from models.data_models import EmailMessage, TriggerData

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def custom_trigger_handler(trigger_data: TriggerData) -> None:
    """Custom handler for email triggers."""
    print(f"\n=== Email Trigger Received ===")
    print(f"Source: {trigger_data.source}")
    print(f"Timestamp: {trigger_data.timestamp}")
    
    email_data = trigger_data.data.get('email', {})
    print(f"From: {email_data.get('sender')}")
    print(f"Subject: {email_data.get('subject')}")
    print(f"Body: {email_data.get('body')[:100]}...")
    print(f"Attachments: {len(email_data.get('attachments', []))}")
    print("=" * 30)


async def example_email_client_usage():
    """Example of using email clients directly."""
    print("\n=== Email Client Example ===")
    
    # Note: This example uses mock credentials - replace with real ones for testing
    try:
        # Create IMAP client
        client = create_email_client(
            protocol='IMAP',
            host='imap.gmail.com',
            port=993,
            username='your_email@gmail.com',
            password='your_app_password',  # Use app password for Gmail
            use_ssl=True,
            mailbox='INBOX'
        )
        
        print(f"Created {client.__class__.__name__} for {client.host}")
        
        # In a real scenario, you would connect and fetch messages:
        # async with client:
        #     messages = await client.fetch_messages(limit=5, unread_only=True)
        #     print(f"Fetched {len(messages)} messages")
        #     
        #     for msg in messages:
        #         print(f"- {msg.subject} from {msg.sender}")
        
        print("Note: Connection not attempted in this example")
        
    except Exception as e:
        print(f"Error creating client: {e}")


async def example_email_poller_usage():
    """Example of using email poller."""
    print("\n=== Email Poller Example ===")
    
    # Create email poller
    poller = EmailPoller(
        protocol='IMAP',
        host='imap.gmail.com',
        port=993,
        username='your_email@gmail.com',
        password='your_app_password',
        poll_interval=30,  # Poll every 30 seconds
        max_messages_per_poll=5
    )
    
    # Create custom message handler
    async def message_handler(email_message: EmailMessage):
        print(f"Received email: {email_message.subject} from {email_message.sender}")
        
        # You could process the email here or convert it to a trigger
        processor = EmailProcessor(trigger_handler=custom_trigger_handler)
        await processor.process_email(email_message)
    
    # Add handler to poller
    poller.add_message_handler(message_handler)
    
    print(f"Created poller for {poller.username}@{poller.host}")
    print(f"Poll interval: {poller.poll_interval} seconds")
    
    # In a real scenario, you would start the poller:
    # await poller.start()
    # print("Poller started - press Ctrl+C to stop")
    # 
    # try:
    #     while True:
    #         await asyncio.sleep(1)
    # except KeyboardInterrupt:
    #     await poller.stop()
    #     print("Poller stopped")
    
    print("Note: Poller not started in this example")


async def example_email_service_usage():
    """Example of using the email service."""
    print("\n=== Email Service Example ===")
    
    # Create email configuration
    config = EmailConfig(
        protocol='IMAP',
        host='imap.gmail.com',
        port=993,
        username='your_email@gmail.com',
        password='your_app_password',
        use_ssl=True,
        mailbox='INBOX',
        poll_interval=60,
        max_messages_per_poll=10,
        auto_process=True,
        enabled=True
    )
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print(f"Configuration errors: {errors}")
        return
    
    # Create and configure service
    service = EmailService()
    service.configure(config)
    
    print(f"Email service configured:")
    print(f"- Protocol: {config.protocol}")
    print(f"- Host: {config.host}")
    print(f"- Username: {config.username}")
    print(f"- Poll interval: {config.poll_interval}s")
    print(f"- Enabled: {config.enabled}")
    
    # Get service status
    status = service.get_status()
    print(f"\nService status: {status}")
    
    # In a real scenario, you would start the service:
    # await service.start()
    # print("Email service started")
    # 
    # # Let it run for a while
    # await asyncio.sleep(60)
    # 
    # await service.stop()
    # print("Email service stopped")
    
    print("Note: Service not started in this example")


async def example_manual_email_processing():
    """Example of manually processing email messages."""
    print("\n=== Manual Email Processing Example ===")
    
    # Create a sample email message
    sample_email = EmailMessage(
        subject="Interested in your product pricing",
        sender="customer@example.com",
        recipient="sales@yourcompany.com",
        body="""
        Hi,
        
        I'm interested in learning more about your products and getting 
        pricing information for a potential purchase. Could you please 
        send me a quote for your enterprise solution?
        
        Best regards,
        John Customer
        """,
        timestamp=datetime.now(),
        headers={
            'Message-ID': '<sample@example.com>',
            'From': 'John Customer <customer@example.com>',
            'To': 'sales@yourcompany.com'
        }
    )
    
    print(f"Processing sample email:")
    print(f"- Subject: {sample_email.subject}")
    print(f"- From: {sample_email.sender}")
    print(f"- To: {sample_email.recipient}")
    
    # Create processor with custom handler
    processor = EmailProcessor(trigger_handler=custom_trigger_handler)
    
    # Process the email
    trigger_data = await processor.process_email(sample_email)
    
    if trigger_data:
        print(f"\nEmail successfully converted to trigger:")
        print(f"- Source: {trigger_data.source}")
        print(f"- Timestamp: {trigger_data.timestamp}")
        print(f"- Data keys: {list(trigger_data.data.keys())}")
    
    # Get processor stats
    stats = processor.get_stats()
    print(f"\nProcessor stats: {stats}")


async def example_email_trigger_handler():
    """Example of using the email trigger handler factory."""
    print("\n=== Email Trigger Handler Example ===")
    
    # Create email trigger handler
    handler = create_email_trigger_handler(trigger_handler=custom_trigger_handler)
    
    # Create sample email
    sample_email = EmailMessage(
        subject="Support Request - Login Issues",
        sender="user@company.com",
        recipient="support@yourcompany.com",
        body="I'm having trouble logging into my account. Can you help?",
        timestamp=datetime.now()
    )
    
    print(f"Using trigger handler for email:")
    print(f"- Subject: {sample_email.subject}")
    print(f"- From: {sample_email.sender}")
    
    # Process email through handler
    await handler(sample_email)
    
    print("Email processed through trigger handler")


def example_email_config_validation():
    """Example of email configuration validation."""
    print("\n=== Email Configuration Validation Example ===")
    
    # Valid configuration
    valid_config = EmailConfig(
        protocol='IMAP',
        host='imap.gmail.com',
        port=993,
        username='test@gmail.com',
        password='password123',
        enabled=True
    )
    
    errors = valid_config.validate()
    print(f"Valid config errors: {errors}")
    
    # Invalid configuration
    invalid_config = EmailConfig(
        protocol='INVALID',  # Invalid protocol
        host='',  # Empty host
        port=0,  # Invalid port
        username='',  # Empty username
        password='',  # Empty password
        poll_interval=-1,  # Invalid interval
        enabled=True
    )
    
    errors = invalid_config.validate()
    print(f"Invalid config errors: {errors}")


async def main():
    """Run all examples."""
    print("AI Agent Framework - Email Integration Examples")
    print("=" * 50)
    
    # Run examples
    await example_email_client_usage()
    await example_email_poller_usage()
    await example_email_service_usage()
    await example_manual_email_processing()
    await example_email_trigger_handler()
    example_email_config_validation()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo use with real email servers:")
    print("1. Update credentials in the examples")
    print("2. Configure your email server settings")
    print("3. Set up environment variables (EMAIL_HOST, EMAIL_USERNAME, etc.)")
    print("4. Enable email integration in your configuration file")


if __name__ == "__main__":
    asyncio.run(main())