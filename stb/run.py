from typing import Set

import typer

from stb.utils.common import cd_with_log, sh_with_log

app = typer.Typer(
    name="run",
    help="Runs the select services together at the same time",
)


def run_services(services: Set[str]) -> None:
    typer.echo("Checking out services...")

    for service in services:
        with cd_with_log(service):
            # TODO: Sounds like this needs to reuse `stb update package`
            sh_with_log("git stash")
            sh_with_log("git checkout master")
            sh_with_log("git pull")
            sh_with_log("stb db reset")
            sh_with_log("poetry install --all-extras")

    concurrently_query = " ".join([f'"cd {s} && (make run || poetry run python3 run.py)"' for s in services])

    sh_with_log("concurrently " + concurrently_query)
