#!/usr/bin/env bash
set -euo pipefail

uv sync
uv run playwright install chromium
uv run python -c "from playwright.async_api import async_playwright; print('Playwright available')"
