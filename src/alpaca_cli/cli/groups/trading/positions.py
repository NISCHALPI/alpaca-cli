"""Positions commands - Get All Positions, Get Open Position, Close Position, Exercise Option."""

import rich_click as click
from typing import List, Any, Optional
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger

logger = get_logger("trading.positions")


@click.group()
def positions() -> None:
    """Position management (list, get, close, exercise)."""
    pass


@positions.command("list")
def list_positions() -> None:
    """Get all open positions."""
    logger.info("Fetching open positions...")
    client = get_trading_client()
    pos_list = client.get_all_positions()

    if not pos_list:
        logger.info("No open positions.")
        return

    rows: List[List[Any]] = []
    for pos in pos_list:
        pl_percent = float(pos.unrealized_plpc) * 100
        pl_color = "green" if pl_percent >= 0 else "red"
        pl_str = f"[{pl_color}]{format_currency(pos.unrealized_pl)} ({pl_percent:.2f}%)[/{pl_color}]"

        rows.append(
            [
                pos.symbol,
                pos.side.value if hasattr(pos.side, "value") else str(pos.side),
                str(pos.qty),
                format_currency(pos.avg_entry_price),
                format_currency(pos.current_price),
                format_currency(pos.market_value),
                pl_str,
            ]
        )

    print_table(
        "Open Positions",
        ["Symbol", "Side", "Qty", "Avg Entry", "Current", "Market Value", "P/L"],
        rows,
    )


@positions.command("get")
@click.argument("symbol_or_asset_id")
def get_position(symbol_or_asset_id: str) -> None:
    """Get a specific open position by symbol or asset ID."""
    logger.info(f"Fetching position for {symbol_or_asset_id}...")
    client = get_trading_client()

    try:
        pos = client.get_open_position(symbol_or_asset_id.upper())
        pl_percent = float(pos.unrealized_plpc) * 100
        pl_color = "green" if pl_percent >= 0 else "red"

        rows = [
            ["Symbol", pos.symbol],
            ["Asset ID", str(pos.asset_id)],
            ["Side", pos.side.value if hasattr(pos.side, "value") else str(pos.side)],
            ["Quantity", str(pos.qty)],
            ["Avg Entry Price", format_currency(pos.avg_entry_price)],
            ["Current Price", format_currency(pos.current_price)],
            ["Market Value", format_currency(pos.market_value)],
            [
                "Unrealized P/L",
                f"[{pl_color}]{format_currency(pos.unrealized_pl)}[/{pl_color}]",
            ],
            ["Unrealized P/L %", f"[{pl_color}]{pl_percent:.2f}%[/{pl_color}]"],
        ]

        print_table(f"Position: {pos.symbol}", ["Field", "Value"], rows)

    except Exception as e:
        logger.error(f"Failed to get position: {e}")


@positions.command("close")
@click.argument("symbol_or_asset_id", required=False)
@click.option("--all", "close_all", is_flag=True, help="Close ALL open positions")
@click.option("--qty", type=float, help="Partial close: number of shares/contracts")
@click.option("--percentage", type=float, help="Partial close: percentage (0-100)")
@click.option("--cancel-orders", is_flag=True, help="Cancel open orders before closing")
def close_position(
    symbol_or_asset_id: Optional[str],
    close_all: bool,
    qty: Optional[float],
    percentage: Optional[float],
    cancel_orders: bool,
) -> None:
    """Close position(s)."""
    from alpaca.trading.requests import ClosePositionRequest

    client = get_trading_client()

    if close_all:
        logger.info("Closing ALL open positions...")
        try:
            responses = client.close_all_positions(cancel_orders=cancel_orders)
            if not responses:
                logger.info("No positions to close.")
                return
            for resp in responses:
                if resp.status == 200:
                    logger.info(f"Closed position: {resp.symbol}")
                else:
                    logger.error(f"Failed to close {resp.symbol}: {resp.body}")
        except Exception as e:
            logger.error(f"Failed to close all positions: {e}")
        return

    if not symbol_or_asset_id:
        logger.error("Must specify SYMBOL_OR_ASSET_ID or --all flag")
        return

    logger.info(f"Closing position for {symbol_or_asset_id.upper()}...")

    try:
        req = None
        if qty:
            req = ClosePositionRequest(qty=str(qty))
        elif percentage:
            req = ClosePositionRequest(percentage=str(percentage / 100))

        order = client.close_position(symbol_or_asset_id.upper(), close_options=req)
        logger.info(f"Position close order submitted: {order.id}")
        logger.info(
            f"Side: {order.side.name}, Qty: {order.qty}, Status: {order.status.name}"
        )
    except Exception as e:
        logger.error(f"Failed to close position: {e}")


@positions.command("exercise")
@click.argument("symbol_or_contract_id")
def exercise_option(symbol_or_contract_id: str) -> None:
    """Exercise an option contract position."""
    client = get_trading_client()
    logger.info(f"Exercising option contract {symbol_or_contract_id}...")

    try:
        result = client.exercise_options_position(symbol_or_contract_id.upper())
        logger.info(f"Option exercise submitted successfully.")
        if result:
            logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"Failed to exercise option: {e}")
