"""
This module has a sub module that holds an invalid dependency which we want to
ensure doesn't break the ability to call the functionality that uses the good
dependencies.
"""
from import_tracker import import_module as _import_module
bad_import = _import_module(".bad_import", __name__)
