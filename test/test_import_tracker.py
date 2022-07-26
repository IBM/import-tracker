"""
Tests for the import_tracker module's public API
"""

# Standard
from types import ModuleType
import sys

# Local
from import_tracker import constants
from import_tracker.import_tracker import (
    _get_imports,
    _mod_defined_in_init_file,
    track_module,
)
import import_tracker

## Package API #################################################################


def test_import_tracker_public_api():
    """Test to catch changes in the set of attributes exposed on the public
    package api
    """
    expected_attrs = {
        "setup_tools",
        "track_module",
        "lazy_import_errors",
    }
    module_attrs = set(dir(import_tracker))
    assert module_attrs.intersection(expected_attrs) == expected_attrs


## track_module ################################################################


def test_track_module_programmatic():
    """Test that calling track_module can be invoked to programmatically do
    tracking (vs as a CLI)
    """
    sample_lib_mapping = track_module("sample_lib")
    assert sample_lib_mapping == {
        "sample_lib": sorted(["alog", "yaml", "conditional_deps"])
    }


def test_track_module_with_package():
    """Test that calling track_module can be invoked with a relative sub module
    and parent package
    """
    sample_lib_mapping = track_module(".submod1", "sample_lib")
    assert sample_lib_mapping == {"sample_lib.submod1": ["conditional_deps"]}


def test_track_module_recursive():
    """Test that calling track_module can recurse with a fixed number of jobs

    NOTE: The num_jobs simply exercises that code as there's no real way to
        validate the parallelism
    """
    sample_lib_mapping = track_module("sample_lib", submodules=True)
    assert sample_lib_mapping == {
        "sample_lib": sorted(["conditional_deps", "alog", "yaml"]),
        "sample_lib.submod1": ["conditional_deps"],
        "sample_lib.submod2": ["alog"],
        "sample_lib.nested": sorted(["alog", "yaml"]),
        "sample_lib.nested.submod3": sorted(["alog", "yaml"]),
    }


def test_track_module_with_limited_submodules():
    """Test that the submodules arg can be passed through"""
    sample_lib_mapping = track_module(
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
    lib_mapping = track_module(
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
    lib_mapping = track_module(
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
    lib_mapping = track_module(
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
    lib_mapping = track_module(
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
    lib_mapping = track_module(
        "sample_lib",
        submodules=["sample_lib.submod1"],
    )
    assert set(lib_mapping.keys()) == {"sample_lib", "sample_lib.submod1"}


def test_detect_transitive_with_nested_module():
    """Test that detect_transitive works with nested modules as expected"""
    lib_mapping = track_module(
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


def test_detect_transitive_with_nested_module_full_depth():
    """Test that with full_depth, nested dependencies are taken into account"""
    lib_mapping = track_module(
        "direct_dep_nested",
        submodules=True,
        detect_transitive=True,
        full_depth=True,
    )
    assert lib_mapping == {
        "direct_dep_nested": {
            "alog": {"type": constants.TYPE_TRANSITIVE},
            "sample_lib": {"type": constants.TYPE_DIRECT},
            "yaml": {"type": constants.TYPE_TRANSITIVE},
            "conditional_deps": {"type": constants.TYPE_TRANSITIVE},
        },
        "direct_dep_nested.nested": {
            "sample_lib": {"type": constants.TYPE_DIRECT},
            "yaml": {"type": constants.TYPE_DIRECT},
            "conditional_deps": {"type": constants.TYPE_TRANSITIVE},
        },
        "direct_dep_nested.nested2": {
            "alog": {"type": constants.TYPE_DIRECT},
            "sample_lib": {"type": constants.TYPE_TRANSITIVE},
            "conditional_deps": {"type": constants.TYPE_TRANSITIVE},
        },
    }


def test_all_import_types():
    """Make sure that all different import statement types are covered"""
    assert track_module("all_import_types", submodules=True) == {
        "all_import_types": [
            "alog",
            "inter_mod_deps",
            "sample_lib",
        ],
        "all_import_types.sub_module1": [
            "alog",
            "inter_mod_deps",
            "sample_lib",
        ],
        "all_import_types.sub_module2": [
            "alog",
            "inter_mod_deps",
            "sample_lib",
        ],
        "all_import_types.sub_module3": [
            "alog",
            "inter_mod_deps",
            "sample_lib",
        ],
    }


def test_deep_siblings():
    """This test exercises the sample library that was the main reason for the
    full refactor in the first place. The library is constructed such that there
    are sub-directories (blocks and workflows) where individual sub-modules
    within workflows may depend on a subset of the sub-modules within blocks. In
    this case, we do not want the entire dependency set of blocks to be
    attributed to a workflows module, but rather we want just the dependencies
    of the block modules that it needs.
    """
    assert track_module("deep_siblings", submodules=True) == {
        "deep_siblings": ["alog", "yaml"],
        "deep_siblings.blocks": ["alog", "yaml"],
        "deep_siblings.blocks.foo_type": ["yaml"],
        "deep_siblings.blocks.foo_type.foo": ["yaml"],
        "deep_siblings.blocks.bar_type": ["alog"],
        "deep_siblings.blocks.bar_type.bar": ["alog"],
        "deep_siblings.workflows": ["yaml"],
        "deep_siblings.workflows.foo_type": ["yaml"],
        "deep_siblings.workflows.foo_type.foo": ["yaml"],
    }


## Details #####################################################################


def test_get_imports_no_bytecode():
    """Excercise _get_imports and _mod_defined_in_init_file on a module with no
    bytecode to ensure that they doesn't explode!
    """
    new_mod = ModuleType("new_mod")
    assert _get_imports(new_mod) == (set(), set())
    assert not _mod_defined_in_init_file(new_mod)


def test_missing_parent_mod():
    """This is a likely unreachable corner case, but this test exercises the
    case where the expected parent module doesn't exist in sys.modules
    """
    # Local
    from sample_lib import nested

    del sys.modules["sample_lib"]
    assert track_module("sample_lib.nested")
