"""
Sample of a nested module where the lazy importing happens one level down
"""

from import_tracker import import_module as _import_module

submod3 = _import_module(".submod3", __name__)
