import os

from cli_helpers.tabular_output import TabularOutputFormatter
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from pygments.lexers.sql import SqlLexer

from dbcli.core.plugin import DatabasePlugin


class SQLitePlugin(DatabasePlugin):
    name = 'sqlite'
    version = '1.15.0'
    lexer = PygmentsLexer(SqlLexer)
    default_prompt = 'sqlite> '

    def create_style(self, syntax_style: str, cli_style: dict) -> Style:
        from pygments.styles import get_style_by_name
        from prompt_toolkit.styles.pygments import style_from_pygments_cls
        return style_from_pygments_cls(get_style_by_name(syntax_style))

    def create_completer(self, smart_completion: bool, settings: dict):
        from dbcli.plugins.litecli_pkg.sqlcompleter import SQLCompleter
        return SQLCompleter(
            supported_formats=['psql', 'csv', 'tsv'],
            keyword_casing='auto',
        )

    def create_executor(self, connection_info: dict):
        from dbcli.plugins.litecli_pkg.sqlexecute import SQLExecute
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
