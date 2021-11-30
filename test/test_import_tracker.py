"""
Tests for the import_tracker module's public API
"""

# Standard
from types import ModuleType
import os
import sys

# Third Party
import pytest

# Local
from test.helpers import (
    BEST_EFFORT_MODE,
    LAZY_MODE,
    PROACTIVE_MODE,
    TRACKING_MODE,
    reset_sys_modules,
)
import import_tracker

## default_import_mode #########################################################


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


## import_module ###############################################################

#################
## BEST_EFFORT ##
#################


def test_import_module_best_effort_unknown_import(BEST_EFFORT_MODE):
    """This test makes sure that the ModuleNotFoundError is not raised for an
    unknown module on import, but that it is raised on attribute access.

    This version tests that this is true when imported via
    import_tracker.import_module
    """
    foobarbaz = import_tracker.import_module("foobarbaz")
    assert isinstance(foobarbaz, ModuleType)
    with pytest.raises(ModuleNotFoundError):
        foobarbaz.foo()


def test_import_module_best_effort_downstream_conditional_deps(BEST_EFFORT_MODE):
    """This test ensures that a library with traditional try/except conditional
    dependencies works as expected.

    This version tests that the import works when imported via
    import_tracker.import_module
    """
    conditional_deps = import_tracker.import_module("conditional_deps")
    assert not conditional_deps.mod.HAS_FB


def test_import_module_best_effort_downstream_unknown_import(BEST_EFFORT_MODE):
    """Test that when a downstream has an unknown import, it only errors out
    when used
    """
    bad_deps = import_tracker.import_module("bad_deps")
    bad_deps.bad_import.use_alog()
    with pytest.raises(ModuleNotFoundError):
        bad_deps.bad_import.use_foobar()


def test_import_module_best_effort_downstream_use(BEST_EFFORT_MODE):
    """Test that a downstream can use import_module itself as expected"""
    sample_lib = import_tracker.import_module("sample_lib")
    assert hasattr(sample_lib, "submod1")
    assert hasattr(sample_lib, "submod2")
    assert hasattr(sample_lib.nested, "submod3")


##########
## LAZY ##
##########


def test_import_module_lazy_direct_use(LAZY_MODE):
    """Test that a lazily imported module imports at attribute access time"""
    assert "alog" not in sys.modules
    alog = import_tracker.import_module("alog")
    assert "alog" not in sys.modules
    alog.use_channel("SOMETHING")
    assert "alog" in sys.modules


def test_import_module_lazy_downstream_use(LAZY_MODE):
    """Test that a lazily imported module in a downstream is only imported on
    attribute access
    """
    mod_name = "sample_lib.nested.submod3"
    assert mod_name not in sys.modules
    submod3 = import_tracker.import_module(mod_name)
    assert mod_name not in sys.modules
    submod3.json_to_yamls('{"foo": 1}')
    assert mod_name in sys.modules


###############
## PROACTIVE ##
###############


def test_import_module_proactive_direct_use(PROACTIVE_MODE):
    """Test that a proactively imported module imports immediately"""
    assert "alog" not in sys.modules
    alog = import_tracker.import_module("alog")
    assert "alog" in sys.modules


def test_import_module_proactive_downstream_use(PROACTIVE_MODE):
    """Test that a proactively imported module in a downstream is imported
    immediately
    """
    mod_name = "sample_lib.nested.submod3"
    assert mod_name not in sys.modules
    submod3 = import_tracker.import_module(mod_name)
    assert mod_name in sys.modules
