"""Tests for email parsing utilities."""

import pytest
from datetime import datetime

from utils.email_parser import EmailParser
from models.data_models import EmailMessage, Attachment


class TestEmailParser:
    """Test EmailParser functionality."""
    
    def test_parse_email_dict_basic(self):
        """Test parsing basic email dictionary."""
        email_data = {
            "subject": "Test Subject",
            "sender": "test@example.com",
            "recipient": "recipient@example.com",
            "body": "This is a test email body."
        }
        
        email_msg = EmailParser.parse_email_dict(email_data)
        
        assert email_msg.subject == "Test Subject"
        assert email_msg.sender == "test@example.com"
        assert email_msg.recipient == "recipient@example.com"
        assert email_msg.body == "This is a test email body."
        assert email_msg.headers == {}
        assert email_msg.attachments == []
        assert email_msg.timestamp is None
    
    def test_parse_email_dict_with_headers(self):
        """Test parsing email dictionary with headers."""
        email_data = {
            "subject": "Test Subject",
            "sender": "test@example.com",
            "recipient": "recipient@example.com",
            "body": "Test body",
            "headers": {
                "Message-ID": "<test123@example.com>",
                "X-Priority": "3"
            }
        }
        
        email_msg = EmailParser.parse_email_dict(email_data)
        
        assert email_msg.headers["Message-ID"] == "<test123@example.com>"
        assert email_msg.headers["X-Priority"] == "3"
    
    def test_parse_email_dict_with_timestamp_string(self):
        """Test parsing email dictionary with timestamp as string."""
        email_data = {
            "subject": "Test Subject",
            "sender": "test@example.com",
            "recipient": "recipient@example.com",
            "body": "Test body",
            "timestamp": "2024-01-01T12:00:00"
        }
        
        email_msg = EmailParser.parse_email_dict(email_data)
        
        assert email_msg.timestamp is not None
        assert email_msg.timestamp.year == 2024
        assert email_msg.timestamp.month == 1
        assert email_msg.timestamp.day == 1
    
    def test_parse_email_dict_with_timestamp_datetime(self):
        """Test parsing email dictionary with timestamp as datetime."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        email_data = {
            "subject": "Test Subject",
            "sender": "test@example.com",
            "recipient": "recipient@example.com",
            "body": "Test body",
            "timestamp": timestamp
        }
        
        email_msg = EmailParser.parse_email_dict(email_data)
        
        assert email_msg.timestamp == timestamp
    
    def test_parse_email_dict_missing_required_fields(self):
        """Test parsing email dictionary with missing required fields."""
        # Missing subject
        email_data = {
            "sender": "test@example.com",
            "recipient": "recipient@example.com",
            "body": "Test body"
        }
        
        with pytest.raises(ValueError, match="Missing required email fields"):
            EmailParser.parse_email_dict(email_data)
        
        # Missing sender
        email_data = {
            "subject": "Test Subject",
            "recipient": "recipient@example.com",
            "body": "Test body"
        }
        
        with pytest.raises(ValueError, match="Missing required email fields"):
            EmailParser.parse_email_dict(email_data)
    
    def test_parse_email_dict_alternative_field_names(self):
        """Test parsing email dictionary with alternative field names."""
        email_data = {
            "subject": "Test Subject",
            "from": "test@example.com",  # Alternative to 'sender'
            "to": "recipient@example.com",  # Alternative to 'recipient'
            "content": "Test body content"  # Alternative to 'body'
        }
        
        email_msg = EmailParser.parse_email_dict(email_data)
        
        assert email_msg.sender == "test@example.com"
        assert email_msg.recipient == "recipient@example.com"
        assert email_msg.body == "Test body content"
    
    def test_normalize_email_message(self):
        """Test email message normalization."""
        email_msg = EmailMessage(
            subject="  Test   Subject  ",
            sender="John Doe <john@example.com>",
            recipient="  jane@company.com  ",
            body="  This is a test   body with   extra spaces  ",
            headers={},
            attachments=[]
        )
        
        normalized = EmailParser.normalize_email_message(email_msg)
        
        assert normalized.subject == "Test Subject"
        assert normalized.sender == "john@example.com"
        assert normalized.recipient == "jane@company.com"
        assert "extra spaces" in normalized.body
        # Should normalize multiple spaces to single spaces
        assert "   " not in normalized.body
    
    def test_extract_email_address_simple(self):
        """Test extracting simple email addresses."""
        assert EmailParser._extract_email_address("test@example.com") == "test@example.com"
        assert EmailParser._extract_email_address("  user@domain.org  ") == "user@domain.org"
    
    def test_extract_email_address_with_name(self):
        """Test extracting email addresses with names."""
        assert EmailParser._extract_email_address("John Doe <john@example.com>") == "john@example.com"
        assert EmailParser._extract_email_address("Jane Smith <jane.smith@company.org>") == "jane.smith@company.org"
        assert EmailParser._extract_email_address("Support Team <support@help.com>") == "support@help.com"
    
    def test_extract_email_address_malformed(self):
        """Test extracting email addresses from malformed input."""
        # Should return the original input if no valid email found
        assert EmailParser._extract_email_address("not-an-email") == "not-an-email"
        assert EmailParser._extract_email_address("") == ""
        assert EmailParser._extract_email_address("John Doe") == "John Doe"
    
    def test_normalize_text(self):
        """Test text normalization."""
        # Test whitespace normalization
        assert EmailParser._normalize_text("  hello   world  ") == "hello world"
        assert EmailParser._normalize_text("line1\n\nline2") == "line1 line2"
        
        # Test soft line break removal
        assert EmailParser._normalize_text("word1=\nword2") == "word1word2"
        assert EmailParser._normalize_text("word1=\r\nword2") == "word1word2"
        
        # Test line ending normalization (converts to single space)
        assert EmailParser._normalize_text("line1\r\nline2") == "line1 line2"
        
        # Test empty input
        assert EmailParser._normalize_text("") == ""
        assert EmailParser._normalize_text(None) == ""
    
    def test_decode_header(self):
        """Test header decoding."""
        # Test simple header
        assert EmailParser._decode_header("Simple Subject") == "Simple Subject"
        
        # Test empty header
        assert EmailParser._decode_header("") == ""
        assert EmailParser._decode_header(None) == ""
        
        # Test header with extra whitespace
        assert EmailParser._decode_header("  Subject  ") == "Subject"
    
    def test_html_to_text(self):
        """Test HTML to text conversion."""
        # Test simple HTML
        html = "<p>Hello <b>world</b>!</p>"
        text = EmailParser._html_to_text(html)
        assert text == "Hello world!"
        
        # Test HTML entities
        html = "Hello&nbsp;world&lt;test&gt;&amp;more"
        text = EmailParser._html_to_text(html)
        assert text == "Hello world<test>&more"
        
        # Test complex HTML
        html = "<div><h1>Title</h1><p>Paragraph with <a href='#'>link</a></p></div>"
        text = EmailParser._html_to_text(html)
        assert "Title" in text
        assert "Paragraph" in text
        assert "link" in text
        assert "<" not in text  # No HTML tags should remain
    
    def test_parse_raw_email_simple(self):
        """Test parsing simple raw email."""
        raw_email = """From: test@example.com
To: recipient@example.com
Subject: Test Subject
Date: Mon, 1 Jan 2024 12:00:00 +0000

This is the email body.
"""
        
        email_msg = EmailParser.parse_raw_email(raw_email)
        
        assert email_msg.subject == "Test Subject"
        assert email_msg.sender == "test@example.com"
        assert email_msg.recipient == "recipient@example.com"
        assert "email body" in email_msg.body
        assert email_msg.timestamp is not None
    
    def test_parse_raw_email_with_headers(self):
        """Test parsing raw email with various headers."""
        raw_email = """From: John Doe <john@example.com>
To: Jane Smith <jane@company.com>
Subject: Important Message
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test123@example.com>
X-Priority: 1

This is an important email message.
"""
        
        email_msg = EmailParser.parse_raw_email(raw_email)
        
        assert email_msg.sender == "john@example.com"
        assert email_msg.recipient == "jane@company.com"
        assert email_msg.headers["Message-ID"] == "<test123@example.com>"
        assert email_msg.headers["X-Priority"] == "1"
    
    def test_parse_raw_email_invalid(self):
        """Test parsing invalid raw email."""
        with pytest.raises(ValueError, match="Invalid email format"):
            EmailParser.parse_raw_email("This is not a valid email")
    
    def test_parse_raw_email_multipart(self):
        """Test parsing multipart raw email."""
        raw_email = """From: test@example.com
To: recipient@example.com
Subject: Multipart Test
Date: Mon, 1 Jan 2024 12:00:00 +0000
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain

This is the plain text part.

--boundary123
Content-Type: text/html

<p>This is the HTML part.</p>

--boundary123--
"""
        
        email_msg = EmailParser.parse_raw_email(raw_email)
        
        assert email_msg.subject == "Multipart Test"
        assert "plain text part" in email_msg.body
        # Should prefer plain text over HTML
        assert "<p>" not in email_msg.body


class TestEmailParserEdgeCases:
    """Test edge cases for EmailParser."""
    
    def test_parse_email_dict_with_attachments(self):
        """Test parsing email dictionary with attachments."""
        email_data = {
            "subject": "Test Subject",
            "sender": "test@example.com",
            "recipient": "recipient@example.com",
            "body": "Test body",
            "attachments": [
                {
                    "filename": "test.txt",
                    "content_type": "text/plain",
                    "size": 100
                }
            ]
        }
        
        email_msg = EmailParser.parse_email_dict(email_data)
        
        assert len(email_msg.attachments) == 1
        assert email_msg.attachments[0].filename == "test.txt"
        assert email_msg.attachments[0].content_type == "text/plain"
        assert email_msg.attachments[0].size == 100
    
    def test_normalize_email_message_with_error(self):
        """Test email message normalization when normalization fails."""
        # Create an email message that might cause normalization issues
        email_msg = EmailMessage(
            subject="Test",
            sender="test@example.com",
            recipient="recipient@example.com",
            body="Test body",
            headers={},
            attachments=[]
        )
        
        # Should return the original message if normalization fails
        normalized = EmailParser.normalize_email_message(email_msg)
        assert normalized.subject == "Test"
    
    def test_parse_email_dict_with_invalid_timestamp(self):
        """Test parsing email dictionary with invalid timestamp."""
        email_data = {
            "subject": "Test Subject",
            "sender": "test@example.com",
            "recipient": "recipient@example.com",
            "body": "Test body",
            "timestamp": "invalid-timestamp"
        }
        
        # Should not raise an error, just set timestamp to None
        email_msg = EmailParser.parse_email_dict(email_data)
        assert email_msg.timestamp is None
    
    def test_extract_email_address_unicode(self):
        """Test extracting email addresses with unicode characters."""
        # Should handle unicode in names
        result = EmailParser._extract_email_address("José García <jose@example.com>")
        assert result == "jose@example.com"
        
        # Should handle unicode domains (though not common in practice)
        result = EmailParser._extract_email_address("test@münchen.de")
        assert "test@" in result