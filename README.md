# glimpse-markets

Official Python client for the [Glimpse](https://docs.glimpse.markets) Nmarket
prediction-market API — for people building forecasting algorithms and
trading bots on Glimpse.

> **Status: early scaffolding (Phase 0).** The client, models, and CLI are
> not implemented yet — see [CLAUDE.md](./CLAUDE.md) for the full build plan
> and current phase.

## Install

```bash
pip install glimpse-markets
```

## Quickstart

```python
from glimpse_markets import Client

client = Client(api_key="glp_live_...")
print(client.wallet_balance())
```

*(Not yet implemented — coming in Phase 1.)*

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

ruff check .
mypy src
pytest
```

## License

MIT
