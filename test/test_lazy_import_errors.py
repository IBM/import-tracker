import pytest
import os

import import_tracker
import importlib

######################## Tests for Direct Invocation of the Context Manager #######################
def test_lazy_import_sad_package():
    with import_tracker.lazy_import_errors():
        foobarbaz = importlib.import_module('foobarbaz')
    with pytest.raises(ModuleNotFoundError):
        foobarbaz.foo()

def test_lazy_import_happy_package_with_sad_optionals():
    standard_pickle = importlib.import_module("pickle")
    with import_tracker.lazy_import_errors():
        numpy = importlib.import_module('numpy')
        assert numpy.compat.py3k.pickle is standard_pickle

########################## Tests for Module Imports via Import Tracker ############################
def test_lazy_import_tracker_sad_package():
    foobarbaz = import_tracker.import_module('foobarbaz')
    with pytest.raises(ModuleNotFoundError):
        foobarbaz.foo()

def test_lazy_import_tracker_happy_package_with_sad_optionals():
    standard_pickle = importlib.import_module("pickle")
    numpy = import_tracker.import_module('numpy')
    assert numpy.compat.py3k.pickle is standard_pickle
