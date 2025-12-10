import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from alpaca_cli.cli.main import cli
from alpaca.trading.models import TradeAccount, Position, Order
from alpaca.trading.enums import (
    AccountStatus,
    OrderSide,
    OrderType,
    OrderStatus,
    TimeInForce,
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_trading_client():
    with patch("alpaca_cli.cli.groups.trading.account.get_trading_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_account_status(runner, mock_trading_client):
    """Test 'trading account status' command."""
    # Mock account response
    mock_account = MagicMock(spec=TradeAccount)
    mock_account.id = "test-account-id"
    mock_account.account_number = "PA123456"
    mock_account.status = AccountStatus.ACTIVE
    mock_account.currency = "USD"
    mock_account.buying_power = "100000.00"
    mock_account.cash = "50000.00"
    mock_account.equity = "100000.00"
    mock_account.portfolio_value = "100000.00"
    mock_account.pattern_day_trader = False
    mock_account.trade_suspended_by_user = False
    mock_account.trading_blocked = False
    mock_account.transfers_blocked = False
    mock_account.account_blocked = False
    mock_account.shorting_enabled = True
    mock_account.multiplier = "4"
    mock_account.long_market_value = "0"
    mock_account.short_market_value = "0"
    mock_account.initial_margin = "0"
    mock_account.maintenance_margin = "0"
    mock_account.last_equity = "100000"
    mock_account.daytrade_count = 0
    mock_account.created_at = "2023-01-01"

    # Missing fields causing AttributeErrors
    mock_account.regt_buying_power = "100000.00"
    mock_account.options_buying_power = "100000.00"
    mock_account.daytrade_buying_power = "100000.00"
    mock_account.effective_buying_power = "100000.00"
    mock_account.non_marginable_buying_power = "100000.00"
    mock_account.bod_dtbp = "0"
    mock_account.cdt = "0"
    mock_account.pending_transfer_in = "0"
    mock_account.pending_transfer_out = "0"
    mock_account.sma = "0"
    mock_account.accrued_fees = "0"

    # Needs to support dict access because print_table iterates properties sometimes?
    # Actually explicit access in account.py: ["ID", acc.id]

    mock_trading_client.get_account.return_value = mock_account

    result = runner.invoke(cli, ["trading", "account", "status"])

    if result.exit_code != 0:
        print(result.output)

    assert result.exit_code == 0
    assert "Account Details" in result.output
    assert "ACTIVE" in result.output
    assert "100,000.00" in result.output


def test_positions_list(runner):
    """Test 'trading positions list' command."""
    with patch(
        "alpaca_cli.cli.groups.trading.positions.get_trading_client"
    ) as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock positions response
        mock_pos = MagicMock(spec=Position)
        mock_pos.symbol = "AAPL"
        mock_pos.qty = "10"
        mock_pos.side = MagicMock()
        mock_pos.side.value = "long"

        mock_pos.avg_entry_price = "150.00"
        mock_pos.current_price = "155.00"
        mock_pos.market_value = "1550.00"
        mock_pos.unrealized_pl = "50.00"
        mock_pos.unrealized_plpc = (
            0.033  # Needs to be float for formatting logic usually
        )

        mock_client.get_all_positions.return_value = [mock_pos]

        result = runner.invoke(cli, ["trading", "positions", "list"])

        assert result.exit_code == 0
        assert "AAPL" in result.output
        assert "1,550.00" in result.output


def test_orders_buy_market(runner):
    """Test 'trading orders buy market' command."""
    with (
        patch(
            "alpaca_cli.cli.groups.trading.orders.get_trading_client"
        ) as mock_get_client,
        patch("alpaca_cli.cli.groups.trading.orders.logger") as mock_logger,
    ):

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock order response
        mock_order = MagicMock(spec=Order)
        mock_order.id = "test-order-id"
        mock_order.status = OrderStatus.NEW

        mock_client.submit_order.return_value = mock_order

        result = runner.invoke(
            cli, ["trading", "orders", "buy", "market", "AAPL", "10"]
        )

        assert result.exit_code == 0

        # Verify logger was called with success message
        # logger.info(f"Order submitted successfully: {order.id}")
        mock_logger.info.assert_any_call("Order submitted successfully: test-order-id")

        # Verify call args
        mock_client.submit_order.assert_called_once()
        call_args = mock_client.submit_order.call_args[1]
        assert call_args["order_data"].symbol == "AAPL"
        assert float(call_args["order_data"].qty) == 10.0
        assert call_args["order_data"].type == OrderType.MARKET
