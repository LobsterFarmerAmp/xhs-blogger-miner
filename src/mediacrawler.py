from __future__ import annotations

import os
import sys
from pathlib import Path

MEDIACRAWLER_PATH = Path(
    os.getenv("MEDIACRAWLER_PATH") or Path.home() / ".openclaw" / "tools" / "MediaCrawler"
).expanduser()


def ensure_mediacrawler_path() -> None:
    """Make MediaCrawler imports resolve before this project's config directory."""
    path = str(MEDIACRAWLER_PATH)
    if path not in sys.path:
        sys.path.insert(0, path)

    for module_name in list(sys.modules):
        if module_name != "config" and not module_name.startswith("config."):
            continue
        module = sys.modules[module_name]
        module_file = str(getattr(module, "__file__", "") or "")
        if module_file.startswith(path):
            continue
        sys.modules.pop(module_name, None)
