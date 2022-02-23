"""
This module has two submodules and the second depends on the first. This
exercises the case where submod1 is deferred, but later needs to be imported by
submod2 in order to be tracked correctly.
"""

# Local
from . import submod1, submod2
