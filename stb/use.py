import itertools
from pathlib import Path
from typing import Any, List

import tomli as toml
import typer
from pysh import sh, which

from stb.config import CONFIG

from .utils.dependency_parser import parse_dependency_specification

PYENV_INSTALLED = which("pyenv")


def use_packages(requirements: List[str], editable: bool = False, fix: bool = False) -> None:
    editable_arg = "--editable" if editable else ""
    pyproject_path = Path("pyproject.toml")
    pyproject = toml.loads(pyproject_path.read_text())
    dependencies = pyproject["tool"]["poetry"]["dependencies"]
    if not pyproject_path.exists():
        raise FileNotFoundError("No pyproject.toml found in the current directory. It is required by 'use' to work.")
    existing_requirements: List[str] = []
    version_based_requirements: List[str] = []
    path_based_requirements: List[str] = []

    for requirement in requirements:
        spec = parse_dependency_specification(requirement)
        if spec.name in dependencies:
            existing_requirements.append(spec.name)

        if not spec.path and editable:
            raise typer.BadParameter("Editable mode is only supported for local packages.")

        old_value = extract_package_info_from_pyproject(spec.name, dependencies)
        version = spec.version or old_value.get("version", "latest")
        extras = old_value.get("extras", [])
        extras = list(itertools.chain.from_iterable([e.split() for e in extras]))

        if spec.path:
            extras_arg = " ".join(["-E " + e for e in extras])
            path_based_requirements.append(requirement + " " + extras_arg)
        else:
            if not "pypi_source" in CONFIG:
                raise typer.BadParameter(
                    "You must set the pypi_source in the config file before you can use this command"
                )

            extras_arg = f'[{",".join(extras)}]' if extras else ""
            version_based_requirements.append(f'"{spec.name}{extras_arg}@{version}"')

    if fix:
        sh(f"poetry remove {' '.join(existing_requirements)}")

    for requirement in path_based_requirements:
        sh(f"poetry add {requirement} {editable_arg}")

    if version_based_requirements:
        formatted_version_based_requirements = " ".join(version_based_requirements)
        sh(f"poetry add {formatted_version_based_requirements} --source={CONFIG['pypi_source']}")


def extract_package_info_from_pyproject(package_name: str, dependencies: "dict[str, str | dict]") -> "dict[str, Any]":
    if package_name in dependencies:
        old_value = dependencies[package_name]

        # oatmeal = "3.8.3"
        if not isinstance(old_value, dict):
            return {"version": old_value}
        # oatmeal = {version="3.8.3", extras=["server"], source="oatmeal_pypi"}
        elif "version" in old_value:
            return old_value
        # oatmeal = {path = "/path/to/local/oatmeal/package", extras = ["server"], develop = true}
        elif "path" in old_value:
            return old_value
        else:
            raise NotImplementedError(f"Unexpected dependency value for {package_name}: {dependencies[package_name]}")
    else:
        return {}
