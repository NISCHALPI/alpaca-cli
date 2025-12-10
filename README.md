<h1 align="center">Alpaca CLI</h1>

<p align="center">
  <strong>A modern, feature-rich Command Line Interface for the Alpaca Trading API</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#command-reference">Command Reference</a> •
  <a href="#examples">Examples</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.14+-blue.svg" alt="Python 3.14+"/>
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License"/>
  <img src="https://img.shields.io/badge/alpaca--py-0.43.2+-orange.svg" alt="Alpaca SDK"/>
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style: Black"/>
    <img src="https://img.shields.io/badge/linted%20with-Ruff-ff69b4.svg" alt="Linted with Ruff"/>
</p>

---

## 📸 Screenshots

### Interactive Dashboard
Real-time portfolio monitoring with account status, positions, orders, and market clock.

![Dashboard](assets/dashboard.png)

### Account Status
Comprehensive account overview with equity, buying power, and P/L metrics.

![Account Status](assets/account_status.png)

### Portfolio Positions
Detailed view of all open positions with real-time P/L tracking.

![Positions](assets/positions.png)

### Market Data
Access to historical and real-time stock, crypto, and options data.

![Market Data](assets/marketdata.png)

---

<a id="features"></a>

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Trading** | Full support for account management, orders, positions, assets, and watchlists |
| 📈 **Market Data** | Comprehensive access to Stock, Crypto, and Options data (historical & real-time) |
| 🎯 **Dashboard** | Interactive terminal dashboard for monitoring markets and your portfolio |
| 📰 **News** | Real-time market news filtered by symbols |
| 🔍 **Screeners** | Market movers and most active stocks |
| 🔄 **Rebalancing** | Portfolio rebalancing with target weights |
| 📡 **Streaming** | Real-time data streaming for quotes, trades, and order updates |
| 🏦 **Paper & Live** | Easy switching between Paper and Live trading environments |
| 🔧 **Scriptable** | JSON/CSV output support for easy integration with scripts and tools |
| ⚡ **Quick Aliases** | Fast commands: `buy`, `sell`, `pos`, `status`, `quote`, `clock` |

---

<a id="installation"></a>

## 📦 Installation

### Using `uv` (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager.

```bash
# Clone the repository
git clone https://github.com/nischalpi/alpaca-cli.git
cd alpaca-cli

# Install dependencies and the CLI tool
uv sync
```

### Using `pip`

```bash
# Clone and install
git clone https://github.com/nischalpi/alpaca-cli.git
cd alpaca-cli
pip install .
```

### Verify Installation

```bash
alpaca-cli --version
alpaca-cli --help
```

---

<a id="configuration"></a>

## ⚙️ Configuration

The CLI requires your Alpaca API credentials. You can configure them in two ways:

### Option 1: Environment Variables

```bash
# Required
export APCA_API_KEY_ID="your_api_key_here"
export APCA_API_SECRET_KEY="your_api_secret_here"

# Optional: Trading endpoint (defaults to Paper)
export APCA_API_BASE_URL="https://paper-api.alpaca.markets"

# For Live trading:
# export APCA_API_BASE_URL="https://api.alpaca.markets"
```

Add these to your `~/.bashrc` or `~/.zshrc` for persistence.

### Option 2: Configuration File (Recommended)

Create `<home>/.alpaca.json`:

```json
{
    "key": "your_api_key",
    "secret": "your_api_secret",
    "paper_endpoint": "https://paper-api.alpaca.markets",
    "live_endpoint": "https://api.alpaca.markets"
}
```

### Configuration Commands

```bash
# Show current configuration
alpaca-cli config show

# Verify API connectivity
alpaca-cli config verify

# Switch between Paper and Live trading
alpaca-cli config set-mode paper
alpaca-cli config set-mode live
```

### Shell Completion

Enable tab completion for your shell:

```bash
# Bash
eval "$(_ALPACA_CLI_COMPLETE=bash_source alpaca-cli)"

# Zsh
eval "$(_ALPACA_CLI_COMPLETE=zsh_source alpaca-cli)"

# Fish
_ALPACA_CLI_COMPLETE=fish_source alpaca-cli | source
```

Add to your shell profile for persistence.

---

<a id="quick-start"></a>

## 🚀 Quick Start

### Check Account Status

```bash
# Using quick alias
alpaca-cli status

# Or full command
alpaca-cli trading account status
```

### Get a Stock Quote

```bash
# Quick quote
alpaca-cli quote AAPL

# Detailed latest data
alpaca-cli data stock latest AAPL
```

### Place Orders

```bash
# Quick buy (market order)
alpaca-cli buy AAPL 10

# Quick sell (market order)
alpaca-cli sell AAPL 10

# Buy by dollar amount
alpaca-cli buy AAPL --notional 1000
```

### View Positions

```bash
# Quick alias
alpaca-cli pos

# Full command
alpaca-cli trading positions list
```

### Launch Dashboard

```bash
# One-time view
alpaca-cli dashboard

# Live updating dashboard (refreshes every 5 seconds)
alpaca-cli dashboard --watch
```

---

<a id="command-reference"></a>

## 📚 Command Reference

### Command Structure

```
alpaca-cli
├── trading          # Trading operations
│   ├── account      # Account management
│   ├── positions    # Position management
│   ├── orders       # Order management
│   ├── assets       # Asset lookup
│   ├── watchlists   # Watchlist management
│   ├── contracts    # Option contracts
│   ├── corporate-actions
│   ├── calendar     # Market calendar
│   ├── clock        # Market clock
│   └── stream       # Real-time order updates
│
├── data             # Market data
│   ├── stock        # Stock data
│   ├── crypto       # Crypto data
│   ├── options      # Options data
│   ├── news         # Market news
│   ├── screeners    # Market screeners
│   └── corporate-actions
│
├── config           # CLI configuration
├── dashboard        # Interactive dashboard
│
└── Quick Aliases
    ├── buy          # → trading orders buy market
    ├── sell         # → trading orders sell market
    ├── pos          # → trading positions list
    ├── status       # → trading account status
    ├── quote        # → data stock latest
    └── clock        # → trading clock
```

---

### 💼 Trading Commands

#### Account Management

```bash
# Get account status (equity, buying power, P/L)
alpaca-cli trading account status

# Get account configuration
alpaca-cli trading account config

# Get portfolio history
alpaca-cli trading account history --period 1M --timeframe 1D
alpaca-cli trading account history --period 1W --extended-hours
```

#### Position Management

```bash
# List all open positions
alpaca-cli trading positions list
alpaca-cli trading positions list --format json

# Get specific position
alpaca-cli trading positions get AAPL

# Close position
alpaca-cli trading positions close AAPL
alpaca-cli trading positions close AAPL --qty 5      # Partial close
alpaca-cli trading positions close AAPL --percent 50 # Close 50%

# Close ALL positions (liquidate)
alpaca-cli trading positions close --all

# Exercise option position
alpaca-cli trading positions exercise AAPL250117C00150000
```

#### Order Management

##### Listing Orders

```bash
# List open orders
alpaca-cli trading orders list

# List with filters
alpaca-cli trading orders list --status closed --limit 100
alpaca-cli trading orders list --side buy --symbols AAPL,MSFT
alpaca-cli trading orders list --days 7 --direction desc

# Export orders
alpaca-cli trading orders list --format json --export orders.json
alpaca-cli trading orders list --format csv --export orders.csv
```

##### Placing Buy Orders

```bash
# Market order
alpaca-cli trading orders buy market AAPL 10
alpaca-cli trading orders buy market AAPL --notional 1000  # $1000 worth

# Limit order
alpaca-cli trading orders buy limit AAPL 10 150.00
alpaca-cli trading orders buy limit AAPL 10 150.00 --tif gtc
alpaca-cli trading orders buy limit AAPL 10 150.00 --extended-hours

# Stop order
alpaca-cli trading orders buy stop AAPL 10 155.00

# Stop-limit order
alpaca-cli trading orders buy stop AAPL 10 155.00 --limit 156.00

# Trailing stop order
alpaca-cli trading orders buy trailing AAPL 10 --trail-price 5.00
alpaca-cli trading orders buy trailing AAPL 10 --trail-percent 2.5

# Bracket order (with take-profit and stop-loss)
alpaca-cli trading orders buy market AAPL 10 \
  --take-profit 180.00 \
  --stop-loss 140.00 \
  --stop-loss-limit 139.00
```

##### Placing Sell Orders

```bash
# Market order
alpaca-cli trading orders sell market AAPL 10

# Limit order
alpaca-cli trading orders sell limit AAPL 10 160.00

# Stop order (stop-loss)
alpaca-cli trading orders sell stop AAPL 10 145.00

# Stop-limit order
alpaca-cli trading orders sell stop AAPL 10 145.00 --limit 144.00

# Trailing stop order
alpaca-cli trading orders sell trailing AAPL 10 --trail-percent 3.0
```

##### Managing Orders

```bash
# Get order details
alpaca-cli trading orders get <order_id>
alpaca-cli trading orders get --client-order-id my-order-123

# Modify/replace order
alpaca-cli trading orders modify <order_id> --qty 15
alpaca-cli trading orders modify <order_id> --limit 155.00
alpaca-cli trading orders modify <order_id> --tif gtc

# Cancel order
alpaca-cli trading orders cancel <order_id>

# Cancel ALL open orders
alpaca-cli trading orders cancel --all
```

##### Portfolio Rebalancing

```bash
# Create target weights file (weights.json)
# {
#   "AAPL": 0.30,
#   "MSFT": 0.30,
#   "GOOGL": 0.20,
#   "CASH": 0.20
# }

# Dry run (preview orders)
alpaca-cli trading orders rebalance weights.json --dry-run

# Execute rebalancing
alpaca-cli trading orders rebalance weights.json --execute

# With options
alpaca-cli trading orders rebalance weights.json --execute \
  --order-type limit \
  --tif day \
  --yes  # Skip confirmation
```

#### Asset Lookup

```bash
# List all tradable assets
alpaca-cli trading assets list
alpaca-cli trading assets list --class us_equity --status active
alpaca-cli trading assets list --exchange NYSE --tradable

# Get specific asset details
alpaca-cli trading assets get AAPL
alpaca-cli trading assets get b28f4066-5c6d-479b-a2af-85dc1a8f16fb  # by ID
```

#### Watchlist Management

```bash
# List all watchlists
alpaca-cli trading watchlists list

# Show watchlist contents
alpaca-cli trading watchlists show "My Watchlist"
alpaca-cli trading watchlists show <watchlist_id>

# Create watchlist
alpaca-cli trading watchlists create "Tech Stocks" --symbols AAPL,MSFT,GOOGL

# Update watchlist
alpaca-cli trading watchlists update "Tech Stocks" --name "Tech Giants"
alpaca-cli trading watchlists update "Tech Stocks" --symbols AAPL,MSFT,GOOGL,AMZN

# Add/remove symbols
alpaca-cli trading watchlists add "Tech Stocks" NVDA
alpaca-cli trading watchlists remove "Tech Stocks" AMZN

# Delete watchlist
alpaca-cli trading watchlists delete "Tech Stocks"
```

#### Market Clock & Calendar

```bash
# Get current market clock
alpaca-cli trading clock
alpaca-cli clock  # Quick alias

# Get market calendar
alpaca-cli trading calendar
alpaca-cli trading calendar --start 2024-01-01 --end 2024-12-31
```

#### Real-time Order Stream

```bash
# Stream order updates
alpaca-cli trading stream
```

---

### 📈 Data Commands

#### Stock Data

```bash
# Latest quote, trade, and bar
alpaca-cli data stock latest AAPL
alpaca-cli data stock latest AAPL,MSFT,GOOGL  # Multiple symbols

# Historical bars (OHLCV)
alpaca-cli data stock bars AAPL --timeframe 1Day --start 2024-01-01
alpaca-cli data stock bars AAPL --timeframe 1Hour --limit 100
alpaca-cli data stock bars AAPL,MSFT --timeframe 15Min --format json

# Historical quotes (NBBO)
alpaca-cli data stock quotes AAPL --start 2024-01-01 --limit 1000

# Historical trades (time & sales)
alpaca-cli data stock trades AAPL --start 2024-01-01

# Snapshot (comprehensive current data)
alpaca-cli data stock snapshot AAPL
alpaca-cli data stock snapshot AAPL,MSFT,GOOGL

# Stream live data
alpaca-cli data stock stream AAPL --quotes --trades
alpaca-cli data stock stream AAPL,MSFT --bars
```

#### Crypto Data

```bash
# Latest data
alpaca-cli data crypto latest BTC/USD
alpaca-cli data crypto latest BTC/USD,ETH/USD

# Historical bars
alpaca-cli data crypto bars BTC/USD --timeframe 1Hour --start 2024-01-01

# Historical quotes
alpaca-cli data crypto quotes BTC/USD --limit 100

# Historical trades
alpaca-cli data crypto trades BTC/USD --start 2024-01-01

# Orderbook (bid/ask depth)
alpaca-cli data crypto orderbook BTC/USD

# Snapshot
alpaca-cli data crypto snapshot BTC/USD

# Stream live data
alpaca-cli data crypto stream BTC/USD --quotes --trades
```

#### Options Data

```bash
# Get option chain
alpaca-cli data options chain AAPL
alpaca-cli data options chain AAPL --expiration 2024-12-20
alpaca-cli data options chain AAPL --type call --strike-min 150 --strike-max 200

# Historical bars
alpaca-cli data options bars AAPL250117C00150000 --timeframe 1Day

# Historical trades
alpaca-cli data options trades AAPL250117C00150000

# Latest quote/trade
alpaca-cli data options latest AAPL250117C00150000

# Snapshot with Greeks
alpaca-cli data options snapshot AAPL250117C00150000

# Exchange mappings
alpaca-cli data options exchanges
```

#### Market News

```bash
# Get latest news
alpaca-cli data news

# Filter by symbols
alpaca-cli data news --symbols AAPL,MSFT

# Date range
alpaca-cli data news --start 2024-01-01 --end 2024-01-31

# Include full content
alpaca-cli data news --symbols AAPL --include-content --limit 5
```

#### Market Screeners

```bash
# Top movers (gainers/losers)
alpaca-cli data screeners movers
alpaca-cli data screeners movers --top 20

# Most active stocks
alpaca-cli data screeners actives
alpaca-cli data screeners actives --top 10
```

#### Corporate Actions

```bash
# Get corporate actions data
alpaca-cli data corporate-actions --symbols AAPL
alpaca-cli data corporate-actions --types dividend,split
```

---

### 🎛️ Configuration Commands

```bash
# Show current configuration
alpaca-cli config show

# Verify API connectivity
alpaca-cli config verify

# Set trading mode
alpaca-cli config set-mode paper
alpaca-cli config set-mode live
```

---

### 📊 Dashboard

```bash
# Static dashboard
alpaca-cli dashboard

# Live updating dashboard
alpaca-cli dashboard --watch
alpaca-cli dashboard -w

# Custom refresh interval
alpaca-cli dashboard --watch --interval 10
alpaca-cli dashboard -w -i 10

# Compact mode (for smaller terminals)
alpaca-cli dashboard --compact
alpaca-cli dashboard -c
```

---

<a id="examples"></a>

## 💡 Examples

### Day Trading Workflow

```bash
# Morning: Check market status and account
alpaca-cli clock
alpaca-cli status

# Check pre-market movers
alpaca-cli data screeners movers

# Get news for symbols of interest
alpaca-cli data news --symbols AAPL,TSLA

# Get current quotes
alpaca-cli quote AAPL TSLA

# Place a buy order
alpaca-cli buy AAPL 10

# Monitor positions throughout the day
alpaca-cli dashboard --watch

# End of day: Close all positions
alpaca-cli trading positions close --all
```

### Building a Watchlist

```bash
# Create a watchlist
alpaca-cli trading watchlists create "Day Trading" --symbols SPY,QQQ,AAPL,TSLA,NVDA

# Add more symbols
alpaca-cli trading watchlists add "Day Trading" AMD
alpaca-cli trading watchlists add "Day Trading" META

# View watchlist
alpaca-cli trading watchlists show "Day Trading"
```

### Bracket Order (Entry + Take Profit + Stop Loss)

```bash
# Buy with automatic profit target and stop loss
alpaca-cli trading orders buy market AAPL 100 \
  --take-profit 185.00 \
  --stop-loss 165.00
```

### Export Data for Analysis

```bash
# Export historical data to CSV
alpaca-cli data stock bars AAPL --timeframe 1Day --start 2024-01-01 \
  --format csv --export aapl_daily.csv

# Export orders history
alpaca-cli trading orders list --status all --days 30 \
  --format json --export orders_history.json
```

### Automated Rebalancing Script

```bash
#!/bin/bash
# rebalance.sh

# Define target allocation
cat > /tmp/weights.json << EOF
{
  "SPY": 0.40,
  "QQQ": 0.30,
  "BND": 0.20,
  "CASH": 0.10
}
EOF

# Run rebalancing (dry-run first)
echo "Preview rebalancing orders:"
alpaca-cli trading orders rebalance /tmp/weights.json --dry-run

# Uncomment to execute:
# alpaca-cli trading orders rebalance /tmp/weights.json --execute --yes
```

---

## 🛠️ Output Formats

Most commands support multiple output formats:

```bash
# Table format (default, human-readable)
alpaca-cli trading positions list

# JSON format (for scripting)
alpaca-cli trading positions list --format json

# CSV format (for spreadsheets)
alpaca-cli trading positions list --format csv

# Export to file
alpaca-cli trading positions list --format csv --export positions.csv
```

---

## 🔧 Troubleshooting

### Common Issues

**API Key Not Found**
```bash
# Check if environment variables are set
echo $APCA_API_KEY_ID
echo $APCA_API_SECRET_KEY

# Or verify config file
cat ~/.alpaca.json
```

**Market is Closed**
```bash
# Check market hours
alpaca-cli clock
alpaca-cli trading calendar
```

**Order Rejected**
```bash
# Check account status and buying power
alpaca-cli status

# Verify asset is tradable
alpaca-cli trading assets get SYMBOL
```

### Debug Mode

```bash
# Enable debug logging
alpaca-cli --debug trading orders list
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📬 Support

- **Issues**: [GitHub Issues](https://github.com/nischalpi/alpaca-cli/issues)
- **Alpaca API Docs**: [docs.alpaca.markets](https://docs.alpaca.markets/)

---

<p align="center">
  Made for CLI lovers.
</p>
