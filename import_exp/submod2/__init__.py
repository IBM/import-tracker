import alog
import os
alog.configure(os.environ.get("LOG_LEVEL", "info"))
alog.use_channel("SUB2").info("Hello there!")
