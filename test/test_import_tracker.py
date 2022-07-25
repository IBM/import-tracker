"""
Tests for the import_tracker module's public API
"""

# Standard
from types import ModuleType
import json
import os
import sys
import tempfile
import warnings

# Third Party
import pytest

# Local
import import_tracker

## Package API #################################################################


def test_import_tracker_public_api():
    """Test to catch changes in the set of attributes exposed on the public
    package api
    """
    expected_attrs = {
        "setup_tools",
        "track_module",
        "LazyModule",
        "lazy_import_errors",
    }
    module_attrs = set(dir(import_tracker))
    assert module_attrs.intersection(expected_attrs) == expected_attrs


## track_module ################################################################


def test_track_module_programmatic():
    """Test that calling track_module can be invoked to programmatically do
    tracking (vs as a CLI)
    """
    sample_lib_mapping = import_tracker.track_module("sample_lib")
    assert sample_lib_mapping == {
        "sample_lib": sorted(["alog", "yaml", "conditional_deps"])
    }


def test_track_module_with_package():
    """Test that calling track_module can be invoked with a relative sub module
    and parent package
    """
    sample_lib_mapping = import_tracker.track_module(".submod1", "sample_lib")
    assert sample_lib_mapping == {"sample_lib.submod1": ["conditional_deps"]}


def test_track_module_recursive():
    """Test that calling track_module can recurse with a fixed number of jobs

    NOTE: The num_jobs simply exercises that code as there's no real way to
        validate the parallelism
    """
    sample_lib_mapping = import_tracker.track_module("sample_lib", submodules=True)
    assert sample_lib_mapping == {
        "sample_lib": sorted(["conditional_deps", "alog", "yaml"]),
        "sample_lib.submod1": ["conditional_deps"],
        "sample_lib.submod2": ["alog"],
        "sample_lib.nested": sorted(["alog", "yaml"]),
        "sample_lib.nested.submod3": sorted(["alog", "yaml"]),
    }


def test_track_module_with_limited_submodules():
    """Test that the submodules arg can be passed through"""
    sample_lib_mapping = import_tracker.track_module(
        "sample_lib",
        submodules=["sample_lib.submod1"],
    )
    assert sample_lib_mapping == {
        "sample_lib": sorted(["conditional_deps", "alog", "yaml"]),
        "sample_lib.submod1": ["conditional_deps"],
    }


def test_sibling_import():
    """Make sure that a library with a submodule that imports a sibling
    submodule properly tracks dependencies through the sibling
    """
    lib_mapping = import_tracker.track_module(
        "inter_mod_deps",
        submodules=True,
    )
    assert (set(lib_mapping["inter_mod_deps.submod1"])) == {"alog"}
    assert (set(lib_mapping["inter_mod_deps.submod2"])) == {
        "alog",
        "yaml",
    }
    assert (set(lib_mapping["inter_mod_deps.submod2.foo"])) == {
        "yaml",
    }
    assert (set(lib_mapping["inter_mod_deps.submod2.bar"])) == {
        "yaml",
    }
    assert (set(lib_mapping["inter_mod_deps.submod3"])) == {
        "alog",
        "yaml",
    }
    assert (set(lib_mapping["inter_mod_deps.submod4"])) == {
        "yaml",
    }
    assert (set(lib_mapping["inter_mod_deps.submod5"])) == {
        "yaml",
    }


def test_import_stack_tracking():
    """Make sure that tracking the import stack works as expected"""
    lib_mapping = import_tracker.track_module(
        "inter_mod_deps",
        submodules=True,
        track_import_stack=True,
    )

    assert set(lib_mapping.keys()) == {
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
    assert lib_mapping["inter_mod_deps.submod2"] == {
        "alog": {
            "stack": [
                [
                    "inter_mod_deps.submod2",
                    "inter_mod_deps.submod1",
                ]
            ]
        },
        "yaml": {
            "stack": [
                ["inter_mod_deps.submod2"],
            ]
        },
    }
