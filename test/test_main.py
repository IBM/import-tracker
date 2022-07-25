"""
Tests for the main entrypoint
"""

# Standard
from contextlib import contextmanager
import json
import logging
import os
import sys

# Third Party
import pytest

# Local
from import_tracker import constants
from import_tracker.__main__ import main

## Helpers #####################################################################


@contextmanager
def cli_args(*args):
    """Wrapper to set the sys.argv for the enclosed context"""
    prev_argv = sys.argv
    sys.argv = ["dummy_script"] + list(args)
    yield
    sys.argv = prev_argv


## Tests #######################################################################


def test_without_package(capsys):
    """Run the main function against the sample lib and check the output"""
    with cli_args("--name", "sample_lib.submod1"):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)
    assert list(parsed_out.keys()) == ["sample_lib.submod1"]
    assert (set(parsed_out["sample_lib.submod1"])) == {"conditional_deps"}


def test_with_package(capsys):
    """Run the main function with a package argument"""
    with cli_args("--name", ".submod1", "--package", "sample_lib"):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)
    assert list(parsed_out.keys()) == ["sample_lib.submod1"]
    assert (set(parsed_out["sample_lib.submod1"])) == {"conditional_deps"}


def test_file_without_parent_path(capsys):
    """Check that the corner case of __file__ being unset is caught"""
    with cli_args("--name", "google.protobuf"):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)

    # Just check the keys. The values are funky because of this being run from
    # within a test
    assert list(parsed_out.keys()) == ["google.protobuf"]


def test_with_logging(capsys):
    """Run the main function with logging turned up and make sure the output is
    not changed
    """
    with cli_args(
        "--name", "sample_lib.submod1", "--log_level", str(logging.DEBUG - 3)
    ):
        main()
    captured = capsys.readouterr()
    assert captured.err
    assert captured.out
    parsed_out = json.loads(captured.out)
    assert list(parsed_out.keys()) == ["sample_lib.submod1"]
    assert (set(parsed_out["sample_lib.submod1"])) == {"conditional_deps"}


def test_import_time_error(capsys):
    """Check that an exception from the imported module is forwarded"""
    with cli_args("--name", "bad_lib"):
        with pytest.raises(RuntimeError):
            main()


def test_submodule_error(capsys):
    """Check that an exception from a submodule is forwarded"""
    with cli_args("--name", "bad_lib"):
        with pytest.raises(RuntimeError):
            main()


def test_sibling_import(capsys):
    """Make sure that a library with a submodule that imports a sibling
    submodule properly tracks dependencies through the sibling
    """
    with cli_args("--name", "inter_mod_deps", "--submodules"):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)
    assert (set(parsed_out["inter_mod_deps.submod1"])) == {"alog"}
    assert (set(parsed_out["inter_mod_deps.submod2"])) == {
        "alog",
        "yaml",
    }
    assert (set(parsed_out["inter_mod_deps.submod2.foo"])) == {
        "yaml",
    }
    assert (set(parsed_out["inter_mod_deps.submod2.bar"])) == {
        "yaml",
    }
    assert (set(parsed_out["inter_mod_deps.submod3"])) == {
        "alog",
        "yaml",
    }
    assert (set(parsed_out["inter_mod_deps.submod4"])) == {
        "yaml",
    }
    assert (set(parsed_out["inter_mod_deps.submod5"])) == {
        "yaml",
    }


def test_lib_with_lazy_imports(capsys):
    """Make sure that a library which uses import_tracker's lazy import errors
    and has "traditional" conditional dependencies does not blow up when tracked
    """
    with cli_args("--name", "lazy_import_errors"):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)
    assert "lazy_import_errors" in parsed_out


def test_detect_transitive_with_nested_module(capsys):
    """Test that --detect_transitive works with nested modules as expected"""
    with cli_args(
        "--name",
        "direct_dep_nested",
        "--submodules",
        "--detect_transitive",
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)

    test_lib_dir = os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),
            "sample_libs",
            "direct_dep_nested",
        )
    )
    assert parsed_out == {
        "direct_dep_nested": {
            "alog": {"type": "transitive"},
            "conditional_deps": {"type": "transitive"},
            "sample_lib": {"type": "direct"},
            "yaml": {"type": "transitive"},
        },
        "direct_dep_nested.nested": {
            "alog": {"type": "transitive"},
            "conditional_deps": {"type": "transitive"},
            "sample_lib": {"type": "direct"},
            "yaml": {"type": "transitive"},
        },
        "direct_dep_nested.nested2": {
            "alog": {"type": "direct"},
        },
    }


def test_lazy_module_trigger(capsys):
    """Make sure that a sub-module which holds LazyModule attrs does not
    incorrectly trigger their imports when run through import_tracker.
    """
    with cli_args("--name", "lazy_module", "--submodules"):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)

    assert parsed_out == {
        "lazy_module": ["alog"],
        "lazy_module.lazy_deps": [],
        "lazy_module.mod": ["alog"],
    }
