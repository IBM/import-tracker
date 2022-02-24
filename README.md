# Import Tracker

`Import Tracker` is a Python package offering a number of capabilities related to tracking and managing optional dependencies in Python projects. Specifically, this project enables developers to:

-   Track the dependencies of a python project to map each module within the project to the set of dependencies it relies on. This can be useful for debugging of dependencies in large projects.

-   Enable lazy import errors in a python projects to prevent code from crashing when uninstalled imports are imported, but not utilized. This can be helpful in large projects, especially those which incorporate lots of hierarchical wild imports, as importing the top level package of such projects can often bring a lot of heavy dependencies into `sys.modules`.

-   Programmatically determine the [`install_requires`](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#declaring-required-dependency) and [`extras_require`](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#optional-dependencies) arguments to `setuptools.setup` where the extras sets are determined by a set of modules that should be optional.

## Running Import Tracker

To run `import_tracker` against a project, simply invoke the module's main:

```
python3 -m import_tracker --name <my_module>
```

The main supports the following additional arguments:

-   `--package`: Allows `--name` to be a relative import (see [`importlib.import_module`](https://docs.python.org/3/library/importlib.html#importlib.import_module))
-   `--recursive`: Recurse into sub-modules within the given module to produce the full mapping for the given module
-   `--num_jobs`: When `--recurse` is given, run the recursive jobs concurrently with the given number of workers (0 implies serial execution)
-   `--indent`: Indent the output json for pretty printing
-   `--log_level`: Set the level of logging (up to `debug4`) to debug unexpected behavior

## Integrating `import_tracker` into a projects

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
