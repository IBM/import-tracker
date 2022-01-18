"""
This module holds tools for libraries to use when definint requirements and
extras_require sets in a setup.py
"""

# Standard
from functools import reduce
from typing import Dict, List, Tuple
import importlib
import logging
import re
import sys

# Local
from .import_tracker import (
    _get_required_packages_for_imports,
    _standardize_package_name,
    get_required_packages,
    get_tracked_modules,
)

# Shared logger
log = logging.getLogger("SETUP")

# Regex for parsing requirements
_REQ_SPLIT_EXPR = re.compile(r"[=><!~\[]")

_ALL_GROUP = "all"


def _map_requirements(declared_dependencies, dependency_set):
    """Given the declared dependencies from requirements.txt and the given
    programmatic dependency set, return the subset of declared dependencies that
    matches the dependency set
    """
    return sorted(
        [
            declared_dependencies[dep.replace("-", "_")]
            for dep in dependency_set
            if dep.replace("-", "_") in declared_dependencies
        ]
    )


def parse_requirements(
    requirements_file: str,
    library_name: str,
) -> Tuple[List[str], Dict[str, List[str]]]:
    """This helper uses the lists of required modules and parameters for the
    given library to produce requirements and the extras_require dict.

    Args:
        requirements_file:  str
            Path to the requirements file for this library
        library_name:  str
            The name of the library being setup

    Returns:
        requirements:  List[str]
            The list of requirements to pass to setup()
        extras_require:  Dict[str, List[str]]
            The extras_require dict to pass to setup()
    """

    # Import the library. This is used at build time, so it's safe to do so.
    importlib.import_module(library_name)

    # Load all requirements from the requirements file
    with open(requirements_file, "r") as handle:
        requirements = {
            _standardize_package_name(_REQ_SPLIT_EXPR.split(line, 1)[0]): line.strip()
            for line in handle.readlines()
            if line.strip() and not line.startswith("#")
        }
    this_pkg = sys.modules[__name__].__name__.split(".")[0]
    assert (
        this_pkg in requirements or this_pkg.replace("_", "-") in requirements
    ), f"No requirement for {this_pkg} found"
    log.debug("Requirements: %s", requirements)

    # Get the raw import sets for each tracked module
    import_sets = {
        tracked_module.split(".")[-1]: set(get_required_packages(tracked_module))
        for tracked_module in get_tracked_modules(library_name)
    }
    log.debug("Import sets: %s", import_sets)

    # Determine the common requirements from the intersection of all import sets
    common_imports = None
    for import_set in import_sets.values():
        if common_imports is None:
            common_imports = import_set
        else:
            common_imports = common_imports.intersection(import_set)
    common_imports.add(_get_required_packages_for_imports([this_pkg])[0])
    log.debug("Common imports: %s", common_imports)

    # Compute the sets of unique requirements for each tracked module
    extras_require_sets = {
        set_name: import_set - common_imports
        for set_name, import_set in import_sets.items()
    }
    log.debug("Extras require sets: %s", extras_require_sets)

    # Add any listed requirements in that don't show up in any tracked module.
    # These requirements may be needed by an untracked portion of the library or
    # they may be runtime imports.
    all_tracked_requirements = reduce(
        lambda acc_set, req_set: acc_set.union(req_set),
        extras_require_sets.values(),
        common_imports,
    )
    missing_reqs = (
        set(_get_required_packages_for_imports(requirements.keys()))
        - all_tracked_requirements
    )
    log.debug(
        "Adding missing requirements %s to common_imports",
        sorted(list(missing_reqs)),
    )
    common_imports = common_imports.union(missing_reqs)

    # Add a special "all" group to the extras_require that will install all deps
    # needed for all extras
    if _ALL_GROUP not in extras_require_sets:
        all_reqs = all_tracked_requirements.union(missing_reqs)
        log.debug("Adding [%s] requirement group: %s", _ALL_GROUP, all_reqs)
        extras_require_sets[_ALL_GROUP] = all_reqs

    # Map all dependencies through those listed in requirements.txt
    standardized_requirements = {
        key.replace("-", "_"): val for key, val in requirements.items()
    }
    return _map_requirements(standardized_requirements, common_imports), {
        set_name: _map_requirements(standardized_requirements, import_set)
        for set_name, import_set in extras_require_sets.items()
    }
