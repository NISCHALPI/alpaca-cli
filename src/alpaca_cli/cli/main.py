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


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.version_option(package_name="alpaca-cli")
def cli(debug: bool) -> None:
    """Alpaca CLI Trading Tool.

    Command Structure (mirrors Alpaca Python SDK):

    TRADING:
      trading account     - Account status, config, activities, history
      trading positions   - Position management (list, get, close, exercise)
      trading orders      - Order management (list, get, cancel, modify, buy, sell)
      trading assets      - Asset lookup
      trading contracts   - Option contracts
      trading watchlists  - Watchlist CRUD
      trading clock       - Market clock
      trading calendar    - Market calendar
      trading corporate-actions - Corporate actions
      trading stream      - Real-time order updates

    DATA:
      data stock      - Stock bars, quotes, trades, latest, snapshot, stream
      data crypto     - Crypto bars, quotes, trades, latest, snapshot, orderbook, stream
      data options    - Option bars, trades, latest, snapshot, chain, exchanges
      data screeners  - Market movers, most actives
      data news       - Market news
      data corporate-actions - Corporate actions data

    Quick Aliases:
      buy       - trading orders buy market
      sell      - trading orders sell market
      pos       - trading positions list
      status    - trading account status
      quote     - data stock latest (get current price)

    Shell Completion:
      Run 'alpaca-cli --install-completion' to enable tab completion.
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
