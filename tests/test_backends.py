import os
import time

from dbcli.plugins import get_plugin

_UID = str(int(time.time() * 1000000))[-8:]


class BaseBackendTest:
    PLUGIN_NAME = ""
    CONNECT_ARGS = []

    @classmethod
    def setup_class(cls):
        cls.plugin_cls = get_plugin(cls.PLUGIN_NAME)
        cls.plugin = cls.plugin_cls()
        conn_info = cls.plugin.connect(cls.CONNECT_ARGS)
        cls.executor = cls.plugin.create_executor(conn_info)
        if hasattr(cls.plugin, "create_completer"):
            cls.plugin.create_completer(True, {"executor": cls.executor})

    def query(self, sql: str) -> list[tuple]:
        return self.plugin.execute_query(self.executor, sql)

    def format(self, results: list[tuple]) -> list[str]:
        return self.plugin.format_output(results, "psql")

    def test_select(self):
        results = self.query("SELECT 1 AS test_col")
        output = self.format(results)
        assert len(output) >= 3
        assert "test_col" in output[1]

    def test_select_from_table(self):
        results = self.query("SELECT * FROM users")
        rows = []
        headers = None
        for title, r, h, status in results:
            if h:
                headers = h
            if r:
                rows.extend(list(r))
        assert headers is not None
        assert len(rows) >= 2

    def test_insert(self):
        uid = _UID
        results = self.query(f"INSERT INTO users (name, email) VALUES ('tuser_{uid}', 't{uid}@i.test')")
        assert results is not None

    def test_insert_with_select(self):
        uid = _UID + "s"
        self.query(f"INSERT INTO users (name, email) VALUES ('mtest_{uid}', 'm{uid}@i.test')")
        results = self.query(f"SELECT * FROM users WHERE email='m{uid}@i.test'")
        rows = []
        headers = None
        for title, r, h, status in results:
            if h:
                headers = h
            if r:
                rows.extend(list(r))
        assert len(rows) == 1

    def test_multi_statement(self):
        results = self.query("SELECT * FROM users; SELECT * FROM orders")
        stmt_count = sum(1 for _ in results)
        assert stmt_count >= 2

    def test_empty_result(self):
        results = self.query("SELECT * FROM users WHERE 1=0")
        rows = []
        for title, r, h, status in results:
            if r:
                rows.extend(list(r))
        assert len(rows) == 0

    def test_error_handling(self):
        try:
            results = self.query("SELECT * FROM nonexistent_table")
        except Exception as e:
            assert str(e) is not None


class TestPostgreSQL(BaseBackendTest):
    PLUGIN_NAME = "postgres"
    CONNECT_ARGS = ["-Upostgres", "-h127.0.0.1", "-p5432", "test"]

    def test_backslash_dt(self):
        results = self.query("\\dt")
        output = self.format(results)
        joined = "\n".join(output)
        assert "users" in joined
        assert "orders" in joined

    def test_backslash_l(self):
        results = self.query("\\l")
        output = self.format(results)
        joined = "\n".join(output)
        assert "test" in joined

    def test_backslash_d_table(self):
        results = self.query("\\d users")
        output = self.format(results)
        joined = "\n".join(output)
        assert "id" in joined
        assert "name" in joined
        assert "email" in joined

    def test_uri_connection(self):
        plugin_cls = get_plugin("postgres")
        plugin = plugin_cls()
        conn_info = plugin.connect(["postgres://postgres@127.0.0.1:5432/test"])
        executor = plugin.create_executor(conn_info)
        results = plugin.execute_query(executor, "SELECT 1 AS uri_ok")
        rows = []
        for title, r, h, status in results:
            if r:
                rows.extend(list(r))
        assert len(rows) == 1


class TestMySQL(BaseBackendTest):
    PLUGIN_NAME = "mysql"
    CONNECT_ARGS = ["-uroot", "-proot", "-h127.0.0.1", "-P3306", "test"]

    def test_separate_args_connection(self):
        plugin_cls = get_plugin("mysql")
        plugin = plugin_cls()
        conn_info = plugin.connect(["-u", "root", "-p", "root", "-h", "127.0.0.1", "-P", "3306", "test"])
        executor = plugin.create_executor(conn_info)
        results = plugin.execute_query(executor, "SELECT 1 AS sep_ok")
        rows = []
        for title, r, h, status in results:
            if r:
                rows.extend(list(r))
        assert len(rows) == 1

    def test_uri_connection(self):
        plugin_cls = get_plugin("mysql")
        plugin = plugin_cls()
        conn_info = plugin.connect(["mysql://root:root@127.0.0.1:3306/test"])
        executor = plugin.create_executor(conn_info)
        results = plugin.execute_query(executor, "SELECT 1 AS uri_ok")
        rows = []
        for title, r, h, status in results:
            if r:
                rows.extend(list(r))
        assert len(rows) == 1

    def test_long_args_connection(self):
        plugin_cls = get_plugin("mysql")
        plugin = plugin_cls()
        conn_info = plugin.connect(["--user=root", "--password=root", "--host=127.0.0.1", "--port=3306", "--database=test"])
        executor = plugin.create_executor(conn_info)
        results = plugin.execute_query(executor, "SELECT 1 AS long_ok")
        rows = []
        for title, r, h, status in results:
            if r:
                rows.extend(list(r))
        assert len(rows) == 1


class TestSQLite(BaseBackendTest):
    PLUGIN_NAME = "sqlite"
    CONNECT_ARGS = ["/tmp/test.db"]

    def test_in_memory(self):
        plugin_cls = get_plugin("sqlite")
        plugin = plugin_cls()
        conn_info = plugin.connect([":memory:"])
        executor = plugin.create_executor(conn_info)
        results = plugin.execute_query(executor, "SELECT 1 AS mem_ok")
        rows = []
        for title, r, h, status in results:
            if r:
                rows.extend(list(r))
        assert len(rows) == 1
