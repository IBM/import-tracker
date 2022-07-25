"""
Tests for the import_tracker module's public API
"""

# Local
from import_tracker import constants
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


def test_detect_transitive_no_stack_traces():
    """Test that --detect_transitive works as expected"""
    lib_mapping = import_tracker.track_module(
        "direct_dep_ambiguous",
        submodules=True,
        detect_transitive=True,
    )
    assert lib_mapping == {
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
        "direct_dep_ambiguous.bar": {
            "alog": {
                "type": constants.TYPE_TRANSITIVE,
            },
        },
    }


def test_detect_transitive_with_stack_traces():
    """Test that detect_transitive + track_import_stack works as expected"""
    lib_mapping = import_tracker.track_module(
        "direct_dep_ambiguous",
        submodules=True,
        detect_transitive=True,
        track_import_stack=True,
    )
    assert lib_mapping == {
        "direct_dep_ambiguous": {
            "alog": {
                "stack": [
                    [
                        "direct_dep_ambiguous",
                    ],
                    [
                        "direct_dep_ambiguous",
                        "direct_dep_ambiguous.foo",
                    ],
                ],
                "type": constants.TYPE_DIRECT,
            },
            "yaml": {
                "stack": [
                    [
                        "direct_dep_ambiguous",
                        "direct_dep_ambiguous.foo",
                    ],
                ],
                "type": constants.TYPE_TRANSITIVE,
            },
        },
        "direct_dep_ambiguous.bar": {
            "alog": {
                "stack": [
                    [
                        "direct_dep_ambiguous",
                        "direct_dep_ambiguous.bar",
                    ],
                ],
                "type": constants.TYPE_TRANSITIVE,
            },
        },
        "direct_dep_ambiguous.foo": {
            "alog": {
                "stack": [
                    ["direct_dep_ambiguous.foo"],
                ],
                "type": constants.TYPE_DIRECT,
            },
            "yaml": {
                "stack": [
                    ["direct_dep_ambiguous.foo"],
                ],
                "type": constants.TYPE_DIRECT,
            },
        },
    }


def test_with_limited_submodules():
    """Make sure that when a list of submodules is given, the recursion only
    applies to those submodules.
    """
    lib_mapping = import_tracker.track_module(
        "sample_lib",
        submodules=["sample_lib.submod1"],
    )
    assert set(lib_mapping.keys()) == {"sample_lib", "sample_lib.submod1"}


def test_detect_transitive_with_nested_module():
    """Test that detect_transitive works with nested modules as expected"""
    lib_mapping = import_tracker.track_module(
        "direct_dep_nested",
        submodules=True,
        detect_transitive=True,
    )
    assert lib_mapping == {
        "direct_dep_nested": {
            "alog": {"type": constants.TYPE_TRANSITIVE},
            "sample_lib": {"type": constants.TYPE_DIRECT},
            "yaml": {"type": constants.TYPE_TRANSITIVE},
        },
        "direct_dep_nested.nested": {
            "sample_lib": {"type": constants.TYPE_DIRECT},
            "yaml": {"type": constants.TYPE_DIRECT},
        },
        "direct_dep_nested.nested2": {
            "alog": {"type": constants.TYPE_DIRECT},
            "sample_lib": {"type": constants.TYPE_TRANSITIVE},
        },
    }


def test_lazy_module_trigger():
    """Make sure that a sub-module which holds LazyModule attrs does not
    incorrectly trigger their imports when run through import_tracker.

    BREAKING CHANGE: With the overhaul to use bytecode, lazy deps are fully
        invisible since there's no way to detect when a LazyModule triggers its
        import without inspecting every __getattr__ invocation in the bytecode!
        This is a departure from the results when instrumenting the import
        framework where these changes can be detected in sys.modules.
        Ultimately, this functionality with LazyModule should probably go away
        fully since it's not a particularly userful tool anymore.
    """
    lib_mapping = import_tracker.track_module(
        "lazy_module",
        submodules=True,
    )
    assert lib_mapping == {
        "lazy_module": [],
        "lazy_module.lazy_deps": [],
        "lazy_module.mod": [],
    }
