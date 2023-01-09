import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import tomlkit
import typer
from platformdirs import user_config_dir

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


@dataclass(init=False)
class Config:
    def __init__(self) -> None:
        self.config_dir = Path(user_config_dir("stb", "ovsyanka83"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "cfg.toml"
        self.doc = tomlkit.loads(self.config_file.read_text()) if self.config_file.exists() else tomlkit.document()

    def __setitem__(self, key: str, value: Any) -> None:
        self.doc.__setitem__(key, value)

    def __getitem__(self, key: str):
        return self.doc.__getitem__(key)

    def __contains__(self, key: str) -> bool:
        return self.doc.__contains__(key)

    def get(self, key: str, default: Any = None):
        return self.doc.get(key, default)

    def save(self, path: Optional[Path] = None) -> None:
        if path is None:
            path = self.config_file
        path.write_text(tomlkit.dumps(self.doc))


CONFIG = Config()

RE_GIT_URL = re.compile(r"^git@[a-zA-Z0-9._-]+:[a-zA-Z0-9._-]+$")


def make_command(
    entry_name: str,
    help: str = "",
    regex: Optional[re.Pattern] = None,
) -> Tuple[Callable[[], Any], Callable[[Any], None]]:
    def get_command():
        if entry_name not in CONFIG:
            raise typer.BadParameter(f"{entry_name} is not set yet")
        return typer.echo(CONFIG[entry_name])

    def set_command(value=typer.Argument(..., help=help, show_default=False)) -> None:
        if regex is not None and regex.match(value) is None:
            raise typer.BadParameter(f"{value} does not match the expected format")
        CONFIG[entry_name] = value
        CONFIG.save()

    get_command.__doc__ = f"Get the {help}"
    set_command.__doc__ = f"Set the {help}"

    return get_app.command(entry_name)(get_command), set_app.command(entry_name)(set_command)


get_git_url, set_git_url = make_command(
    "git_url", "git url for setting up local services in the following format: 'git@github.com:User'", RE_GIT_URL
)

get_pypi_source, set_pypi_source = make_command(
    "pypi_source", "internal pypi source name that is used for downloading internal packages"
)
