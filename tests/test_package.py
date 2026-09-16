""" package installs, imports, and the CLI entry point resolves."""

from click.testing import CliRunner

import glimpse_markets
from glimpse_markets.cli import main


def test_version_is_defined() -> None:
    assert isinstance(glimpse_markets.__version__, str)
    assert glimpse_markets.__version__


def test_cli_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert glimpse_markets.__version__ in result.output


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
