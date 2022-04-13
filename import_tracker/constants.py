"""
Shared constants across the various parts of the library
"""

# Standard
import sys

# The name of this package (import_tracker)
THIS_PACKAGE = sys.modules[__name__].__package__.partition(".")[0]
