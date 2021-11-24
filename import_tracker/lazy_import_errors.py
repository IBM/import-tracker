"""
This module implements a context manager which can be used to wrap import
statements such that ModuleNotFound errors will be deferred until the module is
used.
"""

# Standard
from contextlib import contextmanager
import importlib.abc
import importlib.util
import sys

## Public ######################################################################

@contextmanager
def lazy_import_errors():
    """This context manager injects lazy loading as the default loading method
    for the import statement and then disables it on exit, returning to the
    standard import semantics
    """
    try:
        sys.meta_path.append(_LazyMetaFinder)
        yield
    finally:
        sys.meta_path.pop()

## Implementation Details ######################################################

class _LazyErrorLoader(importlib.abc.Loader):
    """This "loader" can be used with a MetaFinder to catch not-found modules
    and raise a ModuleNotFound error lazily when the module is used rather than
    at import time.
    """
    def __init__(self, fullname):
        self.__fullname = fullname

    def create_module(self, spec):
        return None

    def exec_module(self, spec):
        raise ModuleNotFoundError(f"No module named '{self.__fullname}'")


class _LazyMetaFinder(importlib.abc.MetaPathFinder):
    """A lazy finder that always claims to be able to find the module, but will
    potentially raise an ImportError when the module is used
    """

    @staticmethod
    def find_spec(fullname, path, *args, **kwargs):
        """Since this meta finder is the last priority, it will only be used for
        modules that are not otherwise found. As such, we use it to set up a
        lazy ModuleNotFoundError that will trigger when the module is used
        rather than when it is imported.
        """

        # Set up a lazy loader that wraps the Loader that defers the error to
        # exec_module time
        loader = _LazyErrorLoader(fullname)
        lazy_loader = importlib.util.LazyLoader(loader)

        # Create a spec from this loader so that it acts at import-time like it
        # loaded correctly
        return importlib.util.spec_from_loader(fullname, lazy_loader)
