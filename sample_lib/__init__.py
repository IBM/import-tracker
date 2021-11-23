"""
Sample library to test out the import_tracker functionality
"""

from import_tracker import import_module

# Use the import tool to import and track the sub modules
submod1 = import_module(".submod1", __name__)
submod2 = import_module(".submod2", __name__)

__all__ = ["submod1", "submod2"]
