"""
Remote CMD - SSH 远程服务器管理工具

一个功能强大的 Python 库，用于管理远程服务器。
提供简洁的 API 用于 SSH 连接、命令执行和文件传输。

主要功能：
    - SSH 连接管理（支持密码和密钥认证）
    - 远程命令执行（包括 sudo 命令）
    - 文件上传和下载
    - 主机配置管理
    - 标签分类系统
    - 批量连接测试

快速开始：
    >>> from remote_cmd import SSHClient, HostManager
    >>> from remote_cmd.core.ssh_client import ConnectionConfig
    >>>
    >>> # 创建连接配置
    >>> config = ConnectionConfig(
    ...     hostname="192.168.1.100",
    ...     username="admin",
    ...     key_filename="~/.ssh/id_rsa"
    ... )
    >>>
    >>> # 执行远程命令
    >>> with SSHClient(config) as client:
    ...     result = client.execute("ls -la")
    ...     print(result.stdout)

命令行使用：
    $ remote-cmd host add server1 192.168.1.100 admin -k ~/.ssh/id_rsa
    $ remote-cmd host list
    $ remote-cmd run server1 "uptime"

更多信息：
    - GitHub: https://github.com/Vae-Scrooge/remote-cmd-test
    - 文档: 参见 docs/ 目录

Author: Vae-Scrooge
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Vae-Scrooge"
__email__ = "vae-scrooge@example.com"
__license__ = "MIT"

# 导出主要类，便于直接从包级别导入
from remote_cmd.core.ssh_client import SSHClient
from remote_cmd.core.async_client import AsyncSSHClient, ConnectionPool
from remote_cmd.core.host_manager import HostManager

# 定义公开 API
__all__ = [
    "SSHClient",
    "AsyncSSHClient",
    "ConnectionPool",
    "HostManager",
    "__version__",
    "__author__",
    "__license__",
]
