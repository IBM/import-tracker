"""
Sample sub-module that requires numpy
"""

# Local
import conditional_deps


def check_tf():
    conditional_deps.mod.has_tf()
