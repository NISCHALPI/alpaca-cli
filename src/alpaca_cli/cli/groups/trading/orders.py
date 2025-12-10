"""Orders commands - Create, Get, Replace, Cancel orders."""

import rich_click as click
from typing import Optional, List, Any, Union
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
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.common.enums import Sort
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table, format_currency, output_data
from alpaca_cli.logger.logger import get_logger

logger = get_logger("trading.orders")


def submit_order(order_data) -> None:
    """Submit an order to the trading client."""
    client = get_trading_client()
    try:
        type_name = order_data.__class__.__name__.replace("OrderRequest", "").upper()
        logger.info(
            f"Submitting {type_name} {order_data.side.name} order for {order_data.qty} {order_data.symbol}..."
        )
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
    """Builds bracket order parameters."""
    params = {}
    if take_profit:
        params["take_profit"] = TakeProfitRequest(limit_price=take_profit)
    if stop_loss:
        params["stop_loss"] = StopLossRequest(
            stop_price=stop_loss, limit_price=stop_loss_limit
        )
    return params


@click.group()
def orders() -> None:
    """Order management (list, get, create, modify, cancel)."""
    pass


# --- LIST ORDERS ---
@orders.command("list")
@click.option(
    "--status",
    default="OPEN",
    type=click.Choice(["OPEN", "CLOSED", "ALL"], case_sensitive=False),
)
@click.option("--limit", default=50, help="Max number of orders")
@click.option("--days", default=0, help="Filter orders from the last N days")
@click.option("--direction", type=click.Choice(["asc", "desc"]), default="desc")
@click.option("--side", type=click.Choice(["buy", "sell"], case_sensitive=False))
@click.option("--symbols", help="Comma-separated list of symbols")
@click.option("--nested/--no-nested", default=True, help="Roll up multi-leg orders")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
)
@click.option("--export", type=click.Path(), help="Export to file path")
def list_orders(
    status, limit, days, direction, side, symbols, nested, output_format, export
):
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

        rows = [
            [
                str(o.created_at.strftime("%Y-%m-%d %H:%M")),
                str(o.id)[:8] + "...",
                o.symbol,
                o.side.name,
                o.type.name,
                str(o.qty),
                format_currency(o.filled_avg_price) if o.filled_avg_price else "-",
                o.status.name,
            ]
            for o in orders_list
        ]

        output_data(
            f"{status} Orders",
            ["Time", "ID", "Symbol", "Side", "Type", "Qty", "Fill Price", "Status"],
            rows,
            output_format=output_format,
            export_path=export,
        )
    except Exception as e:
        logger.error(f"Failed to list orders: {e}")


# --- GET ORDER ---
@orders.command("get")
@click.argument("order_id", required=False)
@click.option("--client-order-id", help="Get order by client order ID instead")
def get_order(order_id: Optional[str], client_order_id: Optional[str]):
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
                for l in order.legs
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
@click.option("--all", "cancel_all", is_flag=True, help="Cancel ALL open orders")
def cancel_order(order_id: Optional[str], cancel_all: bool):
    """Cancel open orders."""
    client = get_trading_client()

    if cancel_all:
        logger.info("Cancelling ALL open orders...")
        client.cancel_orders()
        logger.info("Cancellation requested for all orders.")
    elif order_id:
        logger.info(f"Cancelling order {order_id}...")
        try:
            client.cancel_order_by_id(order_id)
            logger.info(f"Order {order_id} cancelled.")
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
    else:
        logger.error("Please specify an Order ID or use --all.")


# --- MODIFY ORDER ---
@orders.command("modify")
@click.argument("order_id")
@click.option("--qty", type=float, help="New quantity")
@click.option("--limit", "limit_price", type=float, help="New limit price")
@click.option("--stop", "stop_price", type=float, help="New stop price")
@click.option("--trail", type=float, help="New trail price")
@click.option(
    "--tif", type=click.Choice(["day", "gtc", "ioc", "fok"]), help="New time in force"
)
@click.option("--client-order-id", help="New client order ID")
def modify_order(order_id, qty, limit_price, stop_price, trail, tif, client_order_id):
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
@click.option("--notional", type=float, help="Trade by dollar value")
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
)
@click.option("--client-order-id", help="Client Order ID")
@click.option("--take-profit", type=float, help="Take Profit Limit Price")
@click.option("--stop-loss", type=float, help="Stop Loss Stop Price")
@click.option("--stop-loss-limit", type=float, help="Stop Loss Limit Price")
def buy_market(
    symbol, qty, notional, tif, client_order_id, take_profit, stop_loss, stop_loss_limit
):
    """Place a MARKET buy order."""
    if qty is None and notional is None:
        logger.error("Must specify QTY or --notional")
        return
    bracket = build_bracket_params(take_profit, stop_loss, stop_loss_limit)
    req = MarketOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        notional=notional,
        side=OrderSide.BUY,
        time_in_force=TimeInForce(tif),
        client_order_id=client_order_id,
        **bracket,
    )
    submit_order(req)


@buy.command("limit")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("limit_price", type=float)
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
)
@click.option("--extended-hours", is_flag=True)
@click.option("--client-order-id")
@click.option("--take-profit", type=float)
@click.option("--stop-loss", type=float)
@click.option("--stop-loss-limit", type=float)
def buy_limit(
    symbol,
    qty,
    limit_price,
    tif,
    extended_hours,
    client_order_id,
    take_profit,
    stop_loss,
    stop_loss_limit,
):
    """Place a LIMIT buy order."""
    bracket = build_bracket_params(take_profit, stop_loss, stop_loss_limit)
    req = LimitOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce(tif),
        limit_price=limit_price,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
        **bracket,
    )
    submit_order(req)


@buy.command("stop")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("stop_price", type=float)
@click.option("--limit", "limit_price", type=float, help="Convert to Stop-Limit")
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
)
@click.option("--extended-hours", is_flag=True)
@click.option("--client-order-id")
def buy_stop(
    symbol, qty, stop_price, limit_price, tif, extended_hours, client_order_id
):
    """Place a STOP or STOP-LIMIT buy order."""
    if limit_price:
        req = StopLimitOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce(tif),
            stop_price=stop_price,
            limit_price=limit_price,
            extended_hours=extended_hours,
            client_order_id=client_order_id,
        )
    else:
        req = StopOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce(tif),
            stop_price=stop_price,
            extended_hours=extended_hours,
            client_order_id=client_order_id,
        )
    submit_order(req)


@buy.command("trailing")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.option("--trail-price", type=float)
@click.option("--trail-percent", type=float)
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
)
@click.option("--extended-hours", is_flag=True)
@click.option("--client-order-id")
def buy_trailing(
    symbol, qty, trail_price, trail_percent, tif, extended_hours, client_order_id
):
    """Place a TRAILING STOP buy order."""
    if not trail_price and not trail_percent:
        logger.error("Must specify --trail-price or --trail-percent")
        return
    req = TrailingStopOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce(tif),
        trail_price=trail_price,
        trail_percent=trail_percent,
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
@click.option("--notional", type=float)
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
)
@click.option("--client-order-id")
@click.option("--take-profit", type=float)
@click.option("--stop-loss", type=float)
@click.option("--stop-loss-limit", type=float)
def sell_market(
    symbol, qty, notional, tif, client_order_id, take_profit, stop_loss, stop_loss_limit
):
    """Place a MARKET sell order."""
    if qty is None and notional is None:
        logger.error("Must specify QTY or --notional")
        return
    bracket = build_bracket_params(take_profit, stop_loss, stop_loss_limit)
    req = MarketOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        notional=notional,
        side=OrderSide.SELL,
        time_in_force=TimeInForce(tif),
        client_order_id=client_order_id,
        **bracket,
    )
    submit_order(req)


@sell.command("limit")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("limit_price", type=float)
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
)
@click.option("--extended-hours", is_flag=True)
@click.option("--client-order-id")
@click.option("--take-profit", type=float)
@click.option("--stop-loss", type=float)
@click.option("--stop-loss-limit", type=float)
def sell_limit(
    symbol,
    qty,
    limit_price,
    tif,
    extended_hours,
    client_order_id,
    take_profit,
    stop_loss,
    stop_loss_limit,
):
    """Place a LIMIT sell order."""
    bracket = build_bracket_params(take_profit, stop_loss, stop_loss_limit)
    req = LimitOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce(tif),
        limit_price=limit_price,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
        **bracket,
    )
    submit_order(req)


@sell.command("stop")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.argument("stop_price", type=float)
@click.option("--limit", "limit_price", type=float)
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
)
@click.option("--extended-hours", is_flag=True)
@click.option("--client-order-id")
def sell_stop(
    symbol, qty, stop_price, limit_price, tif, extended_hours, client_order_id
):
    """Place a STOP or STOP-LIMIT sell order."""
    if limit_price:
        req = StopLimitOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce(tif),
            stop_price=stop_price,
            limit_price=limit_price,
            extended_hours=extended_hours,
            client_order_id=client_order_id,
        )
    else:
        req = StopOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce(tif),
            stop_price=stop_price,
            extended_hours=extended_hours,
            client_order_id=client_order_id,
        )
    submit_order(req)


@sell.command("trailing")
@click.argument("symbol")
@click.argument("qty", type=float)
@click.option("--trail-price", type=float)
@click.option("--trail-percent", type=float)
@click.option(
    "--tif",
    default="day",
    type=click.Choice(["day", "gtc", "opg", "cls", "ioc", "fok"]),
)
@click.option("--extended-hours", is_flag=True)
@click.option("--client-order-id")
def sell_trailing(
    symbol, qty, trail_price, trail_percent, tif, extended_hours, client_order_id
):
    """Place a TRAILING STOP sell order."""
    if not trail_price and not trail_percent:
        logger.error("Must specify --trail-price or --trail-percent")
        return
    req = TrailingStopOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce(tif),
        trail_price=trail_price,
        trail_percent=trail_percent,
        extended_hours=extended_hours,
        client_order_id=client_order_id,
    )
    submit_order(req)


# --- REBALANCE ---
@orders.command("rebalance")
@click.argument("target_weights_path", type=click.Path(exists=True))
@click.option("--allow-short", is_flag=True, help="Allow short selling if needed")
@click.option(
    "--dry-run/--execute", default=True, help="Simulate orders without executing"
)
@click.option("--force", is_flag=True, help="Force execution even if market is closed")
@click.option("--order-type", type=click.Choice(["market", "limit"]), default="market")
@click.option("--tif", type=click.Choice(["day", "gtc", "ioc", "fok"]), default="day")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def rebalance(target_weights_path, allow_short, dry_run, force, order_type, tif, yes):
    """Rebalance portfolio based on target weights JSON file.

    TARGET_WEIGHTS_PATH: Path to JSON file with target weights, e.g. {"AAPL": 0.5, "CASH": 0.5}
    """
    import json
    from alpaca.data.requests import StockLatestQuoteRequest, CryptoLatestQuoteRequest
    from alpaca_cli.core.client import get_stock_data_client, get_crypto_data_client
    from alpaca_cli.cli.utils import calculate_rebalancing_orders

    logger.info(f"Rebalancing portfolio (Dry Run: {dry_run})...")

    # Load weights
    try:
        with open(target_weights_path, "r") as f:
            target_weights = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load weights file: {e}")
        return

    if not isinstance(target_weights, dict):
        logger.error("Invalid weights format. Must be a JSON dictionary.")
        return

    # Auto-calculate CASH if not specified
    if "CASH" not in target_weights:
        target_weights["CASH"] = 1.0 - sum(target_weights.values())
        logger.info(
            f"'CASH' not specified, calculated as: {target_weights['CASH']:.2%}"
        )

    # Validate total
    total_weight = sum(target_weights.values())
    if not (0.99 <= total_weight <= 1.01):
        logger.error(
            f"Total weight is {total_weight:.4f}. Must be between 0.99 and 1.01."
        )
        return

    client = get_trading_client()

    # Check market status
    if not force and not dry_run:
        try:
            clock = client.get_clock()
            if not clock.is_open:
                logger.error("Market is closed. Use --force to override.")
                return
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
            return

    # Get account and positions
    try:
        account = client.get_account()
        positions = client.get_all_positions()
    except Exception as e:
        logger.error(f"Failed to fetch account: {e}")
        return

    current_equity = float(account.equity)
    current_positions = {p.symbol: float(p.qty) for p in positions}

    # Get all symbols
    all_symbols = set(target_weights.keys()) | set(current_positions.keys())
    all_symbols.discard("CASH")

    if not all_symbols:
        logger.info("No assets to rebalance.")
        return

    # Fetch prices
    crypto_symbols = [s for s in all_symbols if "/" in s]
    stock_symbols = [s for s in all_symbols if "/" not in s]
    current_prices = {}

    if stock_symbols:
        try:
            stock_client = get_stock_data_client()
            quotes = stock_client.get_stock_latest_quote(
                StockLatestQuoteRequest(symbol_or_symbols=list(stock_symbols))
            )
            for sym, q in quotes.items():
                current_prices[sym] = (q.bid_price + q.ask_price) / 2
        except Exception as e:
            logger.error(f"Failed to fetch stock prices: {e}")
            return

    if crypto_symbols:
        try:
            crypto_client = get_crypto_data_client()
            quotes = crypto_client.get_crypto_latest_quote(
                CryptoLatestQuoteRequest(symbol_or_symbols=list(crypto_symbols))
            )
            for sym, q in quotes.items():
                current_prices[sym] = (q.bid_price + q.ask_price) / 2
        except Exception as e:
            logger.error(f"Failed to fetch crypto prices: {e}")
            return

    # Check missing prices
    missing = [s for s in all_symbols if s not in current_prices]
    if missing:
        logger.error(f"Missing prices for: {missing}")
        return

    # Calculate orders
    try:
        orders_to_place = calculate_rebalancing_orders(
            current_equity=current_equity,
            current_positions=current_positions,
            target_weights=target_weights,
            current_prices=current_prices,
            allow_short=allow_short,
        )
    except ValueError as e:
        logger.error(f"Rebalancing error: {e}")
        return

    if not orders_to_place:
        logger.info("Portfolio is balanced. No orders needed.")
        return

    # Sort: SELLS first
    sell_orders = [o for o in orders_to_place if o["side"] == "sell"]
    buy_orders = [o for o in orders_to_place if o["side"] == "buy"]
    sorted_orders = sell_orders + buy_orders

    # Dry run display
    if dry_run:
        logger.info("Dry Run Mode - Orders to be placed:")
        rows = [
            [o["symbol"], o["side"].upper(), f"{o['qty']:.4f}", order_type.upper()]
            for o in sorted_orders
        ]
        print_table("Proposed Orders", ["Symbol", "Side", "Qty", "Type"], rows)
        return

    # Confirmation
    if not yes:
        rows = [
            [o["symbol"], o["side"].upper(), f"{o['qty']:.4f}", order_type.upper()]
            for o in sorted_orders
        ]
        print_table("Orders to Execute", ["Symbol", "Side", "Qty", "Type"], rows)
        if not click.confirm("Proceed with execution?"):
            logger.info("Cancelled.")
            return

    # Execute orders
    tif_enum = TimeInForce(tif)
    for o in sorted_orders:
        try:
            if order_type == "market":
                req = MarketOrderRequest(
                    symbol=o["symbol"],
                    qty=o["qty"],
                    side=OrderSide.BUY if o["side"] == "buy" else OrderSide.SELL,
                    time_in_force=tif_enum,
                )
            else:
                price = current_prices.get(o["symbol"])
                req = LimitOrderRequest(
                    symbol=o["symbol"],
                    qty=o["qty"],
                    side=OrderSide.BUY if o["side"] == "buy" else OrderSide.SELL,
                    time_in_force=tif_enum,
                    limit_price=price,
                )
            submit_order(req)
        except Exception as e:
            logger.error(f"Failed to submit order for {o['symbol']}: {e}")
