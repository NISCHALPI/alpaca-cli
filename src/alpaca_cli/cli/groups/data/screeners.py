"""Screeners commands - Market movers, most actives."""

import rich_click as click
from alpaca_cli.core.config import config
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger

logger = get_logger("data.screeners")


@click.group()
def screeners() -> None:
    """Market screeners (movers, actives)."""
    pass


@screeners.command("movers")
@click.option(
    "--market",
    type=click.Choice(["stocks", "crypto"], case_sensitive=False),
    default="stocks",
    help="[Optional] Market type. Choices: stocks, crypto. Default: stocks",
)
@click.option(
    "--top",
    type=int,
    default=10,
    help="[Optional] Number of top movers to display. Default: 10",
)
def movers(market: str, top: int) -> None:
    """Get top market movers (gainers/losers)."""
    from alpaca.data.historical.screener import ScreenerClient
    from alpaca.data.requests import MarketMoversRequest

    config.validate()
    logger.info(f"Fetching {market} movers...")

    try:
        client = ScreenerClient(config.API_KEY, config.API_SECRET)
        req = MarketMoversRequest(top=top)
        result = client.get_market_movers(req)

        if not result or not result.gainers:
            logger.info("No movers data found.")
            return

        gainer_rows = [
            [
                m.symbol,
                format_currency(m.price) if m.price else "-",
                f"[green]+{m.percent_change:.2f}%[/green]" if m.percent_change else "-",
                format_currency(m.change) if m.change else "-",
            ]
            for m in result.gainers[:top]
        ]
        print_table(
            "Top Gainers", ["Symbol", "Price", "% Change", "$ Change"], gainer_rows
        )

        if result.losers:
            loser_rows = [
                [
                    m.symbol,
                    format_currency(m.price) if m.price else "-",
                    f"[red]{m.percent_change:.2f}%[/red]" if m.percent_change else "-",
                    format_currency(m.change) if m.change else "-",
                ]
                for m in result.losers[:top]
            ]
            print_table(
                "Top Losers", ["Symbol", "Price", "% Change", "$ Change"], loser_rows
            )
    except Exception as e:
        logger.error(f"Failed to get movers: {e}")


@screeners.command("actives")
@click.option(
    "--by",
    type=click.Choice(["volume", "trades"], case_sensitive=False),
    default="volume",
    help="[Optional] Sort most active by. Choices: volume, trades. Default: volume",
)
@click.option(
    "--top",
    type=int,
    default=10,
    help="[Optional] Number of stocks to display. Default: 10",
)
def actives(by: str, top: int) -> None:
    """Get most active stocks."""
    from alpaca.data.historical.screener import ScreenerClient
    from alpaca.data.requests import MostActivesRequest
    from alpaca.data.enums import MostActivesBy

    config.validate()
    logger.info(f"Fetching most active stocks (by {by})...")

    try:
        client = ScreenerClient(config.API_KEY, config.API_SECRET)
        by_enum = (
            MostActivesBy.VOLUME if by.lower() == "volume" else MostActivesBy.TRADES
        )
        req = MostActivesRequest(top=top, by=by_enum)
        result = client.get_most_actives(req)

        if not result or not result.most_actives:
            logger.info("No data found.")
            return

        rows = [
            [
                stock.symbol,
                str(int(stock.volume)) if stock.volume else "-",
                str(int(stock.trade_count)) if stock.trade_count else "-",
            ]
            for stock in result.most_actives
        ]
        print_table(f"Most Active ({by.upper()})", ["Symbol", "Volume", "Trades"], rows)
    except Exception as e:
        logger.error(f"Failed to get most actives: {e}")
