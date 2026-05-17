from __future__ import annotations


import os
import subprocess


def handle_cd_command(arg: str) -> tuple[bool, str | None]:
    CD_CMD = "cd"
    tokens = arg.split(CD_CMD + " ")
    directory = tokens[-1] if len(tokens) > 1 else None
    if not directory:
        return False, "No folder name was provided."
    try:
        os.chdir(directory)
        subprocess.call(["pwd"])
        return True, None
    except OSError as e:
        return False, e.strerror


def format_uptime(uptime_in_seconds: str) -> str:
    m, s = divmod(int(uptime_in_seconds), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    uptime_values: list[str] = []

    for value, unit in ((d, "days"), (h, "hours"), (m, "min"), (s, "sec")):
        if value == 0 and not uptime_values:
            continue
        elif value == 1 and unit.endswith("s"):
            unit = unit[:-1]
        uptime_values.append("{0} {1}".format(value, unit))

    uptime = " ".join(uptime_values)
    return uptime


def check_if_sqlitedotcommand(command: object) -> bool:
    sqlite3dotcommands = [
        ".archive",
        ".auth",
        ".backup",
        ".bail",
        ".binary",
        ".cd",
        ".changes",
        ".check",
        ".clone",
        ".connection",
        ".databases",
        ".dbconfig",
        ".dbinfo",
        ".dump",
        ".echo",
        ".eqp",
        ".excel",
        ".exit",
        ".expert",
        ".explain",
        ".filectrl",
        ".fullschema",
        ".headers",
        ".help",
        ".import",
        ".imposter",
        ".indexes",
        ".limit",
        ".lint",
        ".load",
        ".log",
        ".mode",
        ".nonce",
        ".nullvalue",
        ".once",
        ".open",
        ".output",
        ".parameter",
        ".print",
        ".progress",
        ".prompt",
        ".quit",
        ".read",
        ".recover",
        ".restore",
        ".save",
        ".scanstats",
        ".schema",
        ".selftest",
        ".separator",
        ".session",
        ".sha3sum",
        ".shell",
        ".show",
        ".stats",
        ".system",
        ".tables",
        ".testcase",
        ".testctrl",
        ".timeout",
        ".timer",
        ".trace",
        ".vfsinfo",
        ".vfslist",
        ".vfsname",
        ".width",
    ]

    if isinstance(command, str):
        head = command.split(" ", 1)[0].lower()
        return head in sqlite3dotcommands
    return False
