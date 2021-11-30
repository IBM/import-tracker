# Standard
import os

# First Party
import alog

alog.configure(os.environ.get("LOG_LEVEL", "info"))
alog.use_channel("SUB2").info("Hello there!")
