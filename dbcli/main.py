"""dbcli - Unified CLI for MySQL, PostgreSQL, and SQLite databases."""

import os
import sys
from typing import NoReturn

_SQLITE_EXTENSIONS = {'.db', '.sqlite', '.sqlite3', '.db3'}


def _setup_vendors() -> None:
    base = os.path.join(os.path.dirname(__file__), 'vendors')
    if base not in sys.path:
        sys.path.insert(0, base)


def main() -> None:
    _setup_vendors()
    args = sys.argv[1:]

    detected = _detect_db_type(args)
    if detected == 'mysql':
        _run_mycli(args)
    elif detected == 'postgres':
        _run_pgcli(args)
    elif detected == 'sqlite':
        _run_litecli(args)

    _show_usage()


def _detect_db_type(args: list[str]) -> str | None:
    for a in args:
        if '://' in a:
            scheme = a.split('://')[0].lower()
            if scheme in ('mysql', 'mycli'):
                return 'mysql'
            if scheme in ('postgres', 'postgresql', 'pgcli'):
                return 'postgres'
            if scheme in ('sqlite', 'sqlite3'):
                return 'sqlite'

    for i, a in enumerate(args):
        if a in ('-p', '--port', '-P') and i + 1 < len(args):
            port = args[i + 1]
            if port == '3306':
                return 'mysql'
            if port == '5432':
                return 'postgres'

    for a in args:
        if not a.startswith('-'):
            _, ext = os.path.splitext(a)
            if ext.lower() in _SQLITE_EXTENSIONS:
                return 'sqlite'

    return None


def _run_mycli(args: list[str]) -> NoReturn:
    sys.argv = [sys.argv[0], *args]
    from mycli.main import main as mycli_main
    sys.exit(mycli_main())


def _run_pgcli(args: list[str]) -> NoReturn:
    sys.argv = [sys.argv[0], *args]
    from pgcli.main import cli
    try:
        cli(standalone_mode=False)
    except SystemExit as e:
        sys.exit(e.code)
    sys.exit(0)


def _run_litecli(args: list[str]) -> NoReturn:
    sys.argv = [sys.argv[0], *args]
    from litecli.main import cli
    try:
        cli(standalone_mode=False)
    except SystemExit as e:
        sys.exit(e.code)
    sys.exit(0)


def _show_usage() -> NoReturn:
    print("Usage: dbcli [OPTIONS] [DBNAME]")
    print()
    print("  A unified CLI for MySQL, PostgreSQL, and SQLite databases.")
    print()
    print("  Database type is auto-detected from the connection URI or file extension:")
    print("    mysql://user@host:3306/db     -> MySQL (mycli)")
    print("    postgres://user@host:5432/db  -> PostgreSQL (pgcli)")
    print("    path/to/db.sqlite             -> SQLite (litecli)")
    print()
    print("  Port-based detection is also supported (-p/-P/--port 3306 or 5432).")
    sys.exit(1)


if __name__ == "__main__":
    main()
