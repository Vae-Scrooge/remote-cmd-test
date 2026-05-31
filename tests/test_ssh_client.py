"""
SSH 客户端单元测试

测试 SSHClient、ConnectionConfig 和 CommandResult 类的功能。
使用 pytest 和 unittest.mock 进行测试。

测试覆盖：
- ConnectionConfig 配置验证
- CommandResult 结果处理
- SSHClient 连接管理
- SSHClient 命令执行
- 上下文管理器

运行方式：
    pytest tests/test_ssh_client.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from remote_cmd.core.ssh_client import SSHClient, ConnectionConfig, CommandResult
from remote_cmd.utils.exceptions import SSHConnectionError, SSHCommandError

# ============================================================================
# ConnectionConfig 测试
# ============================================================================


class TestConnectionConfig:
    """ConnectionConfig 配置类测试"""

    def test_valid_config_with_password(self):
        """测试：使用密码的有效配置"""
        config = ConnectionConfig(
            hostname="example.com", username="admin", password="secret"
        )

        assert config.hostname == "example.com"
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.port == 22  # 默认端口

    def test_valid_config_with_key(self):
        """测试：使用 SSH 密钥的有效配置"""
        config = ConnectionConfig(
            hostname="example.com", username="admin", key_filename="~/.ssh/id_rsa"
        )

        assert config.key_filename == "~/.ssh/id_rsa"

    def test_ssh_agent_config(self):
        """测试：无密码和密钥时应使用 SSH Agent 认证"""
        config = ConnectionConfig(hostname="example.com", username="admin")
        assert config.hostname == "example.com"
        assert config.username == "admin"
        assert config.password is None
        assert config.key_filename is None


# ============================================================================
# CommandResult 测试
# ============================================================================


class TestCommandResult:
    """CommandResult 结果类测试"""

    def test_success_property(self):
        """测试：成功命令的 success 属性"""
        result = CommandResult(
            command="ls", stdout="file1\nfile2", stderr="", exit_code=0
        )

        assert result.success is True

    def test_failure_property(self):
        """测试：失败命令的 success 属性"""
        result = CommandResult(
            command="invalid_cmd", stdout="", stderr="command not found", exit_code=127
        )

        assert result.success is False

    def test_str_representation_success(self):
        """测试：成功结果的字符串表示"""
        result = CommandResult("ls", "", "", 0)

        assert "✓" in str(result)
        assert "[0]" in str(result)

    def test_str_representation_failure(self):
        """测试：失败结果的字符串表示"""
        result = CommandResult("cmd", "", "", 1)

        assert "✗" in str(result)
        assert "[1]" in str(result)


# ============================================================================
# SSHClient 测试
# ============================================================================


class TestSSHClient:
    """SSHClient 客户端类测试"""

    @patch("remote_cmd.core.ssh_client.paramiko.SSHClient")
    def test_connect_with_password(self, mock_ssh_class):
        """测试：使用密码连接"""
        # 设置模拟对象
        mock_ssh = MagicMock()
        mock_ssh_class.return_value = mock_ssh

        config = ConnectionConfig(
            hostname="example.com", username="admin", password="secret"
        )

        # 执行连接
        client = SSHClient(config)
        result = client.connect()

        # 验证结果
        assert result == client  # 应返回自身
        mock_ssh.connect.assert_called_once()

        # 验证连接参数
        call_kwargs = mock_ssh.connect.call_args.kwargs
        assert call_kwargs["hostname"] == "example.com"
        assert call_kwargs["password"] == "secret"

    @patch("remote_cmd.core.ssh_client.paramiko.SSHClient")
    def test_execute_command(self, mock_ssh_class):
        """测试：执行远程命令"""
        # 设置模拟对象
        mock_ssh = MagicMock()
        mock_ssh_class.return_value = mock_ssh

        # 模拟 exec_command 返回值
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"output line 1\noutput line 2"
        mock_stderr.read.return_value = b""

        mock_ssh.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        config = ConnectionConfig(
            hostname="example.com", username="admin", password="secret"
        )

        # 使用上下文管理器执行命令
        with SSHClient(config) as client:
            result = client.execute("ls -la")

        # 验证结果
        assert result.exit_code == 0
        assert "output line 1" in result.stdout
        assert result.success is True

    def test_execute_without_connection(self):
        """测试：未连接时执行命令应抛出异常"""
        config = ConnectionConfig(
            hostname="example.com", username="admin", password="secret"
        )

        client = SSHClient(config)

        with pytest.raises(SSHConnectionError, match="未连接"):
            client.execute("ls")

    @patch("remote_cmd.core.ssh_client.paramiko.SSHClient")
    def test_context_manager(self, mock_ssh_class):
        """测试：上下文管理器正确管理连接"""
        mock_ssh = MagicMock()
        mock_ssh_class.return_value = mock_ssh

        config = ConnectionConfig(
            hostname="example.com", username="admin", password="secret"
        )

        # 进入和退出上下文
        with SSHClient(config) as client:
            pass

        # 验证连接被关闭
        mock_ssh.close.assert_called_once()

    @patch("remote_cmd.core.ssh_client.paramiko.SSHClient")
    def test_is_connected(self, mock_ssh_class):
        """测试：连接状态检查"""
        # 设置模拟对象
        mock_ssh = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_ssh.get_transport.return_value = mock_transport
        mock_ssh_class.return_value = mock_ssh

        config = ConnectionConfig(
            hostname="example.com", username="admin", password="secret"
        )

        with SSHClient(config) as client:
            assert client.is_connected() is True


# ============================================================================
# 程序入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
