import functools
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, TypeVar, Union

import dotenv
import typer
import yaml
from pysh import cd, sh
from typing_extensions import Concatenate, ParamSpec, TypeAlias

SERVICE_PATHS_ARG = typer.Argument(
    None,
    help="Paths to service directories or root directories that contain multiple services. Current working directory by default",
    dir_okay=True,
    file_okay=False,
    exists=True,
    show_default=False,
)
VERBOSE_ARG = typer.Option(False, "-v", "--verbose", help="Print debugging output")
DOTENV_SECTION_SEPARATOR = "\n# =======================================\n"

ENV_VARS = {
    # Postgres
    "POSTGRES_HOST": '"localhost"',
    "POSTGRES_PORT": 5432,
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
    # Rabbit
    "RABBITMQ_HOST": '"localhost"',
    "RABBITMQ_PORT": 5672,
    "RABBITMQ_LOGIN": "guest",
    "RABBITMQ_PASSWORD": "guest",
    "RABBITMQ_VHOST": '"/"',
    "RABBITMQ_SSL": '"false"',
    # Etc
    "DEBUG": True,
    "CURRENT_ENV": "dev",
    "LOG_LEVEL": "INFO",
}

P = ParamSpec("P")
R = TypeVar("R")
PATHS: TypeAlias = Union[List[Path], None]

RE_PYTHON_VERSION = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<bugfix>\d))?.*")


def parse_python_version(raw_python_version: str) -> Optional[Tuple[int, int]]:
    python_version = clean_python_version(raw_python_version)
    match = RE_PYTHON_VERSION.match(python_version)
    if match:
        return int(match["major"]), int(match["minor"])


def clean_python_version(version: str) -> str:
    return version.strip(" \n\t~^*><=")


def add_default_service_path(function: Callable[Concatenate[List[Path], P], R]) -> Callable[Concatenate[PATHS, P], R]:
    @functools.wraps(function)
    def wrapper(service_paths: PATHS, *args: P.args, **kwargs: P.kwargs) -> R:
        if not service_paths:
            service_paths = [Path.cwd()]
        return function(service_paths, *args, **kwargs)

    return wrapper


@dataclass(frozen=True)
class Service:
    dir: Path
    yaml_config: Union[Dict[str, Any], None]
    dotenv_path: Path
    dotenv: Dict[str, Union[str, None]]
    dotenv_example: Dict[str, Union[str, None]]
    dotenv_example_original_source: str


def get_service(dir: Path):
    dir = dir.absolute()
    return Service(
        dir,
        yaml.safe_load(safely_read_text(dir / ".helm/values.yaml")),
        dir / "settings/.env",
        dotenv.dotenv_values(dir / "settings/.env"),
        dotenv.dotenv_values(dir / "settings/.env.example"),
        safely_read_text(dir / "settings/.env.example"),
    )


def gather_services(paths: List[Path]) -> Dict[str, Service]:
    service_dirs: List[Path] = []
    for path in paths:
        path = path.resolve()

        if is_service_dir(path):
            service_dirs.append(path)
        else:
            service_dirs.extend(unpack_root_path(path))

    return {dir.name: get_service(dir) for dir in service_dirs}


def safely_read_text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def is_service_dir(path: Path) -> bool:
    return path.is_dir() and (path / "settings/.env.example").exists()


def unpack_root_path(path: Path) -> List[Path]:
    return [p for p in path.iterdir() if is_service_dir(p)]


def save_dotenv_file(service: Service) -> None:
    """I save the dotenv file while preserving the comments and the order of entries"""
    new_lines: List[str] = []
    dotenv_items = service.dotenv.copy()
    for line in service.dotenv_example_original_source.splitlines():
        line = line.strip()
        if not line:
            new_lines.append("")
        elif line.startswith("#"):
            new_lines.append(line)
        elif "=" in line:
            key, _ = line.split("=", 1)
            key = key.strip()
            if key in dotenv_items:
                new_lines.append(f"{key}={dotenv_items.pop(key) or ''}")

    new_lines.append(DOTENV_SECTION_SEPARATOR + "# Env vars not present in .env.example" + DOTENV_SECTION_SEPARATOR)
    for key, value in dotenv_items.items():
        new_lines.append(f"{key}={value or ''}")

    service.dotenv_path.write_text("\n".join(new_lines))


def sh_with_log(cmd: str, prefix: str = "\n", suffix: str = "\n", capture: bool = False):
    typer.echo(f"{prefix}>>> {cmd}")
    res = sh(cmd, capture=capture)
    typer.echo(f"{suffix}")
    return res


@contextmanager
def cd_with_log(directory: "Path | str", prefix: str = "") -> Iterator[Path]:
    directory = Path(directory)
    if Path.cwd() == directory.resolve():
        yield directory
        return

    typer.echo(f"{prefix}>>> cd {directory}")
    with cd(directory) as path:
        yield path
    typer.echo(f"{prefix}>>> cd -")
