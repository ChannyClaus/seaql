from __future__ import annotations

from typing import Any, Protocol, Sequence


class DBCursor(Protocol):
    description: Sequence[Sequence[Any]] | None

    connection: Any

    def execute(self, sql: str, params: Any = ...) -> Any: ...

    def fetchall(self) -> list[tuple[Any, ...]]: ...

    def fetchone(self) -> tuple[Any, ...] | None: ...
