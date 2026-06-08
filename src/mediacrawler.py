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

    # Include MediaCrawler's own venv site-packages so its dependencies
    # (aiomysql, matplotlib, motor, etc.) resolve without us duplicating them.
    mediacrawler_site_packages = str(
        MEDIACRAWLER_PATH / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    )
    if mediacrawler_site_packages not in sys.path:
        sys.path.insert(0, mediacrawler_site_packages)

    # HACK: Pre-import tools submodules so that tools/utils.py's
    # `from .crawler_util import *` (etc.) resolves correctly when
    # tools.utils is later imported as part of the MediaCrawler chain.
    import importlib
    for _submod in ("tools.crawler_util", "tools.slider_util", "tools.time_util"):
        try:
            importlib.import_module(_submod)
        except Exception:
            pass

    # HACK: Clear cached 'config' modules to avoid namespace collision between
    # MediaCrawler's `config` package and our own `config/` directory. Without
    # this, Python may resolve `import config` to the wrong path. This affects
    # only modules whose __file__ is outside MEDIACRAWLER_PATH.
    # TODO: Long-term fix - give MediaCrawler a namespace-package config or
    # rename its config module to avoid the conflict entirely.
    for module_name in list(sys.modules):
        if module_name != "config" and not module_name.startswith("config."):
            continue
        module = sys.modules[module_name]
        module_file = str(getattr(module, "__file__", "") or "")
        if module_file.startswith(path):
            continue
        sys.modules.pop(module_name, None)
