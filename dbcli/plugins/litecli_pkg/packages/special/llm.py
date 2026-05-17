from __future__ import annotations

import contextlib
import importlib
import io
import logging
import os
import pprint
import re
import shlex
import sys
from runpy import run_module
from time import time
from typing import Any

import click

from . import export
from .main import Verbosity, parse_special_command
from .types import DBCursor


def _load_llm_module() -> Any | None:
    try:
        return importlib.import_module("llm")
    except ImportError:
        return None


def _load_llm_cli_module() -> Any | None:
    try:
        return importlib.import_module("llm.cli")
    except ImportError:
        return None


llm_module = _load_llm_module()
llm_cli_module = _load_llm_cli_module()

llm = llm_module

LLM_IMPORTED = llm_module is not None

cli: click.Command | None
if llm_cli_module is not None:
    llm_cli = getattr(llm_cli_module, "cli", None)
    cli = llm_cli if isinstance(llm_cli, click.Command) else None
else:
    cli = None

LLM_CLI_IMPORTED = cli is not None

log = logging.getLogger(__name__)

LLM_TEMPLATE_NAME = "litecli-llm-template"
LLM_CLI_COMMANDS: list[str] = list(cli.commands.keys()) if isinstance(cli, click.Group) else []
if llm_module is not None:
    get_models = getattr(llm_module, "get_models", None)
    MODELS: dict[str, None] = {x.model_id: None for x in get_models()} if callable(get_models) else {}
else:
    MODELS = {}


def run_external_cmd(
    cmd: str,
    *args: str,
    capture_output: bool = False,
    restart_cli: bool = False,
    raise_exception: bool = True,
) -> tuple[int, str]:
    original_exe = sys.executable
    original_args = sys.argv

    try:
        sys.argv = [cmd] + list(args)
        code: int = 0

        if capture_output:
            buffer = io.StringIO()
            stack = contextlib.ExitStack()
            stack.enter_context(contextlib.redirect_stdout(buffer))
            stack.enter_context(contextlib.redirect_stderr(buffer))
            redirect: contextlib.AbstractContextManager[Any] = stack
        else:
            redirect = contextlib.nullcontext()

        with redirect:
            try:
                run_module(cmd, run_name="__main__")
            except SystemExit as e:
                exit_code = e.code
                if isinstance(exit_code, int):
                    code = exit_code
                else:
                    code = 1
                if code != 0 and raise_exception:
                    if capture_output:
                        raise RuntimeError(buffer.getvalue())
                    else:
                        raise RuntimeError(f"Command {cmd} failed with exit code {code}.")
            except Exception as e:
                code = 1
                if raise_exception:
                    if capture_output:
                        raise RuntimeError(buffer.getvalue())
                    else:
                        raise RuntimeError(f"Command {cmd} failed: {e}")

        if restart_cli and code == 0:
            os.execv(original_exe, [original_exe] + original_args)

        if capture_output:
            return code, buffer.getvalue()
        else:
            return code, ""
    finally:
        sys.argv = original_args


def build_command_tree(cmd: click.Command) -> dict[str, Any] | None:
    tree: dict[str, Any] = {}
    if isinstance(cmd, click.Group):
        for name, subcmd in cmd.commands.items():
            if cmd.name == "models" and name == "default":
                tree[name] = MODELS
            else:
                tree[name] = build_command_tree(subcmd)
    else:
        return None
    return tree


COMMAND_TREE: dict[str, Any] | None = build_command_tree(cli) if cli is not None else {}


def get_completions(tokens: list[str], tree: dict[str, Any] | None = COMMAND_TREE) -> list[str]:
    if not LLM_CLI_IMPORTED:
        return []
    for token in tokens:
        if token.startswith("-"):
            continue
        if tree and token in tree:
            tree = tree[token]
        else:
            return []

    return list(tree.keys()) if tree else []


@export
class FinishIteration(Exception):
    def __init__(self, results: Any | None = None) -> None:
        self.results: Any | None = results


USAGE = """
Use an LLM to create SQL queries to answer questions from your database.
Examples:

# Ask a question.
> \\llm 'Most visited urls?'

# List available models
> \\llm models
gpt-4o
gpt-3.5-turbo
qwq

# Change default model
> \\llm models default llama3

# Set api key (not required for local models)
> \\llm keys set openai


# Install a model plugin
> \\llm install llm-ollama
llm-ollama installed.

# Plugins directory
# https://llm.datasette.io/en/stable/plugins/directory.html
"""

NEED_DEPENDENCIES = """
To enable LLM features you need to install litecli with AI support:

    pip install 'litecli[ai]'

or install LLM libraries separately

   pip install llm

This is required to use the \\llm command.
"""

_SQL_CODE_FENCE = r"```sql\n(.*?)\n```"
PROMPT = """
You are a helpful assistant who is a SQLite expert. You are embedded in a SQLite
cli tool called litecli.

Answer this question:

$question

Use the following context if it is relevant to answering the question. If the
question is not about the current database then ignore the context.

You are connected to a SQLite database with the following schema:

$db_schema

Here is a sample row of data from each table:

$sample_data

If the answer can be found using a SQL query, include a sql query in a code
fence such as this one:

```sql
SELECT count(*) FROM table_name;
```
Keep your explanation concise and focused on the question asked.
"""


def ensure_litecli_template(replace: bool = False) -> None:
    if not replace:
        code, _ = run_external_cmd("llm", "templates", "show", LLM_TEMPLATE_NAME, capture_output=True, raise_exception=False)
        if code == 0:
            return

    run_external_cmd("llm", PROMPT, "--save", LLM_TEMPLATE_NAME)
    return


@export
def handle_llm(text: str, cur: DBCursor) -> tuple[str, str | None, float]:
    _, mode, arg = parse_special_command(text)
    is_verbose = mode is Verbosity.VERBOSE
    is_succinct = mode is Verbosity.SUCCINCT

    if not LLM_IMPORTED:
        output = [(None, None, None, NEED_DEPENDENCIES)]
        raise FinishIteration(output)

    if not arg.strip():
        output = [(None, None, None, USAGE)]
        raise FinishIteration(output)

    parts = shlex.split(arg)

    restart = False
    if "-c" in parts:
        capture_output = True
        use_context = False
    elif "prompt" in parts:
        capture_output = True
        use_context = True
    elif "install" in parts or "uninstall" in parts:
        capture_output = False
        use_context = False
        restart = True
    elif parts[0] in LLM_CLI_COMMANDS:
        capture_output = False
        use_context = False
    elif "--help" == parts[0]:
        capture_output = False
        use_context = False
    elif not set(parts).intersection(LLM_CLI_COMMANDS):
        capture_output = True
        use_context = True
    else:
        capture_output = True
        use_context = True

    if not use_context:
        args = parts
        if capture_output:
            click.echo("Calling llm command")
            start = time()
            _, result = run_external_cmd("llm", *args, capture_output=capture_output)
            end = time()
            match = re.search(_SQL_CODE_FENCE, result, re.DOTALL)
            if match:
                sql = match.group(1).strip()
            else:
                output = [(None, None, None, result)]
                raise FinishIteration(output)

            context = "" if is_succinct else result
            return context, sql, end - start
        else:
            run_external_cmd("llm", *args, restart_cli=restart)
            raise FinishIteration(None)

    try:
        ensure_litecli_template()
        start = time()
        result, sql, prompt_text = sql_using_llm(cur=cur, question=arg, verbose=is_verbose)
        end = time()
        context = "" if is_succinct else result
        if is_verbose and prompt_text is not None:
            click.echo("LLM Prompt:")
            click.echo(prompt_text)
            click.echo("---")
        return context, sql, end - start
    except Exception as e:
        raise RuntimeError(e)


@export
def is_llm_command(command: str) -> bool:
    cmd, _, _ = parse_special_command(command)
    return cmd in ("\\llm", "\\ai", ".llm", ".ai")


@export
def sql_using_llm(
    cur: DBCursor,
    question: str | None = None,
    verbose: bool = False,
) -> tuple[str, str | None, str | None]:
    if cur is None:
        raise RuntimeError("Connect to a datbase and try again.")
    schema_query = """
        SELECT sql FROM sqlite_master
        WHERE sql IS NOT NULL
        ORDER BY tbl_name, type DESC, name
    """
    tables_query = """
            SELECT name FROM sqlite_master
            WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'sqlean_%'
            ORDER BY 1
    """
    click.echo("Preparing schema information to feed the llm")
    sample_row_query = "SELECT * FROM {table} LIMIT 1"
    log.debug(schema_query)
    cur.execute(schema_query)
    db_schema = "\n".join([x for (x,) in cur.fetchall()])

    log.debug(tables_query)
    cur.execute(tables_query)
    sample_data = {}
    for (table,) in cur.fetchall():
        sample_row = sample_row_query.format(table=table)
        cur.execute(sample_row)
        if cur.description is None:
            continue
        cols = [x[0] for x in cur.description]
        row = cur.fetchone()
        if row is None:
            continue
        sample_data[table] = list(zip(cols, row))

    args = [
        "--template",
        LLM_TEMPLATE_NAME,
        "--param",
        "db_schema",
        db_schema,
        "--param",
        "sample_data",
        sample_data,
        "--param",
        "question",
        question,
        " ",
    ]
    click.echo("Invoking llm command with schema information")
    str_args = [str(a) for a in args]
    _, result = run_external_cmd("llm", *str_args, capture_output=True)
    click.echo("Received response from the llm command")
    match = re.search(_SQL_CODE_FENCE, result, re.DOTALL)
    sql = match.group(1).strip() if match else ""

    prompt_text = None
    if verbose:
        prompt_text = PROMPT
        prompt_text = prompt_text.replace("$db_schema", db_schema)
        prompt_text = prompt_text.replace("$sample_data", pprint.pformat(sample_data))
        prompt_text = prompt_text.replace("$question", question or "")
    if verbose:
        return result, sql, prompt_text
    return result, sql, None
