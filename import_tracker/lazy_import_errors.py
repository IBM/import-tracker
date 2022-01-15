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


class _LazyErrorAttr(type):
    """This object is used to recursively allow attribute access from a
    _LazyErrorModule and only trigger an error when an attribute is used

    NOTE: This object _is_ itself a type. This is done to ensure that attributes
        on a missing module which are types in the module itself can still be
        treated as types. This is particularly important when deserializing a
        pickled object whose type is not available at unpickling time. By acting
        as a type, this object ensures that the appropriate ModuleNotFoundError
        is raised rather than an opaque error about NEWOBJ not being a type.
    """

    def __new__(cls, missing_module_name: str, bases=None, namespace=None):
        # When this is used as a base class, we need to pass __classcell__
        # through to type.__new__ to avoid a runtime warning.
        new_namespace = {}
        if isinstance(namespace, dict):
            new_namespace["__classcell__"] = namespace.get("__classcell__")
        return super().__new__(
            cls, f"_LazyErrorAttr[{missing_module_name}]", (), new_namespace
        )

    def __init__(self, missing_module_name: str, *_, **__):
        """Store the name of the attribute being accessed and the missing module"""

        def _raise(*_, **__):
            raise ModuleNotFoundError(f"No module named '{missing_module_name}'")

        self._raise = _raise

    def __getattr__(self, name: str) -> "_LazyErrorAttr":
        """Return self so that attributes can be extracted recursively"""
        return self

    ##
    # Override _everything_ to raise! This list is taken directly from the
    # CPython source code:
    # https://github.com/python/cpython/blob/main/Objects/typeobject.c#L7986
    #
    # The only exclusions from the set defined above are those which are used as
    # part of the actual import mechanism:
    #   __bool__
    #   __del__
    #   __getattr__
    #   __getattribute__
    #   __init__
    #   __len__
    #   __new__
    #   __repr__
    #   __setattr__
    ##
    def __abs__(self, *_, **__):
        self._raise()

    def __add__(self, *_, **__):
        self._raise()

    async def __aiter__(self, *_, **__):
        self._raise()

    def __and__(self, *_, **__):
        self._raise()

    async def __anext__(self, *_, **__):
        self._raise()

    def __await__(self, *_, **__):
        self._raise()

    def __call__(self, *_, **__):
        self._raise()

    def __contains__(self, *_, **__):
        self._raise()

    def __delattr__(self, *_, **__):
        self._raise()

    def __delete__(self, *_, **__):
        self._raise()

    def __delitem__(self, *_, **__):
        self._raise()

    def __eq__(self, *_, **__):
        self._raise()

    def __float__(self, *_, **__):
        self._raise()

    def __floordiv__(self, *_, **__):
        self._raise()

    def __ge__(self, *_, **__):
        self._raise()

    def __get__(self, *_, **__):
        self._raise()

    def __getitem__(self, *_, **__):
        self._raise()

    def __gt__(self, *_, **__):
        self._raise()

    def __hash__(self, *_, **__):
        self._raise()

    def __iadd__(self, *_, **__):
        self._raise()

    def __iand__(self, *_, **__):
        self._raise()

    def __ifloordiv__(self, *_, **__):
        self._raise()

    def __ilshift__(self, *_, **__):
        self._raise()

    def __imatmul__(self, *_, **__):
        self._raise()

    def __imod__(self, *_, **__):
        self._raise()

    def __imul__(self, *_, **__):
        self._raise()

    def __index__(self, *_, **__):
        self._raise()

    def __int__(self, *_, **__):
        self._raise()

    def __invert__(self, *_, **__):
        self._raise()

    def __ior__(self, *_, **__):
        self._raise()

    def __ipow__(self, *_, **__):
        self._raise()

    def __irshift__(self, *_, **__):
        self._raise()

    def __isub__(self, *_, **__):
        self._raise()

    def __iter__(self, *_, **__):
        self._raise()

    def __itruediv__(self, *_, **__):
        self._raise()

    def __ixor__(self, *_, **__):
        self._raise()

    def __le__(self, *_, **__):
        self._raise()

    def __lshift__(self, *_, **__):
        self._raise()

    def __lt__(self, *_, **__):
        self._raise()

    def __matmul__(self, *_, **__):
        self._raise()

    def __mod__(self, *_, **__):
        self._raise()

    def __mul__(self, *_, **__):
        self._raise()

    def __ne__(self, *_, **__):
        self._raise()

    def __neg__(self, *_, **__):
        self._raise()

    def __next__(self, *_, **__):
        self._raise()

    def __or__(self, *_, **__):
        self._raise()

    def __pos__(self, *_, **__):
        self._raise()

    def __pow__(self, *_, **__):
        self._raise()

    def __radd__(self, *_, **__):
        self._raise()

    def __rand__(self, *_, **__):
        self._raise()

    def __rfloordiv__(self, *_, **__):
        self._raise()

    def __rlshift__(self, *_, **__):
        self._raise()

    def __rmatmul__(self, *_, **__):
        self._raise()

    def __rmod__(self, *_, **__):
        self._raise()

    def __rmul__(self, *_, **__):
        self._raise()

    def __ror__(self, *_, **__):
        self._raise()

    def __rpow__(self, *_, **__):
        self._raise()

    def __rrshift__(self, *_, **__):
        self._raise()

    def __rshift__(self, *_, **__):
        self._raise()

    def __rsub__(self, *_, **__):
        self._raise()

    def __rtruediv__(self, *_, **__):
        self._raise()

    def __rxor__(self, *_, **__):
        self._raise()

    def __set__(self, *_, **__):
        self._raise()

    def __setitem__(self, *_, **__):
        self._raise()

    def __str__(self, *_, **__):
        self._raise()

    def __sub__(self, *_, **__):
        self._raise()

    def __truediv__(self, *_, **__):
        self._raise()

    def __xor__(self, *_, **__):
        self._raise()


class _LazyErrorModule(ModuleType):
    """This module is a lazy error thrower. It is created when the module cannot
    be found so that import errors are deferred until attribute access.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.__path__ = None

    def __getattr__(self, name: str) -> _LazyErrorAttr:
        # For special module attrs, return as if a stub module
        if name in ["__file__", "__module__", "__doc__", "__cached__"]:
            return None
        return _LazyErrorAttr(self.__name__)


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
