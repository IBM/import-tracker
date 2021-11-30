"""
Shared test helpers
"""

# Standard
import sys

# Third Party
import pytest


@pytest.fixture
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
