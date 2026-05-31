"""SqliteHostRepository 主机存储测试"""

from remote_cmd.core.host import Host
from remote_cmd.repository.sqlite_host_repository import SqliteHostRepository


class TestSqliteHostRepository:
    """SqliteHostRepository 集成测试"""

    # --- CRUD ---

    def test_save_and_get(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        host = Host(name="srv1", hostname="10.0.0.1", username="admin", port=22)
        repo.save(host)

        retrieved = repo.get("srv1")
        assert retrieved.name == "srv1"
        assert retrieved.hostname == "10.0.0.1"
        assert retrieved.username == "admin"
        assert retrieved.port == 22

    def test_get_not_found(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        try:
            repo.get("ghost")
            assert False, "应抛出 KeyError"
        except KeyError:
            pass

    def test_save_duplicate(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        host1 = Host(name="srv1", hostname="10.0.0.1", username="admin")
        host2 = Host(name="srv1", hostname="10.0.0.2", username="root")

        repo.save(host1)
        repo.save(host2)

        retrieved = repo.get("srv1")
        assert retrieved.hostname == "10.0.0.2"
        assert retrieved.username == "root"

    def test_delete(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="srv1", hostname="10.0.0.1", username="admin"))
        repo.delete("srv1")
        assert repo.contains("srv1") is False

    def test_delete_not_found(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        try:
            repo.delete("ghost")
            assert False, "应抛出 KeyError"
        except KeyError:
            pass

    def test_contains(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="srv1", hostname="10.0.0.1", username="admin"))
        assert repo.contains("srv1") is True
        assert repo.contains("ghost") is False

    def test_count(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        assert repo.count() == 0
        repo.save(Host(name="srv1", hostname="10.0.0.1", username="admin"))
        repo.save(Host(name="srv2", hostname="10.0.0.2", username="admin"))
        assert repo.count() == 2

    # --- List ---

    def test_list(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        hosts = [
            Host(name="srv1", hostname="10.0.0.1", username="admin"),
            Host(name="srv2", hostname="10.0.0.2", username="root"),
        ]
        for h in hosts:
            repo.save(h)

        result = repo.list()
        assert len(result) == 2
        assert {h.name for h in result} == {"srv1", "srv2"}

    def test_list_empty(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        assert repo.list() == []

    # --- Pagination ---

    def test_list_paginated(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        for i in range(10):
            repo.save(Host(name=f"srv{i}", hostname=f"10.0.0.{i}", username="admin"))

        page1, total1 = repo.list_paginated(offset=0, limit=3)
        assert len(page1) == 3
        assert total1 == 10

        page2, total2 = repo.list_paginated(offset=3, limit=3)
        assert len(page2) == 3
        assert total2 == 10
        names1 = {h.name for h in page1}
        names2 = {h.name for h in page2}
        assert names1.isdisjoint(names2)

    def test_list_paginated_defaults(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        for i in range(5):
            repo.save(Host(name=f"srv{i}", hostname=f"10.0.0.{i}", username="admin"))
        hosts, total = repo.list_paginated()
        assert len(hosts) == 5
        assert total == 5

    # --- Tags ---

    def test_list_tags(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="web1", hostname="10.0.0.1", username="admin", tags=["web", "prod"]))
        repo.save(Host(name="db1", hostname="10.0.0.2", username="admin", tags=["db", "prod"]))

        tags = repo.list_tags()
        assert sorted(tags) == sorted(["web", "prod", "db"])

    def test_list_tags_empty(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        assert repo.list_tags() == []

    def test_list_by_tag(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="web1", hostname="10.0.0.1", username="admin", tags=["web"]))
        repo.save(Host(name="db1", hostname="10.0.0.2", username="admin", tags=["db"]))

        web_hosts = repo.list(tag="web")
        assert len(web_hosts) == 1
        assert web_hosts[0].name == "web1"

    def test_list_by_tag_nonexistent(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="web1", hostname="10.0.0.1", username="admin", tags=["web"]))
        result = repo.list(tag="nonexistent")
        assert result == []

    # --- Search ---

    def test_search_by_name(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="web-server-01", hostname="10.0.0.1", username="admin"))
        repo.save(Host(name="db-server-01", hostname="10.0.0.2", username="admin"))

        result = repo.search("web")
        assert len(result) == 1
        assert result[0].name == "web-server-01"

    def test_search_by_hostname(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="srv1", hostname="api.example.com", username="admin"))

        result = repo.search("example")
        assert len(result) == 1
        assert result[0].name == "srv1"

    def test_search_empty(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="srv1", hostname="10.0.0.1", username="admin"))
        assert repo.search("nonexistent") == []

    def test_search_empty_query(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="srv1", hostname="10.0.0.1", username="admin"))
        result = repo.search("")
        assert len(result) == 1

    # --- Flush ---

    def test_flush(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="srv1", hostname="10.0.0.1", username="admin"))
        repo.flush()
        assert repo.contains("srv1") is True

    # --- Reopen ---

    def test_reopen_persistence(self, tmp_path):
        db_path = str(tmp_path / "persist.db")
        repo = SqliteHostRepository(db_path)
        repo.save(Host(name="persistent", hostname="10.0.0.1", username="admin"))

        repo2 = SqliteHostRepository(db_path)
        retrieved = repo2.get("persistent")
        assert retrieved.hostname == "10.0.0.1"

    # --- All Fields ---

    def test_host_with_all_fields(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        host = Host(
            name="full-srv",
            hostname="full.example.com",
            username="admin",
            port=2222,
            tags=["web", "prod", "us-east"],
            key_filename="/path/to/key",
        )
        repo.save(host)

        retrieved = repo.get("full-srv")
        assert retrieved.port == 2222
        assert retrieved.tags == ["web", "prod", "us-east"]
        assert retrieved.key_filename == "/path/to/key"

    def test_host_with_empty_tags(self, temp_db_path):
        repo = SqliteHostRepository(temp_db_path)
        repo.save(Host(name="no-tags", hostname="10.0.0.1", username="admin"))
        retrieved = repo.get("no-tags")
        assert retrieved.tags == []
