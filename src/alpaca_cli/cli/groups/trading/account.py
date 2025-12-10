"""Account commands - Get Account Details, Account Configuration, Account Activities."""

import rich_click as click
from typing import List, Any, Optional
from datetime import datetime
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger
from alpaca.trading.requests import GetPortfolioHistoryRequest

logger = get_logger("trading.account")


@click.group()
def account() -> None:
    """Account management (status, config, activities, history)."""
    pass


@account.command()
def status() -> None:
    """Get account details and status."""
    logger.info("Fetching account status...")
    client = get_trading_client()
    acct = client.get_account()

    rows: List[List[Any]] = [
        ["ID", acct.id],
        ["Account #", acct.account_number],
        ["Status", acct.status],
        ["Currency", acct.currency],
        ["Pattern Day Trader", str(acct.pattern_day_trader)],
        ["", ""],  # Spacer
        ["Cash", format_currency(acct.cash)],
        ["Portfolio Value", format_currency(acct.portfolio_value)],
        ["Equity", format_currency(acct.equity)],
        ["Last Equity", format_currency(acct.last_equity)],
        ["", ""],  # Spacer
        ["Buying Power", format_currency(acct.buying_power)],
        ["Reg T Buying Power", format_currency(acct.regt_buying_power)],
        ["Non-Marginable BP", format_currency(acct.non_marginable_buying_power)],
        ["", ""],  # Spacer
        ["Initial Margin", format_currency(acct.initial_margin)],
        ["Maintenance Margin", format_currency(acct.maintenance_margin)],
        ["SMA", format_currency(acct.sma)],
        ["", ""],  # Spacer
        ["Long Market Value", format_currency(acct.long_market_value)],
        ["Short Market Value", format_currency(acct.short_market_value)],
        ["Daytrade Count", str(acct.daytrade_count)],
    ]

    print_table("Account Details", ["Metric", "Value"], rows)


@account.command("config")
@click.option(
    "--dtbp-check",
    type=click.Choice(["both", "entry", "exit"]),
    default=None,
    help="[Optional] Day trade buying power check. Choices: both, entry, exit",
)
@click.option(
    "--trade-confirm",
    type=click.Choice(["all", "none"]),
    default=None,
    help="[Optional] Trade confirmation email setting. Choices: all, none",
)
@click.option(
    "--suspend-trade/--resume-trade",
    default=None,
    help="[Optional] Suspend or resume trading on the account",
)
@click.option(
    "--shorting/--no-shorting",
    default=None,
    help="[Optional] Enable or disable short selling",
)
@click.option(
    "--fractional/--no-fractional",
    default=None,
    help="[Optional] Enable or disable fractional share trading",
)
@click.option(
    "--max-margin-multiplier",
    type=float,
    default=None,
    help="[Optional] Maximum margin multiplier. Choices: 1, 2, or 4",
)
@click.option(
    "--pdt-check",
    type=click.Choice(["entry", "exit", "both"]),
    default=None,
    help="[Optional] Pattern day trader check setting. Choices: entry, exit, both",
)
def config(
    dtbp_check: Optional[str],
    trade_confirm: Optional[str],
    suspend_trade: Optional[bool],
    shorting: Optional[bool],
    fractional: Optional[bool],
    max_margin_multiplier: Optional[float],
    pdt_check: Optional[str],
) -> None:
    """Get or update account configuration."""
    client = get_trading_client()

    # If no options provided, show current config
    if all(
        x is None
        for x in [
            dtbp_check,
            trade_confirm,
            suspend_trade,
            shorting,
            fractional,
            max_margin_multiplier,
            pdt_check,
        ]
    ):
        logger.info("Fetching account configuration...")
        try:
            cfg = client.get_account_configurations()
            rows = [
                ["DTBP Check", cfg.dtbp_check.value if cfg.dtbp_check else "-"],
                [
                    "Trade Confirm Email",
                    cfg.trade_confirm_email.value if cfg.trade_confirm_email else "-",
                ],
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
            max_margin_multiplier=(
                str(int(max_margin_multiplier)) if max_margin_multiplier else None
            ),
            pdt_check=pdt_check,
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


@account.command("history")
@click.option(
    "--period",
    type=str,
    default="1M",
    help="[Optional] Duration of data. Choices: 1D, 1W, 1M, 3M, 6M, 1A, all. Default: 1M",
)
@click.option(
    "--timeframe",
    type=str,
    default="1D",
    help="[Optional] Resolution of data. Choices: 1Min, 5Min, 15Min, 1H, 1D. Default: 1D",
)
@click.option(
    "--date-end",
    type=str,
    default=None,
    help="[Optional] End date in YYYY-MM-DD format (UTC)",
)
@click.option(
    "--extended/--no-extended",
    default=False,
    help="[Optional] Include extended trading hours data. Default: --no-extended",
)
@click.option(
    "--start",
    type=str,
    default=None,
    help="[Optional] Start datetime in RFC3339 format (e.g., 2024-01-01T09:00:00-05:00)",
)
@click.option(
    "--intraday-reporting",
    type=click.Choice(["market_hours", "extended_hours", "continuous"]),
    default=None,
    help="[Optional] Timestamps to return for intraday data. Choices: market_hours, extended_hours, continuous",
)
@click.option(
    "--pnl-reset",
    type=click.Choice(["per_day", "no_reset"]),
    default=None,
    help="[Optional] Baseline for P/L calculation. Choices: per_day, no_reset",
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
    """Get portfolio history."""
    client = get_trading_client()
    logger.info(f"Fetching portfolio history ({period}, {timeframe})...")

    date_end_dt = None
    if date_end:
        try:
            date_end_dt = datetime.strptime(date_end, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD.")
            return

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
        hist = client.get_portfolio_history(req)
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        return

    if not hist.timestamp:
        logger.info("No history data found.")
        return

    rows = []
    for i in range(len(hist.timestamp)):
        ts = hist.timestamp[i]
        eq = hist.equity[i]
        pnl = hist.profit_loss[i]
        pnl_pct = (
            hist.profit_loss_pct[i] * 100
            if hist.profit_loss_pct[i] is not None
            else 0.0
        )
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

    print_table("Portfolio History", ["Time", "Equity", "P/L ($)", "P/L (%)"], rows)
