import rich_click as click
from typing import List, Any
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
@click.option("--date_end", help="End date (YYYY-MM-DD)")
@click.option("--extended", is_flag=True, help="Include extended hours")
def history(period: str, timeframe: str, date_end: str, extended: bool) -> None:
    """Show portfolio history."""
    logger.info(f"Fetching portfolio history ({period}, {timeframe})...")
    client = get_trading_client()

    date_end_dt = None
    if date_end:
        try:
            date_end_dt = datetime.strptime(date_end, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD.")
            return

    req = GetPortfolioHistoryRequest(
        period=period,
        timeframe=timeframe,
        date_end=date_end_dt,
        extended_hours=extended,
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
