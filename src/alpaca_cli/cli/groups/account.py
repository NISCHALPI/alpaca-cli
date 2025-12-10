import rich_click as click
from typing import List, Any, Optional
from datetime import datetime
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger
from alpaca.trading.requests import GetPortfolioHistoryRequest

logger = get_logger("account")


@click.group()
def account() -> None:
    """Account management commands."""
    pass


@account.command()
def status() -> None:
    """Show account status."""
    logger.info("Fetching account status...")
    client = get_trading_client()
    account = client.get_account()

    rows: List[List[Any]] = [
        ["ID", account.id],
        ["Account #", account.account_number],
        ["Status", account.status],
        ["Currency", account.currency],
        ["Pattern Day Trader", str(account.pattern_day_trader)],
        ["", ""],  # Spacer
        ["Cash", format_currency(account.cash)],
        ["Portfolio Value", format_currency(account.portfolio_value)],
        ["Equity", format_currency(account.equity)],
        ["Last Equity", format_currency(account.last_equity)],
        ["", ""],  # Spacer
        ["Buying Power", format_currency(account.buying_power)],
        ["Reg T Buying Power", format_currency(account.regt_buying_power)],
        ["Non-Marginable BP", format_currency(account.non_marginable_buying_power)],
        ["", ""],  # Spacer
        ["Initial Margin", format_currency(account.initial_margin)],
        ["Maintenance Margin", format_currency(account.maintenance_margin)],
        ["SMA", format_currency(account.sma)],
        ["", ""],  # Spacer
        ["Long Market Value", format_currency(account.long_market_value)],
        ["Short Market Value", format_currency(account.short_market_value)],
        ["Daytrade Count", str(account.daytrade_count)],
    ]

    print_table("Detailed Account Status", ["Metric", "Value"], rows)


@account.command()
def positions() -> None:
    """List open positions."""
    logger.info("Fetching open positions...")
    client = get_trading_client()
    positions = client.get_all_positions()

    if not positions:
        logger.info("No open positions.")
        return

    rows: List[List[Any]] = []
    for pos in positions:
        pl_percent = float(pos.unrealized_plpc) * 100
        pl_color = "green" if pl_percent >= 0 else "red"
        pl_str = f"[{pl_color}]{format_currency(pos.unrealized_pl)} ({pl_percent:.2f}%)[/{pl_color}]"

        rows.append(
            [
                pos.symbol,
                pos.qty,
                format_currency(pos.avg_entry_price),
                format_currency(pos.current_price),
                format_currency(pos.market_value),
                pl_str,
            ]
        )

    print_table(
        "Open Positions",
        ["Symbol", "Qty", "Avg Entry", "Current", "Market Value", "P/L"],
        rows,
    )


@account.command()
@click.option(
    "--period", default="1M", help="Duration of data (1D, 1W, 1M, 3M, 6M, 1A, all)"
)
@click.option(
    "--timeframe", default="1D", help="Resolution of data (1Min, 5Min, 15Min, 1H, 1D)"
)
@click.option("--date_end", help="End date (YYYY-MM-DD) [UTC]")
@click.option("--extended", is_flag=True, help="Include extended hours")
@click.option(
    "--start",
    default=None,
    help="Start datetime (RFC3339 format, e.g. 2024-01-01T09:00:00-05:00)",
)
@click.option(
    "--intraday-reporting",
    type=click.Choice(
        ["market_hours", "extended_hours", "continuous"], case_sensitive=False
    ),
    default=None,
    help="Timestamps to return for intraday data",
)
@click.option(
    "--pnl-reset",
    type=click.Choice(["per_day", "no_reset"], case_sensitive=False),
    default=None,
    help="Baseline for P/L calculation in intraday queries",
)
def history(
    period: str,
    timeframe: str,
    date_end: str,
    extended: bool,
    start: Optional[str],
    intraday_reporting: Optional[str],
    pnl_reset: Optional[str],
) -> None:
    """Show portfolio history with advanced options."""
    logger.info(f"Fetching portfolio history ({period}, {timeframe})...")
    client = get_trading_client()

    date_end_dt = None
    if date_end:
        try:
            date_end_dt = datetime.strptime(date_end, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD.")
            return

    # Parse start datetime if provided
    start_dt = None
    if start:
        try:
            start_dt = datetime.fromisoformat(start)
        except ValueError:
            logger.error(
                "Invalid start datetime format. Use RFC3339 (e.g. 2024-01-01T09:00:00-05:00)"
            )
            return

    req = GetPortfolioHistoryRequest(
        period=period,
        timeframe=timeframe,
        date_end=date_end_dt,
        extended_hours=extended,
        start=start_dt,
        intraday_reporting=intraday_reporting,
        pnl_reset=pnl_reset,
    )

    try:
        # returns PortfolioHistory object
        history = client.get_portfolio_history(req)
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        return

    if not history.timestamp:
        logger.info("No history data found.")
        return

    rows = []
    # history.timestamp and history.equity are lists
    for i in range(len(history.timestamp)):
        ts = history.timestamp[i]
        eq = history.equity[i]
        pnl = history.profit_loss[i]
        pnl_pct = (
            history.profit_loss_pct[i] * 100
            if history.profit_loss_pct[i] is not None
            else 0.0
        )

        # Determine color for PnL
        color = "green" if (pnl or 0) >= 0 else "red"

        rows.append(
            [
                datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
                format_currency(eq) if eq is not None else "-",
                (
                    f"[{color}]{format_currency(pnl)}[/{color}]"
                    if pnl is not None
                    else "-"
                ),
                f"[{color}]{pnl_pct:.2f}%[/{color}]" if pnl_pct is not None else "-",
            ]
        )

    # Reverse to show newest first? Or oldest first? Usually charts are left-right (old-new).
    # But for a table list, usually newest at top is better or bottom.
    # Let's keep API order (which is usually chronological) but maybe limit if too long?
    # Or just print all.

    print_table("Portfolio History", ["Time", "Equity", "P/L ($)", "P/L (%)"], rows)


@account.command()
def weights() -> None:
    """Show portfolio weights."""
    logger.info("Fetching portfolio weights...")
    client = get_trading_client()

    try:
        account = client.get_account()
        positions = client.get_all_positions()
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return

    total_equity = float(account.equity)
    if total_equity == 0:
        logger.warning("Account equity is zero.")
        return

    rows: List[List[Any]] = []

    # Calculate weights for positions
    for pos in positions:
        market_value = float(pos.market_value)
        weight = (market_value / total_equity) * 100

        # Color coding for weight
        # Long positions are positive weight, short are negative in terms of exposure,
        # but usually weights are presented as % of equity allocated.
        # Short market value is negative in API response? Let's check or assume positive magnitude.
        # In Alpaca API, market_value is positive even for shorts, but side is 'short'.
        # However, for weight distribution, we might want to show direction.
        # But 'market_value' field string usually parses to positive float.
        # Let's check side.

        is_short = pos.side == "short"
        if is_short:
            # If short, maybe we want to show negative weight or just indicate short?
            # Standard convention: Long +%, Short -%
            weight = -weight

        weight_color = "green" if weight >= 0 else "red"

        rows.append(
            [
                pos.symbol,
                pos.side.upper(),
                pos.qty,
                format_currency(pos.current_price),
                format_currency(pos.market_value),
                f"[{weight_color}]{weight:.2f}%[/{weight_color}]",
            ]
        )

    # Calculate cash weight
    cash = float(account.cash)
    cash_weight = (cash / total_equity) * 100
    rows.append(
        [
            "CASH",
            "-",
            "-",
            "-",
            format_currency(cash),
            f"[bold blue]{cash_weight:.2f}%[/bold blue]",
        ]
    )

    # Sort by weight (descending absolute value maybe? or just descending)
    # Let's sort by weight descending
    rows.sort(key=lambda x: float(x[5].split("]")[1].split("%")[0]), reverse=True)

    print_table(
        f"Portfolio Weights (Total Equity: {format_currency(total_equity)})",
        ["Symbol", "Side", "Qty", "Price", "Value", "Weight"],
        rows,
    )


# --- CLOSE POSITION ---
@account.command()
@click.argument("symbol", required=False)
@click.option("--all", "close_all", is_flag=True, help="Close ALL open positions")
@click.option("--qty", type=float, help="Partial close: number of shares to sell")
@click.option("--percentage", type=float, help="Partial close: percentage of position (0-100)")
@click.option("--cancel-orders", is_flag=True, help="Cancel open orders before closing")
def close(
    symbol: Optional[str],
    close_all: bool,
    qty: Optional[float],
    percentage: Optional[float],
    cancel_orders: bool,
) -> None:
    """Close position(s).

    Examples:
        alpaca-cli account close AAPL          # Close entire AAPL position
        alpaca-cli account close AAPL --qty 10 # Sell 10 shares of AAPL
        alpaca-cli account close --all         # Close all positions
    """
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

    if not symbol:
        logger.error("Must specify SYMBOL or --all flag")
        return

    logger.info(f"Closing position for {symbol.upper()}...")

    try:
        req = None
        if qty:
            req = ClosePositionRequest(qty=str(qty))
        elif percentage:
            req = ClosePositionRequest(percentage=str(percentage / 100))

        order = client.close_position(symbol.upper(), close_options=req)
        logger.info(f"Position close order submitted: {order.id}")
        logger.info(f"Side: {order.side.name}, Qty: {order.qty}, Status: {order.status.name}")
    except Exception as e:
        logger.error(f"Failed to close position: {e}")



# --- ACCOUNT CONFIG ---
@account.command("config")
@click.option("--dtbp-check", type=click.Choice(["both", "entry", "exit"]), help="Day trade buying power check")
@click.option("--trade-confirm", type=click.Choice(["all", "none"]), help="Trade confirmation emails")
@click.option("--suspend-trade/--resume-trade", default=None, help="Suspend/resume trading")
@click.option("--shorting/--no-shorting", default=None, help="Enable/disable shorting")
@click.option("--fractional/--no-fractional", default=None, help="Enable/disable fractional trading")
def config(
    dtbp_check: Optional[str],
    trade_confirm: Optional[str],
    suspend_trade: Optional[bool],
    shorting: Optional[bool],
    fractional: Optional[bool],
) -> None:
    """Get or update account configuration."""
    client = get_trading_client()

    # If no options provided, show current config
    if all(x is None for x in [dtbp_check, trade_confirm, suspend_trade, shorting, fractional]):
        logger.info("Fetching account configuration...")
        try:
            cfg = client.get_account_configurations()
            rows = [
                ["DTBP Check", cfg.dtbp_check.value if cfg.dtbp_check else "-"],
                ["Trade Confirm Email", cfg.trade_confirm_email.value if cfg.trade_confirm_email else "-"],
                ["Suspend Trade", str(cfg.suspend_trade)],
                ["No Shorting", str(cfg.no_shorting)],
                ["Fractional Trading", str(cfg.fractional_trading)],
                ["Max Margin Multiplier", str(cfg.max_margin_multiplier)],
                ["PDT Check", cfg.pdt_check.value if cfg.pdt_check else "-"],
                ["PTP No Exception", str(cfg.ptp_no_exception_entry)],
            ]
            print_table("Account Configuration", ["Setting", "Value"], rows)
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
        return

    # Update config
    logger.info("Updating account configuration...")
    try:
        from alpaca.trading.requests import AccountConfigurationRequest

        req = AccountConfigurationRequest(
            dtbp_check=dtbp_check,
            trade_confirm_email=trade_confirm,
            suspend_trade=suspend_trade,
            no_shorting=not shorting if shorting is not None else None,
            fractional_trading=fractional,
        )
        cfg = client.set_account_configurations(req)
        logger.info("Account configuration updated successfully.")
        
        rows = [
            ["DTBP Check", cfg.dtbp_check.value if cfg.dtbp_check else "-"],
            ["Suspend Trade", str(cfg.suspend_trade)],
            ["No Shorting", str(cfg.no_shorting)],
            ["Fractional Trading", str(cfg.fractional_trading)],
        ]
        print_table("Updated Configuration", ["Setting", "Value"], rows)
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
