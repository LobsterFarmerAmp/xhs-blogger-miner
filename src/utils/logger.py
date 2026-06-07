from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(
    name: str = "xhs_miner",
    level: str = "INFO",
    data_path: str | Path = "data",
) -> logging.Logger:
    log_dir = Path(data_path) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(_coerce_level(level))
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(_coerce_level(level))

    file_handler = RotatingFileHandler(
        log_dir / "xhs_miner.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(_coerce_level(level))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return logger


def _coerce_level(level: str) -> int:
    return getattr(logging, str(level).upper(), logging.INFO)
