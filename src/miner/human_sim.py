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

    async def _bezier_move(self, page: Any, target_x: int, target_y: int) -> None:
        """Move mouse along a cubic bezier curve to the target position."""
        import math as _math

        viewport = page.viewport_size or {"width": 1280, "height": 720}
        start_x = viewport.get("width", 1280) // 2
        start_y = viewport.get("height", 720) // 2
        cp1_x = start_x + random.randint(-200, 200)
        cp1_y = start_y + random.randint(-150, 150)
        cp2_x = target_x + random.randint(-100, 100)
        cp2_y = target_y + random.randint(-100, 100)
        steps = random.randint(20, 60)
        for i in range(steps + 1):
            t = i / steps
            x = int(
                (1 - t) ** 3 * start_x
                + 3 * (1 - t) ** 2 * t * cp1_x
                + 3 * (1 - t) * t**2 * cp2_x
                + t**3 * target_x
            )
            y = int(
                (1 - t) ** 3 * start_y
                + 3 * (1 - t) ** 2 * t * cp1_y
                + 3 * (1 - t) * t**2 * cp2_y
                + t**3 * target_y
            )
            await page.mouse.move(x, y, steps=1)
            await asyncio.sleep(random.uniform(0.001, 0.005))

    async def move_mouse_randomly(self, page: Any) -> None:
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        width = int(viewport.get("width", 1280))
        height = int(viewport.get("height", 720))
        points = random.randint(2, 5)
        for _ in range(points):
            x = random.randint(0, max(width - 1, 1))
            y = random.randint(0, max(height - 1, 1))
            await self._bezier_move(page, x, y)
            await self.random_delay(0.3, 1.0)

    async def simulate_typing(
        self,
        page: Any,
        text: str,
        wpm: int = 60,
        error_rate: float = 0.02,
    ) -> float:
        """Type text with human-like pacing and occasional errors.

        Args:
            page: Playwright Page object.
            text: The text to type.
            wpm: Words per minute (default 60).
            error_rate: Probability of making a typo (0.0-1.0, default 0.02).

        Returns:
            Total seconds spent typing.
        """
        base_delay = 60.0 / (wpm * 5)
        total_s = 0.0
        for char in text:
            if random.random() < error_rate:
                wrong = chr(ord(char) + random.choice([-1, 1]))
                await page.keyboard.type(wrong, delay=base_delay * random.uniform(0.5, 1.5))
                await asyncio.sleep(base_delay * random.uniform(1.0, 2.0))
                await page.keyboard.press("Backspace")
                await asyncio.sleep(base_delay * random.uniform(0.5, 1.0))
                total_s += base_delay * 3
            await page.keyboard.type(char, delay=base_delay * random.uniform(0.3, 2.0))
            total_s += base_delay
            if char == " " and random.random() < 0.15:
                pause = random.uniform(0.2, 0.8)
                await asyncio.sleep(pause)
                total_s += pause
        return total_s

    async def human_page_load(self, page: Any) -> float:
        try:
            await page.wait_for_load_state("networkidle", timeout=30_000)
        except Exception:
            await page.wait_for_load_state("domcontentloaded", timeout=30_000)
        return await self.random_delay(self.page_load_min_sec, self.page_load_max_sec)
