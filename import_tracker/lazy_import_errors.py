"""
This module implements a context manager which can be used to wrap import
statements such that ModuleNotFound errors will be deferred until the module is
used.
"""

# Standard
from contextlib import contextmanager
from types import ModuleType
import importlib.abc
import importlib.util
import inspect
import sys

## Public ######################################################################


@contextmanager
def lazy_import_errors():
    """This context manager injects lazy loading as the default loading method
    for the import statement and then disables it on exit, returning to the
    standard import semantics
    """
    try:
        sys.meta_path.append(_LazyMetaFinder())
        yield
    finally:
        sys.meta_path.pop()


## Implementation Details ######################################################


class _LazyErrorModule(ModuleType):
    """This module is a lazy error thrower. It is created when the module cannot
    be found so that import errors are deferred until attribute access.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.__path__ = None

    def __getattr__(self, name: str):
        raise ModuleNotFoundError(f"No module named '{self.__name__}'")


class _LazyErrorLoader(importlib.abc.Loader):
    """This "loader" can be used with a MetaFinder to catch not-found modules
    and raise a ModuleNotFound error lazily when the module is used rather than
    at import time.
    """

    def create_module(self, spec):
        return _LazyErrorModule(spec.name)

    def exec_module(self, *_, **__):
        """Nothing to do here because the errors will be thrown by the module
        created in create_module
        """


class _LazyMetaFinder(importlib.abc.MetaPathFinder):
    """A lazy finder that always claims to be able to find the module, but will
    potentially raise an ImportError when the module is used
    """

    def __init__(self):
        self.calling_pkg = None
        self.this_module = sys.modules[__name__].__package__.split(".")[0]
        non_importlib_mods = self._get_non_import_modules()
        for pkgname in non_importlib_mods:
            # If this is the first non-initial hit that does match this module
            # then the previous module is the one calling import_module
            if self.calling_pkg is None and pkgname not in [
                self.this_module,
                "contextlib",
            ]:
                self.calling_pkg = pkgname
        assert self.calling_pkg is not None

    def find_spec(self, fullname, path, *args, **kwargs):
        """Since this meta finder is the last priority, it will only be used for
        modules that are not otherwise found. As such, we use it to set up a
        lazy ModuleNotFoundError that will trigger when the module is used
        rather than when it is imported.
        """
        importing_pkg = None
        for pkgname in self._get_non_import_modules():
            # If this is the first hit beyond this module, it's the module doing
            # the import
            if importing_pkg is None and pkgname != self.this_module:
                importing_pkg = pkgname
                break

        assert None not in [
            importing_pkg,
            self.calling_pkg,
        ], "Could not determine calling and importing pkg"

        # If the two are not the same, don't mask this with lazy errors
        if importing_pkg != self.calling_pkg:
            return None

        # Set up a lazy loader that wraps the Loader that defers the error to
        # exec_module time
        loader = _LazyErrorLoader()

        # Create a spec from this loader so that it acts at import-time like it
        # loaded correctly
        return importlib.util.spec_from_loader(fullname, loader)

    ## Implementation Details ######################################################
    @staticmethod
    def _get_non_import_modules():
        # Figure out the module that is doing the import and the module that is
        # calling import_module
        stack = inspect.stack()
        non_importlib_mods = list(
            filter(
                lambda x: x != "importlib",
                [frame.frame.f_globals["__name__"].split(".")[0] for frame in stack],
            )
        )
        return non_importlib_mods
