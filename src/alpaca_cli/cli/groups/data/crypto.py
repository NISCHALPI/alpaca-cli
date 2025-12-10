"""Crypto market data commands - bars, quotes, trades, latest, snapshot, orderbook, stream."""

import rich_click as click
import asyncio
from typing import Optional
from datetime import datetime, timedelta, timezone
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.live import CryptoDataStream
from alpaca.data.requests import (
    CryptoBarsRequest,
    CryptoQuoteRequest,
    CryptoTradesRequest,
    CryptoLatestQuoteRequest,
    CryptoLatestTradeRequest,
    CryptoLatestBarRequest,
    CryptoSnapshotRequest,
    CryptoLatestOrderbookRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import CryptoFeed
from alpaca.common.enums import Sort
from alpaca_cli.core.config import config
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger
from rich.live import Live
from rich.table import Table
from rich import box

logger = get_logger("data.crypto")


def get_timeframe(tf_str: str) -> TimeFrame:
    return {
        "1Min": TimeFrame.Minute,
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day,
        "1Week": TimeFrame.Week,
        "1Month": TimeFrame.Month,
    }.get(tf_str, TimeFrame.Day)


@click.group()
def crypto() -> None:
    """Crypto market data (bars, quotes, trades, latest, snapshot, orderbook, stream)."""
    pass


@crypto.command("bars")
@click.argument("symbols")
@click.option(
    "--timeframe",
    "-t",
    default="1Day",
    help="Timeframe (1Min, 1Hour, 1Day, 1Week, 1Month)",
)
@click.option("--start", help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
@click.option("--limit", default=100, help="Number of bars")
@click.option("--sort", type=click.Choice(["asc", "desc"]))
def crypto_bars(symbols, timeframe, start, end, limit, sort):
    """Get historical crypto bars (OHLCV)."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching {timeframe} crypto bars for {symbol_list}...")

    client = CryptoHistoricalDataClient(config.API_KEY, config.API_SECRET)

    end_dt = (
        datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end
        else datetime.now(timezone.utc)
    )
    start_dt = (
        datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if start
        else end_dt - timedelta(days=limit)
    )

    try:
        req = CryptoBarsRequest(
            symbol_or_symbols=symbol_list,
            timeframe=get_timeframe(timeframe),
            start=start_dt,
            end=end_dt,
            limit=limit,
            sort=Sort.ASC if sort == "asc" else Sort.DESC if sort else None,
        )
        bars = client.get_crypto_bars(req)

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
                    str(b.vwap) if b.vwap else "-",
                ]
                for b in bars[sym]
            ]
            print_table(
                f"{sym} Bars",
                ["Time", "Open", "High", "Low", "Close", "Volume", "VWAP"],
                rows,
            )
    except Exception as e:
        logger.error(f"Failed to fetch bars: {e}")


@crypto.command("quotes")
@click.argument("symbols")
@click.option("--start", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
@click.option("--limit", default=100, help="Number of quotes")
@click.option("--sort", type=click.Choice(["asc", "desc"]))
def crypto_quotes(symbols, start, end, limit, sort):
    """Get historical crypto quotes."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching crypto quotes for {symbol_list}...")

    client = CryptoHistoricalDataClient(config.API_KEY, config.API_SECRET)

    start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = (
        datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc) if end else None
    )

    try:
        req = CryptoQuoteRequest(
            symbol_or_symbols=symbol_list,
            start=start_dt,
            end=end_dt,
            limit=limit,
            sort=Sort.ASC if sort == "asc" else Sort.DESC if sort else None,
        )
        quotes = client.get_crypto_quotes(req)

        if not quotes.data:
            logger.info("No data found.")
            return

        for sym in symbol_list:
            if sym not in quotes.data:
                continue
            rows = [
                [
                    q.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    format_currency(q.bid_price),
                    str(q.bid_size),
                    format_currency(q.ask_price),
                    str(q.ask_size),
                ]
                for q in list(quotes[sym])[:50]
            ]
            print_table(
                f"{sym} Quotes", ["Time", "Bid", "Bid Size", "Ask", "Ask Size"], rows
            )
    except Exception as e:
        logger.error(f"Failed to fetch quotes: {e}")


@crypto.command("trades")
@click.argument("symbols")
@click.option("--start", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
@click.option("--limit", default=100, help="Number of trades")
@click.option("--sort", type=click.Choice(["asc", "desc"]))
def crypto_trades(symbols, start, end, limit, sort):
    """Get historical crypto trades."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching crypto trades for {symbol_list}...")

    client = CryptoHistoricalDataClient(config.API_KEY, config.API_SECRET)

    start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = (
        datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc) if end else None
    )

    try:
        req = CryptoTradesRequest(
            symbol_or_symbols=symbol_list,
            start=start_dt,
            end=end_dt,
            limit=limit,
            sort=Sort.ASC if sort == "asc" else Sort.DESC if sort else None,
        )
        trades = client.get_crypto_trades(req)

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
                    str(t.id) if hasattr(t, "id") else "-",
                ]
                for t in list(trades[sym])[:50]
            ]
            print_table(f"{sym} Trades", ["Time", "Price", "Size", "Trade ID"], rows)
    except Exception as e:
        logger.error(f"Failed to fetch trades: {e}")


@crypto.command("latest")
@click.argument("symbols")
def crypto_latest(symbols):
    """Get latest crypto quote, trade, and bar."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching latest crypto data for {symbol_list}...")

    client = CryptoHistoricalDataClient(config.API_KEY, config.API_SECRET)

    try:
        quotes = client.get_crypto_latest_quote(
            CryptoLatestQuoteRequest(symbol_or_symbols=symbol_list)
        )
        trades = client.get_crypto_latest_trade(
            CryptoLatestTradeRequest(symbol_or_symbols=symbol_list)
        )
        bars = client.get_crypto_latest_bar(
            CryptoLatestBarRequest(symbol_or_symbols=symbol_list)
        )

        for sym in symbol_list:
            rows = []
            if sym in quotes:
                q = quotes[sym]
                rows.append(["Bid", f"{format_currency(q.bid_price)} x {q.bid_size}"])
                rows.append(["Ask", f"{format_currency(q.ask_price)} x {q.ask_size}"])
            if sym in trades:
                t = trades[sym]
                rows.append(["Last Trade", f"{format_currency(t.price)} x {t.size}"])
                rows.append(
                    [
                        "Trade Time",
                        t.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
                    ]
                )
            if sym in bars:
                b = bars[sym]
                rows.append(["Latest Bar Close", format_currency(b.close)])
                rows.append(["Latest Bar Volume", str(b.volume)])
            print_table(f"{sym} Latest", ["Metric", "Value"], rows)
    except Exception as e:
        logger.error(f"Failed to fetch latest data: {e}")


@crypto.command("snapshot")
@click.argument("symbols")
def crypto_snapshot(symbols):
    """Get crypto snapshot (quote, trade, bar, prev close)."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching crypto snapshots for {symbol_list}...")

    client = CryptoHistoricalDataClient(config.API_KEY, config.API_SECRET)

    try:
        snapshots = client.get_crypto_snapshot(
            CryptoSnapshotRequest(symbol_or_symbols=symbol_list)
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
            if snap.minute_bar:
                rows.append(
                    ["Minute Bar Close", format_currency(snap.minute_bar.close)]
                )
            if snap.daily_bar:
                rows.append(["Daily Close", format_currency(snap.daily_bar.close)])
                rows.append(["Daily Volume", str(snap.daily_bar.volume)])
            if snap.previous_daily_bar:
                rows.append(
                    ["Prev Close", format_currency(snap.previous_daily_bar.close)]
                )
            print_table(f"{sym} Snapshot", ["Metric", "Value"], rows)
    except Exception as e:
        logger.error(f"Failed to fetch snapshot: {e}")


@crypto.command("orderbook")
@click.argument("symbols")
def crypto_orderbook(symbols):
    """Get crypto orderbook (bid/ask depth)."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching orderbook for {symbol_list}...")

    client = CryptoHistoricalDataClient(config.API_KEY, config.API_SECRET)

    try:
        result = client.get_crypto_latest_orderbook(
            CryptoLatestOrderbookRequest(symbol_or_symbols=symbol_list)
        )

        for sym in symbol_list:
            if sym not in result:
                continue
            ob = result[sym]
            bid_rows = [[format_currency(b.price), str(b.size)] for b in ob.bids[:10]]
            ask_rows = [[format_currency(a.price), str(a.size)] for a in ob.asks[:10]]
            print_table(f"{sym} Bids", ["Price", "Size"], bid_rows)
            print_table(f"{sym} Asks", ["Price", "Size"], ask_rows)
    except Exception as e:
        logger.error(f"Failed to get orderbook: {e}")


@crypto.command("stream")
@click.argument("symbols")
def crypto_stream(symbols):
    """Stream live crypto quotes and trades."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Starting crypto stream for {symbol_list}...")

    stream_client = CryptoDataStream(
        config.API_KEY, config.API_SECRET, feed=CryptoFeed.US
    )

    data = {s: {"bid": "-", "ask": "-", "trade": "-", "time": "-"} for s in symbol_list}

    def get_table():
        table = Table(title="Live Crypto Data", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Bid", style="green")
        table.add_column("Ask", style="red")
        table.add_column("Last Trade", style="yellow")
        table.add_column("Time", style="dim")
        for sym in symbol_list:
            d = data[sym]
            table.add_row(sym, d["bid"], d["ask"], d["trade"], d["time"])
        return table

    async def run():
        async def quote_handler(q):
            if q.symbol in data:
                data[q.symbol]["bid"] = f"{q.bid_price:.2f}"
                data[q.symbol]["ask"] = f"{q.ask_price:.2f}"
                data[q.symbol]["time"] = q.timestamp.astimezone().strftime("%H:%M:%S")

        async def trade_handler(t):
            if t.symbol in data:
                data[t.symbol]["trade"] = f"{format_currency(t.price)} x {t.size}"
                data[t.symbol]["time"] = t.timestamp.astimezone().strftime("%H:%M:%S")

        stream_client.subscribe_quotes(quote_handler, *symbol_list)
        stream_client.subscribe_trades(trade_handler, *symbol_list)

        with Live(get_table(), refresh_per_second=4) as live:

            async def update():
                while True:
                    live.update(get_table())
                    await asyncio.sleep(0.25)

            task = asyncio.create_task(update())
            try:
                await stream_client._run_forever()
            finally:
                task.cancel()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Stream stopped.")
    except Exception as e:
        logger.error(f"Stream error: {e}")
