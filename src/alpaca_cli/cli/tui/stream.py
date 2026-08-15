import threading
from typing import Callable, List
from alpaca.data.live.stock import StockDataStream
from alpaca.data.live.news import NewsDataStream
from alpaca_cli.core.config import config

class MarketStreamer:
    def __init__(self, symbols: List[str], on_quote: Callable = None, on_trade: Callable = None):
        self.symbols = symbols
        self.stream = StockDataStream(config.API_KEY, config.API_SECRET)
        self.thread = None
        self.on_quote = on_quote
        self.on_trade = on_trade
        
        if self.on_quote:
            self.stream.subscribe_quotes(self.on_quote, *self.symbols)
        if self.on_trade:
            self.stream.subscribe_trades(self.on_trade, *self.symbols)
            
    def add_symbol(self, symbol: str):
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            if self.on_quote:
                self.stream.subscribe_quotes(self.on_quote, symbol)
            if self.on_trade:
                self.stream.subscribe_trades(self.on_trade, symbol)

    def remove_symbol(self, symbol: str):
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            if self.on_quote:
                self.stream.unsubscribe_quotes(symbol)
            if self.on_trade:
                self.stream.unsubscribe_trades(symbol)
            
    def start(self):
        self.thread = threading.Thread(target=self.stream.run, daemon=True)
        self.thread.start()

    def stop(self):
        try:
            self.stream.stop()
        except Exception:
            pass
        if self.thread:
            self.thread.join(timeout=1.0)

class NewsStreamer:
    def __init__(self, symbols: List[str], on_news: Callable = None):
        self.symbols = symbols
        self.stream = NewsDataStream(config.API_KEY, config.API_SECRET)
        self.thread = None
        
        if on_news:
            self.stream.subscribe_news(on_news, *self.symbols)
            
    def start(self):
        self.thread = threading.Thread(target=self.stream.run, daemon=True)
        self.thread.start()

    def stop(self):
        try:
            self.stream.stop()
        except Exception:
            pass
        if self.thread:
            self.thread.join(timeout=1.0)
