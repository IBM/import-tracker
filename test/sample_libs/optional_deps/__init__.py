"""
This sample library has two dependencies: alog and yaml. The alog dependency is
held as optional in optional_deps.opt and as non-optional in
optional_deps.not_opt. The yaml dependency is held as optional in
optional_deps.not_opt, but it imported _directly_ in the root of optional_deps.
The resulting tracking should indicate that yaml is not optional everywhere
while alog is optional in opt and nowhere else.
"""

# Third Party
import yaml

# Local
from . import not_opt, opt
