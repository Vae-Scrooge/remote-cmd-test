"""
主机业务逻辑服务

协调 Repository 和 CredentialProvider 完成主机管理。
职责：
    - 主机 CRUD 委托给 Repository
    - 凭据解析委托给 CredentialProvider 链
    - 密码加密委托给 CredentialEncryption
    - SSH 连接测试委托给 SSHService

使用示例:
    >>> from remote_cmd.service.host_service import HostService
    >>> from remote_cmd.repository.json_host_repository import JsonHostRepository
    >>> from remote_cmd.service.credential_provider import (
    ...     EnvCredentialProvider, ChainCredentialProvider
    ... )
    >>>
    >>> repo = JsonHostRepository("hosts.json")
    >>> cred_provider = ChainCredentialProvider([EnvCredentialProvider()])
    >>> service = HostService(repo, credential_provider=cred_provider)
    >>>
    >>> service.add_host(host)
    >>> service.test_connection("web-server")
"""

import logging
from typing import Dict, List, Optional

from remote_cmd.core.host import Host
from remote_cmd.core.ssh_client import SSHClient
from remote_cmd.repository.host_repository import HostRepository
from remote_cmd.service.credential_provider import (
    CredentialProvider,
    ChainCredentialProvider,
    EnvCredentialProvider,
    EncryptedFileCredentialProvider,
)
from remote_cmd.service.ssh_service import SSHService
from remote_cmd.utils.crypto import CredentialEncryption

logger = logging.getLogger(__name__)


class HostService:
    """
    主机业务逻辑服务

    Args:
        repository: 主机配置仓库
        credential_provider: 凭据提供者（可选）
        encryption: 密码加密器（可选）
        ssh_service: SSH 连接服务（可选，自动创建）
    """

    def __init__(
        self,
        repository: HostRepository,
        credential_provider: Optional[CredentialProvider] = None,
        encryption: Optional[CredentialEncryption] = None,
        ssh_service: Optional[SSHService] = None,
    ):
        self._repo = repository
        self._encryption = encryption or CredentialEncryption()
        self._ssh = ssh_service or SSHService()

        if credential_provider:
            self._cred_provider = credential_provider
        else:
            # 默认凭据链: 环境变量 → 加密文件
            self._cred_provider = ChainCredentialProvider(
                [
                    EnvCredentialProvider(),
                    EncryptedFileCredentialProvider(repository, self._encryption),
                ]
            )

    # ========================================================================
    # 主机管理
    # ========================================================================

    def add_host(self, host: Host) -> Host:
        """
        添加主机

        Args:
            host: 主机配置

        Returns:
            Host: 已添加的主机

        Raises:
            ValueError: 同名主机已存在
        """
        if self._repo.contains(host.name):
            raise ValueError(f"主机 '{host.name}' 已存在")

        # 加密密码（如果明文）
        if host.password and not self._encryption.is_encrypted(host.password):
            host.password = self._encryption.encrypt(host.password)

        self._repo.save(host)
        self._repo.flush()
        logger.info(f"已添加主机: {host.name}")
        return host

    def get_host(self, name: str) -> Host:
        """获取主机配置（密码自动解密）"""
        host = self._repo.get(name)
        return self._decrypt_host(host)

    def update_host(self, name: str, **kwargs) -> Host:
        """
        更新主机配置

        Args:
            name: 主机名
            **kwargs: 要更新的字段

        Returns:
            Host: 更新后的主机
        """
        host = self._repo.get(name)
        for key, value in kwargs.items():
            if hasattr(host, key):
                setattr(host, key, value)

        # 如果密码被更新，重新加密
        if "password" in kwargs and kwargs["password"] is not None:
            if not self._encryption.is_encrypted(kwargs["password"]):
                host.password = self._encryption.encrypt(kwargs["password"])

        self._repo.save(host)
        self._repo.flush()
        logger.info(f"已更新主机: {name}")
        return host

    def remove_host(self, name: str) -> None:
        """删除主机"""
        self._repo.delete(name)
        self._repo.flush()
        logger.info(f"已删除主机: {name}")

    def list_hosts(self, tag: Optional[str] = None) -> List[Host]:
        """列出主机（密码自动解密）"""
        hosts = self._repo.list(tag=tag)
        return [self._decrypt_host(h) for h in hosts]

    def list_tags(self) -> List[str]:
        """列出所有标签"""
        return self._repo.list_tags()

    # ========================================================================
    # 连接管理
    # ========================================================================

    def connect_to_host(self, name: str) -> SSHClient:
        """
        建立到主机的 SSH 连接

        Args:
            name: 主机名

        Returns:
            SSHClient: 已连接的客户端
        """
        host = self._resolve_host(name)
        client = self._ssh.create_client(
            hostname=host.hostname,
            username=host.username,
            port=host.port,
            password=host.password,
            key_filename=host.key_filename,
        )
        return client

    def test_connection(self, name: str) -> bool:
        """
        测试主机连接

        Args:
            name: 主机名

        Returns:
            bool: 连接成功返回 True
        """
        host = self._resolve_host(name)
        return self._ssh.test_connection(
            hostname=host.hostname,
            username=host.username,
            port=host.port,
            password=host.password,
            key_filename=host.key_filename,
        )

    def test_all_connections(self, max_workers: int = 10) -> Dict[str, bool]:
        """并行测试所有主机连接"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        hosts = self._repo.list()
        results: Dict[str, bool] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self.test_connection, h.name): h.name for h in hosts
            }
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    logger.error(f"主机 {name} 连接测试异常: {e}")
                    results[name] = False

        return results

    def _decrypt_host(self, host: Host) -> Host:
        """返回主机副本，密码字段自动解密（如已加密）"""
        if host.password and self._encryption.is_encrypted(host.password):
            try:
                decrypted = self._encryption.decrypt(host.password)
                return Host(
                    name=host.name,
                    hostname=host.hostname,
                    username=host.username,
                    port=host.port,
                    password=decrypted,
                    key_filename=host.key_filename,
                    tags=host.tags,
                    description=host.description,
                )
            except Exception as e:
                logger.warning(f"密码解密失败 ({host.name}): {e}")
        return host

    def _resolve_host(self, name: str) -> Host:
        """
        获取主机并尝试解密密码

        如果主机有加密密码，先通过凭据链获取明文。
        """
        host = self._repo.get(name)

        # 尝试解密密码
        if host.password and self._encryption.is_encrypted(host.password):
            resolved = self._cred_provider.get_password(host)
            if resolved:
                host.password = resolved

        # 尝试解析密钥路径
        if host.key_filename:
            from pathlib import Path

            host.key_filename = str(Path(host.key_filename).expanduser())

        return host
