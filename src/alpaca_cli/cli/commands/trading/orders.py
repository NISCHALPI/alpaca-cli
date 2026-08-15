# type: ignore
"""Orders commands - Create, Get, Replace, Cancel orders."""

from alpaca_cli.services.orders import _build_bracket_params
import rich_click as click
from typing import Optional, Union
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
    TrailingStopOrderRequest,
    GetOrdersRequest,
    TakeProfitRequest,
    StopLossRequest,
    ReplaceOrderRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    QueryOrderStatus,
    OrderStatus,
    OrderClass,
)
from alpaca.common.enums import Sort
from alpaca_cli.api.client import get_trading_client
from alpaca_cli.cli.formatters import print_table, format_currency, output_data
from alpaca_cli.core.logger import get_logger
import json
import time
from alpaca_cli.api.client import get_stock_data_client, get_crypto_data_client
from alpaca_cli.services.portfolio import (
    calculate_rebalancing_orders,
    get_stock_latest_price_with_fallback,
    get_crypto_latest_price_with_fallback,
)

logger = get_logger("trading.orders")


# =============================================================================
# ORDER REQUEST BUILDERS
# =============================================================================


def create_market_order(
    symbol: str,
    side: OrderSide,
    qty: Optional[float] = None,
    notional: Optional[float] = None,
    tif: str = "day",
    client_order_id: Optional[str] = None,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    stop_loss_limit: Optional[float] = None,
) -> MarketOrderRequest:
    """Create a MarketOrderRequest."""
    bracket = _build_bracket_params(take_profit, stop_loss, stop_loss_limit)
    return MarketOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        notional=notional,
        side=side,
        time_in_force=TimeInForce(tif),
        client_order_id=client_order_id,
        **bracket,
    )


def create_limit_order(
    symbol: str,
    side: OrderSide,
    qty: float,
    limit_price: float,
    tif: str = "day",
    extended_hours: bool = False,
    client_order_id: Optional[str] = None,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    stop_loss_limit: Optional[float] = None,
) -> LimitOrderRequest:
    """Create a LimitOrderRequest."""
    bracket = _build_bracket_params(take_profit, stop_loss, stop_loss_limit)
    return LimitOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=side,
        time_in_force=TimeInForce(tif),
        limit_price=limit_price,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
        **bracket,
    )


def create_stop_order(
    symbol: str,
    side: OrderSide,
    qty: float,
    stop_price: float,
    limit_price: Optional[float] = None,
    tif: str = "day",
    extended_hours: bool = False,
    client_order_id: Optional[str] = None,
) -> Union[StopOrderRequest, StopLimitOrderRequest]:
    """Create a StopOrderRequest or StopLimitOrderRequest."""
    if limit_price is not None:
        return StopLimitOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=side,
            time_in_force=TimeInForce(tif),
            stop_price=stop_price,
            limit_price=limit_price,
            extended_hours=extended_hours,
            client_order_id=client_order_id,
        )
    return StopOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=side,
        time_in_force=TimeInForce(tif),
        stop_price=stop_price,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
    )


def create_trailing_stop_order(
    symbol: str,
    side: OrderSide,
    qty: float,
    trail_price: Optional[float] = None,
    trail_percent: Optional[float] = None,
    tif: str = "day",
    extended_hours: bool = False,
    client_order_id: Optional[str] = None,
) -> TrailingStopOrderRequest:
    """Create a TrailingStopOrderRequest."""
    return TrailingStopOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=side,
        time_in_force=TimeInForce(tif),
        trail_price=trail_price,
        trail_percent=trail_percent,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
    )


# =============================================================================
# ORDER SUBMISSION & CANCELLATION
# =============================================================================


def submit_order(
    order_request: Union[
        MarketOrderRequest,
        LimitOrderRequest,
        StopOrderRequest,
        StopLimitOrderRequest,
        TrailingStopOrderRequest,
    ],
):
    """Submit an order request to the trading client and return the submitted order."""
    client = get_trading_client()
    try:
        order_type = order_request.__class__.__name__.replace(
            "OrderRequest", ""
        ).upper()

        # Format amount string for logging
        if order_request.qty:
            amount_str = f"{order_request.qty} shares of"
        elif hasattr(order_request, "notional") and order_request.notional:
            amount_str = f"${order_request.notional} of"
        else:
            amount_str = ""

        logger.info(
            f"Submitting {order_type} {order_request.side.name} order for {amount_str} {order_request.symbol}..."
        )
        order = client.submit_order(order_data=order_request)

        # Rich CLI summary table
        summary_rows = [
            ["Symbol", order.symbol],
            ["Side", order.side.name],
            ["Type", order.type.name if hasattr(order.type, "name") else str(order.type)],
        ]
        if order.qty:
            summary_rows.append(["Qty", str(order.qty)])
        if hasattr(order, "notional") and order.notional:
            summary_rows.append(["Notional", format_currency(order.notional)])
        if order.limit_price:
            summary_rows.append(["Limit Price", format_currency(order.limit_price)])
        if order.stop_price:
            summary_rows.append(["Stop Price", format_currency(order.stop_price)])
        if hasattr(order, "trail_price") and order.trail_price:
            summary_rows.append(["Trail Price", format_currency(order.trail_price)])
        if hasattr(order, "trail_percent") and order.trail_percent:
            summary_rows.append(["Trail %", f"{order.trail_percent}%"])
        summary_rows.append(["Time in Force", order.time_in_force.name])
        summary_rows.append(["Status", order.status.name])
        summary_rows.append(["Order ID", str(order.id)])

        print_table(
            f"✓ Order Submitted: {order.side.name} {order.symbol}",
            ["Field", "Value"],
            summary_rows,
        )

        return order
    except Exception as e:
        logger.error(f"Failed to submit order: {e}")
        return None


def cancel_order(order_id: str) -> None:
    """Cancel a single order by ID."""
    client = get_trading_client()
    try:
        logger.info(f"Cancelling order {order_id}...")
        client.cancel_order_by_id(order_id)
        logger.info(f"Order {order_id} cancelled.")
    except Exception as e:
        logger.error(f"Failed to cancel order: {e}")


def cancel_all_orders() -> None:
    """Cancel all open orders."""
    client = get_trading_client()
    try:
        logger.info("Cancelling ALL open orders...")
        client.cancel_orders()
        logger.info("Cancellation requested for all orders.")
    except Exception as e:
        logger.error(f"Failed to cancel all orders: {e}")


# Legacy alias for backward compatibility
def build_bracket_params(
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> dict:
    """Builds bracket order parameters. (Legacy alias)"""
    return _build_bracket_params(take_profit, stop_loss, stop_loss_limit)


@click.group()
def orders() -> None:
    """Order management (list, get, create, modify, cancel)."""
    pass


# --- LIST ORDERS ---
@orders.command("list")
@click.option(
    "--status",
    type=click.Choice(["OPEN", "CLOSED", "ALL"], case_sensitive=False),
    default="OPEN",
    help="[Optional] Filter by order status. Choices: OPEN, CLOSED, ALL. Default: OPEN",
)
@click.option(
    "--limit",
    type=int,
    default=50,
    help="[Optional] Maximum number of orders to return. Default: 50",
)
@click.option(
    "--days",
    type=int,
    default=0,
    help="[Optional] Filter orders from the last N days. Default: 0 (no filter)",
)
@click.option(
    "--direction",
    type=click.Choice(["asc", "desc"]),
    default="desc",
    help="[Optional] Sort direction. Choices: asc, desc. Default: desc",
)
@click.option(
    "--side",
    type=click.Choice(["buy", "sell"], case_sensitive=False),
    default=None,
    help="[Optional] Filter by order side. Choices: buy, sell",
)
@click.option(
    "--symbols",
    type=str,
    default=None,
    help="[Optional] Comma-separated list of symbols to filter by",
)
@click.option(
    "--nested/--no-nested",
    default=True,
    help="[Optional] Roll up multi-leg orders. Default: --nested",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="[Optional] Output format. Choices: table, json, csv. Default: table",
)
@click.option(
    "--export",
    type=click.Path(),
    default=None,
    help="[Optional] Export results to file path",
)
def list_orders(
    status: str,
    limit: int,
    days: int,
    direction: str,
    side: Optional[str],
    symbols: Optional[str],
    nested: bool,
    output_format: str,
    export: Optional[str],
) -> None:
    """Get orders with filtering."""
    from datetime import datetime, timedelta

    logger.info(f"Fetching {status} orders...")
    client = get_trading_client()

    after = datetime.now() - timedelta(days=days) if days > 0 else None
    symbol_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None
    order_side = (
        OrderSide.BUY
        if side and side.lower() == "buy"
        else (OrderSide.SELL if side else None)
    )

    try:
        req = GetOrdersRequest(
            status=getattr(QueryOrderStatus, status.upper()),
            limit=limit,
            nested=nested,
            after=after,
            direction=Sort.ASC if direction == "asc" else Sort.DESC,
            side=order_side,
            symbols=symbol_list,
        )
        orders_list = client.get_orders(filter=req)

        if not orders_list:
            logger.info(f"No {status} orders found.")
            return

        # Use full ID for JSON/CSV, truncated for table display
        def format_id(order_id: str) -> str:
            if output_format == "table":
                return str(order_id)[:8] + "..."
            return str(order_id)

        # Format qty/notional - show notional with $ prefix if qty is None
        def format_qty(order) -> str:
            if order.qty:
                return str(order.qty)
            elif hasattr(order, "notional") and order.notional:
                return f"${order.notional}"
            return "-"

        rows = [
            [
                str(o.created_at.strftime("%Y-%m-%d %H:%M")),
                format_id(o.id),
                o.symbol,
                o.side.name,
                o.type.name,
                format_qty(o),
                format_currency(o.filled_avg_price) if o.filled_avg_price else "-",
                o.status.name,
            ]
            for o in orders_list
        ]

        output_data(
            f"{status} Orders",
            [
                "Time",
                "ID",
                "Symbol",
                "Side",
                "Type",
                "Qty/Notional",
                "Fill Price",
                "Status",
            ],
            rows,
            output_format=output_format,
            export_path=export,
        )
    except Exception as e:
        logger.error(f"Failed to list orders: {e}")


# --- GET ORDER ---
@orders.command("get")
@click.argument("order_id", required=False)
@click.option(
    "--client-order-id",
    type=str,
    default=None,
    help="[Optional] Get order by client order ID instead of order ID",
)
def get_order(order_id: Optional[str], client_order_id: Optional[str]) -> None:
    """Get order details by ID or client order ID."""
    if not order_id and not client_order_id:
        logger.error("Must specify ORDER_ID or --client-order-id")
        return

    client = get_trading_client()

    try:
        if client_order_id:
            logger.info(f"Fetching order by client order ID: {client_order_id}...")
            order = client.get_order_by_client_id(client_order_id)
        else:
            logger.info(f"Fetching order {order_id}...")
            order = client.get_order_by_id(order_id)

        rows = [
            ["Order ID", str(order.id)],
            ["Client Order ID", order.client_order_id or "-"],
            ["Symbol", order.symbol],
            ["Side", order.side.name],
            ["Type", order.type.name],
            ["Qty", str(order.qty)],
            ["Filled Qty", str(order.filled_qty or 0)],
            [
                "Limit Price",
                format_currency(order.limit_price) if order.limit_price else "-",
            ],
            [
                "Stop Price",
                format_currency(order.stop_price) if order.stop_price else "-",
            ],
            [
                "Filled Avg Price",
                (
                    format_currency(order.filled_avg_price)
                    if order.filled_avg_price
                    else "-"
                ),
            ],
            ["Status", order.status.name],
            ["Time in Force", order.time_in_force.name],
            ["Extended Hours", str(order.extended_hours)],
            [
                "Created At",
                (
                    order.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if order.created_at
                    else "-"
                ),
            ],
        ]
        print_table(f"Order: {order.symbol}", ["Field", "Value"], rows)

        if order.legs:
            leg_rows = [
                [
                    str(l.id)[:8] + "...",
                    l.symbol,
                    l.side.name,
                    l.type.name,
                    str(l.qty),
                    l.status.name,
                ]
                for l in order.legs  # type: ignore
            ]
            print_table(
                "Order Legs",
                ["ID", "Symbol", "Side", "Type", "Qty", "Status"],
                leg_rows,
            )

    except Exception as e:
        logger.error(f"Failed to get order: {e}")


# --- CANCEL ORDER ---
@orders.command("cancel")
@click.argument("order_id", required=False)
@click.option(
    "--all",
    "cancel_all_flag",
    is_flag=True,
    help="[Optional] Cancel ALL open orders",
)
def cancel_order_cmd(order_id: Optional[str], cancel_all_flag: bool) -> None:
    """Cancel open orders."""
    if cancel_all_flag:
        cancel_all_orders()
    elif order_id:
        cancel_order(order_id)
    else:
        logger.error("Please specify an Order ID or use --all.")


# --- MODIFY ORDER ---
@orders.command("modify")
@click.argument("order_id")
@click.option(
    "--qty",
    type=float,
    default=None,
    help="[Optional] New quantity for the order",
)
@click.option(
    "--limit",
    "limit_price",
    type=float,
    default=None,
    help="[Optional] New limit price for the order",
)
@click.option(
    "--stop",
    "stop_price",
    type=float,
    default=None,
    help="[Optional] New stop price for the order",
)
@click.option(
    "--trail",
    type=float,
    default=None,
    help="[Optional] New trail price for trailing stop orders",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "ioc", "fok"]),
    default=None,
    help="[Optional] New time in force. Choices: day, gtc, ioc, fok",
)
@click.option(
    "--client-order-id",
    type=str,
    default=None,
    help="[Optional] New client order ID",
)
def modify_order(
    order_id: str,
    qty: Optional[float],
    limit_price: Optional[float],
    stop_price: Optional[float],
    trail: Optional[float],
    tif: Optional[str],
    client_order_id: Optional[str],
) -> None:
    """Modify/replace an existing order."""
    if all(
        x is None for x in [qty, limit_price, stop_price, trail, tif, client_order_id]
    ):
        logger.error("Must specify at least one modification")
        return

    client = get_trading_client()
    logger.info(f"Modifying order {order_id}...")

    try:
        req = ReplaceOrderRequest(
            qty=qty,
            limit_price=limit_price,
            stop_price=stop_price,
            trail=trail,
            time_in_force=TimeInForce(tif) if tif else None,
            client_order_id=client_order_id,
        )
        new_order = client.replace_order_by_id(order_id, req)
        logger.info(f"Order modified. New Order ID: {new_order.id}")
    except Exception as e:
        logger.error(f"Failed to modify order: {e}")


# --- BUY GROUP ---
@orders.group()
def buy():
    """Buy orders (market, limit, stop, trailing)."""
    pass


@buy.command("market")
@click.argument("symbol")
@click.argument("qty", type=float, required=False)
@click.option(
    "--notional",
    type=float,
    default=None,
    help="[Optional] Trade by dollar value instead of quantity",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, opg, cls, ioc, fok. Default: day",
)
@click.option(
    "--client-order-id",
    type=str,
    default=None,
    help="[Optional] Custom client order ID for tracking",
)
@click.option(
    "--take-profit",
    type=float,
    default=None,
    help="[Optional] Take profit limit price for bracket order",
)
@click.option(
    "--stop-loss",
    type=float,
    default=None,
    help="[Optional] Stop loss stop price for bracket order",
)
@click.option(
    "--stop-loss-limit",
    type=float,
    default=None,
    help="[Optional] Stop loss limit price for bracket order",
)
def buy_market(
    symbol: str,
    qty: Optional[float],
    notional: Optional[float],
    tif: str,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a MARKET buy order."""
    if qty is None and notional is None:
        logger.error("Must specify QTY or --notional")
        return
    req = create_market_order(
        symbol=symbol,
        side=OrderSide.BUY,
        qty=qty,
        notional=notional,
        tif=tif,
        client_order_id=client_order_id,
        take_profit=take_profit,
        stop_loss=stop_loss,
        stop_loss_limit=stop_loss_limit,
    )
    submit_order(req)


@buy.command("limit")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("limit_price", type=float)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, opg, cls, ioc, fok. Default: day",
)
@click.option(
    "--extended-hours",
    is_flag=True,
    help="[Optional] Allow execution during extended hours",
)
@click.option(
    "--client-order-id",
    type=str,
    default=None,
    help="[Optional] Custom client order ID for tracking",
)
@click.option(
    "--take-profit",
    type=float,
    default=None,
    help="[Optional] Take profit limit price for bracket order",
)
@click.option(
    "--stop-loss",
    type=float,
    default=None,
    help="[Optional] Stop loss stop price for bracket order",
)
@click.option(
    "--stop-loss-limit",
    type=float,
    default=None,
    help="[Optional] Stop loss limit price for bracket order",
)
def buy_limit(
    symbol: str,
    qty: float,
    limit_price: float,
    tif: str,
    extended_hours: bool,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a LIMIT buy order."""
    req = create_limit_order(
        symbol=symbol,
        side=OrderSide.BUY,
        qty=qty,
        limit_price=limit_price,
        tif=tif,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
        take_profit=take_profit,
        stop_loss=stop_loss,
        stop_loss_limit=stop_loss_limit,
    )
    submit_order(req)


@buy.command("stop")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("stop_price", type=float)
@click.option(
    "--limit",
    "limit_price",
    type=float,
    default=None,
    help="[Optional] Add limit price to convert to stop-limit order",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, opg, cls, ioc, fok. Default: day",
)
@click.option(
    "--extended-hours",
    is_flag=True,
    help="[Optional] Allow execution during extended hours",
)
@click.option(
    "--client-order-id",
    type=str,
    default=None,
    help="[Optional] Custom client order ID for tracking",
)
def buy_stop(
    symbol: str,
    qty: float,
    stop_price: float,
    limit_price: Optional[float],
    tif: str,
    extended_hours: bool,
    client_order_id: Optional[str],
) -> None:
    """Place a STOP or STOP-LIMIT buy order."""
    req = create_stop_order(
        symbol=symbol,
        side=OrderSide.BUY,
        qty=qty,
        stop_price=stop_price,
        limit_price=limit_price,
        tif=tif,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
    )
    submit_order(req)


@buy.command("trailing")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.option(
    "--trail-price",
    type=float,
    default=None,
    help="[Optional] Trail amount in dollars (mutually exclusive with --trail-percent)",
)
@click.option(
    "--trail-percent",
    type=float,
    default=None,
    help="[Optional] Trail amount as percentage (mutually exclusive with --trail-price)",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, opg, cls, ioc, fok. Default: day",
)
@click.option(
    "--extended-hours",
    is_flag=True,
    help="[Optional] Allow execution during extended hours",
)
@click.option(
    "--client-order-id",
    type=str,
    default=None,
    help="[Optional] Custom client order ID for tracking",
)
def buy_trailing(
    symbol: str,
    qty: float,
    trail_price: Optional[float],
    trail_percent: Optional[float],
    tif: str,
    extended_hours: bool,
    client_order_id: Optional[str],
) -> None:
    """Place a TRAILING STOP buy order."""
    if trail_price is None and trail_percent is None:
        logger.error("Must specify --trail-price or --trail-percent")
        return
    req = create_trailing_stop_order(
        symbol=symbol,
        side=OrderSide.BUY,
        qty=qty,
        trail_price=trail_price,
        trail_percent=trail_percent,
        tif=tif,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
    )
    submit_order(req)


# --- SELL GROUP ---
@orders.group()
def sell():
    """Sell orders (market, limit, stop, trailing)."""
    pass


@sell.command("market")
@click.argument("symbol")
@click.argument("qty", type=float, required=False)
@click.option(
    "--notional",
    type=float,
    default=None,
    help="[Optional] Trade by dollar value instead of quantity",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, opg, cls, ioc, fok. Default: day",
)
@click.option(
    "--client-order-id",
    type=str,
    default=None,
    help="[Optional] Custom client order ID for tracking",
)
@click.option(
    "--take-profit",
    type=float,
    default=None,
    help="[Optional] Take profit limit price for bracket order",
)
@click.option(
    "--stop-loss",
    type=float,
    default=None,
    help="[Optional] Stop loss stop price for bracket order",
)
@click.option(
    "--stop-loss-limit",
    type=float,
    default=None,
    help="[Optional] Stop loss limit price for bracket order",
)
def sell_market(
    symbol: str,
    qty: Optional[float],
    notional: Optional[float],
    tif: str,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a MARKET sell order."""
    if qty is None and notional is None:
        logger.error("Must specify QTY or --notional")
        return
    req = create_market_order(
        symbol=symbol,
        side=OrderSide.SELL,
        qty=qty,
        notional=notional,
        tif=tif,
        client_order_id=client_order_id,
        take_profit=take_profit,
        stop_loss=stop_loss,
        stop_loss_limit=stop_loss_limit,
    )
    submit_order(req)


@sell.command("limit")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("limit_price", type=float)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, opg, cls, ioc, fok. Default: day",
)
@click.option(
    "--extended-hours",
    is_flag=True,
    help="[Optional] Allow execution during extended hours",
)
@click.option(
    "--client-order-id",
    type=str,
    default=None,
    help="[Optional] Custom client order ID for tracking",
)
@click.option(
    "--take-profit",
    type=float,
    default=None,
    help="[Optional] Take profit limit price for bracket order",
)
@click.option(
    "--stop-loss",
    type=float,
    default=None,
    help="[Optional] Stop loss stop price for bracket order",
)
@click.option(
    "--stop-loss-limit",
    type=float,
    default=None,
    help="[Optional] Stop loss limit price for bracket order",
)
def sell_limit(
    symbol: str,
    qty: float,
    limit_price: float,
    tif: str,
    extended_hours: bool,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a LIMIT sell order."""
    req = create_limit_order(
        symbol=symbol,
        side=OrderSide.SELL,
        qty=qty,
        limit_price=limit_price,
        tif=tif,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
        take_profit=take_profit,
        stop_loss=stop_loss,
        stop_loss_limit=stop_loss_limit,
    )
    submit_order(req)


@sell.command("stop")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("stop_price", type=float)
@click.option(
    "--limit",
    "limit_price",
    type=float,
    default=None,
    help="[Optional] Add limit price to convert to stop-limit order",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, opg, cls, ioc, fok. Default: day",
)
@click.option(
    "--extended-hours",
    is_flag=True,
    help="[Optional] Allow execution during extended hours",
)
@click.option(
    "--client-order-id",
    type=str,
    default=None,
    help="[Optional] Custom client order ID for tracking",
)
def sell_stop(
    symbol: str,
    qty: float,
    stop_price: float,
    limit_price: Optional[float],
    tif: str,
    extended_hours: bool,
    client_order_id: Optional[str],
) -> None:
    """Place a STOP or STOP-LIMIT sell order."""
    req = create_stop_order(
        symbol=symbol,
        side=OrderSide.SELL,
        qty=qty,
        stop_price=stop_price,
        limit_price=limit_price,
        tif=tif,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
    )
    submit_order(req)


@sell.command("trailing")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.option(
    "--trail-price",
    type=float,
    default=None,
    help="[Optional] Trail amount in dollars (mutually exclusive with --trail-percent)",
)
@click.option(
    "--trail-percent",
    type=float,
    default=None,
    help="[Optional] Trail amount as percentage (mutually exclusive with --trail-price)",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, opg, cls, ioc, fok. Default: day",
)
@click.option(
    "--extended-hours",
    is_flag=True,
    help="[Optional] Allow execution during extended hours",
)
@click.option(
    "--client-order-id",
    type=str,
    default=None,
    help="[Optional] Custom client order ID for tracking",
)
def sell_trailing(
    symbol: str,
    qty: float,
    trail_price: Optional[float],
    trail_percent: Optional[float],
    tif: str,
    extended_hours: bool,
    client_order_id: Optional[str],
) -> None:
    """Place a TRAILING STOP sell order."""
    if trail_price is None and trail_percent is None:
        logger.error("Must specify --trail-price or --trail-percent")
        return
    req = create_trailing_stop_order(
        symbol=symbol,
        side=OrderSide.SELL,
        qty=qty,
        trail_price=trail_price,
        trail_percent=trail_percent,
        tif=tif,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
    )
    submit_order(req)


# --- REBALANCE ---
