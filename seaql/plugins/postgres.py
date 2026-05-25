import os
import sqlparse
import psycopg
from psycopg.conninfo import make_conninfo

from cli_helpers.tabular_output import TabularOutputFormatter
from pygments.lexers.sql import PostgresLexer

from seaql.core.plugin import DatabasePlugin

PSQL_COMMANDS = [
    '\\?', '\\x', '\\timing', '\\h', '\\pset', '\\pager',
    '\\l', '\\list', '\\dt', '\\d', '\\dv', '\\df', '\\di',
    '\\ds', '\\dT', '\\dn', '\\db', '\\dc', '\\dd', '\\dD',
    '\\dF', '\\du', '\\dg', '\\dp', '\\z', '\\do', '\\dx',
    '\\dE', '\\dm', '\\ddp', '\\copy', '\\i', '\\o', '\\echo',
    '\\cd', '\\!', '\\conninfo', '\\c', '\\connect', '\\encoding',
    '\\errverbose', '\\set', '\\unset', '\\a', '\\H', '\\t', '\\C',
    '\\f', '\\watch', '\\g', '\\gexec', '\\sf', '\\ev', '\\ef',
    '\\e', '\\n', 'describe', '\\ts',
]

PG_KEYWORDS = [
    'ABORT', 'ABS', 'ABSOLUTE', 'ACCESS', 'ACTION', 'ADA', 'ADD',
    'ADMIN', 'AFTER', 'AGGREGATE', 'ALIAS', 'ALL', 'ALLOCATE', 'ALTER',
    'ANALYSE', 'ANALYZE', 'AND', 'ANY', 'ARE', 'AS', 'ASC',
    'ASENSITIVE', 'ASSERTION', 'ASSIGNMENT', 'ASYMMETRIC', 'AT',
    'ATOMIC', 'AUTHORIZATION', 'AVG', 'BACKWARD', 'BEFORE', 'BEGIN',
    'BETWEEN', 'BIGINT', 'BINARY', 'BIT', 'BITVAR', 'BIT_LENGTH',
    'BLOB', 'BOOLEAN', 'BOTH', 'BREADTH', 'BY', 'C', 'CACHE', 'CALL',
    'CALLED', 'CARDINALITY', 'CASCADE', 'CASCADED', 'CASE', 'CAST',
    'CATALOG', 'CATALOG_NAME', 'CEIL', 'CEILING', 'CHAIN', 'CHAR',
    'CHARACTER', 'CHARACTERISTICS', 'CHARACTERS', 'CHARACTER_LENGTH',
    'CHARACTER_SET_CATALOG', 'CHARACTER_SET_NAME',
    'CHARACTER_SET_SCHEMA', 'CHAR_LENGTH', 'CHECK', 'CHECKED',
    'CHECKPOINT', 'CLASS', 'CLASS_ORIGIN', 'CLOB', 'CLOSE', 'CLUSTER',
    'COALESCE', 'COBOL', 'COLLATE', 'COLLATION', 'COLLATION_CATALOG',
    'COLLATION_NAME', 'COLLATION_SCHEMA', 'COLUMN', 'COLUMN_NAME',
    'COMMAND_FUNCTION', 'COMMAND_FUNCTION_CODE', 'COMMENT', 'COMMIT',
    'COMMITTED', 'COMPLETION', 'CONDITION', 'CONDITION_NUMBER',
    'CONNECT', 'CONNECTION', 'CONNECTION_NAME', 'CONSTRAINT',
    'CONSTRAINTS', 'CONSTRAINT_CATALOG', 'CONSTRAINT_NAME',
    'CONSTRAINT_SCHEMA', 'CONSTRUCTOR', 'CONTAINS', 'CONTINUE',
    'CONVERSION', 'CONVERT', 'CORRESPONDING', 'COUNT', 'CREATE',
    'CREATEDB', 'CREATEUSER', 'CROSS', 'CUBE', 'CURRENT',
    'CURRENT_DATE', 'CURRENT_DEFAULT_TRANSFORM_GROUP', 'CURRENT_PATH',
    'CURRENT_ROLE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP',
    'CURRENT_TRANSFORM_GROUP_FOR_TYPE', 'CURRENT_USER', 'CURSOR',
    'CURSOR_NAME', 'CYCLE', 'DATA', 'DATABASE', 'DATE',
    'DATETIME_INTERVAL_CODE', 'DATETIME_INTERVAL_PRECISION', 'DAY',
    'DEALLOCATE', 'DEC', 'DECIMAL', 'DECLARE', 'DEFAULT',
    'DEFERRABLE', 'DEFERRED', 'DEFINED', 'DEFINER', 'DEGREE',
    'DELETE', 'DELIMITER', 'DELIMITERS', 'DENSE_RANK', 'DEPTH',
    'DEREF', 'DERIVED', 'DESC', 'DESCRIBE', 'DESCRIPTOR', 'DESTROY',
    'DESTRUCTOR', 'DETERMINISTIC', 'DIAGNOSTICS', 'DICTIONARY',
    'DISCONNECT', 'DISPATCH', 'DISTINCT', 'DO', 'DOMAIN', 'DOUBLE',
    'DROP', 'DYNAMIC', 'DYNAMIC_FUNCTION', 'DYNAMIC_FUNCTION_CODE',
    'EACH', 'ELSE', 'ENCODING', 'ENCRYPTED', 'END', 'END-EXEC',
    'EQUALS', 'ERROR', 'ESCAPE', 'EVERY', 'EXCEPT', 'EXCEPTION',
    'EXCLUDING', 'EXCLUSIVE', 'EXEC', 'EXECUTE', 'EXISTING',
    'EXISTS', 'EXP', 'EXPLAIN', 'EXTERNAL', 'EXTRACT', 'FALSE',
    'FETCH', 'FILTER', 'FINAL', 'FIRST', 'FLOAT', 'FLOOR',
    'FOLLOWING', 'FOR', 'FORCE', 'FOREIGN', 'FORTRAN', 'FORWARD',
    'FOUND', 'FREE', 'FREEZE', 'FROM', 'FULL', 'FUNCTION', 'G',
    'GENERAL', 'GENERATED', 'GET', 'GLOBAL', 'GO', 'GOTO', 'GRANT',
    'GRANTED', 'GROUP', 'GROUPING', 'HAVING', 'HIERARCHY', 'HOLD',
    'HOUR', 'IDENTITY', 'IGNORE', 'ILIKE', 'IMMEDIATE', 'IMMUTABLE',
    'IMPLEMENTATION', 'IMPLICIT', 'IN', 'INCLUDING', 'INCREMENT',
    'INDEX', 'INDICATOR', 'INFIX', 'INHERITS', 'INITIALIZE',
    'INITIALLY', 'INNER', 'INOUT', 'INPUT', 'INSENSITIVE', 'INSERT',
    'INSTEAD', 'INT', 'INTEGER', 'INTERSECT', 'INTERSECTION',
    'INTERVAL', 'INTO', 'INVOKER', 'IS', 'ISOLATION', 'ITERATE',
    'JOIN', 'KEY', 'KEY_MEMBER', 'KEY_TYPE', 'LANCOMPILER', 'LARGE',
    'LAST', 'LATERAL', 'LEADING', 'LEFT', 'LENGTH', 'LESS', 'LEVEL',
    'LIKE', 'LIMIT', 'LISTEN', 'LOAD', 'LOCAL', 'LOCALTIME',
    'LOCALTIMESTAMP', 'LOCATION', 'LOCATOR', 'LOCK', 'LOGIN',
    'LOWER', 'M', 'MAP', 'MATCH', 'MAX', 'MAXVALUE',
    'MESSAGE_LENGTH', 'MESSAGE_OCTET_LENGTH', 'MESSAGE_TEXT',
    'METHOD', 'MIN', 'MINUTE', 'MINVALUE', 'MOD', 'MODE',
    'MODIFIES', 'MODIFY', 'MODULE', 'MONTH', 'MORE', 'MOVE',
    'MUMPS', 'NAME', 'NAMES', 'NATIONAL', 'NATURAL', 'NCHAR',
    'NCLOB', 'NEW', 'NEXT', 'NO', 'NOCREATEDB', 'NOCREATEUSER',
    'NONE', 'NOT', 'NOTHING', 'NOTIFY', 'NOTNULL', 'NULL',
    'NULLABLE', 'NULLIF', 'NUMBER', 'NUMERIC', 'OBJECT',
    'OCTET_LENGTH', 'OF', 'OFF', 'OFFSET', 'OIDS', 'OLD', 'ON',
    'ONLY', 'OPEN', 'OPERATION', 'OPERATOR', 'OPTION', 'OPTIONS',
    'OR', 'ORDER', 'ORDINALITY', 'OUT', 'OUTER', 'OUTPUT', 'OVER',
    'OVERLAPS', 'OVERLAY', 'OVERRIDING', 'OWNER', 'PAD',
    'PARAMETER', 'PARAMETERS', 'PARAMETER_MODE', 'PARAMETER_NAME',
    'PARAMETER_ORDINAL_POSITION', 'PARAMETER_SPECIFIC_CATALOG',
    'PARAMETER_SPECIFIC_NAME', 'PARAMETER_SPECIFIC_SCHEMA',
    'PARTIAL', 'PARTITION', 'PASCAL', 'PASSWORD', 'PATH', 'PERCENT',
    'PLACING', 'PLAN', 'PLI', 'POSITION', 'POSTFIX', 'POWER',
    'PRECISION', 'PREFIX', 'PREORDER', 'PREPARE', 'PRESERVE',
    'PRIMARY', 'PRIOR', 'PRIVILEGES', 'PROCEDURAL', 'PROCEDURE',
    'PUBLIC', 'PURGE', 'QUOTE', 'RANGE', 'RANK', 'READ', 'READS',
    'REAL', 'RECHECK', 'RECURSIVE', 'REF', 'REFERENCES',
    'REFERENCING', 'REINDEX', 'RELATIVE', 'RENAME', 'REPEATABLE',
    'REPLACE', 'RESET', 'RESTART', 'RESTRICT', 'RESULT', 'RETURN',
    'RETURNED_CARDINALITY', 'RETURNED_LENGTH',
    'RETURNED_OCTET_LENGTH', 'RETURNED_SQLSTATE', 'RETURNS',
    'REVOKE', 'RIGHT', 'ROLE', 'ROLLBACK', 'ROLLUP', 'ROUTINE',
    'ROUTINE_CATALOG', 'ROUTINE_NAME', 'ROUTINE_SCHEMA', 'ROW',
    'ROWS', 'ROW_COUNT', 'RULE', 'SAVEPOINT', 'SCALE', 'SCHEMA',
    'SCHEMA_NAME', 'SCOPE', 'SCROLL', 'SEARCH', 'SECOND', 'SECTION',
    'SECURITY', 'SELECT', 'SELF', 'SENSITIVE', 'SEQUENCE',
    'SERIALIZABLE', 'SERVER_NAME', 'SESSION', 'SESSION_USER', 'SET',
    'SETOF', 'SETS', 'SHARE', 'SHOW', 'SIMILAR', 'SIMPLE', 'SIZE',
    'SMALLINT', 'SOME', 'SOURCE', 'SPACE', 'SPECIFIC',
    'SPECIFICTYPE', 'SPECIFIC_NAME', 'SQL', 'SQLCODE', 'SQLERROR',
    'SQLEXCEPTION', 'SQLSTATE', 'SQLWARNING', 'SQRT', 'STABLE',
    'START', 'STATE', 'STATEMENT', 'STATIC', 'STATISTICS', 'STDIN',
    'STDOUT', 'STORAGE', 'STRICT', 'STRUCTURE', 'STYLE',
    'SUBCLASS_ORIGIN', 'SUBLIST', 'SUBMULTISET', 'SUBSTRING', 'SUM',
    'SYSID', 'SYSTEM', 'SYSTEM_USER', 'TABLE', 'TABLESAMPLE',
    'TABLESPACE', 'TEMP', 'TEMPLATE', 'TEMPORARY', 'TERMINATE',
    'THAN', 'THEN', 'TIME', 'TIMESTAMP', 'TIMEZONE_HOUR',
    'TIMEZONE_MINUTE', 'TO', 'TOAST', 'TRAILING', 'TRANSACTION',
    'TRANSACTIONS_COMMITTED', 'TRANSACTIONS_ROLLED_BACK',
    'TRANSACTION_ACTIVE', 'TRANSFORM', 'TRANSFORMS', 'TRANSLATE',
    'TRANSLATION', 'TREAT', 'TRIGGER', 'TRIGGER_CATALOG',
    'TRIGGER_NAME', 'TRIGGER_SCHEMA', 'TRIM', 'TRUE', 'TRUNCATE',
    'TRUSTED', 'TYPE', 'UNCOMMITTED', 'UNDER', 'UNENCRYPTED',
    'UNION', 'UNIQUE', 'UNKNOWN', 'UNLISTEN', 'UNNAMED', 'UNNEST',
    'UNTIL', 'UPDATE', 'UPPER', 'URB', 'USAGE', 'USER',
    'USER_DEFINED_TYPE_CATALOG', 'USER_DEFINED_TYPE_NAME',
    'USER_DEFINED_TYPE_SCHEMA', 'USING', 'VACUUM', 'VALID',
    'VALIDATOR', 'VALUE', 'VALUES', 'VARCHAR', 'VARIABLE', 'VARYING',
    'VERBOSE', 'VERSION', 'VIEW', 'VOLATILE', 'WHEN', 'WHENEVER',
    'WHERE', 'WIDTH', 'WINDOW', 'WITH', 'WITHIN', 'WITHOUT',
    'WORK', 'WRITE', 'YEAR', 'ZONE',
]


class PsqlExecutor:
    def __init__(self, database='', user='', password='', host='', port='', dsn=None):
        self.conn = None
        self._connect(database, user, password, host, port, dsn)

    @property
    def connection(self):
        return self.conn

    def _connect(self, database, user, password, host, port, dsn):
        if dsn:
            conn_info = make_conninfo(
                dsn,
                dbname=database or '',
                user=user or '',
                password=password or '',
                host=host or '',
                port=str(port or ''),
            )
        else:
            conn_info = make_conninfo(
                dbname=database or '',
                user=user or '',
                password=password or '',
                host=host or '',
                port=str(port or ''),
            )
        self.conn = psycopg.connect(conn_info)
        self.conn.autocommit = True

    def run(self, query, pgspecial=None):
        from seaql.vendored.pgspecial.main import CommandNotFound

        statement = query.strip()
        if not statement:
            return

        sqlarr = sqlparse.split(statement)

        for sql in sqlarr:
            sql = sql.rstrip(';')
            sql = sqlparse.format(sql, strip_comments=False).strip()
            if not sql:
                continue

            reset_expanded = False
            if pgspecial and sql.endswith('\\G'):
                pgspecial.expanded_output = True
                reset_expanded = True
                sql = sql[:-2].strip()

            if pgspecial:
                try:
                    cur = self.conn.cursor()
                    response = pgspecial.execute(cur, sql)
                    for result in response:
                        yield result[:4]
                    if reset_expanded:
                        pgspecial.expanded_output = False
                    continue
                except CommandNotFound:
                    if reset_expanded:
                        pgspecial.expanded_output = False

            cur = self.conn.cursor()
            cur.execute(sql)

            if reset_expanded:
                pgspecial.expanded_output = False

            if cur.description:
                headers = [x[0] for x in cur.description]
                yield None, cur, headers, cur.statusmessage
            else:
                yield None, None, None, cur.statusmessage


class PostgresPlugin(DatabasePlugin):
    name = 'postgres'
    version = '0.1.0'
    default_prompt = '\\u@\\h:\\d> '

    def get_sql_lexer_class(self):
        return PostgresLexer

    def get_special_commands(self) -> list[str]:
        from seaql.vendored.pgspecial.main import PGSpecial
        self._pgspecial = PGSpecial()
        return PSQL_COMMANDS + list(self._pgspecial.commands.keys())

    def get_extra_keywords(self) -> list[str]:
        return PG_KEYWORDS

    def populate_completer_schema(self, completer, executor) -> None:
        try:
            conn = executor.connection
            if not conn:
                return

            dbname = conn.info.dbname
            completer.set_dbname(dbname)
            completer.extend_schemata(dbname)

            with conn.cursor() as cur:
                cur.execute("SELECT schema_name FROM information_schema.schemata")
                for row in cur.fetchall():
                    completer.extend_schemata(row[0])

                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
                tables = [row[0] for row in cur.fetchall()]
                if tables:
                    completer.extend_relations(
                        [(t, 'public') for t in tables], 'tables'
                    )

                cur.execute(
                    "SELECT table_name FROM information_schema.views "
                    "WHERE table_schema = 'public'"
                )
                for row in cur.fetchall():
                    completer.extend_relations(
                        [(row[0], 'public')], 'views'
                    )

                cur.execute(
                    "SELECT column_name, table_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = ANY(%s)",
                    (tables,) if tables else ([''],)
                )
                cols = [(r[1], r[0]) for r in cur.fetchall()]
                if cols:
                    completer.extend_columns(cols, 'tables')

                cur.execute(
                    "SELECT routine_name FROM information_schema.routines "
                    "WHERE specific_schema = 'public' AND routine_type = 'FUNCTION'"
                )
                funcs = [(r[0],) for r in cur.fetchall()]
                if funcs:
                    completer.extend_functions(funcs)
        except Exception:
            pass

    def create_executor(self, connection_info: dict):
        return PsqlExecutor(
            database=connection_info.get('database') or '',
            user=connection_info.get('user') or '',
            password=connection_info.get('password') or '',
            host=connection_info.get('host') or '',
            port=connection_info.get('port') or '',
            dsn=connection_info.get('dsn') or None,
        )

    def execute_query(self, executor, query: str) -> list[tuple]:
        results = []
        pgspecial = getattr(self, '_pgspecial', None)
        for title, rows, headers, status, *_ in executor.run(query, pgspecial=pgspecial):
            results.append((title, rows, headers, status))
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
        database = user = password = host = dsn = None
        port = None
        positional = []

        i = 0
        while i < len(args):
            a = args[i]
            if a in ('-U', '--username') and i + 1 < len(args):
                user = args[i + 1]; i += 2; continue
            if a in ('-h', '--host') and i + 1 < len(args):
                host = args[i + 1]; i += 2; continue
            if a in ('-p', '--port') and i + 1 < len(args):
                port = int(args[i + 1]); i += 2; continue
            if a in ('-d', '--dbname') and i + 1 < len(args):
                database = args[i + 1]; i += 2; continue
            if a.startswith('-U') and len(a) > 2 and not a.startswith('--'):
                user = a[2:]; i += 1; continue
            if a.startswith('-h') and len(a) > 2 and not a.startswith('--'):
                host = a[2:]; i += 1; continue
            if a.startswith('-p') and len(a) > 2 and not a.startswith('--'):
                try: port = int(a[2:])
                except ValueError: pass
                i += 1; continue
            if a.startswith('-d') and len(a) > 2 and not a.startswith('--'):
                database = a[2:]; i += 1; continue
            if a.startswith('--username='):
                user = a[11:]; i += 1; continue
            if a.startswith('--host='):
                host = a[7:]; i += 1; continue
            if a.startswith('--port='):
                try: port = int(a[7:])
                except ValueError: pass
                i += 1; continue
            if a.startswith('--dbname='):
                database = a[9:]; i += 1; continue
            if a.startswith('postgres://') or a.startswith('postgresql://'):
                dsn = a
                from urllib.parse import urlparse
                u = urlparse(a)
                database = u.path[1:] or database
                user = u.username or user
                password = u.password or password
                host = u.hostname or host
                port = u.port or port
                i += 1; continue
            if not a.startswith('-'):
                positional.append(a)
            i += 1

        database = database or (positional[0] if positional else None)
        password = password or os.environ.get('PGPASSWORD', '')
        user = user or os.environ.get('PGUSER', 'postgres')
        host = host or os.environ.get('PGHOST', 'localhost')
        port = port or int(os.environ.get('PGPORT', '5432'))
        return {
            'database': database or 'postgres',
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'dsn': dsn or '',
        }

    def get_default_config_path(self) -> str:
        return os.path.expanduser('~/.seaqlrc')
