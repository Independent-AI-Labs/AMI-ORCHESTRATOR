"""Tests for SSH MCP Server."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.backend.config.network import SSHConfig  # noqa: E402
from base.backend.mcp.ssh.server import SSHMCPServer  # noqa: E402
from base.backend.mcp.ssh.tools.executor import SSHConnection, ToolExecutor  # noqa: E402

# Test constants
TEST_PASSWORD = "testpass123"  # noqa: S105
DEFAULT_PORT = 22
DEFAULT_TIMEOUT = 30
ALT_PORT = 2222
NUM_BASIC_TOOLS = 5
NUM_SERVERS = 2


class TestSSHConfig:
    """Test SSH configuration."""

    def test_ssh_config_creation(self):
        """Test creating SSH configuration."""
        config = SSHConfig(
            name="test-server",
            host="192.168.1.1",
            port=DEFAULT_PORT,
            username="testuser",
            password=TEST_PASSWORD,  # noqa: S106
        )

        assert config.name == "test-server"
        assert config.host == "192.168.1.1"
        assert config.port == DEFAULT_PORT
        assert config.username == "testuser"
        assert config.password == TEST_PASSWORD
        assert config.timeout == DEFAULT_TIMEOUT

    def test_ssh_config_validation(self):
        """Test SSH configuration validation."""
        # Test invalid name
        with pytest.raises(ValueError, match="Server name must contain only"):
            SSHConfig(
                name="test server!",  # Invalid characters
                host="192.168.1.1",
                username="testuser",
            )

        # Test invalid port
        with pytest.raises(ValueError, match="Port must be between"):
            SSHConfig(name="test-server", host="192.168.1.1", port=99999, username="testuser")

        # Test empty host
        with pytest.raises(ValueError, match="Host cannot be empty"):
            SSHConfig(name="test-server", host="", username="testuser")

    def test_to_paramiko_config(self):
        """Test conversion to Paramiko configuration."""
        config = SSHConfig(
            name="test-server",
            host="192.168.1.1",
            port=ALT_PORT,
            username="testuser",
            password=TEST_PASSWORD,  # noqa: S106
            key_filename="/path/to/key",
            compression=True,
        )

        paramiko_config = config.to_paramiko_config()

        assert paramiko_config["hostname"] == "192.168.1.1"
        assert paramiko_config["port"] == ALT_PORT
        assert paramiko_config["username"] == "testuser"
        assert paramiko_config["password"] == TEST_PASSWORD
        assert paramiko_config["key_filename"] == "/path/to/key"
        assert paramiko_config["compress"] is True
        assert paramiko_config["timeout"] == DEFAULT_TIMEOUT


class TestSSHMCPServer:
    """Test SSH MCP Server."""

    def test_server_initialization(self):
        """Test server initialization with configuration."""
        config = {
            "servers": {
                "test-server": {
                    "host": "192.168.1.1",
                    "username": "testuser",
                    "password": TEST_PASSWORD,  # noqa: S106
                }
            },
            "options": {"enable_privileged": False},
        }

        server = SSHMCPServer(config=config)

        assert len(server.ssh_servers) == 1
        assert "test-server" in server.ssh_servers
        assert server.ssh_servers["test-server"].host == "192.168.1.1"
        assert len(server.tools) == NUM_BASIC_TOOLS

    def test_server_with_yaml_config(self):
        """Test server initialization with YAML config file."""

        config_data = {
            "servers": {
                "test-server-1": {
                    "host": "192.168.1.1",
                    "username": "user1",
                    "password": "pass1",  # noqa: S106
                },
                "test-server-2": {
                    "host": "192.168.1.2",
                    "username": "user2",
                    "password": "pass2",  # noqa: S106
                },
            },
            "options": {"enable_privileged": False},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name

        try:
            server = SSHMCPServer(config_file=config_file)
            assert len(server.ssh_servers) == NUM_SERVERS
            assert "test-server-1" in server.ssh_servers
            assert "test-server-2" in server.ssh_servers
        finally:
            Path(config_file).unlink()

    def test_privileged_tools_disabled_by_default(self):
        """Test that privileged tools are disabled by default."""
        server = SSHMCPServer()

        # Check that privileged tools are not registered
        assert "ssh_connect_server" not in server.tools
        assert "ssh_disconnect_server" not in server.tools

        # Basic tools should be present
        assert "ssh_execute" in server.tools
        assert "ssh_list_servers" in server.tools

    def test_privileged_tools_enabled_by_env(self):
        """Test enabling privileged tools via environment variable."""

        # Set environment variable
        os.environ["SSH_MCP_ENABLE_PRIVILEGED"] = "true"

        try:
            server = SSHMCPServer()

            # Check that privileged tools are registered
            assert "ssh_connect_server" in server.tools
            assert "ssh_disconnect_server" in server.tools
        finally:
            # Clean up environment
            del os.environ["SSH_MCP_ENABLE_PRIVILEGED"]

    @pytest.mark.asyncio
    async def test_execute_list_servers(self):
        """Test executing list_servers tool."""
        config = {
            "servers": {
                "server1": {
                    "host": "192.168.1.1",
                    "username": "user1",
                    "password": "pass1",  # noqa: S106
                    "description": "Test server 1",
                },
                "server2": {
                    "host": "192.168.1.2",
                    "username": "user2",
                    "password": "pass2",  # noqa: S106
                    "description": "Test server 2",
                },
            }
        }

        server = SSHMCPServer(config=config)
        result = await server.execute_tool("ssh_list_servers", {})

        assert result["count"] == NUM_SERVERS
        assert len(result["servers"]) == NUM_SERVERS

        server_names = [s["name"] for s in result["servers"]]
        assert "server1" in server_names
        assert "server2" in server_names


class TestToolExecutor:
    """Test SSH Tool Executor."""

    def test_executor_initialization(self):
        """Test executor initialization with servers."""
        servers = {
            "server1": SSHConfig(name="server1", host="192.168.1.1", username="user1"),
            "server2": SSHConfig(name="server2", host="192.168.1.2", username="user2"),
        }

        executor = ToolExecutor(servers)

        assert len(executor.servers) == NUM_SERVERS
        assert "server1" in executor.servers
        assert "server2" in executor.servers

    def test_add_remove_server(self):
        """Test adding and removing servers."""
        executor = ToolExecutor()

        # Add a server
        config = SSHConfig(name="test-server", host="192.168.1.1", username="testuser")
        executor.add_server(config)

        assert "test-server" in executor.servers
        assert executor.servers["test-server"] == config

        # Remove the server
        executor.remove_server("test-server")

        assert "test-server" not in executor.servers

    @pytest.mark.asyncio
    async def test_list_servers(self):
        """Test listing servers."""
        servers = {
            "server1": SSHConfig(name="server1", host="192.168.1.1", username="user1", description="Server 1"),
            "server2": SSHConfig(name="server2", host="192.168.1.2", username="user2", description="Server 2"),
        }

        executor = ToolExecutor(servers)
        result = await executor.execute("ssh_list_servers", {})

        assert result["count"] == NUM_SERVERS
        assert len(result["servers"]) == NUM_SERVERS

        # Check server details
        server1 = next(s for s in result["servers"] if s["name"] == "server1")
        assert server1["host"] == "192.168.1.1"
        assert server1["username"] == "user1"
        assert server1["description"] == "Server 1"
        assert server1["connected"] is False  # Not connected yet

    @pytest.mark.asyncio
    async def test_execute_command_mock(self):
        """Test executing command with mocked SSH connection."""
        servers = {
            "test-server": SSHConfig(
                name="test-server",
                host="192.168.1.1",
                username="testuser",
                password=TEST_PASSWORD,  # noqa: S106
            )
        }

        executor = ToolExecutor(servers)

        # Mock the SSH connection
        with patch.object(SSHConnection, "execute_command") as mock_exec:
            mock_exec.return_value = {
                "status": "success",
                "exit_code": 0,
                "output": "Hello, World!",
                "error": "",
                "command": "echo 'Hello, World!'",
                "server": "test-server",
            }

            result = await executor.execute("ssh_execute", {"server": "test-server", "command": "echo 'Hello, World!'"})

            assert result["status"] == "success"
            assert result["output"] == "Hello, World!"
            assert result["server"] == "test-server"

    @pytest.mark.asyncio
    async def test_connect_disconnect_server(self):
        """Test connecting and disconnecting servers at runtime."""
        executor = ToolExecutor()

        # Enable privileged tools
        executor.servers = {}  # Start with no servers

        # Mock SSH connection
        with patch("paramiko.SSHClient") as mock_ssh:
            mock_client = MagicMock()
            mock_ssh.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_transport.return_value = MagicMock(is_active=lambda: True)

            # Connect to a new server
            result = await executor.execute(
                "ssh_connect_server",
                {
                    "name": "new-server",
                    "host": "192.168.1.100",
                    "username": "newuser",
                    "password": "newpass",  # noqa: S106
                },
            )

            assert "new-server" in executor.servers
            assert executor.servers["new-server"].host == "192.168.1.100"

            # Disconnect from the server
            result = await executor.execute("ssh_disconnect_server", {"server": "new-server"})

            assert result["status"] == "disconnected"
            assert "new-server" not in executor.servers

    def test_close_all_connections(self):
        """Test closing all connections."""
        servers = {
            "server1": SSHConfig(name="server1", host="192.168.1.1", username="user1"),
            "server2": SSHConfig(name="server2", host="192.168.1.2", username="user2"),
        }

        executor = ToolExecutor(servers)

        # Create mock connections
        mock_conn1 = MagicMock()
        mock_conn2 = MagicMock()
        executor.connections = {"server1": mock_conn1, "server2": mock_conn2}

        # Close all connections
        executor.close_all()

        # Verify close was called on both connections
        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()
        assert len(executor.connections) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
