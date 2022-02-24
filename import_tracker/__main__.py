"""
This main entrypoint allows import_tracker to run as an independent script to
track the imports for a given module.

Example Usage:

# Track a single module
python -m import_tracker --name my_library

# Track a module and all of the sub-modules it contains
python -m import_tracker --name my_library --recursive --num_jobs 2

# Track a module with relative import syntax
python -m import_tracker --name .my_sub_module --package my_library
"""

# Standard
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType
from typing import Optional, Set
import argparse
import importlib
import json
import logging
import os
import sys
import traceback

# Local
from .constants import THIS_PACKAGE
from .import_tracker import track_module
from .log import log

## Implementation Details ######################################################

# The path where global modules are found
_std_lib_dir = os.path.realpath(os.path.dirname(os.__file__))


def _get_import_parent_path(mod) -> str:
    """Get the parent directory of the given module"""
    # Some standard libs have no __file__ attribute
    if not hasattr(mod, "__file__"):
        return _std_lib_dir

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
        and os.path.splitext(mod.__file__)[-1] not in [".so", ".dylib"]
        and mod_name.split(".")[0] != THIS_PACKAGE
    }


class _DeferredModule(ModuleType):
    """A _DeferredModule is a module subclass that wraps another module but imports
    it lazily and then aliases __getattr__ to the lazily imported module.
    """

    def __init__(self, name: str):
        """Hang onto the import args to use lazily"""
        self.__name = name
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
                    "Not triggering load of [%s] for getattr(%s)", self.name, name
                )
                return None

            log.debug1("Triggering lazy import for %s.%s", self.name, name)
            self.do_import()

        return getattr(self.__wrapped_module, name)

    @property
    def imported(self) -> bool:
        """Return whether or not this module has actually imported"""
        return self.__wrapped_module is not None

    @property
    def name(self) -> str:
        """Expose the name of this module"""
        return self.__name

    def do_import(self):
        """Trigger the import"""
        if log.level <= logging.DEBUG4:
            for line in traceback.format_stack():
                log.debug4(line.strip())

        # Remove this module from sys.modules and re-import it
        log.debug2("Clearing sys.modules of parents of [%s]", self.name)
        self_mod_name_parts = self.name.split(".")
        popped_mods = {}
        for i in range(1, len(self_mod_name_parts) + 1):
            pop_mod_name = ".".join(self_mod_name_parts[:i])
            sys_mod = sys.modules.get(pop_mod_name)
            if isinstance(sys_mod, self.__class__) and not sys_mod.imported:
                log.debug2("Removing sys.modules[%s]", pop_mod_name)
                popped_mods[pop_mod_name] = sys.modules.pop(pop_mod_name)

        log.debug2("Performing deferred import of [%s]", self.name)
        self.__wrapped_module = importlib.import_module(self.name)
        log.debug2("Done with deferred import of [%s]", self.name)

        # Re-decorate the popped mods to fix existing references
        for popped_mod_name, popped_mod in popped_mods.items():
            updated_mod = sys.modules.get(popped_mod_name)
            assert updated_mod, f"No re-imported version of [{popped_mod_name}] found"
            popped_mod.__dict__.update(updated_mod.__dict__)

    def referenced_by(self, module_name: str) -> bool:
        """Determine if this deferred module is referenced by the module with
        the given name
        """
        # Get the module in question
        assert (
            module_name in sys.modules
        ), f"Programming error: Ref module not found {module_name}"
        ref_module = sys.modules[module_name]
        ref_module_pkg = module_name.split(".")[0]

        # Search through the tree of attrs starting at this reference module to
        # see if any holds a reference
        mods_to_check = [ref_module]
        checked_modules = []
        while mods_to_check:
            next_mods_to_check = []
            for mod in mods_to_check:
                for attr in vars(mod).values():
                    if attr is self:
                        return True

                next_mods_to_check.extend(
                    [
                        attr
                        for attr in vars(mod).values()
                        if isinstance(attr, ModuleType)
                        and attr.__spec__.name.startswith(ref_module_pkg)
                        and mod not in checked_modules
                    ]
                )

                checked_modules.append(mod)
            mods_to_check = next_mods_to_check

        return False


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
                log.debug2("Removing lazy module [%s]", mod_name)
                del sys.modules[mod_name]

        # Check to see if the tracked module has finished importing and take a
        # snapshot of the sys.modules if so
        if self._ending_modules is None and not getattr(
            getattr(sys.modules.get(self._tracked_module, {}), "__spec__", {}),
            "_initializing",
            True,
        ):
            log.debug("Tracked module [%s] finished importing", self._tracked_module)
            self._set_ending_modules(fullname)
            log.debug2("Ending modules: %s", self._ending_modules)

        # If downstream (inclusive) of the tracked module, let everything import
        # cleanly as normal by deferring to the real finders
        log.debug3("Allowing import of [%s]", fullname)
        return None

    def get_all_new_modules(self) -> Set[str]:
        """Get all of the imports that have happened since the start"""
        assert self._starting_modules is not None, f"Target module never impoted!"
        if self._ending_modules is None:
            self._set_ending_modules()
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

    def _set_ending_modules(self, trigger_module_name: Optional[str] = None):
        """Set the ending module set for the target"""

        # Avoid infinite recursion by setting _ending_modules to a preliminary
        # empty set
        self._ending_modules = {}

        # Find all attributes on existing modules which are themselves deferred
        # modules and trigger their imports. This fixes the case where a module
        # imports a sibling's attribute which was previously imported and
        # deferred
        deferred_attrs = []
        while True:
            for mod_name, mod in list(sys.modules.items()):
                if mod_name.startswith(self._tracked_module.split(".")[0]):
                    for attr_name, attr in vars(mod).items():
                        if (
                            isinstance(attr, _DeferredModule)
                            and not attr.imported
                            and attr.referenced_by(self._tracked_module)
                        ):
                            deferred_attrs.append((mod_name, attr_name, attr))
            if not deferred_attrs:
                break
            for mod_name, attr_name, attr in deferred_attrs:
                log.debug2("Finalizing deferred import for %s.%s", mod_name, attr_name)
                attr.do_import()
                log.debug2(
                    "Done finalizing deferred import for %s.%s", mod_name, attr_name
                )
            deferred_attrs = []

        # Capture the set of imports in sys.modules (excluding the module that
        # triggered this)
        self._ending_modules = set(sys.modules.keys()) - {trigger_module_name}


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

    # Determine the unqualified module name and use it elsewhere
    full_module_name = args.name
    if args.package is not None:
        assert args.name.startswith(
            "."
        ), "When providing --package, module name must be relative (start with '.')"
        full_module_name = f"{args.package}{args.name}"

    # Create the tracking meta finder
    tracker_finder = ImportTrackerMetaFinder(full_module_name)
    sys.meta_path = [tracker_finder] + sys.meta_path

    # Do the import
    log.debug("Importing %s", full_module_name)
    try:
        imported = importlib.import_module(full_module_name)
    except Exception as err:
        log.error("Error on top-level import [%s]: %s", full_module_name, err)
        raise

    # Set up the mapping with the external downstreams for the tracked package
    downstream_mapping = {
        full_module_name: _get_non_std_modules(tracker_finder.get_all_new_modules())
    }

    # If recursing, do so now by spawning a subprocess for each internal
    # downstream. This must be done in a separate interpreter instance so that
    # the imports are cleanly reset for each downstream.
    if args.recursive:
        all_internals = [
            downstream
            for downstream in sys.modules.keys()
            if downstream.startswith(full_module_name)
            and downstream != full_module_name
        ]

        # Create the thread pool to manage the subprocesses
        if args.num_jobs > 0:
            pool = ThreadPoolExecutor(max_workers=args.num_jobs)
            futures = []
            for internal_downstream in all_internals:
                futures.append(
                    pool.submit(
                        track_module,
                        module_name=internal_downstream,
                        log_level=log_level,
                        recursive=False,
                    )
                )

            # Wait for all futures to complete and merge into the mapping
            for future in futures:
                downstream_mapping.update(future.result())

        else:
            for internal_downstream in all_internals:
                try:
                    log.debug(
                        "Starting sub-module tracking for [%s]", internal_downstream
                    )
                    downstream_mapping.update(
                        track_module(
                            module_name=internal_downstream,
                            log_level=log_level,
                            recursive=False,
                        )
                    )
                # This is useful for catching errors caused by unexpected corner
                # cases. If it's triggered, it's a sign of a bug in the library,
                # so we don't have ways to explicitly exercise this in tests.
                except Exception as err:  # pragma: no cover
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


if __name__ == "__main__":
    main()
