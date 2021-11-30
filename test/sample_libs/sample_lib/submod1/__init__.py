"""
Sample sub-module that requires numpy
"""

# Third Party
import numpy

# Local
import conditional_deps


def make_arr(thing):
    return numpy.array(thing)


def check_tf():
    conditional_deps.mod.has_tf()
