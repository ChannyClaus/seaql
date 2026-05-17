# dbcli

A unified CLI for MySQL, PostgreSQL, and SQLite databases.

Auto-detects the database type from connection URIs, port numbers, or file extensions.

```bash
# Connect to PostgreSQL via URI
dbcli postgres://user:pass@localhost:5432/mydb

# Connect to MySQL via flags
dbcli -u root -p root -h localhost -P 3306 mydb

# Connect to SQLite via file path
dbcli path/to/database.db

# Backslash commands work (PostgreSQL)
> \dt
> \l
> \d users
```

## Installation

```bash
pip install dbcli
```

Or with uv:

```bash
uv tool install dbcli
```

## Usage

```
dbcli [OPTIONS] [DBNAME]
```

Database type is auto-detected from:
- **URI scheme**: `mysql://`, `postgres://`, `postgresql://`, `sqlite://`
- **Port numbers**: `-P 3306` (MySQL), `-p 5432` (PostgreSQL)
- **File extensions**: `.db`, `.sqlite`, `.sqlite3`, `.db3` (SQLite)
- **Flags**: `-u` (MySQL), `-U` (PostgreSQL)

## License

BSD-3-Clause
