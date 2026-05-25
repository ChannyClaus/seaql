import logging
import os
import sys
import threading
from pathlib import Path

from prompt_toolkit.application import get_app
from prompt_toolkit.completion import DynamicCompleter, ThreadedCompleter
from prompt_toolkit.cursor_shapes import ModalCursorShapeConfig
from prompt_toolkit.enums import DEFAULT_BUFFER, EditingMode
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import CompleteStyle, PromptSession

from .plugin import DatabasePlugin
from seaql.plugins.plotter import store_result, plot_timeseries


class DbCliApp:
    """Shared REPL application for all database plugins."""

    def __init__(self, plugin: DatabasePlugin, connection_info: dict):
        self.plugin = plugin
        self.connection_info = connection_info
        self.logger = logging.getLogger(f'seaql.{plugin.name}')
        self.query_history: list = []
        self.executor = None
        self.completer = None
        self.prompt_session: PromptSession | None = None
        self._completer_lock = threading.Lock()
        self._history_file = Path.home() / ".seaql" / "history"

        handler = logging.NullHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s - %(message)s'))
        root = logging.getLogger('seaql')
        root.addHandler(handler)
        root.setLevel(logging.CRITICAL)

        self._connect()

    def _connect(self) -> None:
        try:
            self.executor = self.plugin.create_executor(self.connection_info)
            self.completer = self.plugin.create_completer(
                smart_completion=True,
                settings={'executor': self.executor},
            )
        except Exception as e:
            self.logger.debug('Connection failed: %r', e)
            print(f"\033[31m{e}\033[0m", file=sys.stderr)
            sys.exit(1)

    def run_cli(self) -> None:
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        self.prompt_session = PromptSession(
            lexer=self.plugin.lexer,
            reserve_space_for_menu=5,
            message=self._get_message(self.plugin.default_prompt),
            prompt_continuation=self._get_continuation('.'),
            complete_style=CompleteStyle.COLUMN,
            multiline=self._cli_is_multiline(),
            completer=ThreadedCompleter(DynamicCompleter(lambda: self.completer)),
            complete_while_typing=True,
            style=self.plugin.create_style('default', {}),
            include_default_pygments_style=False,
            search_ignore_case=True,
            cursor=ModalCursorShapeConfig(),
            history=FileHistory(str(self._history_file)),
        )

        print(f'{self.plugin.name} {self.plugin.version}')

        try:
            while True:
                try:
                    text = self.prompt_session.prompt()
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    raise
                self._execute_and_display(text)
        except EOFError:
            print('Goodbye!')

    def _get_message(self, prompt_format):
        def message():
            return ANSI(self._format_prompt(prompt_format))
        return message

    def _get_continuation(self, char):
        def continuation(width, line_number, is_soft_wrap):
            return [('class:continuation', char * (width - 1) + ' ')]
        return continuation

    @staticmethod
    def _multiline_exception(text: str) -> bool:
        return True

    def _cli_is_multiline(self):
        @Condition
        def cond():
            try:
                buf = get_app().layout.get_buffer_by_name(DEFAULT_BUFFER)
                if buf is None:
                    return True
                return not self._multiline_exception(buf.document.text)
            except Exception:
                return True
        return cond

    def _format_prompt(self, prompt_format):
        host = self.connection_info.get('host', '(none)')
        user = self.connection_info.get('user', '(none)')
        dbname = self.connection_info.get('database', '(none)')
        prompt = prompt_format.replace('\\u', user)
        prompt = prompt.replace('\\h', host)
        prompt = prompt.replace('\\d', dbname)
        return prompt

    def _execute_and_display(self, text: str) -> None:
        if not text.strip():
            return
        stripped = text.strip()
        if stripped.lower() in ('exit', 'quit', ':q', '\\q'):
            raise EOFError

        if stripped.startswith('\\ts'):
            arg = stripped[3:].strip()
            results = plot_timeseries(arg)
            output = self.plugin.format_output(results, 'psql')
            for line in output:
                print(line)
            return

        if not stripped.startswith('\\') and not stripped.endswith(';'):
            stripped += ';'
        try:
            results = self.plugin.execute_query(self.executor, stripped)
            materialized = []
            for title, rows, headers, status in results:
                if rows is not None:
                    rows = list(rows)
                materialized.append((title, rows, headers, status))
                if headers is not None and rows is not None:
                    store_result(headers, rows)
            output = self.plugin.format_output(materialized, 'psql')
            for line in output:
                print(line)
        except Exception as e:
            self.logger.error('sql: %r, error: %r', stripped, e)
            print(f"\033[31m{e}\033[0m", file=sys.stderr)
