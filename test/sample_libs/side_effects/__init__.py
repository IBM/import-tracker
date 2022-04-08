"""
This sample module is an example of a library which uses import-time side
effects. It does so by having `global_thing` modify a central object on the base
module and then requiring that step in the import of `mod`.
"""

GLOBAL_RESOURCE = []

# Local
# Import mod second which requires GLOBAL_RESOURCE to be populated
# Import global_thing first to populate GLOBAL_RESOURCE
from . import global_thing, mod
