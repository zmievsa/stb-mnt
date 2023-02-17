from typing import List

import typer
from pysh import which

from stb import config, db, graph, run, update, use
from stb.__version__ import __version__

app = typer.Typer(
    name="stb",
    add_completion=False,
    help="Stanislav's Toolbox (stb) helps you manage your local microservices. Specifically, it can set them up for you, create/delete/migrate databases, manage service ports and .env files, and much more",
)

app.add_typer(db.app, name="db")
app.add_typer(update.app)
app.add_typer(config.config_app)
app.add_typer(graph.app)


def version_callback(value: bool):
    if value:
        typer.echo(f"Stanislav's Toolbox {__version__}")
        raise typer.Exit()


@app.command(name="use")
def use_(
    requirements: List[str] = typer.Argument(
        ...,
        help="Package versions to use. For example, `my_package` or `my_package==3.1.4` or `~/path/to/my_package`",
    ),
    editable: bool = typer.Option(
        False,
        help="Install the package(s) in editable mode. Useful when you want to develop the package and use it in the current project at the same time",
    ),
    fix: bool = typer.Option(
        False,
        help="Fix the broken version of the package in the current project as well. Useful when dependency resolution doesn't work properly",
    ),
) -> None:
    """Switches the version of a company package in the current project. For example, `stb use my_package 0.1.0` or `stb use my_package ~/package`"""
    return use.use_packages(requirements, editable, fix)


def run_(
    services: List[str] = typer.Argument(
        ...,
        help="The select services to checkout and run together at the same time",
    ),
) -> None:
    return run.run_services(set(services))


if which("concurrently"):
    run_ = app.command(name="run")(run_)

try:
    from stb import setup

    @app.command(name="setup")
    def setup_(
        services: List[str] = typer.Argument(
            ...,
            help="Names of services to setup. For example, use 'my_company/backend/oatmeal' to setup oatmeal service in the backend namespace",
        ),
        skip_existing: bool = typer.Option(True, help="Automatically skip existing services when setting up"),
    ) -> None:
        """Does the initial localhost setup of microservices. Downloads, configures .env, inits submodules, installs the correct pyenv environment, creates the correct poetry environment, and installs dependencies"""
        return setup.setup_services(services, skip_existing)

except ImportError:
    pass


@app.callback()
def main(
    version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True),
):
    ...


if __name__ == "__main__":
    app()
