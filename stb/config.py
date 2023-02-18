import functools
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, ParamSpec, Tuple, TypeVar

import tomlkit
import typer
from platformdirs import user_config_dir

from .utils.common import sh_with_log

set_app = typer.Typer(
    name="set",
    help="Set config values in the stb config file",
)
get_app = typer.Typer(
    name="get",
    help="Get config values from the stb config file",
)

config_app = typer.Typer(
    name="config",
    help="Set config values in the stb config file",
)

config_app.add_typer(set_app)
config_app.add_typer(get_app)
P = ParamSpec("P")
T = TypeVar("T")


@dataclass(init=False)
class Config:
    def __init__(self) -> None:
        self.config_dir = Path(user_config_dir("stb", "ovsyanka83"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "cfg.toml"
        self.doc = tomlkit.loads(self.config_file.read_text()) if self.config_file.exists() else tomlkit.document()

    def __setitem__(self, key: str, value: Any) -> None:
        self.doc.__setitem__(key, value)

    def __getitem__(self, key: str) -> str:
        return str(self.doc.__getitem__(key))

    def __contains__(self, key: str) -> bool:
        return self.doc.__contains__(key)

    def get(self, key: str, default: Any = None):
        return self.doc.get(key, default)

    def save(self, path: Optional[Path] = None) -> None:
        if path is None:
            path = self.config_file
        path.write_text(tomlkit.dumps(self.doc))

    def requires(self, first_key: str, *keys: str):
        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            @functools.wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                self.check_keys_have_been_set(first_key, *keys)
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def check_keys_have_been_set(self, *keys: str) -> None:
        missing_keys = [key for key in keys if key not in self]
        if missing_keys:
            raise typer.BadParameter(
                "\n".join(
                    f"You must set the '{key}' parameter in the config file before you can use this command."
                    for key in missing_keys
                )
                + "\n\nSee `stb config set --help for more information`"
            )


CONFIG = Config()

RE_GIT_URL = re.compile(r"^git@[a-zA-Z0-9._-]+$")


def make_command(
    entry_name: str,
    help: str = "",
    regex: Optional[re.Pattern] = None,
    set_callback: Callable[[str], None] = lambda _: None,
) -> Tuple[Callable[[], Any], Callable[[Any], None]]:
    def get_command():
        if entry_name not in CONFIG:
            raise typer.BadParameter(f"{entry_name} is not set yet")
        return typer.echo(CONFIG[entry_name])

    def set_command(value: str = typer.Argument(..., help=help, show_default=False)) -> None:
        set_callback(value)
        if regex is not None and regex.match(value) is None:
            raise typer.BadParameter(f"{value} does not match the expected format")
        CONFIG[entry_name] = value
        CONFIG.save()

    get_command.__doc__ = f"Get the {help}"
    set_command.__doc__ = f"Set the {help}"

    return get_app.command(entry_name)(get_command), set_app.command(entry_name)(set_command)


get_git_url, set_git_url = make_command(
    "git_url", "git url for setting up local services in the following format: 'git@github.com'", RE_GIT_URL
)

get_pypi_source, set_pypi_source = make_command(
    "pypi_source", "internal pypi source name that is used for downloading internal packages"
)

get_pypi_registry_id, set_pypi_registry_id = make_command(
    "pypi_registry_id",
    "id of the package whose registry is used for downloading internal packages",
    re.compile(r"^\d+$"),
)


@get_app.command("gitlab_api_token")
def get_gitlab_api_token() -> None:
    """Get the gitlab api token for setting up local services"""
    if "gitlab_api_token" not in CONFIG or "gitlab_api_token_name" not in CONFIG:
        raise typer.BadParameter("gitlab_api_token is not set yet")

    typer.echo(f"{CONFIG['gitlab_api_token_name']} {CONFIG['gitlab_api_token']}")


@set_app.command("gitlab_api_token")
def set_gitlab_api_token(
    token_name: str = typer.Argument(..., help="token name"),
    token: str = typer.Argument(..., help="token itself"),
) -> None:
    """Set the gitlab api token for setting up local services"""
    CONFIG["gitlab_api_token_name"] = token_name
    CONFIG["gitlab_api_token"] = token
    CONFIG.save()


@CONFIG.requires("pypi_source", "pypi_registry_id", "gitlab_api_token", "git_url")
@config_app.command()
def poetry() -> None:
    """Setup poetry config based on exiting stb config"""

    api_url = get_gitlab_api_url()

    sh_with_log(
        f"poetry config repositories.{CONFIG['pypi_source']} {api_url}/projects/{CONFIG['pypi_registry_id']}/packages/pypi"
    )
    sh_with_log(
        f"poetry config http-basic.{CONFIG['pypi_source']} {CONFIG['gitlab_api_token_name']} {CONFIG['gitlab_api_token']}"
    )


def get_gitlab_api_url() -> str:
    git_host = CONFIG["git_url"].split("@")[1]
    return f"https://{git_host}/api/v4"


if "git_url" in CONFIG and ":" in CONFIG["git_url"]:
    CONFIG["git_url"] = CONFIG["git_url"].split(":")[0]
    CONFIG.save()
