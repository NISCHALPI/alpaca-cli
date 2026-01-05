import rich_click as click
from datetime import datetime
from rich.console import Group
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
from alpaca_cli.cli.theme import (
    colors,
    icons,
    console,
    get_pl_color,
    get_pl_icon,
)
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest, StockSnapshotRequest

logger = get_logger("dashboard")


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


# get_pl_color and get_pl_icon are imported from theme module


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
    """Create a modern styled header banner."""
    now = datetime.now().astimezone()

    # Mode indicator
    mode = "PAPER" if config.IS_PAPER else "LIVE"
    mode_color = colors.PAPER_MODE if config.IS_PAPER else colors.LIVE_MODE
    mode_icon = "◉" if config.IS_PAPER else "●"

    # Build modern header text
    title = Text()

    # Top border with gradient effect
    title.append("┌", style=colors.BORDER)
    title.append("─" * 76, style=colors.BORDER)
    title.append("┐\n", style=colors.BORDER)

    # Main content line
    title.append("│  ", style=colors.BORDER)
    title.append("◆ ", style=colors.PRIMARY)
    title.append("ALPACA", style=f"bold {colors.PRIMARY}")
    title.append(" CLI", style="bold white")
    title.append("  ⋮  ", style=colors.MUTED)
    title.append("Trading Dashboard", style=f"{colors.SECONDARY}")
    title.append("  ⋮  ", style=colors.MUTED)
    title.append(f"{mode_icon} ", style=mode_color)
    title.append(mode, style=mode_color)
    title.append("  ⋮  ", style=colors.MUTED)
    title.append("🕐 ", style=colors.MUTED)
    title.append(now.strftime("%H:%M:%S"), style=colors.TIMESTAMP)
    title.append("  ", style="")

    # Padding to fill width
    title.append(" " * 14, style="")
    title.append("│\n", style=colors.BORDER)

    # Bottom border
    title.append("└", style=colors.BORDER)
    title.append("─" * 76, style=colors.BORDER)
    title.append("┘", style=colors.BORDER)

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
    status_color = colors.SUCCESS if clock.is_open else colors.ERROR
    status_icon = icons.OPEN if clock.is_open else icons.CLOSED

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
    text.append(f"  │  {next_label}: ", style=colors.MUTED)
    text.append(f"{next_session_local.strftime('%H:%M')}", style=colors.PRIMARY)
    text.append(
        f" ({hours:02d}:{minutes:02d}:{seconds:02d})", style=f"dim {colors.PRIMARY}"
    )

    return Panel(
        Align.center(text),
        title=f"[bold {colors.PANEL_MARKET}]{icons.CLOCK} Market Status[/bold {colors.PANEL_MARKET}]",
        border_style=colors.PANEL_MARKET,
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
        header_style=colors.HEADER,
        padding=(0, 1),
        expand=True,
    )
    table.add_column("Index", style=colors.SYMBOL)
    table.add_column("Price", justify="right", style=colors.PRICE)
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
        title=f"[bold {colors.ACCENT}]{icons.CHART} Market Indices[/bold {colors.ACCENT}]",
        border_style=colors.ACCENT,
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
        title=f"[bold {colors.PANEL_ACCOUNT}]{icons.ACCOUNT} Account Overview[/bold {colors.PANEL_ACCOUNT}]",
        border_style=colors.PANEL_ACCOUNT,
        box=box.ROUNDED,
    )


def get_positions_panel():
    """Enhanced positions panel with color gradients."""
    client = get_trading_client()
    positions = client.get_all_positions()

    table = Table(
        show_header=True,
        header_style=colors.HEADER,
        box=box.SIMPLE_HEAD,
        expand=True,
        padding=(0, 1),
    )
    table.add_column("Symbol", style=colors.SYMBOL)
    table.add_column("Qty", justify="right", style=colors.QUANTITY)
    table.add_column("Avg Cost", justify="right", style=colors.MUTED)
    table.add_column("Current", justify="right", style=colors.PRICE)
    table.add_column("Value", justify="right", style=colors.PRICE)
    table.add_column("P/L", justify="right")

    if not positions:
        return Panel(
            Align.center(
                Text(f"{icons.POSITION} No open positions", style=colors.MUTED),
                vertical="middle",
            ),
            title=f"[bold {colors.PANEL_POSITIONS}]{icons.POSITION} Positions[/bold {colors.PANEL_POSITIONS}]",
            border_style=colors.PANEL_POSITIONS,
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
        title=f"[bold {colors.PANEL_POSITIONS}]{icons.POSITION} Positions ({len(positions)})[/bold {colors.PANEL_POSITIONS}]",
        border_style=colors.PANEL_POSITIONS,
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
        header_style=colors.HEADER,
        box=box.SIMPLE_HEAD,
        expand=True,
        padding=(0, 1),
    )
    table.add_column("Symbol", style=colors.SYMBOL)
    table.add_column("Side")
    table.add_column("Type", style=colors.MUTED)
    table.add_column("Qty", justify="right", style=colors.QUANTITY)
    table.add_column("Price", justify="right", style=colors.PRICE)
    table.add_column("Status")

    if not orders:
        return Panel(
            Align.center(
                Text(f"{icons.ORDER} No open orders", style=colors.MUTED),
                vertical="middle",
            ),
            title=f"[bold {colors.PANEL_ORDERS}]{icons.ORDER} Open Orders[/bold {colors.PANEL_ORDERS}]",
            border_style=colors.PANEL_ORDERS,
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
        title=f"[bold {colors.PANEL_ORDERS}]{icons.ORDER} Open Orders ({len(orders)})[/bold {colors.PANEL_ORDERS}]",
        border_style=colors.PANEL_ORDERS,
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
        table.add_column("Time", style=colors.TIMESTAMP, min_width=6)
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
                headline_display = (
                    f"{headline_display} [{colors.MUTED}]({source})[/{colors.MUTED}]"
                )

            table.add_row(f"{icons.CLOCK} {time_str}", headline_display)

        return Panel(
            table,
            title=f"[bold {colors.PANEL_NEWS}]{icons.NEWS} Latest News (click to open)[/bold {colors.PANEL_NEWS}]",
            border_style=colors.PANEL_NEWS,
            box=box.ROUNDED,
        )
    except Exception as e:
        return Panel(
            f"[{colors.ERROR}]Failed to load news: {e}[/{colors.ERROR}]",
            title=f"[bold {colors.PANEL_NEWS}]{icons.NEWS} Latest News[/bold {colors.PANEL_NEWS}]",
            border_style=colors.PANEL_NEWS,
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
