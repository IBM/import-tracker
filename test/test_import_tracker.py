"""
Tests for the import_tracker module's public API
"""

# Standard
from types import ModuleType
import json
import os
import sys
import tempfile
import warnings

# Third Party
import pytest

# Local
from test.helpers import (
    BEST_EFFORT_MODE,
    LAZY_MODE,
    PROACTIVE_MODE,
    TRACKING_MODE,
    remove_test_deps,
    reset_static_trackers,
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


## get_required_imports ########################################################


@pytest.mark.parametrize(
    "mode",
    [
        import_tracker.BEST_EFFORT,
        import_tracker.LAZY,
        import_tracker.PROACTIVE,
    ],
)
def test_get_required_imports_static_tracker(mode):
    """Test that get_required_imports returns the right results in all modes
    that use the static values
    """
    with import_tracker.default_import_mode(mode):
        # Local
        import sample_lib

        assert set(import_tracker.get_required_imports("sample_lib.submod1")) == {
            "conditional_deps",
        }
        assert set(import_tracker.get_required_imports("sample_lib.submod2")) == {
            "alog",
        }
        assert set(
            import_tracker.get_required_imports("sample_lib.nested.submod3")
        ) == {
            "alog",
            "yaml",
        }


def test_get_required_imports_untracked():
    """Test that an appropriate ValueError is raised if an untracked module is
    requested
    """
    with pytest.raises(ValueError):
        import_tracker.get_required_imports("alog")


## get_required_packages #######################################################


@pytest.mark.parametrize(
    "mode",
    [
        import_tracker.BEST_EFFORT,
        import_tracker.LAZY,
        import_tracker.PROACTIVE,
    ],
)
def test_get_required_packages_static_tracker(mode):
    """Test that get_required_packages returns the right results in all modes
    that use the static values
    """
    with import_tracker.default_import_mode(mode):
        # Local
        import sample_lib

        assert set(import_tracker.get_required_packages("sample_lib.submod2")) == {
            "alchemy-logging",
        }
        assert set(
            import_tracker.get_required_packages("sample_lib.nested.submod3")
        ) == {
            "alchemy-logging",
            "PyYAML",
        }


def test_get_required_packages_untracked():
    """Test that an appropriate ValueError is raised if an untracked module is
    requested
    """
    with pytest.raises(ValueError):
        import_tracker.get_required_packages("alog")


def test_get_required_packages_no_package_lookup():
    """Test that an appropriate warning is issued if one of the imports does not
    have a known package name
    """
    with warnings.catch_warnings(record=True) as warns:
        warnings.simplefilter("always")
        submod1 = import_tracker.import_module("sample_lib.submod1")
        import_tracker.get_required_packages("sample_lib.submod1")
    assert len(warns) == 1


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


def test_import_module_lazy_re_import(LAZY_MODE):
    """Test that once a lazy module has been imported, it's simply returned from
    a subsequent import_module
    """
    assert "alog" not in sys.modules
    alog = import_tracker.import_module("alog")
    assert "alog" not in sys.modules
    alog.use_channel("SOMETHING")
    assert "alog" in sys.modules
    alog2 = import_tracker.import_module("alog")
    assert alog2 is sys.modules["alog"]


def test_import_module_lazy_missing_static_tracker(LAZY_MODE):
    """Test that if lazy mode is invoked and the static tracker has not been set
    up, an appropriate warning is raised
    """
    with tempfile.TemporaryDirectory() as workdir:
        static_tracker = os.path.join(workdir, "static_tracker.json")
        import_tracker.set_static_tracker(static_tracker)
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter("always")
            submod1 = import_tracker.import_module("alog")
        assert len(warns) == 1


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


##############
## TRACKING ##
##############


def test_import_module_tracking_direct(TRACKING_MODE):
    """Test that running an import with tracking mode enabled correctly computes
    the dependencies for a module
    """
    submod1 = import_tracker.import_module("sample_lib.submod1")
    submod2 = import_tracker.import_module("sample_lib.submod2")
    assert remove_test_deps(import_tracker.get_required_imports("sample_lib.submod1")) == [
        "conditional_deps"
    ]
    assert remove_test_deps(import_tracker.get_required_imports("sample_lib.submod2")) == [
        "alog"
    ]


def test_import_module_tracking_update_static(TRACKING_MODE):
    """Test that when enabled, the static tracking file is updated correctly"""
    with tempfile.TemporaryDirectory() as workdir:
        static_tracker = os.path.join(workdir, "static_tracker.json")
        import_tracker.set_static_tracker(static_tracker)
        assert not os.path.exists(static_tracker)
        submod1 = import_tracker.import_module("sample_lib.submod1")
        assert os.path.exists(static_tracker)
        with open(static_tracker, "r") as handle:
            content = json.load(handle)
            assert list(content.keys()) == ["sample_lib.submod1"]
        submod2 = import_tracker.import_module("sample_lib.submod2")
        with open(static_tracker, "r") as handle:
            content = json.load(handle)
            assert set(content.keys()) == {"sample_lib.submod1", "sample_lib.submod2"}


def test_import_module_tracking_with_package(TRACKING_MODE):
    """Test that performing tracking when the submodule has a package works as
    expected (this is mostly for coverage)
    """
    import_tracker.import_module(".submod1", "sample_lib")


def test_import_module_tracking_env_passthrough(TRACKING_MODE):
    """Test that performing tracking when the submodule has a package works as
    expected (this is mostly for coverage)
    """
    os.environ["SAMPLE_ENV_VAR"] = "something"
    import_tracker.import_module("env_import")
