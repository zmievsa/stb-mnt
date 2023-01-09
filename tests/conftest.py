import shutil
from pathlib import Path

import pytest


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
