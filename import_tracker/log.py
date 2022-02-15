"""
This module holds a shared logging instance handle to use in the other modules.
This log handle has additional higher-order logging functions defined that align
with the levels for alog (https://github.com/IBM/alchemy-logging).
"""

# Standard
import logging

log = logging.getLogger("IMPRT")

# Add higher-order levels as constants to logging
setattr(logging, "DEBUG1", logging.DEBUG - 1)
setattr(logging, "DEBUG2", logging.DEBUG - 2)
setattr(logging, "DEBUG3", logging.DEBUG - 3)
setattr(logging, "DEBUG4", logging.DEBUG - 4)

# Add higher-order logging
setattr(log, "debug1", lambda *args, **kwargs: log.log(logging.DEBUG1, *args, **kwargs))
setattr(log, "debug2", lambda *args, **kwargs: log.log(logging.DEBUG2, *args, **kwargs))
setattr(log, "debug3", lambda *args, **kwargs: log.log(logging.DEBUG3, *args, **kwargs))
setattr(log, "debug4", lambda *args, **kwargs: log.log(logging.DEBUG4, *args, **kwargs))
