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
from typing import Set
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

_has_splittable_file_attr = lambda mod: hasattr(mod, "__file__") and isinstance(
    mod.__file__, str
)

# The name of this package
_this_pkg = sys.modules[__name__].__package__


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
    """The _DeferredModule is used to defer imports of modules which are not
    part of the tracking tree for the target library. It does its best to avoid
    actually importing the target module, but if the target module does in fact
    use a deferred module, it will be actively imported.
    """

    def __init__(self, spec, finder_args, finder_kwargs):
        """Initialize with the args given to the finder so that the real finders
        can be used when the module actually needs to be imported
        """
        self.__spec = spec
        self.__finder_args = finder_args
        self.__finder_kwargs = finder_kwargs
        self.__wrapped_module = None
        log.debug3("Done constructing lazy module for %s", self.__spec.name)

    def __getattr__(self, name: str) -> any:
        """When asked for an attribute, make sure the wrapped module is imported
        and then delegate
        """

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
                "Not triggering load of [%s] for getattr(%s)", self.__spec.name, name
            )
            return None

        if self.__wrapped_module is None:
            log.debug1("Triggering lazy import for %s", self.__spec.name)
            if log.level <= logging.DEBUG4:
                for line in traceback.format_stack():
                    log.debug4(line.strip())

            # Iterate through all of the `sys.meta_path` finders _except_ the
            # tracking finder and see if we can find a loader that is valid
            for meta_finder in sys.meta_path:
                if not isinstance(meta_finder, ImportTrackerMetaFinder):
                    spec = meta_finder.find_spec(
                        *self.__finder_args, **self.__finder_kwargs
                    )
                    if spec is not None:
                        log.debug3(
                            "Found valid spec for [%s] from %s",
                            self.__spec.name,
                            meta_finder,
                        )
                        self.__wrapped_module = importlib.util.module_from_spec(spec)
                        break

        return getattr(self.__wrapped_module, name)


class _DeferredLoader(importlib.abc.Loader):
    """The _DeferredLoader is used when the tracking finder determines that the
    given module is not on the critical path for the target module.
    """

    def __init__(self, finder_args, finder_kwargs):
        """Initialize with the args given to the finder so that the real finders
        can be used when the module actually needs to be imported
        """
        self._finder_args = finder_args
        self._finder_kwargs = finder_kwargs

    def create_module(self, spec):
        log.debug3("Creating lazy module for %s", spec.name)
        return _DeferredModule(spec, self._finder_args, self._finder_kwargs)

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
        self._import_mapping = {}

    def find_spec(self, fullname: str, *args, **kwargs) -> None:
        """The find_spec implementation for this finder will never return a
        valid Spec. Instead, it simply uses this as a hook to track the stack
        when a given import is requested.

        https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.find_spec

        Args:
            fullname:  str
                The fully qualified module name under import

        Returns:
            result:  None
                This finder always returns None to defer to the rest of the
                meta_path finders once the import has been tracked
        """

        # Get the stack trace and determine if this module is directly below
        # a module within the tracked package (may itself be a tracked package
        # module)
        stack = inspect.stack()
        non_importlib_mods = list(
            filter(
                lambda x: x.split(".")[0] not in ["importlib", "__main__"],
                [frame.frame.f_globals["__name__"] for frame in stack],
            )
        )
        if not non_importlib_mods:
            return None
        log.debug3("[%s] Non importlib mods: %s", fullname, non_importlib_mods)
        upstream_module = non_importlib_mods[0]
        log.debug3("[%s] Upstream mod: %s", fullname, upstream_module)

        # If the upstream is the tracked package, populate the tree
        if self._in_tracked_module(upstream_module):
            log.debug2("Adding [%s] <- [%s]", fullname, upstream_module)
            self._import_mapping.setdefault(upstream_module, set()).add(fullname)

        # If this package is not on the critical path for the target module,
        # we defer it with a lazy module, otherwise we return None to indicate
        # that the real loader should do its job
        lazy_load = not (
            self._in_tracked_module(fullname)
            or self._contains_tracked_module(fullname)
            or self._tracked_module in non_importlib_mods
        )
        log.debug2("[%s] Lazy load? %s", fullname, lazy_load)

        # If lazy loading, "find" the module with a lazy loader
        if lazy_load:
            loader = _DeferredLoader(
                finder_args=tuple([fullname] + list(args)),
                finder_kwargs=kwargs,
            )
            return importlib.util.spec_from_loader(fullname, loader)

        # Explicitly return None for pedanticism!
        return None

    def get_all_downstreams(
        self,
        fullname: str,
        include_internal: bool = False,
    ) -> Set[str]:
        """Recursively fill in the downstreams for the given module based on the
        mapping built at import time

        Args:
            fullname:  str
                The fully-qualified name of the module to fetch downstreams for
            include_internal:  bool
                Include the names of other packages inside of the tracked
                package that are needed by the target package

        Returns:
            downstreams:  Set[str]
                The set of unique import module names required downstream from
                the requested module
        """
        return self._get_all_downstreams(fullname, include_internal, set())

    ## Implementation Details ##

    def _in_tracked_module(self, mod_name: str) -> bool:
        """Determine if the given module is contained within the tracked module"""
        mod_name_parts = mod_name.split(".")
        return (
            mod_name_parts[: len(self._tracked_module_parts)]
            == self._tracked_module_parts
        )

    def _contains_tracked_module(self, mod_name: str) -> bool:
        """Determine if the given module is a parent of the tracked module"""
        mod_name_parts = mod_name.split(".")
        return self._tracked_module_parts[: len(mod_name_parts)] == mod_name_parts

    def _get_all_downstreams(
        self,
        fullname: str,
        include_internal: bool,
        all_downstreams: Set[str],
    ) -> Set[str]:
        """Recursive implementation of get_all_downstreams"""

        # Find the direct downstreams of this module
        downstreams = self._import_mapping.get(fullname, set())
        log.debug4("Raw downstreams for [%s]: %s", fullname, downstreams)

        # Iterate through any downstreams that we haven't already seen and
        # recursively add them to the set of downstreams for this module
        new_downstreams = downstreams - all_downstreams
        log.debug4("New downstreams for [%s]: %s", fullname, new_downstreams)
        all_downstreams = all_downstreams.union(downstreams)
        for downstream in new_downstreams:
            all_downstreams = all_downstreams.union(
                self._get_all_downstreams(downstream, include_internal, all_downstreams)
            )

        # If not including internal dependencies, strip those out
        if not include_internal:
            all_downstreams = {
                mod for mod in all_downstreams if not self._in_tracked_module(mod)
            }
        return all_downstreams


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
        default=None,
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
    imported = importlib.import_module(args.name, package=args.package)

    # Set up the mapping with the external downstreams for the tracked package
    downstream_mapping = {
        args.name: _get_non_std_modules(tracker_finder.get_all_downstreams(args.name))
    }

    # If recursing, do so now by spawning a subprocess for each internal
    # downstream. This must be done in a separate interpreter instance so that
    # the imports are cleanly reset for each downstream.
    if args.recursive:
        all_downstreams = tracker_finder.get_all_downstreams(
            args.name, include_internal=True
        )
        all_internals = [
            downstream
            for downstream in all_downstreams
            if downstream.startswith(args.name)
        ]

        # Create the thread pool to manage the subprocesses
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
