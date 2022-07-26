# Standard
import sys

try:
    # First Party
    import alog

    print("imported alog!")
except ImportError:
    print("Can't import alog")
except:
    print("Double except, just to be sure!")
finally:
    HAVE_ALOG = "alog" in sys.modules


try:
    # Third Party
    import yaml
finally:
    HAVE_YAML = "yaml" in sys.modules
