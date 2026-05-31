"""
Async SSH 客户端与连接池实现（基于 asyncio 进行封装）

本文件实现 AsyncSSHClient，通过组合模式复用 Sync SSHClient 的实现，
避免阻塞事件循环。

特性：
- async connect / disconnect / execute / execute_sudo / upload_file / download_file
- 支持 async with 上下文管理器
- ConnectionPool 提供对 AsyncSSHClient 的连接复用与并发管理
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List

from .ssh_client import SSHClient, ConnectionConfig, CommandResult

logger = logging.getLogger(__name__)


class AsyncSSHClient:
    """Async 版本的 SSHClient，内部通过组合复用 Sync SSHClient 的实现。"""

    def __init__(
        self, config: ConnectionConfig, loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        self.config = config
        self._sync: SSHClient = SSHClient(config)
        self._loop = loop or asyncio.get_event_loop()
        self._connected = False

    # ------------------------------------------------------------------
    # Async API (wrapping sync SSHClient calls in thread pool)
    # ------------------------------------------------------------------
    async def connect(self) -> "AsyncSSHClient":
        if self.is_connected():
            return self
        await self._loop.run_in_executor(None, self._connect_sync)
        return self

    async def disconnect(self) -> None:
        await self._loop.run_in_executor(None, self._disconnect_sync)

    def is_connected(self) -> bool:
        return self._connected

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> CommandResult:
        return await self._loop.run_in_executor(
            None, self._execute_sync, command, timeout, environment
        )

    async def execute_sudo(
        self,
        command: str,
        password: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        return await self._loop.run_in_executor(
            None, self._execute_sudo_sync, command, password, timeout
        )

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        return await self._loop.run_in_executor(
            None, self._upload_sync, local_path, remote_path
        )

    async def download_file(self, remote_path: str, local_path: str) -> None:
        return await self._loop.run_in_executor(
            None, self._download_sync, remote_path, local_path
        )

    async def list_remote_directory(
        self, remote_path: str = "."
    ) -> List[Dict[str, Any]]:
        return await self._loop.run_in_executor(None, self._list_dir_sync, remote_path)

    # ------------------------------------------------------------------
    # Sync helpers wrapping sync SSHClient for thread-pool execution
    # ------------------------------------------------------------------
    def _connect_sync(self) -> None:
        self._sync.connect()
        self._connected = True

    def _disconnect_sync(self) -> None:
        self._sync.disconnect()
        self._connected = False

    def _execute_sync(
        self,
        command: str,
        timeout: Optional[int] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> CommandResult:
        return self._sync.execute(command, timeout=timeout, environment=environment)

    def _execute_sudo_sync(
        self,
        command: str,
        password: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        return self._sync.execute_sudo(command, password=password, timeout=timeout)

    def _upload_sync(self, local_path: str, remote_path: str) -> None:
        self._sync.upload_file(local_path, remote_path)

    def _download_sync(self, remote_path: str, local_path: str) -> None:
        self._sync.download_file(remote_path, local_path)

    def _list_dir_sync(self, remote_path: str) -> List[Dict[str, Any]]:
        return self._sync.list_remote_directory(remote_path)

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

    def __init__(
        self,
        config: ConnectionConfig,
        max_connections: int = 10,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
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
        try:
            conn = self._free.get_nowait()
            if conn.is_connected():
                return conn
        except asyncio.QueueEmpty:
            pass

        async with self._lock:
            active = len([c for c in self._connections if c.is_connected()])
            if active < self._max:
                return await self._create_connection()

        conn = await self._free.get()
        return conn

    async def release(self, conn: AsyncSSHClient) -> None:
        if conn and conn.is_connected():
            try:
                await self._free.put(conn)
            except Exception:
                await conn.disconnect()
        else:
            try:
                await conn.disconnect()
            except Exception:
                pass

    class _PoolContext:
        def __init__(self, pool: "ConnectionPool"):
            self._pool = pool
            self.conn: Optional[AsyncSSHClient] = None

        async def __aenter__(self) -> AsyncSSHClient:
            self.conn = await self._pool.acquire()
            return self.conn

        async def __aexit__(self, exc_type, exc, tb) -> None:
            if self.conn:
                await self._pool.release(self.conn)
                self.conn = None

    def acquire_context(self) -> "_PoolContext":
        return ConnectionPool._PoolContext(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        for c in self._connections:
            try:
                await c.disconnect()
            except Exception:
                pass
