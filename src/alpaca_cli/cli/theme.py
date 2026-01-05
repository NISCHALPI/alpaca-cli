"""Centralized theme configuration for CLI visual styling."""

from dataclasses import dataclass
from contextlib import contextmanager
from typing import Generator, Optional, List, Tuple, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box


@dataclass(frozen=True)
class ColorPalette:
    """Solarized Dark color palette for professional CLI styling.

    Based on Ethan Schoonover's Solarized palette - designed for
    optimal readability and reduced eye strain on dark backgrounds.
    """

    # Status colors - Solarized accent colors
    SUCCESS: str = "#859900"  # green
    ERROR: str = "#dc322f"  # red
    WARNING: str = "#b58900"  # yellow
    INFO: str = "#268bd2"  # blue
    MUTED: str = "#586e75"  # base01

    # P/L gradient colors - Solarized green to red
    PROFIT_HIGH: str = "bold #859900"  # green
    PROFIT_MED: str = "#859900"  # green
    PROFIT_LOW: str = "#2aa198"  # cyan (subtle positive)
    LOSS_LOW: str = "#cb4b16"  # orange (mild warning)
    LOSS_MED: str = "#dc322f"  # red
    LOSS_HIGH: str = "bold #dc322f"  # red
    NEUTRAL: str = "#586e75"  # base01

    # Mode indicators
    PAPER_MODE: str = "bold #b58900"  # yellow
    LIVE_MODE: str = "bold #dc322f"  # red

    # Table styles - Solarized High Contrast
    HEADER: str = "bold #fdf6e3 on #073642"  # cream on dark highlight
    BORDER: str = "#586e75"  # base01 (visible grey)
    ROW_ALT: str = "none"  # transparent/clean background
    TITLE: str = "bold #cb4b16"  # orange (standout title)

    # Column types - semantic coloring
    SYMBOL: str = "bold #93a1a1"  # base1
    PRICE: str = "#859900"  # green
    QUANTITY: str = "#2aa198"  # cyan
    TIMESTAMP: str = "#586e75"  # base01
    LABEL: str = "#586e75"  # base01

    # Accent colors - Solarized palette
    PRIMARY: str = "#268bd2"  # blue
    SECONDARY: str = "#d33682"  # magenta
    ACCENT: str = "#b58900"  # yellow

    # Dashboard panel colors - Solarized
    PANEL_ACCOUNT: str = "#859900"  # green
    PANEL_POSITIONS: str = "#d33682"  # magenta
    PANEL_ORDERS: str = "#2aa198"  # cyan
    PANEL_NEWS: str = "#b58900"  # yellow
    PANEL_MARKET: str = "#268bd2"  # blue


@dataclass(frozen=True)
class Icons:
    """Icons for visual enhancement."""

    SUCCESS: str = "✓"
    ERROR: str = "✗"
    WARNING: str = "⚠"
    INFO: str = "ℹ"

    # Financial
    PROFIT: str = "📈"
    LOSS: str = "📉"
    NEUTRAL: str = "➡️"
    ROCKET: str = "🚀"
    DROP: str = "🔻"

    # Trading
    BUY: str = "🟢"
    SELL: str = "🔴"
    PENDING: str = "🟡"

    # General
    MONEY: str = "💰"
    CASH: str = "💵"
    CHART: str = "📊"
    POSITION: str = "📊"
    ORDER: str = "📋"
    CLOCK: str = "🕐"
    NEWS: str = "📰"
    ACCOUNT: str = "💼"
    CONFIG: str = "⚙️"
    MARKET: str = "🏛️"
    OPEN: str = "🟢"
    CLOSED: str = "🔴"


# Global instances
colors = ColorPalette()
icons = Icons()
console = Console()


def get_pl_color(pct: float) -> str:
    """Get gradient color based on P/L percentage."""
    if pct >= 5:
        return colors.PROFIT_HIGH
    elif pct >= 2:
        return colors.PROFIT_MED
    elif pct >= 0:
        return colors.PROFIT_LOW
    elif pct >= -2:
        return colors.LOSS_LOW
    elif pct >= -5:
        return colors.LOSS_MED
    else:
        return colors.LOSS_HIGH


def get_pl_icon(pct: float) -> str:
    """Get icon based on P/L percentage."""
    if pct >= 2:
        return icons.ROCKET
    elif pct >= 0.5:
        return icons.PROFIT
    elif pct >= 0:
        return icons.NEUTRAL
    elif pct >= -2:
        return icons.LOSS
    else:
        return icons.DROP


def success_panel(message: str, title: Optional[str] = None) -> None:
    """Display a styled success message panel."""
    content = f"[{colors.SUCCESS}]{icons.SUCCESS}[/{colors.SUCCESS}] {message}"
    console.print(
        Panel(
            content,
            title=(
                f"[bold {colors.SUCCESS}]{title}[/bold {colors.SUCCESS}]"
                if title
                else None
            ),
            border_style=colors.SUCCESS,
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def error_panel(message: str, title: Optional[str] = None) -> None:
    """Display a styled error message panel."""
    content = f"[{colors.ERROR}]{icons.ERROR}[/{colors.ERROR}] {message}"
    console.print(
        Panel(
            content,
            title=(
                f"[bold {colors.ERROR}]{title}[/bold {colors.ERROR}]" if title else None
            ),
            border_style=colors.ERROR,
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def warning_panel(message: str, title: Optional[str] = None) -> None:
    """Display a styled warning message panel."""
    content = f"[{colors.WARNING}]{icons.WARNING}[/{colors.WARNING}] {message}"
    console.print(
        Panel(
            content,
            title=(
                f"[bold {colors.WARNING}]{title}[/bold {colors.WARNING}]"
                if title
                else None
            ),
            border_style=colors.WARNING,
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def info_panel(message: str, title: Optional[str] = None) -> None:
    """Display a styled info message panel."""
    content = f"[{colors.INFO}]{icons.INFO}[/{colors.INFO}] {message}"
    console.print(
        Panel(
            content,
            title=(
                f"[bold {colors.INFO}]{title}[/bold {colors.INFO}]" if title else None
            ),
            border_style=colors.INFO,
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def summary_card(
    title: str,
    items: List[Tuple[str, str]],
    icon: str = icons.CHART,
    border_color: str = colors.PRIMARY,
) -> None:
    """Display a summary card with key-value pairs."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style=colors.MUTED, min_width=16)
    table.add_column()

    for label, value in items:
        table.add_row(label, value)

    console.print(
        Panel(
            table,
            title=f"[bold]{icon} {title}[/bold]",
            border_style=border_color,
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def styled_table(
    title: str,
    columns: List[str],
    rows: List[List[Any]],
    show_mode: bool = True,
    border_color: str = colors.BORDER,
) -> None:
    """Display a styled table with consistent formatting."""
    from alpaca_cli.cli.utils import get_mode_indicator

    # Add mode indicator to title if requested
    full_title = f"{get_mode_indicator()} {title}" if show_mode else title

    table = Table(
        title=full_title,
        show_header=True,
        header_style=colors.HEADER,
        box=box.ROUNDED,
        border_style=border_color,
        row_styles=["", colors.ROW_ALT],
        padding=(0, 1),
        expand=False,
    )

    for col in columns:
        table.add_column(col)

    for row in rows:
        table.add_row(*[str(r) for r in row])

    console.print(table)


def weight_bar(pct: float, width: int = 10) -> str:
    """Generate a visual weight indicator bar."""
    if pct < 0:
        pct = 0
    elif pct > 100:
        pct = 100
    filled = int(pct / 100 * width)
    empty = width - filled
    bar = f"[{colors.PRIMARY}]{'█' * filled}{'░' * empty}[/{colors.PRIMARY}]"
    return f"{bar} {pct:.1f}%"


def confirm_action(
    title: str,
    items: List[Tuple[str, str]],
    icon: str = icons.ORDER,
) -> None:
    """Display a confirmation panel for important actions."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style=colors.MUTED)
    table.add_column()

    for label, value in items:
        table.add_row(label, value)

    console.print(
        Panel(
            table,
            title=f"[bold {colors.ACCENT}]{icon} {title}[/bold {colors.ACCENT}]",
            border_style=colors.ACCENT,
            box=box.DOUBLE,
            padding=(0, 1),
        )
    )


@contextmanager
def progress_spinner(description: str) -> Generator[None, None, None]:
    """Context manager for displaying a progress spinner."""
    with Progress(
        SpinnerColumn(style=colors.PRIMARY),
        TextColumn(f"[{colors.INFO}]{{task.description}}[/{colors.INFO}]"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description, total=None)
        yield


def format_side(side: str) -> str:
    """Format order side with color and icon."""
    if side.upper() == "BUY":
        return f"[{colors.SUCCESS}]{icons.BUY} BUY[/{colors.SUCCESS}]"
    else:
        return f"[{colors.ERROR}]{icons.SELL} SELL[/{colors.ERROR}]"


def format_status(status: str) -> str:
    """Format order/position status with appropriate color."""
    status_upper = status.upper()
    if status_upper in ("FILLED", "ACTIVE", "OPEN"):
        return f"[{colors.SUCCESS}]{status}[/{colors.SUCCESS}]"
    elif status_upper in ("PENDING", "NEW", "ACCEPTED", "PENDING_NEW"):
        return f"[{colors.WARNING}]{status}[/{colors.WARNING}]"
    elif status_upper in ("CANCELLED", "CANCELED", "REJECTED", "EXPIRED"):
        return f"[{colors.ERROR}]{status}[/{colors.ERROR}]"
    else:
        return f"[{colors.MUTED}]{status}[/{colors.MUTED}]"


def format_pl(value: float, pct: float, include_icon: bool = True) -> str:
    """Format P/L value with color and optional icon."""
    from alpaca_cli.cli.utils import format_currency

    color = get_pl_color(pct)
    icon = f"{get_pl_icon(pct)} " if include_icon else ""
    return f"[{color}]{icon}{format_currency(value)} ({pct:+.2f}%)[/{color}]"


def print_empty_state(message: str, icon: str = "📭") -> None:
    """Display an empty state message."""
    console.print(
        Panel(
            f"[{colors.MUTED}]{icon} {message}[/{colors.MUTED}]",
            border_style=colors.MUTED,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def create_table(
    title: str,
    columns: List[str],
    show_mode: bool = True,
    expand: bool = False,
    show_lines: bool = False,
    padding: Tuple[int, int] = (0, 2),
) -> Table:
    """Create a consistently themed table with modern styling.

    Args:
        title: Table title
        columns: List of column names
        show_mode: Whether to prepend Paper/Live mode indicator to title
        expand: Whether table should expand to fill width
        show_lines: Whether to show row separator lines
        padding: Cell padding (vertical, horizontal)

    Returns:
        A styled Rich Table ready to receive rows
    """
    from alpaca_cli.cli.utils import get_mode_indicator

    # Add mode indicator if requested
    full_title = f"{get_mode_indicator()} {title}" if show_mode else title

    table = Table(
        title=f"[{colors.TITLE}] {full_title} [/{colors.TITLE}]",
        title_style=colors.TITLE,
        title_justify="center",
        show_header=True,
        header_style=colors.HEADER,
        box=box.ROUNDED,
        border_style=colors.BORDER,
        row_styles=["", colors.ROW_ALT],
        padding=padding,
        expand=expand,
        show_lines=show_lines,
        caption_style=colors.MUTED,
        show_edge=True,
    )

    for col in columns:
        table.add_column(col)

    return table


def create_kv_table(title: str, show_mode: bool = True) -> Table:
    """Create a key-value style table (2 columns: label, value).

    Args:
        title: Table title
        show_mode: Whether to show mode indicator

    Returns:
        A styled Rich Table with Label and Value columns
    """
    from alpaca_cli.cli.utils import get_mode_indicator

    full_title = f"{get_mode_indicator()} {title}" if show_mode else title

    table = Table(
        title=f"[{colors.TITLE}]{full_title}[/{colors.TITLE}]",
        title_style=colors.TITLE,
        show_header=False,
        box=box.ROUNDED,
        border_style=colors.BORDER,
        padding=(0, 2),
        expand=False,
    )
    table.add_column("Label", style=colors.LABEL, min_width=16)
    table.add_column("Value", style=colors.PRICE)

    return table


def create_stream_table(title: str, columns: List[str]) -> Table:
    """Create a table styled for live streaming data.

    Args:
        title: Table title
        columns: Column names

    Returns:
        A styled Rich Table for streaming contexts
    """
    table = Table(
        title=f"[{colors.TITLE}]{title}[/{colors.TITLE}]",
        title_style=colors.TITLE,
        box=box.ROUNDED,
        border_style=colors.BORDER,
        header_style=colors.HEADER,
        padding=(0, 1),
    )

    # Apply semantic styling based on common column names
    for col in columns:
        col_lower = col.lower()
        if col_lower == "symbol":
            table.add_column(col, style=colors.SYMBOL)
        elif col_lower in ("bid", "ask", "price", "last trade"):
            style = (
                colors.SUCCESS
                if col_lower == "bid"
                else (colors.ERROR if col_lower == "ask" else colors.ACCENT)
            )
            table.add_column(col, style=style, justify="right")
        elif col_lower == "time":
            table.add_column(col, style=colors.TIMESTAMP)
        else:
            table.add_column(col)

    return table


def format_price(value: Any) -> str:
    """Format a price value with theme styling."""
    from alpaca_cli.cli.utils import format_currency

    return f"[{colors.PRICE}]{format_currency(value)}[/{colors.PRICE}]"


def format_symbol(symbol: str) -> str:
    """Format a symbol with theme styling."""
    return f"[{colors.SYMBOL}]{symbol}[/{colors.SYMBOL}]"


def format_quantity(qty: Any) -> str:
    """Format a quantity with theme styling."""
    return f"[{colors.QUANTITY}]{qty}[/{colors.QUANTITY}]"


def format_timestamp(timestamp: str) -> str:
    """Format a timestamp with theme styling."""
    return f"[{colors.TIMESTAMP}]{timestamp}[/{colors.TIMESTAMP}]"


def format_pl_simple(value: float, pct: float) -> str:
    """Format P/L with gradient color (no icon).

    Args:
        value: P/L dollar value
        pct: P/L percentage

    Returns:
        Formatted string with color based on P/L
    """
    from alpaca_cli.cli.utils import format_currency

    color = get_pl_color(pct)
    sign = "+" if pct >= 0 else ""
    return f"[{color}]{format_currency(value)} ({sign}{pct:.2f}%)[/{color}]"
