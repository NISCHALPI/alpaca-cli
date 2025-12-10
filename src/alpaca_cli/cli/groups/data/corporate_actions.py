"""Corporate actions data commands."""

import rich_click as click
from typing import Optional
from datetime import datetime
from alpaca_cli.core.config import config
from alpaca_cli.cli.utils import print_table
from alpaca_cli.logger.logger import get_logger

logger = get_logger("data.corporate_actions")


@click.command("corporate-actions")
@click.option(
    "--symbols",
    type=str,
    default=None,
    help="[Optional] Comma-separated list of symbols to filter by",
)
@click.option(
    "--types",
    type=str,
    default=None,
    help="[Optional] Comma-separated action types. Choices: dividend, merger, spinoff, split",
)
@click.option(
    "--start",
    type=str,
    default=None,
    help="[Optional] Start date in YYYY-MM-DD format",
)
@click.option(
    "--end",
    type=str,
    default=None,
    help="[Optional] End date in YYYY-MM-DD format",
)
@click.option(
    "--limit",
    type=int,
    default=50,
    help="[Optional] Maximum number of results to return. Default: 50",
)
def corporate_actions(
    symbols: Optional[str],
    types: Optional[str],
    start: Optional[str],
    end: Optional[str],
    limit: int,
) -> None:
    """Get corporate actions data (dividends, splits, mergers, spinoffs)."""
    from alpaca.data.historical.corporate_actions import CorporateActionsClient
    from alpaca.data.requests import CorporateActionsRequest

    config.validate()
    logger.info("Fetching corporate actions data...")

    try:
        client = CorporateActionsClient(config.API_KEY, config.API_SECRET)

        symbol_list = (
            [s.strip().upper() for s in symbols.split(",")] if symbols else None
        )
        type_list = [t.strip().lower() for t in types.split(",")] if types else None
        start_dt = datetime.strptime(start, "%Y-%m-%d") if start else None
        end_dt = datetime.strptime(end, "%Y-%m-%d") if end else None

        req = CorporateActionsRequest(
            symbols=symbol_list,
            types=type_list,
            start=start_dt,
            end=end_dt,
            limit=limit,
        )
        result = client.get_corporate_actions(req)

        if not result or not result.data:
            logger.info("No corporate actions found.")
            return

        rows = []
        for action_type, actions in result.data.items():
            if not actions:
                continue
            for action in actions:
                rows.append(
                    [
                        action_type,
                        getattr(action, "symbol", getattr(action, "old_symbol", "-")),
                        str(
                            getattr(
                                action,
                                "ex_date",
                                getattr(action, "effective_date", "-"),
                            )
                        ),
                        (
                            str(getattr(action, "record_date", "-"))
                            if hasattr(action, "record_date")
                            else "-"
                        ),
                        str(
                            getattr(
                                action, "cash_amount", getattr(action, "new_rate", "-")
                            )
                        ),
                    ]
                )

        if not rows:
            logger.info("No corporate actions found.")
            return

        print_table(
            "Corporate Actions",
            ["Type", "Symbol", "Ex-Date", "Record Date", "Value"],
            rows,
        )
    except Exception as e:
        logger.error(f"Failed to get corporate actions: {e}")
