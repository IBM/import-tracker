"""
This top-level module conditionally imports some other sub modules in a way that
tracks their third party deps
"""

# First import to set the bar for the baseline standard modules
from .import_tracker import (
    get_required_imports,
    get_required_packages,
    import_module,
    set_static_tracker,
)
