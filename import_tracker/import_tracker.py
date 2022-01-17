"""
This module implements utilities that enable tracking of third party deps
through import statements
"""

# Standard
from contextlib import contextmanager
from types import ModuleType
from typing import Dict, Iterable, List, Optional
import copy
import importlib
import inspect
import json
import os
import re
import shlex
import subprocess
import sys
import warnings

# Local
from .lazy_import_errors import lazy_import_errors

## Public Globals ##############################################################

# Possible import modes
LAZY = "LAZY"
BEST_EFFORT = "BEST_EFFORT"
PROACTIVE = "PROACTIVE"
TRACKING = "TRACKING"

# The env var used to check the mode
MODE_ENV_VAR = "IMPORT_TRACKER_MODE"

## Impl Globals ################################################################

# This global holds the current default import mode when not provided in the
# environment. This may be updated with the default_import_mode contextmanager.
_default_import_mode = BEST_EFFORT
_all_import_modes = [LAZY, BEST_EFFORT, PROACTIVE, TRACKING]

# The global mapping from modules to dependencies
_module_dep_mapping = {}

# Lazily created global mapping from module name to package name
_module_to_pkg = None

# Exprs for finding module names
_pkg_version_expr = re.compile("-[0-9]")
_pkg_name_expr = re.compile("^Name: ([^ \t\n]+)")

# Global mapping of filenames for static tracking files for individual modules
_static_trackers = {}

## Public ######################################################################


def set_static_tracker(fname: Optional[str] = None):
    """This call initializes a static tracking file for the calling module. If
    a fname is given, that file will be used explicitly. If not, a filename will
    be deduced based on the path to the calling module.
    """
    # Get a handle to the module that is calling this function
    calling_package = _get_calling_package()
    assert calling_package is not None, "Degenerate call stack with no calling module"
    assert hasattr(calling_package, "__name__"), f"Calling module has no __name__"

    # Figure out the filename if not given
    if fname is None:
        assert hasattr(
            calling_package, "__file__"
        ), f"Cannot use default static tracker for module {calling_package.__name__} with no __file__"
        fname = os.path.realpath(
            os.path.join(
                os.path.dirname(calling_package.__file__),
                "__static_import_tracker__.json",
            ),
        )

    # Map the calling package name to the final file name in the global mapping of tracked modules
    global _static_trackers
    _static_trackers[calling_package.__name__] = fname


def import_module(name: str, package: Optional[str] = None) -> ModuleType:
    """Import a module by name and keep track of the changes in the global
    modules dict
    """

    # If this module is already imported, just return it
    if name in sys.modules:
        return sys.modules[name]

    # Get the current import mode
    import_mode = _get_import_mode()

    # If not running in TRACKING mode, load the static tracker if available
    if import_mode in [PROACTIVE, LAZY, BEST_EFFORT]:
        _load_static_tracker()

    # If performing a PROACTIVE import, import directly and return
    if import_mode == PROACTIVE:
        return importlib.import_module(name, package)

    # If performing a BEST_EFFORT import, do the import, but wrap it with lazy
    # error semantics
    elif import_mode == BEST_EFFORT:
        with lazy_import_errors():
            return importlib.import_module(name, package)

    # If we're doing a TRACKING import. In this case, we're going to perform the
    # the tracking in a subprocess and then return a lazy importer
    if import_mode == TRACKING:
        _track_deps(name, package)

    # For either LAZY or TRACKING, we return a Lazy Importer
    return LazyModule(name, package)


def get_required_imports(name: str) -> List[str]:
    """Get the set of modules that are required for the given module by name. If
    the module is not known, ImportError is raised
    """
    if name not in _module_dep_mapping:
        raise ValueError(f"Cannot get required imports for untracked module [{name}]")
    return _module_dep_mapping[name]


def get_required_packages(name: str) -> List[str]:
    """Get the set of installable packages required by this names module"""
    return _get_required_packages_for_imports(get_required_imports(name))


def get_tracked_modules(prefix: str = "") -> List[str]:
    """Get all tracked modules whose name starts with the given prefix.
    Libraries which implement static tracking can use this to determine the full
    set of tracked modules in a central location.
    """
    return [name for name in _module_dep_mapping if name.startswith(prefix)]


@contextmanager
def default_import_mode(import_mode: str):
    """This contextmanager will set the default import mode and then reset it on
    exit.

    Args:
        import_mode:  str
            The import mode to set it to inside of the context
    """
    if import_mode not in _all_import_modes:
        raise ValueError(
            f"Invalid import mode <{import_mode}>. Options are: {_all_import_modes}"
        )
    global _default_import_mode
    previous_mode = _default_import_mode
    _default_import_mode = import_mode
    yield
    _default_import_mode = previous_mode


## Implementation Details ######################################################


def _get_import_mode():
    """Get the import mode based on the current default and the environment"""
    return os.environ.get(MODE_ENV_VAR, _default_import_mode)


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
            self.__wrapped_module = importlib.import_module(
                self.__name,
                self.__package,
            )
        return getattr(self.__wrapped_module, name)


def _track_deps(name: str, package: Optional[str] = None):
    """This function is used to track the dependencies needed for an individual
    module. It does this by launching a subprocess to import that dependency in
    isolation and merges the reported results into the global mapping.
    """

    # Run this package as a subprocess and collect the results
    cmd = "{} -W ignore -m {} --name {}".format(
        sys.executable,
        sys.modules[__name__].__package__,
        name,
    )
    if package is not None:
        cmd += f" --package {package}"
    env = dict(copy.deepcopy(os.environ))
    env[MODE_ENV_VAR] = LAZY
    env["PYTHONPATH"] = ":".join(sys.path)
    res = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, env=env)
    assert res.returncode == 0, f"Failed to track {name}"
    deps = json.loads(res.stdout)

    # Merge the results into the global mapping
    global _module_dep_mapping
    _module_dep_mapping.update(deps)

    # If configured, add the results to the static tracking file
    calling_package = _get_calling_package()
    static_tracker = _static_trackers.get(calling_package.__name__)
    if static_tracker is not None:
        static_content = {}
        if os.path.exists(static_tracker):
            with open(static_tracker, "r") as handle:
                static_content = json.load(handle)
        static_content.update(deps)
        with open(static_tracker, "w") as handle:
            handle.write("{}\n".format(json.dumps(static_content, indent=2)))


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
                                and os.path.splitext(mn)[-1]
                                not in [".pth", ".dist-info", ".egg-info"]
                                and "." not in mn
                            ),
                            {
                                line.split("/")[0].split(",")[0].strip()
                                for line in handle.readlines()
                            },
                        ),
                    ):
                        modules_to_package_names.setdefault(modname, set()).add(
                            _standardize_package_name(package_name)
                        )

    return modules_to_package_names


def _get_calling_package() -> ModuleType:
    """Get a handle to the base package for the module that is calling this
    library. This will search through the stack to find the first module outside
    of this library.
    """
    this_pkg = sys.modules[__name__].__name__.split(".")[0]
    for frame in inspect.stack():
        mod = sys.modules[frame.frame.f_globals["__name__"]]
        mod_pkg = mod.__name__.split(".")[0]
        if mod_pkg != this_pkg:
            return sys.modules[mod_pkg]
    assert False, "Degenerate stack with no parent module"  # pragma: no cover


def _load_static_tracker():
    """If configured, load static tracker information for the given package"""
    calling_package = _get_calling_package()
    static_tracker = _static_trackers.get(calling_package.__name__)
    if static_tracker is not None:
        if not os.path.isfile(static_tracker):
            warnings.warn(
                f"Static tracking not initialized for [{calling_package.__name__}]. "
                + f"If you are the maintainer, please run with {MODE_ENV_VAR}={TRACKING} "
                + "and commit the resulting file. If you are a user, please file a bug "
                + "report with the library maintainers."
            )
            return
        with open(static_tracker, "r") as handle:
            global _module_dep_mapping
            _module_dep_mapping.update(json.load(handle))


def _standardize_package_name(raw_package_name):
    """Helper to convert the arbitrary ways packages can be represented to a
    common (matchable) representation
    """
    return raw_package_name.strip().lower().replace("-", "_")


def _get_required_packages_for_imports(imports: Iterable[str]) -> List[str]:
    """Get the set of installable packages required by this list of imports"""
    # Lazily create the global mapping
    global _module_to_pkg
    if _module_to_pkg is None:
        _module_to_pkg = _map_modules_to_package_names()

    # Merge the required packages for each
    required_pkgs = set()
    for mod in imports:
        # If there is a known mapping, use it
        if mod in _module_to_pkg:
            required_pkgs.update(_module_to_pkg[mod])

        # Otherwise, assume that the name of the module is itself the name of
        # the package
        else:
            required_pkgs.add(mod)
    return sorted(list(required_pkgs))
