"""Central logging setup for ModelScout.

Import `configure_logging()` once (agent.py does this on import, and app.py
imports agent.py) so every module logs in the same format, with timestamps,
to both the console and ./logs/modelscout.log. The log file is truncated
each time the process starts, so it only ever holds the current run/session.
"""

import logging
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "modelscout.log"
FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    _configured = True

    LOG_DIR.mkdir(exist_ok=True)
    formatter = logging.Formatter(FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(console_handler)
    root.addHandler(file_handler)
