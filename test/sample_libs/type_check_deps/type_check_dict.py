# Standard
from typing import Dict

# Local
import import_tracker

with import_tracker.lazy_import_errors():
    # Third Party
    from foo.bar import Bar

    def dummy_type_func(var) -> Dict[str, Bar]:
        pass
