import rich_click as click
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

from alpaca_cli.core.client import get_trading_client
from alpaca_cli.core.config import config
from alpaca_cli.logger.logger import get_logger
from alpaca_cli.cli.utils import format_currency
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest, StockSnapshotRequest

logger = get_logger("dashboard")
console = Console()


def make_layout() -> Layout:
    """Define the grid layout."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="top", size=3),
        Layout(name="main", ratio=1),
        Layout(name="news", size=10),
    )

    layout["top"].split_row(
        Layout(name="header", ratio=1),
        Layout(name="indices", ratio=1),
    )

    layout["main"].split_row(
        Layout(name="account", ratio=1),
        Layout(name="positions", ratio=2),
    )
    return layout


def get_market_status_panel():
    client = get_trading_client()
    clock = client.get_clock()

    status_text = "OPEN" if clock.is_open else "CLOSED"
    status_color = "green" if clock.is_open else "red"

    next_session = clock.next_open if not clock.is_open else clock.next_close
    next_label = "Opens" if not clock.is_open else "Closes"

    # Calculate time until next session
    now = datetime.now(next_session.tzinfo)
    time_left = next_session - now
    hours, remainder = divmod(time_left.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    text = Text()
    text.append("Market is ", style="bold white")
    text.append(status_text, style=f"bold {status_color}")
    text.append(f" • Next Session {next_label}: ", style="dim white")
    text.append(f"{next_session.strftime('%H:%M %Z')}", style="cyan")
    text.append(f" (in {hours}h {minutes}m)", style="dim cyan")

    return Panel(
        Align.center(text),
        title="[bold blue]Market Status[/bold blue]",
        border_style="blue",
        box=box.ROUNDED,
    )


def get_indices_panel():
    config.validate()
    client = StockHistoricalDataClient(config.API_KEY, config.API_SECRET)

    symbols = ["SPY", "QQQ", "DIA", "IWM"]
    req = StockSnapshotRequest(symbol_or_symbols=symbols)

    text_parts = []

    try:
        snapshots = client.get_stock_snapshot(req)

        for sym in symbols:
            # Snapshots keyed by symbol
            snap = snapshots.get(sym)
            if not snap:
                continue

            price = snap.latest_trade.price if snap.latest_trade else 0
            prev = snap.previous_daily_bar.close if snap.previous_daily_bar else price

            change = price - prev
            pct = (change / prev) * 100 if prev else 0

            color = "green" if change >= 0 else "red"
            icon = "▲" if change >= 0 else "▼"

            # format: SPY 123.45 ▲ 1.2%
            line = Text()
            line.append(f"{sym} ", style="bold white")
            line.append(f"{price:.2f} ", style="white")
            line.append(f"{icon} {pct:.2f}%", style=color)

            text_parts.append(line)

    except Exception as e:
        return Panel(f"[red]Indices Error: {e}[/red]", title="Indices", box=box.ROUNDED)

    # Join with spacers
    final_text = Text("  |  ").join(text_parts)

    return Panel(
        Align.center(final_text),
        title="[bold yellow]Major Indices[/bold yellow]",
        border_style="yellow",
        box=box.ROUNDED,
    )


def get_account_panel():
    client = get_trading_client()
    acct = client.get_account()

    equity = float(acct.equity)
    last_equity = float(acct.last_equity)
    todays_pl = equity - last_equity
    todays_pl_pct = (todays_pl / last_equity) * 100 if last_equity else 0

    pl_color = "green" if todays_pl >= 0 else "red"

    grid = Table.grid(padding=1)
    grid.add_column(style="bold white", justify="left")
    grid.add_column(justify="right")

    grid.add_row("Equity", format_currency(equity))
    grid.add_row("Cash", format_currency(acct.cash))
    grid.add_row("Buying Power", format_currency(acct.buying_power))
    grid.add_row(
        "Day P/L",
        f"[{pl_color}]{format_currency(todays_pl)} ({todays_pl_pct:.2f}%)[/{pl_color}]",
    )

    # Portfolio Balance Chart (Simulated/Simple)
    # We could implement a mini ascii chart if we had history, but let's stick to metrics for now.

    return Panel(
        Align.center(grid, vertical="middle"),
        title="[bold green]Account Overview[/bold green]",
        border_style="green",
        box=box.ROUNDED,
    )


def get_positions_panel():
    client = get_trading_client()
    positions = client.get_all_positions()

    table = Table(show_header=True, header_style="bold magenta", box=None, expand=True)
    table.add_column("Sym")
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Mkt Val", justify="right")
    table.add_column("P/L", justify="right")

    if not positions:
        return Panel(
            Align.center("[dim]No open positions[/dim]", vertical="middle"),
            title="[bold magenta]Positions[/bold magenta]",
            border_style="magenta",
            box=box.ROUNDED,
        )

    # Limit to top 8 positions to fit
    for pos in positions[:8]:
        pl = float(pos.unrealized_pl)
        pl_pct = float(pos.unrealized_plpc) * 100
        color = "green" if pl >= 0 else "red"

        table.add_row(
            pos.symbol,
            pos.qty,
            format_currency(pos.current_price),
            format_currency(pos.market_value),
            f"[{color}]{format_currency(pl)} ({pl_pct:.1f}%)[/{color}]",
        )

    if len(positions) > 8:
        table.add_row("...", "...", "...", "...", "...")

    return Panel(
        table,
        title=f"[bold magenta]Positions ({len(positions)})[/bold magenta]",
        border_style="magenta",
        box=box.ROUNDED,
    )


def get_news_panel():
    config.validate()
    client = NewsClient(config.API_KEY, config.API_SECRET)
    req = NewsRequest(limit=5)

    try:
        # Access via subscript as debugged previously
        news_items = client.get_news(req)["news"]

        table = Table(show_header=False, box=None, expand=True)
        table.add_column("Time", style="dim", max_width=15)
        table.add_column("Headline")

        for n in news_items:
            # Access attributes directly, News object is pydantic model
            time_str = n.created_at.strftime("%H:%M")
            headline = n.headline
            table.add_row(time_str, headline)

        return Panel(
            table,
            title="[bold yellow]Latest News[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
        )
    except Exception as e:
        return Panel(
            f"[red]Failed to load news: {e}[/red]",
            title="[bold yellow]Latest News[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
        )


@click.command()
def dashboard() -> None:
    """Show the trading dashboard."""
    layout = make_layout()

    # We could do this concurrently but simplest approach first
    layout["header"].update(get_market_status_panel())
    layout["indices"].update(get_indices_panel())
    layout["account"].update(get_account_panel())
    layout["positions"].update(get_positions_panel())
    layout["news"].update(get_news_panel())

    console.print(layout)
