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


def test_parse_requirements_happy():
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
            "submod3": sorted(["PyYaml >= 6.0", "alchemy-logging>=1.0.3"]),
            "submod1": sorted(["conditional_deps"]),
            "submod2": sorted(["alchemy-logging>=1.0.3"]),
        }


def test_parse_requirements_add_untracked_reqs():
    """Make sure that packages in the requirements.txt which don't show up in
    any of the tracked modules are added to the common requirements
    """
    with tempfile.NamedTemporaryFile("w") as requirements_file:
        # Make a requirements file with an extra entry
        extra_req = "something-ElSe[extras]~=1.2.3"
        requirements_file.write("\n".join(sample_lib_requirements + [extra_req]))
        requirements_file.flush()

        # Parse the reqs for "sample_lib"
        requirements, _ = parse_requirements(
            requirements_file.name,
            "sample_lib",
        )

        # Make sure the extra requirement was added
        extra_req in requirements


def test_parse_requirements_missing_import_tracker():
    """Make sure that parse_requirements does require import_tracker (or
    import-tracker) in the requirements list
    """
    with tempfile.NamedTemporaryFile("w") as requirements_file:
        # Make a requirements file that is missing import_tracker
        requirements_file.write(
            "\n".join(set(sample_lib_requirements) - {"import-tracker"})
        )
        requirements_file.flush()

        # Make sure the assertion is tripped
        with pytest.raises(AssertionError):
            parse_requirements(requirements_file.name, "sample_lib")
