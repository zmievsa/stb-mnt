from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests
import tomli as toml
import typer
from pysh import sh, which

from . import update
from .config import CONFIG, get_gitlab_api_url
from .utils.common import cd_with_log, clean_python_version, parse_python_version, sh_with_log

PYENV_INSTALLED = which("pyenv")


def setup_services(services: List[str], skip_existing: bool) -> None:
    if not "git_url" in CONFIG:
        raise typer.BadParameter("You must set the git_url in the config file before you can use this command")
    if not PYENV_INSTALLED:
        typer.echo("Failed to locate pyenv. Will use the system python version(s) instead")
    installable_pyenv_versions = [
        clean_python_version(" \t~^*") for v in sh("pyenv install --list", capture=True).stdout.split("\n") if v.strip()
    ]

    repositories_to_clone = get_repositories_to_clone(services, skip_existing)

    for name, link in repositories_to_clone:
        setup_service(name, link, installable_pyenv_versions)


def setup_service(repo_name: str, git_link: str, installable_pyenv_versions: List[str]):
    typer.echo(f"Setting up {repo_name}")
    success = clone_repo(git_link)

    if success:
        with cd_with_log(repo_name):
            if Path("pyproject.toml").exists():
                python_version = get_python_version(Path("pyproject.toml"))
                if python_version:
                    if PYENV_INSTALLED:
                        setup_pyenv_locally(python_version, installable_pyenv_versions)
                    else:
                        sh_with_log(f"poetry env use {python_version}")
                sh_with_log("poetry install --all-extras")
            update.env([Path()])
            update.ports([Path()])
    else:
        raise FileNotFoundError(f"Failed to enter the directory '{repo_name}'")


def clone_repo(git_link: str) -> bool:
    return bool(sh_with_log(f"git clone {git_link}"))


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


def get_repositories_to_clone(repo_names: List[str], skip_existing: bool) -> List[Tuple[str, str]]:
    """Expands gitlab repo names to include all repos if the name is a group or a namespace"""
    expanded_repo_names = []

    for name in repo_names:
        # Remove all whitespace in case the user accidentally added some
        name = "".join(name.split())

        if name.count("/") == 2:
            expanded_repo_names.append((name.split("/")[-1], f'{CONFIG["git_url"]}:{name}.git'))
        else:
            with requests.Session() as session:
                session.headers = {"PRIVATE-TOKEN": CONFIG["gitlab_api_token"]}
                project_jsons = _paginated_get(f"{get_gitlab_api_url()}/projects", session)

                projects = [
                    (p["path"], p["ssh_url_to_repo"])
                    for p in project_jsons
                    if p["path_with_namespace"].startswith(name)
                ]
                if not projects:
                    raise ValueError(
                        f"Failed to find any projects that start with '{name}'. Maybe you need to add a group/namespace or to fix a typo?"
                    )
                non_repeating_projects = []
                for project in projects:
                    if Path(project[0]).exists():
                        yes = skip_existing or typer.confirm(
                            f"Found project {project[0]} but a folder with the same name already exists. You should use `stb update` for it instead. Would you like to skip it?",
                        )
                        if not yes:
                            raise typer.Exit(1)
                    else:
                        non_repeating_projects.append(project)
                expanded_repo_names.extend(non_repeating_projects)

    return expanded_repo_names


def _paginated_get(url: str, session: requests.Session) -> List[Dict[str, Any]]:
    """Gets a paginated response from the gitlab api"""
    response = session.get(url, params={"per_page": 20})
    response.raise_for_status()

    total_pages = int(response.headers["X-Total-Pages"])

    projects = response.json()

    for _ in range(1, total_pages):
        response = session.get(response.links["next"]["url"])
        response.raise_for_status()
        projects.extend(response.json())

    return projects
