"""
Tests for the lazy_import_errors functionality
"""

# Standard
from types import ModuleType
import os
import pickle
import shlex
import subprocess
import sys
import tempfile

# Third Party
import pytest

# Local
from import_tracker.lazy_import_errors import _LazyErrorMetaFinder
import import_tracker


@pytest.fixture
def reset_lazy_import_errors():
    yield
    while sys.meta_path and isinstance(sys.meta_path[-1], _LazyErrorMetaFinder):
        sys.meta_path.pop()


######################## Tests for Direct Invocation of the Context Manager #######################
def test_lazy_import_sad_package():
    """This test makes sure that the ModuleNotFoundError is not raised for an
    unknown module on import, but that it is raised on attribute access.

    This version tests that this is true when imported directly, but wrapped in
    lazy_import_errors.
    """
    with import_tracker.lazy_import_errors():
        # Third Party
        import foobarbaz
    with pytest.raises(ModuleNotFoundError):
        foobarbaz.foo()


def test_lazy_import_happy_package_with_sad_optionals():
    """This test ensures that a library with traditional try/except conditional
    dependencies works as expected.

    This version tests that the import works when imported directly, but wrapped
    in lazy_import_errors.
    """
    # Standard
    import pickle

    with import_tracker.lazy_import_errors():
        # Local
        import conditional_deps
    assert not conditional_deps.mod.HAS_FB


def test_lazy_import_errors_direct_call(reset_lazy_import_errors):
    """Test that directly invoking lazy_import_errors as a function will
    globally perform the setup
    """
    import_tracker.lazy_import_errors()
    # Third Party
    import foobarbaz

    with pytest.raises(ModuleNotFoundError):
        foobarbaz.foo()


def test_lazy_import_error_with_from():
    """Test that the syntax 'from foo.bar import Baz' does raise lazily"""
    with import_tracker.lazy_import_errors():
        # Third Party
        from foo.bar import Baz

    # Define a class that has no operators so that the __r*__ operators can be
    # exercised
    class RTestStub:
        pass

    # Define some test cases that can't be formulated as lambdas
    def test_delete():
        class Foo:
            foo = Baz

        f = Foo()
        del f.foo

    def test_delitem():
        del Baz["asdf"]

    def test_get():
        class Foo:
            foo = Baz

        f = Foo()
        f.foo

    def test_set():
        class Foo:
            foo = Baz

        f = Foo()
        f.foo = 1

    def test_iadd():
        Baz.buz += 1

    def test_iand():
        Baz.buz &= 1

    def test_ifloordiv():
        Baz.buz //= 1

    def test_ilshift():
        Baz.buz <<= 1

    def test_ishift():
        Baz.buz >>= 1

    def test_imod():
        Baz.buz %= 1

    def test_imatmul():
        Baz.buz @= 1

    def test_imul():
        Baz.buz *= 1

    def test_ior():
        Baz.buz |= 1

    def test_ipow():
        Baz.buz **= 2

    def test_isub():
        Baz.buz -= 1

    def test_itruediv():
        Baz.buz /= 1

    def test_ixor():
        Baz.buz ^= 1

    def test_setitem():
        Baz.buz[1] = 1

    # Make sure that doing _anything_ with Baz does trigger the error
    for fn in [
        lambda: Baz(),
        lambda: Baz + 1,
        lambda: Baz * 2,
        lambda: Baz**2,
        lambda: Baz @ 2,
        lambda: Baz - 1,
        lambda: 1 - Baz,
        lambda: -Baz,
        lambda: +Baz,
        lambda: abs(Baz),
        lambda: Baz & True,
        lambda: Baz | True,
        lambda: 1 in Baz,
        lambda: delattr(Baz, "foo"),
        lambda: [x for x in Baz],
        lambda: Baz == Baz,
        lambda: Baz != Baz,
        lambda: int(Baz),
        lambda: float(Baz),
        lambda: str(Baz),
        lambda: Baz > 1,
        lambda: Baz >= 1,
        lambda: Baz < 1,
        lambda: Baz <= 1,
        lambda: hash(Baz),
        lambda: Baz[0],
        lambda: Baz / 2,
        lambda: Baz // 1,
        lambda: Baz << 1,
        lambda: Baz >> 1,
        lambda: Baz % 1,
        lambda: Baz ^ 1,
        lambda: ~Baz,
        lambda: [1, 2, 3][Baz],
        lambda: next(Baz),
        lambda: RTestStub() + Baz,
        lambda: RTestStub() & Baz,
        lambda: RTestStub() * Baz,
        lambda: RTestStub() / Baz,
        lambda: RTestStub() // Baz,
        lambda: RTestStub() % Baz,
        lambda: RTestStub() ^ Baz,
        lambda: RTestStub() @ Baz,
        lambda: RTestStub() << Baz,
        lambda: RTestStub() >> Baz,
        lambda: RTestStub() | Baz,
        lambda: RTestStub() ** Baz,
        test_delete,
        test_delitem,
        test_get,
        test_set,
        test_iadd,
        test_iand,
        test_ifloordiv,
        test_ilshift,
        test_ishift,
        test_imod,
        test_imatmul,
        test_imul,
        test_ior,
        test_ipow,
        test_isub,
        test_itruediv,
        test_ixor,
        test_setitem,
    ]:
        with pytest.raises(ModuleNotFoundError):
            fn()

    # Make sure it cannot be pickled
    with pytest.raises(pickle.PicklingError):
        pickle.dumps(Baz)


@pytest.mark.asyncio
async def test_lazy_import_error_with_from_async():
    """Test that the async operators also raise"""
    with import_tracker.lazy_import_errors():
        # Third Party
        from foo.bar import Baz

    # Make sure that doing _anything_ with Baz does trigger the error
    for fn in [
        lambda: Baz,
        # These two are really hard to exercise, so we'll just test them
        # directly
        lambda: Baz.__aiter__(),
        lambda: Baz.__anext__(),
    ]:
        with pytest.raises(ModuleNotFoundError):
            await fn()


def test_lazy_import_error_attr_pickle():
    """Test that when deserializing a pickled object created using a class that
    is not available at unpickling time due to a missing module, an appropriate
    ModuleNotFoundError is raised from the _LazyErrorAttr class that fills in
    for the missing type. This one is pretty niche since pickling will actually
    pickle the contents of the class itself. The error only occurs if the class
    relies on _another_ module that is not available at unpickling time.
    """
    with tempfile.TemporaryDirectory() as workdir:
        mod1 = os.path.join(workdir, "some_module.py")
        with open(mod1, "w") as handle:
            handle.write(
                """
import pickle
from other_module import Bar

class Foo:
    def __init__(self):
        self.val = Bar(1)
"""
            )
        mod2 = os.path.join(workdir, "other_module.py")
        with open(mod2, "w") as handle:
            handle.write(
                """
class Bar:
    def __init__(self, val):
        self.val = val + 1
"""
            )
        out, _ = subprocess.Popen(
            shlex.split(
                f"{sys.executable} -c 'from some_module import Foo; import pickle; print(pickle.dumps(Foo()).hex())'"
            ),
            stdout=subprocess.PIPE,
            env={"PYTHONPATH": workdir},
        ).communicate()

    # Import the missing module
    with import_tracker.lazy_import_errors():
        # Third Party
        from some_module import Foo

    # Grab the pickled output
    pickled = bytes.fromhex(out.strip().decode("utf-8"))

    # Try to unpickle it
    with pytest.raises(ModuleNotFoundError):
        pickle.loads(pickled)


def test_lazy_import_error_attr_class_inheritance():
    """Test that when a lazily imported error attribute is used as a base class,
    the import error occurs when the derived class is instantiated.
    """
    with import_tracker.lazy_import_errors():
        # Third Party
        from foo.bar import Baz

    class Bat(Baz):
        def __init__(self, val):
            super().__init__(val)

    with pytest.raises(ModuleNotFoundError):
        Bat(1)


def test_lazy_import_error_infinite_attrs():
    """Make sure that a _LazyErrorAttr can recursively deliver infinite
    attributes to fill in arbitrary attrs on the parent module
    """
    with import_tracker.lazy_import_errors():
        # Third Party
        from foo.bar import Baz

        assert Baz.bat is Baz


def test_lazy_import_error_custom_error_msg():
    """Make sure that the lazy_import_errors context manager can be configured
    with a custom function for creating the error message.
    """
    custom_error_message = "This is a custom message!"

    def make_error_msg(*_, **__):
        return custom_error_message

    with import_tracker.lazy_import_errors(make_error_message=make_error_msg):
        # Third Party
        from foo.bar import Baz

    with pytest.raises(ModuleNotFoundError, match=custom_error_message):
        Baz()


def test_lazy_import_error_get_extras_modules():
    """Make sure that the lazy_import_errors context manager can be configured
    with a get_extras_modules function and perform the custom error message
    creation internally.
    """
    # Third Party
    import missing_dep

    # Using foobar inside missing_dep.mod should catch the custom error
    with pytest.raises(
        ModuleNotFoundError,
        match=r".*pip install missing_dep\[missing_dep.mod\].*",
    ):
        missing_dep.mod.use_foobar()

    # Using bazbat inside missing_dep.other should have the standard error since
    # missing_dep.other is not tracked as an extra
    with pytest.raises(
        ModuleNotFoundError,
        match="No module named 'bazbat'",
    ):
        missing_dep.other.use_bazbat()


def test_lazy_import_error_mutually_exclusive_args():
    """Make sure the args to lazy_import_errors are mutually exclusive"""
    with pytest.raises(TypeError):
        with import_tracker.lazy_import_errors(
            make_error_message=1,
            get_extras_modules=2,
        ):
            # Third Party
            import foobar


def test_frame_generator_stop():
    """For completeness, we need to ensure that the FrameGenerator will stop
    correctly if iterated to the end
    """
    list(_LazyErrorMetaFinder._FrameGenerator())


def test_lazy_import_error_nested():
    """Make sure the each lazy import errors only pops itself off of sys.metapath"""
    with import_tracker.lazy_import_errors():
        with import_tracker.lazy_import_errors():
            pass
        # Third Party
        import foobar


def test_lazy_import_error_modified_meta_path():
    """Make sure lazy import error works if sys.meta_path gets modified
    in between
    """

    class MockModule:
        def find_spec(self, *args, **kwargs):
            pass

    sys.meta_path.append(MockModule)
    with import_tracker.lazy_import_errors():
        with import_tracker.lazy_import_errors():
            pass
        # Third Party
        import foobar

    sys.meta_path.remove(MockModule)
