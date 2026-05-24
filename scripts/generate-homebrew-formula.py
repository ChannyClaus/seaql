"""Generate a Homebrew formula for seaql from PyPI metadata.

Usage:
    python scripts/generate-homebrew-formula.py 0.1.3 > seaql.rb

Requires Python 3.10+ with pip available.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request


def get_pypi_sdist(name: str, version: str) -> tuple[str, str] | None:
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        for u in data["urls"]:
            if u["packagetype"] == "sdist":
                return u["url"], u["digests"]["sha256"]
        for u in data["urls"]:
            if u["packagetype"] == "bdist_wheel" and "none-any" in u["filename"]:
                return u["url"], u["digests"]["sha256"]
        return data["urls"][0]["url"], data["urls"][0]["digests"]["sha256"]
    except Exception as e:
        print(f"  # WARNING: failed to fetch {name}=={version}: {e}", file=sys.stderr)
        return None


def get_project_name(pkg_spec: str) -> str:
    name, *_ = pkg_spec.split("==")
    return name.strip()


def pip_freeze(venv_python: str) -> list[str]:
    result = subprocess.run(
        [venv_python, "-m", "pip", "freeze"],
        capture_output=True, text=True, check=True,
    )
    return [line.strip() for line in result.stdout.strip().split("\n") if "==" in line]


def resource_name(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def generate_formula(version: str) -> str:
    seaql_url, seaql_sha256 = get_pypi_sdist("seaql", version)
    if not seaql_url:
        raise SystemExit(f"Could not find seaql {version} on PyPI")

    print(f"  # Installing seaql=={version} in temporary venv to resolve dependencies...", file=sys.stderr)
    with tempfile.TemporaryDirectory(prefix="seaql-brew-") as tmpdir:
        subprocess.run(
            [sys.executable, "-m", "venv", f"{tmpdir}/venv"],
            check=True, capture_output=True,
        )
        venv_python = f"{tmpdir}/venv/bin/python" if os.name != "nt" else f"{tmpdir}/venv/Scripts/python.exe"

        subprocess.run(
            [venv_python, "-m", "pip", "install", "-q", f"seaql=={version}"],
            check=True, capture_output=True,
        )

        deps = pip_freeze(venv_python)

    resources = []
    for dep in deps:
        name = get_project_name(dep)
        if name.lower() == "seaql":
            continue
        ver = dep.split("==", 1)[1]
        info = get_pypi_sdist(resource_name(name), ver)
        if info:
            url, sha = info
            resources.append((name, url, sha))

    resources.sort(key=lambda x: x[0].lower())

    lines = []
    lines.append(f'class Seaql < Formula')
    lines.append(f'  include Language::Python::Virtualenv')
    lines.append(f'')
    lines.append(f'  desc "Unified CLI for MySQL, PostgreSQL, and SQLite databases"')
    lines.append(f'  homepage "https://github.com/ChannyClaus/seaql"')
    lines.append(f'  url "{seaql_url}"')
    lines.append(f'  sha256 "{seaql_sha256}"')
    lines.append(f'  license "BSD-3-Clause"')
    lines.append(f'')
    lines.append(f'  depends_on "python@3.13"')
    lines.append(f'')
    for name, url, sha in resources:
        rname = resource_name(name)
        lines.append(f'  resource "{rname}" do')
        lines.append(f'    url "{url}"')
        lines.append(f'    sha256 "{sha}"')
        lines.append(f'  end')
        lines.append(f'')
    lines.append(f'  def install')
    lines.append(f'    virtualenv_install_with_resources')
    lines.append(f'  end')
    lines.append(f'')
    lines.append(f'  test do')
    lines.append(f'    system bin/"seaql", "--help"')
    lines.append(f'  end')
    lines.append(f'end')

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <version>", file=sys.stderr)
        sys.exit(1)

    version = sys.argv[1].lstrip("v")
    if not re.match(r"^\d+\.\d+\.\d+", version):
        print(f"Invalid version: {version}", file=sys.stderr)
        sys.exit(1)

    print(generate_formula(version))
