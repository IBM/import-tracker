"""
This module implements utilities that enable tracking of third party deps
through import statements
"""

# Standard
from types import ModuleType
from typing import Dict, Set
import importlib
import os
import re
import sys
import warnings


## Public Globals ##############################################################

# Possible import modes
LAZY = "LAZY"
PROACTIVE = "PROACTIVE"
TRACKING = "TRACKING"

# The env var used to check the mode
MODE_ENV_VAR = "IMPORT_TRACKER_MODE"

## Impl Globals ################################################################

# The configured version. This defaults to lazy importing.
_import_mode = os.environ.get(MODE_ENV_VAR, LAZY)

# The global mapping from modules to dependencies
_module_dep_mapping = {}

# Lazily created global mapping from module name to package name
_module_to_pkg = None

# Exprs for finding module names
_pkg_version_expr = re.compile("-[0-9]")
_pkg_name_expr = re.compile("^Name: ([^\s]+)")


## Utils #######################################################################

def import_module(module_name: str, *args, **kwargs) -> ModuleType:
    """Import a module by name and keep track of the changes in the global
    modules dict
    """
    # If this module is already imported, just return it
    if module_name in sys.modules:
        return sys.modules[module_name]

    # If performing a PROACTIVE import, import directly and return
    if _import_mode == PROACTIVE:
        return importlib.import_module(module_name, *args, **kwargs)

    # If we're doing a TRACKING import. In this case, we're going to perform the
    # the tracking in a subprocess and then return a lazy importer
    if _import_mode == TRACKING:
        _track_deps(module_name, *args, **kwargs)

    # For either LAZY or TRACKING, we return a Lazy Importer
    return LazyModule(module_name, *args, **kwargs)


def get_required_imports(module_name: str) -> Set[str]:
    """Get the set of modules that are required for the given module by name. If
    the module is not known, ImportError is raised
    """
    # TODO: If module not found, look in static module mapping
    if module_name not in _module_dep_mapping:
        raise ImportError(f"Cannot get required imports for untracked module [{module_name}]")
    return _module_dep_mapping[module_name]


def get_required_packages(module_name: str) -> Set[str]:
    """Get the set of installable packages required by this names module"""
    # Lazily create the global mapping
    global _module_to_pkg
    if _module_to_pkg is None:
        _module_to_pkg = _map_modules_to_package_names()

    # Get all required imports
    required_modules = get_required_imports(module_name)

    # Merge the required packages for each
    required_pkgs = set()
    for mod in required_modules:
        if mod in _module_to_pkg:
            required_pkgs.update(_module_to_pkg[mod])
        else:
            warnings.warn(f"Could not find any required packages for {mod}")
    return required_pkgs


## Implementation Details ######################################################


class LazyModule(ModuleType):
    """A LazyModule is a module subclass that wraps another module but imports
    it lazily and then aliases __getattr__ to the lazily imported module.
    """

    def __init__(self, module_name: str, *args, **kwargs):
        """Hang onto the import args to use lazily"""
        self.__module_name = module_name
        self.__args = args
        self.__kwargs = kwargs
        self.__wrapped_module = None

    def __getattr__(self, name: str) -> any:
        """When asked for an attribute, make sure the wrapped module is imported
        and then delegate
        """
        if self.__wrapped_module is None:
            self.__wrapped_module = importlib.import_module(
                self.__module_name, *self.__args, **self.__kwargs,
            )
        return getattr(self.__wrapped_module, name)


def _track_deps(module_name: str, *args, **kwargs):
    """DEBUG!!!!!!!!!!!!!!!

    This needs to be properly implemented
    """

    # Do the import
    imported = importlib.import_module(module_name, *args, **kwargs)

    # Get the snapshot of non-standard modules after importing
    global _module_dep_mapping
    _module_dep_mapping[imported.__name__] = _get_non_std_modules()

    # Return the imported module
    return imported


def _map_modules_to_package_names():
    """Look for any information we can get to map from the name of the imported
    module to the name of the package that installed that module.

    WARNING: This is a best-effort function! It attempts to look for common
        conventions from pip, but it's very possible to break this function by
        non-standard installation topology.
    """
    modules_to_package_names = {}
    for path_dir in sys.path:

        # Traverse all "RECORD" files holding records of the pip installations
        for root, dirs, files in os.walk(path_dir):
            if "RECORD" in files:

                # Parse the package name from the info file name
                package_file = os.path.relpath(root, path_dir).split("/")[-1]
                package_name = _pkg_version_expr.split(package_file)[0]

                # Look for a more accurate package name in METADATA. This can
                # fix the case where the actual package uses a '-' but the wheel
                # uses an '_'.
                if "METADATA" in files:
                    md_file = os.path.join(root, "METADATA")
                    # Parse the package name from the metadata file
                    with open(md_file, "r") as handle:
                        for line in handle.readlines():
                            match = _pkg_name_expr.match(line.strip())
                            if match:
                                package_name = match.group(1)
                                break

                # Iterate each line in RECORD and look for lines that look like
                # unpacking python modules
                with open(os.path.join(root, "RECORD"), "r") as handle:
                    for modname in map(
                        lambda mn: os.path.splitext(mn)[0],
                        filter(
                            lambda mn: (
                                mn
                                and mn != "__pycache__"
                                and os.path.splitext(mn)[-1] not in [".pth", ".dist-info", ".egg-info"]
                                and "." not in mn
                            ),
                            {
                                line.split("/")[0].split(",")[0].strip()
                                for line in handle.readlines()
                            }
                        )
                    ):
                        modules_to_package_names.setdefault(modname, set()).add(package_name)

    return modules_to_package_names
