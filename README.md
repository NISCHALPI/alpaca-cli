# Alpaca CLI

A modern, feature-rich Command Line Interface for the Alpaca API, mirroring the structure of the Alpaca Python SDK.

## Features

- **Trading**: Full support for account management, orders, positions, assets, and watchlists.
- **Market Data**: Comprehensive access to Stock, Crypto, and Options data (historical & real-time).
- **Dashboard**: Interactive terminal dashboard for monitoring markets and your portfolio.
- **Paper & Live**: Easy switching between Paper and Live trading environments.
- **Scriptable**: JSON output support for easy integration with scripts and tools.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/alpaca-cli.git
cd alpaca-cli

# Install with dependencies
pip install -e .
```

## Configuration

Set your Alpaca API credentials using environment variables:

```bash
export APCA_API_KEY_ID="your_api_key"
export APCA_API_SECRET_KEY="your_api_secret"
export APCA_API_BASE_URL="https://paper-api.alpaca.markets" # or https://api.alpaca.markets
```

Or verify your configuration with:

```bash
alpaca-cli config
```

## Usage

The CLI is organized into two main groups: `trading` and `data`.

### Trading Commands

Interact with your account and place orders.

```bash
# Check account status
alpaca-cli trading account status

# List open positions
alpaca-cli trading positions list

# Place a market buy order
alpaca-cli trading orders buy market AAPL 10

# Place a limit sell order
alpaca-cli trading orders sell limit BTC/USD 0.5 --limit-price 30500

# Rebalance portfolio (from a weights file)
alpaca-cli trading orders rebalance targets.json
```

### Market Data Commands

Fetch historical and real-time market data.

```bash
# Get latest stock data
alpaca-cli data stock latest AAPL

# Get historical crypto bars
alpaca-cli data crypto bars BTC/USD --timeframe 1H --limit 10   

# Get options chain
alpaca-cli data options chain SPY

# Screen for market movers
alpaca-cli data screeners movers --top 10
```

### Quick Aliases

For common tasks, use top-level aliases:

- `alpaca-cli buy ...`  -> `trading orders buy market ...`
- `alpaca-cli sell ...` -> `trading orders sell market ...`
- `alpaca-cli pos`      -> `trading positions list`
- `alpaca-cli status`   -> `trading account status`
- `alpaca-cli quote ...`-> `data stock latest ...`
- `alpaca-cli clock`    -> `trading clock`

## Structure

The CLI structure mirrors the SDK:

- **`trading`**
    - `account`
    - `orders`
    - `positions`
    - `assets`
    - `watchlists`
    - `corporate-actions`
    - `contracts` (Options)
- **`data`**
    - `stock`
    - `crypto`
    - `options`
    - `news`
    - `corporate-actions`
    - `screeners`

## Development

Run tests:

```bash
pytest tests/unit
```
