"""Integration tests for API endpoints."""

import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient

from main import app
from models.data_models import EmailMessage


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_webhook_request():
    """Sample webhook request data."""
    return {
        "source": "github",
        "data": {
            "action": "push",
            "repository": "test-repo",
            "commits": [
                {"id": "abc123", "message": "Test commit"}
            ]
        },
        "metadata": {
            "webhook_id": "wh_123",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    }


@pytest.fixture
def sample_email_request():
    """Sample email request data."""
    return {
        "subject": "Test Email Subject",
        "sender": "test@example.com",
        "recipient": "agent@company.com",
        "body": "This is a test email body with some content.",
        "headers": {
            "Message-ID": "<test123@example.com>",
            "X-Priority": "3"
        },
        "timestamp": "2024-01-01T12:00:00Z"
    }


@pytest.fixture
def sample_generic_request():
    """Sample generic trigger request data."""
    return {
        "trigger_type": "api_call",
        "data": {
            "user_id": "user123",
            "action": "create_account",
            "details": {
                "email": "newuser@example.com",
                "plan": "premium"
            }
        },
        "metadata": {
            "source_ip": "192.168.1.1",
            "user_agent": "TestClient/1.0"
        }
    }


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns correct information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "AI Agent Framework API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert "endpoints" in data
        assert "/api/trigger/webhook" in data["endpoints"]["webhook_trigger"]


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "components" in data
        assert "timestamp" in data


class TestWebhookEndpoint:
    """Test webhook trigger endpoint."""
    
    def test_webhook_trigger_success(self, client, sample_webhook_request):
        """Test successful webhook trigger."""
        response = client.post("/api/trigger/webhook", json=sample_webhook_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "github" in data["message"]
        assert "trigger_id" in data
        assert data["processing_time"] >= 0
        assert "timestamp" in data
    
    def test_webhook_trigger_missing_source(self, client):
        """Test webhook trigger with missing source."""
        invalid_request = {
            "data": {"test": "data"},
            "metadata": {}
        }
        
        response = client.post("/api/trigger/webhook", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    def test_webhook_trigger_empty_source(self, client):
        """Test webhook trigger with empty source."""
        invalid_request = {
            "source": "",
            "data": {"test": "data"},
            "metadata": {}
        }
        
        response = client.post("/api/trigger/webhook", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    def test_webhook_trigger_missing_data(self, client):
        """Test webhook trigger with missing data."""
        invalid_request = {
            "source": "test",
            "metadata": {}
        }
        
        response = client.post("/api/trigger/webhook", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    def test_webhook_trigger_with_minimal_data(self, client):
        """Test webhook trigger with minimal valid data."""
        minimal_request = {
            "source": "test",
            "data": {}
        }
        
        response = client.post("/api/trigger/webhook", json=minimal_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "test" in data["message"]


class TestEmailEndpoint:
    """Test email trigger endpoint."""
    
    def test_email_trigger_success(self, client, sample_email_request):
        """Test successful email trigger."""
        response = client.post("/api/trigger/email", json=sample_email_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "test@example.com" in data["message"]
        assert "trigger_id" in data
        assert data["processing_time"] >= 0
        assert "timestamp" in data
    
    def test_email_trigger_invalid_sender(self, client, sample_email_request):
        """Test email trigger with invalid sender email."""
        sample_email_request["sender"] = "invalid-email"
        
        response = client.post("/api/trigger/email", json=sample_email_request)
        assert response.status_code == 422  # Validation error
    
    def test_email_trigger_invalid_recipient(self, client, sample_email_request):
        """Test email trigger with invalid recipient email."""
        sample_email_request["recipient"] = "not-an-email"
        
        response = client.post("/api/trigger/email", json=sample_email_request)
        assert response.status_code == 422  # Validation error
    
    def test_email_trigger_empty_subject(self, client, sample_email_request):
        """Test email trigger with empty subject."""
        sample_email_request["subject"] = ""
        
        response = client.post("/api/trigger/email", json=sample_email_request)
        assert response.status_code == 422  # Validation error
    
    def test_email_trigger_empty_body(self, client, sample_email_request):
        """Test email trigger with empty body."""
        sample_email_request["body"] = ""
        
        response = client.post("/api/trigger/email", json=sample_email_request)
        assert response.status_code == 422  # Validation error
    
    def test_email_trigger_without_optional_fields(self, client):
        """Test email trigger without optional fields."""
        minimal_request = {
            "subject": "Test Subject",
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "body": "Test body content"
        }
        
        response = client.post("/api/trigger/email", json=minimal_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
    
    def test_email_trigger_with_complex_addresses(self, client):
        """Test email trigger with complex email addresses."""
        complex_request = {
            "subject": "Test Subject",
            "sender": "John Doe <john.doe@example.com>",
            "recipient": "Jane Smith <jane.smith@company.com>",
            "body": "Test body content"
        }
        
        response = client.post("/api/trigger/email", json=complex_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True


class TestGenericTriggerEndpoint:
    """Test generic trigger endpoint."""
    
    def test_generic_trigger_success(self, client, sample_generic_request):
        """Test successful generic trigger."""
        response = client.post("/api/trigger", json=sample_generic_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "api_call" in data["message"]
        assert "trigger_id" in data
        assert data["processing_time"] >= 0
        assert "timestamp" in data
    
    def test_generic_trigger_missing_type(self, client):
        """Test generic trigger with missing trigger_type."""
        invalid_request = {
            "data": {"test": "data"},
            "metadata": {}
        }
        
        response = client.post("/api/trigger", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    def test_generic_trigger_empty_type(self, client):
        """Test generic trigger with empty trigger_type."""
        invalid_request = {
            "trigger_type": "",
            "data": {"test": "data"},
            "metadata": {}
        }
        
        response = client.post("/api/trigger", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    def test_generic_trigger_minimal_data(self, client):
        """Test generic trigger with minimal data."""
        minimal_request = {
            "trigger_type": "test_trigger",
            "data": {}
        }
        
        response = client.post("/api/trigger", json=minimal_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post(
            "/api/trigger/webhook",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_content_type(self, client, sample_webhook_request):
        """Test handling of missing content type."""
        response = client.post(
            "/api/trigger/webhook",
            data=json.dumps(sample_webhook_request)
        )
        # FastAPI should handle this gracefully
        assert response.status_code in [200, 422]
    
    def test_nonexistent_endpoint(self, client):
        """Test handling of nonexistent endpoint."""
        response = client.post("/api/nonexistent")
        assert response.status_code == 404


class TestResponseFormat:
    """Test response format consistency."""
    
    def test_webhook_response_format(self, client, sample_webhook_request):
        """Test webhook response has correct format."""
        response = client.post("/api/trigger/webhook", json=sample_webhook_request)
        data = response.json()
        
        # Check required fields
        required_fields = ["success", "message", "trigger_id", "timestamp", "processing_time"]
        for field in required_fields:
            assert field in data
        
        # Check data types
        assert isinstance(data["success"], bool)
        assert isinstance(data["message"], str)
        assert isinstance(data["trigger_id"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["processing_time"], (int, float))
    
    def test_email_response_format(self, client, sample_email_request):
        """Test email response has correct format."""
        response = client.post("/api/trigger/email", json=sample_email_request)
        data = response.json()
        
        # Check required fields
        required_fields = ["success", "message", "trigger_id", "timestamp", "processing_time"]
        for field in required_fields:
            assert field in data
        
        # Check data types
        assert isinstance(data["success"], bool)
        assert isinstance(data["message"], str)
        assert isinstance(data["trigger_id"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["processing_time"], (int, float))
    
    def test_error_response_format(self, client):
        """Test error response has correct format."""
        invalid_request = {"source": "", "data": {}}
        response = client.post("/api/trigger/webhook", json=invalid_request)
        
        assert response.status_code == 422
        data = response.json()
        
        # FastAPI validation error format
        assert "detail" in data


class TestConcurrentRequests:
    """Test concurrent request handling."""
    
    def test_concurrent_webhook_requests(self, client, sample_webhook_request):
        """Test handling multiple concurrent webhook requests."""
        import concurrent.futures
        import threading
        
        def make_request():
            return client.post("/api/trigger/webhook", json=sample_webhook_request)
        
        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        
        # All trigger IDs should be unique
        trigger_ids = [response.json()["trigger_id"] for response in responses]
        assert len(set(trigger_ids)) == len(trigger_ids)


class TestDataNormalization:
    """Test data normalization and parsing."""
    
    def test_email_address_extraction(self, client):
        """Test email address extraction from complex formats."""
        test_cases = [
            {
                "sender": "John Doe <john@example.com>",
                "recipient": "jane@company.com"
            },
            {
                "sender": "user@domain.co.uk",
                "recipient": "Support Team <support@company.org>"
            }
        ]
        
        for case in test_cases:
            request_data = {
                "subject": "Test",
                "sender": case["sender"],
                "recipient": case["recipient"],
                "body": "Test body"
            }
            
            response = client.post("/api/trigger/email", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["success"] is True
    
    def test_whitespace_normalization(self, client):
        """Test whitespace normalization in text fields."""
        request_data = {
            "subject": "  Test   Subject  ",
            "sender": "test@example.com",
            "recipient": "recipient@example.com",
            "body": "  This is a test   body with   extra spaces  "
        }
        
        response = client.post("/api/trigger/email", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True