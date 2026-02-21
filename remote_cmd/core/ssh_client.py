"""
SSH 客户端模块

提供高级别的 SSH 连接和操作接口，包括：
- 远程命令执行
- 文件上传/下载
- 远程目录管理
- sudo 权限命令执行

依赖：paramiko 库

Author: Vae-Scrooge
"""

import paramiko
import socket
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import logging

from remote_cmd.utils.exceptions import SSHConnectionError, SSHCommandError, SSHFileTransferError

# 模块日志记录器
logger = logging.getLogger(__name__)


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class ConnectionConfig:
    """
    SSH 连接配置类
    
    用于存储和管理 SSH 连接所需的所有参数。
    支持密码认证和 SSH 密钥认证两种方式。
    
    Attributes:
        hostname: 目标主机地址（IP 或域名）
        username: SSH 登录用户名
        port: SSH 端口号，默认为 22
        password: 登录密码（可选，与 key_filename 二选一）
        key_filename: SSH 私钥文件路径（可选，与 password 二选一）
        timeout: 连接超时时间（秒），默认 30 秒
        compress: 是否启用压缩，默认启用
    
    Raises:
        ValueError: 当既没有提供 password 也没有提供 key_filename 时抛出
    """
    
    hostname: str
    username: str
    port: int = 22
    password: Optional[str] = None
    key_filename: Optional[str] = None
    timeout: int = 30
    compress: bool = True
    
    def __post_init__(self):
        """初始化后验证：确保至少提供一种认证方式"""
        if not self.password and not self.key_filename:
            raise ValueError("必须提供 password 或 key_filename 其中一种认证方式")


@dataclass
class CommandResult:
    """
    命令执行结果类
    
    封装远程命令执行的返回结果，包括标准输出、标准错误和退出码。
    
    Attributes:
        command: 执行的命令字符串
        stdout: 标准输出内容
        stderr: 标准错误内容
        exit_code: 命令退出码（0 表示成功）
    """
    
    command: str
    stdout: str
    stderr: str
    exit_code: int
    
    @property
    def success(self) -> bool:
        """
        判断命令是否执行成功
        
        Returns:
            bool: 退出码为 0 时返回 True，否则返回 False
        """
        return self.exit_code == 0
    
    def __str__(self) -> str:
        """
        生成命令结果的可读字符串表示
        
        Returns:
            str: 格式为 "状态符号 [退出码] 命令"
        """
        status = "✓" if self.success else "✗"
        return f"{status} [{self.exit_code}] {self.command}"


# ============================================================================
# SSH 客户端类
# ============================================================================

class SSHClient:
    """
    高级 SSH 客户端类
    
    提供完整的 SSH 连接管理功能，支持上下文管理器模式，
    可以使用 `with` 语句自动管理连接的生命周期。
    
    主要功能：
    - 建立/断开 SSH 连接
    - 执行远程命令（普通命令和 sudo 命令）
    - 文件上传/下载
    - 远程目录浏览
    
    使用示例：
        >>> config = ConnectionConfig(
        ...     hostname="example.com",
        ...     username="admin",
        ...     key_filename="~/.ssh/id_rsa"
        ... )
        >>> with SSHClient(config) as client:
        ...     result = client.execute("ls -la")
        ...     print(result.stdout)
    """
    
    def __init__(self, config: ConnectionConfig):
        """
        初始化 SSH 客户端
        
        Args:
            config: ConnectionConfig 对象，包含连接参数
        
        Note:
            初始化时不会建立连接，需要调用 connect() 方法或使用上下文管理器
        """
        self.config = config
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
    
    # ========================================================================
    # 连接管理方法
    # ========================================================================
    
    def connect(self) -> "SSHClient":
        """
        建立 SSH 连接
        
        根据配置信息建立到远程服务器的 SSH 连接。
        支持密码认证和密钥认证两种方式。
        
        Returns:
            SSHClient: 返回自身，支持链式调用
            
        Raises:
            SSHConnectionError: 连接失败时抛出，包括：
                - 认证失败
                - 连接超时
                - 主机无法解析
                - 其他网络错误
        
        Example:
            >>> client = SSHClient(config)
            >>> client.connect()  # 建立连接
            >>> # 或链式调用
            >>> client.connect().execute("ls")
        """
        try:
            # 创建 SSH 客户端实例
            self._client = paramiko.SSHClient()
            
            # 设置主机密钥策略：自动添加新主机密钥（生产环境建议使用更严格的策略）
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 构建连接参数字典
            connect_kwargs = {
                "hostname": self.config.hostname,
                "port": self.config.port,
                "username": self.config.username,
                "timeout": self.config.timeout,
                "compress": self.config.compress,
            }
            
            # 根据认证方式添加相应参数
            if self.config.password:
                # 密码认证
                connect_kwargs["password"] = self.config.password
            elif self.config.key_filename:
                # 密钥认证：展开 ~ 并验证文件存在
                key_path = Path(self.config.key_filename).expanduser()
                if not key_path.exists():
                    raise SSHConnectionError(f"SSH 密钥文件不存在: {key_path}")
                connect_kwargs["key_filename"] = str(key_path)
            
            # 记录连接日志
            logger.info(f"正在连接到 {self.config.hostname}:{self.config.port}")
            
            # 建立连接
            self._client.connect(**connect_kwargs)
            logger.info(f"成功连接到 {self.config.hostname}")
            
            return self
            
        except paramiko.AuthenticationException as e:
            raise SSHConnectionError(f"认证失败: {e}")
        except socket.timeout:
            raise SSHConnectionError(f"连接超时: {self.config.hostname}")
        except socket.gaierror as e:
            raise SSHConnectionError(f"无法解析主机名: {self.config.hostname}")
        except Exception as e:
            raise SSHConnectionError(f"连接错误: {e}")
    
    def disconnect(self) -> None:
        """
        断开 SSH 连接并清理资源
        
        关闭 SFTP 和 SSH 连接，释放所有相关资源。
        即使连接已断开或出现错误，此方法也能安全执行。
        """
        # 关闭 SFTP 连接
        if self._sftp:
            try:
                self._sftp.close()
                logger.debug("SFTP 连接已关闭")
            except Exception as e:
                logger.warning(f"关闭 SFTP 连接时出错: {e}")
            finally:
                self._sftp = None
        
        # 关闭 SSH 连接
        if self._client:
            try:
                self._client.close()
                logger.debug("SSH 连接已关闭")
            except Exception as e:
                logger.warning(f"关闭 SSH 连接时出错: {e}")
            finally:
                self._client = None
    
    def is_connected(self) -> bool:
        """
        检查 SSH 连接是否处于活动状态
        
        Returns:
            bool: 连接活动返回 True，否则返回 False
        """
        if not self._client:
            return False
        
        try:
            transport = self._client.get_transport()
            return transport is not None and transport.is_active()
        except Exception:
            return False
    
    # ========================================================================
    # 上下文管理器支持
    # ========================================================================
    
    def __enter__(self) -> "SSHClient":
        """
        上下文管理器入口：自动建立连接
        
        Returns:
            SSHClient: 已连接的客户端实例
        """
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        上下文管理器出口：自动断开连接
        
        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪信息
        """
        self.disconnect()
    
    # ========================================================================
    # 命令执行方法
    # ========================================================================
    
    def execute(
        self, 
        command: str, 
        timeout: Optional[int] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> CommandResult:
        """
        在远程服务器上执行命令
        
        Args:
            command: 要执行的命令字符串
            timeout: 命令执行超时时间（秒），None 表示使用默认超时
            environment: 环境变量字典，将在命令执行前设置
        
        Returns:
            CommandResult: 包含命令执行结果的对象
        
        Raises:
            SSHCommandError: 命令执行失败时抛出
            SSHConnectionError: 未连接时抛出
        
        Example:
            >>> result = client.execute("ls -la")
            >>> if result.success:
            ...     print(result.stdout)
        """
        # 检查连接状态
        if not self._client:
            raise SSHConnectionError("未连接，请先调用 connect() 方法")
        
        try:
            logger.debug(f"执行命令: {command}")
            
            # 构建环境变量设置命令
            env_str = ""
            if environment:
                env_vars = [f"export {k}={v}" for k, v in environment.items()]
                env_str = "; ".join(env_vars) + "; "
            
            # 组合完整命令（切换到用户主目录执行）
            full_command = f"{env_str}cd ~ && {command}"
            
            # 执行命令
            stdin, stdout, stderr = self._client.exec_command(
                full_command, 
                timeout=timeout
            )
            
            # 获取命令执行结果
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode("utf-8", errors="replace")
            stderr_data = stderr.read().decode("utf-8", errors="replace")
            
            # 构建结果对象
            result = CommandResult(
                command=command,
                stdout=stdout_data,
                stderr=stderr_data,
                exit_code=exit_code
            )
            
            logger.debug(f"命令执行完成，退出码: {exit_code}")
            return result
            
        except Exception as e:
            raise SSHCommandError(f"执行命令 '{command}' 失败: {e}")
    
    def execute_sudo(
        self, 
        command: str, 
        password: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> CommandResult:
        """
        以 sudo 权限执行命令
        
        Args:
            command: 要执行的命令字符串（不需要包含 sudo 前缀）
            password: sudo 密码（如果需要），None 表示使用无密码 sudo
            timeout: 命令执行超时时间（秒）
        
        Returns:
            CommandResult: 包含命令执行结果的对象
        
        Note:
            - 如果提供了 password，将使用 `echo 'password' | sudo -S` 方式
            - 如果未提供 password，假设已配置无密码 sudo
        
        Example:
            >>> result = client.execute_sudo("systemctl restart nginx", password="mypass")
        """
        if password:
            # 使用密码方式的 sudo（-S 参数从 stdin 读取密码）
            full_command = f"echo '{password}' | sudo -S {command}"
        else:
            # 使用无密码 sudo
            full_command = f"sudo {command}"
        
        return self.execute(full_command, timeout)
    
    # ========================================================================
    # 文件传输方法
    # ========================================================================
    
    def upload_file(self, local_path: str, remote_path: str) -> None:
        """
        上传本地文件到远程服务器
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程目标路径（绝对路径）
        
        Raises:
            SSHFileTransferError: 文件传输失败时抛出
            SSHConnectionError: 未连接时抛出
        
        Example:
            >>> client.upload_file("./script.sh", "/home/user/script.sh")
        """
        # 检查连接状态
        if not self._client:
            raise SSHConnectionError("未连接，请先调用 connect() 方法")
        
        try:
            # 延迟初始化 SFTP
            if not self._sftp:
                self._sftp = self._client.open_sftp()
            
            # 验证本地文件存在
            local_file = Path(local_path)
            if not local_file.exists():
                raise SSHFileTransferError(f"本地文件不存在: {local_path}")
            
            # 执行上传
            logger.info(f"上传文件: {local_path} -> {remote_path}")
            self._sftp.put(str(local_file), remote_path)
            logger.info("文件上传完成")
            
        except Exception as e:
            raise SSHFileTransferError(f"文件上传失败: {e}")
    
    def download_file(self, remote_path: str, local_path: str) -> None:
        """
        从远程服务器下载文件到本地
        
        Args:
            remote_path: 远程文件路径（绝对路径）
            local_path: 本地目标路径
        
        Raises:
            SSHFileTransferError: 文件传输失败时抛出
            SSHConnectionError: 未连接时抛出
        
        Note:
            如果本地目录不存在，将自动创建
        
        Example:
            >>> client.download_file("/var/log/syslog", "./logs/syslog")
        """
        # 检查连接状态
        if not self._client:
            raise SSHConnectionError("未连接，请先调用 connect() 方法")
        
        try:
            # 延迟初始化 SFTP
            if not self._sftp:
                self._sftp = self._client.open_sftp()
            
            # 确保本地目录存在
            local_file = Path(local_path)
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 执行下载
            logger.info(f"下载文件: {remote_path} -> {local_path}")
            self._sftp.get(remote_path, str(local_file))
            logger.info("文件下载完成")
            
        except Exception as e:
            raise SSHFileTransferError(f"文件下载失败: {e}")
    
    def list_remote_directory(self, remote_path: str = ".") -> List[Dict[str, Any]]:
        """
        列出远程目录内容
        
        Args:
            remote_path: 远程目录路径，默认为当前目录
        
        Returns:
            List[Dict[str, Any]]: 目录项信息列表，每个字典包含：
                - name: 文件/目录名
                - size: 文件大小（字节）
                - mode: 权限模式（八进制字符串）
                - mtime: 修改时间戳
                - is_dir: 是否为目录
        
        Raises:
            SSHFileTransferError: 列出目录失败时抛出
            SSHConnectionError: 未连接时抛出
        
        Example:
            >>> entries = client.list_remote_directory("/home/user")
            >>> for entry in entries:
            ...     print(f"{entry['name']}: {entry['size']} bytes")
        """
        # 检查连接状态
        if not self._client:
            raise SSHConnectionError("未连接，请先调用 connect() 方法")
        
        try:
            # 延迟初始化 SFTP
            if not self._sftp:
                self._sftp = self._client.open_sftp()
            
            # 获取目录内容
            entries = []
            for entry in self._sftp.listdir_attr(remote_path):
                # 安全获取文件模式
                mode = entry.st_mode if entry.st_mode is not None else 0
                
                # 构建目录项信息字典
                entries.append({
                    "name": entry.filename,
                    "size": entry.st_size,
                    "mode": oct(mode)[-3:] if mode else "000",
                    "mtime": entry.st_mtime,
                    "is_dir": bool(mode & 0o40000) if mode else False  # 检查目录标志位
                })
            
            return entries
            
        except Exception as e:
            raise SSHFileTransferError(f"列出远程目录失败: {e}")
