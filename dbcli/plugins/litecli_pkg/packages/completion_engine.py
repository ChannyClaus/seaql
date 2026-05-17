from __future__ import annotations

from typing import Any

import sqlparse
from sqlparse.sql import Comparison, Identifier, Where, Token
from .parseutils import last_word, extract_tables, find_prev_keyword
from .special.main import parse_special_command


def suggest_type(full_text: str, text_before_cursor: str) -> list[dict[str, Any]]:
    word_before_cursor = last_word(text_before_cursor, include="many_punctuations")

    identifier: Identifier | None = None

    try:
        if word_before_cursor:
            if word_before_cursor.endswith("(") or word_before_cursor.startswith("\\"):
                parsed = sqlparse.parse(text_before_cursor)
            else:
                parsed = sqlparse.parse(text_before_cursor[: -len(word_before_cursor)])

                p = sqlparse.parse(word_before_cursor)[0]

                if p.tokens and isinstance(p.tokens[0], Identifier):
                    identifier = p.tokens[0]
        else:
            parsed = sqlparse.parse(text_before_cursor)
    except (TypeError, AttributeError):
        return [{"type": "keyword"}]

    if len(parsed) > 1:
        current_pos = len(text_before_cursor)
        stmt_start, stmt_end = 0, 0

        for statement in parsed:
            stmt_len = len(str(statement))
            stmt_start, stmt_end = stmt_end, stmt_end + stmt_len

            if stmt_end >= current_pos:
                text_before_cursor = full_text[stmt_start:current_pos]
                full_text = full_text[stmt_start:]
                break

    elif parsed:
        statement = parsed[0]
    else:
        statement = None

    if statement:
        tok1 = statement.token_first()
        if tok1 and tok1.value.startswith("."):
            return suggest_special(text_before_cursor)
        elif tok1 and tok1.value.startswith("\\"):
            return suggest_special(text_before_cursor)
        elif tok1 and tok1.value.startswith("source"):
            return suggest_special(text_before_cursor)
        elif text_before_cursor and text_before_cursor.startswith(".open "):
            return suggest_special(text_before_cursor)

    last_token = statement and statement.token_prev(len(statement.tokens))[1] or ""

    return suggest_based_on_last_token(last_token, text_before_cursor, full_text, identifier)


def suggest_special(text: str) -> list[dict[str, Any]]:
    text = text.lstrip()
    cmd, _, arg = parse_special_command(text)

    if cmd == text:
        return [{"type": "special"}]

    if cmd in ("\\u", "\\r"):
        return [{"type": "database"}]

    if cmd in ("\\T"):
        return [{"type": "table_format"}]

    if cmd in ["\\f", "\\fs", "\\fd"]:
        return [{"type": "favoritequery"}]

    if cmd in ["\\d", "\\dt", "\\dt+", ".schema", ".indexes"]:
        return [
            {"type": "table", "schema": []},
            {"type": "view", "schema": []},
            {"type": "schema"},
        ]

    if cmd in ["\\.", "source", ".open", ".read"]:
        return [{"type": "file_name"}]

    if cmd in [".import"]:
        if _expecting_arg_idx(arg, text) == 1:
            return [{"type": "file_name"}]
        else:
            return [{"type": "table", "schema": []}]

    if cmd in [".llm", ".ai", "\\llm", "\\ai"]:
        return [{"type": "llm"}]

    return [{"type": "keyword"}, {"type": "special"}]


def _expecting_arg_idx(arg: str, text: str) -> int:
    args = arg.split()
    return len(args) + int(text[-1].isspace())


def suggest_based_on_last_token(
    token: str | Token | None,
    text_before_cursor: str,
    full_text: str,
    identifier: Identifier | None,
) -> list[dict[str, Any]]:
    if isinstance(token, str):
        token_v = token.lower()
    elif isinstance(token, Comparison):
        token_v = token.tokens[-1].value.lower()
    elif isinstance(token, Where):
        prev_keyword, text_before_cursor = find_prev_keyword(text_before_cursor)
        return suggest_based_on_last_token(prev_keyword, text_before_cursor, full_text, identifier)
    else:
        assert token is not None
        token_v = token.value.lower()

    def is_operand(x: str | None) -> bool:
        if not x:
            return False
        return any([x.endswith(op) for op in ["+", "-", "*", "/"]])

    if not token:
        return [{"type": "keyword"}, {"type": "special"}]
    elif token_v.endswith("("):
        p = sqlparse.parse(text_before_cursor)[0]

        if p.tokens and isinstance(p.tokens[-1], Where):
            column_suggestions = suggest_based_on_last_token("where", text_before_cursor, full_text, identifier)

            where = p.tokens[-1]
            idx, prev_tok = where.token_prev(len(where.tokens) - 1)

            if isinstance(prev_tok, Comparison):
                prev_tok = prev_tok.tokens[-1]

            prev_tok = prev_tok.value.lower()
            if prev_tok == "exists":
                return [{"type": "keyword"}]
            else:
                return column_suggestions

        idx, prev_tok = p.token_prev(len(p.tokens) - 1)
        if prev_tok and prev_tok.value and prev_tok.value.lower() == "using":
            tables = extract_tables(full_text)
            return [{"type": "column", "tables": tables, "drop_unique": True}]
        elif p.token_first().value.lower() == "select":
            if last_word(text_before_cursor, "all_punctuations").startswith("("):
                return [{"type": "keyword"}]
        elif p.token_first().value.lower() == "show":
            return [{"type": "show"}]

        return [{"type": "column", "tables": extract_tables(full_text)}]
    elif token_v in ("set", "order by", "distinct"):
        return [{"type": "column", "tables": extract_tables(full_text)}]
    elif token_v == "as":
        return []
    elif token_v in ("show"):
        return [{"type": "show"}]
    elif token_v in ("to",):
        p = sqlparse.parse(text_before_cursor)[0]
        if p.token_first().value.lower() == "change":
            return [{"type": "change"}]
        else:
            return [{"type": "user"}]
    elif token_v in ("user", "for"):
        return [{"type": "user"}]
    elif token_v in ("select", "where", "having"):
        parent = (identifier and identifier.get_parent_name()) or []

        tables = extract_tables(full_text)
        if parent:
            tables = [t for t in tables if identifies(parent, *t)]
            return [
                {"type": "column", "tables": tables},
                {"type": "table", "schema": parent},
                {"type": "view", "schema": parent},
                {"type": "function", "schema": parent},
            ]
        else:
            aliases = [alias or table for (schema, table, alias) in tables]
            return [
                {"type": "column", "tables": tables},
                {"type": "function", "schema": []},
                {"type": "alias", "aliases": aliases},
                {"type": "keyword"},
            ]
    elif (token_v.endswith("join") and isinstance(token, Token) and token.is_keyword) or (
        token_v in ("copy", "from", "update", "into", "describe", "truncate", "desc", "explain")
    ):
        schema = (identifier and identifier.get_parent_name()) or []

        suggest = [{"type": "table", "schema": schema}]

        if not schema:
            suggest.insert(0, {"type": "schema"})

        if token_v != "truncate":
            suggest.append({"type": "view", "schema": schema})

        return suggest

    elif token_v in ("table", "view", "function"):
        rel_type = token_v
        schema = (identifier and identifier.get_parent_name()) or []
        if schema:
            return [{"type": rel_type, "schema": schema}]
        else:
            return [{"type": "schema"}, {"type": rel_type, "schema": []}]
    elif token_v == "on":
        tables = extract_tables(full_text)
        parent = (identifier and identifier.get_parent_name()) or []
        if parent:
            tables = [t for t in tables if identifies(parent, *t)]
            return [
                {"type": "column", "tables": tables},
                {"type": "table", "schema": parent},
                {"type": "view", "schema": parent},
                {"type": "function", "schema": parent},
            ]
        else:
            aliases = [alias or table for (schema, table, alias) in tables]
            suggest = [{"type": "alias", "aliases": aliases}]

            if not aliases:
                suggest.append({"type": "table", "schema": parent})
            return suggest

    elif token_v in ("use", "database", "template", "connect"):
        return [{"type": "database"}]
    elif token_v == "tableformat":
        return [{"type": "table_format"}]
    elif token_v.endswith(",") or is_operand(token_v) or token_v in ["=", "and", "or"]:
        prev_keyword, text_before_cursor = find_prev_keyword(text_before_cursor)
        if prev_keyword:
            return suggest_based_on_last_token(prev_keyword, text_before_cursor, full_text, identifier)
        else:
            return []
    else:
        return [{"type": "keyword"}]


def identifies(id: Any, schema: str | None, table: str, alias: str | None) -> bool:
    return (id == alias) or (id == table) or (schema is not None and (id == schema + "." + table))
