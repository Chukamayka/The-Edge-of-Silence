from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "TheEdgeOfSilence"


def _frozen_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    return Path(__file__).resolve().parent.parent


def resource_dir(relative: str) -> Path:
    base = _frozen_base_dir()
    # PyInstaller onedir often keeps resources under _internal.
    internal_candidate = base / "_internal" / relative
    if internal_candidate.exists():
        return internal_candidate
    return base / relative


def user_data_dir() -> Path:
    if os.name == "nt":
        root = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if root:
            path = Path(root) / APP_NAME
            path.mkdir(parents=True, exist_ok=True)
            return path
    path = Path.home() / f".{APP_NAME.lower()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    path = user_data_dir() / "config" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    path = user_data_dir() / "data" / "teos.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
