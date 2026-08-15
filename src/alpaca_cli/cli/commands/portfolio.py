import rich_click as click
import json
import time
from typing import Optional
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, OrderClass
from alpaca.trading.requests import LimitOrderRequest
from alpaca_cli.api.client import get_trading_client, get_stock_data_client, get_crypto_data_client
from alpaca_cli.services.portfolio import get_stock_latest_price_with_fallback, get_crypto_latest_price_with_fallback
from alpaca_cli.cli.formatters import print_table, format_currency
from alpaca_cli.core.logger import get_logger
from alpaca_cli.services.orders import _build_bracket_params
from alpaca_cli.cli.commands.trading.orders import create_market_order, submit_order, create_limit_order, create_trailing_stop_order

logger = get_logger("portfolio")

@click.group("portfolio")
def portfolio() -> None:
    """Manage portfolio-level bulk orders."""
    pass


@portfolio.command("rebalance")
@click.argument("target_weights_path", type=click.Path(exists=True))
@click.option(
    "--dry-run/--execute",
    default=True,
    help="[Optional] Simulate orders without executing. Default: --dry-run",
)
@click.option(
    "--force",
    is_flag=True,
    help="[Optional] Force execution even if market is closed",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, ioc, fok. Default: day",
)
@click.option(
    "--timeout",
    type=int,
    default=60,
    help="[Optional] Timeout in seconds to wait for sell orders. Default: 60",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="[Optional] Skip confirmation prompt",
)
@click.option(
    "--allow-short",
    is_flag=True,
    help="[Optional] Allow negative weights for short positions",
)
def rebalance(
    target_weights_path: str,
    dry_run: bool,
    force: bool,
    tif: str,
    timeout: int,
    yes: bool,
    allow_short: bool,
) -> None:
    """Rebalance portfolio using NOTIONAL market orders with sell-first execution.

    This is the default rebalance command.

    TARGET_WEIGHTS_PATH: Path to JSON file with target weights, e.g. {"AAPL": 0.5, "CASH": 0.5}

    Use --allow-short to permit negative weights for intentional short positions.
    """

    logger.info(f"Rebalancing portfolio with notional orders (Dry Run: {dry_run})...")

    try:
        with open(target_weights_path, "r") as f:
            target_weights = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load weights file: {e}")
        return

    if not isinstance(target_weights, dict):
        logger.error("Invalid weights format. Must be a JSON dictionary.")
        return

    non_cash_weights = {k: v for k, v in target_weights.items() if k != "CASH"}
    non_cash_sum = sum(non_cash_weights.values())

    for sym, weight in non_cash_weights.items():
        if weight < 0 and not allow_short:
            logger.error(
                f"Invalid negative weight for {sym}: {weight}. "
                f"Use --allow-short to permit short positions."
            )
            return

    if non_cash_sum > 1.0 + 1e-9:
        logger.error(
            f"Total weight ({non_cash_sum:.2%}) exceeds 100%. "
            f"Please adjust your weights. Current weights:"
        )
        for sym, weight in non_cash_weights.items():
            logger.error(f"  {sym}: {weight:.2%}")
        return

    if "CASH" not in target_weights:
        target_weights["CASH"] = 1.0 - non_cash_sum
        logger.info(
            f"'CASH' not specified, calculated as: {target_weights['CASH']:.2%}"
        )

    total_weight = sum(target_weights.values())
    if not (0.99 <= total_weight <= 1.01):
        logger.error(
            f"Total weight is {total_weight:.4f}. Must be between 0.99 and 1.01."
        )
        return

    client = get_trading_client()

    if not force and not dry_run:
        try:
            clock = client.get_clock()
            if not clock.is_open:
                logger.error("Market is closed. Use --force to override.")
                return
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
            return

    try:
        account = client.get_account()
        positions = client.get_all_positions()
    except Exception as e:
        logger.error(f"Failed to fetch account: {e}")
        return

    current_equity = float(account.equity)
    current_positions = {p.symbol: float(p.qty) for p in positions}
    position_values = {p.symbol: float(p.market_value) for p in positions}

    all_symbols = set(target_weights.keys()) | set(current_positions.keys())
    all_symbols.discard("CASH")

    if not all_symbols:
        logger.info("No assets to rebalance.")
        return

    crypto_symbols = [s for s in all_symbols if "/" in s]
    stock_symbols = [s for s in all_symbols if "/" not in s]
    current_prices = {}

    if stock_symbols:
        try:
            stock_client = get_stock_data_client()
            stock_prices = get_stock_latest_price_with_fallback(
                list(stock_symbols), stock_client
            )
            current_prices.update(stock_prices)
        except Exception as e:
            logger.error(f"Failed to fetch stock prices: {e}")
            return

    if crypto_symbols:
        try:
            crypto_client = get_crypto_data_client()
            crypto_prices = get_crypto_latest_price_with_fallback(
                list(crypto_symbols), crypto_client
            )
            current_prices.update(crypto_prices)
        except Exception as e:
            logger.error(f"Failed to fetch crypto prices: {e}")
            return

    missing = [s for s in all_symbols if s not in current_prices]
    if missing:
        logger.error(f"Missing prices for: {missing}")
        return

    logger.info("Portfolio Analysis (Calculations for Reference):")

    value_rows = []
    calculated_orders = []

    for symbol in sorted(all_symbols):
        current_qty = current_positions.get(symbol, 0)
        price = current_prices.get(symbol, 0)
        current_value = position_values.get(symbol, current_qty * price)
        current_weight = current_value / current_equity if current_equity > 0 else 0

        target_weight = target_weights.get(symbol, 0)
        target_value = target_weight * current_equity
        diff_value = target_value - current_value

        value_rows.append(
            [
                symbol,
                f"{current_weight:.2%}",
                f"{target_weight:.2%}",
                format_currency(current_value),
                format_currency(target_value),
                format_currency(diff_value),
            ]
        )

        if abs(diff_value) >= 1.0:
            if diff_value < 0:
                # Cap sell notional at current position value to prevent unintended shorts
                current_value_abs = abs(current_value)
                sell_notional = abs(diff_value)
                if sell_notional > current_value_abs and not allow_short:
                    logger.warning(
                        f"[SHORT GUARD] {symbol}: Sell ${sell_notional:.2f} exceeds position value "
                        f"${current_value_abs:.2f}. Capping at position value."
                    )
                    sell_notional = current_value_abs
                if sell_notional >= 1.0:
                    label = "[SHORT] " if sell_notional > current_value_abs else ""
                    calculated_orders.append(
                        {
                            "symbol": symbol,
                            "side": "sell",
                            "notional": sell_notional,
                            "current_qty": current_qty,
                            "label": label,
                        }
                    )
            else:
                calculated_orders.append(
                    {
                        "symbol": symbol,
                        "side": "buy",
                        "notional": abs(diff_value),
                        "label": "",
                    }
                )

    cash_current_value = current_equity - sum(
        position_values.get(s, current_positions.get(s, 0) * current_prices.get(s, 0))
        for s in all_symbols
    )
    cash_current_weight = (
        cash_current_value / current_equity if current_equity > 0 else 0
    )
    cash_target_weight = target_weights.get("CASH", 0)
    cash_target_value = cash_target_weight * current_equity
    cash_diff = cash_target_value - cash_current_value

    value_rows.append(
        [
            "CASH",
            f"{cash_current_weight:.2%}",
            f"{cash_target_weight:.2%}",
            format_currency(cash_current_value),
            format_currency(cash_target_value),
            format_currency(cash_diff),
        ]
    )

    print_table(
        f"Market Value Breakdown (Equity: {format_currency(current_equity)})",
        ["Symbol", "Current %", "Target %", "Current Value", "Target Value", "Diff"],
        value_rows,
    )

    sell_orders = [o for o in calculated_orders if o["side"] == "sell"]
    buy_orders = [o for o in calculated_orders if o["side"] == "buy"]

    if not sell_orders and not buy_orders:
        logger.info("Portfolio is balanced. No orders needed.")
        return

    logger.info("Proposed Notional Orders:")
    order_rows = []
    for o in sell_orders + buy_orders:
        label = o.get("label", "")
        order_rows.append(
            [
                f"{label}{o['symbol']}",
                o["side"].upper(),
                format_currency(o["notional"]),
                "MARKET (notional)",
            ]
        )
    print_table("Proposed Orders", ["Symbol", "Side", "Notional", "Type"], order_rows)

    if dry_run:
        logger.info("Dry run complete. Use --execute to place orders.")
        return

    if not yes:
        if not click.confirm("Proceed with execution? (Sells first, then Buys)"):
            logger.info("Cancelled.")
            return

    execution_summary = []

    if sell_orders:
        logger.info(
            f"Phase 1/2: Executing SELL orders ({len(sell_orders)} order(s))..."
        )
        sell_order_ids = []

        for i, o in enumerate(sell_orders, 1):
            label = o.get("label", "")
            try:
                req = create_market_order(
                    symbol=o["symbol"],
                    side=OrderSide.SELL,
                    notional=round(o["notional"], 2),
                    tif=tif,
                )
                result = submit_order(req)
                if result:
                    sell_order_ids.append(result.id)
                    logger.info(
                        f"  ├── {label}{o['symbol']}: SELL {format_currency(o['notional'])} "
                        f"(order {i}/{len(sell_orders)}) → submitted"
                    )
                    execution_summary.append(
                        [f"{label}{o['symbol']}", "SELL", format_currency(o["notional"]), "SUBMITTED"]
                    )
                else:
                    logger.error(f"  ├── {label}{o['symbol']}: SELL failed (no order returned)")
                    execution_summary.append(
                        [f"{label}{o['symbol']}", "SELL", format_currency(o["notional"]), "FAILED"]
                    )
            except Exception as e:
                logger.error(f"  ├── {label}{o['symbol']}: SELL failed: {e}")
                execution_summary.append(
                    [f"{label}{o['symbol']}", "SELL", format_currency(o["notional"]), "ERROR"]
                )

        logger.info("  Waiting for sell orders to fill...")
        all_sells_filled = True
        for idx, order_id in enumerate(sell_order_ids):
            filled = _wait_for_order_completion(
                client, order_id, timeout_seconds=timeout
            )
            status = "✓ FILLED" if filled else "✗ INCOMPLETE"
            logger.info(f"  ├── Order {str(order_id)[:8]}...: {status}")
            if not filled:
                all_sells_filled = False

        if not all_sells_filled:
            logger.warning(
                "  └── Not all sell orders completed. Proceeding with buy orders anyway."
            )
        else:
            logger.info("  └── All sell orders filled successfully.")

    if buy_orders:
        logger.info(
            f"Phase 2/2: Executing BUY orders ({len(buy_orders)} order(s))..."
        )
        for i, o in enumerate(buy_orders, 1):
            try:
                req = create_market_order(
                    symbol=o["symbol"],
                    side=OrderSide.BUY,
                    notional=round(o["notional"], 2),
                    tif=tif,
                )
                result = submit_order(req)
                if result:
                    logger.info(
                        f"  ├── {o['symbol']}: BUY {format_currency(o['notional'])} "
                        f"(order {i}/{len(buy_orders)}) → submitted"
                    )
                    execution_summary.append(
                        [o["symbol"], "BUY", format_currency(o["notional"]), "SUBMITTED"]
                    )
                else:
                    logger.error(f"  ├── {o['symbol']}: BUY failed (no order returned)")
                    execution_summary.append(
                        [o["symbol"], "BUY", format_currency(o["notional"]), "FAILED"]
                    )
            except Exception as e:
                logger.error(f"  ├── {o['symbol']}: BUY failed: {e}")
                execution_summary.append(
                    [o["symbol"], "BUY", format_currency(o["notional"]), "ERROR"]
                )

    # Final execution summary
    if execution_summary:
        print_table(
            "Execution Summary",
            ["Symbol", "Side", "Notional", "Status"],
            execution_summary,
        )

    logger.info("Rebalancing complete.")


# --- ORDER WAITING HELPERS ---
def _wait_for_order_completion(
    client,
    order_id: str,
    timeout_seconds: int = 60,
    poll_interval: float = 1.0,
) -> bool:
    """
    Poll an order until it reaches a terminal state (filled, canceled, expired, rejected).

    Returns True if order was filled, False otherwise.
    """
    terminal_states = {
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
    }

    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            order = client.get_order_by_id(order_id)
            if order.status in terminal_states:
                if order.status == OrderStatus.FILLED:
                    logger.info(f"Order {order_id} filled successfully.")
                    return True
                else:
                    logger.warning(
                        f"Order {order_id} ended with status: {order.status}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Error polling order {order_id}: {e}")
        time.sleep(poll_interval)

    logger.error(f"Order {order_id} timed out after {timeout_seconds}s")
    return False


@portfolio.command("sell-notional")
@click.argument("amount", type=float)
@click.option(
    "--dry-run/--execute",
    default=True,
    help="[Optional] Simulate orders without executing. Default: --dry-run",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, ioc, fok. Default: day",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="[Optional] Skip confirmation prompt",
)
def sell_portfolio_notional(
    amount: float,
    dry_run: bool,
    tif: str,
    yes: bool,
) -> None:
    """Sell a notional amount across all holdings proportionally.

    AMOUNT: The total dollar amount to sell from the portfolio.
    """
    logger.info(f"Selling ${amount:.2f} of portfolio (Dry Run: {dry_run})...")

    if amount <= 0:
        logger.error("Amount must be greater than 0.")
        return

    client = get_trading_client()

    # Get account and positions
    try:
        positions = client.get_all_positions()
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return

    if not positions:
        logger.info("No positions to sell.")
        return

    # Calculate total market value of current equity positions
    current_positions = {p.symbol: float(p.market_value) for p in positions}
    total_market_value = sum(current_positions.values())

    if total_market_value == 0:
        logger.error("Total market value of positions is zero.")
        return

    if amount > total_market_value:
        logger.warning(
            f"Requested sell amount (${amount:.2f}) exceeds total market value of positions (${total_market_value:.2f})."
        )
        if not yes and not click.confirm(
            "Do you still want to proceed by selling the entire portfolio?"
        ):
            logger.info("Cancelled.")
            return
        amount = total_market_value

    orders_to_place = []
    for symbol, market_value in current_positions.items():
        weight = market_value / total_market_value
        sell_notional = amount * weight
        if sell_notional >= 1.0:  # Alpaca minimum notional order is usually $1
            orders_to_place.append(
                {
                    "symbol": symbol,
                    "notional": sell_notional,
                }
            )

    if not orders_to_place:
        logger.info(
            "Calculated sell amounts are too small to place orders (minimum $1 per position)."
        )
        return

    # Dry run display
    order_rows = []
    for o in orders_to_place:
        order_rows.append([o["symbol"], format_currency(o["notional"]), "MARKET"])

    print_table("Proposed Sell Orders", ["Symbol", "Notional", "Type"], order_rows)

    if dry_run:
        logger.info("Dry run complete. Use --execute to place orders.")
        return

    # Confirmation
    if not yes:
        if not click.confirm("Proceed with execution?"):
            logger.info("Cancelled.")
            return

    # Execution
    logger.info("Executing SELL orders...")
    for o in orders_to_place:
        try:
            req = create_market_order(
                symbol=o["symbol"],
                side=OrderSide.SELL,
                notional=round(o["notional"], 2),
                tif=tif,
            )
            submit_order(req)
        except Exception as e:
            logger.error(f"Failed to submit sell order for {o['symbol']}: {e}")

    logger.info("Sell portfolio notional complete.")


@portfolio.command("buy-notional")
@click.argument("amount", type=float)
@click.option(
    "--dry-run/--execute",
    default=True,
    help="[Optional] Simulate orders without executing. Default: --dry-run",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "ioc", "fok"]),
    default="day",
    help="[Optional] Time in force. Choices: day, gtc, ioc, fok. Default: day",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="[Optional] Skip confirmation prompt",
)
def buy_portfolio_notional(
    amount: float,
    dry_run: bool,
    tif: str,
    yes: bool,
) -> None:
    """Buy assets proportionally to your current portfolio weights with new cash.

    AMOUNT: The total dollar amount of new cash to deploy.
    """
    logger.info(f"Buying ${amount:.2f} of portfolio (Dry Run: {dry_run})...")

    if amount <= 0:
        logger.error("Amount must be greater than 0.")
        return

    client = get_trading_client()

    try:
        positions = client.get_all_positions()
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return

    if not positions:
        logger.error("No positions currently held. Cannot determine portfolio weights.")
        return

    # Calculate total market value of current equity positions
    current_positions = {p.symbol: float(p.market_value) for p in positions}
    total_market_value = sum(current_positions.values())

    if total_market_value == 0:
        logger.error("Total market value of positions is zero.")
        return

    orders_to_place = []
    for symbol, market_value in current_positions.items():
        weight = market_value / total_market_value
        buy_notional = amount * weight
        if buy_notional >= 1.0:  # Alpaca minimum notional order is usually $1
            orders_to_place.append(
                {
                    "symbol": symbol,
                    "notional": buy_notional,
                }
            )

    if not orders_to_place:
        logger.info(
            "Calculated buy amounts are too small to place orders (minimum $1 per position)."
        )
        return

    # Dry run display
    order_rows = []
    for o in orders_to_place:
        order_rows.append([o["symbol"], format_currency(o["notional"]), "MARKET"])

    print_table("Proposed Buy Orders", ["Symbol", "Notional", "Type"], order_rows)

    if dry_run:
        logger.info("Dry run complete. Use --execute to place orders.")
        return

    # Confirmation
    if not yes:
        if not click.confirm("Proceed with execution?"):
            logger.info("Cancelled.")
            return

    # Execution
    logger.info("Executing BUY orders...")
    for o in orders_to_place:
        try:
            req = create_market_order(
                symbol=o["symbol"],
                side=OrderSide.BUY,
                notional=round(o["notional"], 2),
                tif=tif,
            )
            submit_order(req)
        except Exception as e:
            logger.error(f"Failed to submit buy order for {o['symbol']}: {e}")

    logger.info("Buy portfolio notional complete.")


@portfolio.command("take-profit-all")
@click.argument("percentage", type=float)
@click.option(
    "--dry-run/--execute",
    default=True,
    help="[Optional] Simulate orders without executing. Default: --dry-run",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "ioc", "fok"]),
    default=None,
    help="[Optional] Time in force. Choices: day, gtc, ioc, fok. Default: gtc (day for fractional)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="[Optional] Skip confirmation prompt",
)
@click.option(
    "--include-short",
    is_flag=True,
    help="[Optional] Include short positions",
)
def take_profit_all(
    percentage: float,
    dry_run: bool,
    tif: Optional[str],
    yes: bool,
    include_short: bool,
) -> None:
    """Set take-profit limit orders for all open positions.

    PERCENTAGE: Percentage above current price to take profit (e.g., 5 for 5%).
    """
    if percentage <= 0:
        logger.error("Percentage must be greater than 0.")
        return

    logger.info(
        f"Setting take-profit for all positions at {percentage}% (Dry Run: {dry_run})..."
    )
    client = get_trading_client()

    try:
        positions = client.get_all_positions()
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return

    if not positions:
        logger.info("No open positions.")
        return

    orders_to_place = []
    for pos in positions:
        if pos.side.name != "LONG" and not include_short:
            continue

        current_price = float(pos.current_price)
        if pos.side.name == "LONG":
            limit_price = current_price * (1 + (percentage / 100))
            side = OrderSide.SELL
        else:
            limit_price = current_price * (1 - (percentage / 100))
            side = OrderSide.BUY

        orders_to_place.append(
            {
                "symbol": pos.symbol,
                "qty": abs(float(pos.qty)),
                "limit_price": limit_price,
                "current_price": current_price,
                "side": side,
            }
        )

    if not orders_to_place:
        logger.info("No valid positions to apply take-profit.")
        return

    order_rows = []
    for o in orders_to_place:
        order_rows.append(
            [
                o["symbol"],
                str(o["qty"]),
                format_currency(o["current_price"]),
                format_currency(o["limit_price"]),
            ]
        )

    print_table(
        "Proposed Take-Profit Orders",
        ["Symbol", "Qty", "Current Price", "Limit Price"],
        order_rows,
    )

    if dry_run:
        logger.info("Dry run complete. Use --execute to place orders.")
        return

    if not yes:
        if not click.confirm("Proceed with execution?"):
            logger.info("Cancelled.")
            return

    logger.info("Executing take-profit orders...")
    for o in orders_to_place:
        try:
            is_fractional = not float(o["qty"]).is_integer()
            order_tif = tif or ("day" if is_fractional else "gtc")
            req = create_limit_order(
                symbol=o["symbol"],
                side=o["side"],
                qty=o["qty"],
                limit_price=round(o["limit_price"], 2),
                tif=order_tif,
            )
            submit_order(req)
        except Exception as e:
            logger.error(f"Failed to submit take-profit for {o['symbol']}: {e}")

    logger.info("Take-profit all complete.")


@portfolio.command("trailing-stop-all")
@click.argument("percentage", type=float)
@click.option(
    "--dry-run/--execute",
    default=True,
    help="[Optional] Simulate orders without executing. Default: --dry-run",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "ioc", "fok"]),
    default=None,
    help="[Optional] Time in force. Choices: day, gtc, ioc, fok. Default: gtc (day for fractional)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="[Optional] Skip confirmation prompt",
)
@click.option(
    "--include-short",
    is_flag=True,
    help="[Optional] Include short positions",
)
def trailing_stop_all(
    percentage: float,
    dry_run: bool,
    tif: Optional[str],
    yes: bool,
    include_short: bool,
) -> None:
    """Set trailing stop orders for all open positions.

    PERCENTAGE: Trailing percentage for the stop loss (e.g., 5 for 5%).
    """
    if percentage <= 0:
        logger.error("Percentage must be greater than 0.")
        return

    logger.info(
        f"Setting trailing stop for all positions at {percentage}% (Dry Run: {dry_run})..."
    )
    client = get_trading_client()

    try:
        positions = client.get_all_positions()
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return

    if not positions:
        logger.info("No open positions.")
        return

    orders_to_place = []
    for pos in positions:
        if pos.side.name != "LONG" and not include_short:
            continue

        side = OrderSide.SELL if pos.side.name == "LONG" else OrderSide.BUY

        orders_to_place.append(
            {"symbol": pos.symbol, "qty": abs(float(pos.qty)), "trail_percent": percentage, "side": side}
        )

    if not orders_to_place:
        logger.info("No valid positions to apply trailing stops.")
        return

    order_rows = []
    for o in orders_to_place:
        order_rows.append([o["symbol"], str(o["qty"]), f"{o['trail_percent']}%"])

    print_table(
        "Proposed Trailing Stop Orders", ["Symbol", "Qty", "Trail Percent"], order_rows
    )

    if dry_run:
        logger.info("Dry run complete. Use --execute to place orders.")
        return

    if not yes:
        if not click.confirm("Proceed with execution?"):
            logger.info("Cancelled.")
            return

    logger.info("Executing trailing stop orders...")
    for o in orders_to_place:
        try:
            is_fractional = not float(o["qty"]).is_integer()
            order_tif = tif or ("day" if is_fractional else "gtc")
            req = create_trailing_stop_order(
                symbol=o["symbol"],
                side=o["side"],
                qty=o["qty"],
                trail_percent=o["trail_percent"],
                tif=order_tif,
            )
            submit_order(req)
        except Exception as e:
            logger.error(f"Failed to submit trailing stop for {o['symbol']}: {e}")

    logger.info("Trailing stop all complete.")


@portfolio.command("bracket-all")
@click.argument("take_profit_pct", type=float)
@click.argument("stop_loss_pct", type=float)
@click.option(
    "--stop-loss-limit",
    "stop_loss_limit_pct",
    type=float,
    default=None,
    help="[Optional] Stop loss limit percentage",
)
@click.option(
    "--tif",
    type=click.Choice(["day", "gtc", "ioc", "fok"]),
    default=None,
    help="[Optional] Time in force. Default: gtc (day for fractional)",
)
@click.option(
    "--dry-run/--execute",
    default=True,
    help="[Optional] Simulate orders without executing. Default: --dry-run",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="[Optional] Skip confirmation prompt",
)
@click.option(
    "--include-short",
    is_flag=True,
    help="[Optional] Include short positions",
)
def bracket_all(
    take_profit_pct: float,
    stop_loss_pct: float,
    stop_loss_limit_pct: Optional[float],
    tif: Optional[str],
    dry_run: bool,
    yes: bool,
    include_short: bool,
) -> None:
    """Set OCO bracket orders (take-profit & stop-loss) for all open positions.

    TAKE_PROFIT_PCT: Percentage above current price to take profit (e.g. 5 for 5%).
    STOP_LOSS_PCT: Percentage below current price to cut losses (e.g. 2 for 2%).
    """
    if take_profit_pct <= 0 or stop_loss_pct <= 0:
        logger.error("Percentages must be greater than 0.")
        return

    logger.info(
        f"Setting OCO brackets for all positions (TP: {take_profit_pct}%, SL: {stop_loss_pct}%) (Dry Run: {dry_run})..."
    )
    client = get_trading_client()

    try:
        positions = client.get_all_positions()
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return

    if not positions:
        logger.info("No open positions.")
        return

    orders_to_place = []
    for pos in positions:
        if pos.side.name != "LONG" and not include_short:
            continue

        current_price = float(pos.current_price)
        if pos.side.name == "LONG":
            tp_price = current_price * (1 + (take_profit_pct / 100))
            sl_price = current_price * (1 - (stop_loss_pct / 100))
            sl_limit_price = (
                current_price * (1 - (stop_loss_limit_pct / 100))
                if stop_loss_limit_pct
                else None
            )
            side = OrderSide.SELL
        else:
            tp_price = current_price * (1 - (take_profit_pct / 100))
            sl_price = current_price * (1 + (stop_loss_pct / 100))
            sl_limit_price = (
                current_price * (1 + (stop_loss_limit_pct / 100))
                if stop_loss_limit_pct
                else None
            )
            side = OrderSide.BUY

        orders_to_place.append(
            {
                "symbol": pos.symbol,
                "qty": abs(float(pos.qty)),
                "current_price": current_price,
                "take_profit_price": tp_price,
                "stop_loss_price": sl_price,
                "stop_loss_limit_price": sl_limit_price,
                "side": side,
            }
        )

    if not orders_to_place:
        logger.info("No valid positions to apply brackets.")
        return

    order_rows = []
    for o in orders_to_place:
        sl_str = format_currency(o["stop_loss_price"])
        if o["stop_loss_limit_price"]:
            sl_str += f" (Limit: {format_currency(o['stop_loss_limit_price'])})"

        order_rows.append(
            [
                o["symbol"],
                str(o["qty"]),
                format_currency(o["take_profit_price"]),
                sl_str,
            ]
        )

    print_table(
        "Proposed OCO Brackets",
        ["Symbol", "Qty", "Take Profit", "Stop Loss"],
        order_rows,
    )

    if dry_run:
        logger.info("Dry run complete. Use --execute to place orders.")
        return

    if not yes:
        if not click.confirm("Proceed with execution?"):
            logger.info("Cancelled.")
            return

    logger.info("Executing bracket orders...")
    for o in orders_to_place:
        try:
            is_fractional = not float(o["qty"]).is_integer()
            order_tif = tif or ("day" if is_fractional else "gtc")

            # Build bracket legs (take-profit + stop-loss)
            bracket_params = _build_bracket_params(
                take_profit=round(o["take_profit_price"], 2),
                stop_loss=round(o["stop_loss_price"], 2),
                stop_loss_limit=(
                    round(o["stop_loss_limit_price"], 2)
                    if o["stop_loss_limit_price"]
                    else None
                ),
            )

            # For exit-only OCO orders on existing positions, override to OCO
            # (not BRACKET, which is for entry orders with attached exit legs)
            bracket_params["order_class"] = OrderClass.OCO

            req = LimitOrderRequest(
                symbol=o["symbol"],
                side=o["side"],
                qty=o["qty"],
                time_in_force=TimeInForce(order_tif),
                limit_price=round(o["take_profit_price"], 2),
                **bracket_params,
            )
            submit_order(req)
        except Exception as e:
            logger.error(f"Failed to submit bracket for {o['symbol']}: {e}")

    logger.info("Bracket all complete.")


@portfolio.command("liquidate-all")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="[Optional] Skip confirmation prompt",
)
def liquidate_all(yes: bool) -> None:
    """Panic button: Cancels all open orders and liquidates all positions immediately."""
    logger.warning("LIQUIDATE ALL requested.")
    if not yes:
        if not click.confirm(
            "WARNING: This will cancel all open orders and sell ALL your positions immediately. Are you sure?"
        ):
            logger.info("Cancelled.")
            return

    client = get_trading_client()

    logger.info("Canceling all open orders and submitting close all positions...")
    try:
        responses = client.close_all_positions(cancel_orders=True)
        if not responses:
            logger.info("No positions to close.")
            return

        for resp in responses:
            if resp.status == 200:
                logger.info(f"Liquidated position: {resp.symbol}")
            else:
                logger.error(f"Failed to liquidate {resp.symbol}: {resp.body}")
    except Exception as e:
        logger.error(f"Failed to liquidate all positions: {e}")
