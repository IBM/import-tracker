import pytest
import os

import import_tracker
import importlib

######################## Tests for Direct Invocation of the Context Manager #######################
def test_lazy_import_sad_package():
    """This test makes sure that the ModuleNotFoundError is not raised for an
    unknown module on import, but that it is raised on attribute access.

    This version tests that this is true when imported directly, but wrapped in
    lazy_import_errors.
    """
    with import_tracker.lazy_import_errors():
        import foobarbaz
    with pytest.raises(ModuleNotFoundError):
        foobarbaz.foo()

def test_lazy_import_happy_package_with_sad_optionals():
    """This test uses `numpy` which has several "optional" dependencies in order
    to support backwards compatibility. We need to ensure that these usecases
    are supported such that the downstream libs do not get confused.

    This version tests that the import works when imported directly, but wrapped
    in lazy_import_errors.

    CITE: https://github.com/numpy/numpy/blob/main/numpy/compat/py3k.py#L24
    """
    standard_pickle = importlib.import_module("pickle")
    with import_tracker.lazy_import_errors():
        import numpy
        assert numpy.compat.py3k.pickle is standard_pickle

########################## Tests for Module Imports via Import Tracker ############################
def test_lazy_import_tracker_sad_package():
    """This test makes sure that the ModuleNotFoundError is not raised for an
    unknown module on import, but that it is raised on attribute access.

    This version tests that this is true when imported via
    import_tracker.import_module
    """
    foobarbaz = import_tracker.import_module('foobarbaz')
    with pytest.raises(ModuleNotFoundError):
        foobarbaz.foo()

def test_lazy_import_tracker_happy_package_with_sad_optionals():
    """This test uses `numpy` which has several "optional" dependencies in order
    to support backwards compatibility. We need to ensure that these usecases
    are supported such that the downstream libs do not get confused.

    This version tests that the import works when imported via
    import_tracker.import_module

    CITE: https://github.com/numpy/numpy/blob/main/numpy/compat/py3k.py#L24
    """
    standard_pickle = importlib.import_module("pickle")
    numpy = import_tracker.import_module('numpy')
    assert numpy.compat.py3k.pickle is standard_pickle
