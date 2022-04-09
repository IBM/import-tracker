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
from test.helpers import remove_test_deps, reset_sys_modules
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
    sample_lib_mapping = import_tracker.track_module(
        "sample_lib", recursive=True, num_jobs=2
    )
    assert sample_lib_mapping == {
        "sample_lib": sorted(["conditional_deps", "alog", "yaml"]),
        "sample_lib.submod1": ["conditional_deps"],
        "sample_lib.submod2": ["alog"],
        "sample_lib.nested": sorted(["alog", "yaml"]),
        "sample_lib.nested.submod3": sorted(["alog", "yaml"]),
    }


def test_track_module_with_log_level():
    """Test that a log level can be given to track_module"""
    sample_lib_mapping = import_tracker.track_module(
        "sample_lib.submod1", log_level="error"
    )
    assert sample_lib_mapping == {"sample_lib.submod1": ["conditional_deps"]}


def test_track_module_with_limited_submodules():
    """Test that the submodules arg can be passed through"""
    sample_lib_mapping = import_tracker.track_module(
        "sample_lib",
        recursive=True,
        submodules=["sample_lib.submod1"],
    )
    assert sample_lib_mapping == {
        "sample_lib": sorted(["conditional_deps", "alog", "yaml"]),
        "sample_lib.submod1": ["conditional_deps"],
    }
