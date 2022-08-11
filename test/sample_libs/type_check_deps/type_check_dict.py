import import_tracker
from typing import Dict

with import_tracker.lazy_import_errors():
    # Third Party
    from foo.bar import Bar

    def dummy_type_func(var) -> Dict[str, Bar]:
        pass
