"""Stock market data commands - bars, quotes, trades, latest, snapshot, stream."""

import rich_click as click
import asyncio
from typing import Optional
from datetime import datetime, timedelta, timezone
from alpaca.data.live import StockDataStream
from alpaca.data.requests import (
    StockBarsRequest,
    StockQuotesRequest,
    StockTradesRequest,
    StockLatestQuoteRequest,
    StockLatestTradeRequest,
    StockLatestBarRequest,
    StockSnapshotRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed, Adjustment
from alpaca.common.enums import Sort
from alpaca_cli.core.config import config
from alpaca_cli.core.client import get_stock_data_client
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger
from rich.live import Live
from rich.table import Table
from rich import box

logger = get_logger("data.stock")


def get_timeframe(tf_str: str) -> TimeFrame:
    return {
        "1Min": TimeFrame.Minute,
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day,
        "1Week": TimeFrame.Week,
        "1Month": TimeFrame.Month,
    }.get(tf_str, TimeFrame.Day)


def get_stock_feed(feed_str: Optional[str]) -> DataFeed:
    return DataFeed.SIP if feed_str and feed_str.lower() == "sip" else DataFeed.IEX


def get_adjustment(adj_str: Optional[str]) -> Optional[Adjustment]:
    if not adj_str:
        return None
    return {
        "raw": Adjustment.RAW,
        "split": Adjustment.SPLIT,
        "dividend": Adjustment.DIVIDEND,
        "all": Adjustment.ALL,
    }.get(adj_str.lower())


@click.group()
def stock() -> None:
    """Stock market data (bars, quotes, trades, latest, snapshot, stream)."""
    pass


@stock.command("bars")
@click.argument("symbols")
@click.option(
    "--timeframe",
    "-t",
    type=str,
    default="1Day",
    help="[Optional] Timeframe for bars. Choices: 1Min, 1Hour, 1Day, 1Week, 1Month. Default: 1Day",
)
@click.option(
    "--start",
    type=str,
    default=None,
    help="[Optional] Start date in YYYY-MM-DD format. Default: end date minus limit days",
)
@click.option(
    "--end",
    type=str,
    default=None,
    help="[Optional] End date in YYYY-MM-DD format. Default: current date",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="[Optional] Maximum number of bars to return. Default: 100",
)
@click.option(
    "--adjustment",
    type=click.Choice(["raw", "split", "dividend", "all"]),
    default=None,
    help="[Optional] Price adjustment type. Choices: raw, split, dividend, all",
)
@click.option(
    "--feed",
    type=click.Choice(["iex", "sip"]),
    default="iex",
    help="[Optional] Data feed source. Choices: iex, sip. Default: iex",
)
@click.option(
    "--sort",
    type=click.Choice(["asc", "desc"]),
    default=None,
    help="[Optional] Sort order for results. Choices: asc, desc",
)
@click.option(
    "--currency",
    type=str,
    default=None,
    help="[Optional] Currency for price results (e.g., USD, EUR)",
)
def stock_bars(
    symbols: str,
    timeframe: str,
    start: Optional[str],
    end: Optional[str],
    limit: int,
    adjustment: Optional[str],
    feed: str,
    sort: Optional[str],
    currency: Optional[str],
) -> None:
    """Get historical stock bars (OHLCV)."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching {timeframe} bars for {symbol_list}...")

    client = get_stock_data_client()

    end_dt = (
        datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end
        else datetime.now(timezone.utc) - timedelta(minutes=30)
    )
    start_dt = (
        datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if start
        else end_dt - timedelta(days=limit)
    )

    try:
        req = StockBarsRequest(
            symbol_or_symbols=symbol_list,
            timeframe=get_timeframe(timeframe),
            start=start_dt,
            end=end_dt,
            limit=limit,
            adjustment=get_adjustment(adjustment),
            feed=get_stock_feed(feed),
            sort=Sort.ASC if sort == "asc" else Sort.DESC if sort else None,
            currency=currency,
        )
        bars = client.get_stock_bars(req)

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


@stock.command("quotes")
@click.argument("symbols")
@click.option(
    "--start",
    type=str,
    required=True,
    help="[Required] Start date in YYYY-MM-DD format",
)
@click.option(
    "--end",
    type=str,
    default=None,
    help="[Optional] End date in YYYY-MM-DD format. Default: current date",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="[Optional] Maximum number of quotes to return. Default: 100",
)
@click.option(
    "--feed",
    type=click.Choice(["iex", "sip"]),
    default="iex",
    help="[Optional] Data feed source. Choices: iex, sip. Default: iex",
)
@click.option(
    "--sort",
    type=click.Choice(["asc", "desc"]),
    default=None,
    help="[Optional] Sort order for results. Choices: asc, desc",
)
def stock_quotes(
    symbols: str,
    start: str,
    end: Optional[str],
    limit: int,
    feed: str,
    sort: Optional[str],
) -> None:
    """Get historical stock quotes (NBBO)."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching quotes for {symbol_list}...")

    client = get_stock_data_client()

    start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = (
        datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc) if end else None
    )

    try:
        req = StockQuotesRequest(
            symbol_or_symbols=symbol_list,
            start=start_dt,
            end=end_dt,
            limit=limit,
            feed=get_stock_feed(feed),
            sort=Sort.ASC if sort == "asc" else Sort.DESC if sort else None,
        )
        quotes = client.get_stock_quotes(req)

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
                    q.bid_exchange or "-",
                    q.ask_exchange or "-",
                ]
                for q in list(quotes[sym])[:50]
            ]  # Limit rows for display
            print_table(
                f"{sym} Quotes",
                ["Time", "Bid", "Bid Size", "Ask", "Ask Size", "Bid Ex", "Ask Ex"],
                rows,
            )
    except Exception as e:
        logger.error(f"Failed to fetch quotes: {e}")


@stock.command("trades")
@click.argument("symbols")
@click.option(
    "--start",
    type=str,
    required=True,
    help="[Required] Start date in YYYY-MM-DD format",
)
@click.option(
    "--end",
    type=str,
    default=None,
    help="[Optional] End date in YYYY-MM-DD format. Default: current date",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="[Optional] Maximum number of trades to return. Default: 100",
)
@click.option(
    "--feed",
    type=click.Choice(["iex", "sip"]),
    default="iex",
    help="[Optional] Data feed source. Choices: iex, sip. Default: iex",
)
@click.option(
    "--sort",
    type=click.Choice(["asc", "desc"]),
    default=None,
    help="[Optional] Sort order for results. Choices: asc, desc",
)
def stock_trades(
    symbols: str,
    start: str,
    end: Optional[str],
    limit: int,
    feed: str,
    sort: Optional[str],
) -> None:
    """Get historical stock trades (time & sales)."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching trades for {symbol_list}...")

    client = get_stock_data_client()

    start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = (
        datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc) if end else None
    )

    try:
        req = StockTradesRequest(
            symbol_or_symbols=symbol_list,
            start=start_dt,
            end=end_dt,
            limit=limit,
            feed=get_stock_feed(feed),
            sort=Sort.ASC if sort == "asc" else Sort.DESC if sort else None,
        )
        trades = client.get_stock_trades(req)

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
                    str(t.id) if t.id else "-",
                ]
                for t in list(trades[sym])[:50]
            ]
            print_table(
                f"{sym} Trades", ["Time", "Price", "Size", "Exchange", "Trade ID"], rows
            )
    except Exception as e:
        logger.error(f"Failed to fetch trades: {e}")


@stock.command("latest")
@click.argument("symbols")
@click.option(
    "--feed",
    type=click.Choice(["iex", "sip"]),
    default="iex",
    help="[Optional] Data feed source. Choices: iex, sip. Default: iex",
)
@click.option(
    "--currency",
    type=str,
    default=None,
    help="[Optional] Currency for price results (e.g., USD, EUR)",
)
def stock_latest(symbols: str, feed: str, currency: Optional[str]) -> None:
    """Get latest stock quote, trade, and bar."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching latest data for {symbol_list}...")

    client = get_stock_data_client()
    feed_enum = get_stock_feed(feed)

    try:
        q_req = StockLatestQuoteRequest(
            symbol_or_symbols=symbol_list, feed=feed_enum, currency=currency
        )
        t_req = StockLatestTradeRequest(
            symbol_or_symbols=symbol_list, feed=feed_enum, currency=currency
        )
        b_req = StockLatestBarRequest(
            symbol_or_symbols=symbol_list, feed=feed_enum, currency=currency
        )

        quotes = client.get_stock_latest_quote(q_req)
        trades = client.get_stock_latest_trade(t_req)
        bars = client.get_stock_latest_bar(b_req)

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


@stock.command("snapshot")
@click.argument("symbols")
@click.option(
    "--feed",
    type=click.Choice(["iex", "sip"]),
    default="iex",
    help="[Optional] Data feed source. Choices: iex, sip. Default: iex",
)
@click.option(
    "--currency",
    type=str,
    default=None,
    help="[Optional] Currency for price results (e.g., USD, EUR)",
)
def stock_snapshot(symbols: str, feed: str, currency: Optional[str]) -> None:
    """Get stock snapshot (quote, trade, bar, prev close)."""
    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Fetching snapshots for {symbol_list}...")

    client = get_stock_data_client()

    try:
        req = StockSnapshotRequest(
            symbol_or_symbols=symbol_list, feed=get_stock_feed(feed), currency=currency
        )
        snapshots = client.get_stock_snapshot(req)

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
                rows.append(["Daily Open", format_currency(snap.daily_bar.open)])
                rows.append(["Daily High", format_currency(snap.daily_bar.high)])
                rows.append(["Daily Low", format_currency(snap.daily_bar.low)])
                rows.append(["Daily Close", format_currency(snap.daily_bar.close)])
                rows.append(["Daily Volume", str(snap.daily_bar.volume)])
            if snap.previous_daily_bar:
                rows.append(
                    ["Prev Close", format_currency(snap.previous_daily_bar.close)]
                )
            print_table(f"{sym} Snapshot", ["Metric", "Value"], rows)
    except Exception as e:
        logger.error(f"Failed to fetch snapshot: {e}")


@stock.command("stream")
@click.argument("symbols")
@click.option(
    "--feed",
    type=click.Choice(["iex", "sip"]),
    default="iex",
    help="[Optional] Data feed source. Choices: iex, sip. Default: iex",
)
def stock_stream(symbols: str, feed: str) -> None:
    """Stream live stock quotes and trades."""
    import logging as stdlib_logging

    config.validate()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    logger.info(f"Starting stock stream for {symbol_list}...")

    feed_enum = get_stock_feed(feed)
    stream_client = StockDataStream(config.API_KEY, config.API_SECRET, feed=feed_enum)

    data = {s: {"bid": "-", "ask": "-", "trade": "-", "time": "-"} for s in symbol_list}

    def get_table():
        from alpaca_cli.cli.theme import create_stream_table

        table = create_stream_table(
            "Live Stock Data", ["Symbol", "Bid", "Ask", "Last Trade", "Time"]
        )
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

        # Suppress websocket logging during Live display to prevent interference
        ws_logger = stdlib_logging.getLogger("alpaca.data.live.websocket")
        ws_logger.setLevel(stdlib_logging.WARNING)

        # Disable auto_refresh and use only manual update() calls to avoid double rendering
        with Live(get_table(), auto_refresh=False) as live:

            async def update():
                while True:
                    await asyncio.sleep(0.25)
                    live.update(get_table(), refresh=True)

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
