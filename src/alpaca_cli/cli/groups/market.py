import rich_click as click
from typing import Optional, List, Any
from datetime import datetime, date
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.core.config import config
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger
from alpaca.trading.requests import GetCalendarRequest
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest

logger = get_logger("market")


@click.group()
def market() -> None:
    """Market information (Clock, Calendar, News)."""
    pass


@market.command()
def clock() -> None:
    """Get market clock."""
    logger.info("Fetching market clock...")
    client = get_trading_client()
    try:
        clock = client.get_clock()
        rows = [
            [
                "Timestamp",
                clock.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            ],
            ["Is Open", "[green]Yes[/green]" if clock.is_open else "[red]No[/red]"],
            [
                "Next Open",
                clock.next_open.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            ],
            [
                "Next Close",
                clock.next_close.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            ],
        ]
        print_table("Market Clock", ["Metric", "Value"], rows)
    except Exception as e:
        logger.error(f"Failed to get clock: {e}")


@market.command()
@click.option("--start", help="Start date (YYYY-MM-DD) [UTC]")
@click.option("--end", help="End date (YYYY-MM-DD) [UTC]")
def calendar(start: Optional[str], end: Optional[str]) -> None:
    """Get market calendar."""
    logger.info("Fetching market calendar...")
    client = get_trading_client()

    start_dt = datetime.strptime(start, "%Y-%m-%d").date() if start else None
    end_dt = datetime.strptime(end, "%Y-%m-%d").date() if end else None

    req = GetCalendarRequest(start=start_dt, end=end_dt)

    try:
        calendars = client.get_calendar(req)
        rows = []
        for cal in calendars:
            rows.append(
                [
                    cal.date.strftime("%Y-%m-%d"),
                    cal.open.strftime("%H:%M"),
                    cal.close.strftime("%H:%M"),
                ]
            )
        print_table(
            "Market Calendar",
            ["Date", "Open", "Close"],
            rows,
        )
    except Exception as e:
        logger.error(f"Failed to get calendar: {e}")


@market.command()
@click.option("--symbols", help="Comma-separated symbols")
@click.option("--start", help="Start date (YYYY-MM-DD) [UTC]")
@click.option("--end", help="End date (YYYY-MM-DD) [UTC]")
@click.option(
    "--limit", default=10, help="Limit number of news items (default 10, max 50)"
)
@click.option("--include-content", is_flag=True, help="Include summary content")
def news(
    symbols: Optional[str],
    start: Optional[str],
    end: Optional[str],
    limit: int,
    include_content: bool,
) -> None:
    """Get market news."""
    logger.info("Fetching market news...")
    config.validate()
    client = NewsClient(config.API_KEY, config.API_SECRET)

    start_dt = datetime.strptime(start, "%Y-%m-%d") if start else None
    end_dt = datetime.strptime(end, "%Y-%m-%d") if end else None
    symbol_list = symbols.upper().split(",") if symbols else None

    # Check limit constraint
    if limit > 50:
        logger.warning("Limit capped at 50 by API.")
        limit = 50

    req = NewsRequest(
        symbols=symbol_list,
        start=start_dt,
        end=end_dt,
        limit=limit,
        include_content=include_content,
    )

    try:
        news_list = client.get_news(req)["news"]
        rows = []
        for n in news_list:
            headline = n.headline
            if include_content and n.summary:
                headline += f"\n[dim]{n.summary[:200]}...[/dim]"

            rows.append(
                [
                    n.created_at.astimezone().strftime("%Y-%m-%d %H:%M"),
                    headline,
                    n.source,
                    ", ".join(n.symbols) if n.symbols else "",
                    f"[link={n.url}]Link[/link]" if n.url else "",
                ]
            )

        print_table(
            "Market News", ["Time", "Headline", "Source", "Symbols", "URL"], rows
        )

    except Exception as e:
        logger.error(f"Failed to get news: {e}")
