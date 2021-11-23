"""
This top-level module conditionally imports some other sub modules in a way that
tracks their third party deps
"""

# First import to set the bar for the baseline standard modules
from ._import_util import get_required_imports, get_required_packages, import_module

# Use the import tool to import and track the sub modules
submod1 = import_module(".submod1", __name__)
submod2 = import_module(".submod2", __name__)
