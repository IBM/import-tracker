"""
Tests for setup tools
"""

# Standard
import os
import tempfile

# Third Party
import pytest

# Local
from .helpers import configure_logging
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
    assert requirements == ["PyYaml >= 6.0", "import-tracker"]
    assert extras_require == {
        "sample_lib.submod1": sorted(["conditional_deps"]),
        "sample_lib.submod2": sorted(["alchemy-logging>=1.0.3"]),
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
        side_effect_modules=["side_effects.global_thing"],
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
    assert requirements == ["alchemy-logging"]
    assert extras_require == {"single_extra.extra": ["PyYaml"]}
