"""
Sample library to test out the import_tracker functionality
"""

# Local
# Set up a static file to track dependencies. This will be used when not in
# tracking mode instead of determining the dependencies directly
from import_tracker import set_static_tracker as _set_static_tracker

_set_static_tracker()

# Local
# Import the nested submodule
from .nested import submod3

# Use the import tool to import and track the sub modules
from import_tracker import import_module as _import_module

submod1 = _import_module(".submod1", __name__)
submod2 = _import_module(".submod2", __name__)
