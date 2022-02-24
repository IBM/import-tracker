"""
This module a collection of submodules which exercise different corner cases
around inter-dependency between modules:

* submod1: Single external import
* submod2: Imports submod1 + external
    * Needs to have the union of submod1 + external lib
* submod3: Imports submod2
    * Needs to transitively import submod1
* submod4: Imported after the others, but does not depend on them
    * Should NOT pick up deps from others
* submod5: Import a nested module from an earlier sibling
    * Should trigger logic to pop sibling from sys.module
"""

# Local
from . import submod1, submod2, submod3, submod4, submod5
