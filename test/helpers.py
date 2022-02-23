"""
Shared test helpers
"""

# Standard
from contextlib import contextmanager
import os
import sys

# Third Party
import pytest

# Local
import import_tracker


@pytest.fixture(autouse=True)
def configure_logging():
    """Fixture that configures logging from the env. It is auto-used, so if
    imported, it will automatically configure for each test.

    NOTE: The import of alog is inside the function since alog is used as a
        sample package for lazy importing in some tests
    """
    # First Party
    import alog

    alog.configure(
        default_level=os.environ.get("LOG_LEVEL", "info"),
        filters=os.environ.get("LOG_FILTERS", ""),
    )


@pytest.fixture(autouse=True)
def reset_sys_modules():
    """This fixture will reset the sys.modules dict to only the keys held before
    the test initialized
    """
    before_keys = list(sys.modules.keys())
    yield
    added_keys = [
        module_name
        for module_name in sys.modules.keys()
        if module_name not in before_keys
    ]
    for added_key in added_keys:
        mod = sys.modules.pop(added_key)
        del mod


def remove_test_deps(deps):
    """If running with pytest coverage enabled, these deps will show up. We
    don't want run-env-dependent tests, so we just pop them out.
    """
    for test_dep in ["pytest_cov", "coverage"]:
        try:
            deps.remove(test_dep)
        except ValueError:
            continue
    return deps
