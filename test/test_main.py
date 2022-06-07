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
from .helpers import reset_sys_modules
from import_tracker import constants
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
    with cli_args("--name", "inter_mod_deps", "--recursive"):
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


def test_lib_with_side_effect_imports():
    """Make sure that a library with import-time side effects works when
    specifying the --side_effect_modules argument and fails without it
    """

    # Expect failure without the argument
    with cli_args("--name", "side_effects.mod"):
        with pytest.raises(AssertionError):
            main()

    # Expect success with the argument
    with cli_args(
        "--name",
        "side_effects.mod",
        "--side_effect_modules",
        "side_effects.global_thing",
    ):
        main()

    # Ensure that the argument is passed recursively
    with cli_args(
        "--name",
        "side_effects",
        "--side_effect_modules",
        "side_effects.global_thing",
        "--recursive",
    ):
        main()


def test_with_limited_submodules(capsys):
    """Make sure that when a list of submodules is given, the recursion only
    applies to those submodules.
    """
    with cli_args(
        "--name",
        "sample_lib",
        "--recursive",
        "--submodules",
        "sample_lib.submod1",
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)
    assert list(parsed_out.keys()) == ["sample_lib", "sample_lib.submod1"]


def test_error_submodules_without_recursive():
    """Make sure an error is raised when submodules given without recursive"""
    with cli_args(
        "--name",
        "sample_lib",
        "--submodules",
        "sample_lib.submod1",
    ):
        with pytest.raises(ValueError):
            main()


def test_import_stack_tracking(capsys):
    """Make sure that tracking the import stack works as expected"""
    with cli_args(
        "--name",
        "inter_mod_deps",
        "--recursive",
        "--track_import_stack",
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)

    assert set(parsed_out.keys()) == {
        "inter_mod_deps",
        "inter_mod_deps.submod1",
        "inter_mod_deps.submod2",
        "inter_mod_deps.submod2.foo",
        "inter_mod_deps.submod2.bar",
        "inter_mod_deps.submod3",
        "inter_mod_deps.submod4",
        "inter_mod_deps.submod5",
    }

    # Check one of the stacks to make sure it's correct
    test_lib_dir = os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),
            "sample_libs",
            "inter_mod_deps",
        )
    )
    assert parsed_out["inter_mod_deps.submod2"] == {
        "alog": [
            {
                "filename": f"{test_lib_dir}/submod1/__init__.py",
                "lineno": 6,
                "code_context": ["import alog"],
            },
            {
                "filename": f"{test_lib_dir}/__init__.py",
                "lineno": 17,
                "code_context": [
                    "from . import submod1, submod2, submod3, submod4, submod5"
                ],
            },
        ],
        "yaml": [
            {
                "filename": f"{test_lib_dir}/submod2/__init__.py",
                "lineno": 6,
                "code_context": ["import yaml"],
            },
            {
                "filename": f"{test_lib_dir}/__init__.py",
                "lineno": 17,
                "code_context": [
                    "from . import submod1, submod2, submod3, submod4, submod5"
                ],
            },
        ],
    }


def test_detect_transitive_no_stack_traces(capsys):
    """Test that --detect_transitive works as expected"""
    with cli_args(
        "--name",
        "direct_dep_ambiguous",
        "--recursive",
        "--detect_transitive",
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)
    assert parsed_out == {
        "direct_dep_ambiguous": {
            "alog": {
                "type": constants.TYPE_DIRECT,
            },
            "yaml": {
                "type": constants.TYPE_TRANSITIVE,
            },
        },
        "direct_dep_ambiguous.foo": {
            "alog": {
                "type": constants.TYPE_DIRECT,
            },
            "yaml": {
                "type": constants.TYPE_DIRECT,
            },
        },
        "direct_dep_ambiguous.bar": {},
    }


def test_detect_transitive_with_stack_traces(capsys):
    """Test that --detect_transitive works as expected"""
    with cli_args(
        "--name",
        "direct_dep_ambiguous",
        "--recursive",
        "--detect_transitive",
        "--track_import_stack",
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)

    test_lib_dir = os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),
            "sample_libs",
            "direct_dep_ambiguous",
        )
    )
    assert parsed_out == {
        "direct_dep_ambiguous": {
            "alog": {
                "stack": [
                    {
                        "filename": f"{test_lib_dir}/foo.py",
                        "lineno": 6,
                        "code_context": ["import alog"],
                    },
                    {
                        "filename": f"{test_lib_dir}/__init__.py",
                        "lineno": 9,
                        "code_context": ["from . import bar, foo"],
                    },
                ],
                "type": "direct",
            },
            "yaml": {
                "stack": [
                    {
                        "filename": f"{test_lib_dir}/foo.py",
                        "lineno": 3,
                        "code_context": ["import yaml"],
                    },
                    {
                        "filename": f"{test_lib_dir}/__init__.py",
                        "lineno": 9,
                        "code_context": ["from . import bar, foo"],
                    },
                ],
                "type": "transitive",
            },
        },
        "direct_dep_ambiguous.bar": {},
        "direct_dep_ambiguous.foo": {
            "alog": {
                "stack": [
                    {
                        "filename": f"{test_lib_dir}/foo.py",
                        "lineno": 6,
                        "code_context": ["import alog"],
                    },
                    {
                        "filename": f"{test_lib_dir}/__init__.py",
                        "lineno": 9,
                        "code_context": ["from . import bar, foo"],
                    },
                ],
                "type": "direct",
            },
            "yaml": {
                "stack": [
                    {
                        "filename": f"{test_lib_dir}/foo.py",
                        "lineno": 3,
                        "code_context": ["import yaml"],
                    },
                    {
                        "filename": f"{test_lib_dir}/__init__.py",
                        "lineno": 9,
                        "code_context": ["from . import bar, foo"],
                    },
                ],
                "type": "direct",
            },
        },
    }


def test_detect_transitive_with_nested_module(capsys):
    """Test that --detect_transitive works with nested modules as expected"""
    with cli_args(
        "--name",
        "direct_dep_nested",
        "--recursive",
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
    with cli_args("--name", "lazy_module", "--recursive"):
        main()
    captured = capsys.readouterr()
    assert captured.out
    parsed_out = json.loads(captured.out)

    assert parsed_out == {
        "lazy_module": ["alog"],
        "lazy_module.lazy_deps": [],
        "lazy_module.mod": ["alog"],
    }
