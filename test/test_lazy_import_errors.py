"""
Tests for the lazy_import_errors functionality
"""

# Standard
import os

# Third Party
import pytest

# Local
from test.helpers import reset_sys_modules
import import_tracker

######################## Tests for Direct Invocation of the Context Manager #######################
def test_lazy_import_sad_package(reset_sys_modules):
    """This test makes sure that the ModuleNotFoundError is not raised for an
    unknown module on import, but that it is raised on attribute access.

    This version tests that this is true when imported directly, but wrapped in
    lazy_import_errors.
    """
    with import_tracker.lazy_import_errors():
        import foobarbaz
    with pytest.raises(ModuleNotFoundError):
        foobarbaz.foo()

def test_lazy_import_happy_package_with_sad_optionals(reset_sys_modules):
    """This test ensures that a library with traditional try/except conditional
    dependencies works as expected.

    This version tests that the import works when imported directly, but wrapped
    in lazy_import_errors.
    """
    import pickle
    with import_tracker.lazy_import_errors():
        import conditional_deps
    assert not conditional_deps.mod.HAS_FB
