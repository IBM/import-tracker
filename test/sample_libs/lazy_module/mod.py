# Local
from .lazy_deps import alog

# Calling __getattr__ here triggers the lazy import at import time!
log = alog.use_channel("foobar")
