"""
Async SSH 客户端与连接池实现（基于 asyncio 进行封装）

本文件实现 AsyncSSHClient，为现有的 Sync SSHClient 提供异步接口，
通过在后台线程执行阻塞的 Paramiko 调用来实现异步行为，避免阻塞事件循环。

特性：
- async connect / disconnect / execute / execute_sudo / upload_file / download_file
- 支持 async with 上下文管理器
- ConnectionPool 提供对 AsyncSSHClient 的连接复用与并发管理
"""

import asyncio
import socket
import logging
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

import paramiko

from .ssh_client import ConnectionConfig, SSHConnectionError, SSHCommandError, SSHFileTransferError
from .ssh_client import CommandResult  # reuse result container

logger = logging.getLogger(__name__)


class AsyncSSHClient:
    """Async 版本的 SSHClient，内部通过线程池执行阻塞 I/O。"""

    def __init__(self, config: ConnectionConfig, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.config = config
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._loop = loop or asyncio.get_event_loop()
        self._connected = False

    # ------------------------------------------------------------------
    # Internal blocking implementations (同步逻辑复用于线程中执行)
    # ------------------------------------------------------------------
    def _connect_sync(self) -> None:
        # 阻塞实现，内部通过线程执行
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": self.config.hostname,
            "port": self.config.port,
            "username": self.config.username,
            "timeout": self.config.timeout,
            "compress": self.config.compress,
        }

        if self.config.password:
            connect_kwargs["password"] = self.config.password
        elif self.config.key_filename:
            key_path = Path(self.config.key_filename).expanduser()
            if not key_path.exists():
                raise SSHConnectionError(f"SSH 密钥文件不存在: {key_path}")
            connect_kwargs["key_filename"] = str(key_path)

        logger.info(f"[async] 正在连接到 {self.config.hostname}:{self.config.port}")
        self._client.connect(**connect_kwargs)
        self._connected = True

    def _disconnect_sync(self) -> None:
        if self._sftp:
            try:
                self._sftp.close()
            except Exception as e:
                logger.warning(f"[async] 关闭 SFTP 时出错: {e}")
            finally:
                self._sftp = None
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"[async] 关闭 SSH 时出错: {e}")
            finally:
                self._client = None
        self._connected = False

    def _is_connected_sync(self) -> bool:
        if not self._client:
            return False
        try:
            transport = self._client.get_transport()
            return transport is not None and transport.is_active()
        except Exception:
            return False

    def _exec_sync(self, command: str, timeout: Optional[int] = None, environment: Optional[Dict[str, str]] = None) -> CommandResult:
        if not self._client:
            raise SSHConnectionError("未连接，请先调用 connect() 方法")

        try:
            env_str = ""
            if environment:
                env_vars = [f"export {k}={v}" for k, v in environment.items()]
                env_str = "; ".join(env_vars) + "; "

            full_command = f"{env_str}cd ~ && {command}"

            stdin, stdout, stderr = self._client.exec_command(full_command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode("utf-8", errors="replace")
            stderr_data = stderr.read().decode("utf-8", errors="replace")
            return CommandResult(command=command, stdout=stdout_data, stderr=stderr_data, exit_code=exit_code)
        except Exception as e:
            raise SSHCommandError(f"执行命令 '{command}' 失败: {e}")

    def _exec_sudo_sync(self, command: str, password: Optional[str], timeout: Optional[int] = None) -> CommandResult:
        if not self._client:
            raise SSHConnectionError("未连接，请先调用 connect() 方法")

        if password is None:
            full_command = f"sudo {command}"
            env_str = "cd ~ && "
            full_command = f"{env_str}{full_command}"
            stdin, stdout, stderr = self._client.exec_command(full_command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode("utf-8", errors="replace")
            stderr_data = stderr.read().decode("utf-8", errors="replace")
            return CommandResult(command=command, stdout=stdout_data, stderr=stderr_data, exit_code=exit_code)

        # 安全方式：使用交互式 shell
        try:
            channel = self._client.invoke_shell()
        except Exception as e:
            return CommandResult(stdout=str(e), stderr="sudo interactive mode failed", exit_code=1)

        timeout_sec = timeout or 120
        start_time = time.time()
        prompt_sentinel = "__SSH_SUDO_PASSWORD_PROMPT__"
        done_sentinel = "__SSH_SUDO_COMMAND_DONE__"

        wrapped_command = f"sudo -S -p '{prompt_sentinel}' {command}; echo {done_sentinel}$?\n"
        channel.send(wrapped_command)

        stdout_buf = []
        exit_code = None
        password_sent = False

        while True:
            if time.time() - start_time > timeout_sec:
                try:
                    channel.close()
                except Exception:
                    pass
                break

            if channel.recv_ready():
                try:
                    data = channel.recv(4096)
                    if data:
                        stdout_buf.append(data.decode(errors="replace"))
                        text = data.decode(errors="replace").lower()
                        if not password_sent and ("password" in text or "[sudo]" in text or "password for" in text):
                            channel.send(password + "\n")
                            password_sent = True
                        joined = "".join(stdout_buf)
                        marker_idx = joined.find(done_sentinel)
                        if marker_idx != -1:
                            after = joined[marker_idx + len(done_sentinel):]
                            m = re.match(r"(-?\d+)", after)
                            exit_code = int(m.group(1)) if m else 0
                            break
                except Exception:
                    pass

            time.sleep(0.05)

        try:
            channel.close()
        except Exception:
            pass

        stdout = "".join(stdout_buf)
        if exit_code is None:
            exit_code = 0

        return CommandResult(stdout=stdout, stderr="", exit_code=exit_code)

    def _upload_sync(self, local_path: str, remote_path: str) -> None:
        if not self._client:
            raise SSHConnectionError("未连接，请先调用 connect() 方法")
        if not self._sftp:
            self._sftp = self._client.open_sftp()
        local_file = Path(local_path)
        if not local_file.exists():
            raise SSHFileTransferError(f"本地文件不存在: {local_path}")
        self._sftp.put(str(local_file), remote_path)

    def _download_sync(self, remote_path: str, local_path: str) -> None:
        if not self._client:
            raise SSHConnectionError("未连接，请先调用 connect() 方法")
        if not self._sftp:
            self._sftp = self._client.open_sftp()
        local_file = Path(local_path)
        local_file.parent.mkdir(parents=True, exist_ok=True)
        self._sftp.get(remote_path, str(local_file))

    def _list_dir_sync(self, remote_path: str) -> List[Dict[str, Any]]:
        if not self._client:
            raise SSHConnectionError("未连接，请先调用 connect() 方法")
        if not self._sftp:
            self._sftp = self._client.open_sftp()
        entries = []
        for entry in self._sftp.listdir_attr(remote_path):
            mode = entry.st_mode if entry.st_mode is not None else 0
            entries.append({
                "name": entry.filename,
                "size": entry.st_size,
                "mode": oct(mode)[-3:] if mode else "000",
                "mtime": entry.st_mtime,
                "is_dir": bool(mode & 0o40000) if mode else False,
            })
        return entries

    # ------------------------------------------------------------------
    # Async API (wrapping blocking implementations in thread pool)
    # ------------------------------------------------------------------
    async def connect(self) -> "AsyncSSHClient":
        if self.is_connected():
            return self
        await self._loop.run_in_executor(None, self._connect_sync)
        return self

    async def disconnect(self) -> None:
        await self._loop.run_in_executor(None, self._disconnect_sync)

    def is_connected(self) -> bool:
        return self._is_connected_sync()

    async def execute(self, command: str, timeout: Optional[int] = None, environment: Optional[Dict[str, str]] = None) -> CommandResult:
        return await self._loop.run_in_executor(None, self._exec_sync, command, timeout, environment)

    async def execute_sudo(self, command: str, password: Optional[str] = None, timeout: Optional[int] = None) -> CommandResult:
        # 使用带参数的中间封装
        return await self._loop.run_in_executor(None, self._exec_sudo_sync, command, password, timeout)

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        await self._loop.run_in_executor(None, self._upload_sync, local_path, remote_path)

    async def download_file(self, remote_path: str, local_path: str) -> None:
        await self._loop.run_in_executor(None, self._download_sync, remote_path, local_path)

    async def list_remote_directory(self, remote_path: str = ".") -> List[Dict[str, Any]]:
        return await self._loop.run_in_executor(None, self._list_dir_sync, remote_path)

    # ------------------------------------------------------------------
    # Async context manager support
    # ------------------------------------------------------------------
    async def __aenter__(self) -> "AsyncSSHClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.disconnect()


class ConnectionPool:
    """异步 SSH 连接池，复用 AsyncSSHClient 实例。"""

    def __init__(self, config: ConnectionConfig, max_connections: int = 10, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.config = config
        self._max = max_connections
        self._loop = loop or asyncio.get_event_loop()
        self._connections: List[AsyncSSHClient] = []
        self._free: asyncio.Queue[AsyncSSHClient] = asyncio.Queue()
        self._lock = asyncio.Lock()

    async def _create_connection(self) -> AsyncSSHClient:
        client = AsyncSSHClient(self.config, loop=self._loop)
        await client.connect()
        self._connections.append(client)
        return client

    async def acquire(self) -> AsyncSSHClient:
        # 优先尝试获取已空闲的连接
        try:
            conn = self._free.get_nowait()
            if conn.is_connected():
                return conn
        except asyncio.QueueEmpty:
            pass

        async with self._lock:
            # 如果还未达到最大连接数，创建一个新连接
            if len([c for c in self._connections if c.is_connected()]) < self._max:
                return await self._create_connection()

        # 否则等待一个可用连接
        conn = await self._free.get()
        return conn

    async def release(self, conn: AsyncSSHClient) -> None:
        if conn and conn.is_connected():
            try:
                await self._free.put(conn)
            except Exception:
                # 回收失败，尝试断开并清理
                await conn.disconnect()
        else:
            # 非活动连接，尝试断开并丢弃
            try:
                await conn.disconnect()
            except Exception:
                pass

    # 上下文管理器：返回一个可上下文的对象，便于语法 sugar
    class _PoolContext:
        def __init__(self, pool: "ConnectionPool"):  # type: ignore
            self._pool = pool
            self.conn: Optional[AsyncSSHClient] = None

        async def __aenter__(self) -> AsyncSSHClient:
            self.conn = await self._pool.acquire()
            return self.conn

        async def __aexit__(self, exc_type, exc, tb) -> None:
            if self.conn:
                await self._pool.release(self.conn)
                self.conn = None

    def acquire_context(self) -> "ConnectionPool._PoolContext":
        return ConnectionPool._PoolContext(self)

    # 快捷方法：用于直接使用 async with pool.acquire_context() as conn:
    async def __aenter__(self):  # pragma: no cover - convenience
        # 直接返回一个上下文管理器，以便直接用作 `async with pool_acquire()`
        return self

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover
        # 在退出时断开所有连接，作为安全兜底
        for c in self._connections:
            try:
                await c.disconnect()
            except Exception:
                pass
