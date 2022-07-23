"""
Global autouse fixtures that will be used by all tests
"""

# Standard
import logging
import os
import sys

# Third Party
import pytest

# Local
from import_tracker.log import log


@pytest.fixture(autouse=True)
def configure_logging():
    """Fixture that configures logging from the env. It is auto-used, so if
    imported, it will automatically configure for each test.

    NOTE: The import of alog is inside the function since alog is used as a
        sample package for lazy importing in some tests
    """
    logging.basicConfig()
    log.root.setLevel(getattr(logging, os.environ.get("LOG_LEVEL", "warning").upper()))


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
