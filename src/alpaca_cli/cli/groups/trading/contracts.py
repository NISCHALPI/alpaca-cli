"""Option Contracts commands - Get Option Contracts, Get Option Contract."""

import rich_click as click
from typing import Optional, List, Any
from datetime import datetime, date
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger

logger = get_logger("trading.contracts")


@click.group()
def contracts() -> None:
    """Option contracts lookup (list, get)."""
    pass


@contracts.command("list")
@click.argument("underlying_symbol")
@click.option("--expiry", help="Exact expiration date (YYYY-MM-DD)")
@click.option("--expiry-from", help="Expiration date range start (YYYY-MM-DD)")
@click.option("--expiry-to", help="Expiration date range end (YYYY-MM-DD)")
@click.option(
    "--type",
    "option_type",
    type=click.Choice(["call", "put"], case_sensitive=False),
    help="Option type",
)
@click.option("--strike-from", type=float, help="Strike price range start")
@click.option("--strike-to", type=float, help="Strike price range end")
@click.option(
    "--style",
    type=click.Choice(["american", "european"], case_sensitive=False),
    help="Option style",
)
@click.option("--root-symbol", help="Root symbol filter")
@click.option("--limit", default=50, help="Max contracts to return")
@click.option("--page-token", help="Pagination token")
def list_contracts(
    underlying_symbol: str,
    expiry: Optional[str],
    expiry_from: Optional[str],
    expiry_to: Optional[str],
    option_type: Optional[str],
    strike_from: Optional[float],
    strike_to: Optional[float],
    style: Optional[str],
    root_symbol: Optional[str],
    limit: int,
    page_token: Optional[str],
) -> None:
    """List option contracts for an underlying symbol."""
    from alpaca.trading.requests import GetOptionContractsRequest

    logger.info(f"Fetching option contracts for {underlying_symbol.upper()}...")
    client = get_trading_client()

    try:
        # Parse dates
        expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date() if expiry else None
        expiry_from_date = (
            datetime.strptime(expiry_from, "%Y-%m-%d").date() if expiry_from else None
        )
        expiry_to_date = (
            datetime.strptime(expiry_to, "%Y-%m-%d").date() if expiry_to else None
        )

        req = GetOptionContractsRequest(
            underlying_symbols=[underlying_symbol.upper()],
            expiration_date=expiry_date,
            expiration_date_gte=expiry_from_date,
            expiration_date_lte=expiry_to_date,
            type=option_type.lower() if option_type else None,
            strike_price_gte=str(strike_from) if strike_from else None,
            strike_price_lte=str(strike_to) if strike_to else None,
            style=style.lower() if style else None,
            root_symbol=root_symbol,
            limit=limit,
            page_token=page_token,
        )

        response = client.get_option_contracts(req)

        if not response or not response.option_contracts:
            logger.info("No contracts found.")
            return

        rows: List[List[Any]] = []
        for c in response.option_contracts:
            rows.append(
                [
                    c.symbol,
                    c.underlying_symbol,
                    c.type.value if hasattr(c.type, "value") else str(c.type),
                    str(c.expiration_date),
                    format_currency(c.strike_price),
                    c.style.value if hasattr(c.style, "value") else str(c.style),
                    c.status.value if hasattr(c.status, "value") else str(c.status),
                ]
            )

        print_table(
            f"Option Contracts: {underlying_symbol.upper()}",
            ["Symbol", "Underlying", "Type", "Expiry", "Strike", "Style", "Status"],
            rows,
        )

        if response.next_page_token:
            logger.info(f"Next page token: {response.next_page_token}")

    except Exception as e:
        logger.error(f"Failed to list contracts: {e}")


@contracts.command("get")
@click.argument("symbol_or_id")
def get_contract(symbol_or_id: str) -> None:
    """Get details for a specific option contract."""
    logger.info(f"Fetching contract {symbol_or_id}...")
    client = get_trading_client()

    try:
        contract = client.get_option_contract(symbol_or_id.upper())

        rows = [
            ["Symbol", contract.symbol],
            ["Contract ID", str(contract.id)],
            ["Underlying Symbol", contract.underlying_symbol],
            ["Underlying Asset ID", str(contract.underlying_asset_id)],
            [
                "Type",
                (
                    contract.type.value
                    if hasattr(contract.type, "value")
                    else str(contract.type)
                ),
            ],
            [
                "Style",
                (
                    contract.style.value
                    if hasattr(contract.style, "value")
                    else str(contract.style)
                ),
            ],
            [
                "Status",
                (
                    contract.status.value
                    if hasattr(contract.status, "value")
                    else str(contract.status)
                ),
            ],
            ["Expiration Date", str(contract.expiration_date)],
            ["Strike Price", format_currency(contract.strike_price)],
            ["Root Symbol", contract.root_symbol or "-"],
            ["Size", str(contract.size) if contract.size else "100"],
            [
                "Open Interest",
                str(contract.open_interest) if contract.open_interest else "-",
            ],
            [
                "Open Interest Date",
                (
                    str(contract.open_interest_date)
                    if contract.open_interest_date
                    else "-"
                ),
            ],
            [
                "Close Price",
                format_currency(contract.close_price) if contract.close_price else "-",
            ],
            [
                "Close Price Date",
                str(contract.close_price_date) if contract.close_price_date else "-",
            ],
        ]

        print_table(f"Contract: {contract.symbol}", ["Field", "Value"], rows)

    except Exception as e:
        logger.error(f"Failed to get contract: {e}")
