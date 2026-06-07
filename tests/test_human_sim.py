import pytest

from src.miner.human_sim import HumanSimulator


@pytest.mark.asyncio
async def test_random_delay_uses_requested_range(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("src.miner.human_sim.asyncio.sleep", fake_sleep)
    sim = HumanSimulator()

    delay = await sim.random_delay(1.0, 2.0)

    assert 1.0 <= delay <= 2.0
    assert sleeps == [delay]


@pytest.mark.asyncio
async def test_random_delay_swaps_reversed_range(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("src.miner.human_sim.asyncio.sleep", fake_sleep)
    sim = HumanSimulator()

    delay = await sim.random_delay(5.0, 3.0)

    assert 3.0 <= delay <= 5.0
    assert sleeps == [delay]
