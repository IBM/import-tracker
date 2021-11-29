"""
Sample of how downstream libs may choose to write conditional dependencies. We
need to make sure that this doesn't break.
"""

try:
    import tensorflow as tf
    HAS_TF = True
except ModuleNotFoundError:
    HAS_TF = False


def has_tf():
    if HAS_TF:
        print("We've got the flow!")
    else:
        print("No flow here")
