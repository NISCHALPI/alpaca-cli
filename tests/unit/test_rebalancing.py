"""Unit tests for calculate_rebalancing_orders function."""

import pytest
import math
from decimal import Decimal

from alpaca_cli.cli.utils import calculate_rebalancing_orders, validate_not_nan


class TestValidateNotNan:
    """Tests for validate_not_nan helper function."""

    def test_valid_number(self):
        """Normal numbers should pass."""
        validate_not_nan("test", 100.0)
        validate_not_nan("test", 0)
        validate_not_nan("test", -50.5)

    def test_nan_raises_error(self):
        """NaN values should raise ValueError."""
        with pytest.raises(ValueError, match="is NaN"):
            validate_not_nan("test_field", float("nan"))

    def test_none_raises_error(self):
        """None values should raise ValueError."""
        with pytest.raises(ValueError, match="is None"):
            validate_not_nan("test_field", None)


class TestCalculateRebalancingOrders:
    """Tests for calculate_rebalancing_orders function."""

    def test_basic_rebalance(self, sample_positions, sample_prices):
        """Test basic rebalancing calculation."""
        target_weights = {
            "AAPL": 0.5,
            "MSFT": 0.3,
            "CASH": 0.2,
        }
        equity = 10000.0

        orders = calculate_rebalancing_orders(
            current_equity=equity,
            current_positions=sample_positions,
            target_weights=target_weights,
            current_prices=sample_prices,
        )

        assert isinstance(orders, list)
        for order in orders:
            assert "symbol" in order
            assert "qty" in order
            assert "side" in order
            assert "type" in order

    def test_zero_equity_raises_error(self):
        """Zero equity should raise ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculate_rebalancing_orders(
                current_equity=0,
                current_positions={"AAPL": 10},
                target_weights={"AAPL": 0.5},
                current_prices={"AAPL": 150.0},
            )

    def test_negative_equity_raises_error(self):
        """Negative equity should raise ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculate_rebalancing_orders(
                current_equity=-1000,
                current_positions={"AAPL": 10},
                target_weights={"AAPL": 0.5},
                current_prices={"AAPL": 150.0},
            )

    def test_nan_price_raises_error(self):
        """NaN price should raise ValueError."""
        with pytest.raises(ValueError, match="is NaN"):
            calculate_rebalancing_orders(
                current_equity=10000,
                current_positions={"AAPL": 10},
                target_weights={"AAPL": 0.5},
                current_prices={"AAPL": float("nan")},
            )

    def test_zero_price_raises_error(self):
        """Zero price should raise ValueError."""
        with pytest.raises(ValueError, match="Price for AAPL is 0"):
            calculate_rebalancing_orders(
                current_equity=10000,
                current_positions={"AAPL": 10},
                target_weights={"AAPL": 0.5},
                current_prices={"AAPL": 0},
            )

    def test_short_position_blocked_by_default(self):
        """Short positions should raise error when not allowed."""
        with pytest.raises(ValueError, match="illegal short position"):
            calculate_rebalancing_orders(
                current_equity=10000,
                current_positions={"AAPL": 0},
                target_weights={"AAPL": -0.1},  # Negative weight implies short
                current_prices={"AAPL": 150.0},
            )

    def test_short_position_allowed_when_enabled(self):
        """Short positions should be allowed when allow_short=True."""
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={"AAPL": 10},
            target_weights={"AAPL": -0.1},
            current_prices={"AAPL": 150.0},
            allow_short=True,
        )

        # Should have a sell order
        sell_orders = [o for o in orders if o["side"] == "sell"]
        assert len(sell_orders) >= 1

    def test_cash_weight_ignored(self):
        """CASH weight should not generate orders."""
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={"AAPL": 10},
            target_weights={"AAPL": 0.5, "CASH": 0.5},
            current_prices={"AAPL": 150.0},
        )

        # No order for CASH
        cash_orders = [o for o in orders if o["symbol"] == "CASH"]
        assert len(cash_orders) == 0

    def test_liquidation_order(self):
        """Weight of 0 should generate sell order to close position."""
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={"AAPL": 10},
            target_weights={"AAPL": 0, "CASH": 1.0},
            current_prices={"AAPL": 150.0},
        )

        # Should have a sell order for AAPL
        aapl_orders = [o for o in orders if o["symbol"] == "AAPL"]
        assert len(aapl_orders) == 1
        assert aapl_orders[0]["side"] == "sell"

    def test_new_position_order(self, sample_prices):
        """New symbol in target should generate buy order."""
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={},  # No positions
            target_weights={"AAPL": 0.5, "CASH": 0.5},
            current_prices=sample_prices,
        )

        # Should have a buy order for AAPL
        aapl_orders = [o for o in orders if o["symbol"] == "AAPL"]
        assert len(aapl_orders) == 1
        assert aapl_orders[0]["side"] == "buy"

    def test_dust_threshold_skips_tiny_trades(self):
        """Very small trades should be skipped due to dust threshold."""
        # Position almost at target weight - tiny adjustment needed
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={"AAPL": 33.33},  # ~50% of 10k at $150
            target_weights={"AAPL": 0.5, "CASH": 0.5},
            current_prices={"AAPL": 150.0},
        )

        # The difference is tiny, should be skipped
        # 33.33 * 150 = 4999.5, target 5000, diff = 0.5 / 150 = 0.00333 shares
        aapl_orders = [o for o in orders if o["symbol"] == "AAPL"]
        # Depending on threshold, may or may not have order
        # At MIN_TRADE_VALUE_THRESHOLD = $1, 0.00333 shares * $150 = $0.50 < $1
        assert len(aapl_orders) == 0
