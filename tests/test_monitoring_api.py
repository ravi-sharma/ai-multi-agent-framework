"""Tests for monitoring API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from monitoring import (
    ComponentHealth,
    HealthStatus,
    PerformanceMetrics,
    MonitoringDashboard
)


@pytest.fixture
def mock_health_checker():
    """Mock health checker for testing."""
    mock_checker = MagicMock()
    mock_checker._health_checks = {"test_component": AsyncMock()}
    
    # Mock overall health
    mock_checker.get_overall_health.return_value = {
        "status": HealthStatus.HEALTHY.value,
        "message": "All components are healthy",
        "component_count": 1,
        "healthy_count": 1,
        "degraded_count": 0,
        "unhealthy_count": 0,
        "unknown_count": 0,
        "components": {
            "test_component": {
                "name": "test_component",
                "status": HealthStatus.HEALTHY.value,
                "message": "Component is healthy",
                "last_check": "2023-01-01T00:00:00",
                "response_time": 0.1,
                "metadata": {},
                "error_count": 0,
                "consecutive_failures": 0
            }
        },
        "last_check": "2023-01-01T00:00:00"
    }
    
    # Mock component health check
    async def mock_check_component_health(component_name):
        if component_name == "test_component":
            return ComponentHealth(
                name="test_component",
                status=HealthStatus.HEALTHY,
                message="Component is healthy"
            )
        else:
            raise KeyError(f"Component '{component_name}' not found")
    
    mock_checker.check_component_health = mock_check_component_health
    
    # Mock check all components
    async def mock_check_all_components():
        return {
            "test_component": ComponentHealth(
                name="test_component",
                status=HealthStatus.HEALTHY,
                message="Component is healthy"
            )
        }
    
    mock_checker.check_all_components = mock_check_all_components
    
    return mock_checker


@pytest.fixture
def mock_metrics_collector():
    """Mock metrics collector for testing."""
    mock_collector = MagicMock()
    
    # Mock performance metrics
    test_metrics = PerformanceMetrics()
    test_metrics.total_requests = 100
    test_metrics.successful_requests = 95
    test_metrics.failed_requests = 5
    test_metrics.avg_execution_time = 0.5
    test_metrics.success_rate = 95.0
    test_metrics.error_rate = 5.0
    
    mock_collector.get_performance_metrics.return_value = {
        "test_component.test_operation": test_metrics
    }
    
    # Mock metrics summary
    mock_collector.get_metrics_summary.return_value = {
        "uptime_seconds": 3600,
        "total_requests": 100,
        "total_successes": 95,
        "total_failures": 5,
        "overall_success_rate": 95.0,
        "overall_error_rate": 5.0,
        "component_metrics": {
            "test_component.test_operation": test_metrics.to_dict()
        },
        "counters": {"test_counter": 10},
        "gauges": {"test_gauge": 42.0},
        "histogram_count": 1,
        "last_updated": "2023-01-01T00:00:00"
    }
    
    return mock_collector


@pytest.fixture
def mock_dashboard():
    """Mock monitoring dashboard for testing."""
    mock_dashboard = MagicMock()
    
    # Mock performance summary
    mock_dashboard.get_performance_summary.return_value = {
        "total_requests": 100,
        "overall_success_rate": 95.0,
        "overall_error_rate": 5.0,
        "uptime_seconds": 3600,
        "requests_per_second": 0.028,
        "avg_response_time": 0.5,
        "slowest_components": [
            {"name": "slow_component", "avg_response_time": 2.0, "total_requests": 10, "success_rate": 90.0}
        ],
        "fastest_components": [
            {"name": "fast_component", "avg_response_time": 0.1, "total_requests": 50, "success_rate": 99.0}
        ]
    }
    
    # Mock error summary
    mock_dashboard.get_error_summary.return_value = {
        "total_errors": 5,
        "time_period_hours": 24,
        "errors_by_type": {"ValueError": 3, "TypeError": 2},
        "errors_by_component": {"test_component": 5},
        "recent_errors": [
            {
                "timestamp": "2023-01-01T00:00:00",
                "component": "test_component",
                "operation": "test_operation",
                "error_type": "ValueError",
                "error_message": "Test error",
                "metadata": {}
            }
        ]
    }
    
    # Mock dashboard data collection
    from monitoring.dashboard import DashboardData
    mock_dashboard_data = DashboardData()
    mock_dashboard_data.uptime_seconds = 3600
    mock_dashboard_data.overall_health = {
        "status": HealthStatus.HEALTHY.value,
        "message": "All components are healthy"
    }
    
    async def mock_collect_dashboard_data():
        return mock_dashboard_data
    
    mock_dashboard.collect_dashboard_data = mock_collect_dashboard_data
    
    return mock_dashboard


class TestMonitoringEndpoints:
    """Test monitoring API endpoints."""
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_health_checker')
    def test_health_check_endpoint(self, mock_get_health_checker, mock_health_checker):
        """Test the main health check endpoint."""
        from main import app
        
        mock_get_health_checker.return_value = mock_health_checker
        
        client = TestClient(app)
        response = client.get("/api/monitoring/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == HealthStatus.HEALTHY.value
        assert data["component_count"] == 1
        assert data["healthy_count"] == 1
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_health_checker')
    def test_component_health_check_endpoint(self, mock_get_health_checker, mock_health_checker):
        """Test component-specific health check endpoint."""
        from main import app
        
        mock_get_health_checker.return_value = mock_health_checker
        
        client = TestClient(app)
        response = client.get("/api/monitoring/health/test_component")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_component"
        assert data["status"] == HealthStatus.HEALTHY.value
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_health_checker')
    def test_component_health_check_not_found(self, mock_get_health_checker, mock_health_checker):
        """Test component health check for non-existent component."""
        from main import app
        
        mock_get_health_checker.return_value = mock_health_checker
        
        client = TestClient(app)
        response = client.get("/api/monitoring/health/nonexistent_component")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_metrics_collector')
    def test_metrics_endpoint_json(self, mock_get_metrics_collector, mock_metrics_collector):
        """Test metrics endpoint with JSON format."""
        from main import app
        
        mock_get_metrics_collector.return_value = mock_metrics_collector
        
        client = TestClient(app)
        response = client.get("/api/monitoring/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 100
        assert data["overall_success_rate"] == 95.0
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_metrics_collector')
    def test_metrics_endpoint_with_component_filter(self, mock_get_metrics_collector, mock_metrics_collector):
        """Test metrics endpoint with component filter."""
        from main import app
        
        mock_get_metrics_collector.return_value = mock_metrics_collector
        
        client = TestClient(app)
        response = client.get("/api/monitoring/metrics?component=test_component")
        
        assert response.status_code == 200
        data = response.json()
        assert "test_component.test_operation" in data
    
    @patch('ai_agent_framework.api.monitoring_endpoints.dashboard')
    def test_performance_summary_endpoint(self, mock_dashboard_instance, mock_dashboard):
        """Test performance summary endpoint."""
        from main import app
        
        mock_dashboard_instance.get_performance_summary = mock_dashboard.get_performance_summary
        
        client = TestClient(app)
        response = client.get("/api/monitoring/metrics/performance")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 100
        assert data["overall_success_rate"] == 95.0
        assert len(data["fastest_components"]) > 0
    
    @patch('ai_agent_framework.api.monitoring_endpoints.dashboard')
    def test_error_summary_endpoint(self, mock_dashboard_instance, mock_dashboard):
        """Test error summary endpoint."""
        from main import app
        
        mock_dashboard_instance.get_error_summary = mock_dashboard.get_error_summary
        
        client = TestClient(app)
        response = client.get("/api/monitoring/errors")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_errors"] == 5
        assert "errors_by_type" in data
        assert "errors_by_component" in data
    
    @patch('ai_agent_framework.api.monitoring_endpoints.dashboard')
    def test_error_summary_with_custom_hours(self, mock_dashboard_instance, mock_dashboard):
        """Test error summary endpoint with custom time period."""
        from main import app
        
        mock_dashboard_instance.get_error_summary = mock_dashboard.get_error_summary
        
        client = TestClient(app)
        response = client.get("/api/monitoring/errors?hours=48")
        
        assert response.status_code == 200
        # Verify the mock was called with the correct parameter
        mock_dashboard.get_error_summary.assert_called_with(48)
    
    @patch('ai_agent_framework.api.monitoring_endpoints.dashboard')
    def test_dashboard_endpoint(self, mock_dashboard_instance, mock_dashboard):
        """Test dashboard data endpoint."""
        from main import app
        
        mock_dashboard_instance.collect_dashboard_data = mock_dashboard.collect_dashboard_data
        
        client = TestClient(app)
        response = client.get("/api/monitoring/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "overall_health" in data
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_health_checker')
    def test_trigger_health_check_endpoint(self, mock_get_health_checker, mock_health_checker):
        """Test trigger health check endpoint."""
        from main import app
        
        mock_get_health_checker.return_value = mock_health_checker
        
        client = TestClient(app)
        response = client.post("/api/monitoring/health/check")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Health check completed"
        assert "overall_health" in data
        assert "component_results" in data
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_metrics_collector')
    def test_reset_metrics_endpoint(self, mock_get_metrics_collector, mock_metrics_collector):
        """Test reset metrics endpoint."""
        from main import app
        
        mock_get_metrics_collector.return_value = mock_metrics_collector
        
        client = TestClient(app)
        response = client.post("/api/monitoring/metrics/reset")
        
        assert response.status_code == 200
        data = response.json()
        assert "reset" in data["message"].lower()
        mock_metrics_collector.reset_metrics.assert_called_once_with(None)
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_metrics_collector')
    def test_reset_metrics_with_component(self, mock_get_metrics_collector, mock_metrics_collector):
        """Test reset metrics endpoint with specific component."""
        from main import app
        
        mock_get_metrics_collector.return_value = mock_metrics_collector
        
        client = TestClient(app)
        response = client.post("/api/monitoring/metrics/reset?component=test_component")
        
        assert response.status_code == 200
        mock_metrics_collector.reset_metrics.assert_called_once_with("test_component")
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_health_checker')
    @patch('ai_agent_framework.api.monitoring_endpoints.get_metrics_collector')
    def test_system_status_endpoint(self, mock_get_metrics_collector, mock_get_health_checker, 
                                   mock_metrics_collector, mock_health_checker):
        """Test system status endpoint."""
        from main import app
        
        mock_get_health_checker.return_value = mock_health_checker
        mock_get_metrics_collector.return_value = mock_metrics_collector
        
        client = TestClient(app)
        response = client.get("/api/monitoring/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "health" in data
        assert "performance" in data
        assert data["health"]["overall_status"] == HealthStatus.HEALTHY.value
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_metrics_collector')
    def test_prometheus_metrics_format(self, mock_get_metrics_collector, mock_metrics_collector):
        """Test metrics endpoint with Prometheus format."""
        from main import app
        
        mock_get_metrics_collector.return_value = mock_metrics_collector
        
        client = TestClient(app)
        response = client.get("/api/monitoring/metrics?format=prometheus")
        
        assert response.status_code == 200
        # Should return text content for Prometheus format
        content = response.text
        assert "ai_agent_requests_total" in content
        assert "ai_agent_success_rate" in content


class TestMonitoringEndpointErrors:
    """Test error handling in monitoring endpoints."""
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_health_checker')
    def test_health_check_endpoint_error(self, mock_get_health_checker):
        """Test health check endpoint error handling."""
        from main import app
        
        # Mock health checker to raise an exception
        mock_health_checker = MagicMock()
        mock_health_checker.get_overall_health.side_effect = Exception("Health check failed")
        mock_get_health_checker.return_value = mock_health_checker
        
        client = TestClient(app)
        response = client.get("/api/monitoring/health")
        
        assert response.status_code == 500
        data = response.json()
        assert "Health check failed" in data["detail"]
    
    @patch('ai_agent_framework.api.monitoring_endpoints.get_metrics_collector')
    def test_metrics_endpoint_error(self, mock_get_metrics_collector):
        """Test metrics endpoint error handling."""
        from main import app
        
        # Mock metrics collector to raise an exception
        mock_metrics_collector = MagicMock()
        mock_metrics_collector.get_metrics_summary.side_effect = Exception("Metrics collection failed")
        mock_get_metrics_collector.return_value = mock_metrics_collector
        
        client = TestClient(app)
        response = client.get("/api/monitoring/metrics")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve metrics" in data["detail"]
    
    def test_error_summary_invalid_hours(self):
        """Test error summary endpoint with invalid hours parameter."""
        from main import app
        
        client = TestClient(app)
        response = client.get("/api/monitoring/errors?hours=0")
        
        # Should return validation error for hours < 1
        assert response.status_code == 422
    
    def test_error_summary_too_many_hours(self):
        """Test error summary endpoint with too many hours."""
        from main import app
        
        client = TestClient(app)
        response = client.get("/api/monitoring/errors?hours=200")
        
        # Should return validation error for hours > 168
        assert response.status_code == 422


class TestMonitoringIntegration:
    """Integration tests for monitoring endpoints."""
    
    def test_monitoring_endpoints_in_main_app(self):
        """Test that monitoring endpoints are properly included in main app."""
        from main import app
        
        # Check that monitoring routes are included
        routes = [route.path for route in app.routes]
        
        monitoring_routes = [
            "/api/monitoring/health",
            "/api/monitoring/metrics",
            "/api/monitoring/dashboard",
            "/api/monitoring/status"
        ]
        
        for route in monitoring_routes:
            assert any(route in r for r in routes), f"Route {route} not found in app routes"
    
    def test_cors_headers_on_monitoring_endpoints(self):
        """Test that CORS headers are properly set on monitoring endpoints."""
        from main import app
        
        client = TestClient(app)
        response = client.options("/api/monitoring/health")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers