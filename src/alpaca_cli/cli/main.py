"""Main CLI entry point - Alpaca CLI Trading Tool."""

import rich_click as click
from alpaca_cli.cli.groups.config import configuration as config_cmd
from alpaca_cli.cli.groups.trading import trading
from alpaca_cli.cli.groups.data import data
from alpaca_cli.cli.groups.dashboard import dashboard
from alpaca_cli.logger.logger import configure_logging

# Use Rich markup for all help text
click.rich_click.USE_RICH_MARKUP = True

# Configure logging at startup
configure_logging()


def get_version_info() -> str:
    """Get version information for CLI and dependencies."""
    from importlib.metadata import version, PackageNotFoundError

    try:
        cli_version = version("alpaca-cli")
    except PackageNotFoundError:
        cli_version = "dev"

    try:
        alpaca_version = version("alpaca-py")
    except PackageNotFoundError:
        alpaca_version = "unknown"

    click.echo(f"Alpaca CLI: v{cli_version}")
    click.echo(f"Alpaca-py: v{alpaca_version}", nl=False)


def version_callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    """Custom version callback to show both CLI and API versions."""
    if not value or ctx.resilient_parsing:
        return
    click.echo(get_version_info())
    ctx.exit()


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--version",
    "-V",
    is_flag=True,
    callback=version_callback,
    expose_value=False,
    is_eager=True,
    help="Show version information",
)
def cli(debug: bool) -> None:
    """
    [bold cyan]Alpaca CLI Trading Tool[/bold cyan] - Command-line interface for Alpaca Markets API.

    Use [green]trading[/green] for account, positions, orders, and assets management.
    Use [green]data[/green] for market data (stock, crypto, options, news).

    [dim]Quick aliases: buy, sell, pos, status, quote, clock[/dim]

    [dim]Shell completion: eval "$(_ALPACA_CLI_COMPLETE=bash_source alpaca-cli)"[/dim]
    """
    if debug:
        import logging

        logging.getLogger("alpaca_cli").setLevel(logging.DEBUG)


# Register main command groups
cli.add_command(trading)
cli.add_command(data)
cli.add_command(dashboard)
cli.add_command(config_cmd, name="config")


# --- COMMAND ALIASES ---
# These are shortcuts for common operations


@cli.command("buy")
@click.argument("symbol")
@click.argument("qty", type=float, required=False, default=None)
@click.option("--notional", type=float, help="Trade by dollar value instead of qty")
@click.option("--tif", default="day", help="Time in Force")
def buy_alias(symbol: str, qty, notional, tif: str):
    """Quick buy (alias for 'trading orders buy market')."""
    from alpaca_cli.cli.groups.trading.orders import buy_market
    from click import Context

    ctx = Context(buy_market)
    ctx.invoke(
        buy_market,
        symbol=symbol,
        qty=qty,
        notional=notional,
        tif=tif,
        client_order_id=None,
        take_profit=None,
        stop_loss=None,
        stop_loss_limit=None,
    )


@cli.command("sell")
@click.argument("symbol")
@click.argument("qty", type=float, required=False, default=None)
@click.option("--notional", type=float, help="Trade by dollar value instead of qty")
@click.option("--tif", default="day", help="Time in Force")
def sell_alias(symbol: str, qty, notional, tif: str):
    """Quick sell (alias for 'trading orders sell market')."""
    from alpaca_cli.cli.groups.trading.orders import sell_market
    from click import Context

    ctx = Context(sell_market)
    ctx.invoke(
        sell_market,
        symbol=symbol,
        qty=qty,
        notional=notional,
        tif=tif,
        client_order_id=None,
        take_profit=None,
        stop_loss=None,
        stop_loss_limit=None,
    )


@cli.command("pos")
def pos_alias():
    """Show positions (alias for 'trading positions list')."""
    from alpaca_cli.cli.groups.trading.positions import list_positions
    from click import Context

    ctx = Context(list_positions)
    ctx.invoke(list_positions)


@cli.command("status")
def status_alias():
    """Show account status (alias for 'trading account status')."""
    from alpaca_cli.cli.groups.trading.account import status
    from click import Context

    ctx = Context(status)
    ctx.invoke(status)


@cli.command("quote")
@click.argument("symbols")
@click.option("--feed", type=click.Choice(["iex", "sip"]), default="iex")
def quote_alias(symbols: str, feed: str):
    """Get latest quote/price (alias for 'data stock latest')."""
    from alpaca_cli.cli.groups.data.stock import stock_latest
    from click import Context

    ctx = Context(stock_latest)
    ctx.invoke(stock_latest, symbols=symbols, feed=feed, currency=None)


@cli.command("clock")
def clock_alias():
    """Market clock (alias for 'trading clock')."""
    from alpaca_cli.cli.groups.trading.market_info import clock
    from click import Context

    ctx = Context(clock)
    ctx.invoke(clock)


if __name__ == "__main__":
    cli()
