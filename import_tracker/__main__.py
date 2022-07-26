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
import argparse
import json
import logging
import os

# Local
from .import_tracker import track_module

## Main ########################################################################


def main():
    """Main entrypoint as a function"""

    # Set up the args
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name",
        "-n",
        required=True,
        help="Module name to track",
    )
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
        "--submodules",
        "-s",
        nargs="*",
        default=None,
        help="List of subodules to include (all if no value given)",
    )
    parser.add_argument(
        "--track_import_stack",
        "-t",
        action="store_true",
        default=False,
        help="Store the stack trace of imports belonging to the tracked module",
    )
    parser.add_argument(
        "--full_depth",
        "-f",
        action="store_true",
        default=False,
        help="Include transitive third-party deps brought in by direct third-party deps",
    )
    parser.add_argument(
        "--detect_transitive",
        "-d",
        action="store_true",
        default=False,
        help="Detect whether each dependency is 'direct' or 'transitive'",
    )
    parser.add_argument(
        "--show_optional",
        "-o",
        action="store_true",
        default=False,
        help="Show whether each dependency is optional or required",
    )
    parser.add_argument(
        "--log_level",
        "-l",
        default=os.environ.get("LOG_LEVEL", "warning"),
        help="Default log level",
    )
    args = parser.parse_args()

    # Determine the submodules argument value
    submodules = (
        False
        if args.submodules is None
        else (args.submodules if args.submodules else True)
    )

    # Set the level on the shared logger
    log_level = getattr(logging, args.log_level.upper(), None)
    if log_level is None:
        log_level = int(args.log_level)
    logging.basicConfig(level=log_level)

    # Perform the tracking and print out the output
    print(
        json.dumps(
            track_module(
                module_name=args.name,
                package_name=args.package,
                submodules=submodules,
                track_import_stack=args.track_import_stack,
                full_depth=args.full_depth,
                detect_transitive=args.detect_transitive,
                show_optional=args.show_optional,
            ),
            indent=args.indent,
        )
    )


if __name__ == "__main__":  # pragma: no cover
    main()
