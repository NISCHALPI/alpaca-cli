"""Watchlists commands - CRUD operations for watchlists."""

import rich_click as click
from typing import Optional, List, Any
from alpaca.trading.requests import CreateWatchlistRequest, UpdateWatchlistRequest
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table, format_currency
from alpaca_cli.logger.logger import get_logger

logger = get_logger("trading.watchlists")


def get_watchlist_id_by_name_or_id(name_or_id: str) -> Optional[str]:
    """Resolve watchlist ID from name or ID."""
    client = get_trading_client()
    try:
        if len(name_or_id) == 36:  # UUID length
            try:
                wl = client.get_watchlist_by_id(name_or_id)
                return wl.id
            except Exception:
                pass
        watchlists = client.get_watchlists()
        for wl in watchlists:
            if wl.name == name_or_id or wl.id == name_or_id:
                return wl.id
        return None
    except Exception as e:
        logger.error(f"Error resolving watchlist: {e}")
        return None


@click.group()
def watchlists() -> None:
    """Watchlist management (list, show, create, update, delete)."""
    pass


@watchlists.command("list")
def list_watchlists() -> None:
    """Get all watchlists."""
    logger.info("Fetching watchlists...")
    client = get_trading_client()
    try:
        wl_list = client.get_watchlists()
        if not wl_list:
            logger.info("No watchlists found.")
            return

        rows: List[List[Any]] = []
        for wl in wl_list:
            rows.append(
                [
                    str(wl.created_at.strftime("%Y-%m-%d")),
                    wl.id,
                    wl.name,
                    str(len(wl.assets) if wl.assets else 0),
                ]
            )

        print_table("Watchlists", ["Created", "ID", "Name", "Assets"], rows)
    except Exception as e:
        logger.error(f"Failed to list watchlists: {e}")


@watchlists.command("show")
@click.argument("name_or_id")
def show_watchlist(name_or_id: str) -> None:
    """Get a watchlist by ID or name."""
    wl_id = get_watchlist_id_by_name_or_id(name_or_id)
    if not wl_id:
        logger.error(f"Watchlist '{name_or_id}' not found.")
        return

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
            ],
        )

        if wl.assets:
            positions_map = {}
            try:
                positions = client.get_all_positions()
                positions_map = {pos.symbol: pos for pos in positions}
            except Exception:
                pass

            asset_rows = []
            for asset in wl.assets:
                pos = positions_map.get(asset.symbol)
                qty = str(pos.qty) if pos else "-"
                current = format_currency(pos.current_price) if pos else "-"
                pl_str = "-"
                if pos:
                    pl_pct = float(pos.unrealized_plpc) * 100
                    color = "green" if pl_pct >= 0 else "red"
                    pl_str = f"[{color}]{format_currency(pos.unrealized_pl)} ({pl_pct:.2f}%)[/{color}]"
                asset_rows.append([asset.symbol, asset.name, qty, current, pl_str])

            print_table(
                f"Assets in {wl.name}",
                ["Symbol", "Name", "Qty", "Price", "P/L"],
                asset_rows,
            )
        else:
            logger.info("This watchlist is empty.")
    except Exception as e:
        logger.error(f"Failed to show watchlist: {e}")


@watchlists.command("create")
@click.argument("name")
@click.argument("symbols", nargs=-1)
def create_watchlist(name: str, symbols: tuple) -> None:
    """Create a new watchlist."""
    logger.info(f"Creating watchlist '{name}'...")
    client = get_trading_client()
    try:
        req = CreateWatchlistRequest(name=name, symbols=list(symbols))
        wl = client.create_watchlist(req)
        logger.info(f"Watchlist '{wl.name}' created (ID: {wl.id}).")
    except Exception as e:
        logger.error(f"Failed to create watchlist: {e}")


@watchlists.command("update")
@click.argument("name_or_id")
@click.option(
    "--name",
    "new_name",
    type=str,
    default=None,
    help="[Optional] New name for the watchlist",
)
@click.option(
    "--symbols",
    type=str,
    default=None,
    help="[Optional] Comma-separated list of symbols to REPLACE all items in watchlist",
)
def update_watchlist(
    name_or_id: str, new_name: Optional[str], symbols: Optional[str]
) -> None:
    """Update a watchlist (rename or replace assets)."""
    wl_id = get_watchlist_id_by_name_or_id(name_or_id)
    if not wl_id:
        logger.error(f"Watchlist '{name_or_id}' not found.")
        return

    client = get_trading_client()
    try:
        symbol_list = symbols.split(",") if symbols else None
        req = UpdateWatchlistRequest(name=new_name, symbols=symbol_list)
        wl = client.update_watchlist_by_id(wl_id, req)
        logger.info(f"Watchlist '{wl.name}' updated.")
    except Exception as e:
        logger.error(f"Failed to update watchlist: {e}")


@watchlists.command("add")
@click.argument("name_or_id")
@click.argument("symbol")
def add_asset(name_or_id: str, symbol: str) -> None:
    """Add an asset to a watchlist."""
    wl_id = get_watchlist_id_by_name_or_id(name_or_id)
    if not wl_id:
        logger.error(f"Watchlist '{name_or_id}' not found.")
        return

    client = get_trading_client()
    try:
        client.add_asset_to_watchlist_by_id(wl_id, symbol.upper())
        logger.info(f"Asset {symbol.upper()} added to watchlist.")
    except Exception as e:
        logger.error(f"Failed to add asset: {e}")


@watchlists.command("remove")
@click.argument("name_or_id")
@click.argument("symbol")
def remove_asset(name_or_id: str, symbol: str) -> None:
    """Remove an asset from a watchlist."""
    wl_id = get_watchlist_id_by_name_or_id(name_or_id)
    if not wl_id:
        logger.error(f"Watchlist '{name_or_id}' not found.")
        return

    client = get_trading_client()
    try:
        client.remove_asset_from_watchlist_by_id(wl_id, symbol.upper())
        logger.info(f"Asset {symbol.upper()} removed from watchlist.")
    except Exception as e:
        logger.error(f"Failed to remove asset: {e}")


@watchlists.command("delete")
@click.argument("name_or_id")
def delete_watchlist(name_or_id: str) -> None:
    """Delete a watchlist."""
    wl_id = get_watchlist_id_by_name_or_id(name_or_id)
    if not wl_id:
        logger.error(f"Watchlist '{name_or_id}' not found.")
        return

    client = get_trading_client()
    try:
        client.delete_watchlist_by_id(wl_id)
        logger.info("Watchlist deleted.")
    except Exception as e:
        logger.error(f"Failed to delete watchlist: {e}")
