"""
主机管理模块

提供远程主机的集中管理功能，包括：
- 主机配置的增删改查
- 主机标签分类管理
- 配置持久化（JSON 格式）
- 批量连接测试

Author: Vae-Scrooge
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging

from remote_cmd.core.ssh_client import SSHClient, ConnectionConfig

# 模块日志记录器
logger = logging.getLogger(__name__)


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class Host:
    """
    远程主机配置类
    
    存储单个远程主机的所有连接信息和元数据。
    支持通过标签进行分类管理。
    
    Attributes:
        name: 主机名称（唯一标识符）
        hostname: 主机地址（IP 或域名）
        username: SSH 登录用户名
        port: SSH 端口号，默认为 22
        password: 登录密码（可选）
        key_filename: SSH 私钥文件路径（可选）
        tags: 主机标签列表，用于分类和筛选
        description: 主机描述信息
    
    Example:
        >>> host = Host(
        ...     name="web-server",
        ...     hostname="192.168.1.100",
        ...     username="admin",
        ...     key_filename="~/.ssh/id_rsa",
        ...     tags=["production", "web"]
        ... )
    """
    
    name: str
    hostname: str
    username: str
    port: int = 22
    password: Optional[str] = None
    key_filename: Optional[str] = None
    tags: Optional[List[str]] = None
    description: str = ""
    
    def __post_init__(self):
        """初始化后处理：设置默认标签列表"""
        if self.tags is None:
            self.tags = []
    
    def to_connection_config(self) -> ConnectionConfig:
        """
        将主机配置转换为 SSH 连接配置
        
        Returns:
            ConnectionConfig: 可直接用于 SSHClient 的连接配置对象
        
        Example:
            >>> config = host.to_connection_config()
            >>> client = SSHClient(config)
        """
        return ConnectionConfig(
            hostname=self.hostname,
            username=self.username,
            port=self.port,
            password=self.password,
            key_filename=self.key_filename
        )
    
    def to_dict(self) -> Dict:
        """
        将主机配置转换为字典
        
        Returns:
            Dict: 包含所有主机属性的字典
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Host":
        """
        从字典创建主机配置对象
        
        Args:
            data: 包含主机属性的字典
        
        Returns:
            Host: 主机配置对象
        
        Example:
            >>> host = Host.from_dict({
            ...     "name": "server1",
            ...     "hostname": "192.168.1.1",
            ...     "username": "admin"
            ... })
        """
        return cls(**data)


# ============================================================================
# 主机管理器类
# ============================================================================

class HostManager:
    """
    主机管理器类
    
    集中管理多个远程主机的配置信息，提供持久化存储、
    分类标签、连接测试等功能。
    
    主要功能：
    - 主机的增删改查
    - 按标签筛选主机
    - 配置导入导出（JSON 格式）
    - 批量连接测试
    
    使用示例：
        >>> manager = HostManager()
        >>> manager.add_host(Host(
        ...     name="web-server",
        ...     hostname="192.168.1.100",
        ...     username="admin",
        ...     key_filename="~/.ssh/id_rsa"
        ... ))
        >>> manager.save_to_file("hosts.json")
    
    Attributes:
        hosts: 主机字典，键为主机名称，值为 Host 对象
        hosts_file: 默认配置文件路径（可选）
    """
    
    def __init__(self, hosts_file: Optional[str] = None):
        """
        初始化主机管理器
        
        Args:
            hosts_file: 配置文件路径（可选）。如果文件存在，将自动加载配置。
        """
        self.hosts: Dict[str, Host] = {}
        self.hosts_file = hosts_file
        
        # 如果指定了配置文件且文件存在，自动加载
        if hosts_file and Path(hosts_file).exists():
            self.load_from_file(hosts_file)
    
    # ========================================================================
    # 主机管理方法
    # ========================================================================
    
    def add_host(self, host: Host) -> None:
        """
        添加主机到管理器
        
        Args:
            host: 要添加的主机配置对象
        
        Raises:
            ValueError: 如果同名主机已存在
        
        Example:
            >>> manager.add_host(Host(
            ...     name="new-server",
            ...     hostname="192.168.1.200",
            ...     username="admin"
            ... ))
        """
        if host.name in self.hosts:
            raise ValueError(f"主机 '{host.name}' 已存在")
        
        self.hosts[host.name] = host
        logger.info(f"已添加主机: {host.name}")
    
    def remove_host(self, name: str) -> None:
        """
        从管理器中移除主机
        
        Args:
            name: 要移除的主机名称
        
        Raises:
            KeyError: 如果指定的主机不存在
        
        Example:
            >>> manager.remove_host("old-server")
        """
        if name not in self.hosts:
            raise KeyError(f"主机 '{name}' 不存在")
        
        del self.hosts[name]
        logger.info(f"已移除主机: {name}")
    
    def get_host(self, name: str) -> Host:
        """
        获取指定主机的配置
        
        Args:
            name: 主机名称
        
        Returns:
            Host: 主机配置对象
        
        Raises:
            KeyError: 如果指定的主机不存在
        
        Example:
            >>> host = manager.get_host("web-server")
            >>> print(host.hostname)
        """
        if name not in self.hosts:
            raise KeyError(f"主机 '{name}' 不存在")
        return self.hosts[name]
    
    def list_hosts(self, tag: Optional[str] = None) -> List[Host]:
        """
        获取主机列表
        
        Args:
            tag: 可选的标签筛选条件。如果指定，只返回包含该标签的主机。
        
        Returns:
            List[Host]: 主机配置对象列表
        
        Example:
            >>> # 获取所有主机
            >>> all_hosts = manager.list_hosts()
            >>> 
            >>> # 获取特定标签的主机
            >>> web_hosts = manager.list_hosts(tag="web")
        """
        hosts = list(self.hosts.values())
        
        if tag:
            # 筛选包含指定标签的主机
            hosts = [h for h in hosts if h.tags and tag in h.tags]
        
        return hosts
    
    def list_tags(self) -> List[str]:
        """
        获取所有使用的标签列表
        
        Returns:
            List[str]: 排序后的标签名称列表
        
        Example:
            >>> tags = manager.list_tags()
            >>> print(tags)  # ['database', 'production', 'web']
        """
        tags = set()
        for host in self.hosts.values():
            if host.tags:
                tags.update(host.tags)
        return sorted(list(tags))
    
    # ========================================================================
    # 持久化方法
    # ========================================================================
    
    def save_to_file(self, filepath: str) -> None:
        """
        将主机配置保存到 JSON 文件
        
        Args:
            filepath: 目标文件路径
        
        Note:
            - 如果目录不存在，将自动创建
            - 使用 UTF-8 编码保存，支持中文
        
        Example:
            >>> manager.save_to_file("config/hosts.json")
        """
        # 转换为字典格式
        data = {name: host.to_dict() for name, host in self.hosts.items()}
        
        # 确保目录存在
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"已保存 {len(self.hosts)} 个主机配置到 {filepath}")
    
    def load_from_file(self, filepath: str) -> None:
        """
        从 JSON 文件加载主机配置
        
        Args:
            filepath: 配置文件路径
        
        Note:
            如果文件不存在，将记录警告日志但不抛出异常
        
        Example:
            >>> manager.load_from_file("config/hosts.json")
        """
        path = Path(filepath)
        
        if not path.exists():
            logger.warning(f"配置文件不存在: {filepath}")
            return
        
        # 读取并解析文件
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 转换为 Host 对象
        self.hosts = {
            name: Host.from_dict(host_data) 
            for name, host_data in data.items()
        }
        
        logger.info(f"从 {filepath} 加载了 {len(self.hosts)} 个主机配置")
    
    # ========================================================================
    # 连接测试方法
    # ========================================================================
    
    def connect_to_host(self, name: str) -> SSHClient:
        """
        建立到指定主机的 SSH 连接
        
        Args:
            name: 主机名称
        
        Returns:
            SSHClient: 已连接的 SSH 客户端实例
        
        Raises:
            KeyError: 如果指定的主机不存在
            SSHConnectionError: 如果连接失败
        
        Note:
            返回的客户端需要手动管理连接生命周期（建议使用上下文管理器）
        
        Example:
            >>> with manager.connect_to_host("web-server") as client:
            ...     result = client.execute("uptime")
        """
        host = self.get_host(name)
        config = host.to_connection_config()
        client = SSHClient(config)
        return client.connect()
    
    def test_connection(self, name: str) -> bool:
        """
        测试到指定主机的连接
        
        Args:
            name: 主机名称
        
        Returns:
            bool: 连接成功返回 True，失败返回 False
        
        Example:
            >>> if manager.test_connection("web-server"):
            ...     print("连接正常")
        """
        try:
            with self.connect_to_host(name) as client:
                return client.is_connected()
        except Exception as e:
            logger.error(f"主机 {name} 连接测试失败: {e}")
            return False
    
    def test_all_connections(self) -> Dict[str, bool]:
        """
        测试所有主机的连接状态
        
        Returns:
            Dict[str, bool]: 主机名称到连接状态的映射字典
        
        Example:
            >>> results = manager.test_all_connections()
            >>> for name, success in results.items():
            ...     status = "✓" if success else "✗"
            ...     print(f"{status} {name}")
        """
        results = {}
        for name in self.hosts:
            results[name] = self.test_connection(name)
        return results
    
    # ========================================================================
    # 魔术方法
    # ========================================================================
    
    def __len__(self) -> int:
        """返回管理的主机数量"""
        return len(self.hosts)
    
    def __contains__(self, name: str) -> bool:
        """检查指定名称的主机是否存在"""
        return name in self.hosts
