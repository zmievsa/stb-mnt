import contextlib
import functools
import shutil
from pathlib import Path

import keyring
import keyring.errors
import pytest

TESTING_KEYRING_SERVICE_NAME = "STB_PYTEST_SERVICE"
TESTING_KEYRING_USERNAME = "STB_PYTEST_USERNAME"
TESTING_KEYRING_PASSWORD = "STB_PYTEST_PASSWORD"


@pytest.fixture(scope="session")
def temporary_directory():
    # We don't use the tmp dir in case it's outside of our permissions or if we wish to see the testing process
    # and verify cleanup
    tmp_dir = Path("tests_tmp_dir")
    tmp_dir.mkdir()
    yield tmp_dir
    shutil.rmtree(tmp_dir)


@pytest.fixture
def dummy_microservice(request: pytest.FixtureRequest, temporary_directory: Path):
    microservice_dir: Path = temporary_directory / (request.function.__name__ + "_microservice")
    microservice_dir.mkdir()
    microservice_dir / ""


@pytest.fixture
def keyring_app():
    with contextlib.suppress(keyring.errors.PasswordDeleteError):
        keyring.delete_password(TESTING_KEYRING_SERVICE_NAME, TESTING_KEYRING_USERNAME)
    yield keyring.get_keyring()
    with contextlib.suppress(keyring.errors.PasswordDeleteError):
        keyring.delete_password(TESTING_KEYRING_SERVICE_NAME, TESTING_KEYRING_USERNAME)
