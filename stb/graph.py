import contextlib
import datetime
import io
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import List

import gitlab
import tomli
import typer
from pysh import which
from rich.console import Console
from rich.progress import Progress, track

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
console = Console(stderr=True)

REPLACEMENTS = {
    "xchange-rates": "exchange-rates",
    "mailbox": "mailboxes",
}

GRAPHVIZ_INPUT = """
digraph prof {{
	ratio = fill;
	node [style=filled];
    beautify=true;
    {domains}
    {dependencies}
    subgraph cluster_legend {{
        label = "Legend";
        style = "rounded";
        node [style=solid, shape=plaintext, width=0];
        
        FullServiceNode [label="Full Use of Service"];
        FullServiceNode -> FullServiceLegend [color=blue, style=solid];
        FullServiceLegend [label="", shape=none];

        DoesntDoHTTPCallsNode [label="HTTP-less use of Service"];
        DoesntDoHTTPCallsNode -> DoesntDoHTTPCallsLegend [color=DarkOrange, style=dashed, arrowhead=tee];
        DoesntDoHTTPCallsLegend [label="", shape=none];
        
        {{rank=same; FullServiceNode; DoesntDoHTTPCallsNode;}}
    }}
}}
"""


today = datetime.datetime.today().strftime("%y%m%d_%H%M%S")

if which("dot"):

    @app.command()
    def graphviz(
        services: List[str],
        ignore_packages: list[str] = ignore_packages,
        display_domains: bool = False,
        connector_usage_source: Path = typer.Option(default=None, dir_okay=True, file_okay=False, exists=True),
    ):
        """Graphs the dependencies of microservices using graphviz"""
        with contextlib.redirect_stdout(io.StringIO()):
            dependencies = json_(services, ignore_packages)

        dependencies = {
            project_name.replace("-", "_"): {
                "id": project["id"],
                "name_with_namespace": project["name_with_namespace"],
                "name": project["name"],
                "dependencies": [dep.replace("-", "_") for dep in project["dependencies"]],
            }
            for project_name, project in dependencies.items()
        }
        if connector_usage_source is not None:
            _find_connector_usages(dependencies, connector_usage_source)
        domains = defaultdict(list)
        for project_name, project in dependencies.items():
            domains[project["name_with_namespace"].split(" / ")[-2]].append(project_name)
        graphviz_dependency_definitions = "\n".join(
            [
                f"{k} -> {dep} {'[color=blue, style=solid]' if dep in v.get('dependencies_with_connectors', ()) or 'dependencies_with_connectors' not in v else '[color=red, style=dashed, arrowhead=tee]'};"
                for k, v in dependencies.items()
                for dep in v["dependencies"]
            ]
        )
        newline = "\n"
        if display_domains:
            graphviz_domain_definitions = "\n".join(
                [
                    f"""
    subgraph cluster_{domain_name} {{
    style=filled;
    color=lightgrey;
    node [style=filled,color=white];
    {newline.join([dep + ";" for dep in domain])}
    label = "{domain_name}";
        }}"""
                    for domain_name, domain in domains.items()
                ]
            )
        else:
            graphviz_domain_definitions = ""
        graphviz_input = GRAPHVIZ_INPUT.format(
            domains=graphviz_domain_definitions, dependencies=graphviz_dependency_definitions
        )

        subprocess.run(
            f"dot -Tpng",
            shell=True,
            text=True,
            input=graphviz_input,
        )

    def _find_connector_usages(dependencies: dict, connector_usage_source: Path):
        for _, project_info in dependencies.items():
            project = connector_usage_source / project_info["name"]

            project_info["dependencies_with_connectors"] = []
            for dep in project_info["dependencies"]:
                found = subprocess.run(
                    ["rg", f"from.+{dep}.+connectors.+import"],
                    cwd=project,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if found.returncode == 0:
                    project_info["dependencies_with_connectors"].append(dep)


@CONFIG.requires("gitlab_api_token", "git_url", "pypi_registry_id")
@app.command(name="json")
def json_(
    services: List[str],
    ignore_packages: list[str] = ignore_packages,
):
    gl = gitlab.Gitlab(url=get_gitlab_api_url().removesuffix("/api/v4"), private_token=CONFIG["gitlab_api_token"])

    with Progress(console=console) as progress:
        progress.add_task("[red]Loading all projects...", total=None)
        projects = get_projects(gl, services)
    dep_mapping = {}
    project_with_registry = gl.projects.get(CONFIG["pypi_registry_id"])
    packages = project_with_registry.packages.list(all=True)
    packages_in_registry = {package.name for package in packages}

    for project, pyproject in track(
        get_pyproject_tomls(projects), description="Getting pyproject files", total=len(projects), console=console
    ):
        service_name = get_service_name(pyproject)
        if not service_name:
            continue

        direct_dependencies = get_direct_dependencies(pyproject)
        direct_registry_dependencies = [
            dep for dep in direct_dependencies if dep in packages_in_registry and not dep in ignore_packages
        ]
        if service_name in direct_registry_dependencies:
            direct_registry_dependencies.remove(service_name)
        dep_mapping[service_name] = {
            "id": project.id,
            "name": project.name,
            "name_with_namespace": project.name_with_namespace,
            "dependencies": direct_registry_dependencies,
        }
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
                yield project, tomli.loads(project.repository_raw_blob(possible_pyproject_ids[0]).decode("utf-8"))


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
