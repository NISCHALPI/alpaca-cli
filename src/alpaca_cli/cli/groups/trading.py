import rich_click as click
from typing import Optional, List, Any, Union
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    TrailingStopOrderRequest,
    GetOrdersRequest,
    TakeProfitRequest,
    StopLossRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    OrderStatus,
    OrderClass,
    QueryOrderStatus,
)
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger

logger = get_logger("trading")


@click.group()
def trading() -> None:
    """Trading management commands."""
    pass


def submit_order(
    order_data: Union[
        MarketOrderRequest,
        LimitOrderRequest,
        StopOrderRequest,
        TrailingStopOrderRequest,
    ],
) -> None:
    client = get_trading_client()
    try:
        # Log the type of order being placed
        type_name = order_data.__class__.__name__.replace("OrderRequest", "").upper()
        symbol = order_data.symbol
        qty = order_data.qty
        side = order_data.side.name

        logger.info(f"Submitting {type_name} {side} order for {qty} {symbol}...")

        order = client.submit_order(order_data=order_data)
        logger.info(f"Order submitted successfully: {order.id}")
        logger.info(f"Status: {order.status}")
    except Exception as e:
        logger.error(f"Failed to submit order: {e}")


def build_bracket_params(
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> dict:
    """Builds bracket order parameters (take_profit and stop_loss requests)."""
    params = {}
    if take_profit:
        params["take_profit"] = TakeProfitRequest(limit_price=take_profit)

    if stop_loss:
        params["stop_loss"] = StopLossRequest(
            stop_price=stop_loss, limit_price=stop_loss_limit
        )

    return params


# --- BUY COMMANDS ---
@trading.group()
def buy() -> None:
    """Buy assets with various order types."""
    pass


@buy.command()
@click.argument("symbol")
@click.argument("qty", type=float)
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"], case_sensitive=False),
    help="Time in Force",
)
@click.option("--client-order-id", help="Client Order ID")
@click.option(
    "--take-profit", type=float, help="Take Profit Limit Price (triggers Bracket Order)"
)
@click.option(
    "--stop-loss", type=float, help="Stop Loss Stop Price (triggers Bracket Order)"
)
@click.option("--stop-loss-limit", type=float, help="Stop Loss Limit Price (optional)")
def market(
    symbol: str,
    qty: float,
    tif: str,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a MARKET buy order."""
    bracket_params = build_bracket_params(take_profit, stop_loss, stop_loss_limit)

    req = MarketOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce(tif.lower()),
        client_order_id=client_order_id,
        **bracket_params,
    )
    submit_order(req)


@buy.command()
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("limit_price", type=float)
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"], case_sensitive=False),
    help="Time in Force",
)
@click.option("--extended-hours", is_flag=True, help="Enable Extended Hours Execution")
@click.option("--client-order-id", help="Client Order ID")
@click.option(
    "--take-profit", type=float, help="Take Profit Limit Price (triggers Bracket Order)"
)
@click.option(
    "--stop-loss", type=float, help="Stop Loss Stop Price (triggers Bracket Order)"
)
@click.option("--stop-loss-limit", type=float, help="Stop Loss Limit Price (optional)")
def limit(
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
    bracket_params = build_bracket_params(take_profit, stop_loss, stop_loss_limit)

    req = LimitOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce(tif.lower()),
        limit_price=limit_price,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
        **bracket_params,
    )
    submit_order(req)


@buy.command()
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("stop_price", type=float)
@click.option("--limit", type=float, help="Limit price (converts to Stop-Limit)")
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"], case_sensitive=False),
    help="Time in Force",
)
@click.option("--extended-hours", is_flag=True, help="Enable Extended Hours Execution")
@click.option("--client-order-id", help="Client Order ID")
@click.option(
    "--take-profit", type=float, help="Take Profit Limit Price (triggers Bracket Order)"
)
@click.option(
    "--stop-loss", type=float, help="Stop Loss Stop Price (triggers Bracket Order)"
)
@click.option("--stop-loss-limit", type=float, help="Stop Loss Limit Price (optional)")
def stop(
    symbol: str,
    qty: float,
    stop_price: float,
    limit: Optional[float],
    tif: str,
    extended_hours: bool,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a STOP (or Stop-Limit) buy order."""
    bracket_params = build_bracket_params(take_profit, stop_loss, stop_loss_limit)

    if limit:
        from alpaca.trading.requests import StopLimitOrderRequest

        req = StopLimitOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce(tif.lower()),
            stop_price=stop_price,
            limit_price=limit,
            extended_hours=extended_hours,
            client_order_id=client_order_id,
            **bracket_params,
        )
    else:
        req = StopOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce(tif.lower()),
            stop_price=stop_price,
            extended_hours=extended_hours,
            client_order_id=client_order_id,
            **bracket_params,
        )
    submit_order(req)


@buy.command()
@click.argument("symbol")
@click.argument("qty", type=float)
@click.option("--trail-price", type=float, help="Trailing stop price offset")
@click.option("--trail-percent", type=float, help="Trailing stop percent offset")
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"], case_sensitive=False),
    help="Time in Force",
)
@click.option("--extended-hours", is_flag=True, help="Enable Extended Hours Execution")
@click.option("--client-order-id", help="Client Order ID")
@click.option(
    "--take-profit", type=float, help="Take Profit Limit Price (triggers Bracket Order)"
)
@click.option(
    "--stop-loss", type=float, help="Stop Loss Stop Price (triggers Bracket Order)"
)
@click.option("--stop-loss-limit", type=float, help="Stop Loss Limit Price (optional)")
def trailing(
    symbol: str,
    qty: float,
    trail_price: Optional[float],
    trail_percent: Optional[float],
    tif: str,
    extended_hours: bool,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a TRAILING STOP buy order."""
    if not trail_price and not trail_percent:
        logger.error("Must specify either --trail-price or --trail-percent")
        return

    bracket_params = build_bracket_params(take_profit, stop_loss, stop_loss_limit)

    req = TrailingStopOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce(tif.lower()),
        trail_price=trail_price,
        trail_percent=trail_percent,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
        **bracket_params,
    )
    submit_order(req)


# --- SELL COMMANDS ---
@trading.group()
def sell() -> None:
    """Sell assets with various order types."""
    pass


@sell.command()
@click.argument("symbol")
@click.argument("qty", type=float)
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"], case_sensitive=False),
    help="Time in Force",
)
@click.option("--client-order-id", help="Client Order ID")
@click.option(
    "--take-profit", type=float, help="Take Profit Limit Price (triggers Bracket Order)"
)
@click.option(
    "--stop-loss", type=float, help="Stop Loss Stop Price (triggers Bracket Order)"
)
@click.option("--stop-loss-limit", type=float, help="Stop Loss Limit Price (optional)")
def market(
    symbol: str,
    qty: float,
    tif: str,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a MARKET sell order."""
    bracket_params = build_bracket_params(take_profit, stop_loss, stop_loss_limit)

    req = MarketOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce(tif.lower()),
        client_order_id=client_order_id,
        **bracket_params,
    )
    submit_order(req)


@sell.command()
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("limit_price", type=float)
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"], case_sensitive=False),
    help="Time in Force",
)
@click.option("--extended-hours", is_flag=True, help="Enable Extended Hours Execution")
@click.option("--client-order-id", help="Client Order ID")
@click.option(
    "--take-profit", type=float, help="Take Profit Limit Price (triggers Bracket Order)"
)
@click.option(
    "--stop-loss", type=float, help="Stop Loss Stop Price (triggers Bracket Order)"
)
@click.option("--stop-loss-limit", type=float, help="Stop Loss Limit Price (optional)")
def limit(
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
    bracket_params = build_bracket_params(take_profit, stop_loss, stop_loss_limit)

    req = LimitOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce(tif.lower()),
        limit_price=limit_price,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
        **bracket_params,
    )
    submit_order(req)


@sell.command()
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("stop_price", type=float)
@click.option("--limit", type=float, help="Limit price (converts to Stop-Limit)")
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"], case_sensitive=False),
    help="Time in Force",
)
@click.option("--extended-hours", is_flag=True, help="Enable Extended Hours Execution")
@click.option("--client-order-id", help="Client Order ID")
@click.option(
    "--take-profit", type=float, help="Take Profit Limit Price (triggers Bracket Order)"
)
@click.option(
    "--stop-loss", type=float, help="Stop Loss Stop Price (triggers Bracket Order)"
)
@click.option("--stop-loss-limit", type=float, help="Stop Loss Limit Price (optional)")
def stop(
    symbol: str,
    qty: float,
    stop_price: float,
    limit: Optional[float],
    tif: str,
    extended_hours: bool,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a STOP (or Stop-Limit) sell order."""
    bracket_params = build_bracket_params(take_profit, stop_loss, stop_loss_limit)

    if limit:
        from alpaca.trading.requests import StopLimitOrderRequest

        req = StopLimitOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce(tif.lower()),
            stop_price=stop_price,
            limit_price=limit,
            extended_hours=extended_hours,
            client_order_id=client_order_id,
            **bracket_params,
        )
    else:
        req = StopOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce(tif.lower()),
            stop_price=stop_price,
            extended_hours=extended_hours,
            client_order_id=client_order_id,
            **bracket_params,
        )
    submit_order(req)


@sell.command()
@click.argument("symbol")
@click.argument("qty", type=float)
@click.option("--trail-price", type=float, help="Trailing stop price offset")
@click.option("--trail-percent", type=float, help="Trailing stop percent offset")
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"], case_sensitive=False),
    help="Time in Force",
)
@click.option("--extended-hours", is_flag=True, help="Enable Extended Hours Execution")
@click.option("--client-order-id", help="Client Order ID")
@click.option(
    "--take-profit", type=float, help="Take Profit Limit Price (triggers Bracket Order)"
)
@click.option(
    "--stop-loss", type=float, help="Stop Loss Stop Price (triggers Bracket Order)"
)
@click.option("--stop-loss-limit", type=float, help="Stop Loss Limit Price (optional)")
def trailing(
    symbol: str,
    qty: float,
    trail_price: Optional[float],
    trail_percent: Optional[float],
    tif: str,
    extended_hours: bool,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a TRAILING STOP sell order."""
    if not trail_price and not trail_percent:
        logger.error("Must specify either --trail-price or --trail-percent")
        return

    bracket_params = build_bracket_params(take_profit, stop_loss, stop_loss_limit)

    req = TrailingStopOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce(tif.lower()),
        trail_price=trail_price,
        trail_percent=trail_percent,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
        **bracket_params,
    )
    submit_order(req)


@trading.command()
@click.option(
    "--status",
    default="OPEN",
    type=click.Choice(["OPEN", "CLOSED", "ALL"], case_sensitive=False),
    help="Filter by order status",
)
@click.option("--limit", default=50, help="Max number of orders to list")
@click.option("--days", default=0, help="Filter orders from the last N days")
def orders(status: str, limit: int, days: int) -> None:
    """List orders."""
    logger.info(f"Fetching {status} orders (Limit: {limit})...")

    from datetime import datetime, timedelta

    after = None
    if days > 0:
        after = datetime.now() - timedelta(days=days)
        logger.info(f"Filtering orders after: {after.strftime('%Y-%m-%d')}")

    client = get_trading_client()

    try:
        req = GetOrdersRequest(
            status=getattr(QueryOrderStatus, status.upper()),
            limit=limit,
            nested=True,  # Show nested orders if any (e.g. OCO legs)
            after=after,
        )
        orders_list = client.get_orders(filter=req)

        if not orders_list:
            logger.info(f"No {status} orders found.")
            return

        rows: List[List[Any]] = []
        for o in orders_list:
            rows.append(
                [
                    str(o.created_at.strftime("%Y-%m-%d %H:%M:%S")),
                    o.id,
                    o.symbol,
                    o.side.name,
                    o.type.name,
                    str(o.qty),
                    format_currency(o.filled_avg_price) if o.filled_avg_price else "-",
                    o.status.name,
                ]
            )

        print_table(
            f"{status} Orders",
            ["Time", "ID", "Symbol", "Side", "Type", "Qty", "Fill Price", "Status"],
            rows,
        )

    except Exception as e:
        logger.error(f"Failed to list orders: {e}")


@trading.command()
@click.argument("order_id", required=False)
@click.option("--all", is_flag=True, help="Cancel ALL open orders")
def cancel(order_id: Optional[str], all: bool) -> None:
    """Cancel open orders."""
    client = get_trading_client()

    if all:
        logger.info("Cancelling ALL open orders...")
        cancel_statuses = client.cancel_orders()
        logger.info("Requested cancellation for all orders.")
    elif order_id:
        logger.info(f"Cancelling order {order_id}...")
        try:
            client.cancel_order_by_id(order_id)
            logger.info(f"Order {order_id} cancelled.")
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
    else:
        logger.error("Please specify an Order ID or use --all.")
