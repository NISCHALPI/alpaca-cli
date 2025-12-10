import rich_click as click
from typing import Optional, List, Any
from alpaca.trading.requests import CreateWatchlistRequest, UpdateWatchlistRequest
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger

logger = get_logger("watchlist")


@click.group()
def watchlist() -> None:
    """Manage watchlists."""
    pass


def get_watchlist_id_by_name_or_id(name_or_id: str) -> Optional[str]:
    """Resolve watchlist ID from name or ID."""
    client = get_trading_client()
    try:
        # Try fetching by ID first if it looks like a UUID
        if len(name_or_id) == 36:  # Simple UUID length check
            try:
                wl = client.get_watchlist_by_id(name_or_id)
                return wl.id
            except Exception:
                pass  # Not found by ID, try name

        # Fetch all and search by name
        watchlists = client.get_watchlists()
        for wl in watchlists:
            if wl.name == name_or_id or wl.id == name_or_id:
                return wl.id

        return None
    except Exception as e:
        logger.error(f"Error resolving watchlist: {e}")
        return None


@watchlist.command("list")
def list_watchlists() -> None:
    """List all watchlists."""
    logger.info("Fetching watchlists...")
    client = get_trading_client()
    try:
        watchlists = client.get_watchlists()
        if not watchlists:
            logger.info("No watchlists found.")
            return

        rows: List[List[Any]] = []
        for wl in watchlists:
            assets_count = len(wl.assets) if wl.assets else 0
            rows.append(
                [
                    str(wl.created_at.strftime("%Y-%m-%d")),
                    wl.id,
                    wl.name,
                    str(assets_count),
                ]
            )

        print_table(
            "Watchlists",
            ["Created", "ID", "Name", "Assets"],
            rows,
        )
    except Exception as e:
        logger.error(f"Failed to list watchlists: {e}")


@watchlist.command("show")
@click.argument("name_or_id")
def show_watchlist(name_or_id: str) -> None:
    """Show details of a specific watchlist."""
    wl_id = get_watchlist_id_by_name_or_id(name_or_id)
    if not wl_id:
        logger.error(f"Watchlist '{name_or_id}' not found.")
        return

    logger.info(f"Fetching watchlist {name_or_id}...")
    client = get_trading_client()
    try:
        wl = client.get_watchlist_by_id(wl_id)

        print_table(
            f"Watchlist: {wl.name}",
            ["Property", "Value"],
            [
                ["ID", wl.id],
                ["Name", wl.name],
                ["Created", str(wl.created_at)],
                ["Updated", str(wl.updated_at)],
                ["Account ID", wl.account_id],
            ],
        )

        if wl.assets:
            # Fetch current positions to cross-reference
            positions_map = {}
            try:
                positions = client.get_all_positions()
                for pos in positions:
                    positions_map[pos.symbol] = pos
            except Exception:
                pass  # Ignore errors fetching positions, just show empty columns

            asset_rows = []
            for asset in wl.assets:
                pos = positions_map.get(asset.symbol)

                qty = str(pos.qty) if pos else "-"
                avg_entry = format_currency(pos.avg_entry_price) if pos else "-"
                current_price = format_currency(pos.current_price) if pos else "-"

                pl_str = "-"
                if pos:
                    pl_percent = float(pos.unrealized_plpc) * 100
                    pl_color = "green" if pl_percent >= 0 else "red"
                    pl_str = f"[{pl_color}]{format_currency(pos.unrealized_pl)} ({pl_percent:.2f}%)[/{pl_color}]"

                asset_rows.append(
                    [
                        asset.symbol,
                        asset.name,
                        asset.status.name,
                        qty,
                        avg_entry,
                        current_price,
                        pl_str,
                    ]
                )

            print_table(
                f"Assets in {wl.name}",
                ["Symbol", "Name", "Status", "Qty", "Avg Entry", "Current", "P/L"],
                asset_rows,
            )
        else:
            logger.info("This watchlist is empty.")

    except Exception as e:
        logger.error(f"Failed to show watchlist: {e}")


@watchlist.command("create")
@click.argument("name")
@click.argument("symbols", nargs=-1)
def create_watchlist(name: str, symbols: tuple) -> None:
    """Create a new watchlist."""
    logger.info(f"Creating watchlist '{name}'...")
    client = get_trading_client()
    try:
        req = CreateWatchlistRequest(name=name, symbols=list(symbols))
        wl = client.create_watchlist(req)
        logger.info(f"Watchlist '{wl.name}' created successfully (ID: {wl.id}).")
    except Exception as e:
        logger.error(f"Failed to create watchlist: {e}")


@watchlist.command("update")
@click.argument("name_or_id")
@click.option("--name", help="New name for the watchlist")
@click.option("--symbols", help="Comma-separated list of symbols to REPLACE items")
def update_watchlist(
    name_or_id: str, name: Optional[str], symbols: Optional[str]
) -> None:
    """Update a watchlist (rename or replace assets)."""
    wl_id = get_watchlist_id_by_name_or_id(name_or_id)
    if not wl_id:
        logger.error(f"Watchlist '{name_or_id}' not found.")
        return

    logger.info(f"Updating watchlist {name_or_id}...")
    client = get_trading_client()
    try:
        symbol_list = symbols.split(",") if symbols else None
        req = UpdateWatchlistRequest(name=name, symbols=symbol_list)
        wl = client.update_watchlist_by_id(wl_id, req)
        logger.info(f"Watchlist '{wl.name}' updated successfully.")
    except Exception as e:
        logger.error(f"Failed to update watchlist: {e}")


@watchlist.command("add")
@click.argument("name_or_id")
@click.argument("symbol")
def add_asset(name_or_id: str, symbol: str) -> None:
    """Add an asset to a watchlist."""
    wl_id = get_watchlist_id_by_name_or_id(name_or_id)
    if not wl_id:
        logger.error(f"Watchlist '{name_or_id}' not found.")
        return

    logger.info(f"Adding {symbol} to watchlist {name_or_id}...")
    client = get_trading_client()
    try:
        client.add_asset_to_watchlist_by_id(wl_id, symbol)
        logger.info(f"Asset {symbol} added to watchlist.")
    except Exception as e:
        logger.error(f"Failed to add asset: {e}")


@watchlist.command("remove")
@click.argument("name_or_id")
@click.argument("symbol")
def remove_asset(name_or_id: str, symbol: str) -> None:
    """Remove an asset from a watchlist."""
    wl_id = get_watchlist_id_by_name_or_id(name_or_id)
    if not wl_id:
        logger.error(f"Watchlist '{name_or_id}' not found.")
        return

    logger.info(f"Removing {symbol} from watchlist {name_or_id}...")
    client = get_trading_client()
    try:
        client.remove_asset_from_watchlist_by_id(wl_id, symbol)
        logger.info(f"Asset {symbol} removed from watchlist.")
    except Exception as e:
        logger.error(f"Failed to remove asset: {e}")


@watchlist.command("delete")
@click.argument("name_or_id")
def delete_watchlist(name_or_id: str) -> None:
    """Delete a watchlist."""
    wl_id = get_watchlist_id_by_name_or_id(name_or_id)
    if not wl_id:
        logger.error(f"Watchlist '{name_or_id}' not found.")
        return

    logger.info(f"Deleting watchlist {name_or_id}...")
    client = get_trading_client()
    try:
        client.delete_watchlist_by_id(wl_id)
        logger.info(f"Watchlist deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete watchlist: {e}")
