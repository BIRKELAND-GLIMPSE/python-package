# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-09-19

### Added

- `glimpse_markets.forecasting`, an optional forecasting layer built
  around Google's TimesFM:
  - `MarketRecorder` builds a local price history from `MarketStream`
    (Glimpse has no historical/candle endpoint of its own), with bounded
    per-series memory, optional NDJSON persistence, and resampling to an
    evenly spaced series for forecasting.
  - `TimesFMForecaster` wraps TimesFM 2.5 for point + quantile
    forecasting. Requires the new `forecasting` extra:
    `pip install glimpse-markets[forecasting]`. Deliberately targets 2.5,
    not 3.0 — TimesFM 3.0's pretrained weights are non-commercial/
    non-production only, unlike 2.5's Apache-2.0 license.
  - `bucket_probabilities()`, `probability_between()`, and `edge()` map a
    decile forecast onto Glimpse's bucketed-option markets and compare
    the model-implied probability to the live LMSR price. Pure Python,
    model-agnostic, no extra dependencies — usable with any decile
    forecast, not just TimesFM's.
  - Only `model.py` (and therefore only `TimesFMForecaster`) needs the
    `forecasting` extra; `MarketRecorder` and the signal functions are
    always available in the base install.
  - `fetch_yfinance_history()` — an opt-in Yahoo Finance adapter for
    forecasting the underlying asset (BTC/ETH/PAX Gold) a Glimpse market
    tracks, rather than Glimpse's own quote history. Requires a separate
    `yfinance` extra: `pip install glimpse-markets[yfinance]`. Yahoo's own
    terms describe their finance data as personal-use-only (stated twice,
    in bold, in `yfinance`'s own README) — documented prominently in
    `sources.py` rather than silently pulled in; not installed by default.
- An "Installation" section in the README laying out the base install plus
  both optional extras side by side, and a short notice on the `glimpse`
  CLI's `--help` output (and bare `glimpse` invocation) pointing at both
  extras — there's no supported way to have `pip install` itself print a
  message on completion (wheel installs are deliberately just file copies,
  no post-install code execution), so the CLI's help text is the closest
  real "right after install" touchpoint.

## [0.1.0] - 2026-09-17

Initial release.

### Added

- `Client`, a synchronous client covering every endpoint of the Glimpse
  Nmarket public API: wallet balance; batches; markets; live LMSR quotes;
  market stats and volume; ended/resolved market listings; and portfolio
  (active, ended-unresolved, ended-resolved, summary).
- Trade execution: `estimate_trade`, `enter_multi_topic_multi_leg`,
  `exit_consolidated`, `exit_consolidated_multi`, `exit_multi_topic_multi_leg`,
  `exit_batch`.
- `dry_run` mode on every trade-mutating call, pricing orders through the
  public `/trades/estimate` endpoint instead of placing them. Glimpse has no
  sandbox environment, so this is the client's own paper-trading safety net.
- `GlimpseAmbiguousTradeStateError`, raised instead of retrying on a network
  failure mid-trade — the API has no idempotency key, so a blind retry could
  double-execute an order.
- A `GlimpseError` exception hierarchy normalizing the API's inconsistent
  error response shapes across endpoints.
- A client-side rate limiter matching Glimpse's 60-requests-per-60-seconds
  per-key limit, so a naive bot loop doesn't immediately trip a 429.
- Pydantic v2 models for every response and request shape.
- `Millisats` / `PriceUnits` distinct types plus conversion helpers, to
  prevent confusing the API's two numeric scales (real money vs. a 0-100
  LMSR pricing scale).
- `AsyncClient`, mirroring `Client`'s entire method surface on
  `httpx.AsyncClient`, for bots already running an asyncio event loop.
- `MarketStream`, a real-time client for Glimpse's public WebSocket feed
  (`/ws/nmarket-updates`) — undocumented, found by reading the server
  source and confirmed live.
- `Strategy` / `StrategyRunner` / `PositionTracker`, a minimal scaffold for
  driving a trading bot off live quotes without hand-writing the
  connect/dispatch/reconnect plumbing.
- The `glimpse` CLI: `balance`, `portfolio`, `batches`, `quotes`,
  `estimate`, `execute`, `exit`, `exit-batch`, each supporting `--dry-run`
  where applicable.
- `.env` / environment-variable configuration (`GLIMPSE_API_KEY`,
  `GLIMPSE_BASE_URL`).

[Unreleased]: https://github.com/BIRKELAND-GLIMPSE/python-package/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/BIRKELAND-GLIMPSE/python-package/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/BIRKELAND-GLIMPSE/python-package/releases/tag/v0.1.0
