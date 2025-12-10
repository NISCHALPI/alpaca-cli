"""Corporate Actions commands (Trading API)."""

import rich_click as click
from typing import Optional, List, Any
from datetime import datetime
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.cli.utils import print_table
from alpaca_cli.logger.logger import get_logger

logger = get_logger("trading.corporate_actions")


@click.group("corporate-actions")
def corporate_actions() -> None:
    """Corporate actions announcements (list, get)."""
    pass


@corporate_actions.command("list")
@click.option(
    "--ca-types", help="Comma-separated types (dividend, merger, spinoff, split)"
)
@click.option("--since", help="Since date (YYYY-MM-DD)")
@click.option("--until", help="Until date (YYYY-MM-DD)")
@click.option("--symbol", help="Filter by symbol")
@click.option("--cusip", help="Filter by CUSIP")
@click.option(
    "--date-type",
    type=click.Choice(["declaration", "ex", "record", "payable"]),
    help="Date type for filtering",
)
def list_corporate_actions(
    ca_types: Optional[str],
    since: Optional[str],
    until: Optional[str],
    symbol: Optional[str],
    cusip: Optional[str],
    date_type: Optional[str],
) -> None:
    """Get corporate action announcements."""
    from alpaca.trading.requests import GetCorporateAnnouncementsRequest
    from alpaca.trading.enums import CorporateActionType, CorporateActionDateType

    logger.info("Fetching corporate actions...")
    client = get_trading_client()

    try:
        # Parse types
        types_list = None
        if ca_types:
            type_map = {
                "dividend": CorporateActionType.DIVIDEND,
                "merger": CorporateActionType.MERGER,
                "spinoff": CorporateActionType.SPINOFF,
                "split": CorporateActionType.SPLIT,
            }
            types_list = [
                type_map[t.lower()]
                for t in ca_types.split(",")
                if t.lower() in type_map
            ]

        since_dt = datetime.strptime(since, "%Y-%m-%d").date() if since else None
        until_dt = datetime.strptime(until, "%Y-%m-%d").date() if until else None

        date_type_enum = None
        if date_type:
            date_type_map = {
                "declaration": CorporateActionDateType.DECLARATION,
                "ex": CorporateActionDateType.EX,
                "record": CorporateActionDateType.RECORD,
                "payable": CorporateActionDateType.PAYABLE,
            }
            date_type_enum = date_type_map.get(date_type)

        req = GetCorporateAnnouncementsRequest(
            ca_types=types_list
            or [CorporateActionType.DIVIDEND],  # Default to dividends
            since=since_dt,
            until=until_dt,
            symbol=symbol.upper() if symbol else None,
            cusip=cusip,
            date_type=date_type_enum,
        )

        announcements = client.get_corporate_announcements(req)

        if not announcements:
            logger.info("No corporate actions found.")
            return

        rows: List[List[Any]] = []
        for ca in announcements[:50]:  # Limit display
            rows.append(
                [
                    (
                        ca.ca_type.value
                        if hasattr(ca.ca_type, "value")
                        else str(ca.ca_type)
                    ),
                    ca.symbol,
                    str(ca.ex_date) if ca.ex_date else "-",
                    str(ca.record_date) if ca.record_date else "-",
                    str(ca.cash) if hasattr(ca, "cash") and ca.cash else "-",
                    (
                        ca.ca_sub_type.value
                        if hasattr(ca, "ca_sub_type") and ca.ca_sub_type
                        else "-"
                    ),
                ]
            )

        print_table(
            "Corporate Actions",
            ["Type", "Symbol", "Ex-Date", "Record Date", "Cash", "Sub-Type"],
            rows,
        )

    except Exception as e:
        logger.error(f"Failed to get corporate actions: {e}")


@corporate_actions.command("get")
@click.argument("announcement_id")
def get_corporate_action(announcement_id: str) -> None:
    """Get a specific corporate action by ID."""
    logger.info(f"Fetching corporate action {announcement_id}...")
    client = get_trading_client()

    try:
        ca = client.get_corporate_announcement_by_id(announcement_id)

        rows = [
            ["ID", str(ca.id)],
            [
                "Type",
                ca.ca_type.value if hasattr(ca.ca_type, "value") else str(ca.ca_type),
            ],
            [
                "Sub-Type",
                (
                    ca.ca_sub_type.value
                    if hasattr(ca, "ca_sub_type") and ca.ca_sub_type
                    else "-"
                ),
            ],
            ["Symbol", ca.symbol],
            ["CUSIP", ca.cusip or "-"],
            ["", ""],
            [
                "Declaration Date",
                str(ca.declaration_date) if ca.declaration_date else "-",
            ],
            ["Ex-Date", str(ca.ex_date) if ca.ex_date else "-"],
            ["Record Date", str(ca.record_date) if ca.record_date else "-"],
            ["Payable Date", str(ca.payable_date) if ca.payable_date else "-"],
            ["", ""],
            ["Cash", str(ca.cash) if hasattr(ca, "cash") and ca.cash else "-"],
            [
                "Old Rate",
                str(ca.old_rate) if hasattr(ca, "old_rate") and ca.old_rate else "-",
            ],
            [
                "New Rate",
                str(ca.new_rate) if hasattr(ca, "new_rate") and ca.new_rate else "-",
            ],
        ]

        print_table(f"Corporate Action: {ca.symbol}", ["Field", "Value"], rows)

    except Exception as e:
        logger.error(f"Failed to get corporate action: {e}")
