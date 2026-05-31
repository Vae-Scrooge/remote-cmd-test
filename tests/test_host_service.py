"""主机业务逻辑服务测试"""

import pytest

from remote_cmd.core.host import Host
from remote_cmd.repository.json_host_repository import JsonHostRepository
from remote_cmd.service.host_service import HostService
from remote_cmd.utils.crypto import CredentialEncryption


@pytest.fixture
def repo(tmp_path):
    return JsonHostRepository(filepath=str(tmp_path / "hosts.json"))


@pytest.fixture
def service(repo):
    return HostService(repository=repo)


class TestHostService:
    """HostService 业务逻辑测试"""

    def test_add_host(self, service):
        """测试：添加主机"""
        host = Host(name="srv1", hostname="10.0.0.1", username="root", tags=["prod"])
        result = service.add_host(host)
        assert result.name == "srv1"

        loaded = service.get_host("srv1")
        assert loaded.hostname == "10.0.0.1"

    def test_add_duplicate_raises(self, service):
        """测试：添加同名主机应抛出 ValueError"""
        service.add_host(Host(name="dup", hostname="1", username="u"))
        with pytest.raises(ValueError, match="已存在"):
            service.add_host(Host(name="dup", hostname="2", username="u"))

    def test_get_host(self, service):
        """测试：获取主机"""
        service.add_host(Host(name="srv", hostname="10.0.0.1", username="root"))
        host = service.get_host("srv")
        assert host.name == "srv"
        assert host.hostname == "10.0.0.1"

    def test_get_nonexistent_raises(self, service):
        """测试：获取不存在的主机应抛出 KeyError"""
        with pytest.raises(KeyError):
            service.get_host("phantom")

    def test_update_host(self, service):
        """测试：更新主机"""
        service.add_host(Host(name="srv", hostname="10.0.0.1", username="root", port=22))
        service.update_host("srv", port=2222, description="updated")

        updated = service.get_host("srv")
        assert updated.port == 2222
        assert updated.description == "updated"

    def test_remove_host(self, service):
        """测试：删除主机"""
        service.add_host(Host(name="srv", hostname="1", username="u"))
        service.remove_host("srv")
        assert len(service.list_hosts()) == 0

    def test_remove_nonexistent_raises(self, service):
        """测试：删除不存在的主机应抛出 KeyError"""
        with pytest.raises(KeyError):
            service.remove_host("phantom")

    def test_list_hosts(self, service):
        """测试：列出主机"""
        service.add_host(Host(name="a", hostname="1", username="u"))
        service.add_host(Host(name="b", hostname="2", username="u"))
        hosts = service.list_hosts()
        assert len(hosts) == 2

    def test_list_hosts_by_tag(self, service):
        """测试：按标签列出主机"""
        service.add_host(Host(name="web", hostname="1", username="u", tags=["web"]))
        service.add_host(Host(name="db", hostname="2", username="u", tags=["db"]))

        web_hosts = service.list_hosts(tag="web")
        assert len(web_hosts) == 1
        assert web_hosts[0].name == "web"

    def test_list_tags(self, service):
        """测试：列出所有标签"""
        service.add_host(Host(name="a", hostname="1", username="u", tags=["web", "prod"]))
        service.add_host(Host(name="b", hostname="2", username="u", tags=["db"]))
        tags = service.list_tags()
        assert set(tags) == {"web", "prod", "db"}

    def test_add_encrypts_password(self, tmp_path):
        """测试：添加主机时密码被自动加密"""
        key_path = tmp_path / ".key"
        crypto = CredentialEncryption(key_path=key_path)
        repo = JsonHostRepository(filepath=str(tmp_path / "hosts.json"), encryption=crypto)
        svc = HostService(repository=repo, encryption=crypto)

        svc.add_host(Host(name="secure", hostname="10.0.0.1", username="root", password="secret"))

        # 从文件读取，验证密码已加密
        import json

        with open(tmp_path / "hosts.json") as f:
            data = json.load(f)
        stored_pw = data["hosts"]["secure"]["password"]
        assert stored_pw.startswith("$encrypted$")

        # 通过 service 读取，密码自动解密
        loaded = svc.get_host("secure")
        assert loaded.password == "secret"
