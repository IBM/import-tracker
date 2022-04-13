"""
This sample lib intentionally implements a bad import so that it can be used to
test lazy import errors
"""
# Local
import import_tracker


def get_extras_modules():
    return {"missing_dep.mod"}


with import_tracker.lazy_import_errors(get_extras_modules=get_extras_modules):
    # Local
    from . import mod, other
