#!/usr/bin/env python3

import enum
import multiprocessing
from contextlib import suppress
from pathlib import Path
from typing import List, cast

import rich
import typer
from pysh import env

from .utils.common import SERVICE_PATHS_ARG, Service, add_default_service_path, cd_with_log, get_service, sh_with_log


def old_parallel_flag_deprecation_callback(value: bool):
    if value:
        rich.print(
            "[bold red]The flag '-p' for 'stb db' is deprecated and will be removed in the future. Its behavior is now the default[/bold red]\n",
        )


app = typer.Typer(
    name="migrator",
    help="creates/upgrades/drops dbs for microservices",
)
REQUIRED_DOTENV_KEYS = "POSTGRES_PASSWORD", "POSTGRES_PORT", "POSTGRES_USER"
OLD_PARALLEL_MIGRATIONS_ARG = typer.Option(
    False,
    "-p",
    "--parallel",
    help="Deprecated. This behavior is now the default. If you want to disable it, use --no-parallel.",
    callback=old_parallel_flag_deprecation_callback,
)
NO_PARALLEL_MIGRATIONS_ARG = typer.Option(False, "-P", "--no-parallel", help="Do not run migrations in parallel")
FORCE_DROP_ARG = typer.Option(
    False,
    "-f",
    "--force",
    help="Force the drop of the databases. Helpful if other clients are connected to any of the databases. Use with caution.",
)


class Choices(str, enum.Enum):
    upgrade = "upgrade"
    create = "create"
    drop = "drop"


@app.command()
@add_default_service_path
def upgrade(
    service_paths: List[Path] = SERVICE_PATHS_ARG,
    no_parallel_migrations: bool = NO_PARALLEL_MIGRATIONS_ARG,
    old_parallel_migrations: bool = OLD_PARALLEL_MIGRATIONS_ARG,
):
    """Upgrade database migrations"""
    run_on_several_services(service_paths, Choices.upgrade, not no_parallel_migrations)


@app.command()
@add_default_service_path
def create(
    service_paths: List[Path] = SERVICE_PATHS_ARG,
    no_parallel_migrations: bool = NO_PARALLEL_MIGRATIONS_ARG,
    old_parallel_migrations: bool = OLD_PARALLEL_MIGRATIONS_ARG,
):
    """Create databases and upgrade their migrations"""
    run_on_several_services(service_paths, Choices.create, not no_parallel_migrations)


@app.command()
@add_default_service_path
def drop(
    service_paths: List[Path] = SERVICE_PATHS_ARG,
    force: bool = FORCE_DROP_ARG,
):
    """Drop databases"""
    run_on_several_services(service_paths, Choices.drop, force)


@app.command()
@add_default_service_path
def reset(
    service_paths: List[Path] = SERVICE_PATHS_ARG,
    no_parallel_migrations: bool = NO_PARALLEL_MIGRATIONS_ARG,
    force: bool = FORCE_DROP_ARG,
    old_parallel_migrations: bool = OLD_PARALLEL_MIGRATIONS_ARG,
):
    """Drop databases, recreate them, and then upgrade their migrations"""
    for service in service_paths:
        with suppress(Exception):
            run_on_single_service(service, Choices.drop, not no_parallel_migrations, force)
            run_on_single_service(service, Choices.create, not no_parallel_migrations)


def run_on_several_services(
    service_paths: List[Path],
    choice: Choices,
    parallel_migrations: bool = False,
    force_drop: bool = False,
):
    for service in service_paths:
        with suppress(Exception):
            run_on_single_service(service, choice, parallel_migrations, force_drop)


def run_on_single_service(
    service_path: Path,
    command: Choices,
    parallel_migrations: bool = False,
    force_drop: bool = False,
) -> None:
    service = get_service(service_path)

    for field in REQUIRED_DOTENV_KEYS:
        if not service.dotenv.get(field):
            err = f"{field} field is required for the correct functioning of stb db but it was not filled out in {service.dotenv_path}"
            typer.echo(err, err=True)
            raise LookupError(err)

    aerich_apps = find_aerich_apps(service)
    postgres_dbs = {v for k, v in service.dotenv.items() if k.startswith("POSTGRES_DB")}
    postgres_user = service.dotenv["POSTGRES_USER"]
    postgres_password = cast(str, service.dotenv["POSTGRES_PASSWORD"])
    postgres_port = service.dotenv["POSTGRES_PORT"]

    with cd_with_log(service.dir), env(PGPASSWORD=postgres_password):
        for db in aerich_apps | postgres_dbs:
            if command == Choices.create:
                sh_with_log(f"createdb -h localhost -p {postgres_port} -U {postgres_user} {db}", "", "")
            elif command == Choices.drop:
                sh_with_log(
                    f"dropdb {'-f' if force_drop else ''} -h localhost -p {postgres_port} -U {postgres_user} {db}",
                    "",
                    "",
                )

        if command in {Choices.create, Choices.upgrade}:
            if "aerich" in aerich_apps:
                aerich_apps.remove("aerich")
            sh_with_log("poetry run aerich upgrade")
            commands_to_run = [f"poetry run aerich --app {db} upgrade" for db in aerich_apps]

            if parallel_migrations:
                with multiprocessing.Pool() as pool:
                    pool.map(sh_with_log, commands_to_run)
            else:
                for cmd in commands_to_run:
                    sh_with_log(cmd)


def find_aerich_apps(service: Service) -> "set[str]":
    migrations_dir = service.dir / "migrations"
    if migrations_dir.is_dir():
        return {d.name for d in migrations_dir.iterdir() if d.is_dir()}
    else:
        return set()


if __name__ == "__main__":
    app()
