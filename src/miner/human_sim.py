from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class HumanSimulator:
    min_delay_sec: float = 3.0
    max_delay_sec: float = 10.0
    reading_min_sec: float = 8.0
    reading_max_sec: float = 20.0
    page_load_min_sec: float = 3.0
    page_load_max_sec: float = 8.0

    async def random_delay(self, min_s: float | None = None, max_s: float | None = None) -> float:
        lower = self.min_delay_sec if min_s is None else min_s
        upper = self.max_delay_sec if max_s is None else max_s
        if upper < lower:
            lower, upper = upper, lower
        delay = random.uniform(lower, upper)
        await asyncio.sleep(delay)
        return delay

    async def simulate_reading(self) -> float:
        return await self.random_delay(self.reading_min_sec, self.reading_max_sec)

    async def simulate_scroll(self, page: Any, total_scrolls: int = 5) -> None:
        for _ in range(max(total_scrolls, 0)):
            scroll_distance = random.randint(350, 1200)
            await page.mouse.wheel(0, scroll_distance)
            await self.random_delay(0.8, 2.5)

    async def move_mouse_randomly(self, page: Any) -> None:
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        width = int(viewport.get("width", 1280))
        height = int(viewport.get("height", 720))
        points = random.randint(2, 5)
        for _ in range(points):
            x = random.randint(0, max(width - 1, 1))
            y = random.randint(0, max(height - 1, 1))
            steps = random.randint(8, 30)
            await page.mouse.move(x, y, steps=steps)
            await self.random_delay(0.2, 0.8)

    async def human_page_load(self, page: Any) -> float:
        try:
            await page.wait_for_load_state("networkidle", timeout=30_000)
        except Exception:
            await page.wait_for_load_state("domcontentloaded", timeout=30_000)
        return await self.random_delay(self.page_load_min_sec, self.page_load_max_sec)
