"""
Tests for setup tools
"""

# Standard
import os
import tempfile

# Third Party
import pytest

# Local
from import_tracker.setup_tools import parse_requirements

sample_lib_requirements = [
    "alchemy-logging>=1.0.3",
    "PyYaml >= 6.0",
    "conditional_deps",
    "import-tracker",
]


def test_parse_requirements_happy_file():
    """Make sure that parse_requirements correctly parses requirements for a
    library with multiple tracked modules
    """
    with tempfile.NamedTemporaryFile("w") as requirements_file:
        # Make a requirements file that looks normal
        requirements_file.write("\n".join(sample_lib_requirements))
        requirements_file.flush()

        # Parse the reqs for "sample_lib"
        requirements, extras_require = parse_requirements(
            requirements_file.name,
            "sample_lib",
        )

        # Make sure the right parsing happened
        assert requirements == ["import-tracker"]
        assert extras_require == {
            "sample_lib.nested.submod3": sorted(
                ["PyYaml >= 6.0", "alchemy-logging>=1.0.3"]
            ),
            "sample_lib.nested": sorted(["PyYaml >= 6.0", "alchemy-logging>=1.0.3"]),
            "sample_lib.submod1": sorted(["conditional_deps"]),
            "sample_lib.submod2": sorted(["alchemy-logging>=1.0.3"]),
            "sample_lib": sorted(set(sample_lib_requirements) - {"import-tracker"}),
            "all": sorted(sample_lib_requirements),
        }


@pytest.mark.parametrize("iterable_type", [list, tuple, set])
def test_parse_requirements_happy_iterable(iterable_type):
    """Make sure that parse_requirements correctly parses requirements for a
    library with multiple tracked modules from the supported iterable types
    """
    # Parse the reqs for "sample_lib"
    requirements, extras_require = parse_requirements(
        iterable_type(sample_lib_requirements),
        "sample_lib",
    )

    # Make sure the right parsing happened
    assert requirements == ["import-tracker"]
    assert extras_require == {
        "sample_lib.nested.submod3": sorted(
            ["PyYaml >= 6.0", "alchemy-logging>=1.0.3"]
        ),
        "sample_lib.nested": sorted(["PyYaml >= 6.0", "alchemy-logging>=1.0.3"]),
        "sample_lib.submod1": sorted(["conditional_deps"]),
        "sample_lib.submod2": sorted(["alchemy-logging>=1.0.3"]),
        "sample_lib": sorted(set(sample_lib_requirements) - {"import-tracker"}),
        "all": sorted(sample_lib_requirements),
    }


def test_parse_requirements_add_untracked_reqs():
    """Make sure that packages in the requirements.txt which don't show up in
    any of the tracked modules are added to the common requirements
    """
    # Make requirements with an extra entry
    extra_req = "something-ElSe[extras]~=1.2.3"
    reqs = sample_lib_requirements + [extra_req]
    requirements, extras_require = parse_requirements(reqs, "sample_lib")

    # Make sure the extra requirement was added
    assert extra_req in requirements
    assert extras_require["all"] == sorted(reqs)


def test_parse_requirements_add_subset_of_submodules():
    """Make sure that parse_requirements can parse only a subset of the full set
    of submodules within the target library
    """
    # Parse the reqs for "sample_lib"
    requirements, extras_require = parse_requirements(
        sample_lib_requirements,
        "sample_lib",
        ["sample_lib.submod1", "sample_lib.submod2"],
    )

    # Make sure the right parsing happened
    assert sorted(requirements) == sorted(
        ["alchemy-logging>=1.0.3", "PyYaml >= 6.0", "import-tracker"]
    )
    assert extras_require == {
        "sample_lib.submod1": ["conditional_deps"],
        "sample_lib.submod2": [],
        "all": sorted(sample_lib_requirements),
    }


def test_parse_requirements_unknown_extras():
    """Make sure that parse_requirements raises an error if extras_modules are
    requested that don't exist
    """
    # Make sure the assertion is tripped
    with pytest.raises(AssertionError):
        parse_requirements(
            sample_lib_requirements,
            "sample_lib",
            ["foobar"],
        )


def test_parse_requirements_with_side_effects():
    """Make sure that side_effect_modules can be passed through to allow for
    successful parsing
    """
    # Parse the reqs for "side_effects". We only care that this doesn't
    # raise, so there's no validation of the results.
    parse_requirements(
        requirements=sample_lib_requirements,
        library_name="side_effects",
    )


def test_parse_requirements_bad_requirements_type():
    """Make sure that a ValueError is raised if an invalid type is given for the
    requirements argument
    """
    # Make sure the assertion is tripped
    with pytest.raises(ValueError):
        parse_requirements({"foo": "bar"}, "sample_lib", ["foobar"])


def test_single_extras_module():
    """Make sure that for a library with a single extras module and a non-zero
    set of non-extra modules, the deps for the extra module are correctly
    allocated.
    """
    requirements, extras_require = parse_requirements(
        ["alchemy-logging", "PyYaml"],
        "single_extra",
        ["single_extra.extra"],
    )
    assert requirements == sorted(["alchemy-logging"])
    assert extras_require == {
        "all": sorted(["alchemy-logging", "PyYaml"]),
        "single_extra.extra": ["PyYaml"],
    }


def test_parent_direct_deps():
    """Make sure that direct dependencies of parent modules are correctly
    attributed when holding children as extras that also require the same deps
    """
    requirements, extras_require = parse_requirements(
        ["alchemy-logging", "PyYaml"],
        "direct_dep_ambiguous",
        ["direct_dep_ambiguous.foo"],
    )
    assert requirements == ["alchemy-logging"]
    assert extras_require == {
        "all": sorted(["PyYaml", "alchemy-logging"]),
        "direct_dep_ambiguous.foo": ["PyYaml"],
    }


def test_nested_deps():
    """Make sure that direct depencencies show up in requirements
    for nested modules
    """
    requirements, extras_require = parse_requirements(
        ["sample_lib", "PyYaml", "alchemy-logging"],
        "direct_dep_nested",
        ["direct_dep_nested.nested", "direct_dep_nested.nested2"],
    )
    assert requirements == sorted(["sample_lib"])
    assert extras_require == {
        "all": sorted(["sample_lib", "PyYaml", "alchemy-logging"]),
        "direct_dep_nested.nested": sorted(["PyYaml"]),
        "direct_dep_nested.nested2": sorted(["alchemy-logging"]),
    }


def test_full_depth_direct_and_transitive():
    """Make sure that a library which holds a dependency as both a direct import
    dependency and also requires it transitively through another third party
    library correclty allocates the dependency to places where the intermediate
    third party library is required.
    """
    # Run without full_depth and ensure that alog is only allocated to foo and
    # is not in the base requirements
    requirements, extras_require = parse_requirements(
        ["single_extra", "alchemy-logging"],
        "full_depth_direct_and_transitive",
        [
            "full_depth_direct_and_transitive.foo",
            "full_depth_direct_and_transitive.bar",
        ],
        full_depth=False,
    )
    assert requirements == []
    assert extras_require == {
        "all": sorted(["single_extra", "alchemy-logging"]),
        "full_depth_direct_and_transitive.foo": ["alchemy-logging"],
        "full_depth_direct_and_transitive.bar": ["single_extra"],
    }

    # Run without overriding full_depth (defaults to True) and ensure that alog
    # is found transitively via single_extra so it ends up in the base
    # requirements
    requirements, extras_require = parse_requirements(
        ["single_extra", "alchemy-logging"],
        "full_depth_direct_and_transitive",
        [
            "full_depth_direct_and_transitive.foo",
            "full_depth_direct_and_transitive.bar",
        ],
    )
    assert requirements == ["alchemy-logging"]
    assert extras_require == {
        "all": sorted(["single_extra", "alchemy-logging"]),
        "full_depth_direct_and_transitive.foo": [],
        "full_depth_direct_and_transitive.bar": ["single_extra"],
    }


def test_setup_tools_keep_optionals():
    """Make sure that the semantics of keep_optionals work as expected for all
    valid inputs to keep_optionals
    """
    # Without keep_optionals, optional_deps.opt should not depend on alog
    requirements, extras_require = parse_requirements(
        ["alchemy-logging", "PyYaml"],
        "optional_deps",
        ["optional_deps.opt", "optional_deps.not_opt"],
    )
    assert requirements == ["PyYaml"]
    assert extras_require == {
        "all": sorted(["alchemy-logging", "PyYaml"]),
        "optional_deps.opt": [],
        "optional_deps.not_opt": ["alchemy-logging"],
    }

    # With keep_optionals=True, optional_deps.opt should depend on alog
    requirements, extras_require = parse_requirements(
        ["alchemy-logging", "PyYaml"],
        "optional_deps",
        ["optional_deps.opt", "optional_deps.not_opt"],
        keep_optional=True,
    )
    assert requirements == sorted(["alchemy-logging", "PyYaml"])
    assert extras_require == {
        "all": sorted(["alchemy-logging", "PyYaml"]),
        "optional_deps.opt": [],
        "optional_deps.not_opt": [],
    }

    # With keep_optionals={"optional_deps.opt": ["alog"]}, optional_deps.opt
    # should depend on alog
    requirements, extras_require = parse_requirements(
        ["alchemy-logging", "PyYaml"],
        "optional_deps",
        ["optional_deps.opt", "optional_deps.not_opt"],
        keep_optional={"optional_deps.opt": ["alog"]},
    )
    assert requirements == sorted(["alchemy-logging", "PyYaml"])
    assert extras_require == {
        "all": sorted(["alchemy-logging", "PyYaml"]),
        "optional_deps.opt": [],
        "optional_deps.not_opt": [],
    }

    # With keep_optionals={"optional_deps.opt": ["something_else"]},
    # optional_deps.opt should depend on alog
    requirements, extras_require = parse_requirements(
        ["alchemy-logging", "PyYaml"],
        "optional_deps",
        ["optional_deps.opt", "optional_deps.not_opt"],
        keep_optional={"optional_deps.opt": ["something_else"]},
    )
    assert requirements == sorted(["PyYaml"])
    assert extras_require == {
        "all": sorted(["alchemy-logging", "PyYaml"]),
        "optional_deps.opt": [],
        "optional_deps.not_opt": ["alchemy-logging"],
    }


def test_intermediate_extras():
    """Make sure that intermediate extras correctly own unique dependencies that
    belong to their children
    """
    requirements, extras_require = parse_requirements(
        ["alchemy-logging"],
        "intermediate_extras",
        ["intermediate_extras.foo", "intermediate_extras.bar"],
    )
    assert not requirements
    assert extras_require == {
        "all": ["alchemy-logging"],
        "intermediate_extras.foo": ["alchemy-logging"],
        "intermediate_extras.bar": [],
    }
