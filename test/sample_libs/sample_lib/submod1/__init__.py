"""
Sample sub-module that requires numpy
"""

# Third Party
import numpy
import sample_lib_conditional_deps


def make_arr(thing):
    return numpy.array(thing)


def check_tf():
    sample_lib_conditional_deps.mod.has_tf()
