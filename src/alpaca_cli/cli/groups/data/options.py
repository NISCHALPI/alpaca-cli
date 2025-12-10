"""Options market data commands - bars, trades, latest, snapshot, chain, exchanges."""

import rich_click as click
from typing import Optional
from datetime import datetime, timedelta, timezone
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import (
    OptionBarsRequest,
    OptionTradesRequest,
    OptionLatestQuoteRequest,
    OptionLatestTradeRequest,
    OptionSnapshotRequest,
    OptionChainRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.common.enums import Sort
from alpaca_cli.core.config import config
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger

logger = get_logger("data.options")


def get_timeframe(tf_str: str) -> TimeFrame:
    return {
        "1Min": TimeFrame.Minute,
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day,
        "1Week": TimeFrame.Week,
        "1Month": TimeFrame.Month,
    }.get(tf_str, TimeFrame.Day)


@click.group()
def options() -> None:
    """Options market data (bars, trades, latest, snapshot, chain)."""
    pass


@options.command("bars")
@click.argument("symbols")
@click.option("--timeframe", "-t", default="1Day", help="Timeframe (1Min, 1Hour, 1Day)")
@click.option("--start", help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
@click.option("--limit", default=100, help="Number of bars")
@click.option("--sort", type=click.Choice(["asc", "desc"]))
def option_bars(symbols, timeframe, start, end, limit, sort):
    """Get historical option bars (OHLCV)."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching option bars for {symbol_list}...")

    client = OptionHistoricalDataClient(config.API_KEY, config.API_SECRET)

    end_dt = (
        datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end
        else datetime.now(timezone.utc)
    )
    start_dt = (
        datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if start
        else end_dt - timedelta(days=30)
    )

    try:
        req = OptionBarsRequest(
            symbol_or_symbols=symbol_list,
            timeframe=get_timeframe(timeframe),
            start=start_dt,
            end=end_dt,
            limit=limit,
            sort=Sort.ASC if sort == "asc" else Sort.DESC if sort else None,
        )
        bars = client.get_option_bars(req)

        if not bars.data:
            logger.info("No data found.")
            return

        for sym in symbol_list:
            if sym not in bars.data:
                continue
            rows = [
                [
                    b.timestamp.strftime("%Y-%m-%d %H:%M"),
                    format_currency(b.open),
                    format_currency(b.high),
                    format_currency(b.low),
                    format_currency(b.close),
                    str(b.volume),
                ]
                for b in bars[sym]
            ]
            print_table(
                f"{sym} Bars", ["Time", "Open", "High", "Low", "Close", "Volume"], rows
            )
    except Exception as e:
        logger.error(f"Failed to fetch bars: {e}")


@options.command("trades")
@click.argument("symbols")
@click.option("--start", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
@click.option("--limit", default=100, help="Number of trades")
@click.option("--sort", type=click.Choice(["asc", "desc"]))
def option_trades(symbols, start, end, limit, sort):
    """Get historical option trades."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching option trades for {symbol_list}...")

    client = OptionHistoricalDataClient(config.API_KEY, config.API_SECRET)

    start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = (
        datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc) if end else None
    )

    try:
        req = OptionTradesRequest(
            symbol_or_symbols=symbol_list,
            start=start_dt,
            end=end_dt,
            limit=limit,
            sort=Sort.ASC if sort == "asc" else Sort.DESC if sort else None,
        )
        trades = client.get_option_trades(req)

        if not trades.data:
            logger.info("No data found.")
            return

        for sym in symbol_list:
            if sym not in trades.data:
                continue
            rows = [
                [
                    t.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    format_currency(t.price),
                    str(t.size),
                    t.exchange or "-",
                ]
                for t in list(trades[sym])[:50]
            ]
            print_table(f"{sym} Trades", ["Time", "Price", "Size", "Exchange"], rows)
    except Exception as e:
        logger.error(f"Failed to fetch trades: {e}")


@options.command("latest")
@click.argument("symbols")
@click.option(
    "--type", "data_type", type=click.Choice(["quote", "trade", "both"]), default="both"
)
def option_latest(symbols, data_type):
    """Get latest option quote and/or trade."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching latest option data for {symbol_list}...")

    client = OptionHistoricalDataClient(config.API_KEY, config.API_SECRET)

    try:
        for sym in symbol_list:
            rows = []

            if data_type in ["quote", "both"]:
                quotes = client.get_option_latest_quote(
                    OptionLatestQuoteRequest(symbol_or_symbols=sym)
                )
                if sym in quotes:
                    q = quotes[sym]
                    rows.append(
                        ["Bid", f"{format_currency(q.bid_price)} x {q.bid_size}"]
                    )
                    rows.append(
                        ["Ask", f"{format_currency(q.ask_price)} x {q.ask_size}"]
                    )

            if data_type in ["trade", "both"]:
                trades = client.get_option_latest_trade(
                    OptionLatestTradeRequest(symbol_or_symbols=sym)
                )
                if sym in trades:
                    t = trades[sym]
                    rows.append(
                        ["Last Trade", f"{format_currency(t.price)} x {t.size}"]
                    )
                    rows.append(
                        [
                            "Trade Time",
                            t.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )

            if rows:
                print_table(f"{sym} Latest", ["Metric", "Value"], rows)
    except Exception as e:
        logger.error(f"Failed to fetch latest data: {e}")


@options.command("snapshot")
@click.argument("symbols")
def option_snapshot(symbols):
    """Get option snapshot with Greeks and implied volatility."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching option snapshots for {symbol_list}...")

    client = OptionHistoricalDataClient(config.API_KEY, config.API_SECRET)

    try:
        snapshots = client.get_option_snapshot(
            OptionSnapshotRequest(symbol_or_symbols=symbol_list)
        )

        for sym in symbol_list:
            if sym not in snapshots:
                continue
            snap = snapshots[sym]
            rows = []

            if snap.latest_quote:
                rows.append(
                    [
                        "Bid",
                        f"{format_currency(snap.latest_quote.bid_price)} x {snap.latest_quote.bid_size}",
                    ]
                )
                rows.append(
                    [
                        "Ask",
                        f"{format_currency(snap.latest_quote.ask_price)} x {snap.latest_quote.ask_size}",
                    ]
                )

            if snap.latest_trade:
                rows.append(
                    [
                        "Last Trade",
                        f"{format_currency(snap.latest_trade.price)} x {snap.latest_trade.size}",
                    ]
                )

            # Greeks
            if hasattr(snap, "greeks") and snap.greeks:
                rows.append(["", ""])  # Spacer
                rows.append(
                    ["Delta", f"{snap.greeks.delta:.4f}" if snap.greeks.delta else "-"]
                )
                rows.append(
                    ["Gamma", f"{snap.greeks.gamma:.4f}" if snap.greeks.gamma else "-"]
                )
                rows.append(
                    ["Theta", f"{snap.greeks.theta:.4f}" if snap.greeks.theta else "-"]
                )
                rows.append(
                    ["Vega", f"{snap.greeks.vega:.4f}" if snap.greeks.vega else "-"]
                )
                rows.append(
                    ["Rho", f"{snap.greeks.rho:.4f}" if snap.greeks.rho else "-"]
                )

            if hasattr(snap, "implied_volatility") and snap.implied_volatility:
                rows.append(["Implied Volatility", f"{snap.implied_volatility:.2%}"])

            print_table(f"{sym} Snapshot", ["Metric", "Value"], rows)
    except Exception as e:
        logger.error(f"Failed to fetch snapshot: {e}")


@options.command("chain")
@click.argument("underlying_symbol")
@click.option("--expiry", help="Expiration date filter (YYYY-MM-DD)")
@click.option(
    "--type", "option_type", type=click.Choice(["call", "put"]), help="Option type"
)
@click.option("--strike-from", type=float, help="Strike price range start")
@click.option("--strike-to", type=float, help="Strike price range end")
def option_chain(underlying_symbol, expiry, option_type, strike_from, strike_to):
    """Get full option chain for an underlying symbol."""
    config.validate()
    logger.info(f"Fetching option chain for {underlying_symbol.upper()}...")

    client = OptionHistoricalDataClient(config.API_KEY, config.API_SECRET)

    try:
        expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date() if expiry else None

        req = OptionChainRequest(
            underlying_symbol=underlying_symbol.upper(),
            expiration_date=expiry_date,
            type=option_type.lower() if option_type else None,
            strike_price_gte=strike_from,
            strike_price_lte=strike_to,
        )

        chain = client.get_option_chain(req)

        if not chain:
            logger.info("No chain data found.")
            return

        rows = []
        for symbol, snap in list(chain.items())[:50]:  # Limit display
            row = [symbol]

            if snap.latest_quote:
                row.extend(
                    [
                        format_currency(snap.latest_quote.bid_price),
                        format_currency(snap.latest_quote.ask_price),
                    ]
                )
            else:
                row.extend(["-", "-"])

            if snap.latest_trade:
                row.append(format_currency(snap.latest_trade.price))
            else:
                row.append("-")

            if hasattr(snap, "greeks") and snap.greeks:
                row.append(f"{snap.greeks.delta:.3f}" if snap.greeks.delta else "-")
            else:
                row.append("-")

            if hasattr(snap, "implied_volatility") and snap.implied_volatility:
                row.append(f"{snap.implied_volatility:.1%}")
            else:
                row.append("-")

            rows.append(row)

        print_table(
            f"Option Chain: {underlying_symbol.upper()}",
            ["Symbol", "Bid", "Ask", "Last", "Delta", "IV"],
            rows,
        )

        if len(chain) > 50:
            logger.info(f"Showing 50 of {len(chain)} contracts. Use filters to narrow.")
    except Exception as e:
        logger.error(f"Failed to fetch chain: {e}")


@options.command("exchanges")
def option_exchanges():
    """Get option exchange code mappings."""
    config.validate()
    logger.info("Fetching option exchange codes...")

    client = OptionHistoricalDataClient(config.API_KEY, config.API_SECRET)

    try:
        exchanges = client.get_option_exchange_codes()

        if not exchanges:
            logger.info("No exchange data found.")
            return

        rows = [[code, name] for code, name in exchanges.items()]
        print_table("Option Exchanges", ["Code", "Name"], rows)
    except Exception as e:
        logger.error(f"Failed to fetch exchanges: {e}")
