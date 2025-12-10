"""Market Info commands - Calendar and Clock."""

import rich_click as click
from typing import Optional
from datetime import datetime
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table
from alpaca_cli.logger.logger import get_logger
from alpaca.trading.requests import GetCalendarRequest

logger = get_logger("trading.market_info")


@click.command()
def clock() -> None:
    """Get market clock (current status, next open/close)."""
    logger.info("Fetching market clock...")
    client = get_trading_client()
    try:
        clk = client.get_clock()
        rows = [
            ["Timestamp", clk.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")],
            ["Is Open", "[green]Yes[/green]" if clk.is_open else "[red]No[/red]"],
            ["Next Open", clk.next_open.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")],
            [
                "Next Close",
                clk.next_close.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            ],
        ]
        print_table("Market Clock", ["Metric", "Value"], rows)
    except Exception as e:
        logger.error(f"Failed to get clock: {e}")


@click.command()
@click.option("--start", help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
@click.option("--limit", default=30, help="Number of days to show")
def calendar(start: Optional[str], end: Optional[str], limit: int) -> None:
    """Get market calendar (trading days and hours)."""
    logger.info("Fetching market calendar...")
    client = get_trading_client()

    start_dt = datetime.strptime(start, "%Y-%m-%d").date() if start else None
    end_dt = datetime.strptime(end, "%Y-%m-%d").date() if end else None

    req = GetCalendarRequest(start=start_dt, end=end_dt)

    try:
        calendars = client.get_calendar(req)
        rows = []
        for cal in calendars[:limit]:
            rows.append(
                [
                    cal.date.strftime("%Y-%m-%d"),
                    cal.date.strftime("%A"),
                    cal.open.strftime("%H:%M"),
                    cal.close.strftime("%H:%M"),
                    (
                        str(cal.session_open)
                        if hasattr(cal, "session_open") and cal.session_open
                        else "-"
                    ),
                    (
                        str(cal.session_close)
                        if hasattr(cal, "session_close") and cal.session_close
                        else "-"
                    ),
                ]
            )
        print_table(
            "Market Calendar",
            ["Date", "Day", "Open", "Close", "Session Open", "Session Close"],
            rows,
        )
    except Exception as e:
        logger.error(f"Failed to get calendar: {e}")
