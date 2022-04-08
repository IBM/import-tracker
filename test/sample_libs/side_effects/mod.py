"""
This module requires that GLOBAL_RESOURCE has at least one valid element
"""

# Local
from . import GLOBAL_RESOURCE

assert GLOBAL_RESOURCE, "I need my side effects!"
