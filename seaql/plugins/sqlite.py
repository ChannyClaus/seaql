import os

from cli_helpers.tabular_output import TabularOutputFormatter
from pygments.lexers.sql import SqlLexer

from seaql.core.plugin import DatabasePlugin


SQLITE_KEYWORDS = [
    'ABORT', 'ACTION', 'ADD', 'AFTER', 'ALL', 'ALTER', 'ANALYZE', 'AND',
    'AS', 'ASC', 'ATTACH', 'AUTOINCREMENT', 'BEFORE', 'BEGIN', 'BETWEEN',
    'BIGINT', 'BLOB', 'BOOLEAN', 'BY', 'CASCADE', 'CASE', 'CAST', 'CHECK',
    'CLOB', 'COLLATE', 'COLUMN', 'COMMIT', 'CONFLICT', 'CONSTRAINT',
    'CREATE', 'CROSS', 'CURRENT', 'CURRENT_DATE', 'CURRENT_TIME',
    'CURRENT_TIMESTAMP', 'DATABASE', 'DATE', 'DATETIME', 'DECIMAL',
    'DEFAULT', 'DEFERRABLE', 'DEFERRED', 'DELETE', 'DETACH', 'DISTINCT',
    'DO', 'DOUBLE', 'DROP', 'EACH', 'ELSE', 'ESCAPE', 'EXCEPT',
    'EXCLUSIVE', 'EXISTS', 'EXPLAIN', 'FAIL', 'FILTER', 'FLOAT',
    'FOLLOWING', 'FOR', 'FOREIGN', 'FROM', 'FULL', 'GLOB', 'GROUP',
    'HAVING', 'IF', 'IGNORE', 'IMMEDIATE', 'IN', 'INDEX', 'INDEXED',
    'INITIALLY', 'INNER', 'INSERT', 'INSTEAD', 'INT', 'INTEGER',
    'INTERSECT', 'INTO', 'IS', 'ISNULL', 'JOIN', 'KEY', 'LEFT', 'LIKE',
    'LIMIT', 'MATCH', 'NATURAL', 'NO', 'NOT', 'NOTHING', 'NULL',
    'NULLS', 'NUMERIC', 'OF', 'OFFSET', 'ON', 'OR', 'ORDER', 'OUTER',
    'OVER', 'PARTITION', 'PLAN', 'PRAGMA', 'PRECEDING', 'PRIMARY',
    'QUERY', 'RAISE', 'RANGE', 'REAL', 'RECURSIVE', 'REFERENCES',
    'REGEXP', 'REINDEX', 'RELEASE', 'RENAME', 'REPLACE', 'RESTRICT',
    'RIGHT', 'ROLLBACK', 'ROW', 'ROWS', 'SAVEPOINT', 'SELECT', 'SET',
    'SMALLINT', 'TABLE', 'TEMP', 'TEMPORARY', 'TEXT', 'THEN', 'TO',
    'TRANSACTION', 'TRIGGER', 'UNBOUNDED', 'UNION', 'UNIQUE', 'UPDATE',
    'USING', 'VACUUM', 'VALUES', 'VARCHAR', 'VIEW', 'VIRTUAL', 'WHEN',
    'WHERE', 'WINDOW', 'WITH', 'WITHOUT',
]

SQLITE_COMMANDS = [
    '.databases', '.exit', '.import', '.indexes', '.load',
    '.once', '.open', '.output', '.read', '.schema',
    '.status', '.tables', '.views',
    '\\?', '\\d', '\\di', '\\dt', '\\dv', '\\e', '\\f', '\\fd', '\\fs',
    '\\G', '\\l', '\\n', '\\o', '\\once', '\\P', '\\pipe_once',
    '\\q', '\\s', '\\|', '\\ts',
    'desc', 'describe', 'exit', 'help', 'pager', 'nopager',
    'quit', 'system', 'tee', 'notee', 'watch',
]


class SQLitePlugin(DatabasePlugin):
    name = 'sqlite'
    version = '1.15.0'
    default_prompt = 'sqlite> '

    def get_sql_lexer_class(self):
        return SqlLexer

    def get_special_commands(self) -> list[str]:
        return SQLITE_COMMANDS

    def get_extra_keywords(self) -> list[str]:
        return SQLITE_KEYWORDS

    def populate_completer_schema(self, completer, executor) -> None:
        conn = executor.conn
        if not conn:
            return
        dbname = 'main'
        completer.set_dbname(dbname)
        completer.extend_schemata(dbname)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        if tables:
            completer.extend_relations([(t,) for t in tables], 'tables')
        cur.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = [r[0] for r in cur.fetchall()]
        for v in views:
            completer.extend_relations([(v,)], 'views')

    def create_executor(self, connection_info: dict):
        from seaql.plugins.litecli_pkg.sqlexecute import SQLExecute
        return SQLExecute(connection_info.get('database'))

    def execute_query(self, executor, query: str) -> list[tuple]:
        results = []
        for r in executor.run(query):
            results.append(r)
        return results

    def format_output(self, results: list[tuple], table_format: str) -> list[str]:
        lines = []
        formatter = TabularOutputFormatter(format_name=table_format)
        for title, rows, headers, status in results:
            if title:
                lines.append(title)
            if headers is not None and rows is not None:
                formatted = formatter.format_output(list(rows), headers)
                lines.extend(formatted)
            if status:
                lines.append(status)
        return lines

    def connect(self, args: list[str]) -> dict:
        db_file = ':memory:'
        for a in args:
            if not a.startswith('-'):
                db_file = a
                break
        return {'database': os.path.abspath(db_file) if db_file != ':memory:' else db_file}

    def get_default_config_path(self) -> str:
        return os.path.expanduser('~/.liteclirc')
