from typing import Optional
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca_cli.core.config import config


class AlpacaClient:
    _instance: Optional[TradingClient] = None

    @classmethod
    def get_client(cls) -> TradingClient:
        if cls._instance is None:
            config.validate()
            # We know these are not None after validate()
            assert config.API_KEY is not None
            assert config.API_SECRET is not None

            cls._instance = TradingClient(
                api_key=config.API_KEY,
                secret_key=config.API_SECRET,
                paper=config.IS_PAPER,
                url_override=None if config.IS_PAPER else config.BASE_URL,
            )
        return cls._instance


class AlpacaDataClient:
    """Singleton manager for data clients (Stock and Crypto)."""

    _stock_instance: Optional[StockHistoricalDataClient] = None
    _crypto_instance: Optional[CryptoHistoricalDataClient] = None

    @classmethod
    def get_stock_client(cls) -> StockHistoricalDataClient:
        """Get singleton StockHistoricalDataClient instance."""
        if cls._stock_instance is None:
            config.validate()
            assert config.API_KEY is not None
            assert config.API_SECRET is not None
            cls._stock_instance = StockHistoricalDataClient(
                api_key=config.API_KEY,
                secret_key=config.API_SECRET,
            )
        return cls._stock_instance

    @classmethod
    def get_crypto_client(cls) -> CryptoHistoricalDataClient:
        """Get singleton CryptoHistoricalDataClient instance."""
        if cls._crypto_instance is None:
            config.validate()
            assert config.API_KEY is not None
            assert config.API_SECRET is not None
            cls._crypto_instance = CryptoHistoricalDataClient(
                api_key=config.API_KEY,
                secret_key=config.API_SECRET,
            )
        return cls._crypto_instance


def get_trading_client() -> TradingClient:
    """Get singleton TradingClient instance."""
    return AlpacaClient.get_client()


def get_stock_data_client() -> StockHistoricalDataClient:
    """Get singleton StockHistoricalDataClient instance."""
    return AlpacaDataClient.get_stock_client()


def get_crypto_data_client() -> CryptoHistoricalDataClient:
    """Get singleton CryptoHistoricalDataClient instance."""
    return AlpacaDataClient.get_crypto_client()
