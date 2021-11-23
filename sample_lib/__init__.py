"""
Sample library to test out the import_tracker functionality
"""

from import_tracker import import_module as _import_module

# Use the import tool to import and track the sub modules
submod1 = _import_module(".submod1", __name__)
submod2 = _import_module(".submod2", __name__)
