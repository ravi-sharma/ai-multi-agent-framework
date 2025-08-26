"""Tests for monitoring and logging functionality."""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from monitoring import (
    StructuredLogger,
    get_logger,
    setup_logging,
    MetricsCollector,
    PerformanceMetrics,
    get_metrics_collector,
    HealthChecker,
    ComponentHealth,
    HealthStatus,
    get_health_checker,
    MonitoringDashboard,
    MetricsTimer
)


class TestStructuredLogger:
    """Test structured logging functionality."""
    
    def test_logger_creation(self):
        """Test logger creation and configuration."""
        logger = StructuredLogger("test_logger")
        assert logger.logger.name == "test_logger"
        assert len(logger.logger.handlers) > 0
    
    def test_correlation_id_management(self):
        """Test correlation ID setting and retrieval."""
        logger = StructuredLogger("test_logger")
        
        # Test setting correlation ID
        corr_id = logger.set_correlation_id("test-123")
        assert corr_id == "test-123"
        assert logger.get_correlation_id() == "test-123"
        
        # Test auto-generation
        auto_id = logger.set_correlation_id()
        assert auto_id is not None
        assert len(auto_id) > 0
        assert logger.get_correlation_id() == auto_id
        
        # Test clearing
        logger.clear_correlation_id()
        assert logger.get_correlation_id() is None
    
    def test_structured_logging_methods(self):
        """Test structured logging methods with extra fields."""
        logger = StructuredLogger("test_logger")
        logger.set_correlation_id("test-123")
        
        # Test logging with extra fields
        with patch.object(logger.logger, 'info') as mock_info:
            logger.info("Test message", component="test", operation="test_op")
            mock_info.assert_called_once_with(
                "Test message", 
                extra={"component": "test", "operation": "test_op"}
            )
    
    def test_agent_execution_logging(self):
        """Test agent execution logging."""
        logger = StructuredLogger("test_logger")
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.log_agent_execution(
                agent_name="test_agent",
                operation="process",
                status="success",
                execution_time=1.5,
                input_data_size=100,
                output_data_size=200
            )
            
            mock_info.assert_called_once()
            args, kwargs = mock_info.call_args
            assert "Agent execution: test_agent.process" in args[0]
            assert kwargs["extra"]["agent_name"] == "test_agent"
            assert kwargs["extra"]["execution_time"] == 1.5
    
    def test_api_request_logging(self):
        """Test API request logging."""
        logger = StructuredLogger("test_logger")
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.log_api_request(
                method="POST",
                path="/api/test",
                status_code=200,
                response_time=0.5,
                user_agent="test-agent"
            )
            
            mock_info.assert_called_once()
            args, kwargs = mock_info.call_args
            assert "API request: POST /api/test" in args[0]
            assert kwargs["extra"]["status_code"] == 200
    
    def test_error_logging_with_context(self):
        """Test error logging with contextual information."""
        logger = StructuredLogger("test_logger")
        
        with patch.object(logger.logger, 'error') as mock_error:
            test_error = ValueError("Test error")
            logger.log_error_with_context(
                error=test_error,
                component="test_component",
                operation="test_operation",
                context={"key": "value"}
            )
            
            mock_error.assert_called_once()
            args, kwargs = mock_error.call_args
            assert "Error in test_component.test_operation" in args[0]
            assert kwargs["extra"]["error_type"] == "ValueError"
            assert kwargs["extra"]["context"] == {"key": "value"}


class TestMetricsCollector:
    """Test metrics collection functionality."""
    
    def test_metrics_collector_creation(self):
        """Test metrics collector creation."""
        collector = MetricsCollector()
        assert collector.max_history_size == 1000
        assert len(collector._metrics) == 0
    
    def test_execution_recording(self):
        """Test recording execution metrics."""
        collector = MetricsCollector()
        
        # Record successful execution
        collector.record_execution("test_component", "test_op", 1.5, True)
        
        metrics = collector.get_performance_metrics()
        assert "test_component.test_op" in metrics
        
        component_metrics = metrics["test_component.test_op"]
        assert component_metrics.total_requests == 1
        assert component_metrics.successful_requests == 1
        assert component_metrics.failed_requests == 0
        assert component_metrics.avg_execution_time == 1.5
        assert component_metrics.success_rate == 100.0
    
    def test_multiple_executions(self):
        """Test recording multiple executions."""
        collector = MetricsCollector()
        
        # Record multiple executions
        collector.record_execution("test_component", "test_op", 1.0, True)
        collector.record_execution("test_component", "test_op", 2.0, True)
        collector.record_execution("test_component", "test_op", 3.0, False)
        
        metrics = collector.get_performance_metrics()
        component_metrics = metrics["test_component.test_op"]
        
        assert component_metrics.total_requests == 3
        assert component_metrics.successful_requests == 2
        assert component_metrics.failed_requests == 1
        assert component_metrics.avg_execution_time == 2.0
        assert component_metrics.success_rate == pytest.approx(66.67, rel=1e-2)
        assert component_metrics.error_rate == pytest.approx(33.33, rel=1e-2)
    
    def test_counter_operations(self):
        """Test counter metric operations."""
        collector = MetricsCollector()
        
        # Increment counters
        collector.increment_counter("test_counter")
        collector.increment_counter("test_counter", value=5.0)
        collector.increment_counter("test_counter_with_labels", labels={"env": "test"})
        
        assert collector.get_counter("test_counter") == 6.0
        assert collector.get_counter("test_counter_with_labels", {"env": "test"}) == 1.0
        assert collector.get_counter("nonexistent_counter") == 0.0
    
    def test_gauge_operations(self):
        """Test gauge metric operations."""
        collector = MetricsCollector()
        
        # Set gauges
        collector.set_gauge("test_gauge", 42.5)
        collector.set_gauge("test_gauge_with_labels", 100.0, {"env": "test"})
        
        assert collector.get_gauge("test_gauge") == 42.5
        assert collector.get_gauge("test_gauge_with_labels", {"env": "test"}) == 100.0
        assert collector.get_gauge("nonexistent_gauge") is None
    
    def test_histogram_operations(self):
        """Test histogram metric operations."""
        collector = MetricsCollector()
        
        # Record histogram values
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        for value in values:
            collector.record_histogram("test_histogram", value)
        
        stats = collector.get_histogram_stats("test_histogram")
        assert stats["count"] == 10
        assert stats["min"] == 1.0
        assert stats["max"] == 10.0
        assert stats["avg"] == 5.5
        assert stats["p50"] == 5.0
        assert stats["p90"] == 9.0
    
    def test_metrics_summary(self):
        """Test metrics summary generation."""
        collector = MetricsCollector()
        
        # Record some metrics
        collector.record_execution("component1", "op1", 1.0, True)
        collector.record_execution("component1", "op2", 2.0, False)
        collector.record_execution("component2", "op1", 1.5, True)
        
        summary = collector.get_metrics_summary()
        
        assert summary["total_requests"] == 3
        assert summary["total_successes"] == 2
        assert summary["total_failures"] == 1
        assert summary["overall_success_rate"] == pytest.approx(66.67, rel=1e-2)
        assert "component_metrics" in summary
        assert "uptime_seconds" in summary
    
    def test_metrics_reset(self):
        """Test metrics reset functionality."""
        collector = MetricsCollector()
        
        # Record some metrics
        collector.record_execution("component1", "op1", 1.0, True)
        collector.increment_counter("test_counter")
        collector.set_gauge("test_gauge", 42.0)
        
        # Reset specific component
        collector.reset_metrics("component1")
        
        metrics = collector.get_performance_metrics()
        assert "component1.op1" not in metrics
        assert collector.get_counter("test_counter") == 1.0  # Should remain
        
        # Reset all metrics
        collector.reset_metrics()
        
        assert len(collector.get_performance_metrics()) == 0
        assert collector.get_counter("test_counter") == 0.0


class TestMetricsTimer:
    """Test metrics timer context manager."""
    
    def test_successful_timing(self):
        """Test successful operation timing."""
        collector = MetricsCollector()
        
        with MetricsTimer(collector, "test_component", "test_op"):
            time.sleep(0.1)  # Simulate work
        
        metrics = collector.get_performance_metrics()
        component_metrics = metrics["test_component.test_op"]
        
        assert component_metrics.total_requests == 1
        assert component_metrics.successful_requests == 1
        assert component_metrics.avg_execution_time >= 0.1
    
    def test_failed_timing(self):
        """Test failed operation timing."""
        collector = MetricsCollector()
        
        try:
            with MetricsTimer(collector, "test_component", "test_op"):
                time.sleep(0.1)
                raise ValueError("Test error")
        except ValueError:
            pass
        
        metrics = collector.get_performance_metrics()
        component_metrics = metrics["test_component.test_op"]
        
        assert component_metrics.total_requests == 1
        assert component_metrics.failed_requests == 1
        assert component_metrics.avg_execution_time >= 0.1
    
    def test_manual_failure_marking(self):
        """Test manual failure marking."""
        collector = MetricsCollector()
        
        with MetricsTimer(collector, "test_component", "test_op") as timer:
            timer.mark_failure()
        
        metrics = collector.get_performance_metrics()
        component_metrics = metrics["test_component.test_op"]
        
        assert component_metrics.total_requests == 1
        assert component_metrics.failed_requests == 1


class TestHealthChecker:
    """Test health checking functionality."""
    
    @pytest.fixture
    def health_checker(self):
        """Create a health checker for testing."""
        return HealthChecker(check_interval=1)
    
    async def test_health_check_registration(self, health_checker):
        """Test health check registration."""
        async def test_health_check():
            return ComponentHealth(
                name="test_component",
                status=HealthStatus.HEALTHY,
                message="All good"
            )
        
        health_checker.register_health_check("test_component", test_health_check)
        
        assert "test_component" in health_checker._health_checks
        assert "test_component" in health_checker._component_health
    
    async def test_component_health_check(self, health_checker):
        """Test individual component health check."""
        async def test_health_check():
            return ComponentHealth(
                name="test_component",
                status=HealthStatus.HEALTHY,
                message="Component is healthy"
            )
        
        health_checker.register_health_check("test_component", test_health_check)
        
        health = await health_checker.check_component_health("test_component")
        
        assert health.name == "test_component"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "Component is healthy"
        assert health.response_time > 0
    
    async def test_failing_health_check(self, health_checker):
        """Test failing health check."""
        async def failing_health_check():
            raise Exception("Health check failed")
        
        health_checker.register_health_check("failing_component", failing_health_check)
        
        health = await health_checker.check_component_health("failing_component")
        
        assert health.name == "failing_component"
        assert health.status == HealthStatus.UNHEALTHY
        assert "Health check failed" in health.message
        assert health.consecutive_failures == 1
    
    async def test_all_components_health_check(self, health_checker):
        """Test checking all components."""
        async def healthy_check():
            return ComponentHealth(
                name="healthy_component",
                status=HealthStatus.HEALTHY,
                message="Healthy"
            )
        
        async def unhealthy_check():
            return ComponentHealth(
                name="unhealthy_component",
                status=HealthStatus.UNHEALTHY,
                message="Unhealthy"
            )
        
        health_checker.register_health_check("healthy_component", healthy_check)
        health_checker.register_health_check("unhealthy_component", unhealthy_check)
        
        results = await health_checker.check_all_components()
        
        assert len(results) == 2
        assert results["healthy_component"].status == HealthStatus.HEALTHY
        assert results["unhealthy_component"].status == HealthStatus.UNHEALTHY
    
    async def test_overall_health_summary(self, health_checker):
        """Test overall health summary."""
        async def healthy_check():
            return ComponentHealth(
                name="healthy_component",
                status=HealthStatus.HEALTHY,
                message="Healthy"
            )
        
        async def degraded_check():
            return ComponentHealth(
                name="degraded_component",
                status=HealthStatus.DEGRADED,
                message="Degraded"
            )
        
        health_checker.register_health_check("healthy_component", healthy_check)
        health_checker.register_health_check("degraded_component", degraded_check)
        
        # Run health checks
        await health_checker.check_all_components()
        
        overall = health_checker.get_overall_health()
        
        assert overall["status"] == HealthStatus.DEGRADED.value
        assert overall["component_count"] == 2
        assert overall["healthy_count"] == 1
        assert overall["degraded_count"] == 1
        assert overall["unhealthy_count"] == 0
    
    async def test_periodic_health_checks(self, health_checker):
        """Test periodic health checks."""
        check_count = 0
        
        async def counting_health_check():
            nonlocal check_count
            check_count += 1
            return ComponentHealth(
                name="test_component",
                status=HealthStatus.HEALTHY,
                message=f"Check #{check_count}"
            )
        
        health_checker.register_health_check("test_component", counting_health_check)
        
        # Start periodic checks
        await health_checker.start_periodic_checks()
        
        # Wait for a few checks
        await asyncio.sleep(2.5)
        
        # Stop periodic checks
        await health_checker.stop_periodic_checks()
        
        # Should have run at least 2 checks
        assert check_count >= 2


class TestMonitoringDashboard:
    """Test monitoring dashboard functionality."""
    
    @pytest.fixture
    def dashboard(self):
        """Create a monitoring dashboard for testing."""
        metrics_collector = MetricsCollector()
        health_checker = HealthChecker()
        return MonitoringDashboard(metrics_collector, health_checker)
    
    def test_error_recording(self, dashboard):
        """Test error recording for dashboard."""
        dashboard.record_error(
            component="test_component",
            operation="test_operation",
            error_type="ValueError",
            error_message="Test error message",
            metadata={"key": "value"}
        )
        
        assert len(dashboard._error_history) == 1
        error = dashboard._error_history[0]
        assert error["component"] == "test_component"
        assert error["error_type"] == "ValueError"
        assert error["metadata"]["key"] == "value"
    
    async def test_dashboard_data_collection(self, dashboard):
        """Test comprehensive dashboard data collection."""
        # Add some test data
        dashboard.metrics_collector.record_execution("test_component", "test_op", 1.0, True)
        dashboard.record_error("test_component", "test_op", "TestError", "Test error")
        
        # Mock health checker
        async def test_health_check():
            return ComponentHealth(
                name="test_component",
                status=HealthStatus.HEALTHY,
                message="Healthy"
            )
        
        dashboard.health_checker.register_health_check("test_component", test_health_check)
        await dashboard.health_checker.check_component_health("test_component")
        
        # Collect dashboard data
        dashboard_data = await dashboard.collect_dashboard_data()
        
        assert dashboard_data.uptime_seconds > 0
        assert "test_component" in dashboard_data.component_health
        assert "test_component.test_op" in dashboard_data.performance_metrics
        assert len(dashboard_data.recent_errors) == 1
        assert dashboard_data.agent_statistics["total_agents"] >= 0
    
    def test_error_summary(self, dashboard):
        """Test error summary generation."""
        # Record some errors
        dashboard.record_error("comp1", "op1", "Error1", "Message 1")
        dashboard.record_error("comp1", "op2", "Error2", "Message 2")
        dashboard.record_error("comp2", "op1", "Error1", "Message 3")
        
        summary = dashboard.get_error_summary(hours=24)
        
        assert summary["total_errors"] == 3
        assert summary["errors_by_type"]["Error1"] == 2
        assert summary["errors_by_type"]["Error2"] == 1
        assert summary["errors_by_component"]["comp1"] == 2
        assert summary["errors_by_component"]["comp2"] == 1
    
    def test_performance_summary(self, dashboard):
        """Test performance summary generation."""
        # Add some performance data
        dashboard.metrics_collector.record_execution("fast_component", "op1", 0.1, True)
        dashboard.metrics_collector.record_execution("slow_component", "op1", 2.0, True)
        dashboard.metrics_collector.record_execution("failing_component", "op1", 1.0, False)
        
        summary = dashboard.get_performance_summary()
        
        assert summary["total_requests"] == 3
        assert summary["overall_success_rate"] == pytest.approx(66.67, rel=1e-2)
        assert len(summary["fastest_components"]) > 0
        assert len(summary["slowest_components"]) > 0


class TestGlobalInstances:
    """Test global instance management."""
    
    def test_get_logger(self):
        """Test global logger instance management."""
        logger1 = get_logger("test_logger")
        logger2 = get_logger("test_logger")
        
        # Should return the same instance
        assert logger1 is logger2
        
        # Different names should return different instances
        logger3 = get_logger("different_logger")
        assert logger1 is not logger3
    
    def test_get_metrics_collector(self):
        """Test global metrics collector instance."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        # Should return the same instance
        assert collector1 is collector2
    
    def test_get_health_checker(self):
        """Test global health checker instance."""
        checker1 = get_health_checker()
        checker2 = get_health_checker()
        
        # Should return the same instance
        assert checker1 is checker2


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for monitoring components."""
    
    async def test_end_to_end_monitoring(self):
        """Test end-to-end monitoring workflow."""
        # Get global instances
        logger = get_logger("integration_test")
        metrics_collector = get_metrics_collector()
        health_checker = get_health_checker()
        
        # Set correlation ID
        correlation_id = logger.set_correlation_id("integration-test-123")
        
        # Register a health check
        async def test_health_check():
            return ComponentHealth(
                name="integration_component",
                status=HealthStatus.HEALTHY,
                message="Integration test component is healthy"
            )
        
        health_checker.register_health_check("integration_component", test_health_check)
        
        # Simulate some operations with metrics
        with MetricsTimer(metrics_collector, "integration_component", "test_operation"):
            logger.info("Starting integration test operation", 
                       component="integration_component",
                       operation="test_operation")
            
            # Simulate work
            await asyncio.sleep(0.1)
            
            logger.info("Integration test operation completed successfully")
        
        # Check health
        health = await health_checker.check_component_health("integration_component")
        assert health.status == HealthStatus.HEALTHY
        
        # Check metrics
        metrics = metrics_collector.get_performance_metrics("integration_component")
        assert "integration_component.test_operation" in metrics
        
        component_metrics = metrics["integration_component.test_operation"]
        assert component_metrics.total_requests == 1
        assert component_metrics.successful_requests == 1
        assert component_metrics.avg_execution_time >= 0.1
        
        # Create dashboard and collect data
        dashboard = MonitoringDashboard(metrics_collector, health_checker)
        dashboard_data = await dashboard.collect_dashboard_data()
        
        assert dashboard_data.uptime_seconds > 0
        assert "integration_component" in dashboard_data.component_health
        assert dashboard_data.component_health["integration_component"].status == HealthStatus.HEALTHY
        
        # Verify correlation ID is maintained
        assert logger.get_correlation_id() == correlation_id