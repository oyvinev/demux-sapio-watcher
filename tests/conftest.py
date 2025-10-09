import logging
import pytest


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
