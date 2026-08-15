"""Utility functions for CLI commands."""

import json
import csv
import io
import math
from typing import List, Any, Dict, Optional, Literal
from decimal import Decimal, InvalidOperation

from rich.console import Console
from rich.table import Table

from alpaca_cli.core.constants import (
    MIN_TRADE_VALUE_THRESHOLD,
    MIN_QTY_THRESHOLD,
    MAX_SPREAD_THRESHOLD,
)
from alpaca_cli.core.logger import get_logger
from alpaca.data.requests import (
    StockLatestQuoteRequest,
    CryptoLatestQuoteRequest,
    StockLatestBarRequest,
    CryptoLatestBarRequest,
)

logger = get_logger("cli.utils")

console = Console()

# Output format type
OutputFormat = Literal["table", "json", "csv"]


def get_mode_indicator() -> str:
    """Get Paper/Live mode indicator string."""
    from alpaca_cli.core.config import config

    try:
        if config.IS_PAPER:
            return "[bold yellow][PAPER][/bold yellow]"
        else:
            return "[bold red][LIVE][/bold red]"
    except Exception:
        return ""


def output_data(
    title: str,
    columns: List[str],
    rows: List[List[Any]],
    output_format: OutputFormat = "table",
    show_mode: bool = True,
    export_path: Optional[str] = None,
) -> None:
    """Output data in specified format (table, json, or csv).

    Args:
        title: Table title (used in table format)
        columns: List of column names
        rows: List of rows, where each row is a list of values
        output_format: Output format ("table", "json", "csv")
        show_mode: Whether to show Paper/Live mode indicator
        export_path: Optional path to export data to file
    """
    if output_format == "json":
        # Convert rows to list of dicts
        data = [dict(zip(columns, row)) for row in rows]
        json_output = json.dumps(data, indent=2, default=str)

        if export_path:
            with open(export_path, "w") as f:
                f.write(json_output)
            console.print(f"[green]Exported to {export_path}[/green]")
        else:
            console.print(json_output)

    elif output_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([str(v) for v in row])
        csv_output = output.getvalue()

        if export_path:
            with open(export_path, "w") as f:
                f.write(csv_output)
            console.print(f"[green]Exported to {export_path}[/green]")
        else:
            console.print(csv_output)

    else:  # table format (default)
        print_table(title, columns, rows, show_mode)


def print_table(
    title: str,
    columns: List[str],
    rows: List[List[Any]],
    show_mode: bool = True,
) -> None:
    """Print a rich table with consistent theming.

    Args:
        title: Table title
        columns: List of column names
        rows: List of rows, where each row is a list of values
        show_mode: Whether to show Paper/Live mode indicator (default: True)
    """
    from alpaca_cli.cli.theme import create_table, console as theme_console

    table = create_table(title, columns, show_mode=show_mode)

    for row in rows:
        table.add_row(*[str(r) for r in row])

    theme_console.print(table)


def format_currency(value: Any) -> str:
    """Format a value as USD currency."""
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)


