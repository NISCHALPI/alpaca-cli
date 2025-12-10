"""Assets commands - Get All Assets, Get Asset."""

import rich_click as click
from typing import Optional, List, Any
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetStatus, AssetClass, AssetExchange
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table
from alpaca_cli.logger.logger import get_logger

logger = get_logger("trading.assets")


@click.group()
def assets() -> None:
    """Asset lookup (list, get)."""
    pass


@assets.command("list")
@click.option(
    "--status",
    type=click.Choice(["active", "inactive"], case_sensitive=False),
    help="Filter by status",
)
@click.option(
    "--asset-class",
    "asset_class",
    type=click.Choice(["us_equity", "crypto", "us_option"], case_sensitive=False),
    help="Filter by class",
)
@click.option(
    "--exchange",
    type=click.Choice(
        ["AMEX", "ARCA", "BATS", "NYSE", "NASDAQ", "IEX", "OTC"], case_sensitive=False
    ),
    help="Filter by exchange",
)
@click.option(
    "--attributes",
    help="Comma-separated attributes (e.g., fractional,ptp_no_exception)",
)
def list_assets(
    status: Optional[str],
    asset_class: Optional[str],
    exchange: Optional[str],
    attributes: Optional[str],
) -> None:
    """Get all tradable assets."""
    logger.info("Fetching assets...")
    client = get_trading_client()

    attr_list = attributes.split(",") if attributes else None

    req = GetAssetsRequest(
        status=AssetStatus(status.lower()) if status else None,
        asset_class=AssetClass(asset_class.lower()) if asset_class else None,
        exchange=AssetExchange(exchange.upper()) if exchange else None,
        attributes=attr_list,
    )

    try:
        assets_list = client.get_all_assets(req)

        if not assets_list:
            logger.info("No assets found.")
            return

        rows: List[List[Any]] = []
        for asset in assets_list[:100]:  # Limit to 100 for display
            rows.append(
                [
                    asset.symbol,
                    asset.name[:30] + "..." if len(asset.name) > 30 else asset.name,
                    asset.exchange.name,
                    asset.asset_class.name,
                    "Active" if asset.status == AssetStatus.ACTIVE else "Inactive",
                    "Yes" if asset.tradable else "No",
                    "Yes" if asset.fractionable else "No",
                ]
            )

        print_table(
            "Assets",
            ["Symbol", "Name", "Exchange", "Class", "Status", "Tradable", "Fractional"],
            rows,
        )
        if len(assets_list) > 100:
            logger.info(
                f"Showing 100 of {len(assets_list)} assets. Use filters to narrow down."
            )

    except Exception as e:
        logger.error(f"Failed to list assets: {e}")


@assets.command("get")
@click.argument("symbol_or_id")
def get_asset(symbol_or_id: str) -> None:
    """Get details of a specific asset."""
    logger.info(f"Fetching details for {symbol_or_id}...")
    client = get_trading_client()

    try:
        asset = client.get_asset(symbol_or_id)

        rows = [
            ["ID", str(asset.id)],
            ["Symbol", asset.symbol],
            ["Name", asset.name],
            ["Exchange", asset.exchange.name],
            ["Class", asset.asset_class.name],
            ["Status", asset.status.name],
            ["Tradable", str(asset.tradable)],
            ["Marginable", str(asset.marginable)],
            ["Shortable", str(asset.shortable)],
            ["Easy to Borrow", str(asset.easy_to_borrow)],
            ["Fractionable", str(asset.fractionable)],
        ]

        if hasattr(asset, "min_order_size") and asset.min_order_size:
            rows.append(["Min Order Size", str(asset.min_order_size)])
        if hasattr(asset, "min_trade_increment") and asset.min_trade_increment:
            rows.append(["Min Trade Increment", str(asset.min_trade_increment)])
        if hasattr(asset, "price_increment") and asset.price_increment:
            rows.append(["Price Increment", str(asset.price_increment)])

        print_table(f"Asset: {asset.symbol}", ["Property", "Value"], rows)

    except Exception as e:
        logger.error(f"Failed to get asset: {e}")
