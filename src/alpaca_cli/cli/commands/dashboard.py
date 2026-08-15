import rich_click as click
from alpaca_cli.cli.tui.app import DashboardApp

@click.command()
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    help="[Optional] Enable auto-refresh mode for live updates (Not fully supported in Textual yet, starts normally)",
)
@click.option(
    "--interval",
    "-i",
    type=int,
    default=5,
    help="[Optional] Refresh interval in seconds when using --watch. Default: 5",
)
@click.option(
    "--compact",
    "-c",
    is_flag=True,
    help="[Optional] Use compact layout for smaller terminals",
)
def dashboard(watch: bool, interval: int, compact: bool) -> None:
    """Show the trading dashboard.

    A comprehensive view of your account, positions, orders, and market status.
    """
    app = DashboardApp()
    app.run()
