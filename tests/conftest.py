from contextlib import contextmanager
import logging
import sys
from pathlib import Path
import tempfile

import pytest

from tests.data_generation import PairedReadSampleTestData, RunFolder

# Make sure the workspace package directory is first on sys.path so imports
# load the edited source under /workspaces/fastq-sapio-watcher instead of any
# duplicate copies mounted at /app.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def enable_logger_propagation_session():
    """Enable propagation on the module logger for the duration of the test session.

    Some tests use caplog to capture log records. The application sets
    `LOGGER.propagate = False` by default; this fixture temporarily enables
    propagation so caplog can see the records, then restores the previous
    value after tests complete.
    """
    logger = logging.getLogger("fastq-sapio-watcher")
    old = logger.propagate
    logger.propagate = True
    yield
    logger.propagate = old


@contextmanager
def runfolder(samples: list[PairedReadSampleTestData], dir: Path | None = None):
    with tempfile.TemporaryDirectory(dir=dir) as tmpdirname:
        rf = RunFolder(tmpdirname)
        rf.write_samples(samples)
        yield rf
