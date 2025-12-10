import rich_click as click
import asyncio
from typing import Optional, List, Any
from typing import Optional, List, Any
from datetime import datetime, timedelta, timezone
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.live import StockDataStream, CryptoDataStream
from alpaca.data.requests import (
    StockBarsRequest,
    CryptoBarsRequest,
    StockLatestQuoteRequest,
    CryptoLatestQuoteRequest,
    StockLatestTradeRequest,
    CryptoLatestTradeRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed, CryptoFeed, Adjustment
from alpaca.common.enums import Sort
from alpaca_cli.core.config import config
from alpaca_cli.cli.utils import print_table, format_currency
from rich.live import Live
from rich.table import Table
from rich import box
from alpaca_cli.logger.logger import get_logger

logger = get_logger("data")


class StreamDisplay:
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.data = {
            s: {"bid": "-", "ask": "-", "trade": "-", "time": "-"} for s in symbols
        }

    def update_quote(self, symbol, bid, ask, timestamp):
        if symbol in self.data:
            self.data[symbol]["bid"] = f"{bid:.2f}"
            self.data[symbol]["ask"] = f"{ask:.2f}"
            self.data[symbol]["time"] = timestamp.strftime("%H:%M:%S")

    def update_trade(self, symbol, price, size, timestamp):
        if symbol in self.data:
            self.data[symbol]["trade"] = f"{format_currency(price)} x {size}"
            self.data[symbol]["time"] = timestamp.strftime("%H:%M:%S")

    def get_table(self) -> Table:
        table = Table(title="Live Market Data", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan", no_wrap=True)
        table.add_column("Bid", style="green")
        table.add_column("Ask", style="red")
        table.add_column("Last Trade", style="yellow")
        table.add_column("Last Update", style="dim")

        for sym in self.symbols:
            d = self.data[sym]
            table.add_row(sym, d["bid"], d["ask"], d["trade"], d["time"])

        return table


@click.group()
def data() -> None:
    """Market data (History, Latest, Stream)."""
    pass


@data.group()
def stock() -> None:
    """Stock market data."""
    pass


@data.group()
def crypto() -> None:
    """Crypto market data."""
    pass


# --- Helpers ---


def get_timeframe(tf_str: str) -> TimeFrame:
    tf_map = {
        "1Min": TimeFrame.Minute,
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day,
        "1Week": TimeFrame.Week,
        "1Month": TimeFrame.Month,
    }
    return tf_map.get(tf_str, TimeFrame.Day)


def get_sort(sort_str: Optional[str]) -> Optional[Sort]:
    if not sort_str:
        return None
    return Sort.ASC if sort_str.lower() == "asc" else Sort.DESC


def get_adjustment(adj_str: Optional[str]) -> Optional[Adjustment]:
    if not adj_str:
        return None
    adj_map = {
        "raw": Adjustment.RAW,
        "split": Adjustment.SPLIT,
        "dividend": Adjustment.DIVIDEND,
        "all": Adjustment.ALL,
    }
    return adj_map.get(adj_str.lower())


def get_stock_feed(feed_str: Optional[str]) -> DataFeed:
    if not feed_str:
        return DataFeed.IEX  # Default
    return DataFeed.SIP if feed_str.lower() == "sip" else DataFeed.IEX


def get_timeframe_delta(tf_str: str, limit: int) -> timedelta:
    """Calculate timedelta based on timeframe and limit."""
    if tf_str == "1Min":
        return timedelta(minutes=limit)
    elif tf_str == "1Hour":
        return timedelta(hours=limit)
    elif tf_str == "1Day":
        # Add buffer for weekends? User asked for strict "time frame for limit",
        # but pure calendar days might be short.
        # Let's interpret strict for now as per request: limit * 1 day.
        # Actually, adding a small multiplier (e.g. 1.5) for days helps cover weekends
        # to ensure we actually get 'limit' bars if intended.
        # But user said "start should be end - the time frame for limit".
        # I will strictly follow "limit * unit".
        return timedelta(days=limit)
    elif tf_str == "1Week":
        return timedelta(weeks=limit)
    elif tf_str == "1Month":
        return timedelta(days=30 * limit)
    return timedelta(days=limit)


# --- Stock Commands ---


@stock.command("history")
@click.argument("symbol")
@click.option(
    "--timeframe", default="1Day", help="Timeframe (1Min, 1Hour, 1Day, 1Week, 1Month)"
)
@click.option("--start", help="Start date (YYYY-MM-DD) [UTC]")
@click.option("--end", help="End date (YYYY-MM-DD) [UTC]")
@click.option("--limit", default=5, help="Number of bars")
@click.option(
    "--adjustment",
    type=click.Choice(["raw", "split", "dividend", "all"]),
    help="Corporate action adjustment",
)
@click.option("--feed", type=click.Choice(["iex", "sip"]), help="Data feed source")
@click.option("--sort", type=click.Choice(["asc", "desc"]), help="Sort direction")
def stock_history(
    symbol: str,
    timeframe: str,
    start: Optional[str],
    end: Optional[str],
    limit: int,
    adjustment: Optional[str],
    feed: Optional[str],
    sort: Optional[str],
) -> None:
    """Get historical stock bars."""
    config.validate()
    symbol = symbol.upper()
    logger.info(f"Fetching {timeframe} stock history for {symbol}...")

    client = StockHistoricalDataClient(config.API_KEY, config.API_SECRET)

    # default end is now - 30 minutes (UTC) since free tier SIP data is not available
    now_utc = datetime.now(timezone.utc)
    default_end = now_utc - timedelta(minutes=30)

    end_dt = default_end
    if end:
        end_dt = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    start_dt = None
    if start:
        start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        # Calculate start based on end and limit
        delta = get_timeframe_delta(timeframe, limit)
        start_dt = end_dt - delta

    try:
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=get_timeframe(timeframe),
            start=start_dt,
            end=end_dt,
            limit=limit,
            adjustment=get_adjustment(adjustment),
            feed=get_stock_feed(feed),
            sort=get_sort(sort),
        )
        bars = client.get_stock_bars(req)

        if not bars or not bars.data:
            logger.info("No data found.")
            return

        data_rows = []
        for bar in bars[symbol]:
            data_rows.append(
                [
                    bar.timestamp.strftime("%Y-%m-%d %H:%M"),
                    format_currency(bar.open),
                    format_currency(bar.high),
                    format_currency(bar.low),
                    format_currency(bar.close),
                    str(bar.volume),
                ]
            )

        print_table(
            f"{symbol} History",
            ["Time", "Open", "High", "Low", "Close", "Volume"],
            data_rows,
        )

    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")


@stock.command("latest")
@click.argument("symbol")
@click.option("--feed", type=click.Choice(["iex", "sip"]), help="Data feed source")
def stock_latest(symbol: str, feed: Optional[str]) -> None:
    """Get latest stock quote and trade."""
    config.validate()
    symbol = symbol.upper()
    logger.info(f"Fetching latest stock data for {symbol}...")

    client = StockHistoricalDataClient(config.API_KEY, config.API_SECRET)
    feed_enum = get_stock_feed(feed)

    try:
        q_req = StockLatestQuoteRequest(symbol_or_symbols=symbol, feed=feed_enum)
        t_req = StockLatestTradeRequest(symbol_or_symbols=symbol, feed=feed_enum)

        quote = client.get_stock_latest_quote(q_req)
        trade = client.get_stock_latest_trade(t_req)

        rows = []
        if symbol in quote:
            q = quote[symbol]
            rows.append(["Bid", f"{format_currency(q.bid_price)} x {q.bid_size}"])
            rows.append(["Ask", f"{format_currency(q.ask_price)} x {q.ask_size}"])

        if symbol in trade:
            t = trade[symbol]
            rows.append(["Last Trade", f"{format_currency(t.price)} x {t.size}"])
            local_dt = t.timestamp.astimezone()
            rows.append(["Trade Time", local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")])

        print_table(f"{symbol} Latest", ["Metric", "Value"], rows)

    except Exception as e:
        logger.error(f"Failed to fetch latest data: {e}")


@stock.command("stream")
@click.argument("symbols")
@click.option("--feed", default="iex", help="Data feed (iex, sip)")
def stock_stream(symbols: str, feed: str) -> None:
    """Stream live stock data."""
    config.validate()
    symbol_list = symbols.upper().split(",")
    logger.info(f"Starting STOCK stream for {symbol_list} (Feed: {feed})...")

    feed_enum = DataFeed.SIP if feed.lower() == "sip" else DataFeed.IEX
    stream_client = StockDataStream(config.API_KEY, config.API_SECRET, feed=feed_enum)
    display = StreamDisplay(symbol_list)

    async def run_stream():
        async def quote_handler(data):
            # Convert to local time for display
            local_dt = data.timestamp.astimezone()
            display.update_quote(data.symbol, data.bid_price, data.ask_price, local_dt)

        async def trade_handler(data):
            # Convert to local time for display
            local_dt = data.timestamp.astimezone()
            display.update_trade(data.symbol, data.price, data.size, local_dt)

        stream_client.subscribe_quotes(quote_handler, *symbol_list)
        stream_client.subscribe_trades(trade_handler, *symbol_list)

        # Use a background task for the stream to allow Live loop to update?
        # Actually simplest way with rich.Live in async is:
        # run stream in task, and while it runs, update live.
        # But stream_client._run_forever blocks.
        # So we can just update the display in handlers (which updates the object),
        # And Live(..., refresh_per_second=4) will poll get_table().

        # We need to run Live in context manager, then await stream.
        with Live(display.get_table(), refresh_per_second=4) as live:
            # We need to hook into the loop to update the table reference because get_table returns a NEW table.
            # Rich Live calls the renderable (if it's a function) or re-prints the object.
            # If we pass a function that returns a table, Live works great.
            def generate_table():
                return display.get_table()

            live.update(
                generate_table
            )  # This sets the renderable to the function... wait Live expects a Renderable.
            # Correction: Live(get_renderable=generate_table) is not the signature.
            # We can use live.update(display.get_table()) inside a loop, but we are blocked by _run_forever.
            # Solution: Run _run_forever in a task.

            # Better pattern for async stream + rich live:
            # Pass a "proxy" renderable or use screen update loop.
            # Actually, we can just update the live display in the handlers!
            # But handlers are async.
            # Let's try passing the `live` object to handlers? No, thread safety.
            # Standard pattern:
            # live = Live(display.get_table(), auto_refresh=True)
            # live.start()
            # ... await stream ...
            # live.stop()
            # But we need to update the table object in Live because we create a NEW table each time in get_table().
            # If we modify a SINGLE table object, rows are appended? No, Rich tables are static data.
            # We must replace the table.

            # Let's use a wrapper task that updates the Live view periodically.
            async def update_view():
                while True:
                    live.update(display.get_table())
                    await asyncio.sleep(0.25)

            view_task = asyncio.create_task(update_view())

            try:
                await stream_client._run_forever()
            finally:
                view_task.cancel()

    try:
        asyncio.run(run_stream())
    except KeyboardInterrupt:
        logger.info("Stream stopped.")
    except Exception as e:
        logger.error(f"Stream error: {e}")


# --- Crypto Commands ---


@crypto.command("history")
@click.argument("symbol")
@click.option(
    "--timeframe", default="1Day", help="Timeframe (1Min, 1Hour, 1Day, 1Week, 1Month)"
)
@click.option("--start", help="Start date (YYYY-MM-DD) [UTC]")
@click.option("--end", help="End date (YYYY-MM-DD) [UTC]")
@click.option("--limit", default=5, help="Number of bars")
@click.option("--sort", type=click.Choice(["asc", "desc"]), help="Sort direction")
def crypto_history(
    symbol: str,
    timeframe: str,
    start: Optional[str],
    end: Optional[str],
    limit: int,
    sort: Optional[str],
) -> None:
    """Get historical crypto bars."""
    config.validate()
    symbol = symbol.upper()
    logger.info(f"Fetching {timeframe} crypto history for {symbol}...")

    client = CryptoHistoricalDataClient(config.API_KEY, config.API_SECRET)

    end_dt = None
    if end:
        end_dt = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    start_dt = None
    if start:
        start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        # For crypto default end is now
        anchor = end_dt if end_dt else datetime.now(timezone.utc)
        delta = get_timeframe_delta(timeframe, limit)
        start_dt = anchor - delta

    try:
        req = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=get_timeframe(timeframe),
            start=start_dt,
            end=end_dt,
            limit=limit,
            sort=get_sort(sort),
            # Crypto doesn't use feed/adjustment in requests quite the same way or defaults are fine
        )
        bars = client.get_crypto_bars(req)

        if not bars or not bars.data:
            logger.info("No data found.")
            return

        data_rows = []
        for bar in bars[symbol]:
            data_rows.append(
                [
                    bar.timestamp.strftime("%Y-%m-%d %H:%M"),
                    format_currency(bar.open),
                    format_currency(bar.high),
                    format_currency(bar.low),
                    format_currency(bar.close),
                    str(bar.volume),
                ]
            )

        print_table(
            f"{symbol} History",
            ["Time", "Open", "High", "Low", "Close", "Volume"],
            data_rows,
        )

    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")


@crypto.command("latest")
@click.argument("symbol")
def crypto_latest(symbol: str) -> None:
    """Get latest crypto quote and trade."""
    config.validate()
    symbol = symbol.upper()
    logger.info(f"Fetching latest crypto data for {symbol}...")

    client = CryptoHistoricalDataClient(config.API_KEY, config.API_SECRET)

    try:
        q_req = CryptoLatestQuoteRequest(symbol_or_symbols=symbol)
        t_req = CryptoLatestTradeRequest(symbol_or_symbols=symbol)

        quote = client.get_crypto_latest_quote(q_req)
        trade = client.get_crypto_latest_trade(t_req)

        rows = []
        if symbol in quote:
            q = quote[symbol]
            rows.append(["Bid", f"{format_currency(q.bid_price)} x {q.bid_size}"])
            rows.append(["Ask", f"{format_currency(q.ask_price)} x {q.ask_size}"])

        if symbol in trade:
            t = trade[symbol]
            rows.append(["Last Trade", f"{format_currency(t.price)} x {t.size}"])
            local_dt = t.timestamp.astimezone()
            rows.append(["Trade Time", local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")])

        print_table(f"{symbol} Latest", ["Metric", "Value"], rows)

    except Exception as e:
        logger.error(f"Failed to fetch latest data: {e}")


@crypto.command("stream")
@click.argument("symbols")
def crypto_stream(symbols: str) -> None:
    """Stream live crypto data."""
    config.validate()
    symbol_list = symbols.upper().split(",")
    logger.info(f"Starting CRYPTO stream for {symbol_list}...")

    stream_client = CryptoDataStream(
        config.API_KEY, config.API_SECRET, feed=CryptoFeed.US
    )
    display = StreamDisplay(symbol_list)

    async def run_stream():
        async def quote_handler(data):
            # Convert to local time for display
            local_dt = data.timestamp.astimezone()
            display.update_quote(data.symbol, data.bid_price, data.ask_price, local_dt)

        async def trade_handler(data):
            local_dt = data.timestamp.astimezone()
            display.update_trade(data.symbol, data.price, data.size, local_dt)

        stream_client.subscribe_quotes(quote_handler, *symbol_list)
        stream_client.subscribe_trades(trade_handler, *symbol_list)

        with Live(display.get_table(), refresh_per_second=4) as live:

            async def update_view():
                while True:
                    live.update(display.get_table())
                    await asyncio.sleep(0.25)

            view_task = asyncio.create_task(update_view())
            try:
                await stream_client._run_forever()
            finally:
                view_task.cancel()

    try:
        asyncio.run(run_stream())
    except KeyboardInterrupt:
        logger.info("Stream stopped.")
    except Exception as e:
        logger.error(f"Stream error: {e}")


# --- SCREENERS ---
@data.group()
def screeners() -> None:
    """Market screeners (movers, most actives)."""
    pass


@screeners.command("movers")
@click.option(
    "--market",
    type=click.Choice(["stocks", "crypto"], case_sensitive=False),
    default="stocks",
    help="Market type",
)
@click.option("--top", default=10, help="Number of movers to show")
def movers(market: str, top: int) -> None:
    """Get top market movers (gainers/losers)."""
    from alpaca.data.historical.screener import ScreenerClient
    from alpaca.data.requests import MarketMoversRequest

    config.validate()
    logger.info(f"Fetching {market} movers...")

    try:
        client = ScreenerClient(config.API_KEY, config.API_SECRET)
        req = MarketMoversRequest(top=top)
        result = client.get_market_movers(req)
        
        if not result or not result.gainers:
            logger.info("No movers data found.")
            return

        # Gainers
        gainer_rows = []
        for m in result.gainers[:top]:
            gainer_rows.append([
                m.symbol,
                format_currency(m.price) if m.price else "-",
                f"[green]+{m.percent_change:.2f}%[/green]" if m.percent_change else "-",
                format_currency(m.change) if m.change else "-",
            ])

        print_table("Top Gainers", ["Symbol", "Price", "% Change", "$ Change"], gainer_rows)

        # Losers
        if result.losers:
            loser_rows = []
            for m in result.losers[:top]:
                loser_rows.append([
                    m.symbol,
                    format_currency(m.price) if m.price else "-",
                    f"[red]{m.percent_change:.2f}%[/red]" if m.percent_change else "-",
                    format_currency(m.change) if m.change else "-",
                ])
            print_table("Top Losers", ["Symbol", "Price", "% Change", "$ Change"], loser_rows)

    except Exception as e:
        logger.error(f"Failed to get movers: {e}")


@screeners.command("actives")
@click.option(
    "--by",
    type=click.Choice(["volume", "trades"], case_sensitive=False),
    default="volume",
    help="Sort by volume or number of trades",
)
@click.option("--top", default=10, help="Number of stocks to show")
def actives(by: str, top: int) -> None:
    """Get most active stocks."""
    from alpaca.data.historical.screener import ScreenerClient
    from alpaca.data.requests import MostActivesRequest
    from alpaca.data.enums import MostActivesBy

    config.validate()
    logger.info(f"Fetching most active stocks (by {by})...")

    try:
        client = ScreenerClient(config.API_KEY, config.API_SECRET)
        
        by_enum = MostActivesBy.VOLUME if by.lower() == "volume" else MostActivesBy.TRADES
        req = MostActivesRequest(top=top, by=by_enum)
        result = client.get_most_actives(req)
        
        if not result or not result.most_actives:
            logger.info("No data found.")
            return

        rows = []
        for stock in result.most_actives:
            rows.append([
                stock.symbol,
                str(int(stock.volume)) if stock.volume else "-",
                str(int(stock.trade_count)) if stock.trade_count else "-",
            ])

        print_table(f"Most Active ({by.upper()})", ["Symbol", "Volume", "Trades"], rows)

    except Exception as e:
        logger.error(f"Failed to get most actives: {e}")


# --- ORDERBOOK ---
@crypto.command("orderbook")
@click.argument("symbol")
def crypto_orderbook(symbol: str) -> None:
    """Get crypto orderbook (bid/ask depth)."""
    from alpaca.data.requests import CryptoLatestOrderbookRequest

    config.validate()
    symbol = symbol.upper()
    logger.info(f"Fetching orderbook for {symbol}...")

    try:
        client = CryptoHistoricalDataClient(config.API_KEY, config.API_SECRET)
        req = CryptoLatestOrderbookRequest(symbol_or_symbols=symbol)
        result = client.get_crypto_latest_orderbook(req)

        if not result or symbol not in result:
            logger.info("No orderbook data found.")
            return

        orderbook = result[symbol]

        # Bids
        bid_rows = []
        for bid in orderbook.bids[:10]:
            bid_rows.append([format_currency(bid.price), str(bid.size)])
        
        print_table(f"{symbol} Bids", ["Price", "Size"], bid_rows)

        # Asks
        ask_rows = []
        for ask in orderbook.asks[:10]:
            ask_rows.append([format_currency(ask.price), str(ask.size)])
        
        print_table(f"{symbol} Asks", ["Price", "Size"], ask_rows)

    except Exception as e:
        logger.error(f"Failed to get orderbook: {e}")


# --- CORPORATE ACTIONS ---
@data.command("corporate-actions")
@click.option("--symbols", help="Comma-separated symbols")
@click.option(
    "--types",
    help="Comma-separated types (dividend, merger, spinoff, split)",
)
@click.option("--start", help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
@click.option("--limit", default=20, help="Max results")
def corporate_actions(
    symbols: Optional[str],
    types: Optional[str],
    start: Optional[str],
    end: Optional[str],
    limit: int,
) -> None:
    """Get corporate actions (dividends, splits, etc.)."""
    from alpaca.data.historical.corporate_actions import CorporateActionsClient
    from alpaca.data.requests import CorporateActionsRequest

    config.validate()
    logger.info("Fetching corporate actions...")

    try:
        client = CorporateActionsClient(config.API_KEY, config.API_SECRET)

        symbol_list = symbols.upper().split(",") if symbols else None
        type_list = types.lower().split(",") if types else None
        start_dt = datetime.strptime(start, "%Y-%m-%d") if start else None
        end_dt = datetime.strptime(end, "%Y-%m-%d") if end else None

        req = CorporateActionsRequest(
            symbols=symbol_list,
            types=type_list,
            start=start_dt,
            end=end_dt,
            limit=limit,
        )

        result = client.get_corporate_actions(req)

        if not result or not result.data:
            logger.info("No corporate actions found.")
            return

        rows = []
        # Corporate actions data is in result.data dict with action types as keys
        for action_type, actions in result.data.items():
            if not actions:
                continue
            for action in actions:
                rows.append([
                    action_type,
                    getattr(action, "symbol", getattr(action, "old_symbol", "-")),
                    str(getattr(action, "ex_date", getattr(action, "effective_date", "-"))),
                    str(getattr(action, "record_date", "-") if hasattr(action, "record_date") else "-"),
                    str(getattr(action, "cash_amount", getattr(action, "new_rate", "-"))),
                ])

        if not rows:
            logger.info("No corporate actions found.")
            return

        print_table(
            "Corporate Actions",
            ["Type", "Symbol", "Ex-Date", "Record Date", "Value"],
            rows,
        )

    except Exception as e:
        logger.error(f"Failed to get corporate actions: {e}")
