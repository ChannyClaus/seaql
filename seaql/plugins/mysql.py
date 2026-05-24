import os

from cli_helpers.tabular_output import TabularOutputFormatter
from prompt_toolkit.styles import Style
from pygments.lexers.sql import MySqlLexer

from seaql.core.plugin import DatabasePlugin


class MySQLPlugin(DatabasePlugin):
    name = 'mysql'
    version = '1.72.1'
    default_prompt = 'mysql \\u@\\h:\\d> '

    def get_sql_lexer_class(self):
        return MySqlLexer

    def create_style(self, syntax_style: str, cli_style: dict) -> Style:
        from mycli.clistyle import style_factory_ptoolkit
        return style_factory_ptoolkit(syntax_style, cli_style)

    def create_completer(self, smart_completion: bool, settings: dict):
        from mycli.sqlcompleter import SQLCompleter
        return SQLCompleter(
            smart_completion=smart_completion,
            supported_formats=['psql', 'csv', 'tsv'],
            keyword_casing='auto',
        )

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
