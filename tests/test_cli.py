"""CLI 命令行接口单元测试

使用 Click 的 CliRunner 测试命令行解析和输出。
SSH 连接部分使用 mock 避免真实连接。
"""

import json
import os
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from remote_cmd.cli.main import cli
from remote_cmd.core.host_manager import Host


@pytest.fixture
def runner():
    """提供 Click CliRunner 实例"""
    return CliRunner()


@pytest.fixture
def hosts_file(tmp_path):
    """生成临时的 hosts.json 文件路径"""
    return str(tmp_path / "hosts.json")


@pytest.fixture
def config_file(tmp_path):
    """生成临时的 config.yaml 文件路径"""
    path = tmp_path / "config.yaml"
    path.write_text(f"hosts_file: {tmp_path / 'hosts.json'}", encoding="utf-8")
    return str(path)


# ============================================================================
# host add 命令测试
# ============================================================================


class TestHostAdd:
    """测试 host add 命令"""

    def test_add_with_key_success(self, runner, config_file):
        """测试：使用 SSH 密钥添加主机成功"""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "web-server",
                    "192.168.1.10",
                    "admin",
                    "-k",
                    "~/.ssh/id_rsa",
                ],
            )
            assert result.exit_code == 0
            assert "添加成功" in result.output

    def test_add_with_env_password(self, runner, config_file):
        """测试：使用环境变量密码添加主机（推荐做法）"""
        with runner.isolated_filesystem():
            env = {"REMOTE_CMD_PASSWORD": "secret123"}
            result = runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "db-server",
                    "10.0.0.1",
                    "root",
                ],
                env=env,
            )
            assert result.exit_code == 0
            assert "添加成功" in result.output

    def test_add_duplicate_fails(self, runner, config_file):
        """测试：添加同名主机应报错"""
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "dup-host",
                    "1.2.3.4",
                    "admin",
                    "-k",
                    "~/.ssh/id_rsa",
                ],
            )
            result = runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "dup-host",
                    "5.6.7.8",
                    "admin",
                    "-k",
                    "~/.ssh/id_rsa",
                ],
            )
            assert result.exit_code != 0
            assert "已存在" in result.output


# ============================================================================
# host list 命令测试
# ============================================================================


class TestHostList:
    """测试 host list 命令"""

    def test_list_empty(self, runner, config_file):
        """测试：没有主机时列出应为空"""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["--config", config_file, "host", "list"])
            assert result.exit_code == 0
            assert "没有配置任何主机" in result.output

    def test_list_with_hosts(self, runner, config_file):
        """测试：列出已添加的主机"""
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "srv1",
                    "10.0.0.1",
                    "admin",
                    "-k",
                    "~/.ssh/id_rsa",
                ],
            )
            result = runner.invoke(cli, ["--config", config_file, "host", "list"])
            assert result.exit_code == 0
            assert "srv1" in result.output
            assert "10.0.0.1" in result.output

    def test_list_filter_by_tag(self, runner, config_file):
        """测试：按标签筛选主机"""
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "prod-web",
                    "10.0.0.1",
                    "admin",
                    "-k",
                    "~/.ssh/id_rsa",
                    "-t",
                    "production",
                    "-t",
                    "web",
                ],
            )
            runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "dev-web",
                    "10.0.0.2",
                    "admin",
                    "-k",
                    "~/.ssh/id_rsa",
                    "-t",
                    "development",
                ],
            )
            result = runner.invoke(
                cli,
                ["--config", config_file, "host", "list", "-t", "production"],
            )
            assert result.exit_code == 0
            assert "prod-web" in result.output
            assert "dev-web" not in result.output


# ============================================================================
# host show 命令测试
# ============================================================================


class TestHostShow:
    """测试 host show 命令"""

    def test_show_existing_host(self, runner, config_file):
        """测试：显示已存在主机的详细信息"""
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "my-server",
                    "192.168.1.1",
                    "ubuntu",
                    "-k",
                    "~/.ssh/id_rsa",
                    "-d",
                    "My server",
                ],
            )
            result = runner.invoke(
                cli, ["--config", config_file, "host", "show", "my-server"]
            )
            assert result.exit_code == 0
            assert "my-server" in result.output
            assert "192.168.1.1" in result.output
            assert "ubuntu" in result.output
            assert "My server" in result.output

    def test_show_nonexistent_host(self, runner, config_file):
        """测试：显示不存在的主机应报错"""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["--config", config_file, "host", "show", "ghost"]
            )
            assert result.exit_code != 0
            assert "不存在" in result.output


# ============================================================================
# host remove 命令测试
# ============================================================================


class TestHostRemove:
    """测试 host remove 命令"""

    def test_remove_with_confirmation(self, runner, config_file):
        """测试：带确认的移除操作"""
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "to-delete",
                    "1.2.3.4",
                    "admin",
                    "-k",
                    "~/.ssh/id_rsa",
                ],
            )
            result = runner.invoke(
                cli,
                ["--config", config_file, "host", "remove", "to-delete"],
                input="y\n",
            )
            assert result.exit_code == 0
            assert "已移除" in result.output

    def test_remove_nonexistent(self, runner, config_file):
        """测试：移除不存在的主机应报错"""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--config", config_file, "host", "remove", "nonexistent"],
                input="y\n",
            )
            assert result.exit_code != 0
            assert "不存在" in result.output


# ============================================================================
# host test 命令测试
# ============================================================================


class TestHostTest:
    """测试 host test 命令"""

    def test_connection_success(self, runner, config_file):
        """测试：连接成功"""
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "good-host",
                    "10.0.0.1",
                    "admin",
                    "-k",
                    "~/.ssh/id_rsa",
                ],
            )
            with patch(
                "remote_cmd.service.host_service.HostService.test_connection",
                return_value=True,
            ):
                result = runner.invoke(
                    cli,
                    ["--config", config_file, "host", "test", "good-host"],
                )
                assert result.exit_code == 0
                assert "连接成功" in result.output

    def test_connection_failure(self, runner, config_file):
        """测试：连接失败"""
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "--config",
                    config_file,
                    "host",
                    "add",
                    "bad-host",
                    "10.0.0.99",
                    "admin",
                    "-k",
                    "~/.ssh/id_rsa",
                ],
            )
            with patch(
                "remote_cmd.service.host_service.HostService.test_connection",
                return_value=False,
            ):
                result = runner.invoke(
                    cli,
                    ["--config", config_file, "host", "test", "bad-host"],
                )
                assert result.exit_code != 0
                assert "连接失败" in result.output


# ============================================================================
# CLI 根命令测试
# ============================================================================


class TestCliRoot:
    """测试 CLI 根命令"""

    def test_version(self, runner):
        """测试：--version 显示版本号"""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_help(self, runner):
        """测试：--help 显示帮助信息"""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "host" in result.output
        assert "run" in result.output
        assert "upload" in result.output
        assert "download" in result.output
