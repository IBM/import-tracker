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


## Globals #####################################################################

g_module_dep_mapping = {}

# The path where global modules are found
g_std_lib_dir = os.path.realpath(os.path.dirname(os.__file__))

# Lazily created global mapping from module name to package name
g_module_to_pkg = None

# Implementation detail exprs for finding module names
_pkg_version_expr = re.compile("-[0-9]")
_pkg_name_expr = re.compile("^Name: ([^\s]+)")

## Utils #######################################################################

def import_tracked_module(module_name: str, *args, **kwargs) -> ModuleType:
    """Import a module by name and keep track of the changes in the global
    modules dict
    """
    # If this module is already imported, just return it
    if module_name in sys.modules:
        return sys.modules[module_name]

    # Do the import
    imported = importlib.import_module(module_name, *args, **kwargs)

    # Get the snapshot of non-standard modules after importing
    global g_module_dep_mapping
    g_module_dep_mapping[imported.__name__] = _get_non_std_modules()

    # Return the imported module
    return imported


def get_required_imports(module_name: str) -> Set[str]:
    """Get the set of modules that are required for the given module by name. If
    the module is not known, ImportError is raised
    """
    if module_name not in g_module_dep_mapping:
        raise ImportError(f"Cannot get required imports for untracked module [{module_name}]")
    return g_module_dep_mapping[module_name]


def get_required_packages(module_name: str) -> Set[str]:
    """Get the set of installable packages required by this names module"""
    # Lazily create the global mapping
    global g_module_to_pkg
    if g_module_to_pkg is None:
        g_module_to_pkg = _map_modules_to_package_names()

    # Get all required imports
    required_modules = get_required_imports(module_name)

    # Merge the required packages for each
    required_pkgs = set()
    for mod in required_modules:
        if mod in g_module_to_pkg:
            required_pkgs.update(g_module_to_pkg[mod])
        else:
            warnings.warn(f"Could not find any required packages for {mod}")
    return required_pkgs


## Implementation Details ######################################################

def _get_non_std_modules() -> Set[str]:
    """Take a snapshot of the non-standard modules currently imported"""
    this_module = __name__.split(".")[0]
    return {
        mod_name.split(".")[0]
        for mod_name, mod in sys.modules.items()
        if not mod_name.startswith("_")
        and "." not in mod_name
        and _get_import_parent_path(mod) != g_std_lib_dir
        and os.path.splitext(mod.__file__)[-1] not in [".so", ".dylib"]
        and mod_name.split(".")[0] != this_module
    }


def _get_import_parent_path(mod) -> str:
    """Get the parent directory of the given module"""
    # Some standard libs have no __file__ attribute
    if not hasattr(mod, "__file__"):
        return g_std_lib_dir

    # If the module comes from an __init__, we need to pop two levels off
    file_path = mod.__file__
    if os.path.splitext(os.path.basename(mod.__file__))[0] == "__init__":
        file_path = os.path.dirname(file_path)
    parent_path = os.path.dirname(file_path)
    return parent_path


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
