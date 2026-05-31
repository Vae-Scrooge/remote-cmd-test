"""
凭据提供链模块

定义凭据获取的抽象接口和多种实现：
1. EnvCredentialProvider: 从环境变量获取密码
2. EncryptedFileCredentialProvider: 从加密存储获取密码
3. ChainCredentialProvider: 按优先级链式尝试

使用策略:
    >>> from remote_cmd.service.credential_provider import (
    ...     EnvCredentialProvider,
    ...     EncryptedFileCredentialProvider,
    ...     ChainCredentialProvider,
    ... )
    >>> from remote_cmd.repository.json_host_repository import JsonHostRepository
    >>> provider = ChainCredentialProvider([
    ...     EnvCredentialProvider("REMOTE_CMD_PASSWORD"),
    ...     EncryptedFileCredentialProvider(repo),  # 从加密的 hosts.json 读取
    ... ])
    >>> password = provider.get_password(host)
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, List

from remote_cmd.core.host import Host
from remote_cmd.repository.host_repository import HostRepository
from remote_cmd.utils.crypto import CredentialEncryption

logger = logging.getLogger(__name__)


class CredentialProvider(ABC):
    """凭据提供者抽象基类"""

    @abstractmethod
    def get_password(self, host: Host) -> Optional[str]:
        """获取指定主机的密码，无可返回 None"""
        ...


class EnvCredentialProvider(CredentialProvider):
    """
    从环境变量获取密码

    适用于 CI/CD 或容器环境。
    优先级低于交互式输入但高于默认值。

    Args:
        env_var: 环境变量名（默认 REMOTE_CMD_PASSWORD）
    """

    def __init__(self, env_var: str = "REMOTE_CMD_PASSWORD"):
        self._env_var = env_var

    def get_password(self, host: Host) -> Optional[str]:
        password = os.environ.get(self._env_var)
        return password


class EncryptedFileCredentialProvider(CredentialProvider):
    """
    从加密的 hosts.json 获取密码

    通过 CredentialEncryption 解密已存储的加密密码。
    适用于持久化保存密码的场景。
    """

    def __init__(
        self,
        repo: HostRepository,
        encryption: Optional[CredentialEncryption] = None,
    ):
        self._repo = repo
        self._encryption = encryption or CredentialEncryption()

    def get_password(self, host: Host) -> Optional[str]:
        try:
            stored_host = self._repo.get(host.name)
            pw = stored_host.password
            if pw and self._encryption.is_encrypted(pw):
                return self._encryption.decrypt(pw)
            return pw
        except (KeyError, Exception):
            return None


class ChainCredentialProvider(CredentialProvider):
    """
    链式凭据提供者

    按顺序尝试每个提供者，返回第一个非空结果。
    适用于 "环境变量 → 加密文件 → 交互式输入" 的优先级链。

    Args:
        providers: 凭据提供者列表，按优先级降序排列
    """

    def __init__(self, providers: List[CredentialProvider]):
        self._providers = list(providers)

    def get_password(self, host: Host) -> Optional[str]:
        for provider in self._providers:
            password = provider.get_password(host)
            if password is not None:
                return password
        return None

    def add_provider(self, provider: CredentialProvider) -> None:
        """在链尾添加一个提供者"""
        self._providers.append(provider)
