"""
Tests for the main entrypoint
"""

# Standard
from contextlib import contextmanager
import json
import logging
import sys

# Third Party
import pytest

# Local
from .helpers import LAZY_MODE, reset_sys_modules
from import_tracker.__main__ import main
import import_tracker

## Helpers #####################################################################


@contextmanager
def cli_args(*args):
    """Wrapper to set the sys.argv for the enclosed context"""
    prev_argv = sys.argv
    sys.argv = ["dummy_script"] + list(args)
    yield
    sys.argv = prev_argv


# We keep track of the base system modules names so that they can be removed
# from the results in the tests
BASE_SYS_MODULES = set(sys.modules.keys())

## Tests #######################################################################


def test_without_package(capsys, LAZY_MODE):
    """Run the main function against the sample lib and check the output"""
    with cli_args("--name", "sample_lib.submod1"):
        main()
    captured = capsys.readouterr()
    assert not captured.err
    assert captured.out
    parsed_out = json.loads(captured.out)
    assert list(parsed_out.keys()) == ["sample_lib.submod1"]
    assert (set(parsed_out["sample_lib.submod1"]) - BASE_SYS_MODULES) == {
        "conditional_deps"
    }


def test_with_package(capsys, LAZY_MODE):
    """Run the main function with a package argument"""
    with cli_args("--name", ".submod1", "--package", "sample_lib"):
        main()
    captured = capsys.readouterr()
    assert not captured.err
    assert captured.out
    parsed_out = json.loads(captured.out)
    assert list(parsed_out.keys()) == ["sample_lib.submod1"]
    assert (set(parsed_out["sample_lib.submod1"]) - BASE_SYS_MODULES) == {
        "conditional_deps"
    }


def test_file_without_parent_path(capsys):
    """Check that the corner case of __file__ being unset is caught"""
    with cli_args("--name", "google.protobuf"):
        main()
    captured = capsys.readouterr()
    assert not captured.err
    assert captured.out
    parsed_out = json.loads(captured.out)

    # Just check the keys. The values are funky because of this being run from
    # within a test
    assert list(parsed_out.keys()) == ["google.protobuf"]


def test_with_logging(capsys, LAZY_MODE):
    """Run the main function with logging turned up and make sure the output is
    not changed
    """
    with cli_args(
        "--name", "sample_lib.submod1", "--log_level", str(logging.DEBUG - 3)
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)
    assert list(parsed_out.keys()) == ["sample_lib.submod1"]
    assert (set(parsed_out["sample_lib.submod1"]) - BASE_SYS_MODULES) == {
        "conditional_deps"
    }
