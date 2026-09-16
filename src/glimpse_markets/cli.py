"""Command-line entry point for the ``glimpse`` CLI.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from typing import Any, TypeVar

import click
from dotenv import load_dotenv
from pydantic import BaseModel

from glimpse_markets import (
    Client,
    EnterMultiTopicLegGroup,
    GlimpseError,
    TradeLeg,
    __version__,
)

F = TypeVar("F", bound=Callable[..., None])


def _handle_errors(func: F) -> F:
    """Turn a GlimpseError into a clean stderr message + exit(1) instead of a traceback."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            func(*args, **kwargs)
        except GlimpseError as exc:
            click.echo(f"Error: {exc}", err=True)
            raise SystemExit(1) from exc

    return wrapper  # type: ignore[return-value]


def _print(data: Any) -> None:
    if isinstance(data, BaseModel):
        click.echo(data.model_dump_json(indent=2))
    else:
        click.echo(json.dumps(data, indent=2, default=str))


def _client_from_env() -> Client:
    load_dotenv()
    return Client.from_env()


def _require_api_key(client: Client) -> None:
    if not client.api_key:
        click.echo(
            "config error: GLIMPSE_API_KEY is required for this command ",
            err=True,
        )
        raise SystemExit(1)


def _parse_leg(value: str) -> TradeLeg:
    try:
        option_id_str, contracts_str = value.split(":", 1)
        return TradeLeg(option_id=int(option_id_str), contracts=float(contracts_str))
    except ValueError as exc:
        raise click.BadParameter(
            f"expected OPTION_ID:CONTRACTS (e.g. 500:10), got {value!r}"
        ) from exc


@click.group()
@click.version_option(version=__version__, prog_name="glimpse")
def main() -> None:
    """Glimpse Nmarket API command-line client."""


@main.command()
@_handle_errors
def balance() -> None:
    """Wallet balance, max exposure, and current open exposure."""
    with _client_from_env() as client:
        _require_api_key(client)
        _print(client.wallet_balance())


@main.group()
def portfolio() -> None:
    """Portfolio positions (requires an API key)."""


@portfolio.command("active")
@_handle_errors
def portfolio_active_cmd() -> None:
    """All open consolidated positions."""
    with _client_from_env() as client:
        _require_api_key(client)
        _print(client.portfolio_active())


@portfolio.command("summary")
@_handle_errors
def portfolio_summary_cmd() -> None:
    """Aggregate value, PnL, and market counts."""
    with _client_from_env() as client:
        _require_api_key(client)
        _print(client.portfolio_summary())


@portfolio.command("ended")
@click.option("--limit", type=int, default=None)
@click.option("--offset", type=int, default=None)
@_handle_errors
def portfolio_ended_cmd(limit: int | None, offset: int | None) -> None:
    """Ended but not yet resolved positions (paginated)."""
    with _client_from_env() as client:
        _require_api_key(client)
        _print(client.portfolio_ended(limit=limit, offset=offset))


@portfolio.command("resolved")
@click.option("--limit", type=int, default=None)
@click.option("--offset", type=int, default=None)
@_handle_errors
def portfolio_resolved_cmd(limit: int | None, offset: int | None) -> None:
    """Resolved market positions (paginated)."""
    with _client_from_env() as client:
        _require_api_key(client)
        _print(client.portfolio_resolved(limit=limit, offset=offset))


@main.command()
@click.option(
    "--batch-id",
    default=None,
    help="Show active markets in this batch instead of listing all batches.",
)
@_handle_errors
def batches(batch_id: str | None) -> None:
    """List all batches, or active markets within one batch (public, no API key required)."""
    with _client_from_env() as client:
        if batch_id:
            _print(client.batch_active_markets(batch_id))
        else:
            _print(client.batches())


@main.command()
@click.option("--topic-id", type=int, required=True)
@_handle_errors
def quotes(topic_id: int) -> None:
    """LMSR quotes for a market (public, no API key required)."""
    with _client_from_env() as client:
        _print(client.market_quotes(topic_id))


@main.command()
@click.option("--topic-id", type=int, required=True)
@click.option("--type", "trade_type", type=click.Choice(["buy", "sell"]), required=True)
@click.option("--leg", "legs", multiple=True, required=True, metavar="OPTION_ID:CONTRACTS")
@_handle_errors
def estimate(topic_id: int, trade_type: str, legs: tuple[str, ...]) -> None:
    """Estimate cost/price impact of a trade (public, no API key required)."""
    trade_legs = [_parse_leg(leg) for leg in legs]
    with _client_from_env() as client:
        _print(client.estimate_trade(topic_id, trade_type, trade_legs))


@main.command()
@click.option("--topic-id", type=int, required=True)
@click.option("--leg", "legs", multiple=True, required=True, metavar="OPTION_ID:CONTRACTS")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate via /trades/estimate instead of placing a real order.",
)
@_handle_errors
def execute(topic_id: int, legs: tuple[str, ...], dry_run: bool) -> None:
    """Enter a position (buy-only; requires an API key). Run `estimate` first."""
    trade_legs = [_parse_leg(leg) for leg in legs]
    with _client_from_env() as client:
        if not dry_run:
            _require_api_key(client)
        group = EnterMultiTopicLegGroup(topic_id=topic_id, legs=trade_legs)
        _print(client.enter_multi_topic_multi_leg([group], dry_run=dry_run))


@main.command("exit")
@click.option("--topic-id", type=int, required=True)
@click.option("--option-id", type=int, required=True)
@click.option(
    "--shares", type=float, default=None, help="Shares to exit; omit to exit the full position."
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate via /trades/estimate instead of placing a real order.",
)
@_handle_errors
def exit_cmd(topic_id: int, option_id: int, shares: float | None, dry_run: bool) -> None:
    """Exit a single position, full or partial (requires an API key).
    """
    with _client_from_env() as client:
        if not dry_run or not shares:
            _require_api_key(client)
        _print(client.exit_consolidated(topic_id, option_id, shares=shares, dry_run=dry_run))


@main.command("exit-batch")
@click.option("--batch-id", required=True)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate via /trades/estimate instead of placing a real order.",
)
@_handle_errors
def exit_batch_cmd(batch_id: str, dry_run: bool) -> None:
    """Exit every position in a batch (requires an API key).
    """
    with _client_from_env() as client:
        _require_api_key(client)
        _print(client.exit_batch(batch_id, dry_run=dry_run))


if __name__ == "__main__":
    main()
