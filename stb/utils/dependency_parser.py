# Taken from poetry project: https://github.com/python-poetry

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

import tomli as toml


@dataclass
class DependencySpec:
    name: str
    path: Union[str, None] = None
    version: Union[str, None] = None
    extras: Union[List[str], None] = None


def _parse_dependency_specification_simple(requirement: str) -> Union[DependencySpec, None]:
    extras: List[str] = []
    pair = re.sub("^([^@=: ]+)(?:@|==|(?<![<>~!])=|:| )(.*)$", "\\1 \\2", requirement)
    pair = pair.strip()

    require = DependencySpec("")

    if " " in pair:
        name, version = pair.split(" ", 2)
        extras_m = re.search(r"\[([\w\d,-_]+)\]$", name)
        if extras_m:
            extras = [e.strip() for e in extras_m.group(1).split(",")]
            name, _ = name.split("[")

        require.name = name
        require.version = version
    else:
        m = re.match(r"^([^><=!: ]+)((?:>=|<=|>|<|!=|~=|~|\^).*)$", requirement.strip())
        if m:
            name, constraint = m.group(1), m.group(2)
            extras_m = re.search(r"\[([\w\d,-_]+)\]$", name)
            if extras_m:
                extras = [e.strip() for e in extras_m.group(1).split(",")]
                name, _ = name.split("[")

            require.name = name
            require.version = constraint
        else:
            extras_m = re.search(r"\[([\w\d,-_]+)\]$", pair)
            if extras_m:
                extras = [e.strip() for e in extras_m.group(1).split(",")]
                pair, _ = pair.split("[")

            require.name = pair

    if extras:
        require.extras = extras

    return require


def _parse_dependency_specification_path(requirement):
    path = Path(requirement)
    if path.exists() and path.is_dir():
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            package_name = toml.loads(pyproject.read_text())["tool"]["poetry"]["name"]
            return DependencySpec(name=package_name, path=str(path))


def parse_dependency_specification(requirement: str) -> DependencySpec:
    requirement = requirement.strip()

    extras = []
    extras_m = re.search(r"\[([\w\d,-_ ]+)\]$", requirement)
    if extras_m:
        extras = [e.strip() for e in extras_m.group(1).split(",")]
        requirement, _ = requirement.split("[")

    specification = _parse_dependency_specification_path(requirement) or _parse_dependency_specification_simple(
        requirement
    )

    if specification:
        if extras and not specification.extras:
            specification.extras = extras
        return specification

    raise ValueError(f"Invalid dependency specification: {requirement}")
