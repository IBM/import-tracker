"""
This sample module uses import tracker's lazy_import_errors
"""

# Local
import import_tracker

with import_tracker.lazy_import_errors():
    # Local
    from . import foo
