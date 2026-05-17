"""dbcli - Unified CLI for MySQL, PostgreSQL, and SQLite databases."""

import os
import sys
from typing import NoReturn

from dbcli.plugins import get_plugin
from dbcli.core.app import DbCliApp

_SQLITE_EXTENSIONS = {'.db', '.sqlite', '.sqlite3', '.db3'}


def main() -> None:
    args = sys.argv[1:]
    db_type = _detect_db_type(args)
    if not db_type:
        _show_usage()

    plugin_cls = get_plugin(db_type)
    plugin = plugin_cls()

    app = DbCliApp(plugin, plugin.connect(args))
    app.run_cli()


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

    for a in args:
        if not a.startswith('-'):
            _, ext = os.path.splitext(a)
            if ext.lower() in _SQLITE_EXTENSIONS:
                return 'sqlite'

    for i, a in enumerate(args):
        if a == '-P' and i + 1 < len(args) and args[i + 1] == '3306':
            return 'mysql'
        if a.startswith('-P') and len(a) > 2 and a[2:] == '3306':
            return 'mysql'
        if a == '--port' and i + 1 < len(args) and args[i + 1] == '3306':
            return 'mysql'
        if a.startswith('--port=') and a[7:] == '3306':
            return 'mysql'

    for i, a in enumerate(args):
        if a == '-p' and i + 1 < len(args):
            val = args[i + 1]
            try:
                if int(val) in (5432, 5433):
                    return 'postgres'
            except ValueError:
                pass
        if a.startswith('-p') and len(a) > 2 and not a.startswith('--'):
            try:
                if int(a[2:]) in (5432, 5433):
                    return 'postgres'
            except ValueError:
                pass
        if a == '--port' and i + 1 < len(args) and args[i + 1] == '5432':
            return 'postgres'
        if a.startswith('--port=') and a[7:] == '5432':
            return 'postgres'

    for a in args:
        if a.startswith('-u') and not a.startswith('--'):
            return 'mysql'

    for a in args:
        if a.startswith('-U') and not a.startswith('--'):
            return 'postgres'

    return None


def _show_usage() -> NoReturn:
    print("Usage: dbcli [OPTIONS] [DBNAME]")
    print()
    print("  A unified CLI for MySQL, PostgreSQL, and SQLite databases.")
    print()
    print("  Database type is auto-detected from the connection URI or file extension:")
    print("    mysql://user@host:3306/db     -> MySQL")
    print("    postgres://user@host:5432/db  -> PostgreSQL")
    print("    path/to/db.sqlite             -> SQLite")
    print()
    print("  Port-based detection is also supported (-p/-P/--port 3306 or 5432).")
    sys.exit(1)


if __name__ == "__main__":
    main()
