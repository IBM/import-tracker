"""
This main entrypoint is used as an implementation detail for tracking the deps
of individual modules. The challenge is that projects which use multiple tracked
imports need to track them in isolation to avoid cross-contaminating the
dependency sets. This entrypoint solves that by running a _single_ import in
tracking mode and reporting the results. This is then run as a subprocess from
the import_module implementation when running in TRACKING mode.
"""

# Standard
from typing import Set
import argparse
import importlib
import inspect
import json
import logging
import os
import sys

# Local
from .log import log

## Implementation Details ######################################################

# The path where global modules are found
_std_lib_dir = os.path.realpath(os.path.dirname(os.__file__))

_has_splittable_file_attr = lambda mod: hasattr(mod, "__file__") and isinstance(
    mod.__file__, str
)


def _get_import_parent_path(mod) -> str:
    """Get the parent directory of the given module"""
    # Some standard libs have no __file__ attribute
    if not hasattr(mod, "__file__"):
        return _std_lib_dir

    # In some cases, we might have __file__ set, but it may be some other value; for the case
    # of namespace packages, this might be set to None, which is the default value.
    # ref: https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec.origin
    if not _has_splittable_file_attr(mod):
        return None

    # If the module comes from an __init__, we need to pop two levels off
    file_path = mod.__file__
    if os.path.splitext(os.path.basename(mod.__file__))[0] == "__init__":
        file_path = os.path.dirname(file_path)
    parent_path = os.path.dirname(file_path)
    return parent_path


def _get_non_std_modules() -> Set[str]:
    """Take a snapshot of the non-standard modules currently imported"""
    this_module = sys.modules[__name__].__package__
    return {
        mod_name.split(".")[0]
        for mod_name, mod in sys.modules.items()
        if not mod_name.startswith("_")
        and "." not in mod_name
        and _get_import_parent_path(mod) != _std_lib_dir
        and _has_splittable_file_attr(mod)
        and os.path.splitext(mod.__file__)[-1] not in [".so", ".dylib"]
        and mod_name.split(".")[0] != this_module
    }


class _LoggingMetaFinder(importlib.abc.MetaPathFinder):
    """Metafinder that simply logs the stack that is requesting the import of
    the given package
    """

    def __init__(self, package_name: str):
        """Construct with the name of the package being tracked"""
        self._package_name = package_name
        self._inspected_pacakges = []

    def find_spec(self, fullname, path, *args, **kwargs):
        """The primary metafinder inteface function"""
        log.debug4("Looking for [fullname: %s, path: %s]", fullname, path)

        # If this is the first time we've seen this top-level package, inspect
        # the path
        search_pkg_name = fullname.split(".")[0]
        if search_pkg_name not in self._inspected_pacakges:
            self._inspected_pacakges.append(search_pkg_name)

            # Get the stack trace and prune out importlib
            stack = inspect.stack()
            non_importlib_mods = list(
                filter(
                    lambda x: x.split(".")[0] != "importlib",
                    [frame.frame.f_globals["__name__"] for frame in stack],
                )
            )
            log.debug3(
                "[%s] Import stack for [%s]: %s",
                self._package_name,
                search_pkg_name,
                non_importlib_mods,
            )

        return None


def _setup_logging_meta_finder(package_name: str):
    """Put a new metafinder at the front of the list that will simply log out
    the stack that is requesting the import of a given package
    """
    sys.meta_path = [_LoggingMetaFinder(package_name)] + sys.meta_path


## Main ########################################################################


def main():
    """Main entrypoint as a function"""

    # Set up the args
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", "-n", help="Module name to import", required=True)
    parser.add_argument(
        "--package",
        "-p",
        help="Package for relative imports",
        default=None,
    )
    parser.add_argument(
        "--indent",
        "-i",
        type=int,
        help="Indent for json printing",
        default=None,
    )
    parser.add_argument(
        "--log_level",
        "-l",
        type=int,
        help="Log level",
        default=logging.ERROR,
    )
    args = parser.parse_args()

    # Set the level on the shared logger
    logging.basicConfig(level=args.log_level)

    # Inject the "tracking" finder that will report the stack that triggers each
    # import if the log level is high enough
    if args.log_level <= logging.DEBUG - 3:
        _setup_logging_meta_finder(args.name)

    # Do the import
    log.debug("Importing %s.%s", args.package, args.name)
    imported = importlib.import_module(args.name, package=args.package)

    # Get the set of non-standard modules after the import and filter out any
    # modules that are parents of the target module itself
    parent_mod_name = imported.__name__.split(".")[0]
    log.debug2("Parent module name: %s", parent_mod_name)
    non_std_modules = _get_non_std_modules()
    log.debug3("Non standard modules: %s", non_std_modules)
    module_deps = sorted(
        list(
            filter(
                lambda mod: mod != parent_mod_name and mod is not None,
                non_std_modules,
            )
        )
    )
    log.debug("Module deps for %s: %s", imported.__name__, module_deps)

    # Print out the json dump
    print(json.dumps({imported.__name__: module_deps}, indent=args.indent))


if __name__ == "__main__":  # pragma: no cover
    main()
