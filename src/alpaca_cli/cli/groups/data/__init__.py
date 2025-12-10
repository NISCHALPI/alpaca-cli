"""Data module - mirrors Alpaca Market Data API Reference."""

import rich_click as click
from alpaca_cli.cli.groups.data.stock import stock
from alpaca_cli.cli.groups.data.crypto import crypto
from alpaca_cli.cli.groups.data.options import options
from alpaca_cli.cli.groups.data.screeners import screeners
from alpaca_cli.cli.groups.data.corporate_actions import corporate_actions
from alpaca_cli.cli.groups.data.news import news


@click.group()
def data() -> None:
    """Market data (Stock, Crypto, Options, Screeners, News)."""
    pass


# Register subgroups
data.add_command(stock)
data.add_command(crypto)
data.add_command(options)
data.add_command(screeners)
data.add_command(corporate_actions)
data.add_command(news)
