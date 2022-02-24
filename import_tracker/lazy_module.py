"""
This module implements utilities that enable tracking of third party deps
through import statements
"""

# Standard
from types import ModuleType
from typing import Optional
import importlib

# Local
from .log import log


class LazyModule(ModuleType):
    """A LazyModule is a module subclass that wraps another module but imports
    it lazily and then aliases __getattr__ to the lazily imported module.
    """

    def __init__(self, name: str, package: Optional[str] = None):
        """Hang onto the import args to use lazily"""
        self.__name = name
        self.__package = package
        self.__wrapped_module = None

    def __getattr__(self, name: str) -> any:
        """When asked for an attribute, make sure the wrapped module is imported
        and then delegate
        """
        if self.__wrapped_module is None:
            log.debug1("Triggering lazy import for %s.%s", self.__package, self.__name)
            self.__wrapped_module = importlib.import_module(
                self.__name,
                self.__package,
            )
        return getattr(self.__wrapped_module, name)
