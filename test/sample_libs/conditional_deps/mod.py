"""
Sample of how downstream libs may choose to write conditional dependencies. We
need to make sure that this doesn't break.
"""

try:
    import foobar as fb
    HAS_FB = True
except ModuleNotFoundError:
    HAS_FB = False


def has_fb():
    if HAS_FB:
        print("We've got the foo!")
    else:
        print("No foo here")
