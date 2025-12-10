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
from alpaca_cli.core.client import (
    get_trading_client,
    get_stock_data_client,
    get_crypto_data_client,
)
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger
from alpaca.data.requests import StockLatestQuoteRequest, CryptoLatestQuoteRequest

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
@click.argument("qty", type=float, required=False, default=None)
@click.option(
    "--notional",
    type=float,
    default=None,
    help="Trade by dollar value instead of qty (for fractional shares)",
)
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
    qty: Optional[float],
    notional: Optional[float],
    tif: str,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a MARKET buy order. Use QTY for shares or --notional for dollar value."""
    # Validate that exactly one of qty or notional is provided
    if qty is None and notional is None:
        logger.error("Must specify either QTY or --notional")
        return
    if qty is not None and notional is not None:
        logger.error("Cannot specify both QTY and --notional")
        return

    bracket_params = build_bracket_params(take_profit, stop_loss, stop_loss_limit)

    req = MarketOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        notional=notional,
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
@click.argument("qty", type=float, required=False, default=None)
@click.option(
    "--notional",
    type=float,
    default=None,
    help="Trade by dollar value instead of qty (for fractional shares)",
)
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
    qty: Optional[float],
    notional: Optional[float],
    tif: str,
    client_order_id: Optional[str],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
) -> None:
    """Place a MARKET sell order. Use QTY for shares or --notional for dollar value."""
    # Validate that exactly one of qty or notional is provided
    if qty is None and notional is None:
        logger.error("Must specify either QTY or --notional")
        return
    if qty is not None and notional is not None:
        logger.error("Cannot specify both QTY and --notional")
        return

    bracket_params = build_bracket_params(take_profit, stop_loss, stop_loss_limit)

    req = MarketOrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        notional=notional,
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
@click.option(
    "--direction",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default="desc",
    help="Sort direction by submission time",
)
@click.option(
    "--side",
    type=click.Choice(["buy", "sell"], case_sensitive=False),
    default=None,
    help="Filter by order side",
)
@click.option(
    "--symbols",
    default=None,
    help="Comma-separated list of symbols to filter",
)
@click.option(
    "--nested/--no-nested",
    default=True,
    help="Roll up multi-leg orders under primary",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.option(
    "--export",
    type=click.Path(),
    default=None,
    help="Export to file path",
)
def orders(
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
    """List orders with advanced filtering."""
    from alpaca.common.enums import Sort
    from alpaca_cli.cli.utils import output_data

    logger.info(f"Fetching {status} orders (Limit: {limit}, Direction: {direction})...")

    from datetime import datetime, timedelta

    after = None
    if days > 0:
        after = datetime.now() - timedelta(days=days)
        logger.info(f"Filtering orders after: {after.strftime('%Y-%m-%d')}")

    # Parse symbols if provided
    symbol_list = None
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        logger.info(f"Filtering by symbols: {symbol_list}")

    # Parse side if provided
    order_side = None
    if side:
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        logger.info(f"Filtering by side: {order_side.name}")

    client = get_trading_client()

    try:
        req = GetOrdersRequest(
            status=getattr(QueryOrderStatus, status.upper()),
            limit=limit,
            nested=nested,
            after=after,
            direction=Sort.ASC if direction.lower() == "asc" else Sort.DESC,
            side=order_side,
            symbols=symbol_list,
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
                    str(o.id),
                    o.symbol,
                    o.side.name,
                    o.type.name,
                    str(o.qty),
                    format_currency(o.filled_avg_price) if o.filled_avg_price else "-",
                    o.status.name,
                ]
            )

        columns = [
            "Time",
            "ID",
            "Symbol",
            "Side",
            "Type",
            "Qty",
            "Fill Price",
            "Status",
        ]
        output_data(
            f"{status} Orders",
            columns,
            rows,
            output_format=output_format,
            export_path=export,
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


@trading.command()
@click.argument("target_weights_path", type=click.Path(exists=True))
@click.option(
    "--allow-short",
    is_flag=True,
    help="Allow short selling if target weight is negative or requires shorting",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=True,
    help="Simulate orders without executing (Default: True). Use --execute to run.",
)
@click.option(
    "--execute", is_flag=True, help="Execute orders (removes dry-run protection)"
)
@click.option("--force", is_flag=True, help="Force execution even if market is closed")
@click.option(
    "--order-type",
    type=click.Choice(["market", "limit"], case_sensitive=False),
    default="market",
    help="Order type: market (immediate) or limit (at current price)",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "ioc", "fok"], case_sensitive=False),
    default="day",
    help="Time in Force: day, gtc (good-til-cancelled), ioc, fok",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt (required for execution without prompts)",
)
def rebalance(
    target_weights_path: str,
    allow_short: bool,
    dry_run: bool,
    execute: bool,
    force: bool,
    order_type: str,
    tif: str,
    yes: bool,
) -> None:
    """Rebalance portfolio based on target weights JSON file.

    TARGET_WEIGHTS_PATH: Path to JSON file containing target weights (e.g. {"AAPL": 0.5, "CASH": 0.5})
    """
    import json
    from alpaca_cli.cli.utils import calculate_rebalancing_orders

    # Handle dry_run/execute logic logic
    # If execute is True, dry_run is False.
    # If execute is False, dry_run defaults to True (per option default)
    if execute:
        dry_run = False

    logger.info(f"Rebalancing portfolio (Dry Run: {dry_run})...")

    # 1. Load weights
    try:
        with open(target_weights_path, "r") as f:
            target_weights = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load weights file: {e}")
        return

    # Validate inputs
    if not isinstance(target_weights, dict):
        logger.error("Invalid weights format. Must be a JSON dictionary.")
        return

    # check cash in keys - if missing, calculate remaining weight as cash
    if "CASH" not in target_weights:
        asset_weight_sum = sum(target_weights.values())
        remaining_weight = 1.0 - asset_weight_sum
        target_weights["CASH"] = remaining_weight
        logger.info(
            f"'CASH' not found in weights. Calculated remaining weight as CASH: {remaining_weight:.2%}"
        )

    # Check sum - strict validation (error, not warning)
    total_weight = sum(target_weights.values())
    if not (0.99 <= total_weight <= 1.01):
        logger.error(
            f"Total target weight is {total_weight:.4f}. Must be between 0.99 and 1.01. Aborting."
        )
        return

    client = get_trading_client()

    # 2. Check Market Status
    if not force and not dry_run:
        try:
            clock = client.get_clock()
            if not clock.is_open:
                logger.error(
                    "Market is closed. Use --force to override or wait for market open."
                )
                return
        except Exception as e:
            logger.error(f"Failed to fetch market clock: {e}")
            return

    # 3. Fetch Account and Positions
    try:
        account = client.get_account()
        positions = client.get_all_positions()
    except Exception as e:
        logger.error(f"Failed to fetch account/positions: {e}")
        return

    current_equity = float(account.equity)
    current_positions_map = {p.symbol: float(p.qty) for p in positions}

    # 4. Fetch Prices
    # We need prices for all symbols in targets AND current positions
    all_symbols = set(target_weights.keys()) | set(current_positions_map.keys())
    if "CASH" in all_symbols:
        all_symbols.remove("CASH")

    if not all_symbols:
        logger.info("No assets to rebalance.")
        return

    # 4a. Validate symbols are tradable (stocks only, crypto symbols contain '/')
    stock_symbols_to_validate = [s for s in all_symbols if "/" not in s]
    if stock_symbols_to_validate and not dry_run:
        try:
            invalid_symbols = []
            for sym in stock_symbols_to_validate:
                try:
                    asset = client.get_asset(sym)
                    if not asset.tradable:
                        invalid_symbols.append(f"{sym} (not tradable)")
                except Exception:
                    invalid_symbols.append(f"{sym} (not found)")

            if invalid_symbols:
                logger.error(f"Invalid symbols detected: {invalid_symbols}. Aborting.")
                return
            logger.info(
                f"Validated {len(stock_symbols_to_validate)} symbol(s) as tradable"
            )
        except Exception as e:
            logger.error(f"Failed to validate symbols: {e}")
            return

    # Separate crypto and stock symbols
    # Crypto symbols contain "/" (e.g., BTC/USD, ETH/USD)
    crypto_symbols = [s for s in all_symbols if "/" in s]
    stock_symbols = [s for s in all_symbols if "/" not in s]

    current_prices = {}

    # Fetch stock prices using singleton client
    if stock_symbols:
        try:
            stock_client = get_stock_data_client()
            req = StockLatestQuoteRequest(symbol_or_symbols=list(stock_symbols))
            quotes = stock_client.get_stock_latest_quote(req)
            for sym, quote in quotes.items():
                current_prices[sym] = (quote.bid_price + quote.ask_price) / 2
            logger.info(f"Fetched prices for {len(stock_symbols)} stock(s)")
        except Exception as e:
            logger.error(f"Failed to fetch stock prices: {e}")
            return

    # Fetch crypto prices using singleton client
    if crypto_symbols:
        try:
            crypto_client = get_crypto_data_client()
            req = CryptoLatestQuoteRequest(symbol_or_symbols=list(crypto_symbols))
            quotes = crypto_client.get_crypto_latest_quote(req)
            for sym, quote in quotes.items():
                current_prices[sym] = (quote.bid_price + quote.ask_price) / 2
            logger.info(f"Fetched prices for {len(crypto_symbols)} crypto(s)")
        except Exception as e:
            logger.error(f"Failed to fetch crypto prices: {e}")
            return

    # Merge prices from positions if data API fails for some?
    # Positions has `current_price` (15 min delayed? or realtime?).
    # Data API is better.

    # Check if we missed any prices - with fault-proof implementation, missing prices will raise ValueError
    missing_prices = [s for s in all_symbols if s not in current_prices]
    if missing_prices:
        logger.error(
            f"Could not fetch prices for: {missing_prices}. Cannot proceed with rebalance."
        )
        return

    # 5. Calculate Orders (fault-proof implementation raises ValueError on bad data)
    try:
        orders_to_place = calculate_rebalancing_orders(
            current_equity=current_equity,
            current_positions=current_positions_map,
            target_weights=target_weights,
            current_prices=current_prices,
            allow_short=allow_short,
        )
    except ValueError as e:
        logger.error(f"Rebalancing calculation failed: {e}")
        return

    if not orders_to_place:
        logger.info("Portfolio is balanced. No orders to place.")
        return

    # Sort orders: SELLS first, then BUYS (to free up cash before buying)
    sell_orders = [o for o in orders_to_place if o["side"] == "sell"]
    buy_orders = [o for o in orders_to_place if o["side"] == "buy"]
    sorted_orders = sell_orders + buy_orders

    # 6. Dry Run / Execute
    if dry_run:
        logger.info("Dry Run Mode. The following orders would be placed:")
        logger.info(f"Order Type: {order_type.upper()}, Time in Force: {tif.upper()}")
        logger.info("Order sequence: SELLS first, then BUYS")
        rows = []
        for o in sorted_orders:
            rows.append(
                [o["symbol"], o["side"].upper(), f"{o['qty']:.4f}", order_type.upper()]
            )

        print_table("Proposed Orders", ["Symbol", "Side", "Qty", "Type"], rows)
        return

    # 7. Confirmation prompt (if not --yes)
    if not yes:
        logger.info("The following orders will be executed:")
        rows = []
        for o in sorted_orders:
            rows.append(
                [o["symbol"], o["side"].upper(), f"{o['qty']:.4f}", order_type.upper()]
            )
        print_table("Orders to Execute", ["Symbol", "Side", "Qty", "Type"], rows)

        confirm = click.confirm("Do you want to proceed with execution?", default=False)
        if not confirm:
            logger.info("Execution cancelled by user.")
            return

    # 8. Execute orders (sells first, then buys)
    tif_enum = TimeInForce(tif.lower())

    for o in sorted_orders:
        try:
            if order_type.lower() == "market":
                req = MarketOrderRequest(
                    symbol=o["symbol"],
                    qty=o["qty"],
                    side=OrderSide.BUY if o["side"] == "buy" else OrderSide.SELL,
                    time_in_force=tif_enum,
                )
            else:
                # Limit order at current price
                limit_price = current_prices.get(o["symbol"])
                if not limit_price:
                    logger.error(f"No price for {o['symbol']}, skipping limit order.")
                    continue
                req = LimitOrderRequest(
                    symbol=o["symbol"],
                    qty=o["qty"],
                    side=OrderSide.BUY if o["side"] == "buy" else OrderSide.SELL,
                    time_in_force=tif_enum,
                    limit_price=limit_price,
                )
            submit_order(req)
        except Exception as e:
            logger.error(f"Failed to submit order for {o['symbol']}: {e}")
