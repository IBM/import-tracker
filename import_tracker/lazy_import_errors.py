"""
This module implements a context manager which can be used to wrap import
statements such that ModuleNotFound errors will be deferred until the module is
used.
"""

# Standard
from contextlib import AbstractContextManager
from functools import partial
from types import ModuleType
from typing import Callable, Optional, Set
import importlib.abc
import importlib.util
import inspect
import sys

## Public ######################################################################


def lazy_import_errors(
    *,
    get_extras_modules: Optional[Callable[[], Set[str]]] = None,
    make_error_message: Optional[Callable[[str], str]] = None,
):
    """Enable lazy import errors.

    When enabled, lazy import errors will capture imports that would otherwise
    raise ImportErrors and defer those errors until the last possible moment
    when the functionality is needed. This is done by returning a special object
    which can be used in all "non-meaningful" ways without raising, but when
    used in a "meaningful" way will raise.

    This function may be used either as a function directly or as a
    contextmanager which will disable lazy errors upon exit.

    Args:
        get_extras_modules:  Optional[Callable[[], Set[str]]]
            Optional callable that fetches the list of module names in the
            calling library that are managed as extras using
            setup_tools.parse_requirements. (Mutually exclusive
            with make_error_message)
        make_error_message:  Optional[Callable[[str], str]]
            Optional callable that takes the name of the module which faild to
            import and returns an error message string to be used for the
            ModuleNotFoundError. (Mutually exclusive with get_extras_modules)
    """
    if get_extras_modules is not None and make_error_message is not None:
        raise TypeError(
            "Cannot specify both 'get_extras_modules' and 'make_error_message'"
        )

    if get_extras_modules is not None:
        make_error_message = partial(_make_extras_import_error, get_extras_modules)

    return _LazyImportErrorCtx(make_error_message)


## Implementation Details ######################################################

_TRACKING_MODE = False


def enable_tracking_mode():
    """This is used by the main function to disable all lazy import errors when
    running as a standalone script to track the modules in a library.

    This function should NOT be exposed as a public API
    """
    global _TRACKING_MODE
    _TRACKING_MODE = True


def _make_extras_import_error(
    get_extras_modules: Callable[[], Set[str]],
    missing_module_name: str,
) -> Optional[str]:
    """This function implements the most common implementation of a custom error
    message where the calling library has some mechanism for determining which
    modules are managed as extras and wants the error messages to include the
    `pip install` command needed to add the missing dependencies.

    NOTE: There is an assumption here that the name of the root module is the
        name of the pip package. If this is NOT true (e.g. alchemy-logging vs
        alog), the module will need to implement its own custom
        make_error_message.

    Args:
        get_extras_modules:  Callable[[] Set[str]]
            The function bound in from the caller that yields the set of extras
            modules for the library
        missing_module_name:  str
            The name of the module that failed to import

    Returns:
        error_msg:  Optional[str]
            If the current stack includes an extras module, the formatted string
            will be returned, otherwise None will be returned to allow the base
            error message to be used.
    """
    # Get the set of extras modules from the library
    extras_modules = get_extras_modules()

    # Look through frames in the stack to see if there's an extras module
    extras_module = None
    for frame in inspect.stack():
        frame_module = frame.frame.f_globals["__name__"]
        if frame_module in extras_modules:
            extras_module = frame_module
            break

    # If an extras module was found, return the formatted message
    if extras_module is not None:
        base_module = extras_module.partition(".")[0]
        return (
            f"No module named '{missing_module_name}'. To install the "
            + f"missing dependencies, run `pip install {base_module}[{extras_module}]`"
        )


class _LazyImportErrorCtx(AbstractContextManager):
    """This class implements the Context Manager version of lazy_import_errors"""

    def __init__(self, make_error_message: Optional[Callable[[str], str]]):
        """This class is always constructed inside of lazy_import_errors which
        acts as the context manager, so the __enter__ implementation lives in
        the constructor.
        """
        if (
            not _TRACKING_MODE
            and sys.meta_path
            and not isinstance(sys.meta_path[-1], _LazyErrorMetaFinder)
        ):
            sys.meta_path.append(_LazyErrorMetaFinder(make_error_message))

    @staticmethod
    def __enter__():
        """Nothing to do in __enter__ since it's done in __init__"""
        pass

    @classmethod
    def __exit__(cls, *_, **__):
        """On exit, ensure there are no lazy meta finders left"""
        while sys.meta_path and isinstance(sys.meta_path[-1], _LazyErrorMetaFinder):
            sys.meta_path.pop()


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

    def __new__(
        cls,
        missing_module_name: str,
        bases=None,
        namespace=None,
        **__,
    ):
        # When this is used as a base class, we need to pass __classcell__
        # through to type.__new__ to avoid a runtime warning.
        new_namespace = {}
        if isinstance(namespace, dict):
            new_namespace["__classcell__"] = namespace.get("__classcell__")
        return super().__new__(
            cls, f"_LazyErrorAttr[{missing_module_name}]", (), new_namespace
        )

    def __init__(
        self,
        missing_module_name: str,
        *_,
        make_error_message: Optional[Callable[[str], str]] = None,
        **__,
    ):
        """Store the name of the attribute being accessed and the missing module"""

        def _raise(*_, **__):
            msg = None
            if make_error_message is not None:
                msg = make_error_message(missing_module_name)
            if msg is None:
                msg = f"No module named '{missing_module_name}'"
            raise ModuleNotFoundError(msg)

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

    def __init__(self, name: str, make_error_message: Optional[Callable[[str], str]]):
        super().__init__(name)
        self.__path__ = None
        self._make_error_message = make_error_message

    def __getattr__(self, name: str) -> _LazyErrorAttr:
        # For special module attrs, return as if a stub module
        if name in ["__file__", "__module__", "__doc__", "__cached__"]:
            return None
        return _LazyErrorAttr(
            self.__name__, make_error_message=self._make_error_message
        )


class _LazyErrorLoader(importlib.abc.Loader):
    """This "loader" can be used with a MetaFinder to catch not-found modules
    and raise a ModuleNotFound error lazily when the module is used rather than
    at import time.
    """

    def __init__(self, make_error_message: Optional[Callable[[str], str]]):
        self._make_error_message = make_error_message

    def create_module(self, spec):
        return _LazyErrorModule(spec.name, self._make_error_message)

    def exec_module(self, *_, **__):
        """Nothing to do here because the errors will be thrown by the module
        created in create_module
        """


class _LazyErrorMetaFinder(importlib.abc.MetaPathFinder):
    """A lazy finder that always claims to be able to find the module, but will
    potentially raise an ImportError when the module is used
    """

    def __init__(self, make_error_message: Optional[Callable[[str], str]]):
        self._make_error_message = make_error_message
        self.calling_pkg = None
        self.this_module = sys.modules[__name__].__package__.split(".")[0]
        for pkgname in self._get_non_import_modules():
            # If this is the first non-initial hit that does match this module
            # then the previous module is the one calling import_module
            if self.calling_pkg is None and pkgname not in [
                self.this_module,
                "contextlib",
            ]:
                self.calling_pkg = pkgname
                break
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
        loader = _LazyErrorLoader(self._make_error_message)

        # Create a spec from this loader so that it acts at import-time like it
        # loaded correctly
        return importlib.util.spec_from_loader(fullname, loader)

    ## Implementation Details ######################################################

    # Custom iterable that uses the low-level sys._getframe to get frames
    # one-at-a-time
    class _FrameGenerator:
        def __init__(self):
            self._depth = -1

        def __iter__(self):
            return self

        def __next__(self):
            self._depth += 1
            try:
                return sys._getframe(self._depth)
            except ValueError:
                self._depth = -1
                raise StopIteration

    @classmethod
    def _get_non_import_modules(cls):

        # Figure out the module that is doing the import and the module that is
        # calling import_module
        return filter(
            lambda x: x != "importlib",
            (
                frame.f_globals["__name__"].split(".")[0]
                for frame in cls._FrameGenerator()
            ),
        )
