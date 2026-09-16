"""Command-line entry point for the ``glimpse`` CLI.
"""

from __future__ import annotations

import click

from glimpse_markets import __version__


@click.group()
@click.version_option(version=__version__, prog_name="glimpse")
def main() -> None:
    """Glimpse Nmarket API command-line client."""


if __name__ == "__main__":
    main()
