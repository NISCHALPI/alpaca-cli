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
def cli(debug: bool) -> None:
    """Alpaca CLI Trading Tool."""
    if debug:
        import logging

        logging.getLogger("alpaca_cli").setLevel(logging.DEBUG)


cli.add_command(account)
cli.add_command(trading)
cli.add_command(assets)
cli.add_command(watchlist)
cli.add_command(data)
cli.add_command(market)
cli.add_command(dashboard)
cli.add_command(config, name="config")

if __name__ == "__main__":
    cli()
