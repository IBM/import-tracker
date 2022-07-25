"""
This sample lib explicitly exercises ALL different flavors of import statements
to ensure that the bytecode parsing is handling them correctly.

NOTE: This does _not_ handle dynamic importing via importlib!
"""

## Third Party #################################################################

# Third Party
# Import with a *
from inter_mod_deps import *

# Import local module with a fully qualified name (ug)
import all_import_types.sub_module3

# First Party
# Import multiple attributes in the same from statement
# Import non-module attribute
from alog import AlogFormatterBase, alog, configure

# Local
# Import sibling module defined in dir w/ __init__.py
# NOTE: This module imports with .. to import submod1
# Import sibling module defined in file
# NOTE: This module imports with .. to import submod2
from . import sub_module1, sub_module2

# Import nested submodule with a "from" clause
from sample_lib import submod2

# Directly import
import sample_lib

# Directly import nested submodule
import sample_lib.submod1

## Local #######################################################################
