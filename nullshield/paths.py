from __future__ import annotations

import os
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def templates_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", app_dir())) / "templates"
    return app_dir() / "templates"


CONFIG_FILE = app_dir() / "display_config.json"
OUTPUT_DIR = app_dir() / "output"
