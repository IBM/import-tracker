"""
This main entrypoint is used as an implementation detail for tracking the deps
of individual modules. The challenge is that projects which use multiple tracked
imports need to track them in isolation to avoid cross-contaminating the
dependency sets. This entrypoint solves that by running a _single_ import in
tracking mode and reporting the results. This is then run as a subprocess from
the import_module implementation when running in TRACKING mode.
"""

# Standard
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType
from typing import List, Optional, Set
import argparse
import copy
import importlib
import inspect
import json
import logging
import os
import shlex
import subprocess
import sys
import traceback

# Local
from .log import log

## Implementation Details ######################################################

# The path where global modules are found
_std_lib_dir = os.path.realpath(os.path.dirname(os.__file__))

# The name of this package
_this_pkg = sys.modules[__name__].__package__


def _has_splittable_file_attr(mod) -> bool:
    """Determine if the given module has a __file__ attr that can be manipulated"""
    return hasattr(mod, "__file__") and isinstance(mod.__file__, str)


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


def _get_non_std_modules(mod_names: Set[str]) -> Set[str]:
    """Take a snapshot of the non-standard modules currently imported"""

    return {
        mod_name.split(".")[0]
        for mod_name, mod in sys.modules.items()
        if mod_name in mod_names
        and not mod_name.startswith("_")
        and "." not in mod_name
        and _get_import_parent_path(mod) != _std_lib_dir
        and _has_splittable_file_attr(mod)
        and os.path.splitext(mod.__file__)[-1] not in [".so", ".dylib"]
        and mod_name.split(".")[0] != _this_pkg
    }


class _DeferredModule(ModuleType):
    """A _DeferredModule is a module subclass that wraps another module but imports
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

            # If this is one of the special attributes accessed during the import
            # we'll just return None and not trigger the import
            if name in [
                "__name__",
                "__loader__",
                "__package__",
                "__path__",
                "__file__",
                "__cached__",
            ]:
                log.debug4(
                    "Not triggering load of [%s] for getattr(%s)", self.__name, name
                )
                return None

            log.debug1(
                "Triggering lazy import for %s.%s.%s", self.__package, self.__name, name
            )
            self.do_import()

        return getattr(self.__wrapped_module, name)

    def do_import(self):
        """Trigger the import"""
        if self.__wrapped_module is not None:
            return

        if log.level <= logging.DEBUG4:
            for line in traceback.format_stack():
                log.debug4(line.strip())

        # Remove this module from sys.modules and re-import it
        self_mod_name = self.__spec__.name
        log.debug2("Clearing sys.modules of parents of [%s]", self_mod_name)
        self_mod_name_parts = self_mod_name.split(".")
        popped_mods = {}
        for i in range(1, len(self_mod_name_parts) + 1):
            pop_mod_name = ".".join(self_mod_name_parts[:i])
            if isinstance(sys.modules.get(pop_mod_name), self.__class__):
                log.debug2("Removing sys.modules[%s]", pop_mod_name)
                popped_mods[pop_mod_name] = sys.modules.pop(pop_mod_name)

        self.__wrapped_module = importlib.import_module(
            self.__name,
            self.__package,
        )

        # Re-decorate the popped mods to fix existing references
        for popped_mod_name, popped_mod in popped_mods.items():
            updated_mod = sys.modules.get(popped_mod_name)
            assert updated_mod, f"No re-imported version of [{popped_mod_name}] found"
            popped_mod.__dict__.update(updated_mod.__dict__)


class _LazyLoader(importlib.abc.Loader):
    """This "loader" can be used with a MetaFinder to catch not-found modules
    and raise a ModuleNotFound error lazily when the module is used rather than
    at import time.
    """

    def create_module(self, spec):
        return _DeferredModule(spec.name)

    def exec_module(self, *_, **__):
        """Nothing to do here because the errors will be thrown by the module
        created in create_module
        """


class ImportTrackerMetaFinder(importlib.abc.MetaPathFinder):
    """The ImportTrackerMetaFinder is a meta finder that is intended to be used
    at the front of the sys.meta_path to automatically track the imports for a
    given library. It does this by looking at the call stack when a given import
    is requested and tracking the upstream for each import made inside of the
    target package.

    NOTE: Since a stack trace is traversed on every import, this is very slow
        and is intended only for a static build-time operation and should not be
        used during the import phase of a library at runtime!
    """

    def __init__(self, tracked_module: str):
        """Initialize with the name of the package being tracked

        Args:
            tracked_module:  str
                The name of the module (may be nested) being tracked
        """
        self._tracked_module = tracked_module
        self._tracked_module_parts = tracked_module.split(".")
        self._enabled = True
        self._starting_modules = set(sys.modules.keys())
        log.debug2("Starting modules: %s", self._starting_modules)
        self._ending_modules = None
        self._deferred_modules = set()

    def find_spec(
        self, fullname: str, *args, **kwargs
    ) -> Optional[importlib.machinery.ModuleSpec]:
        """The find_spec implementation for this finder tracks the source of the
        import call for the given module and determines if it is on the critical
        path for the target module.

        https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.find_spec

        Args:
            fullname:  str
                The fully qualified module name under import

        Returns:
            spec:  Optional[importlib.machinery.ModuleSpec]
                If the desired import is not on the critical path for the target
                module, a spec with a _DeferredLoader will be returned. If the
                import is on the critical path, None will be returned to defer
                to the rest of the "real" finders.
        """

        # We want to lazy load this module if it's not on the critical path for
        # the target module. We define the critical path as:
        #
        #   - Modules that are direct parents of the target
        #   - Modules that are themselves downstream of the target
        #   - The target itself

        # If this finder is enabled and the requested import is not the target,
        # defer it with a lazy module
        if (
            self._enabled
            and fullname != self._tracked_module
            and not self._is_parent_module(fullname)
            and fullname not in self._deferred_modules
            and fullname.split(".")[0] == self._tracked_module_parts[0]
        ):
            log.debug3("Deferring import of [%s]", fullname)
            self._deferred_modules.add(fullname)
            loader = _LazyLoader()
            return importlib.util.spec_from_loader(fullname, loader)

        # If this is the target, disable this finder for future imports
        if fullname == self._tracked_module:
            log.debug(
                "Tracked module [%s] found. Tracking started", self._tracked_module
            )
            self._enabled = False

            # Remove all lazy modules from sys.modules to force them to be
            # reimported
            lazy_modules = [
                mod_name
                for mod_name, mod in sys.modules.items()
                if isinstance(mod, _DeferredModule)
            ]
            for mod_name in lazy_modules:
                del sys.modules[mod_name]

        # Check to see if the tracked module has finished importing and take a
        # snapshot of the sys.modules if so
        if self._ending_modules is None and not getattr(
            getattr(sys.modules.get(self._tracked_module, {}), "__spec__", {}),
            "_initializing",
            True,
        ):
            log.debug("Tracked module [%s] finished importing", self._tracked_module)
            self._ending_modules = set(sys.modules.keys()) - {fullname}
            log.debug2("Ending modules: %s", self._ending_modules)

        # If there are any upstream modules from the target fullname that are
        # lazy, trigger their active imports
        log.debug3("Allowing import of [%s]", fullname)
        name_parts = fullname.split(".")
        for i in range(1, len(name_parts) + 1):
            parent_mod_name = ".".join(name_parts[:i])
            parent_mod = sys.modules.get(parent_mod_name)
            if isinstance(parent_mod, _DeferredModule):
                log.debug3("Triggering parent import for [%s]", parent_mod_name)
                parent_mod.do_import()

        # If downstream (inclusive) of the tracked module, let everything import
        # cleanly as normal by deferring to the real finders
        return None

    def get_all_new_modules(self) -> Set[str]:
        """Get all of the imports that have happened since the start"""
        assert self._starting_modules is not None, f"Target module never impoted!"
        if self._ending_modules is None:
            self._ending_modules = set(sys.modules.keys())
        return {
            mod
            for mod in self._ending_modules - self._starting_modules
            if not self._is_parent_module(mod)
        }

    ## Implementation Details ##

    def _is_parent_module(self, fullname: str) -> bool:
        """Determine if the given module fullname is a direct parent of the
        tracked module
        """
        parts = fullname.split(".")
        return self._tracked_module_parts[: len(parts)] == parts


def track_sub_module(sub_module_name, package_name, log_level):
    """This function is intended to run inside of a ThreadPoolExecutor and will
    launch a subprocess to ensure that the tracking happens in isolation
    """
    # Set up the environment with all sys.paths available (included those added
    # in code)
    env = dict(copy.deepcopy(os.environ))
    env["PYTHONPATH"] = ":".join(sys.path)

    # Set up the command to run this module
    cmd = cmd = "{} -W ignore -m {} --name {} --log_level {}".format(
        sys.executable,
        _this_pkg,
        sub_module_name,
        log_level,
    )
    if package_name is not None:
        cmd += f" --package {package_name}"

    # Launch the process
    proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, env=env)

    # Wait for the result and parse it as json
    result, _ = proc.communicate()
    return json.loads(result)


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
        help="Log level",
        default=os.environ.get("LOG_LEVEL", "error"),
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively perform tracking on all nested modules",
        default=False,
    )
    parser.add_argument(
        "--num_jobs",
        "-j",
        type=int,
        help="Number of workers to spawn when recursing",
        default=0,
    )
    args = parser.parse_args()

    # Set the level on the shared logger
    log_level = getattr(logging, args.log_level.upper(), None)
    if log_level is None:
        log_level = int(args.log_level)
    logging.basicConfig(level=log_level)

    # Create the tracking meta finder
    tracker_finder = ImportTrackerMetaFinder(args.name)
    sys.meta_path = [tracker_finder] + sys.meta_path

    # Do the import
    log.debug("Importing %s.%s", args.package, args.name)
    try:
        imported = importlib.import_module(args.name, package=args.package)
    except Exception as err:
        log.error("Error on top-level import [%s.%s]: %s", args.package, args.name, err)
        # DEBUG
        # breakpoint()
        raise

    # Set up the mapping with the external downstreams for the tracked package
    downstream_mapping = {
        args.name: _get_non_std_modules(tracker_finder.get_all_new_modules())
    }

    # If recursing, do so now by spawning a subprocess for each internal
    # downstream. This must be done in a separate interpreter instance so that
    # the imports are cleanly reset for each downstream.
    if args.recursive:
        all_internals = [
            downstream
            for downstream in sys.modules.keys()
            if downstream.startswith(args.name)
        ]

        # Create the thread pool to manage the subprocesses
        if args.num_jobs > 0:
            pool = ThreadPoolExecutor(max_workers=args.num_jobs)
            futures = []
            for internal_downstream in all_internals:
                futures.append(
                    pool.submit(
                        track_sub_module, internal_downstream, args.package, log_level
                    )
                )

            # Wait for all futures to complete and merge into the mapping
            for future in futures:
                downstream_mapping.update(future.result())

        else:
            for internal_downstream in all_internals:
                try:
                    downstream_mapping.update(
                        track_sub_module(internal_downstream, args.package, log_level)
                    )
                except Exception as err:
                    log.error(
                        "Error while tracking submodule [%s]: %s",
                        internal_downstream,
                        err,
                    )
                    raise

    # Get all of the downstreams for the module in question, including internals
    log.debug("Downstream Mapping: %s", downstream_mapping)

    # Print out the json dump
    print(
        json.dumps(
            {key: sorted(list(val)) for key, val in downstream_mapping.items()},
            indent=args.indent,
        ),
    )


if __name__ == "__main__":  # pragma: no cover
    main()
