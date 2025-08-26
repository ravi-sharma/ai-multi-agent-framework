"""Integration tests for email functionality."""

import asyncio
import pytest
import email
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from email import (
    EmailClient, IMAPClient, POP3Client, create_email_client,
    EmailPoller, EmailProcessor, EmailService,
    get_email_service, configure_email_service
)
from models.data_models import EmailMessage, TriggerData, Attachment
from models.config_models import EmailConfig


class TestEmailClients:
    """Test email client implementations."""
    
    @pytest.fixture
    def sample_raw_email(self):
        """Sample raw email for testing."""
        return """From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test@example.com>

This is a test email body.
"""
    
    @pytest.fixture
    def email_config(self):
        """Sample email configuration."""
        return EmailConfig(
            protocol='IMAP',
            host='imap.example.com',
            port=993,
            username='test@example.com',
            password='password',
            use_ssl=True,
            mailbox='INBOX',
            poll_interval=60,
            max_messages_per_poll=10,
            auto_process=True,
            enabled=True
        )
    
    def test_create_email_client_imap(self, email_config):
        """Test creating IMAP client."""
        client = create_email_client(
            protocol='IMAP',
            host=email_config.host,
            port=email_config.port,
            username=email_config.username,
            password=email_config.password,
            use_ssl=email_config.use_ssl,
            mailbox=email_config.mailbox
        )
        
        assert isinstance(client, IMAPClient)
        assert client.host == email_config.host
        assert client.port == email_config.port
        assert client.username == email_config.username
        assert client.mailbox == email_config.mailbox
    
    def test_create_email_client_pop3(self, email_config):
        """Test creating POP3 client."""
        client = create_email_client(
            protocol='POP3',
            host=email_config.host,
            port=email_config.port,
            username=email_config.username,
            password=email_config.password,
            use_ssl=email_config.use_ssl
        )
        
        assert isinstance(client, POP3Client)
        assert client.host == email_config.host
        assert client.port == email_config.port
        assert client.username == email_config.username
    
    def test_create_email_client_invalid_protocol(self, email_config):
        """Test creating client with invalid protocol."""
        with pytest.raises(ValueError, match="Unsupported email protocol"):
            create_email_client(
                protocol='SMTP',
                host=email_config.host,
                port=email_config.port,
                username=email_config.username,
                password=email_config.password
            )
    
    @pytest.mark.asyncio
    async def test_imap_client_connection_error(self, email_config):
        """Test IMAP client connection error handling."""
        client = IMAPClient(
            host='invalid.host.com',
            port=993,
            username=email_config.username,
            password=email_config.password
        )
        
        with pytest.raises(ConnectionError):
            await client.connect()
    
    @pytest.mark.asyncio
    async def test_pop3_client_connection_error(self, email_config):
        """Test POP3 client connection error handling."""
        client = POP3Client(
            host='invalid.host.com',
            port=995,
            username=email_config.username,
            password=email_config.password
        )
        
        with pytest.raises(ConnectionError):
            await client.connect()
    
    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_imap_client_fetch_messages(self, mock_imap, sample_raw_email):
        """Test IMAP client message fetching."""
        # Mock IMAP connection
        mock_connection = Mock()
        mock_imap.return_value = mock_connection
        
        # Mock search results
        mock_connection.search.return_value = ('OK', [b'1 2 3'])
        
        # Mock fetch results
        mock_connection.fetch.return_value = ('OK', [(None, sample_raw_email.encode())])
        
        client = IMAPClient('imap.example.com', 993, 'test@example.com', 'password')
        client._connection = mock_connection
        
        messages = await client.fetch_messages(limit=3)
        
        assert len(messages) == 3
        for msg in messages:
            assert isinstance(msg, EmailMessage)
            assert msg.sender == 'sender@example.com'
            assert msg.subject == 'Test Email'
    
    @pytest.mark.asyncio
    @patch('poplib.POP3_SSL')
    async def test_pop3_client_fetch_messages(self, mock_pop3, sample_raw_email):
        """Test POP3 client message fetching."""
        # Mock POP3 connection
        mock_connection = Mock()
        mock_pop3.return_value = mock_connection
        
        # Mock stat results (3 messages)
        mock_connection.stat.return_value = (3, 1024)
        
        # Mock retr results
        email_lines = sample_raw_email.encode().split(b'\n')
        mock_connection.retr.return_value = ('OK', email_lines, len(sample_raw_email))
        
        client = POP3Client('pop.example.com', 995, 'test@example.com', 'password')
        client._connection = mock_connection
        
        messages = await client.fetch_messages(limit=3)
        
        assert len(messages) == 3
        for msg in messages:
            assert isinstance(msg, EmailMessage)
            assert msg.sender == 'sender@example.com'
            assert msg.subject == 'Test Email'


class TestEmailPoller:
    """Test email polling functionality."""
    
    @pytest.fixture
    def email_config(self):
        """Sample email configuration."""
        return EmailConfig(
            protocol='IMAP',
            host='imap.example.com',
            port=993,
            username='test@example.com',
            password='password',
            poll_interval=1,  # Short interval for testing
            max_messages_per_poll=5,
            enabled=True
        )
    
    @pytest.fixture
    def sample_email_message(self):
        """Sample email message."""
        return EmailMessage(
            subject='Test Subject',
            sender='sender@example.com',
            recipient='recipient@example.com',
            body='Test body',
            timestamp=datetime.now()
        )
    
    def test_email_poller_initialization(self, email_config):
        """Test email poller initialization."""
        poller = EmailPoller(
            protocol=email_config.protocol,
            host=email_config.host,
            port=email_config.port,
            username=email_config.username,
            password=email_config.password,
            poll_interval=email_config.poll_interval,
            max_messages_per_poll=email_config.max_messages_per_poll
        )
        
        assert poller.protocol == email_config.protocol
        assert poller.host == email_config.host
        assert poller.poll_interval == email_config.poll_interval
        assert not poller._running
    
    @pytest.mark.asyncio
    async def test_email_poller_message_handler(self, email_config, sample_email_message):
        """Test email poller message handler."""
        poller = EmailPoller(
            protocol=email_config.protocol,
            host=email_config.host,
            port=email_config.port,
            username=email_config.username,
            password=email_config.password
        )
        
        # Mock handler
        handler = AsyncMock()
        poller.add_message_handler(handler)
        
        # Process message
        await poller._process_message(sample_email_message)
        
        # Verify handler was called
        handler.assert_called_once_with(sample_email_message)
    
    @pytest.mark.asyncio
    @patch('ai_agent_framework.email.poller.create_email_client')
    async def test_email_poller_poll_once(self, mock_create_client, email_config, sample_email_message):
        """Test single poll operation."""
        # Mock client with async context manager support
        mock_client = AsyncMock()
        mock_client.fetch_messages.return_value = [sample_email_message]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_create_client.return_value = mock_client
        
        poller = EmailPoller(
            protocol=email_config.protocol,
            host=email_config.host,
            port=email_config.port,
            username=email_config.username,
            password=email_config.password
        )
        
        # Mock handler
        handler = AsyncMock()
        poller.add_message_handler(handler)
        
        messages = await poller.poll_once()
        
        assert len(messages) == 1
        assert messages[0] == sample_email_message
        handler.assert_called_once_with(sample_email_message)
    
    def test_email_poller_status(self, email_config):
        """Test email poller status reporting."""
        poller = EmailPoller(
            protocol=email_config.protocol,
            host=email_config.host,
            port=email_config.port,
            username=email_config.username,
            password=email_config.password
        )
        
        status = poller.get_status()
        
        assert status['running'] is False
        assert status['protocol'] == email_config.protocol
        assert status['host'] == email_config.host
        assert status['username'] == email_config.username


class TestEmailProcessor:
    """Test email processing functionality."""
    
    @pytest.fixture
    def sample_email_message(self):
        """Sample email message."""
        return EmailMessage(
            subject='Test Subject',
            sender='sender@example.com',
            recipient='recipient@example.com',
            body='Test body',
            timestamp=datetime.now(),
            headers={'Message-ID': '<test@example.com>'},
            attachments=[
                Attachment(
                    filename='test.txt',
                    content_type='text/plain',
                    size=100
                )
            ]
        )
    
    @pytest.mark.asyncio
    async def test_email_processor_create_trigger_data(self, sample_email_message):
        """Test creating trigger data from email message."""
        processor = EmailProcessor(auto_process=False)
        
        trigger_data = await processor.process_email(sample_email_message)
        
        assert isinstance(trigger_data, TriggerData)
        assert trigger_data.source == 'email'
        assert 'email' in trigger_data.data
        
        email_data = trigger_data.data['email']
        assert email_data['subject'] == sample_email_message.subject
        assert email_data['sender'] == sample_email_message.sender
        assert email_data['recipient'] == sample_email_message.recipient
        assert email_data['body'] == sample_email_message.body
        assert len(email_data['attachments']) == 1
    
    @pytest.mark.asyncio
    async def test_email_processor_with_custom_handler(self, sample_email_message):
        """Test email processor with custom trigger handler."""
        custom_handler = AsyncMock()
        processor = EmailProcessor(trigger_handler=custom_handler, auto_process=True)
        
        trigger_data = await processor.process_email(sample_email_message)
        
        assert trigger_data is not None
        custom_handler.assert_called_once()
        
        # Verify the trigger data passed to handler
        call_args = custom_handler.call_args[0]
        assert isinstance(call_args[0], TriggerData)
        assert call_args[0].source == 'email'
    
    def test_email_processor_stats(self, sample_email_message):
        """Test email processor statistics."""
        processor = EmailProcessor(auto_process=False)
        
        initial_stats = processor.get_stats()
        assert initial_stats['processed_count'] == 0
        assert initial_stats['error_count'] == 0
        assert initial_stats['success_rate'] == 0
        
        # Process a message (this will succeed since auto_process is False)
        asyncio.run(processor.process_email(sample_email_message))
        
        updated_stats = processor.get_stats()
        assert updated_stats['processed_count'] == 1
        assert updated_stats['error_count'] == 0
        assert updated_stats['success_rate'] == 1.0


class TestEmailService:
    """Test email service functionality."""
    
    @pytest.fixture
    def email_config(self):
        """Sample email configuration."""
        return EmailConfig(
            protocol='IMAP',
            host='imap.example.com',
            port=993,
            username='test@example.com',
            password='password',
            poll_interval=60,
            max_messages_per_poll=10,
            enabled=True
        )
    
    def test_email_service_configuration(self, email_config):
        """Test email service configuration."""
        service = EmailService()
        
        assert not service.is_configured()
        
        service.configure(email_config)
        
        assert service.is_configured()
        assert service.config == email_config
    
    def test_email_service_disabled_config(self):
        """Test email service with disabled configuration."""
        config = EmailConfig(
            protocol='IMAP',
            host='imap.example.com',
            port=993,
            username='test@example.com',
            password='password',
            enabled=False  # Disabled
        )
        
        service = EmailService(config)
        
        assert not service.is_configured()  # Should be False when disabled
    
    @pytest.mark.asyncio
    async def test_email_service_start_stop(self, email_config):
        """Test email service start and stop."""
        service = EmailService()
        service.configure(email_config)
        
        assert not service.is_running()
        
        # Mock the poller to avoid actual network connections
        with patch('ai_agent_framework.email.poller.EmailPoller') as mock_poller_class:
            mock_poller = AsyncMock()
            mock_poller_class.return_value = mock_poller
            
            await service.start()
            
            assert service.is_running()
            
            await service.stop()
            
            assert not service.is_running()
    
    def test_email_service_status(self, email_config):
        """Test email service status reporting."""
        service = EmailService()
        
        # Test unconfigured status
        status = service.get_status()
        assert not status['configured']
        assert not status['enabled']
        assert not status['running']
        
        # Test configured status
        service.configure(email_config)
        status = service.get_status()
        assert status['configured']
        assert status['enabled']
        assert status['protocol'] == email_config.protocol
        assert status['host'] == email_config.host
    
    def test_global_email_service(self, email_config):
        """Test global email service functions."""
        # Configure global service
        configure_email_service(email_config)
        
        # Get global service
        service = get_email_service()
        
        assert service.is_configured()
        assert service.config == email_config


class TestEmailConfigValidation:
    """Test email configuration validation."""
    
    def test_valid_email_config(self):
        """Test valid email configuration."""
        config = EmailConfig(
            protocol='IMAP',
            host='imap.example.com',
            port=993,
            username='test@example.com',
            password='password'
        )
        
        errors = config.validate()
        assert len(errors) == 0
    
    def test_invalid_protocol(self):
        """Test invalid protocol validation."""
        config = EmailConfig(
            protocol='INVALID',
            host='imap.example.com',
            port=993,
            username='test@example.com',
            password='password'
        )
        
        errors = config.validate()
        assert any('Protocol must be' in error for error in errors)
    
    def test_empty_required_fields(self):
        """Test empty required fields validation."""
        config = EmailConfig(
            protocol='',
            host='',
            port=993,
            username='',
            password=''
        )
        
        errors = config.validate()
        assert len(errors) >= 4  # protocol, host, username, password
        assert any('Protocol cannot be empty' in error for error in errors)
        assert any('Host cannot be empty' in error for error in errors)
        assert any('Username cannot be empty' in error for error in errors)
        assert any('Password cannot be empty' in error for error in errors)
    
    def test_invalid_port(self):
        """Test invalid port validation."""
        config = EmailConfig(
            protocol='IMAP',
            host='imap.example.com',
            port=0,  # Invalid port
            username='test@example.com',
            password='password'
        )
        
        errors = config.validate()
        assert any('Port must be between' in error for error in errors)
    
    def test_invalid_intervals(self):
        """Test invalid interval validation."""
        config = EmailConfig(
            protocol='IMAP',
            host='imap.example.com',
            port=993,
            username='test@example.com',
            password='password',
            poll_interval=0,  # Invalid
            max_messages_per_poll=0  # Invalid
        )
        
        errors = config.validate()
        assert any('Poll interval must be positive' in error for error in errors)
        assert any('Max messages per poll must be positive' in error for error in errors)


@pytest.mark.integration
class TestEmailIntegrationEndToEnd:
    """End-to-end integration tests for email functionality."""
    
    @pytest.fixture
    def email_config(self):
        """Sample email configuration."""
        return EmailConfig(
            protocol='IMAP',
            host='imap.example.com',
            port=993,
            username='test@example.com',
            password='password',
            poll_interval=1,
            max_messages_per_poll=5,
            enabled=True
        )
    
    @pytest.mark.asyncio
    @patch('ai_agent_framework.email.client.create_email_client')
    async def test_end_to_end_email_processing(self, mock_create_client, email_config):
        """Test complete email processing workflow."""
        # Create sample email message
        sample_message = EmailMessage(
            subject='Sales Inquiry',
            sender='customer@example.com',
            recipient='sales@company.com',
            body='I am interested in your product pricing.',
            timestamp=datetime.now()
        )
        
        # Mock email client
        mock_client = AsyncMock()
        mock_client.fetch_messages.return_value = [sample_message]
        mock_create_client.return_value = mock_client
        
        # Mock trigger handler
        trigger_handler = AsyncMock()
        
        # Create and configure service
        service = EmailService()
        service.configure(email_config)
        
        # Create poller with custom handler
        poller = EmailPoller(
            protocol=email_config.protocol,
            host=email_config.host,
            port=email_config.port,
            username=email_config.username,
            password=email_config.password
        )
        
        # Create processor and handler
        processor = EmailProcessor(trigger_handler=trigger_handler)
        
        async def email_handler(email_msg):
            await processor.process_email(email_msg)
        
        poller.add_message_handler(email_handler)
        
        # Poll for messages
        messages = await poller.poll_once()
        
        # Verify results
        assert len(messages) == 1
        assert messages[0] == sample_message
        
        # Verify trigger handler was called
        trigger_handler.assert_called_once()
        
        # Verify trigger data
        call_args = trigger_handler.call_args[0]
        trigger_data = call_args[0]
        assert isinstance(trigger_data, TriggerData)
        assert trigger_data.source == 'email'
        assert trigger_data.data['email']['subject'] == 'Sales Inquiry'
        assert trigger_data.data['email']['sender'] == 'customer@example.com'