"""Database plugin interface."""

from abc import ABC, abstractmethod
from typing import Any

from prompt_toolkit.completion import Completer
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style


class DatabasePlugin(ABC):
    """A database backend plugin providing database-specific functionality."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @property
    def lexer(self) -> PygmentsLexer:
        return PygmentsLexer(self.get_sql_lexer_class())

    @abstractmethod
    def get_sql_lexer_class(self):
        ...

    @property
    def default_prompt(self) -> str:
        return "\\u@\\h:\\d> "

    def create_style(self, syntax_style: str, cli_style: dict) -> Style:
        from pygments.styles import get_style_by_name
        from prompt_toolkit.styles.pygments import style_from_pygments_cls
        return style_from_pygments_cls(get_style_by_name(syntax_style))

    def create_output_style(self, syntax_style: str, cli_style: dict) -> Any:
        return None

    def create_completer(self, smart_completion: bool, settings: dict) -> Completer:
        from seaql.plugins.litecli_pkg.sqlcompleter import SQLCompleter

        completer = SQLCompleter(
            supported_formats=['psql', 'csv', 'tsv'],
            keyword_casing='auto',
        )
        commands = self.get_special_commands()
        if commands:
            completer.extend_special_commands(commands)
        keywords = self.get_extra_keywords()
        if keywords:
            completer.extend_keywords(keywords)
        executor = settings.get('executor')
        if executor:
            self.populate_completer_schema(completer, executor)
        return completer

    def get_special_commands(self) -> list[str]:
        return []

    def get_extra_keywords(self) -> list[str]:
        return []

    def populate_completer_schema(self, completer, executor) -> None:
        pass

    @abstractmethod
    def create_executor(self, connection_info: dict) -> Any: ...

    @abstractmethod
    def execute_query(self, executor: Any, query: str) -> list[tuple]:
        """Execute a query and return list of (title, rows, headers, status)."""
        ...

    @abstractmethod
    def format_output(self, results: list[tuple], table_format: str) -> list[str]:
        """Format query results into output lines."""
        ...

    @abstractmethod
    def connect(self, args: list[str]) -> dict: ...

    @abstractmethod
    def get_default_config_path(self) -> str: ...

    def get_default_config_content(self) -> str:
        return ''
