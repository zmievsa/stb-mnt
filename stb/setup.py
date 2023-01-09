from pathlib import Path
from typing import Dict, List, Optional, Sequence

import tomlkit as toml
import typer
from pysh import sh, which

from . import update
from .config import CONFIG
from .util import cd_with_log, clean_python_version, parse_python_version, sh_with_log

PYENV_INSTALLED = which("pyenv")


def setup_services(services: List[str], no_clone: bool) -> None:
    if not "git_url" in CONFIG and not no_clone:
        raise typer.BadParameter("You must set the git_url in the config file before you can use this command")
    if not PYENV_INSTALLED:
        typer.echo("Failed to locate pyenv. Will use the system python version(s) instead")
    installable_pyenv_versions = [
        clean_python_version(" \t~^*") for v in sh("pyenv install --list", capture=True).stdout.split("\n") if v.strip()
    ]

    repositories_to_clone = get_repositories_to_clone(services)

    for name, link in repositories_to_clone.items():
        setup_service(name, link, installable_pyenv_versions, no_clone)


def setup_service(service_name: str, git_link: str, installable_pyenv_versions: List[str], no_clone: bool):
    typer.echo(f"Setting up {service_name}")

    repo_name = service_name.rsplit("/")[-1]
    if no_clone:
        success = Path(repo_name).exists()
    else:
        success = clone_repo(repo_name, git_link)

    if success:
        with cd_with_log(repo_name):
            sh_with_log("git submodule update --init --recursive", "", "")
            if Path("pyproject.toml").exists():
                python_version = get_python_version(Path("pyproject.toml"))
                if python_version:
                    if PYENV_INSTALLED:
                        setup_pyenv_locally(python_version, installable_pyenv_versions)
                    else:
                        sh_with_log(f"poetry env use {python_version}")
                sh_with_log("poetry install")
            update.env([Path()])
            update.ports([Path()])
    else:
        raise FileNotFoundError(f"Failed to enter the directory '{repo_name}'")


def clone_repo(repo_name: str, git_link: str) -> bool:
    if not Path(repo_name, ".git").exists():
        return bool(sh_with_log(f"git clone {git_link}"))
    else:
        typer.echo(f"{repo_name} has already been cloned. Either rename the existing one or use 'stb update' instead")
        return False


def get_python_version(pyproject_path: Path) -> Optional[str]:
    pyproject = toml.loads(pyproject_path.read_text())
    raw_python_version: str = pyproject["tool"]["poetry"]["dependencies"]["python"]  # type: ignore
    version_info = parse_python_version(raw_python_version)
    if version_info:
        return f"{version_info[0]}.{version_info[1]}"
    else:
        typer.echo("Failed to read python version from pyproject.toml. It's either invalid or too complex for me.")


def setup_pyenv_locally(python_version: str, installable_pyenv_versions: List[str]):
    raw_installed_pyenv_venvs = sh("pyenv versions", capture=True).stdout.split("\n")
    installed_pyenv_venvs = [clean_python_version(v) for v in raw_installed_pyenv_venvs]
    installable_python_version = get_usable_pyenv_version(
        python_version,
        installed_pyenv_venvs,
    ) or get_usable_pyenv_version(
        python_version,
        installable_pyenv_versions,
    )

    if installable_python_version is not None:
        if " " in installable_python_version:
            installable_python_version = installable_python_version.split(" ")[0]
        sh_with_log(f"pyenv local {installable_python_version}")
        sh_with_log(f"poetry env use {installable_python_version}")


def get_usable_pyenv_version(current: str, available: Sequence[str], install: bool = False) -> Optional[str]:
    for version in reversed(available):
        version = version.strip("* \t\n")
        if version.startswith(current):
            if install:
                sh(f"pyenv install {version}")
            return version


def get_repositories_to_clone(repo_names: List[str]) -> Dict[str, str]:
    return {n: f"{CONFIG['git_url']}/{n}.git" for n in repo_names}
