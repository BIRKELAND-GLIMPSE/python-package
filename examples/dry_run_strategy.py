

from __future__ import annotations

import asyncio

from glimpse_markets import (
    AsyncClient,
    EnterMultiTopicLegGroup,
    MarketUpdate,
    Strategy,
    StrategyRunner,
    TradeLeg,
)


class LogAndEstimateStrategy(Strategy):

    def __init__(self) -> None:
        self.quote_count = 0
        self.tick_count = 0
        self._last_topic_id: int | None = None
        self._last_option_id: int | None = None

    async def on_start(self) -> None:
        print("strategy starting (dry_run — no real orders will be placed)")

    async def on_quote(self, update: MarketUpdate) -> None:
        self.quote_count += 1
        if update.data and update.data.quotes:
            self._last_topic_id = update.topic_id
            self._last_option_id = update.data.quotes[0].option_id
        elif update.data and update.data.binary_quotes:
            self._last_topic_id = update.topic_id
            self._last_option_id = update.data.binary_quotes[0].option_id
        print(f"quote #{self.quote_count}: topic_id={update.topic_id}")

    async def on_tick(self) -> None:
        self.tick_count += 1
        print(f"tick #{self.tick_count} — {self.quote_count} quotes seen so far")
        if self.tick_count % 3 == 0 and self._last_topic_id is not None:
            topics = [
                EnterMultiTopicLegGroup(
                    topic_id=self._last_topic_id,
                    legs=[TradeLeg(option_id=self._last_option_id, contracts=1)],
                )
            ]
            result = await self.client.enter_multi_topic_multi_leg(topics)
            print(f"  dry-run buy on topic {self._last_topic_id}: {result}")


async def main() -> None:
    client = AsyncClient(dry_run=True, timeout=15)
    strategy = LogAndEstimateStrategy()
    runner = StrategyRunner(strategy, client=client, tick_interval=5.0)
    try:
        await asyncio.wait_for(runner.run(), timeout=20)
    except TimeoutError:
        print(
            f"stopping after 20s demo window — saw {strategy.quote_count} quotes, "
            f"{strategy.tick_count} ticks"
        )
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
