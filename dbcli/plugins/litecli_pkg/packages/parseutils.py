from __future__ import annotations

import re
from typing import Generator, Iterable, Literal

import sqlparse
from sqlparse.sql import Function, Identifier, IdentifierList, Token, TokenList
from sqlparse.tokens import DML, Keyword, Punctuation

cleanup_regex: dict[str, re.Pattern[str]] = {
    "alphanum_underscore": re.compile(r"(\w+)$"),
    "many_punctuations": re.compile(r"([^():,\s]+)$"),
    "most_punctuations": re.compile(r"([^\.():,\s]+)$"),
    "all_punctuations": re.compile(r"([^\s]+)$"),
}

LAST_WORD_INCLUDE_TYPE = Literal["alphanum_underscore", "many_punctuations", "most_punctuations", "all_punctuations"]


def last_word(text: str, include: LAST_WORD_INCLUDE_TYPE = "alphanum_underscore") -> str:
    if not text:
        return ""

    if text[-1].isspace():
        return ""
    else:
        regex = cleanup_regex[include]
        matches = regex.search(text)
        if matches:
            return matches.group(0)
        else:
            return ""


def is_subselect(parsed: TokenList) -> bool:
    if not parsed.is_group:
        return False
    for item in parsed.tokens:
        if item.ttype is DML and item.value.upper() in (
            "SELECT",
            "INSERT",
            "UPDATE",
            "CREATE",
            "DELETE",
        ):
            return True
    return False


def extract_from_part(parsed: TokenList, stop_at_punctuation: bool = True) -> Generator[Token, None, None]:
    tbl_prefix_seen = False
    for item in parsed.tokens:
        if tbl_prefix_seen:
            if is_subselect(item):
                for x in extract_from_part(item, stop_at_punctuation):
                    yield x
            elif stop_at_punctuation and item.ttype is Punctuation:
                return
            elif item.ttype is Keyword and (not item.value.upper() == "FROM") and (not item.value.upper().endswith("JOIN")):
                return
            else:
                yield item
        elif (item.ttype is Keyword or item.ttype is Keyword.DML) and item.value.upper() in (
            "COPY",
            "FROM",
            "INTO",
            "UPDATE",
            "TABLE",
            "JOIN",
        ):
            tbl_prefix_seen = True
        elif isinstance(item, IdentifierList):
            for identifier in item.get_identifiers():
                if identifier.ttype is Keyword and identifier.value.upper() == "FROM":
                    tbl_prefix_seen = True
                    break


def extract_table_identifiers(token_stream: Iterable[Token]) -> Generator[tuple[str | None, str, str | None], None, None]:
    for item in token_stream:
        if isinstance(item, IdentifierList):
            for identifier in item.get_identifiers():
                try:
                    schema_name = identifier.get_parent_name()
                    real_name = identifier.get_real_name()
                except AttributeError:
                    continue
                if real_name:
                    yield (schema_name, real_name, identifier.get_alias())
        elif isinstance(item, Identifier):
            real_name = item.get_real_name()
            schema_name = item.get_parent_name()

            if real_name:
                yield (schema_name, real_name, item.get_alias())
            else:
                name = item.get_name()
                yield (None, name, item.get_alias() or name)
        elif isinstance(item, Function):
            yield (None, item.get_name(), item.get_name())


def extract_tables(sql: str) -> list[tuple[str | None, str, str | None]]:
    parsed = sqlparse.parse(sql)
    if not parsed:
        return []

    insert_stmt = parsed[0].token_first().value.lower() == "insert"
    stream = extract_from_part(parsed[0], stop_at_punctuation=insert_stmt)
    return list(extract_table_identifiers(stream))


def find_prev_keyword(sql: str) -> tuple[Token | None, str]:
    if not sql.strip():
        return None, ""

    parsed = sqlparse.parse(sql)[0]
    flattened = list(parsed.flatten())

    logical_operators = ("AND", "OR", "NOT", "BETWEEN")

    for t in reversed(flattened):
        if t.value == "(" or (t.is_keyword and (t.value.upper() not in logical_operators)):
            idx = flattened.index(t)
            text = "".join(tok.value for tok in flattened[: idx + 1])
            return t, text

    return None, ""


def query_starts_with(query: str, prefixes: Iterable[str]) -> bool:
    prefixes = [prefix.lower() for prefix in prefixes]
    formatted_sql = sqlparse.format(query.lower(), strip_comments=True)
    return bool(formatted_sql) and formatted_sql.split()[0] in prefixes


def queries_start_with(queries: str, prefixes: Iterable[str]) -> bool:
    for query in sqlparse.split(queries):
        if query and query_starts_with(query, prefixes) is True:
            return True
    return False


def is_destructive(queries: str) -> bool:
    keywords = ("drop", "shutdown", "delete", "truncate", "alter")
    return queries_start_with(queries, keywords)
