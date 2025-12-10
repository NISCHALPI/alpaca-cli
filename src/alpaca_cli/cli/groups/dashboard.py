import rich_click as click
from datetime import datetime
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

from alpaca_cli.core.client import get_trading_client, get_stock_data_client
from alpaca_cli.core.config import config
from alpaca_cli.logger.logger import get_logger
from alpaca_cli.cli.utils import format_currency
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest, StockSnapshotRequest

logger = get_logger("dashboard")
console = Console()


# Sparkline characters (block elements for mini charts)
SPARK_CHARS = "▁▂▃▄▅▆▇█"


def get_sparkline(values: list[float], width: int = 8) -> str:
    """Generate a sparkline from a list of values."""
    if not values or len(values) < 2:
        return "─" * width

    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val

    if val_range == 0:
        return SPARK_CHARS[3] * min(len(values), width)

    # Normalize and map to spark characters
    result = []
    step = max(1, len(values) // width)
    sampled = values[::step][:width]

    for val in sampled:
        normalized = (val - min_val) / val_range
        idx = int(normalized * (len(SPARK_CHARS) - 1))
        result.append(SPARK_CHARS[idx])

    return "".join(result)


def get_pl_color(pct: float) -> str:
    """Get gradient color based on P/L percentage."""
    if pct >= 5:
        return "bold green"
    elif pct >= 2:
        return "green"
    elif pct >= 0:
        return "bright_green"
    elif pct >= -2:
        return "bright_red"
    elif pct >= -5:
        return "red"
    else:
        return "bold red"


def get_pl_icon(pct: float) -> str:
    """Get icon based on P/L."""
    if pct >= 2:
        return "🚀"
    elif pct >= 0.5:
        return "📈"
    elif pct >= 0:
        return "➡️"
    elif pct >= -2:
        return "📉"
    else:
        return "🔻"


def make_layout() -> Layout:
    """Define the grid layout."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="header", size=5),
        Layout(name="top_bar", size=8),
        Layout(name="main", ratio=1),
        Layout(name="bottom", size=12),
    )

    layout["main"].split_row(
        Layout(name="account", ratio=1),
        Layout(name="positions", ratio=2),
    )

    layout["bottom"].split_row(
        Layout(name="orders", ratio=1),
        Layout(name="news", ratio=1),
    )

    return layout


def get_header_panel():
    """Create a styled header banner."""
    now = datetime.now().astimezone()

    # Mode indicator
    mode = "PAPER" if config.IS_PAPER else "LIVE"
    mode_color = "yellow" if config.IS_PAPER else "red"
    mode_style = f"bold {mode_color}"

    # Build header text
    title = Text()
    title.append(
        "╔══════════════════════════════════════════════════════════════════════════╗\n",
        style="cyan",
    )
    title.append("║  ", style="cyan")
    title.append("ALPACA CLI", style="bold white")
    title.append("  │  ", style="dim")
    title.append("Trading Dashboard", style="bold cyan")
    title.append("  │  ", style="dim")
    title.append(f"[{mode}]", style=mode_style)
    title.append("  │  ", style="dim")
    title.append(now.strftime("%Y-%m-%d %H:%M:%S %Z"), style="dim white")

    # Pad to fill width
    padding = " " * 10
    title.append(padding, style="cyan")
    title.append("║\n", style="cyan")
    title.append(
        "╚══════════════════════════════════════════════════════════════════════════╝",
        style="cyan",
    )

    return Panel(
        Align.center(title),
        box=box.SIMPLE,
        padding=(0, 0),
    )


def get_market_status_panel():
    """Get market status with countdown timer."""
    client = get_trading_client()
    clock = client.get_clock()

    status_text = "OPEN" if clock.is_open else "CLOSED"
    status_color = "green" if clock.is_open else "red"
    status_icon = "🟢" if clock.is_open else "🔴"

    next_session = clock.next_open if not clock.is_open else clock.next_close
    next_label = "Opens" if not clock.is_open else "Closes"

    next_session_local = next_session.astimezone()
    now_local = datetime.now().astimezone()

    time_left = next_session_local - now_local
    hours, remainder = divmod(int(time_left.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    text = Text()
    text.append(f"{status_icon} Market ", style="bold white")
    text.append(status_text, style=f"bold {status_color}")
    text.append(f"  │  {next_label}: ", style="dim white")
    text.append(f"{next_session_local.strftime('%H:%M')}", style="cyan")
    text.append(f" ({hours:02d}:{minutes:02d}:{seconds:02d})", style="dim cyan")

    return Panel(
        Align.center(text),
        title="[bold blue]⏰ Market Status[/bold blue]",
        border_style="blue",
        box=box.ROUNDED,
    )


def get_indices_panel():
    """Get major indices with sparklines."""
    client = get_stock_data_client()

    # Major ETFs tracking key indices
    symbols = ["SPY", "QQQ", "DIA", "IWM", "VTI", "ARKK"]
    req = StockSnapshotRequest(symbol_or_symbols=symbols)

    # Names for display
    index_names = {
        "SPY": "S&P 500",
        "QQQ": "Nasdaq",
        "DIA": "Dow Jones",
        "IWM": "Russell 2K",
        "VTI": "Total Mkt",
        "ARKK": "ARK Innov",
    }

    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold yellow",
        padding=(0, 1),
        expand=True,
    )
    table.add_column("Index", style="bold white")
    table.add_column("Price", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("Trend", justify="center")

    try:
        snapshots = client.get_stock_snapshot(req)

        for sym in symbols:
            snap = snapshots.get(sym)
            if not snap:
                # Show placeholder if data not available
                table.add_row(
                    f"{index_names.get(sym, sym)}",
                    "[dim]--[/dim]",
                    "[dim]--[/dim]",
                    "[dim]----[/dim]",
                )
                continue

            price = snap.latest_trade.price if snap.latest_trade else 0
            prev = snap.previous_daily_bar.close if snap.previous_daily_bar else price

            change = price - prev
            pct = (change / prev) * 100 if prev else 0

            color = get_pl_color(pct)
            icon = "▲" if change >= 0 else "▼"

            # Generate sparkline based on current momentum
            spark_values = [
                prev,
                prev + change * 0.3,
                prev + change * 0.5,
                prev + change * 0.7,
                price,
            ]
            sparkline = get_sparkline(spark_values)
            spark_color = "green" if change >= 0 else "red"

            table.add_row(
                f"{index_names.get(sym, sym)}",
                f"${price:.2f}",
                f"[{color}]{icon} {pct:+.2f}%[/{color}]",
                f"[{spark_color}]{sparkline}[/{spark_color}]",
            )

    except Exception as e:
        return Panel(f"[red]Error: {e}[/red]", title="Indices", box=box.ROUNDED)

    return Panel(
        table,
        title="[bold yellow]📊 Market Indices[/bold yellow]",
        border_style="yellow",
        box=box.ROUNDED,
    )


def get_account_panel():
    """Enhanced account panel with progress bars."""
    client = get_trading_client()
    acct = client.get_account()

    equity = float(acct.equity)
    last_equity = float(acct.last_equity)
    cash = float(acct.cash)
    buying_power = float(acct.buying_power)

    todays_pl = equity - last_equity
    todays_pl_pct = (todays_pl / last_equity) * 100 if last_equity else 0

    pl_color = get_pl_color(todays_pl_pct)
    pl_icon = get_pl_icon(todays_pl_pct)

    # Calculate buying power usage
    bp_used = equity - buying_power if buying_power < equity else 0
    bp_pct = (bp_used / equity) * 100 if equity > 0 else 0

    # Build the account display
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", justify="left", min_width=14)
    grid.add_column(justify="right", min_width=16)

    grid.add_row("", "")  # Spacing
    grid.add_row(
        "💰 Equity",
        f"[bold white]{format_currency(equity)}[/bold white]",
    )
    grid.add_row(
        "💵 Cash",
        f"[white]{format_currency(cash)}[/white]",
    )
    grid.add_row(
        "📈 Buying Power",
        f"[cyan]{format_currency(buying_power)}[/cyan]",
    )
    grid.add_row("", "")  # Spacing
    grid.add_row(
        f"{pl_icon} Day P/L",
        f"[{pl_color}]{format_currency(todays_pl)} ({todays_pl_pct:+.2f}%)[/{pl_color}]",
    )

    # Buying power usage bar
    bp_bar_text = Text()
    bp_bar_text.append("\n\n📊 BP Usage: ", style="dim")
    bp_bar_text.append(f"{bp_pct:.1f}%", style="cyan")

    rendered = Group(
        Align.center(grid, vertical="middle"),
        Align.center(bp_bar_text),
    )

    return Panel(
        rendered,
        title="[bold green]💼 Account Overview[/bold green]",
        border_style="green",
        box=box.ROUNDED,
    )


def get_positions_panel():
    """Enhanced positions panel with color gradients."""
    client = get_trading_client()
    positions = client.get_all_positions()

    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.SIMPLE_HEAD,
        expand=True,
        padding=(0, 1),
    )
    table.add_column("Symbol", style="bold white")
    table.add_column("Qty", justify="right")
    table.add_column("Avg Cost", justify="right", style="dim")
    table.add_column("Current", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("P/L", justify="right")

    if not positions:
        return Panel(
            Align.center(
                Text("📭 No open positions", style="dim italic"),
                vertical="middle",
            ),
            title="[bold magenta]📊 Positions[/bold magenta]",
            border_style="magenta",
            box=box.ROUNDED,
        )

    # Sort by absolute P/L (biggest movers first)
    sorted_positions = sorted(
        positions, key=lambda p: abs(float(p.unrealized_pl)), reverse=True
    )

    for pos in sorted_positions[:10]:
        pl = float(pos.unrealized_pl)
        pl_pct = float(pos.unrealized_plpc) * 100
        color = get_pl_color(pl_pct)
        icon = get_pl_icon(pl_pct)

        table.add_row(
            pos.symbol,
            str(pos.qty),
            format_currency(pos.avg_entry_price),
            format_currency(pos.current_price),
            format_currency(pos.market_value),
            f"[{color}]{icon} {format_currency(pl)} ({pl_pct:+.1f}%)[/{color}]",
        )

    if len(positions) > 10:
        table.add_row("...", "", "", "", "", f"[dim]+{len(positions) - 10} more[/dim]")

    return Panel(
        table,
        title=f"[bold magenta]📊 Positions ({len(positions)})[/bold magenta]",
        border_style="magenta",
        box=box.ROUNDED,
    )


def get_orders_panel():
    """New open orders panel."""
    client = get_trading_client()

    try:
        orders = client.get_orders(status="open")
    except Exception:
        orders = []

    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=box.SIMPLE_HEAD,
        expand=True,
        padding=(0, 1),
    )
    table.add_column("Symbol")
    table.add_column("Side")
    table.add_column("Type")
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Status")

    if not orders:
        return Panel(
            Align.center(
                Text("📭 No open orders", style="dim italic"),
                vertical="middle",
            ),
            title="[bold cyan]📋 Open Orders[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )

    for order in orders[:6]:
        side_color = "green" if order.side.name == "BUY" else "red"
        side_icon = "🟢" if order.side.name == "BUY" else "🔴"

        # Get limit/stop price if applicable
        price_str = "-"
        if order.limit_price:
            price_str = format_currency(order.limit_price)
        elif order.stop_price:
            price_str = format_currency(order.stop_price)

        status_color = (
            "yellow"
            if order.status.name in ["NEW", "ACCEPTED", "PENDING_NEW"]
            else "dim"
        )

        table.add_row(
            order.symbol,
            f"[{side_color}]{side_icon} {order.side.name}[/{side_color}]",
            order.type.name.replace("_", " ").title(),
            str(order.qty),
            price_str,
            f"[{status_color}]{order.status.name}[/{status_color}]",
        )

    if len(orders) > 6:
        table.add_row("", "", "", "", "", f"[dim]+{len(orders) - 6} more[/dim]")

    return Panel(
        table,
        title=f"[bold cyan]📋 Open Orders ({len(orders)})[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
    )


def get_news_panel():
    """Enhanced news panel with clickable hyperlinks."""
    config.validate()
    client = NewsClient(config.API_KEY, config.API_SECRET)
    req = NewsRequest(limit=10)

    try:
        news_items = client.get_news(req)["news"]

        table = Table(show_header=False, box=None, expand=True, padding=(0, 1))
        table.add_column("Time", style="dim cyan", min_width=6)
        table.add_column("Headline", overflow="fold")

        for n in news_items:
            time_str = n.created_at.astimezone().strftime("%H:%M")

            # Get URL for hyperlink
            url = getattr(n, "url", None)

            # Truncate long headlines
            headline = n.headline
            if len(headline) > 55:
                headline = headline[:52] + "..."

            # Make headline a clickable hyperlink if URL available
            if url:
                headline_display = f"[link={url}]{headline}[/link]"
            else:
                headline_display = headline

            # Add source if available
            source = getattr(n, "source", None)
            if source:
                headline_display = f"{headline_display} [dim]({source})[/dim]"

            table.add_row(f"🕐 {time_str}", headline_display)

        return Panel(
            table,
            title="[bold yellow]📰 Latest News (click to open)[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
        )
    except Exception as e:
        return Panel(
            f"[red]Failed to load news: {e}[/red]",
            title="[bold yellow]📰 Latest News[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
        )


def get_top_bar():
    """Combined market status and indices bar."""
    status = get_market_status_panel()
    indices = get_indices_panel()

    layout = Layout()
    layout.split_row(
        Layout(name="status", ratio=1),
        Layout(name="indices", ratio=1),
    )
    layout["status"].update(status)
    layout["indices"].update(indices)

    return layout


@click.command()
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    help="[Optional] Enable auto-refresh mode for live updates",
)
@click.option(
    "--interval",
    "-i",
    type=int,
    default=5,
    help="[Optional] Refresh interval in seconds when using --watch. Default: 5",
)
@click.option(
    "--compact",
    "-c",
    is_flag=True,
    help="[Optional] Use compact layout for smaller terminals",
)
def dashboard(watch: bool, interval: int, compact: bool) -> None:
    """Show the trading dashboard.

    A comprehensive view of your account, positions, orders, and market status.
    Use --watch for live updates.
    """
    import time
    from rich.live import Live

    config.validate()

    def render_dashboard():
        layout = make_layout()
        layout["header"].update(get_header_panel())
        layout["top_bar"].update(get_top_bar())
        layout["account"].update(get_account_panel())
        layout["positions"].update(get_positions_panel())
        layout["orders"].update(get_orders_panel())
        layout["news"].update(get_news_panel())
        return layout

    if watch:
        logger.info(
            f"Starting dashboard with {interval}s refresh. Press Ctrl+C to exit."
        )
        try:
            with Live(render_dashboard(), console=console, auto_refresh=False) as live:
                while True:
                    time.sleep(interval)
                    live.update(render_dashboard(), refresh=True)
        except KeyboardInterrupt:
            logger.info("Dashboard stopped.")
    else:
        console.print(render_dashboard())
