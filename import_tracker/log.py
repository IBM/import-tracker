"""
This module holds a shared logging instance handle to use in the other modules.
This log handle has additional higher-order logging functions defined that align
with the levels for alog (https://github.com/IBM/alchemy-logging).
"""

# Standard
import logging

log = logging.getLogger("IMPRT")

# Add higher-order logging
setattr(
    log, "debug1", lambda *args, **kwargs: log.log(logging.DEBUG - 1, *args, **kwargs)
)
setattr(
    log, "debug2", lambda *args, **kwargs: log.log(logging.DEBUG - 2, *args, **kwargs)
)
setattr(
    log, "debug3", lambda *args, **kwargs: log.log(logging.DEBUG - 3, *args, **kwargs)
)
setattr(
    log, "debug4", lambda *args, **kwargs: log.log(logging.DEBUG - 4, *args, **kwargs)
)
