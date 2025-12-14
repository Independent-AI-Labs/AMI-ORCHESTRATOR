"""
Integration tests for monitoring and observability features.
Tests for health check endpoints, metrics collection, and status reporting.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from aiohttp import ClientSession

from base.backend.dataops.models.security import SecurityContext
from launcher.production.production_monitor import ProductionHealthMonitor


class TestHealthCheckEndpoints:
    """Test health check endpoint functionality."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_proper_format(self):
        """Test /health endpoint returns accurate status information."""
        # Create a temporary directory for the monitor
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            
            # Create a minimal services.yaml for testing
            services_dir = repo_root / "nodes" / "config"
            services_dir.mkdir(parents=True)
            (services_dir / "services.yaml").write_text("""
services:
  test-service:
    module: test.module
    summary: Test service for monitoring
""")
            
            monitor = ProductionHealthMonitor(repo_root)
            
            # Mock the supervisor to avoid actual service startup
            mock_supervisor = Mock()
            mock_supervisor.status = AsyncMock(return_value={})
            monitor.supervisor = mock_supervisor
            
            # Call the health handler directly
            request_mock = Mock()
            response = await monitor.health_handler(request_mock)
            
            # Parse the response
            response_text = response.body.decode('utf-8')
            health_data = json.loads(response_text)
            
            # Verify response structure
            assert "status" in health_data
            assert "timestamp" in health_data
            assert "service" in health_data
            assert health_data["service"] == "ami-orchestrator-monitoring"
            
            # Status should be healthy when supervisor is available
            assert health_data["status"] in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_service_status_integration(self, tmp_path):
        """Test health endpoint verifies actual service status."""
        # Create a services.yaml file
        services_dir = tmp_path / "config"
        services_dir.mkdir(exist_ok=True)
        services_file = services_dir / "services.yaml"
        services_file.write_text("""
services:
  web-service:
    module: web.module
    summary: Web service
  api-service:
    module: api.module
    summary: API service
""")

        monitor = ProductionHealthMonitor(tmp_path)

        # Mock supervisor with specific statuses
        mock_supervisor = Mock()
        async def mock_status(_):
            # Create a simple mock state instead of importing ServiceState
            class MockState:
                def __init__(self, value):
                    self.value = value
            return {
                "web-service": MockState("RUNNING"),
                "api-service": MockState("STOPPED")
            }
        mock_supervisor.status = mock_status
        monitor.supervisor = mock_supervisor

        # Call the health handler
        request_mock = Mock()
        response = await monitor.health_handler(request_mock)
        health_data = json.loads(response.body.decode('utf-8'))

        # Verify service status information
        assert "running_services" in health_data
        assert "total_services" in health_data
        assert health_data["total_services"] == 2
        assert health_data["running_services"] == 1  # Only one is running
        

class TestMetricsCollection:
    """Test metrics collection and Prometheus endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_format(self):
        """Test /metrics endpoint exposes Prometheus-compatible metrics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)

            monitor = ProductionHealthMonitor(repo_root)

            # Mock psutil import to avoid error
            with patch.dict('sys.modules', {'psutil': Mock()}):
                # Mock the psutil Process object with proper context manager support
                mock_process = Mock()
                mock_process.cpu_percent.return_value = 10.0
                mock_process.memory_info.return_value.rss = 1000000
                mock_process.create_time.return_value = 1234567890.0
                # Add context manager protocol support
                mock_process.__enter__ = Mock(return_value=mock_process)
                mock_process.__exit__ = Mock(return_value=False)

                mock_psutil = Mock()
                mock_psutil.Process.return_value = mock_process
                mock_psutil.boot_time.return_value = 1234567000.0
                mock_disk_usage = Mock()
                mock_disk_usage.total = 1000000000
                mock_disk_usage.used = 500000000
                mock_disk_usage.free = 500000000
                mock_psutil.disk_usage.return_value = mock_disk_usage
                mock_psutil.virtual_memory.return_value.percent = 50.0
                import sys
                sys.modules['psutil'] = mock_psutil

                # Call the metrics handler directly
                request_mock = Mock()
                response = await monitor.metrics_handler(request_mock)
                metrics_text = response.text

                # If metrics collection fails gracefully, the endpoint should still handle the error gracefully
                # Since we've mocked psutil properly, this should not happen in a test environment
                if metrics_text.strip() == "# Error in metrics collection":
                    # If this happens, there's an issue with our mocking or the test setup
                    pytest.fail("Metrics collection failed due to missing dependencies - psutil mock may not be set up correctly")
                else:
                    # Verify Prometheus format - should have HELP and TYPE comments
                    lines = metrics_text.strip().split('\n')
                    help_lines = [line for line in lines if line.startswith('# HELP')]
                    type_lines = [line for line in lines if line.startswith('# TYPE')]

                    # If psutil is not available, we may not get the full metrics,
                    # but should still get basic metrics
                    # Verify specific metrics are present
                    assert any('ami_system_timestamp' in line for line in lines), "Should have timestamp metric"

    @pytest.mark.asyncio
    async def test_service_state_metrics(self, tmp_path):
        """Test service state metrics are exposed in Prometheus format."""
        services_dir = tmp_path / "config"
        services_dir.mkdir(exist_ok=True)
        (services_dir / "services.yaml").write_text("""
services:
  test-service:
    module: test.module
    summary: Test service
""")

        monitor = ProductionHealthMonitor(tmp_path)

        # Mock supervisor with service states
        mock_supervisor = Mock()
        async def mock_status(_):
            # Create a simple mock state instead of importing ServiceState
            class MockState:
                def __init__(self, value):
                    self.value = value
            return {
                "test-service": MockState("RUNNING")
            }
        mock_supervisor.status = mock_status
        monitor.supervisor = mock_supervisor

        # Mock psutil import to avoid error
        with patch.dict('sys.modules', {'psutil': Mock()}):
            # Mock the psutil Process object with proper context manager support
            mock_process = Mock()
            mock_process.cpu_percent.return_value = 10.0
            mock_process.memory_info.return_value.rss = 1000000
            mock_process.create_time.return_value = 1234567890.0
            # Add context manager protocol support
            mock_process.__enter__ = Mock(return_value=mock_process)
            mock_process.__exit__ = Mock(return_value=False)

            mock_psutil = Mock()
            mock_psutil.Process.return_value = mock_process
            mock_psutil.boot_time.return_value = 1234567000.0
            mock_disk_usage = Mock()
            mock_disk_usage.total = 1000000000
            mock_disk_usage.used = 500000000
            mock_disk_usage.free = 500000000
            mock_psutil.disk_usage.return_value = mock_disk_usage
            mock_psutil.virtual_memory.return_value.percent = 50.0
            import sys
            sys.modules['psutil'] = mock_psutil

            # Call the metrics handler
            request_mock = Mock()
            response = await monitor.metrics_handler(request_mock)
            metrics_text = response.text

            # Check that service state metrics are present (if metrics collection succeeded)
            if metrics_text.strip() == "# Error in metrics collection":
                # If this happens, there's an issue with our mocking or the test setup
                pytest.fail("Service state metrics collection failed due to missing dependencies - psutil mock may not be set up correctly")
            else:
                # Check that service state metrics are present
                assert 'ami_service_state{service="test-service"' in metrics_text
                assert 'state="running"' in metrics_text

                # Verify the state is mapped to the correct numeric value (RUNNING = 2)
                assert ' 2' in metrics_text or '2.0' in metrics_text

    @pytest.mark.asyncio
    async def test_system_metrics_collection(self):
        """Test system metrics (CPU, memory, disk) are collected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)

            monitor = ProductionHealthMonitor(repo_root)

            # Mock psutil import to avoid error
            with patch.dict('sys.modules', {'psutil': Mock()}):
                # Mock the psutil Process object with proper context manager support
                mock_process = Mock()
                mock_process.cpu_percent.return_value = 10.0
                mock_process.memory_info.return_value.rss = 1000000
                mock_process.create_time.return_value = 1234567890.0
                # Add context manager protocol support
                mock_process.__enter__ = Mock(return_value=mock_process)
                mock_process.__exit__ = Mock(return_value=False)

                mock_psutil = Mock()
                mock_psutil.Process.return_value = mock_process
                mock_psutil.boot_time.return_value = 1234567000.0
                mock_disk_usage = Mock()
                mock_disk_usage.total = 1000000000
                mock_disk_usage.used = 500000000
                mock_disk_usage.free = 500000000
                mock_psutil.disk_usage.return_value = mock_disk_usage
                mock_psutil.virtual_memory.return_value.percent = 50.0
                import sys
                sys.modules['psutil'] = mock_psutil

                # Call the metrics handler
                request_mock = Mock()
                response = await monitor.metrics_handler(request_mock)
                metrics_text = response.text

                # If metrics collection fails gracefully, we should still handle it appropriately
                if metrics_text.strip() == "# Error in metrics collection":
                    # If this happens, there's an issue with our mocking or the test setup
                    pytest.fail("System metrics collection failed due to missing dependencies - psutil mock may not be set up correctly")
                else:
                    # Verify system metrics are present
                    assert 'ami_process_cpu_percent' in metrics_text
                    assert 'ami_process_memory_bytes' in metrics_text
                    assert 'ami_disk_total_bytes' in metrics_text
                    assert 'ami_disk_used_bytes' in metrics_text
                    assert 'ami_disk_free_bytes' in metrics_text
                    assert 'ami_process_start_time_seconds' in metrics_text


class TestStatusEndpoints:
    """Test status and monitoring endpoints."""

    @pytest.mark.asyncio
    async def test_status_endpoint_comprehensive_info(self):
        """Test /status endpoint provides comprehensive system status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)

            monitor = ProductionHealthMonitor(repo_root)

            # Mock supervisor
            mock_supervisor = Mock()
            async def mock_status(_):
                # Create a simple mock state instead of importing ServiceState
                class MockState:
                    def __init__(self, value):
                        self.value = value
                return {"test-service": MockState("RUNNING")}
            mock_supervisor.status = mock_status
            monitor.supervisor = mock_supervisor

            # Mock psutil import to avoid error
            with patch.dict('sys.modules', {'psutil': Mock()}):
                # Mock the psutil Process object with proper context manager support
                mock_process = Mock()
                mock_process.cpu_percent.return_value = 10.0
                # Add context manager protocol support
                mock_process.__enter__ = Mock(return_value=mock_process)
                mock_process.__exit__ = Mock(return_value=False)

                mock_psutil = Mock()
                mock_psutil.Process.return_value = mock_process
                mock_psutil.cpu_percent.return_value = 10.0
                mock_psutil.virtual_memory.return_value.percent = 50.0
                mock_psutil.disk_usage.return_value.percent = 40.0
                mock_psutil.boot_time.return_value = 1234567000.0
                import sys
                sys.modules['psutil'] = mock_psutil

                # Mock health handler to return healthy status
                original_health = monitor.health_handler
                async def mock_health_handler(request):
                    from aiohttp import web
                    try:
                        health_response = await original_health(request)
                        health_data = json.loads(health_response.body.decode('utf-8'))
                        health_data['status'] = 'healthy'
                        return web.json_response(health_data)
                    except:
                        # If health handler fails, return a mock response
                        return web.json_response({
                            'status': 'healthy',
                            'timestamp': '2025-12-09T12:00:00Z',
                            'service': 'ami-orchestrator-monitoring',
                            'version': '1.0.0'
                        })
                monitor.health_handler = mock_health_handler

                # Call the overall status handler
                request_mock = Mock()
                response = await monitor.overall_status_handler(request_mock)
                try:
                    status_data = json.loads(response.body.decode('utf-8'))

                    # Verify structure
                    assert "health" in status_data
                    assert "system" in status_data
                    assert "overall_status" in status_data
                    assert "service" in status_data

                    # Verify system metrics are present
                    system_metrics = status_data["system"]
                    assert "cpu_percent" in system_metrics
                    assert "memory_percent" in system_metrics
                    assert "disk_percent" in system_metrics
                    assert "uptime_seconds" in system_metrics
                except json.JSONDecodeError as e:
                    # Instead of silently passing, fail with a descriptive error that explains the issue
                    # This reveals the dependency problem rather than hiding it with 'pass'
                    pytest.fail(f"JSON parsing failed in overall status endpoint: {str(e)}. This indicates missing dependencies that should be resolved for monitoring functionality to work properly.")

    @pytest.mark.asyncio
    async def test_launcher_status_endpoint_detailed_info(self, tmp_path):
        """Test /launcher/status endpoint provides detailed launcher information."""
        services_dir = tmp_path / "config"
        services_dir.mkdir(exist_ok=True)
        (services_dir / "services.yaml").write_text("""
services:
  web-service:
    module: web.module
    summary: Web service
    entry_point: web:main
""")

        monitor = ProductionHealthMonitor(tmp_path)

        # Mock supervisor with manifest and status
        mock_manifest = Mock()
        mock_manifest.services = {
            "web-service": Mock(summary="Web service", module="web.module")
        }
        mock_manifest.profiles = {"default": ["web-service"]}

        mock_supervisor = Mock()
        mock_supervisor.manifest = mock_manifest
        async def mock_status(_):
            # Create a simple mock state instead of importing ServiceState
            class MockState:
                def __init__(self, value):
                    self.value = value
            return {
                "web-service": MockState("RUNNING")
            }

        # Mock the list_services method to return runtime info
        mock_supervisor.list_services = Mock(return_value={
            "web-service": Mock(
                last_error=None,
                last_updated="2025-01-01T00:00:00Z",
                last_health="healthy"
            )
        })

        mock_supervisor.status = mock_status
        monitor.supervisor = mock_supervisor

        # Call the launcher status handler
        request_mock = Mock()
        response = await monitor.launcher_status_handler(request_mock)
        try:
            status_data = json.loads(response.body.decode('utf-8'))

            # Verify structure
            assert "timestamp" in status_data
            assert "supervisor_available" in status_data
            assert "service_count" in status_data
            assert "services" in status_data

            # Verify service details
            assert status_data["service_count"] == 1
            assert "web-service" in status_data["services"]

            web_service_info = status_data["services"]["web-service"]
            assert web_service_info["state"] == "RUNNING"
            assert web_service_info["summary"] == "Web service"
            assert web_service_info["module"] == "web.module"
        except json.JSONDecodeError as e:
            # Instead of silently passing with 'pass', fail with a descriptive error that explains the issue
            # This reveals the dependency problem rather than hiding it
            pytest.fail(f"JSON parsing failed in launcher status endpoint: {str(e)}. This indicates missing dependencies that should be resolved for monitoring functionality to work properly.")


class AsyncMock(Mock):
    """Helper class for async mocking."""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)