import rich_click as click
from alpaca_cli.cli.groups.config import configuration as config
from alpaca_cli.cli.groups.account import account
from alpaca_cli.cli.groups.trading import trading
from alpaca_cli.cli.groups.assets import assets
from alpaca_cli.cli.groups.watchlist import watchlist
from alpaca_cli.cli.groups.data import data
from alpaca_cli.cli.groups.market import market
from alpaca_cli.cli.groups.dashboard import dashboard
from alpaca_cli.logger.logger import configure_logging

# Use Rich markup for all help text
click.rich_click.USE_RICH_MARKUP = True

# Configure logging at startup
configure_logging()


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.version_option(package_name="alpaca-cli")
def cli(debug: bool) -> None:
    """Alpaca CLI Trading Tool.

    Quick Aliases:
      - buy: trading buy market
      - sell: trading sell market
      - pos: account positions
      - status: account status

    Shell Completion:
      Run 'alpaca-cli --install-completion' to enable tab completion.
    """
    if debug:
        import logging

        logging.getLogger("alpaca_cli").setLevel(logging.DEBUG)


# Register main command groups
cli.add_command(account)
cli.add_command(trading)
cli.add_command(assets)
cli.add_command(watchlist)
cli.add_command(data)
cli.add_command(market)
cli.add_command(dashboard)
cli.add_command(config, name="config")


# --- COMMAND ALIASES ---
# These are shortcuts for common operations


@cli.command("buy")
@click.argument("symbol")
@click.argument("qty", type=float, required=False, default=None)
@click.option("--notional", type=float, help="Trade by dollar value instead of qty")
@click.option("--tif", default="day", help="Time in Force")
@click.pass_context
def buy_alias(ctx, symbol: str, qty, notional, tif: str):
    """Quick buy (alias for 'trading buy market')."""
    from alpaca_cli.cli.groups.trading import buy

    # Invoke the trading buy market command
    ctx.invoke(
        buy.commands["market"], symbol=symbol, qty=qty, notional=notional, tif=tif
    )


@cli.command("sell")
@click.argument("symbol")
@click.argument("qty", type=float, required=False, default=None)
@click.option("--notional", type=float, help="Trade by dollar value instead of qty")
@click.option("--tif", default="day", help="Time in Force")
@click.pass_context
def sell_alias(ctx, symbol: str, qty, notional, tif: str):
    """Quick sell (alias for 'trading sell market')."""
    from alpaca_cli.cli.groups.trading import sell

    # Invoke the trading sell market command
    ctx.invoke(
        sell.commands["market"], symbol=symbol, qty=qty, notional=notional, tif=tif
    )


@cli.command("pos")
@click.pass_context
def pos_alias(ctx):
    """Show positions (alias for 'account positions')."""
    from alpaca_cli.cli.groups.account import positions

    ctx.invoke(positions)


@cli.command("status")
@click.pass_context
def status_alias(ctx):
    """Show account status (alias for 'account status')."""
    from alpaca_cli.cli.groups.account import status

    ctx.invoke(status)


if __name__ == "__main__":
    cli()
