# Alpaca CLI

A modern, feature-rich Command Line Interface for the Alpaca API, designed to mirror the structure of the Alpaca Python SDK.

## Features

- **Trading**: Full support for account management, orders, positions, assets, and watchlists.
- **Market Data**: Comprehensive access to Stock, Crypto, and Options data (historical & real-time).
- **Dashboard**: Interactive terminal dashboard for monitoring markets and your portfolio.
- **Paper & Live**: Easy switching between Paper and Live trading environments.
- **Scriptable**: JSON output support for easy integration with scripts and tools.

## Installation

### Using `uv` (Recommended)

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone https://github.com/nischalpi/alpaca-cli.git
cd alpaca-cli

# Install dependencies and the tool
uv sync
```

### Using `pip`

```bash
pip install .
```

## Configuration

The CLI needs your Alpaca API credentials to function. You can provide these via environment variables or a configuration file.

### Environment Variables

```bash
export APCA_API_KEY_ID="your_api_key_here"
export APCA_API_SECRET_KEY="your_api_secret_here"

# Optional: Default is Paper API
export APCA_API_BASE_URL="https://paper-api.alpaca.markets" 
# For Live trading:
# export APCA_API_BASE_URL="https://api.alpaca.markets"
```

### Configuration File

Run the config wizard to set up your credentials interactively:

```bash
alpaca-cli config
```

Or manually create `~/.alpaca.json`:

```json
{
    "key": "your_api_key",
    "secret": "your_api_secret",
    "paper_endpoint": "https://paper-api.alpaca.markets",
    "live_endpoint": "https://api.alpaca.markets"
}
```

## Usage

The CLI is organized into two main groups: `trading` and `data`.

### Trading Commands

Interact with your account, manage positions, and handle orders.

#### Account & Positions

```bash
# Check account status (Equity, Buying Power, P/L)
alpaca-cli trading account status

# List all open positions
alpaca-cli trading positions list

# Close all positions (Liquidate)
alpaca-cli trading positions close-all --cancel-orders
```

#### Orders

```bash
# Place a Market Buy Order (Day)
alpaca-cli trading orders buy market AAPL 10

# Place a Limit Sell Order
alpaca-cli trading orders sell limit BTC/USD 0.5 --limit-price 65000

# Place a Stop Loss Order
alpaca-cli trading orders buy stop TSLA 5 200

# List Open Orders
alpaca-cli trading orders list --status OPEN

# Cancel a specific order
alpaca-cli trading orders cancel <order_id> 

# Cancel ALL open orders
alpaca-cli trading orders cancel --all
```

#### Rebalancing

Rebalance your portfolio based on a target weights file.

```bash
# rebalance.json example: {"AAPL": 0.5, "MSFT": 0.3, "CASH": 0.2}
alpaca-cli trading orders rebalance rebalance.json
```

### Market Data Commands

Fetch historical and real-time market data.

#### Stocks

```bash
# Get latest quote and bar for a stock
alpaca-cli data stock latest AAPL

# Get historical bars (Hourly)
alpaca-cli data stock bars SPY --timeframe 1H --limit 20
```

#### Crypto

```bash
# Get latest crypto pricing
alpaca-cli data crypto latest BTC/USD ETH/USD

# Get historical bars
alpaca-cli data crypto bars ETH/USD --timeframe 15Min --start 2024-01-01
```

#### Options

```bash
# Get Option Chain for a symbol
alpaca-cli data options chain AMD

# Get latest option quotes
alpaca-cli data options quotes "AMD241220C00150000"
```

#### News & Screeners

```bash
# Get latest market news
alpaca-cli data news --limit 5

# Screen for top market movers (gainers/losers)
alpaca-cli data screeners movers
```

### Quick Aliases

For common tasks, use these top-level shortcuts:

- `alpaca-cli buy ...`  -> `trading orders buy market ...`
- `alpaca-cli sell ...` -> `trading orders sell market ...`
- `alpaca-cli pos`      -> `trading positions list`
- `alpaca-cli status`   -> `trading account status`
- `alpaca-cli quote ...`-> `data stock latest ...`
- `alpaca-cli clock`    -> `trading clock`
- `alpaca-cli dashboard`-> Launch interactive dashboard

## Development

### Running Tests

We use `pytest` for unit and integration testing.

```bash
uv run pytest
```

### Code Formatting

This project uses standard Python formatting tools.

```bash
uv run ruff check .
```

## License

MIT
