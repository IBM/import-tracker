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


@pytest.fixture(autouse=True)
def reset_static_trackers():
    """This fixture clears out the global static tracker map"""
    before_static_trackers = list(import_tracker.import_tracker._static_trackers.keys())
    yield
    for key in list(import_tracker.import_tracker._static_trackers.keys()):
        if key not in before_static_trackers:
            del import_tracker.import_tracker._static_trackers[key]


@pytest.fixture
def BEST_EFFORT_MODE():
    """Fixture that uses the default_import_mode context manager to ensure that
    the mode is BEST_EFFORT
    """
    with _set_mode(import_tracker.BEST_EFFORT):
        yield


@pytest.fixture
def LAZY_MODE():
    """Fixture that uses the default_import_mode context manager to ensure that
    the mode is LAZY
    """
    with _set_mode(import_tracker.LAZY):
        yield


@pytest.fixture
def PROACTIVE_MODE():
    """Fixture that uses the default_import_mode context manager to ensure that
    the mode is PROACTIVE
    """
    with _set_mode(import_tracker.PROACTIVE):
        yield


@pytest.fixture
def TRACKING_MODE():
    """Fixture that uses the default_import_mode context manager to ensure that
    the mode is TRACKING
    """
    with _set_mode(import_tracker.TRACKING):
        yield


## Implementations #############################################################


@contextmanager
def _set_mode(mode):
    prev_env_val = os.environ.pop(import_tracker.MODE_ENV_VAR, None)
    with import_tracker.default_import_mode(mode):
        yield
    if prev_env_val is not None:
        os.environ[import_tracker.MODE_ENV_VAR] = prev_env_val
