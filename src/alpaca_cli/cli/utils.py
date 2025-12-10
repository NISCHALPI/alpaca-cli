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
    PRECISION,
    MIN_TRADE_VALUE_THRESHOLD,
    MIN_QTY_THRESHOLD,
)

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
    """Print a rich table.

    Args:
        title: Table title
        columns: List of column names
        rows: List of rows, where each row is a list of values
        show_mode: Whether to show Paper/Live mode indicator (default: True)
    """
    # Add mode indicator to title if requested
    full_title = f"{get_mode_indicator()} {title}" if show_mode else title

    table = Table(title=full_title, show_header=True, header_style="bold magenta")

    for col in columns:
        table.add_column(col)

    for row in rows:
        table.add_row(*[str(r) for r in row])

    console.print(table)


def format_currency(value: Any) -> str:
    """Format a value as USD currency."""
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)


def validate_not_nan(name: str, value: Any) -> None:
    """
    Helper to strictly validate that a value is not NaN.
    Treats None as missing data (which is also invalid in this strict context),
    but specifically checks for float('nan').
    """
    if value is None:
        raise ValueError(f"Data validation failed: '{name}' is None (Missing).")

    if isinstance(value, float) and math.isnan(value):
        raise ValueError(f"Data validation failed: '{name}' is NaN.")


def calculate_rebalancing_orders(
    current_equity: float,
    current_positions: Dict[str, float],
    target_weights: Dict[str, float],
    current_prices: Dict[str, float],
    allow_short: bool = False,
) -> List[Dict[str, Any]]:
    """
    Calculate orders to rebalance portfolio with STRICT data validation.

    Args:
        current_equity: Current equity value
        current_positions: Current positions as a dictionary of symbol to quantity
        target_weights: Target weights as a dictionary of symbol to weight
        current_prices: Current prices as a dictionary of symbol to price
        allow_short: Whether to allow short selling

    Raises:
        ValueError: If ANY input data (Equity, Qty, Weight, Price) is NaN.
    """

    # 1. Global Equity Validation
    validate_not_nan("current_equity", current_equity)

    # Convert equity to Decimal
    try:
        equity_d = Decimal(str(current_equity))
    except InvalidOperation:
        raise ValueError(f"Invalid equity value: {current_equity}")

    if equity_d <= 0:
        raise ValueError(f"Current equity must be positive. Received: {equity_d}")

    orders = []

    # Identify all symbols involved (Union of keys)
    all_symbols = set(current_positions.keys()) | set(target_weights.keys())

    # Filter out Cash placeholder if it exists
    if "CASH" in all_symbols:
        all_symbols.remove("CASH")

    for symbol in all_symbols:
        # Retrieve raw values
        # We default to 0.0 only if the key is missing.
        # If the key exists but the value is NaN, the dict.get returns NaN.
        raw_qty = current_positions.get(symbol, 0.0)
        raw_weight = target_weights.get(symbol, 0.0)
        raw_price = current_prices.get(symbol)

        # 2. Strict Per-Symbol Validation
        # If a symbol is in the universe, we strictly require valid numbers.
        validate_not_nan(f"Qty for {symbol}", raw_qty)
        validate_not_nan(f"Weight for {symbol}", raw_weight)

        # Special Case for Price:
        # If we have a position OR a target, we generally require a valid price.
        # Even if we are just selling (Target=0), a NaN price implies a feed failure.
        # In a fault-proof strict system, we do not trade on corrupted feeds.
        if raw_qty != 0 or raw_weight != 0:
            validate_not_nan(f"Price for {symbol}", raw_price)

        # 3. Calculation (Decimal Precision)
        try:
            qty_d = Decimal(str(raw_qty))
            weight_d = Decimal(str(raw_weight))
            price_d = Decimal(str(raw_price))

            if price_d < 0:
                raise ValueError(f"Price for {symbol} cannot be negative: {price_d}")

        except InvalidOperation:
            raise ValueError(f"Non-numeric data found for {symbol}")

        # Skip irrelevant symbols (No position, No target)
        if qty_d == 0 and weight_d == 0:
            continue

        # Prevent Division by Zero if Price is 0 (even if not NaN)
        if price_d == 0:
            if weight_d > 0:
                raise ValueError(
                    f"Price for {symbol} is 0, cannot calculate buy quantity."
                )
            # If Price is 0 and we are Liquidating (weight=0), we can technically sell,
            # but a price of 0 usually indicates delisting or data error.
            # Strict mode: Raise Error.
            raise ValueError(f"Price for {symbol} is 0. Aborting rebalance.")

        # Logic: Calculate Target Quantity
        target_value_d = equity_d * weight_d
        target_qty_d = target_value_d / price_d

        diff_qty_d = target_qty_d - qty_d

        # 4. Short Selling Safety Check
        final_qty_d = qty_d + diff_qty_d
        if final_qty_d < 0 and not allow_short:
            # Allow for microscopic precision errors (e.g. -0.000000001) -> Snap to 0
            if abs(final_qty_d) < MIN_QTY_THRESHOLD:
                diff_qty_d = -qty_d  # Close exactly
            else:
                # If the math implies a true short position, we raise an error in strict mode
                # rather than silently skipping.
                raise ValueError(
                    f"Calculation results in illegal short position for {symbol}. Target Weight: {weight_d}"
                )

        # 5. Dust Thresholds
        if abs(diff_qty_d) < MIN_QTY_THRESHOLD:
            continue

        trade_value = abs(diff_qty_d) * price_d
        if trade_value < MIN_TRADE_VALUE_THRESHOLD:
            # Check if this is a full liquidation. If so, ignore threshold and clean up dust.
            is_liquidation = weight_d == 0
            if not is_liquidation:
                continue

        side = "buy" if diff_qty_d > 0 else "sell"

        orders.append(
            {
                "symbol": symbol,
                "qty": float(abs(diff_qty_d)),
                "side": side,
                "type": "market",
            }
        )

    return orders
