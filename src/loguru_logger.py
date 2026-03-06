import os
import sys
from loguru import logger

logger.remove()

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

logger.add(
    os.path.join(_LOG_DIR, "main.log"),
    rotation="100 MB",
    enqueue=True,
    compression="zip",
    backtrace=True,
    diagnose=True,
    encoding="utf-8"
)

logger.add(
    sys.stderr,
    level="DEBUG",
    enqueue=True,
    format="{time:HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True
)