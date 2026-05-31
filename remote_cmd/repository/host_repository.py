"""
主机存储仓库接口

定义 HostRepository 抽象基类，用于主机配置的持久化。
当前实现: JsonHostRepository
未来可实现: SqliteHostRepository, YamlHostRepository
"""

import builtins
from abc import ABC, abstractmethod
from typing import Optional

from remote_cmd.core.host import Host


class HostRepository(ABC):
    """主机配置仓库抽象基类"""

    @abstractmethod
    def save(self, host: Host) -> None:
        """保存主机（新增或覆盖）"""
        ...

    @abstractmethod
    def get(self, name: str) -> Host:
        """按名称获取主机，不存在时抛出 KeyError"""
        ...

    @abstractmethod
    def delete(self, name: str) -> None:
        """按名称删除主机，不存在时抛出 KeyError"""
        ...

    @abstractmethod
    def list(self, tag: Optional[str] = None) -> list[Host]:
        """列出主机，可选按标签筛选"""
        ...

    @abstractmethod
    def list_tags(self) -> builtins.list[str]:
        """列出所有标签"""
        ...

    @abstractmethod
    def contains(self, name: str) -> bool:
        """检查主机是否存在"""
        ...

    @abstractmethod
    def count(self) -> int:
        """返回主机数量"""
        ...

    @abstractmethod
    def flush(self) -> None:
        """将所有内存中更改写入存储"""
        ...
