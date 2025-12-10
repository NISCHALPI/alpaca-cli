"""News commands - Market news."""

import rich_click as click
from typing import Optional
from datetime import datetime
from alpaca_cli.core.config import config
from alpaca_cli.cli.utils import print_table
from alpaca_cli.logger.logger import get_logger

logger = get_logger("data.news")


@click.command()
@click.option(
    "--symbols",
    type=str,
    default=None,
    help="[Optional] Comma-separated list of symbols to filter news by",
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
    default=10,
    help="[Optional] Maximum number of news items to return. Default: 10",
)
@click.option(
    "--include-content/--no-content",
    default=False,
    help="[Optional] Include full article content in output. Default: --no-content",
)
@click.option(
    "--exclude-contentless/--include-contentless",
    default=False,
    help="[Optional] Exclude articles without content. Default: --include-contentless",
)
def news(
    symbols: Optional[str],
    start: Optional[str],
    end: Optional[str],
    limit: int,
    include_content: bool,
    exclude_contentless: bool,
) -> None:
    """Get market news."""
    from alpaca.data.historical.news import NewsClient
    from alpaca.data.requests import NewsRequest
    from alpaca.common.enums import Sort

    config.validate()
    logger.info("Fetching market news...")

    try:
        client = NewsClient(config.API_KEY, config.API_SECRET)

        symbol_str = (
            ",".join([s.strip().upper() for s in symbols.split(",")])
            if symbols
            else None
        )
        start_dt = datetime.strptime(start, "%Y-%m-%d") if start else None
        end_dt = datetime.strptime(end, "%Y-%m-%d") if end else None

        req = NewsRequest(
            symbols=symbol_str,
            start=start_dt,
            end=end_dt,
            limit=limit,
            include_content=include_content,
            exclude_contentless=exclude_contentless,
            sort=Sort.DESC,
        )

        result = client.get_news(req)

        if not result or not result.data.get("news"):
            logger.info("No news found.")
            return

        rows = []
        for article in result.data.get("news", []):
            symbols_str = (
                ", ".join(article.symbols[:3])
                + ("..." if len(article.symbols) > 3 else "")
                if article.symbols
                else "-"
            )
            headline = (
                article.headline[:60] + "..."
                if len(article.headline) > 60
                else article.headline
            )

            rows.append(
                [
                    (
                        article.created_at.strftime("%Y-%m-%d %H:%M")
                        if article.created_at
                        else "-"
                    ),
                    headline,
                    symbols_str,
                    article.source or "-",
                ]
            )

        print_table("Market News", ["Time", "Headline", "Symbols", "Source"], rows)

        if include_content:
            logger.info("\n--- Full Articles ---")
            for article in result.data.get("news", []):
                logger.info(f"\n[bold]{article.headline}[/bold]")
                logger.info(f"Source: {article.source} | {article.created_at}")
                if article.content:
                    # Print first 500 chars of content
                    content = (
                        article.content[:500] + "..."
                        if len(article.content) > 500
                        else article.content
                    )
                    logger.info(content)
                logger.info(f"URL: {article.url}")
                logger.info("-" * 50)

    except Exception as e:
        logger.error(f"Failed to get news: {e}")
