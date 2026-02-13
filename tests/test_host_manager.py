# test_host_manager.py
import pytest
import json
import tempfile
from pathlib import Path
from remote_cmd.core.host_manager import HostManager, Host
from remote_cmd.utils.exceptions import SSHConnectionError


class TestHost:
    def test_host_creation(self):
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
        host = Host(
            name="test-server",
            hostname="192.168.1.100",
            username="admin"
        )
        
        data = host.to_dict()
        assert data["name"] == "test-server"
        assert data["hostname"] == "192.168.1.100"
    
    def test_host_from_dict(self):
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


class TestHostManager:
    def test_add_host(self):
        manager = HostManager()
        host = Host(name="server1", hostname="192.168.1.1", username="admin")
        
        manager.add_host(host)
        
        assert "server1" in manager
        assert len(manager) == 1
        retrieved_host = manager.get_host("server1")
        assert retrieved_host.hostname == "192.168.1.1"
    
    def test_add_duplicate_host(self):
        manager = HostManager()
        host = Host(name="server1", hostname="192.168.1.1", username="admin")
        
        manager.add_host(host)
        
        with pytest.raises(ValueError, match="already exists"):
            manager.add_host(host)
    
    def test_remove_host(self):
        manager = HostManager()
        host = Host(name="server1", hostname="192.168.1.1", username="admin")
        
        manager.add_host(host)
        manager.remove_host("server1")
        
        assert "server1" not in manager
        assert len(manager) == 0
    
    def test_remove_nonexistent_host(self):
        manager = HostManager()
        
        with pytest.raises(KeyError, match="not found"):
            manager.remove_host("nonexistent")
    
    def test_list_hosts(self):
        manager = HostManager()
        manager.add_host(Host(name="web1", hostname="192.168.1.1", username="admin", tags=["web"]))
        manager.add_host(Host(name="db1", hostname="192.168.1.2", username="admin", tags=["db"]))
        manager.add_host(Host(name="web2", hostname="192.168.1.3", username="admin", tags=["web"]))
        
        all_hosts = manager.list_hosts()
        assert len(all_hosts) == 3
        
        web_hosts = manager.list_hosts(tag="web")
        assert len(web_hosts) == 2
        
        db_hosts = manager.list_hosts(tag="db")
        assert len(db_hosts) == 1
    
    def test_list_tags(self):
        manager = HostManager()
        manager.add_host(Host(name="web1", hostname="192.168.1.1", username="admin", tags=["web", "production"]))
        manager.add_host(Host(name="db1", hostname="192.168.1.2", username="admin", tags=["db", "production"]))
        
        tags = manager.list_tags()
        assert tags == ["db", "production", "web"]
    
    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            manager = HostManager()
            manager.add_host(Host(name="server1", hostname="192.168.1.1", username="admin"))
            manager.add_host(Host(name="server2", hostname="192.168.1.2", username="root"))
            
            manager.save_to_file(temp_path)
            
            # Load in new manager
            new_manager = HostManager(temp_path)
            
            assert len(new_manager) == 2
            assert "server1" in new_manager
            assert "server2" in new_manager
            assert new_manager.get_host("server1").hostname == "192.168.1.1"
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_contains(self):
        manager = HostManager()
        host = Host(name="server1", hostname="192.168.1.1", username="admin")
        
        manager.add_host(host)
        
        assert "server1" in manager
        assert "server2" not in manager


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
