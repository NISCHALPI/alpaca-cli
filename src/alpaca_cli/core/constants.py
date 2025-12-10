"""Constants and configuration values for Alpaca CLI."""

from decimal import Decimal

# Rebalancing thresholds
MIN_TRADE_VALUE_THRESHOLD = Decimal("1.00")  # Minimum trade value in USD
MIN_QTY_THRESHOLD = Decimal("0.000001")  # Minimum quantity threshold
PRECISION = Decimal("0.00000001")  # Decimal precision for calculations

# Weight validation
WEIGHT_TOLERANCE = 0.01  # 1% tolerance for weight sum (0.99 to 1.01)

# API defaults
DEFAULT_ORDER_LIMIT = 50
MAX_ORDER_LIMIT = 500
DEFAULT_NEWS_LIMIT = 10
MAX_NEWS_LIMIT = 50

# Dashboard refresh
DASHBOARD_REFRESH_SECONDS = 5
MAX_POSITIONS_DISPLAY = 8

# Market indices for dashboard
MARKET_INDICES = ["SPY", "QQQ", "DIA", "IWM"]
