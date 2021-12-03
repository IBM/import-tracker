"""
Tests for the main entrypoint
"""

# Standard
from contextlib import contextmanager
import json
import sys

# Third Party
import pytest

# Local
from .helpers import LAZY_MODE
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

## Tests #######################################################################

def test_without_package(capsys, LAZY_MODE):
    """Run the main function against the sample lib and check the output"""
    with cli_args("--name", "sample_lib.submod1"):
        main()
    captured = capsys.readouterr()
    assert not captured.err
    assert captured.out
    parsed_out = json.loads(captured.out)

    # Just check the keys. The values are funky because of this being run from
    # within a test
    assert list(parsed_out.keys()) == ["sample_lib.submod1"]


def test_with_package(capsys, LAZY_MODE):
    """Run the main function with a package argument"""
    with cli_args("--name", ".submod1", "--package", "sample_lib"):
        main()
    captured = capsys.readouterr()
    assert not captured.err
    assert captured.out
    parsed_out = json.loads(captured.out)

    # Just check the keys. The values are funky because of this being run from
    # within a test
    assert list(parsed_out.keys()) == ["sample_lib.submod1"]


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
