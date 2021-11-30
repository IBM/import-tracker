"""
Tests for the import_tracker module's public API
"""

# Standard
import os

# Third Party
import pytest

# Local
from test.helpers import reset_sys_modules
import import_tracker

def test_lazy_import_tracker_sad_package(reset_sys_modules):
    """This test makes sure that the ModuleNotFoundError is not raised for an
    unknown module on import, but that it is raised on attribute access.

    This version tests that this is true when imported via
    import_tracker.import_module
    """
    foobarbaz = import_tracker.import_module("foobarbaz")
    with pytest.raises(ModuleNotFoundError):
        foobarbaz.foo()

def test_lazy_import_tracker_happy_package_with_sad_optionals(reset_sys_modules):
    """This test uses `numpy` which has several "optional" dependencies in order
    to support backwards compatibility. We need to ensure that these usecases
    are supported such that the downstream libs do not get confused.

    This version tests that the import works when imported via
    import_tracker.import_module

    CITE: https://github.com/numpy/numpy/blob/main/numpy/compat/py3k.py#L24
    """
    import pickle
    numpy = import_tracker.import_module("numpy")
    assert numpy.compat.py3k.pickle is pickle
