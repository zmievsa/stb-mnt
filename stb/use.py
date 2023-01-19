from pathlib import Path
from typing import Any

import tomlkit as toml
import typer
from pysh import which

from stb.config import CONFIG

from .util import sh_with_log

PYENV_INSTALLED = which("pyenv")


def use_package(package_name: str, version_or_path: str) -> None:
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("No pyproject.toml found in the current directory. It is required by 'use' to work.")

    new_value_is_path = is_path(version_or_path)

    raw_old_pyproject = pyproject_path.read_text()
    pyproject = toml.loads(raw_old_pyproject)
    dependencies: dict[str, str | dict] = pyproject["tool"]["poetry"]["dependencies"]  # type: ignore
    old_value = extract_package_info_from_pyproject(package_name, dependencies)

    if new_value_is_path:
        new_path = Path(version_or_path).resolve()
        if "path" in old_value:
            old_value["path"] = str(new_path)
        else:
            old_value.pop("version", None)
            old_value.pop("source", None)
            extras = old_value.pop("extras", [])
            old_value.update(
                {
                    "path": str(new_path),
                    "develop": True,
                    "extras": extras,
                }
            )

    else:
        if "path" in old_value:
            old_value.pop("path", None)
            old_value.pop("develop", None)
            extras = old_value.pop("extras", [])
            old_value.update(
                remove_none(
                    {
                        "version": version_or_path,
                        "source": CONFIG.get("pypi_source"),
                        "extras": extras,
                    }
                )
            )
        else:
            old_value["version"] = version_or_path

    save_pyproject(pyproject_path, pyproject)
    try:
        if new_value_is_path:
            cmd = "poetry install"
        else:
            cmd = f"poetry update {package_name}"
        result = sh_with_log(cmd)
        if result.returncode != 0:
            typer.echo("Failed to update the package. Rolling back the changes.")
            pyproject_path.write_text(raw_old_pyproject)
    except BaseException:
        typer.echo("Failed to update the package. Rolling back the changes.")
        pyproject_path.write_text(raw_old_pyproject)
        raise


def save_pyproject(pyproject_path, pyproject):
    pyproject_path.write_text(toml.dumps(pyproject))


def remove_none(value: "dict[str, Any | None]") -> "dict[str, Any]":
    """This is only necessary to preserve ordering of the keys. See that source is always in the middle and extras is always at the end."""
    return {k: v for k, v in value.items() if v is not None}


def extract_package_info_from_pyproject(package_name: str, dependencies: "dict[str, str | dict]") -> "dict[str, Any]":
    if package_name in dependencies:
        old_value = dependencies[package_name]

        # oatmeal = "3.8.3"
        if not isinstance(old_value, dict):
            new_value = toml.inline_table()
            new_value.update(
                remove_none({"version": dependencies[package_name], "source": CONFIG.get("pypi_source"), "extras": []})
            )
            dependencies[package_name] = new_value
            # That's assuming that path cannot be inputted as a string.
            # I.e. oatmeal = ./hello/darkness/my/old/friend
            return new_value
        # oatmeal = {version="3.8.3", extras=["server"], source="oatmeal_pypi"}
        elif "version" in old_value:
            return old_value
        # oatmeal = {path = "/path/to/local/oatmeal/package", extras = ["server"], develop = true, source="oatmeal_pypi"}
        elif "path" in old_value:
            return old_value
        else:
            raise NotImplementedError(f"Unexpected dependency value for {package_name}: {dependencies[package_name]}")
    else:
        new_value = toml.inline_table()
        new_value.update(remove_none({"version": "", "source": CONFIG.get("pypi_source"), "extras": []}))
        dependencies[package_name] = new_value
        return new_value


def is_path(version_or_path: str) -> bool:
    # Dumb but works
    if "/" in version_or_path or version_or_path.startswith((".", "..", "~", "$HOME")):
        if not Path(version_or_path).is_dir():
            raise FileNotFoundError(f"Path {version_or_path} does not exist. Please provide a valid path.")
        return True
    else:
        return False
