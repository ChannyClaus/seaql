from __future__ import annotations

import os


def list_path(root_dir: str) -> list[str]:
    res: list[str] = []
    if os.path.isdir(root_dir):
        for name in os.listdir(root_dir):
            res.append(name)
    return res


def complete_path(curr_dir: str, last_dir: str) -> str | None:
    if not last_dir or curr_dir.startswith(last_dir):
        return curr_dir
    elif last_dir == "~":
        return os.path.join(last_dir, curr_dir)
    return None


def parse_path(root_dir: str) -> tuple[str, str, int]:
    base_dir, last_dir, position = "", "", 0
    if root_dir:
        base_dir, last_dir = os.path.split(root_dir)
        position = -len(last_dir) if last_dir else 0
    return base_dir, last_dir, position


def suggest_path(root_dir: str) -> list[str]:
    if not root_dir:
        return [str(x) for x in [os.path.abspath(os.sep), "~", os.curdir, os.pardir]]

    if "~" in root_dir:
        root_dir = str(os.path.expanduser(root_dir))

    if not os.path.exists(root_dir):
        root_dir, _ = os.path.split(root_dir)

    return list_path(root_dir)


def dir_path_exists(path: str) -> bool:
    return os.path.exists(os.path.dirname(path))
