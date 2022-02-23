"""
This module implements utilities that enable tracking of third party deps
through import statements
"""

# Standard
from typing import Dict, List, Optional
import copy
import json
import logging
import os
import shlex
import subprocess
import sys

# Local
from .constants import THIS_PACKAGE
from .log import log

## Public ######################################################################


def track_module(
    module_name: str,
    package_name: Optional[str] = None,
    log_level: Optional[int] = None,
    recursive: bool = False,
    num_jobs: int = 0,
) -> Dict[str, List[str]]:
    """This function executes the tracking of a single module by launching a
    subprocess to execute this module against the target module. The
    implementation of thie tracking resides in the __main__ in order to
    carefully control the import ecosystem.

    Args:
        module_name:  str
            The name of the module to track (may be relative if package_name
            provided)
        package_name:  Optional[str]
            The parent package name of the module if the module name is relative
        log_level:  Optional[Union[int, str]]
            Log level to pass through to the child process
        recursive:  bool
            Whether or not to recursively track sub-modules within the target
            module
        num_jobs:  int
            The number of concurrent jobs to run when recursing

    Returns:
        import_mapping:  Dict[str, List[str]]
            The mapping from fully-qualified module name to the set of imports
            needed by the given module
    """
    # Set up the environment with all sys.paths available (included those added
    # in code)
    env = dict(copy.deepcopy(os.environ))
    env["PYTHONPATH"] = ":".join(sys.path)

    # Determine the log level
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), None)
    if log_level is None:
        log_level = os.environ.get("LOG_LEVEL", "error")

    # Set up the command to run this module
    cmd = cmd = "{} -W ignore -m {} --name {} --log_level {} --num_jobs {}".format(
        sys.executable,
        THIS_PACKAGE,
        module_name,
        log_level,
        num_jobs,
    )
    if package_name is not None:
        cmd += f" --package {package_name}"
    if recursive:
        cmd += " --recursive"

    # Launch the process
    proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, env=env)

    # Wait for the result and parse it as json
    result, _ = proc.communicate()
    return json.loads(result)
