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
import json
import os
import sys

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


def _get_non_std_modules() -> Set[str]:
    """Take a snapshot of the non-standard modules currently imported"""
    this_module = sys.modules[__name__].__package__
    return {
        mod_name.split(".")[0]
        for mod_name, mod in sys.modules.items()
        if not mod_name.startswith("_")
        and "." not in mod_name
        and _get_import_parent_path(mod) != _std_lib_dir
        and os.path.splitext(mod.__file__)[-1] not in [".so", ".dylib"]
        and mod_name.split(".")[0] != this_module
    }


## Main ########################################################################


def main():
    """Main entrypoint as a function"""

    # Set up the args
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", "-n", help="Module name to import", required=True)
    parser.add_argument("--package", "-p", help="Package for relative imports", default=None)
    parser.add_argument("--indent", "-i", type=int, help="Indent for json printing", default=None)
    args = parser.parse_args()

    # Do the import
    imported = importlib.import_module(args.name, package=args.package)

    # Get the set of non-standard modules after the import
    print(json.dumps({imported.__name__: sorted(list(_get_non_std_modules()))}, indent=args.indent))

if __name__ == "__main__":
    main()
