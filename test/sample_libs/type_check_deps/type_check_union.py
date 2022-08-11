import import_tracker
from typing import Union

with import_tracker.lazy_import_errors():
    # Third Party
    from foo import Bar

    def dummy_type_func(var) -> Union[str, Bar]:
        pass
