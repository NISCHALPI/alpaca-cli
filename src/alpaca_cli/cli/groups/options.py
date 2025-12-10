"""Options trading commands."""

import rich_click as click
from typing import Optional, List, Any
from datetime import datetime, date

from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger

logger = get_logger("options")


@click.group()
def options() -> None:
    """Options trading commands."""
    pass


@options.command("contracts")
@click.argument("underlying_symbol")
@click.option("--expiry", help="Expiration date (YYYY-MM-DD)")
@click.option("--expiry-from", help="Expiration date from (YYYY-MM-DD)")
@click.option("--expiry-to", help="Expiration date to (YYYY-MM-DD)")
@click.option(
    "--type",
    "option_type",
    type=click.Choice(["call", "put"], case_sensitive=False),
    help="Option type",
)
@click.option("--strike-from", type=float, help="Minimum strike price")
@click.option("--strike-to", type=float, help="Maximum strike price")
@click.option("--limit", default=20, help="Max contracts to return")
def contracts(
    underlying_symbol: str,
    expiry: Optional[str],
    expiry_from: Optional[str],
    expiry_to: Optional[str],
    option_type: Optional[str],
    strike_from: Optional[float],
    strike_to: Optional[float],
    limit: int,
) -> None:
    """List option contracts for an underlying symbol.

    Examples:
        alpaca-cli options contracts AAPL
        alpaca-cli options contracts AAPL --expiry 2024-03-15 --type call
        alpaca-cli options contracts AAPL --strike-from 150 --strike-to 200
    """
    from alpaca.trading.requests import GetOptionContractsRequest
    from alpaca.trading.enums import ContractType

    logger.info(f"Fetching option contracts for {underlying_symbol.upper()}...")
    client = get_trading_client()

    try:
        # Parse dates
        expiry_dt = datetime.strptime(expiry, "%Y-%m-%d").date() if expiry else None
        expiry_from_dt = datetime.strptime(expiry_from, "%Y-%m-%d").date() if expiry_from else None
        expiry_to_dt = datetime.strptime(expiry_to, "%Y-%m-%d").date() if expiry_to else None

        req = GetOptionContractsRequest(
            underlying_symbols=[underlying_symbol.upper()],
            expiration_date=expiry_dt,
            expiration_date_gte=expiry_from_dt,
            expiration_date_lte=expiry_to_dt,
            type=ContractType(option_type.lower()) if option_type else None,
            strike_price_gte=str(strike_from) if strike_from else None,
            strike_price_lte=str(strike_to) if strike_to else None,
            limit=limit,
        )

        response = client.get_option_contracts(req)
        contracts_list = response.option_contracts if response else []

        if not contracts_list:
            logger.info("No option contracts found.")
            return

        rows = []
        for c in contracts_list:
            rows.append([
                c.symbol,
                c.underlying_symbol,
                c.type.value if c.type else "-",
                str(c.expiration_date),
                format_currency(c.strike_price) if c.strike_price else "-",
                c.status.value if c.status else "-",
                str(c.open_interest) if c.open_interest else "-",
            ])

        print_table(
            f"Option Contracts: {underlying_symbol.upper()}",
            ["Symbol", "Underlying", "Type", "Expiry", "Strike", "Status", "Open Int"],
            rows,
        )
        logger.info(f"Found {len(contracts_list)} contract(s)")

    except Exception as e:
        logger.error(f"Failed to get option contracts: {e}")


@options.command("contract")
@click.argument("contract_symbol")
def contract(contract_symbol: str) -> None:
    """Get details for a specific option contract.

    Example: alpaca-cli options contract AAPL240315C00150000
    """
    logger.info(f"Fetching contract {contract_symbol}...")
    client = get_trading_client()

    try:
        c = client.get_option_contract(contract_symbol)

        rows = [
            ["Symbol", c.symbol],
            ["Underlying", c.underlying_symbol],
            ["Type", c.type.value if c.type else "-"],
            ["Style", c.style.value if c.style else "-"],
            ["Expiration", str(c.expiration_date)],
            ["Strike Price", format_currency(c.strike_price) if c.strike_price else "-"],
            ["Status", c.status.value if c.status else "-"],
            ["Open Interest", str(c.open_interest) if c.open_interest else "-"],
            ["Close Price", format_currency(c.close_price) if c.close_price else "-"],
            ["Root Symbol", c.root_symbol or "-"],
            ["Tradable", str(c.tradable)],
        ]

        print_table(f"Contract: {c.symbol}", ["Field", "Value"], rows)

    except Exception as e:
        logger.error(f"Failed to get contract: {e}")


@options.command("exercise")
@click.argument("contract_symbol")
def exercise(contract_symbol: str) -> None:
    """Exercise an option position.

    Example: alpaca-cli options exercise AAPL240315C00150000
    """
    logger.info(f"Exercising option {contract_symbol}...")
    client = get_trading_client()

    try:
        result = client.exercise_options_position(contract_symbol)
        logger.info(f"Option exercise submitted successfully.")
        if result:
            logger.info(f"Order ID: {result.id}")
    except Exception as e:
        logger.error(f"Failed to exercise option: {e}")


# --- OPTION ORDER HELPERS ---
def submit_option_order(order_data) -> None:
    """Submit an option order."""
    from alpaca.trading.client import TradingClient

    client = get_trading_client()
    try:
        order = client.submit_order(order_data=order_data)
        logger.info(f"Option order submitted: {order.id}")
        logger.info(f"Symbol: {order.symbol}, Side: {order.side.name}, Status: {order.status.name}")
    except Exception as e:
        logger.error(f"Failed to submit option order: {e}")


@options.group()
def buy() -> None:
    """Buy options (calls/puts)."""
    pass


@options.group()
def sell() -> None:
    """Sell options (calls/puts)."""
    pass


@buy.command("market")
@click.argument("contract_symbol")
@click.argument("qty", type=int)
@click.option("--tif", default="day", type=click.Choice(["day", "gtc", "ioc", "fok"]), help="Time in Force")
def buy_market(contract_symbol: str, qty: int, tif: str) -> None:
    """Buy option contract at market price."""
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    req = MarketOrderRequest(
        symbol=contract_symbol.upper(),
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce(tif),
    )
    submit_option_order(req)


@buy.command("limit")
@click.argument("contract_symbol")
@click.argument("qty", type=int)
@click.argument("limit_price", type=float)
@click.option("--tif", default="day", type=click.Choice(["day", "gtc", "ioc", "fok"]), help="Time in Force")
def buy_limit(contract_symbol: str, qty: int, limit_price: float, tif: str) -> None:
    """Buy option contract at limit price."""
    from alpaca.trading.requests import LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    req = LimitOrderRequest(
        symbol=contract_symbol.upper(),
        qty=qty,
        limit_price=limit_price,
        side=OrderSide.BUY,
        time_in_force=TimeInForce(tif),
    )
    submit_option_order(req)


@sell.command("market")
@click.argument("contract_symbol")
@click.argument("qty", type=int)
@click.option("--tif", default="day", type=click.Choice(["day", "gtc", "ioc", "fok"]), help="Time in Force")
def sell_market(contract_symbol: str, qty: int, tif: str) -> None:
    """Sell option contract at market price."""
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    req = MarketOrderRequest(
        symbol=contract_symbol.upper(),
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce(tif),
    )
    submit_option_order(req)


@sell.command("limit")
@click.argument("contract_symbol")
@click.argument("qty", type=int)
@click.argument("limit_price", type=float)
@click.option("--tif", default="day", type=click.Choice(["day", "gtc", "ioc", "fok"]), help="Time in Force")
def sell_limit(contract_symbol: str, qty: int, limit_price: float, tif: str) -> None:
    """Sell option contract at limit price."""
    from alpaca.trading.requests import LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    req = LimitOrderRequest(
        symbol=contract_symbol.upper(),
        qty=qty,
        limit_price=limit_price,
        side=OrderSide.SELL,
        time_in_force=TimeInForce(tif),
    )
    submit_option_order(req)
