import contextlib
import datetime
import io
import json
import subprocess
from typing import List

import gitlab
import tomli
import typer
from pysh import which

from .config import CONFIG, get_gitlab_api_url

app = typer.Typer(
    name="graph",
    help="graphs the dependencies of microservices using various backends",
)
ignore_packages = typer.Option(
    None,
    "-i",
    help="The packages to omit from output even if they are in the registry.",
)

REPLACEMENTS = {
    "xchange-rates": "exchange-rates",
    "mailbox": "mailboxes",
}

GRAPHVIZ_INPUT = """
digraph prof {{
	ratio = fill;
	node [style=filled];
    {}
}}
"""

today = datetime.datetime.today().strftime("%y%m%d_%H%M%S")

if which("dot"):

    @app.command()
    def graphviz(
        services: List[str],
        ignore_packages: list[str] = ignore_packages,
    ):
        """Graphs the dependencies of microservices using graphviz"""
        with contextlib.redirect_stdout(io.StringIO()):
            deps = json_(services, ignore_packages)
        stuff = "\n".join([f"{k.replace('-', '_')} -> {dep.replace('-', '_')}" for k, v in deps.items() for dep in v])
        subprocess.run(f"dot -Tsvg", shell=True, text=True, input=GRAPHVIZ_INPUT.format(stuff))


@CONFIG.requires("gitlab_api_token", "git_url", "pypi_registry_id")
@app.command(name="json")
def json_(
    services: List[str],
    ignore_packages: list[str] = ignore_packages,
):
    gl = gitlab.Gitlab(url=get_gitlab_api_url().removesuffix("/api/v4"), private_token=CONFIG["gitlab_api_token"])
    projects = get_projects(gl, services)
    dep_mapping = {}
    project_with_registry = gl.projects.get(CONFIG["pypi_registry_id"])
    packages = project_with_registry.packages.list(all=True)
    package_names_in_registry = {package.name for package in packages}

    for pyproject in get_pyproject_tomls(projects):
        service_name = get_service_name(pyproject)
        if not service_name:
            continue

        direct_dependencies = get_direct_dependencies(pyproject)
        direct_registry_dependencies = [
            dep for dep in direct_dependencies if dep in package_names_in_registry and not dep in ignore_packages
        ]
        if service_name in direct_registry_dependencies:
            direct_registry_dependencies.remove(service_name)
        dep_mapping[service_name] = direct_registry_dependencies
    dep_mapping = {k: v for k, v in dep_mapping.items() if dep_is_in_mapping(dep_mapping, k)}
    typer.echo(json.dumps(dep_mapping, indent=4, ensure_ascii=False))
    return dep_mapping


def dep_is_in_mapping(dep_mapping: dict[str, list[str]], searched_service: str):
    if dep_mapping.get(searched_service):
        return True
    for dependencies in dep_mapping.values():
        for dependency in dependencies:
            if dependency == searched_service:
                return True
    return False


def get_service_name(pyproject: dict) -> str:
    service_name = "-".join(pyproject["tool"]["poetry"]["name"].replace("_", "-").split("-")[:-1]).strip()
    if service_name in REPLACEMENTS:
        return REPLACEMENTS[service_name]
    return service_name


def get_direct_dependencies(pyproject):
    return [dep.replace("_", "-") for dep in pyproject["tool"]["poetry"]["dependencies"].keys()]


def get_pyproject_tomls(projects: list):
    for project in projects:
        with contextlib.suppress(gitlab.GitlabGetError):
            possible_pyproject_ids = [
                i["id"] for i in project.repository_tree(get_all=True) if i["path"] == "pyproject.toml"
            ]
            if possible_pyproject_ids:
                yield tomli.loads(project.repository_raw_blob(possible_pyproject_ids[0]).decode("utf-8"))


def get_projects(gl: gitlab.Gitlab, repo_names: List[str]) -> list:
    all_projects = gl.projects.list(get_all=True)

    calculated_projects = []
    repo_names = ["".join(name.split()) for name in repo_names]
    for name in repo_names:
        if name.count("/") == 2:
            calculated_projects.append(name.split("/")[-1])

    for name in repo_names:
        # Remove all whitespace in case the user accidentally added some
        projects = [p for p in all_projects if p.path_with_namespace.startswith(name)]
        if not projects:
            raise ValueError(
                f"Failed to find any projects that start with '{name}'. Maybe you need to add a group/namespace or to fix a typo?"
            )
        calculated_projects.extend(projects)

    return calculated_projects
