"""
This sample library includes a "third party" library as optional which itself
includes a different "third party" library as non-optional. The transitive
third party should also be considered optional since the interim link in the
import chain is optional.
"""

try:
    # Third Party
    import single_extra
except ImportError:
    print("nothing to see here!")
