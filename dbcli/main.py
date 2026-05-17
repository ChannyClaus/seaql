"""dbcli - Unified CLI for MySQL (mycli) and PostgreSQL (pgcli)."""

import shutil
import subprocess
import sys
from typing import NoReturn


def main() -> None:
    args = sys.argv[1:]

    detected = _detect_db_type(args)
    if detected == 'mysql':
        _run_tool('mycli', 'mycli', args)
    elif detected == 'postgres':
        _run_tool('pgcli', 'pgcli', args)

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


def _run_tool(name: str, cmd: str, args: list[str]) -> NoReturn:
    bin_path = shutil.which(cmd)
    if not bin_path:
        print(
            f"dbcli: {name} is not installed.\n"
            f"  Install it with:  pip install {name}\n"
            f"  Or via brew:      brew install {name}\n"
            f"  Or via uv:        uv tool install {name}",
            file=sys.stderr,
        )
        sys.exit(1)
    sys.exit(subprocess.run([bin_path, *args]).returncode)


def _show_usage() -> NoReturn:
    print("Usage: dbcli [OPTIONS] [DBNAME]")
    print()
    print("  A unified CLI for MySQL and PostgreSQL databases.")
    print()
    print("  Database type is auto-detected from the connection URI:")
    print("    mysql://user@host:3306/db     -> MySQL (mycli)")
    print("    postgres://user@host:5432/db  -> PostgreSQL (pgcli)")
    print()
    print("  Port-based detection is also supported (-p/-P/--port 3306 or 5432).")
    sys.exit(1)


if __name__ == "__main__":
    main()
