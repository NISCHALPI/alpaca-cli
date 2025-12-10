"""Trading module - mirrors Alpaca Trading API Reference."""

import rich_click as click
from alpaca_cli.cli.groups.trading.account import account
from alpaca_cli.cli.groups.trading.positions import positions
from alpaca_cli.cli.groups.trading.orders import orders
from alpaca_cli.cli.groups.trading.assets import assets
from alpaca_cli.cli.groups.trading.contracts import contracts
from alpaca_cli.cli.groups.trading.watchlists import watchlists
from alpaca_cli.cli.groups.trading.market_info import calendar, clock
from alpaca_cli.cli.groups.trading.corporate_actions import corporate_actions
from alpaca_cli.cli.groups.trading.stream import stream


@click.group()
def trading() -> None:
    """Trading commands (Account, Positions, Orders, Assets, Watchlists)."""
    pass


# Register subgroups
trading.add_command(account)
trading.add_command(positions)
trading.add_command(orders)
trading.add_command(assets)
trading.add_command(contracts)
trading.add_command(watchlists)
trading.add_command(calendar)
trading.add_command(clock)
trading.add_command(corporate_actions)
trading.add_command(stream)
