from typing import Optional
from alpaca.trading.client import TradingClient
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


def get_trading_client() -> TradingClient:
    return AlpacaClient.get_client()
