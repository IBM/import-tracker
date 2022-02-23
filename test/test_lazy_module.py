"""
Tests for the LazyModule
"""

# Standard
import sys

# Third Party
import pytest

# Local
from import_tracker.lazy_module import LazyModule
from test.helpers import reset_sys_modules


def test_lazy_module_valid_import():
    """Test that using LazyModule, a module is only imported on attribute access"""
    assert "alog" not in sys.modules
    alog = LazyModule("alog")
    assert "alog" not in sys.modules
    getattr(alog, "configure")
    assert "alog" in sys.modules


def test_lazy_module_with_package():
    """Make sure that a relative import works with a package name"""
    assert "alog.alog" not in sys.modules
    alog = LazyModule(".alog", "alog")
    assert "alog.alog" not in sys.modules
    getattr(alog, "configure")
    assert "alog.alog" in sys.modules


def test_lazy_module_bad_import():
    """Make sure that imports of bad modules don't raise until attribute access"""
    thingywidget = LazyModule("thingywidget")
    with pytest.raises(ImportError):
        getattr(thingywidget, "baz")
        # DEBUG
        # Standard
        import sys

        print(sys.modules.keys())
