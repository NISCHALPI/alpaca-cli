"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal


@pytest.fixture
def mock_trading_client():
    """Mock TradingClient for tests."""
    with patch("alpaca_cli.core.client.TradingClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        # Mock account data
        mock_account = MagicMock()
        mock_account.equity = "10000.00"
        mock_account.cash = "5000.00"
        mock_account.buying_power = "10000.00"
        mock_account.last_equity = "9900.00"
        mock_client.get_account.return_value = mock_account

        # Mock clock
        mock_clock = MagicMock()
        mock_clock.is_open = True
        mock_client.get_clock.return_value = mock_clock

        yield mock_client


@pytest.fixture
def mock_stock_data_client():
    """Mock StockHistoricalDataClient for tests."""
    with patch("alpaca_cli.core.client.StockHistoricalDataClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_crypto_data_client():
    """Mock CryptoHistoricalDataClient for tests."""
    with patch("alpaca_cli.core.client.CryptoHistoricalDataClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_positions():
    """Sample position data for testing."""
    return {
        "AAPL": 10.0,
        "MSFT": 5.0,
        "GOOGL": 2.0,
    }


@pytest.fixture
def sample_weights():
    """Sample target weights for testing."""
    return {
        "AAPL": 0.4,
        "MSFT": 0.3,
        "GOOGL": 0.2,
        "CASH": 0.1,
    }


@pytest.fixture
def sample_prices():
    """Sample price data for testing."""
    return {
        "AAPL": 150.00,
        "MSFT": 300.00,
        "GOOGL": 140.00,
    }
