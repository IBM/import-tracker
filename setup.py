"""A setuptools setup module for import_tracker"""

# Standard
import os

# Third Party
from setuptools import setup

# Read the README to provide the long description
python_base = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(python_base, "README.md"), "r") as handle:
    long_description = handle.read()

# Read version from the env
version = os.environ.get("RELEASE_VERSION")
assert version is not None, "Must set RELEASE_VERSION"

setup(
    name="import_tracker",
    version=version,
    description="A tool for managing dependencies in a modular python "
    "project by tracking which dependencies are needed by which sub-modules",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.ibm.com/ghart/import_tracker",
    author="Gabe Goodhart",
    author_email="gabe.l.hart@gmail.com",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    keywords=["import", "importlib", "dependencies"],
    packages=["import_tracker"],
)
