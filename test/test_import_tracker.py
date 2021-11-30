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

#########################
## default_import_mode ##
#########################


def test_default_import_mode():
    """Make sure that the test_default_import_mode context manager correctly
    sets the default import mode
    """
    assert (
        import_tracker.import_tracker._default_import_mode == import_tracker.BEST_EFFORT
    )
    with import_tracker.default_import_mode(import_tracker.LAZY):
        assert import_tracker.import_tracker._default_import_mode == import_tracker.LAZY
    assert (
        import_tracker.import_tracker._default_import_mode == import_tracker.BEST_EFFORT
    )


def test_default_import_mode_nested():
    """Make sure that the test_default_import_mode context manager nests
    multiple contexts correctly
    """
    assert (
        import_tracker.import_tracker._default_import_mode == import_tracker.BEST_EFFORT
    )
    with import_tracker.default_import_mode(import_tracker.LAZY):
        assert import_tracker.import_tracker._default_import_mode == import_tracker.LAZY
        with import_tracker.default_import_mode(import_tracker.TRACKING):
            assert (
                import_tracker.import_tracker._default_import_mode
                == import_tracker.TRACKING
            )
        assert import_tracker.import_tracker._default_import_mode == import_tracker.LAZY
    assert (
        import_tracker.import_tracker._default_import_mode == import_tracker.BEST_EFFORT
    )


def test_default_import_mode_validation():
    """Make sure that the test_default_import_mode context manager validates the
    string as expected
    """
    assert (
        import_tracker.import_tracker._default_import_mode == import_tracker.BEST_EFFORT
    )
    with pytest.raises(ValueError):
        with import_tracker.default_import_mode("foobar"):
            assert False, "We should not get here!"
    assert (
        import_tracker.import_tracker._default_import_mode == import_tracker.BEST_EFFORT
    )


###################
## import_module ##
###################


def test_import_module_unknown_import(reset_sys_modules):
    """This test makes sure that the ModuleNotFoundError is not raised for an
    unknown module on import, but that it is raised on attribute access.

    This version tests that this is true when imported via
    import_tracker.import_module
    """
    foobarbaz = import_tracker.import_module("foobarbaz")
    with pytest.raises(ModuleNotFoundError):
        foobarbaz.foo()


def test_import_module_downstream_conditional_deps(reset_sys_modules):
    """This test ensures that a library with traditional try/except conditional
    dependencies works as expected.

    This version tests that the import works when imported via
    import_tracker.import_module
    """
    conditional_deps = import_tracker.import_module("conditional_deps")
    assert not conditional_deps.mod.HAS_FB
