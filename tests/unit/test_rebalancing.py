"""Unit tests for calculate_rebalancing_orders function."""

import pytest

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


class TestMinimalOrderCalculation:
    """Tests to verify minimal order calculation - only adjusts what's needed."""

    def test_perfectly_balanced_portfolio_no_orders(self):
        """A perfectly balanced portfolio should generate no orders."""
        # Portfolio: 50% AAPL, 50% MSFT at $100 each
        # Equity: $10,000 -> 50 shares each
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={"AAPL": 50, "MSFT": 50},
            target_weights={"AAPL": 0.5, "MSFT": 0.5},
            current_prices={"AAPL": 100.0, "MSFT": 100.0},
        )

        assert len(orders) == 0, "Balanced portfolio should generate no orders"

    def test_partial_rebalance_only_adjusts_needed_positions(self):
        """Only positions that deviate from target should generate orders."""
        # AAPL is at target (50%), MSFT needs adjustment
        # Equity: $10,000
        # AAPL: 50 shares @ $100 = $5000 (50%) - OK
        # MSFT: 30 shares @ $100 = $3000 (30%) - needs to be 20%
        # GOOGL: 0 shares, needs to be 20% = $2000 / $100 = 20 shares
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={"AAPL": 50, "MSFT": 30},
            target_weights={"AAPL": 0.5, "MSFT": 0.2, "GOOGL": 0.2, "CASH": 0.1},
            current_prices={"AAPL": 100.0, "MSFT": 100.0, "GOOGL": 100.0},
        )

        # AAPL should have NO orders (already at 50%)
        aapl_orders = [o for o in orders if o["symbol"] == "AAPL"]
        assert len(aapl_orders) == 0, "AAPL is at target, should have no orders"

        # MSFT should have SELL order (30% -> 20% = sell 10 shares)
        msft_orders = [o for o in orders if o["symbol"] == "MSFT"]
        assert len(msft_orders) == 1
        assert msft_orders[0]["side"] == "sell"
        assert abs(msft_orders[0]["qty"] - 10) < 0.01  # Sell 10 shares

        # GOOGL should have BUY order (0% -> 20% = buy 20 shares)
        googl_orders = [o for o in orders if o["symbol"] == "GOOGL"]
        assert len(googl_orders) == 1
        assert googl_orders[0]["side"] == "buy"
        assert abs(googl_orders[0]["qty"] - 20) < 0.01  # Buy 20 shares

    def test_correct_quantity_calculation(self):
        """Verify exact quantity calculations for rebalancing."""
        # Equity: $50,000
        # Current: AAPL 100 shares @ $150 = $15,000 (30%)
        # Target: AAPL 40% = $20,000 / $150 = 133.33 shares
        # Need to BUY: 133.33 - 100 = 33.33 shares
        orders = calculate_rebalancing_orders(
            current_equity=50000,
            current_positions={"AAPL": 100},
            target_weights={"AAPL": 0.4, "CASH": 0.6},
            current_prices={"AAPL": 150.0},
        )

        assert len(orders) == 1
        assert orders[0]["symbol"] == "AAPL"
        assert orders[0]["side"] == "buy"
        # Expected: ($50000 * 0.4) / $150 - 100 = 133.33 - 100 = 33.33
        expected_qty = (50000 * 0.4) / 150 - 100
        assert abs(orders[0]["qty"] - expected_qty) < 0.01

    def test_mixed_buy_sell_orders(self):
        """Test a scenario requiring both buy and sell orders."""
        # Equity: $10,000
        # Current: AAPL 40 @ $100 = $4000 (40%), MSFT 60 @ $100 = $6000 (60%)
        # Target: AAPL 60%, MSFT 40%
        # Need: AAPL buy 20, MSFT sell 20
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={"AAPL": 40, "MSFT": 60},
            target_weights={"AAPL": 0.6, "MSFT": 0.4},
            current_prices={"AAPL": 100.0, "MSFT": 100.0},
        )

        assert len(orders) == 2

        aapl_order = next(o for o in orders if o["symbol"] == "AAPL")
        msft_order = next(o for o in orders if o["symbol"] == "MSFT")

        assert aapl_order["side"] == "buy"
        assert abs(aapl_order["qty"] - 20) < 0.01

        assert msft_order["side"] == "sell"
        assert abs(msft_order["qty"] - 20) < 0.01

    def test_accounts_for_existing_positions_not_in_target(self):
        """Positions not in target should be liquidated."""
        # Current: AAPL 50, MSFT 50, GOOGL 10 (not in target)
        # Target: AAPL 50%, MSFT 50% (no GOOGL)
        # GOOGL should be sold
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={"AAPL": 50, "MSFT": 50, "GOOGL": 10},
            target_weights={"AAPL": 0.5, "MSFT": 0.5},
            current_prices={"AAPL": 100.0, "MSFT": 100.0, "GOOGL": 100.0},
        )

        # GOOGL should be liquidated (not in target, so weight=0)
        googl_orders = [o for o in orders if o["symbol"] == "GOOGL"]
        assert len(googl_orders) == 1
        assert googl_orders[0]["side"] == "sell"
        assert abs(googl_orders[0]["qty"] - 10) < 0.01

    def test_large_portfolio_minimal_orders(self):
        """Test with a larger portfolio - only deviant positions should trade."""
        # 5-stock portfolio, only 2 need adjustment
        current = {
            "AAPL": 100,  # 20% at $100 - OK
            "MSFT": 100,  # 20% at $100 - OK
            "GOOGL": 150,  # 30% at $100 - needs to be 20% (sell 50)
            "AMZN": 50,  # 10% at $100 - needs to be 20% (buy 50)
            "NVDA": 100,  # 20% at $100 - OK
        }
        target = {
            "AAPL": 0.2,
            "MSFT": 0.2,
            "GOOGL": 0.2,
            "AMZN": 0.2,
            "NVDA": 0.2,
        }
        prices = {sym: 100.0 for sym in current.keys()}

        # Total equity: 500 shares * $100 = $50,000
        orders = calculate_rebalancing_orders(
            current_equity=50000,
            current_positions=current,
            target_weights=target,
            current_prices=prices,
        )

        # Should only have 2 orders: GOOGL sell, AMZN buy
        assert len(orders) == 2

        symbols_with_orders = {o["symbol"] for o in orders}
        assert symbols_with_orders == {"GOOGL", "AMZN"}

        googl_order = next(o for o in orders if o["symbol"] == "GOOGL")
        assert googl_order["side"] == "sell"
        assert abs(googl_order["qty"] - 50) < 0.01

        amzn_order = next(o for o in orders if o["symbol"] == "AMZN")
        assert amzn_order["side"] == "buy"
        assert abs(amzn_order["qty"] - 50) < 0.01

    def test_fractional_shares_precision(self):
        """Test that fractional share quantities are calculated correctly."""
        # Equity: $10,000
        # Target: AAPL 33.33%
        # Expected qty: (10000 * 0.3333) / 175 = 19.047 shares
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={},
            target_weights={"AAPL": 0.3333, "CASH": 0.6667},
            current_prices={"AAPL": 175.0},
        )

        assert len(orders) == 1
        expected_qty = (10000 * 0.3333) / 175
        assert abs(orders[0]["qty"] - expected_qty) < 0.001

    def test_sell_before_buy_ordering_in_output(self):
        """The function returns raw orders - verify both buy and sell present."""
        orders = calculate_rebalancing_orders(
            current_equity=10000,
            current_positions={"AAPL": 80, "MSFT": 20},  # AAPL overweight
            target_weights={"AAPL": 0.3, "MSFT": 0.7},  # Flip weights
            current_prices={"AAPL": 100.0, "MSFT": 100.0},
        )

        buy_orders = [o for o in orders if o["side"] == "buy"]
        sell_orders = [o for o in orders if o["side"] == "sell"]

        assert len(buy_orders) >= 1
        assert len(sell_orders) >= 1
