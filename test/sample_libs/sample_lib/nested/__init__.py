"""
Sample of a nested module where the lazy importing happens one level down
"""

# Local
from . import submod3
from import_tracker import import_module as _import_module
