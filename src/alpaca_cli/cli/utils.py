from typing import List, Any
from rich.console import Console
from rich.table import Table

console = Console()


def print_table(title: str, columns: List[str], rows: List[List[Any]]) -> None:
    """Print a rich table.

    Args:
        title: Table title
        columns: List of column names
        rows: List of rows, where each row is a list of values
    """
    table = Table(title=title, show_header=True, header_style="bold magenta")

    for col in columns:
        table.add_column(col)

    for row in rows:
        table.add_row(*[str(r) for r in row])

    console.print(table)


def format_currency(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)
