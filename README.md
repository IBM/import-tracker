# Import Tracker

`Import Tracker` is a Python package offering a number of capabilities related to tracking and managing optional dependencies in Python projects. Specifically, this project enables developers to:

-   Track the dependencies of a python project to map each module within the project to the set of dependencies it relies on. This can be useful for debugging of dependencies in large projects.

-   Enable lazy import errors in a python projects to prevent code from crashing when uninstalled imports are imported, but not utilized. This can be helpful in large projects, especially those which incorporate lots of hierarchical wild imports, as importing the top level package of such projects can often bring a lot of heavy dependencies into `sys.modules`.

-   Programmatically determine the [`install_requires`](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#declaring-required-dependency) and [`extras_require`](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#optional-dependencies) arguments to `setuptools.setup` where the extras sets are determined by a set of modules that should be optional.

## Table of contents

<!-- @import "[TOC]" {cmd="toc" depthFrom=2 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

-   [Table of contents](#table-of-contents)
-   [Running Import Tracker](#running-import-tracker)
-   [Integrating `import_tracker` into a project](#integrating-import_tracker-into-a-project)
    -   [Enabling `lazy_import_errors`](#enabling-lazy_import_errors)
    -   [Using `setup_tools.parse_requirements`](#using-setup_toolsparse_requirements)
-   [Gotchas](#gotchas)
    -   [Minor issue with zsh](#minor-issue-with-zsh)

<!-- /code_chunk_output -->

## Running Import Tracker

To run `import_tracker` against a project, simply invoke the module's main:

```
python3 -m import_tracker --name <my_module>
```

The main supports the following additional arguments:

-   `--package`: Allows `--name` to be a relative import (see [`importlib.import_module`](https://docs.python.org/3/library/importlib.html#importlib.import_module))
-   `--indent`: Indent the output json for pretty printing
-   `--log_level`: Set the level of logging (up to `debug4`) to debug unexpected behavior
-   `--submodules`: List of sub-modules to recurse on (or full recursion when no args given)
-   `--track_import_stack`: Store the stack trace of imports belonging to the tracked module
-   `--detect_transitive`: Mark each dependency as either "direct" (imported directly) or "transitive" (inherited from a direct import)
-   `--full_depth`: Track all dependencies, including transitive dependencies of direct third-party deps
-   `--show_optional`: Show whether each dependency is optional or required

## Integrating `import_tracker` into a project

When using `import_tracker` to implement optional dependencies in a project, there are two steps to take:

1. Enable `lazy_import_errors` for the set of modules that should be managed as optional
2. Use `setup_tools.parse_requirements` in `setup.py` to determine the `install_requires` and `extras_require` arguments

In the following examples, we'll use a fictitious project with the following structure:

```
my_module/
├── __init__.py
├── utils.py
└── widgets
    ├── __init__.py
    ├── widget1.py
    └── widget2.py
```

### Enabling `lazy_import_errors`

The `import_tracker.lazy_import_errors` function can be invoked directly to enable lazy import errors globally, or used as a context manager to enable them only for a selcted set of modules.

To globally enable lazy import errors, `my_module/__init__.py` would look like the following:

```py
# Globally enable lazy import errors
from import_tracker import lazy_import_errors
lazy_import_errors()

from . import utils, widgets
```

Alternately, applying lazy import error semantics only to the `widgets` would look like the following:

```py
from import_tracker import lazy_import_errors

# Require all downstream imports from utils to exist
from . import utils

# Enable lazy import errors for widgets
with lazy_import_errors():
    from . import widgets
```

When using lazy import errors, there are two ways to customize the error message that is raised when a failed import is used:

1.  1. The `get_extras_modules` argument takes a function which returns a `Set[str]` of the module names that are tracked as extras. If the import error is triggered within a module that is managed as an extras set, the error message is updated to include instructions on which extras set needs to be installed.

2.  The `make_error_message` argument allows the caller to specify a fully custom error message generation function.

### Using `setup_tools.parse_requirements`

To take advantage of the automatic dependency parsing when building a package, the `setup.py` would look like the following:

```py
import import_tracker
import os
import setuptools

# Determine the path to the requirements.txt for the project
requirements_file = os.path.join(os.path.dirname(__file__), "requirements.txt")

# Parse the requirement sets
install_requires, extras_require = import_tracker.setup_tools.parse_requirements(
    requirements_file=requirements_file,
    library_name="my_module",
    extras_modules=[
        "my_module.widgets.widget1",
        "my_module.widgets.widget2",
    ],
)

# Perform the standard setup call
setuptools.setup(
    name="my_module",
    author="me",
    version="1.2.3",
    license="MIT",
    install_requires=install_requires,
    extras_require=extras_require,
    packages=setuptools.find_packages(),
)
```

## Gotchas

### Minor issue with zsh

As mentioned before, when using lazy import errors in `import_tracker`, if the import error is triggered within a module that is managed as an extras set, the error message is updated to include instructions on which extras set needs to be installed. The error message might look something like this:

```bash
ModuleNotFoundError: No module named 'example_module'.

To install the missing dependencies, run `pip install my_module[my_module.example_module]`

```

There might be an issue when running `pip install my_module[my_module.example_module]` within a `zsh` environment, since square brackets in `zsh` have special meanings. We have to escape them by putting \ (`backslash`) before them. So for `zsh`, something like this will work:

```
pip install my_module\[my_module.example_module\]
```
