"""
This top-level module conditionally imports some other sub modules in a way that
tracks their third party deps
"""

# Local
from . import setup_tools
from .import_tracker import (
    BEST_EFFORT,
    LAZY,
    MODE_ENV_VAR,
    PROACTIVE,
    TRACKING,
    LazyModule,
    default_import_mode,
    get_required_imports,
    get_required_packages,
    get_tracked_modules,
    import_module,
    set_static_tracker,
)
from .lazy_import_errors import lazy_import_errors
