import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from alpaca_cli.cli.main import cli
from datetime import datetime


@pytest.fixture
def runner():
    return CliRunner()


def test_stock_latest(runner):
    """Test 'data stock latest' command."""
    with patch(
        "alpaca_cli.cli.groups.data.stock.StockHistoricalDataClient"
    ) as MockClient:
        mock_instance = MockClient.return_value

        # Mock response objects
        mock_quote = MagicMock()
        mock_quote.bid_price = 150.00
        mock_quote.ask_price = 150.10
        mock_quote.bid_size = 100
        mock_quote.ask_size = 200
        mock_quote.timestamp = datetime.now()

        mock_trade = MagicMock()
        mock_trade.price = 150.05
        mock_trade.size = 50
        mock_trade.timestamp = datetime.now()

        mock_bar = MagicMock()
        mock_bar.close = 150.00
        mock_bar.volume = 1000
        mock_bar.timestamp = datetime.now()

        # Setup returns
        mock_instance.get_stock_latest_quote.return_value = {"AAPL": mock_quote}
        mock_instance.get_stock_latest_trade.return_value = {"AAPL": mock_trade}
        mock_instance.get_stock_latest_bar.return_value = {"AAPL": mock_bar}

        result = runner.invoke(cli, ["data", "stock", "latest", "AAPL"])

        assert result.exit_code == 0
        assert "AAPL Latest" in result.output
        assert "150.05" in result.output  # Last trade price


def test_crypto_bars(runner):
    """Test 'data crypto bars' command."""
    with patch(
        "alpaca_cli.cli.groups.data.crypto.CryptoHistoricalDataClient"
    ) as MockClient:
        mock_instance = MockClient.return_value

        # Mock bar object
        mock_bar = MagicMock()
        mock_bar.timestamp = datetime(2023, 1, 1, 12, 0)
        mock_bar.open = 30000.0
        mock_bar.high = 31000.0
        mock_bar.low = 29000.0
        mock_bar.close = 30500.0
        mock_bar.volume = 100.0
        mock_bar.vwap = 30200.0

        # Setup return object that behaves like BarSet
        mock_response = MagicMock()
        mock_response.data = {"BTC/USD": [mock_bar]}
        mock_response.__getitem__.side_effect = lambda k: (
            [mock_bar] if k == "BTC/USD" else []
        )
        mock_response.__contains__.side_effect = lambda k: k in mock_response.data

        mock_instance.get_crypto_bars.return_value = mock_response

        # Set COLUMNS to prevent truncation locally
        result = runner.invoke(
            cli,
            ["data", "crypto", "bars", "BTC/USD", "--limit", "1"],
            env={"COLUMNS": "200"},
        )
        if result.exit_code != 0:
            print(result.output)

        assert result.exit_code == 0
        assert "BTC/USD Bars" in result.output
        assert "30,500.00" in result.output


def test_options_chain(runner):
    """Test 'data options chain' command."""
    with patch(
        "alpaca_cli.cli.groups.data.options.OptionHistoricalDataClient"
    ) as MockClient:
        mock_instance = MockClient.return_value

        # Mock option snapshot for chain
        mock_snap = MagicMock()
        mock_snap.latest_quote.bid_price = 5.00
        mock_snap.latest_quote.ask_price = 5.10
        mock_snap.latest_trade.price = 5.05
        mock_snap.greeks.delta = 0.5
        mock_snap.implied_volatility = 0.2

        # Setup return
        mock_instance.get_option_chain.return_value = {"AAPL230616C00150000": mock_snap}

        result = runner.invoke(cli, ["data", "options", "chain", "AAPL"])

        assert result.exit_code == 0
        assert "Option Chain: AAPL" in result.output
        assert "AAPL230616C00150000" in result.output
        assert "0.500" in result.output  # Delta


def test_news_command(runner):
    """Test 'data news' command."""
    from alpaca.data.models.news import NewsSet

    with patch("alpaca.data.historical.news.NewsClient") as MockClient:
        mock_instance = MockClient.return_value
        
        # Mock result
        mock_result = MagicMock(spec=NewsSet)
        
        # Mock article
        mock_article = MagicMock()
        mock_article.headline = "Test Headline"
        mock_article.symbols = ["AAPL"]
        mock_article.created_at = datetime(2023, 1, 1, 12, 0)
        mock_article.source = "Benzinga"
        # Mock content if needed
        mock_article.content = "Content"
        mock_article.url = "http://example.com"
        
        # Setup .data dictionary
        mock_result.data = {"news": [mock_article]}
        
        mock_instance.get_news.return_value = mock_result
        
        result = runner.invoke(cli, ["data", "news", "--symbols", "AAPL"])
        
        if result.exit_code != 0:
            print(result.output)

        assert result.exit_code == 0
        assert "Test Headline" in result.output
        assert "Benzinga" in result.output

