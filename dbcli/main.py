"""dbcli - Unified CLI for MySQL (mycli) and PostgreSQL (pgcli)."""

import sys
from typing import NoReturn


def main() -> None:
    """Detect database type and delegate to mycli or pgcli."""
    args = sys.argv[1:]

    force_mysql = False
    force_postgres = False
    clean_args: list[str] = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == '--mysql':
            force_mysql = True
        elif a in ('--postgres', '--pg'):
            force_postgres = True
        else:
            clean_args.append(a)
        i += 1

    if force_mysql and force_postgres:
        print("dbcli: error: cannot use both --mysql and --postgres", file=sys.stderr)
        sys.exit(2)

    if force_mysql:
        _run_mycli(clean_args)
    elif force_postgres:
        _run_pgcli(clean_args)

    detected = _detect_db_type(clean_args)
    if detected == 'mysql':
        _run_mycli(clean_args)
    elif detected == 'postgres':
        _run_pgcli(clean_args)

    _show_usage()


def _detect_db_type(args: list[str]) -> str | None:
    for a in args:
        if '://' in a:
            scheme = a.split('://')[0].lower()
            if scheme in ('mysql', 'mycli'):
                return 'mysql'
            if scheme in ('postgres', 'postgresql', 'pgcli'):
                return 'postgres'

    for i, a in enumerate(args):
        if a in ('-p', '--port', '-P') and i + 1 < len(args):
            port = args[i + 1]
            if port == '3306':
                return 'mysql'
            if port == '5432':
                return 'postgres'

    return None


def _run_mycli(args: list[str]) -> NoReturn:
    sys.argv = [sys.argv[0]] + args
    from mycli.main import main as mycli_main
    sys.exit(mycli_main())


def _run_pgcli(args: list[str]) -> NoReturn:
    sys.argv = [sys.argv[0]] + args
    from pgcli.main import cli
    try:
        cli(standalone_mode=False)
    except SystemExit as e:
        sys.exit(e.code)
    except KeyboardInterrupt:
        sys.exit(1)
    sys.exit(0)


def _show_usage() -> NoReturn:
    print("Usage: dbcli [OPTIONS] [DBNAME]")
    print()
    print("  A unified CLI for MySQL and PostgreSQL databases.")
    print()
    print("  Database type is auto-detected from the connection URI:")
    print("    mysql://user@host:3306/db     -> MySQL (mycli)")
    print("    postgres://user@host:5432/db  -> PostgreSQL (pgcli)")
    print()
    print("  To force a database type:")
    print("    dbcli --mysql [OPTIONS] [DBNAME]")
    print("    dbcli --postgres [OPTIONS] [DBNAME]")
    print()
    print("  For full option reference:")
    print("    dbcli --mysql --help")
    print("    dbcli --postgres --help")
    sys.exit(1)


if __name__ == "__main__":
    main()
