import os

from cli_helpers.tabular_output import TabularOutputFormatter
from pygments.lexers.sql import MySqlLexer

from seaql.core.plugin import DatabasePlugin


MYSQL_COMMANDS = [
    '.databases', '.exit', '.import', '.indexes', '.load',
    '.once', '.open', '.output', '.read', '.schema',
    '.status', '.tables', '.views',
    '\\?', '\\d', '\\dt', '\\dv', '\\e', '\\f', '\\fd', '\\fs',
    '\\G', '\\l', '\\n', '\\o', '\\once', '\\P', '\\pipe_once',
    '\\q', '\\s', '\\|', '\\watch', '\\ts',
    'desc', 'describe', 'exit', 'help', 'pager', 'nopager',
    'quit', 'system', 'tee', 'notee',
]

MYSQL_KEYWORDS = [
    'ACCESSIBLE', 'ADD', 'ALL', 'ALTER', 'ANALYZE', 'AND', 'AS', 'ASC',
    'ASENSITIVE', 'AUTO_INCREMENT', 'BEFORE', 'BETWEEN', 'BIGINT',
    'BINARY', 'BLOB', 'BOTH', 'BY', 'CALL', 'CASCADE', 'CASE', 'CHANGE',
    'CHAR', 'CHARACTER', 'CHECK', 'COLLATE', 'COLUMN', 'COMMIT',
    'CONDITION', 'CONNECTION', 'CONSTRAINT', 'CONTINUE', 'CONVERT',
    'CREATE', 'CROSS', 'CUBE', 'CURRENT_DATE', 'CURRENT_TIME',
    'CURRENT_TIMESTAMP', 'CURRENT_USER', 'CURSOR', 'DATABASE',
    'DATABASES', 'DATE', 'DATETIME', 'DAY', 'DAY_HOUR',
    'DAY_MICROSECOND', 'DAY_MINUTE', 'DAY_SECOND', 'DEC', 'DECIMAL',
    'DECLARE', 'DEFAULT', 'DELAYED', 'DELETE', 'DESC', 'DESCRIBE',
    'DETERMINISTIC', 'DISTINCT', 'DISTINCTROW', 'DIV', 'DOUBLE', 'DROP',
    'DUAL', 'EACH', 'ELSE', 'ELSEIF', 'ENCLOSED', 'ENGINE', 'ESCAPED',
    'EXISTS', 'EXIT', 'EXPLAIN', 'FALSE', 'FETCH', 'FLOAT', 'FLOAT4',
    'FLOAT8', 'FOR', 'FORCE', 'FOREIGN', 'FROM', 'FULLTEXT', 'FUNCTION',
    'GENERATED', 'GET', 'GRANT', 'GROUP', 'HAVING', 'HIGH_PRIORITY',
    'HOUR_MICROSECOND', 'HOUR_MINUTE', 'HOUR_SECOND', 'IF', 'IGNORE',
    'IN', 'INDEX', 'INFILE', 'INNER', 'INOUT', 'INSENSITIVE', 'INSERT',
    'INT', 'INT1', 'INT2', 'INT3', 'INT4', 'INT8', 'INTEGER',
    'INTERVAL', 'INTO', 'IO_AFTER_GTIDS', 'IO_BEFORE_GTIDS', 'IS',
    'ITERATE', 'JOIN', 'KEY', 'KEYS', 'KILL', 'LATERAL', 'LEADING',
    'LEAVE', 'LEFT', 'LIKE', 'LIMIT', 'LINEAR', 'LINES', 'LOAD',
    'LOCALTIME', 'LOCALTIMESTAMP', 'LOCK', 'LONG', 'LONGBLOB',
    'LONGTEXT', 'LOOP', 'LOW_PRIORITY', 'MASTER_BIND',
    'MASTER_SSL_VERIFY_SERVER_CERT', 'MATCH', 'MAXVALUE', 'MEDIUMBLOB',
    'MEDIUMINT', 'MEDIUMTEXT', 'MIDDLEINT', 'MINUTE_MICROSECOND',
    'MINUTE_SECOND', 'MOD', 'MODE', 'MODIFIES', 'NATURAL', 'NOT',
    'NO_WRITE_TO_BINLOG', 'NULL', 'NUMERIC', 'ON', 'OPTIMIZE',
    'OPTION', 'OPTIONALLY', 'OR', 'ORDER', 'OUT', 'OUTER', 'OUTFILE',
    'OVER', 'PARTITION', 'PRECISION', 'PRIMARY', 'PROCEDURE', 'PURGE',
    'RANGE', 'READ', 'READS', 'READ_WRITE', 'REAL', 'RECURSIVE',
    'REFERENCES', 'REGEXP', 'RELEASE', 'RENAME', 'REPEAT', 'REPLACE',
    'REQUIRE', 'RESIGNAL', 'RESTRICT', 'RETURN', 'REVOKE', 'RIGHT',
    'RLIKE', 'ROLLBACK', 'SCHEMA', 'SCHEMAS', 'SECOND_MICROSECOND',
    'SELECT', 'SENSITIVE', 'SEPARATOR', 'SET', 'SHOW', 'SIGNAL',
    'SMALLINT', 'SPATIAL', 'SPECIFIC', 'SQL', 'SQLEXCEPTION',
    'SQLSTATE', 'SQLWARNING', 'SQL_BIG_RESULT',
    'SQL_CALC_FOUND_ROWS', 'SQL_SMALL_RESULT', 'SSL', 'STARTING',
    'STORED', 'STRAIGHT_JOIN', 'TABLE', 'TERMINATED', 'TEXT', 'THEN',
    'TINYBLOB', 'TINYINT', 'TINYTEXT', 'TO', 'TRAILING', 'TRIGGER',
    'TRUE', 'TRUNCATE', 'TYPE', 'UNBOUNDED', 'UNDO', 'UNION', 'UNIQUE',
    'UNLOCK', 'UNSIGNED', 'UPDATE', 'USAGE', 'USE', 'USING',
    'UTC_DATE', 'UTC_TIME', 'UTC_TIMESTAMP', 'VALUES', 'VARBINARY',
    'VARCHAR', 'VARCHARACTER', 'VARYING', 'VIRTUAL', 'WHEN', 'WHERE',
    'WHILE', 'WINDOW', 'WITH', 'WRITE', 'XOR', 'YEAR_MONTH',
    'ZEROFILL',
]


class MySQLPlugin(DatabasePlugin):
    name = 'mysql'
    version = '1.72.1'
    default_prompt = 'mysql \\u@\\h:\\d> '

    def get_sql_lexer_class(self):
        return MySqlLexer

    def get_special_commands(self) -> list[str]:
        return MYSQL_COMMANDS

    def get_extra_keywords(self) -> list[str]:
        return MYSQL_KEYWORDS

    def populate_completer_schema(self, completer, executor) -> None:
        try:
            conn = executor.conn
            if not conn:
                return
            cur = conn.cursor()
            cur.execute("SELECT DATABASE()")
            row = cur.fetchone()
            dbname = row[0] if row else 'mysql'
            completer.set_dbname(dbname)
            completer.extend_schemata(dbname)

            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'"
            )
            tables = [r[0] for r in cur.fetchall()]
            if tables:
                completer.extend_relations([(t,) for t in tables], 'tables')

            cur.execute(
                "SELECT table_name FROM information_schema.views "
                "WHERE table_schema = DATABASE()"
            )
            for r in cur.fetchall():
                completer.extend_relations([(r[0],)], 'views')

            cols = []
            for t in tables:
                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name = %s",
                    (t,),
                )
                for r in cur.fetchall():
                    cols.append((t, r[0]))
            if cols:
                completer.extend_columns(cols, 'tables')

            cur.execute(
                "SELECT routine_name FROM information_schema.routines "
                "WHERE routine_schema = DATABASE() AND routine_type = 'FUNCTION'"
            )
            funcs = [(r[0],) for r in cur.fetchall()]
            if funcs:
                completer.extend_functions(funcs)
        except Exception:
            pass

    def create_executor(self, connection_info: dict):
        from mycli.sqlexecute import SQLExecute
        return SQLExecute(
            database=connection_info.get('database'),
            user=connection_info.get('user'),
            password=connection_info.get('password'),
            host=connection_info.get('host'),
            port=connection_info.get('port'),
            socket=connection_info.get('socket'),
            character_set=connection_info.get('character_set'),
            local_infile=connection_info.get('local_infile'),
            ssl=connection_info.get('ssl'),
            ssh_user=connection_info.get('ssh_user'),
            ssh_host=connection_info.get('ssh_host'),
            ssh_port=connection_info.get('ssh_port'),
            ssh_password=connection_info.get('ssh_password'),
            ssh_key_filename=connection_info.get('ssh_key_filename'),
        )

    def execute_query(self, executor, query: str) -> list[tuple]:
        results = []
        for r in executor.run(query):
            status = r.status_plain if hasattr(r, 'status_plain') else r.status
            results.append((r.preamble, r.rows, r.header, status))
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
        database = user = password = host = None
        port = None
        positional = []

        i = 0
        while i < len(args):
            a = args[i]
            if a in ('-u', '--user') and i + 1 < len(args):
                user = args[i + 1]; i += 2; continue
            if a in ('-p', '--password') and i + 1 < len(args):
                password = args[i + 1]; i += 2; continue
            if a in ('-h', '--host') and i + 1 < len(args):
                host = args[i + 1]; i += 2; continue
            if a in ('-P', '--port') and i + 1 < len(args):
                port = int(args[i + 1]); i += 2; continue
            if a in ('-D', '--database') and i + 1 < len(args):
                database = args[i + 1]; i += 2; continue
            if a.startswith('-u') and len(a) > 2 and not a.startswith('--'):
                user = a[2:]; i += 1; continue
            if a.startswith('-p') and len(a) > 2 and not a.startswith('--'):
                password = a[2:]; i += 1; continue
            if a.startswith('-h') and len(a) > 2 and not a.startswith('--'):
                host = a[2:]; i += 1; continue
            if a.startswith('-P') and len(a) > 2:
                try: port = int(a[2:])
                except ValueError: pass
                i += 1; continue
            if a.startswith('--user='):
                user = a[7:]; i += 1; continue
            if a.startswith('--password='):
                password = a[11:]; i += 1; continue
            if a.startswith('--host='):
                host = a[7:]; i += 1; continue
            if a.startswith('--port='):
                try: port = int(a[7:])
                except ValueError: pass
                i += 1; continue
            if a.startswith('--database='):
                database = a[11:]; i += 1; continue
            if a == '--socket' and i + 1 < len(args):
                i += 2; continue
            if a.startswith('--socket='):
                i += 1; continue
            if not a.startswith('-'):
                positional.append(a)
            i += 1

        for a in args:
            if a.startswith('mysql://'):
                from urllib.parse import urlparse
                u = urlparse(a)
                database = u.path[1:] or database
                user = u.username or user
                password = u.password or password
                host = u.hostname or host
                port = u.port or port

        database = database or (positional[0] if positional else None)

        return {
            'database': database or 'test',
            'user': user or 'root',
            'password': password or '',
            'host': host or 'localhost',
            'port': port or 3306,
            'character_set': 'utf8mb4',
        }

    def get_default_config_path(self) -> str:
        return os.path.expanduser('~/.myclirc')
