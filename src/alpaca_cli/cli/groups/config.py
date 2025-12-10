import rich_click as click
from alpaca_cli.core.config import config
from alpaca_cli.core.client import get_trading_client
from alpaca_cli.logger.logger import get_logger

logger = get_logger("config")


@click.group()
def configuration() -> None:
    """Manage CLI configuration."""
    pass


@configuration.command()
def verify() -> None:
    """Verify configuration and API connectivity."""
    logger.info("Verifying configuration...")

    # Check loading source
    logger.info(f"Source: {config.SOURCE}")

    logger.info(f"Base URL: {config.BASE_URL}")
    logger.info(f"Mode: {'Paper' if config.IS_PAPER else 'Live'}")

    try:
        config.validate()
        logger.info("Credentials: Found (Masked)")
    except ValueError as e:
        logger.error(f"Credentials Error: {e}")
        return

    # Check Connectivity
    logger.info("Testing API Connectivity...")
    try:
        client = get_trading_client()
        account = client.get_account()
        logger.info(f"Success! Connected to account: {account.id}")
        logger.info(f"Status: {account.status}")
    except Exception as e:
        logger.error(f"Connection Failed: {e}")


@configuration.command()
def show() -> None:
    """Show current configuration."""
    logger.info(f"Source: {config.SOURCE}")
    logger.info(f"API Key: {'*' * 8 if config.API_KEY else 'Not Set'}")
    logger.info(f"API Secret: {'*' * 8 if config.API_SECRET else 'Not Set'}")
    logger.info(f"Base URL: {config.BASE_URL}")
    logger.info(f"Paper Trading: {config.IS_PAPER}")


@configuration.command()
@click.argument("mode", type=click.Choice(["paper", "live"], case_sensitive=False))
def set_mode(mode: str) -> None:
    """Set trading mode (Paper or Live)."""
    url = config.PAPER_URL if mode.lower() == "paper" else config.LIVE_URL

    config.save("APCA_API_BASE_URL", url)
    logger.info(f"Configuration updated. Switched to {mode.upper()} mode.")
    logger.info(f"Base URL set to: {url}")
