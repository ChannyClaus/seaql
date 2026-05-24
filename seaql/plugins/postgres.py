import os

from cli_helpers.tabular_output import TabularOutputFormatter
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from pygments.lexers.sql import PostgresLexer

from seaql.core.plugin import DatabasePlugin


class PostgresPlugin(DatabasePlugin):
    name = 'postgres'
    version = '4.3.0'
    lexer = PygmentsLexer(PostgresLexer)
    default_prompt = '\\u@\\h:\\d> '

    def create_style(self, syntax_style: str, cli_style: dict) -> Style:
        from pgcli.pgstyle import style_factory
        return style_factory(syntax_style, cli_style)

    def create_completer(self, smart_completion: bool, settings: dict):
        from pgcli.pgcompleter import PGCompleter
        from pgspecial.main import PGSpecial
        self._pgspecial = PGSpecial()
        return PGCompleter(
            smart_completion=smart_completion,
            pgspecial=self._pgspecial,
            settings=settings,
        )

    def create_executor(self, connection_info: dict):
        from pgcli.pgexecute import PGExecute
        def noop_callback(notify):
            pass
        return PGExecute(
            database=connection_info.get('database') or '',
            user=connection_info.get('user') or '',
            password=connection_info.get('password') or '',
            host=connection_info.get('host') or '',
            port=connection_info.get('port') or '',
            dsn=connection_info.get('dsn') or None,
            notify_callback=noop_callback,
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
        return os.path.expanduser('~/.pgclirc')
