# glimpse-markets

The official Python client for [Glimpse](https://docs.glimpse.markets)'s
Nmarket prediction-market API — for people building forecasting algorithms
and trading bots on Glimpse without writing HTTP plumbing by hand.

```bash
pip install glimpse-markets
```

> **Status:** every read endpoint, every trade endpoint, the `glimpse` CLI,
> an async client, real-time streaming, and a small bot-building layer are
> all implemented.

## Contents

- [Installation](#installation)
- [Features](#features)
- [Quickstart](#quickstart)
- [Trading](#trading)
- [Paper trading (dry run)](#paper-trading-dry-run)
- [Async client](#async-client)
- [Real-time streaming](#real-time-streaming)
- [Building a bot](#building-a-bot)
- [Forecasting](#forecasting)
- [CLI](#cli)
- [Units: millisats vs. price](#units-millisats-vs-price)
- [Error handling](#error-handling)
- [Development](#development)
- [License](#license)

## Installation

```bash
pip install glimpse-markets
```

This one command gets you the full client, the `glimpse` CLI, real-time
streaming, the bot-building layer, and the pure-Python half of the
forecasting toolkit (`MarketRecorder`, `bucket_probabilities`, `edge`) —
everything in this README except the two pieces below.

**Two optional extras sit alongside it, installed the same way, whenever
you actually want them:**

| Extra | Install | Unlocks |
|---|---|---|
| `forecasting` | `pip install glimpse-markets[forecasting]` | `TimesFMForecaster` — Google TimesFM 2.5 point + quantile forecasting (pulls in PyTorch) |
| `yfinance` | `pip install glimpse-markets[yfinance]` | `fetch_yfinance_history()` — real BTC/ETH/PAX-Gold price history from Yahoo Finance |

Install either independently, both together (`pip install
"glimpse-markets[forecasting,yfinance]"`), or neither — the base package
never requires them, and nothing breaks if you skip them. `glimpse --help`
prints a reminder about both any time you want to check what's available.
See [Forecasting](#forecasting) for what each one actually does and the
one licensing caveat worth reading before using `yfinance`.

## Features

- **Sync and async clients** with an identical method surface — every
  market-data, portfolio, and trading endpoint the public API exposes.
- **Typed responses.** Every call returns a [Pydantic](https://docs.pydantic.dev)
  model, not a raw dict — autocomplete and validation instead of
  `resp["message"]["..."]`.
- **Built-in paper trading.** Glimpse has no sandbox environment — every API
  key is a live key. `dry_run=True` simulates trades client-side through the
  free `/trades/estimate` endpoint, so you can test a strategy against real
  live prices without risking real funds.
- **Real-time market data** over Glimpse's WebSocket feed, with no polling
  loop to write yourself.
- **A minimal bot-building layer** (`Strategy` / `StrategyRunner`) for
  wiring strategy logic up to the live feed without hand-rolling the
  connect/dispatch/reconnect plumbing.
- **A `glimpse` CLI** for one-off calls from the terminal — check a
  balance, get a quote, place a trade — without writing any code.
- **Safety around the sharp edges.** The API has no idempotency key, so a
  network failure mid-trade is surfaced as a distinct
  `GlimpseAmbiguousTradeStateError` instead of being silently retried (which
  could double-execute a real trade) or silently swallowed.

## Quickstart

```python
from glimpse_markets import Client

with Client(api_key="glp_live_...") as client:
    print(client.wallet_balance())

    batch = client.batches().batches[0]
    print(client.batch_active_markets(batch.batch_id))

# Market-data endpoints (batches, markets, quotes, stats) are public --
# no API key needed:
with Client() as client:
    print(client.market_quotes(topic_id=6674))
```

Or configure from the environment (`GLIMPSE_API_KEY`, `GLIMPSE_BASE_URL`),
optionally via a `.env` file in your working directory:

```python
from glimpse_markets import Client

with Client.from_env() as client:
    print(client.portfolio_summary())
```

Generate an API key from your Glimpse account under **Settings → Developer
API Keys**.

## Trading

```python
from glimpse_markets import Client, TradeLeg, EnterMultiTopicLegGroup

with Client.from_env() as client:
    # Always check cost and price impact first -- free, no API key required.
    estimate = client.estimate_trade(6674, "buy", [TradeLeg(option_id=500, contracts=10)])
    print(estimate)

    topics = [EnterMultiTopicLegGroup(topic_id=6674, legs=[TradeLeg(option_id=500, contracts=10)])]
    result = client.enter_multi_topic_multi_leg(topics)
    print(result)

    client.exit_consolidated(topic_id=6674, option_id=500)  # exits the full position
```

Entering a position is buy-only, by design of the underlying API — exit an
existing position to realize a "sell." `exit_consolidated_multi`,
`exit_multi_topic_multi_leg`, and `exit_batch` cover multi-leg and
whole-batch exits.

## Paper trading (dry run)

Glimpse has no sandbox environment — every API key trades with real funds.
Pass `dry_run=True` (client-wide, or per call via `dry_run=...` on any trade
method) to paper-trade instead: every `enter`/`exit` call is priced through
the side-effect-free `/trades/estimate` endpoint rather than placing a real
order, and returns a `DryRunTradeResult` — a distinct type from a real
response, so a simulated fill can never be mistaken for a real one:

```python
with Client.from_env(dry_run=True) as client:
    result = client.enter_multi_topic_multi_leg(topics)
    assert result.simulated is True  # no order was placed
```

A network failure while an `enter`/`exit` call is genuinely in flight
raises `GlimpseAmbiguousTradeStateError` rather than being retried — the API
has no idempotency key, so the client can't safely guess whether the trade
went through. Check `client.portfolio_active()` before resubmitting.

## Async client

`AsyncClient` mirrors `Client`'s entire method surface — same names, same
signatures, `await` in front — built on `httpx.AsyncClient`, for bots
already running an asyncio event loop:

```python
import asyncio
from glimpse_markets import AsyncClient, TradeLeg

async def main():
    async with AsyncClient.from_env() as client:
        print(await client.wallet_balance())
        estimate = await client.estimate_trade(6674, "buy", [TradeLeg(option_id=500, contracts=10)])
        print(estimate)

asyncio.run(main())
```

## Real-time streaming

Glimpse pushes live quote updates over a public WebSocket feed — no API key
required, no polling loop to write:

```python
import asyncio
from glimpse_markets import AsyncClient

async def main():
    async with AsyncClient() as client:
        async with client.stream_market_updates(topic_id=6674) as stream:
            async for update in stream:
                print(update.data.quotes or update.data.binary_quotes)

asyncio.run(main())
```

Pass `topic_id` and/or `batch_id` to filter the feed to one market or batch
(call `stream.subscribe(...)` again later to change the filter without
reconnecting); pass neither to receive every market's updates. There is
**no separate "market resolved" event on this feed** — detect resolution by
polling `quote_mode` via `market_quotes()` or `batch_active_markets_page()`
instead.

`MarketStream` also works standalone: `from glimpse_markets import MarketStream`.

## Building a bot

`Strategy` and `StrategyRunner` wire a `MarketStream` up to your logic
without you writing the connect/dispatch/reconnect plumbing yourself:

```python
import asyncio
from glimpse_markets import AsyncClient, MarketUpdate, Strategy, StrategyRunner

class MyStrategy(Strategy):
    async def on_quote(self, update: MarketUpdate) -> None:
        # called for every market_update from the stream
        print(update.topic_id, update.data.quotes)

    async def on_tick(self) -> None:
        # called every `tick_interval` seconds, independent of quote events
        positions = await self.positions.get()  # cached portfolio_active()
        print(f"{len(positions)} open positions")

async def main():
    client = AsyncClient.from_env(dry_run=True)  # paper-trade by default
    runner = StrategyRunner(MyStrategy(), client=client, topic_id=6674, tick_interval=5.0)
    await runner.run()

asyncio.run(main())
```

`self.client` (the `AsyncClient`) and `self.positions` (a `PositionTracker`)
are available inside any hook — place trades with the former, check current
positions with the latter without re-fetching your whole portfolio on every
quote tick. `PositionTracker` caches `portfolio_active()` and refreshes at
most once every few seconds; call `self.positions.invalidate()` right after
placing a trade to force a fresh read.

An exception raised from `on_quote` or `on_tick` stops the runner and
propagates out of `run()` — a strategy bug fails loud instead of getting
silently swallowed. See [`examples/dry_run_strategy.py`](./examples/dry_run_strategy.py)
for a complete, runnable example.

## Forecasting

Glimpse has no historical/candle data endpoint as of now(we will patch this in very soon), so any forecasting story
here has to start with data acquisition, not just a model wrapper.
`glimpse_markets.forecasting` (importable without any extra dependencies —
only actually running a forecast needs one) provides:

- **`MarketRecorder`** — builds a local price history from `MarketStream`,
  since that's the SDK's only source of historical data. Updates are
  event-driven (fired on trades, not a fixed clock tick), so use
  `resampled_prices_for()` for an evenly spaced series rather than feeding
  the raw irregular one to a forecaster.
- **`TimesFMForecaster`** — wraps Google's [TimesFM 2.5](https://github.com/google-research/timesfm)
  for point + quantile forecasting. Requires `pip install
  glimpse-markets[forecasting]` (pulls in PyTorch). **Deliberately targets
  2.5, not the newer 3.0** — TimesFM 3.0's pretrained weights are licensed
  for non-commercial, non-production use only, which rules them out for a
  package whose purpose is real trading bots; 2.5 and earlier remain
  Apache-2.0.
- **`bucket_probabilities()` / `probability_between()` / `edge()`** — maps
  a decile forecast onto Glimpse's bucketed-option markets (parsing names
  like `"64000-65000"`) and compares the model-implied probability to the
  live LMSR price. Pure Python, model-agnostic — works with
  `TimesFMForecaster`'s output, or with your own forecast of the
  *underlying asset* from whatever external price-data source you already
  use (this package doesn't pick a vendor for that)...
- **...except `fetch_yfinance_history()`**, the one deliberate exception —
  a convenience adapter for pulling real BTC/ETH/PAX-Gold price history
  from Yahoo Finance via `yfinance`, for forecasting the *underlying asset*
  Glimpse's markets track rather than Glimpse's own quote history. Requires
  `pip install glimpse-markets[yfinance]` (a separate extra from
  `forecasting`, since you may want one without the other). **Read this
  before using it:** Yahoo's own terms describe their finance data as
  personal-use-only (stated twice, in bold, in `yfinance`'s own README) —
  fine for research and development, but check Yahoo's actual terms
  yourself before relying on it for anything commercial. Not installed by
  default, and never will be without you opting in explicitly.

```python
import asyncio
from glimpse_markets import AsyncClient
from glimpse_markets.forecasting import MarketRecorder, TimesFMForecaster, bucket_probabilities

async def main():
    recorder = MarketRecorder(persist_path="btc_7120.ndjson")
    async with AsyncClient() as client:
        async with client.stream_market_updates(topic_id=7120) as stream:
            async for update in stream:
                recorder.record(update)
                # once you've accumulated enough history:
                # series = recorder.resampled_prices_for(7120, option_id, interval_seconds=60)
                # forecast = TimesFMForecaster().forecast(series, horizon=60)
                # quotes = await client.market_quotes(7120)
                # for s in bucket_probabilities(quotes.outcomes, forecast.deciles_at(-1)):
                #     print(s.name, s.market_price, s.model_probability, s.edge)

asyncio.run(main())
```

`edge()` is a raw signal, not investment advice — it says nothing about
confidence, fees, slippage, or whether the model itself is any good.

Forecasting the underlying asset instead of Glimpse's own quotes (read the
license note above first):

```python
from glimpse_markets.forecasting import fetch_yfinance_history, TimesFMForecaster, bucket_probabilities

btc_history = fetch_yfinance_history("BTC-USD", period="60d", interval="1h")
forecast = TimesFMForecaster().forecast(btc_history, horizon=24)

quotes = client.market_quotes(7120)  # a Daily Bitcoin Markets topic
for s in bucket_probabilities(quotes.outcomes, forecast.deciles_at(-1)):
    print(s.name, s.market_price, s.model_probability, s.edge)
```

## CLI

The `glimpse` command covers the same ground as the Python client, for
one-off calls from the terminal. Config comes from `GLIMPSE_API_KEY` /
`GLIMPSE_BASE_URL`, read from the environment or a `.env` file in the
current directory.

```bash
glimpse balance

glimpse portfolio active
glimpse portfolio summary
glimpse portfolio ended [--limit N --offset N]
glimpse portfolio resolved [--limit N --offset N]

glimpse batches                       # list all batches
glimpse batches --batch-id <id>       # active markets in a batch
glimpse quotes --topic-id <id>

glimpse estimate --topic-id <id> --type buy --leg 500:10 [--leg 501:5]
glimpse execute --topic-id <id> --leg 500:10 [--dry-run]
glimpse exit --topic-id <id> --option-id 500 [--shares 5] [--dry-run]
glimpse exit-batch --batch-id <id> [--dry-run]
```

`--dry-run` works the same way it does in the Python client. `execute` and
a partial `exit --shares N` never need an API key in dry-run mode, since
both are priced entirely through the public estimate endpoint. A
full-position `exit` (no `--shares`) or `exit-batch` still needs a key even
in dry-run mode, since pricing them requires looking up your current
positions first.

## Units: millisats vs. price

The API mixes two numeric scales that are easy to confuse:

- **millisats** (`*_millisats` fields, wallet balance) — real money.
  1 satoshi = 1000 millisatoshis.
- **price** (`yes_price` / `no_price` / `odds` from quotes) — a 0–100
  LS-LMSR pricing scale, only converted to millisats at trade/settlement
  time.

`glimpse_markets.money` exposes `Millisats` and `PriceUnits` as distinct
types, plus `millisats_to_sats()` / `sats_to_millisats()` helpers, so it's
harder to accidentally treat a price of `62.1` as `62.1` millisats.

## Error handling

Every non-2xx response raises a subclass of `GlimpseAPIError`
(`GlimpseAuthenticationError`, `GlimpseForbiddenError`,
`GlimpseTradingNotEligibleError`, `GlimpseNotFoundError`,
`GlimpseValidationError`, `GlimpseRateLimitError`, `GlimpseServerError`),
each carrying `.status_code`, `.error`, `.reason`, `.message`, and the raw
response body:

```python
from glimpse_markets import GlimpseAPIError

try:
    client.wallet_balance()
except GlimpseAPIError as e:
    print(e.status_code, e.error, e.reason)
```

Both clients also throttle themselves client-side to stay under Glimpse's
60-requests-per-60-seconds-per-key limit, so a naive loop doesn't
immediately trip a 429.

## Development

```bash
git clone <repo-url>
cd python-package

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

ruff check .
mypy src
pytest
```

## License

MIT — see [LICENSE](./LICENSE).
