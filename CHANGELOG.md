# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/BIRKELAND-GLIMPSE/python-package/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/BIRKELAND-GLIMPSE/python-package/releases/tag/v0.1.0
