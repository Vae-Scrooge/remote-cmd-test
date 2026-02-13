# test_ssh_client.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from remote_cmd.core.ssh_client import SSHClient, ConnectionConfig, CommandResult
from remote_cmd.utils.exceptions import SSHConnectionError, SSHCommandError


class TestConnectionConfig:
    def test_valid_config_with_password(self):
        config = ConnectionConfig(
            hostname="example.com",
            username="admin",
            password="secret"
        )
        assert config.hostname == "example.com"
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.port == 22  # default
    
    def test_valid_config_with_key(self):
        config = ConnectionConfig(
            hostname="example.com",
            username="admin",
            key_filename="~/.ssh/id_rsa"
        )
        assert config.key_filename == "~/.ssh/id_rsa"
    
    def test_invalid_config_no_auth(self):
        with pytest.raises(ValueError, match="password or key_filename"):
            ConnectionConfig(
                hostname="example.com",
                username="admin"
            )


class TestCommandResult:
    def test_success_property(self):
        result = CommandResult(
            command="ls",
            stdout="file1\nfile2",
            stderr="",
            exit_code=0
        )
        assert result.success is True
    
    def test_failure_property(self):
        result = CommandResult(
            command="invalid_cmd",
            stdout="",
            stderr="command not found",
            exit_code=127
        )
        assert result.success is False
    
    def test_str_representation_success(self):
        result = CommandResult("ls", "", "", 0)
        assert "✓" in str(result)
        assert "[0]" in str(result)
    
    def test_str_representation_failure(self):
        result = CommandResult("cmd", "", "", 1)
        assert "✗" in str(result)
        assert "[1]" in str(result)


class TestSSHClient:
    @patch('remote_cmd.core.ssh_client.paramiko.SSHClient')
    def test_connect_with_password(self, mock_ssh_class):
        mock_ssh = MagicMock()
        mock_ssh_class.return_value = mock_ssh
        
        config = ConnectionConfig(
            hostname="example.com",
            username="admin",
            password="secret"
        )
        
        client = SSHClient(config)
        result = client.connect()
        
        assert result == client
        mock_ssh.connect.assert_called_once()
        call_kwargs = mock_ssh.connect.call_args.kwargs
        assert call_kwargs['hostname'] == "example.com"
        assert call_kwargs['password'] == "secret"
    
    @patch('remote_cmd.core.ssh_client.paramiko.SSHClient')
    def test_execute_command(self, mock_ssh_class):
        mock_ssh = MagicMock()
        mock_ssh_class.return_value = mock_ssh
        
        # Mock the exec_command return values
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"output line 1\noutput line 2"
        mock_stderr.read.return_value = b""
        
        mock_ssh.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        config = ConnectionConfig(
            hostname="example.com",
            username="admin",
            password="secret"
        )
        
        with SSHClient(config) as client:
            result = client.execute("ls -la")
        
        assert result.exit_code == 0
        assert "output line 1" in result.stdout
        assert result.success is True
    
    def test_execute_without_connection(self):
        config = ConnectionConfig(
            hostname="example.com",
            username="admin",
            password="secret"
        )
        client = SSHClient(config)
        
        with pytest.raises(SSHConnectionError, match="Not connected"):
            client.execute("ls")
    
    @patch('remote_cmd.core.ssh_client.paramiko.SSHClient')
    def test_context_manager(self, mock_ssh_class):
        mock_ssh = MagicMock()
        mock_ssh_class.return_value = mock_ssh
        
        config = ConnectionConfig(
            hostname="example.com",
            username="admin",
            password="secret"
        )
        
        with SSHClient(config) as client:
            pass
        
        mock_ssh.close.assert_called_once()
    
    @patch('remote_cmd.core.ssh_client.paramiko.SSHClient')
    def test_is_connected(self, mock_ssh_class):
        mock_ssh = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_ssh.get_transport.return_value = mock_transport
        mock_ssh_class.return_value = mock_ssh
        
        config = ConnectionConfig(
            hostname="example.com",
            username="admin",
            password="secret"
        )
        
        with SSHClient(config) as client:
            assert client.is_connected() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
