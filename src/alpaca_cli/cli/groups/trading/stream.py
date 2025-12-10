"""Trading Stream command."""

import rich_click as click
import asyncio
from alpaca_cli.cli.utils import format_currency
from alpaca_cli.logger.logger import get_logger

logger = get_logger("trading.stream")


@click.command()
def stream() -> None:
    """Stream real-time order updates.

    Shows order fills, cancellations, and status changes in real-time.
    Press Ctrl+C to stop.
    """
    from alpaca.trading.stream import TradingStream
    from alpaca_cli.core.config import config
    from rich.live import Live
    from rich.table import Table
    from rich import box

    config.validate()
    logger.info("Starting trading stream. Press Ctrl+C to stop...")

    trading_stream = TradingStream(
        config.API_KEY, config.API_SECRET, paper=config.IS_PAPER
    )

    events = []
    MAX_EVENTS = 20

    def create_table():
        table = Table(title="[bold]Trading Stream[/bold]", box=box.ROUNDED)
        table.add_column("Time", style="dim")
        table.add_column("Event", style="cyan")
        table.add_column("Symbol", style="yellow")
        table.add_column("Side")
        table.add_column("Qty")
        table.add_column("Price")
        table.add_column("Status", style="bold")

        for event in events[-MAX_EVENTS:]:
            table.add_row(*event)

        return table

    async def trade_update_handler(data):
        event = data.event
        order = data.order

        time_str = order.updated_at.strftime("%H:%M:%S") if order.updated_at else "-"
        side_color = "green" if order.side.name == "BUY" else "red"
        side_str = f"[{side_color}]{order.side.name}[/{side_color}]"

        status_color = "green" if order.status.name == "FILLED" else "yellow"
        if order.status.name in ["CANCELED", "REJECTED", "EXPIRED"]:
            status_color = "red"
        status_str = f"[{status_color}]{order.status.name}[/{status_color}]"

        price_str = (
            format_currency(order.filled_avg_price) if order.filled_avg_price else "-"
        )

        events.append(
            [
                time_str,
                event,
                order.symbol,
                side_str,
                str(order.filled_qty or order.qty),
                price_str,
                status_str,
            ]
        )

        logger.info(
            f"{event}: {order.symbol} {order.side.name} {order.qty} @ {price_str} - {order.status.name}"
        )

    async def run_stream():
        trading_stream.subscribe_trade_updates(trade_update_handler)

        with Live(create_table(), refresh_per_second=2) as live:

            async def update_view():
                while True:
                    live.update(create_table())
                    await asyncio.sleep(0.5)

            view_task = asyncio.create_task(update_view())

            try:
                await trading_stream._run_forever()
            finally:
                view_task.cancel()

    try:
        asyncio.run(run_stream())
    except KeyboardInterrupt:
        logger.info("Trading stream stopped.")
    except Exception as e:
        logger.error(f"Stream error: {e}")
