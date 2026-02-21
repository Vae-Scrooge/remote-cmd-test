"""
主机管理器单元测试

测试 HostManager 和 Host 类的功能。
使用 pytest 进行测试。

测试覆盖：
- Host 数据类功能
- HostManager 主机管理
- 配置持久化（JSON）
- 连接测试

运行方式：
    pytest tests/test_host_manager.py -v
"""

import pytest
import json
import tempfile
from pathlib import Path

from remote_cmd.core.host_manager import HostManager, Host
from remote_cmd.utils.exceptions import SSHConnectionError


# ============================================================================
# Host 数据类测试
# ============================================================================

class TestHost:
    """Host 数据类测试"""
    
    def test_host_creation(self):
        """测试：创建主机配置"""
        host = Host(
            name="test-server",
            hostname="192.168.1.100",
            username="admin",
            password="secret",
            tags=["web", "production"]
        )
        
        assert host.name == "test-server"
        assert host.hostname == "192.168.1.100"
        assert host.username == "admin"
        assert host.tags == ["web", "production"]
    
    def test_host_to_dict(self):
        """测试：主机配置转字典"""
        host = Host(
            name="test-server",
            hostname="192.168.1.100",
            username="admin"
        )
        
        data = host.to_dict()
        
        assert data["name"] == "test-server"
        assert data["hostname"] == "192.168.1.100"
    
    def test_host_from_dict(self):
        """测试：从字典创建主机配置"""
        data = {
            "name": "test-server",
            "hostname": "192.168.1.100",
            "username": "admin",
            "port": 2222,
            "tags": ["db"]
        }
        
        host = Host.from_dict(data)
        
        assert host.name == "test-server"
        assert host.port == 2222
        assert host.tags == ["db"]
    
    def test_to_connection_config(self):
        """测试：转换为 SSH 连接配置"""
        host = Host(
            name="test-server",
            hostname="192.168.1.100",
            username="admin",
            password="secret",
            port=2222
        )
        
        config = host.to_connection_config()
        
        assert config.hostname == "192.168.1.100"
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.port == 2222


# ============================================================================
# HostManager 测试
# ============================================================================

class TestHostManager:
    """HostManager 主机管理器测试"""
    
    def test_add_host(self):
        """测试：添加主机"""
        manager = HostManager()
        host = Host(name="server1", hostname="192.168.1.1", username="admin")
        
        manager.add_host(host)
        
        assert "server1" in manager
        assert len(manager) == 1
        
        retrieved_host = manager.get_host("server1")
        assert retrieved_host.hostname == "192.168.1.1"
    
    def test_add_duplicate_host(self):
        """测试：添加重复主机应抛出异常"""
        manager = HostManager()
        host = Host(name="server1", hostname="192.168.1.1", username="admin")
        
        manager.add_host(host)
        
        with pytest.raises(ValueError, match="已存在"):
            manager.add_host(host)
    
    def test_remove_host(self):
        """测试：移除主机"""
        manager = HostManager()
        host = Host(name="server1", hostname="192.168.1.1", username="admin")
        
        manager.add_host(host)
        manager.remove_host("server1")
        
        assert "server1" not in manager
        assert len(manager) == 0
    
    def test_remove_nonexistent_host(self):
        """测试：移除不存在的主机应抛出异常"""
        manager = HostManager()
        
        with pytest.raises(KeyError, match="不存在"):
            manager.remove_host("nonexistent")
    
    def test_list_hosts(self):
        """测试：列出主机"""
        manager = HostManager()
        
        manager.add_host(Host(name="web1", hostname="192.168.1.1", username="admin", tags=["web"]))
        manager.add_host(Host(name="db1", hostname="192.168.1.2", username="admin", tags=["db"]))
        manager.add_host(Host(name="web2", hostname="192.168.1.3", username="admin", tags=["web"]))
        
        # 列出所有主机
        all_hosts = manager.list_hosts()
        assert len(all_hosts) == 3
        
        # 按标签筛选
        web_hosts = manager.list_hosts(tag="web")
        assert len(web_hosts) == 2
        
        db_hosts = manager.list_hosts(tag="db")
        assert len(db_hosts) == 1
    
    def test_list_tags(self):
        """测试：列出所有标签"""
        manager = HostManager()
        
        manager.add_host(Host(name="web1", hostname="192.168.1.1", username="admin", tags=["web", "production"]))
        manager.add_host(Host(name="db1", hostname="192.168.1.2", username="admin", tags=["db", "production"]))
        
        tags = manager.list_tags()
        
        assert tags == ["db", "production", "web"]
    
    def test_save_and_load(self):
        """测试：保存和加载配置"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            # 保存配置
            manager = HostManager()
            manager.add_host(Host(name="server1", hostname="192.168.1.1", username="admin"))
            manager.add_host(Host(name="server2", hostname="192.168.1.2", username="root"))
            
            manager.save_to_file(temp_path)
            
            # 加载配置到新管理器
            new_manager = HostManager(temp_path)
            
            assert len(new_manager) == 2
            assert "server1" in new_manager
            assert "server2" in new_manager
            assert new_manager.get_host("server1").hostname == "192.168.1.1"
        finally:
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)
    
    def test_contains(self):
        """测试：检查主机是否存在"""
        manager = HostManager()
        host = Host(name="server1", hostname="192.168.1.1", username="admin")
        
        manager.add_host(host)
        
        assert "server1" in manager
        assert "server2" not in manager


# ============================================================================
# 程序入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
