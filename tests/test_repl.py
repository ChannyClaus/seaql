import os
import subprocess
import sys
import time

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(args: list[str], input_text: str, timeout: int = 10) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "dbcli"] + args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=BASE_DIR,
        env=env,
    )
    try:
        stdout, stderr = proc.communicate(input=input_text.encode(), timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        pytest.fail(f"CLI timed out after {timeout}s\nstdout: {stdout.decode(errors='replace')}\nstderr: {stderr.decode(errors='replace')}")

    return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")


class TestPostgreSQLRepl:
    def test_basic_select(self):
        input_text = "SELECT 1;\n\\q\n"
        rc, stdout, stderr = run_cli(["-Upostgres", "-h127.0.0.1", "-p5432", "test"], input_text)
        assert rc == 0 or "Goodbye" in stdout

    def test_backslash_dt(self):
        input_text = "\\dt\n\\q\n"
        rc, stdout, stderr = run_cli(["-Upostgres", "-h127.0.0.1", "-p5432", "test"], input_text)
        assert "users" in stdout
        assert "orders" in stdout

    def test_backslash_l(self):
        input_text = "\\l\n\\q\n"
        rc, stdout, stderr = run_cli(["-Upostgres", "-h127.0.0.1", "-p5432", "test"], input_text)
        assert "test" in stdout

    def test_backslash_d_table(self):
        input_text = "\\d users\n\\q\n"
        rc, stdout, stderr = run_cli(["-Upostgres", "-h127.0.0.1", "-p5432", "test"], input_text)
        assert "id" in stdout
        assert "name" in stdout
        assert "email" in stdout

    def test_backslash_df(self):
        input_text = "\\df\n\\q\n"
        rc, stdout, stderr = run_cli(["-Upostgres", "-h127.0.0.1", "-p5432", "test"], input_text)
        assert rc == 0 or "Goodbye" in stdout

    def test_backslash_dv(self):
        input_text = "\\dv\n\\q\n"
        rc, stdout, stderr = run_cli(["-Upostgres", "-h127.0.0.1", "-p5432", "test"], input_text)
        assert rc == 0 or "Goodbye" in stdout

    def test_exit_command(self):
        input_text = "SELECT 1;\nexit\n"
        rc, stdout, stderr = run_cli(["-Upostgres", "-h127.0.0.1", "-p5432", "test"], input_text)
        assert "Goodbye" in stdout

    def test_quit_command(self):
        input_text = "SELECT 1;\nquit\n"
        rc, stdout, stderr = run_cli(["-Upostgres", "-h127.0.0.1", "-p5432", "test"], input_text)
        assert "Goodbye" in stdout

    def test_q_command(self):
        input_text = "SELECT 1;\n\\q\n"
        rc, stdout, stderr = run_cli(["-Upostgres", "-h127.0.0.1", "-p5432", "test"], input_text)
        assert "Goodbye" in stdout

    def test_uri_connection(self):
        input_text = "SELECT 1 AS uri_test;\n\\q\n"
        rc, stdout, stderr = run_cli(["postgres://postgres@127.0.0.1:5432/test"], input_text)
        assert "uri_test" in stdout

    def test_default_port_detection(self):
        input_text = "SELECT 1;\n\\q\n"
        rc, stdout, stderr = run_cli(["-Upostgres", "-h127.0.0.1", "test"], input_text)
        assert "Goodbye" in stdout


class TestMySQLRepl:
    def test_basic_select(self):
        input_text = "SELECT 1;\n\\q\n"
        rc, stdout, stderr = run_cli(["-uroot", "-proot", "-h127.0.0.1", "-P3306", "test"], input_text)
        assert "Goodbye" in stdout

    def test_exit_command(self):
        input_text = "SELECT 1;\nexit\n"
        rc, stdout, stderr = run_cli(["-uroot", "-proot", "-h127.0.0.1", "-P3306", "test"], input_text)
        assert "Goodbye" in stdout

    def test_uri_connection(self):
        input_text = "SELECT 1 AS uri_test;\n\\q\n"
        rc, stdout, stderr = run_cli(["mysql://root:root@127.0.0.1:3306/test"], input_text)
        assert "uri_test" in stdout

    def test_separate_args(self):
        input_text = "SELECT 1 AS sep_test;\n\\q\n"
        rc, stdout, stderr = run_cli(["-u", "root", "-p", "root", "-h", "127.0.0.1", "-P", "3306", "test"], input_text)
        assert "sep_test" in stdout


class TestSQLiteRepl:
    def test_basic_select(self):
        input_text = "SELECT 1;\n\\q\n"
        rc, stdout, stderr = run_cli(["/tmp/test.db"], input_text)
        assert "Goodbye" in stdout

    def test_select_from_table(self):
        input_text = "SELECT * FROM users;\n\\q\n"
        rc, stdout, stderr = run_cli(["/tmp/test.db"], input_text)
        assert "Alice" in stdout
        assert "Bob" in stdout

    def test_exit_command(self):
        input_text = "SELECT 1;\nexit\n"
        rc, stdout, stderr = run_cli(["/tmp/test.db"], input_text)
        assert "Goodbye" in stdout
