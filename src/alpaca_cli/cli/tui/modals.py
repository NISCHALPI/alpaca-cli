from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Button, DataTable, Static, Log, Input
from alpaca_cli.api.client import get_trading_client


class AssetInfoModal(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close")]
    CSS = """
    AssetInfoModal {
        align: center middle;
    }
    #asset-modal-dialog {
        width: 85;
        height: auto;
        padding: 1 2;
        border: heavy $accent;
        background: $surface;
    }
    .asset-modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        width: 100%;
        margin-bottom: 1;
    }
    #asset_data_table {
        height: auto;
        border: none;
    }
    #asset_modal_btn_container {
        margin-top: 1;
        height: auto;
    }
    .asset-modal-btn {
        width: 1fr;
        margin: 0 1;
    }
    """
    
    def __init__(self, asset, **kwargs):
        super().__init__(**kwargs)
        self.asset = asset

    def compose(self) -> ComposeResult:
        with Vertical(id="asset-modal-dialog"):
            yield Label(f"Asset Information: {self.asset.symbol}", classes="asset-modal-title")
            
            table = DataTable(id="asset_data_table")
            table.show_header = False
            table.add_columns("Field", "Value")
            
            fields = [
                ("Symbol", str(self.asset.symbol)),
                ("Name", str(self.asset.name)),
                ("Exchange", str(self.asset.exchange)),
                ("Class", str(self.asset.asset_class)),
                ("Status", str(self.asset.status).upper()),
                ("Tradable", "[green]Yes[/green]" if self.asset.tradable else "[red]No[/red]"),
                ("Marginable", "[green]Yes[/green]" if self.asset.marginable else "[red]No[/red]"),
                ("Shortable", "[green]Yes[/green]" if self.asset.shortable else "[red]No[/red]"),
                ("Easy to Borrow", "[green]Yes[/green]" if getattr(self.asset, 'easy_to_borrow', False) else "[red]No[/red]"),
                ("Fractionable", "[green]Yes[/green]" if getattr(self.asset, 'fractionable', False) else "[red]No[/red]"),
            ]
            
            for f, v in fields:
                table.add_row(f, str(v))
                
            yield table
            
            with Horizontal(id="asset_modal_btn_container"):
                yield Button("Remove Watchlist", id="remove_watchlist_modal_btn", variant="error", classes="asset-modal-btn")
                yield Button("Close", id="close_modal_btn", variant="primary", classes="asset-modal-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "remove_watchlist_modal_btn":
            self.app.call_later(self.app.action_remove_symbol, self.asset.symbol)
            self.dismiss()
        elif event.button.id == "close_modal_btn":
            self.dismiss()


class OrderInfoModal(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close")]
    CSS = """
    OrderInfoModal {
        align: center middle;
    }
    #order-modal-dialog {
        width: 85;
        height: auto;
        padding: 1 2;
        border: heavy $accent;
        background: $surface;
    }
    .order-modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        width: 100%;
        margin-bottom: 1;
    }
    #order_info_table {
        height: auto;
        border: none;
    }
    #order_modal_btn_container {
        margin-top: 1;
        height: auto;
    }
    .order-modal-btn {
        width: 1fr;
    }
    """

    def __init__(self, order, **kwargs):
        super().__init__(**kwargs)
        self.order = order

    def compose(self) -> ComposeResult:
        with Vertical(id="order-modal-dialog"):
            yield Label(f"Order Details: {self.order.symbol} ({str(self.order.id)[:8]})", classes="order-modal-title")
            
            table = DataTable(id="order_info_table")
            table.show_header = False
            table.add_columns("Field", "Value")
            
            table.add_row("Order ID", str(self.order.id))
            table.add_row("Symbol", str(self.order.symbol))
            table.add_row("Side", str(self.order.side).upper())
            table.add_row("Quantity", str(self.order.qty))
            table.add_row("Filled Qty", str(getattr(self.order, 'filled_qty', '0')))
            table.add_row("Order Type", str(self.order.order_type).upper())
            table.add_row("Time In Force", str(self.order.time_in_force).upper())
            table.add_row("Status", str(self.order.status).upper())
            if getattr(self.order, "limit_price", None):
                table.add_row("Limit Price", f"${float(self.order.limit_price):.2f}")
            if getattr(self.order, "stop_price", None):
                table.add_row("Stop Price", f"${float(self.order.stop_price):.2f}")
            if getattr(self.order, "filled_avg_price", None):
                table.add_row("Avg Fill Price", f"${float(self.order.filled_avg_price):.2f}")
            table.add_row("Submitted At", str(getattr(self.order, "submitted_at", "-"))[:19])
            
            yield table
            
            status_str = str(self.order.status).lower()
            is_active = any(s in status_str for s in ["new", "accepted", "pending", "partially_filled", "held"])
            
            with Horizontal(id="order_modal_btn_container"):
                if is_active:
                    yield Button("Cancel Order", id="modal_cancel_order_btn", variant="error", classes="order-modal-btn")
                yield Button("Close", id="modal_close_btn", variant="primary", classes="order-modal-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal_cancel_order_btn":
            try:
                client = get_trading_client()
                client.cancel_order_by_id(self.order.id)
                self.app.notify(f"Cancelled order {str(self.order.id)[:8]} for {self.order.symbol}", title="Order Cancelled", severity="warning")
                self.app.load_orders()
            except Exception as e:
                self.app.notify(f"Cancel failed: {e}", severity="error")
            self.dismiss()
        elif event.button.id == "modal_close_btn":
            self.dismiss()


class PositionModal(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close")]
    CSS = """
    PositionModal {
        align: center middle;
    }
    #pos-modal-dialog {
        width: 85;
        height: auto;
        padding: 1 2;
        border: heavy $accent;
        background: $surface;
    }
    .pos-modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        width: 100%;
        margin-bottom: 1;
    }
    #pos_info_table {
        height: auto;
        border: none;
    }
    #pos_modal_btn_container {
        margin-top: 1;
        height: auto;
    }
    .pos-modal-btn {
        width: 1fr;
    }
    """

    def __init__(self, position, **kwargs):
        super().__init__(**kwargs)
        self.position = position

    def compose(self) -> ComposeResult:
        with Vertical(id="pos-modal-dialog"):
            yield Label(f"Position Summary: {self.position.symbol}", classes="pos-modal-title")
            
            table = DataTable(id="pos_info_table")
            table.show_header = False
            table.add_columns("Field", "Value")
            
            pnl_val = float(self.position.unrealized_pl)
            pnl_color = "green" if pnl_val >= 0 else "red"
            
            table.add_row("Symbol", str(self.position.symbol))
            table.add_row("Side", str(self.position.side).upper())
            table.add_row("Quantity", str(self.position.qty))
            table.add_row("Avg Entry Price", f"${float(self.position.avg_entry_price):.2f}")
            table.add_row("Current Price", f"${float(self.position.current_price):.2f}")
            table.add_row("Market Value", f"${float(self.position.market_value):.2f}")
            table.add_row("Cost Basis", f"${float(self.position.cost_basis):.2f}")
            table.add_row("Unrealized PnL", f"[{pnl_color}]${pnl_val:.2f} ({float(self.position.unrealized_plpc)*100:.2f}%)[/{pnl_color}]")
            
            yield table
            
            with Horizontal(id="pos_modal_btn_container"):
                yield Button("Liquidate Position", id="modal_close_pos_btn", variant="error", classes="pos-modal-btn")
                yield Button("Close", id="modal_close_btn", variant="primary", classes="pos-modal-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal_close_pos_btn":
            try:
                client = get_trading_client()
                client.close_position(self.position.symbol)
                self.app.notify(f"Liquidating position for {self.position.symbol}...", title="Position Closing", severity="warning")
                self.app.load_portfolio()
            except Exception as e:
                self.app.notify(f"Close failed: {e}", severity="error")
            self.dismiss()
        elif event.button.id == "modal_close_btn":
            self.dismiss()


class NewsReaderModal(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close")]
    CSS = """
    NewsReaderModal {
        align: center middle;
    }
    #news-modal-dialog {
        width: 85;
        height: auto;
        max-height: 85%;
        padding: 1 2;
        border: heavy $accent;
        background: $surface;
    }
    .news-modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        width: 100%;
        margin-bottom: 1;
    }
    #news_meta_table {
        height: auto;
        border: none;
        margin-bottom: 1;
    }
    #news_body_container {
        height: auto;
        min-height: 5;
        max-height: 12;
        border: round $primary;
        padding: 1;
        margin-bottom: 1;
        background: $panel;
    }
    #news_modal_btn_container {
        margin-top: 1;
        height: auto;
    }
    .news-modal-btn {
        width: 1fr;
        margin: 0 1;
    }
    """

    def __init__(self, article, **kwargs):
        super().__init__(**kwargs)
        self.article = article

    def compose(self) -> ComposeResult:
        with Vertical(id="news-modal-dialog"):
            headline = self.article.get("headline") if isinstance(self.article, dict) else getattr(self.article, "headline", "Market News")
            yield Label(f"{headline}", classes="news-modal-title")
            
            table = DataTable(id="news_meta_table")
            table.show_header = False
            table.add_columns("Field", "Value")
            
            author = self.article.get("author") if isinstance(self.article, dict) else getattr(self.article, "author", "Unknown")
            source = self.article.get("source") if isinstance(self.article, dict) else getattr(self.article, "source", "Unknown")
            created_at = self.article.get("created_at") if isinstance(self.article, dict) else getattr(self.article, "created_at", None)
            symbols = self.article.get("symbols") if isinstance(self.article, dict) else getattr(self.article, "symbols", [])
            
            symbols_str = ", ".join(symbols) if symbols else "General Market"
            
            table.add_row("Source", str(source).upper())
            table.add_row("Author", str(author))
            table.add_row("Published", str(created_at)[:19] if created_at else "-")
            table.add_row("Tickers", f"[bold cyan]{symbols_str}[/bold cyan]")
            yield table
            
            summary = self.article.get("summary") if isinstance(self.article, dict) else getattr(self.article, "summary", "No summary available.")
            with VerticalScroll(id="news_body_container"):
                yield Static(f"[b]Summary:[/b]\n{summary}")
                
            with Horizontal(id="news_modal_btn_container"):
                if symbols:
                    yield Button(f"Trade {symbols[0]}", id="modal_trade_news_btn", variant="success", classes="news-modal-btn")
                yield Button("Close", id="modal_close_btn", variant="primary", classes="news-modal-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal_trade_news_btn":
            symbols = self.article.get("symbols") if isinstance(self.article, dict) else getattr(self.article, "symbols", [])
            if symbols:
                sym = symbols[0]
                try:
                    self.app.query_one("#trade_symbol", Input).value = sym
                    self.app.query_one("TabbedContent").active = "trade_tab"
                    self.app.notify(f"Pre-filled trade ticket with {sym} from news article.", severity="information")
                except Exception:
                    pass
            self.dismiss()
        elif event.button.id == "modal_close_btn":
            self.dismiss()


class ActivityLogModal(ModalScreen):
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("ctrl+l", "dismiss", "Close Log"),
    ]
    CSS = """
    ActivityLogModal {
        align: center middle;
    }
    #log-modal-dialog {
        width: 90%;
        height: 85%;
        padding: 1 2;
        border: heavy $accent;
        background: $surface;
    }
    .log-modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        width: 100%;
        margin-bottom: 1;
    }
    #modal_execution_log_drawer {
        height: 1fr;
        width: 100%;
        border: round $accent;
        background: $panel;
        padding: 1;
    }
    #log_modal_btn_container {
        margin-top: 1;
        height: auto;
    }
    .log-modal-btn {
        width: 1fr;
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="log-modal-dialog"):
            yield Label("System Activity & Execution Log [dim](Ctrl+L / Esc to Close)[/dim]", classes="log-modal-title")
            yield Log(id="modal_execution_log_drawer")
            with Horizontal(id="log_modal_btn_container"):
                yield Button("Clear Log", id="modal_clear_log_btn", variant="error", classes="log-modal-btn")
                yield Button("Close (Esc)", id="modal_close_btn", variant="primary", classes="log-modal-btn")

    def on_mount(self) -> None:
        try:
            log_widget = self.query_one("#modal_execution_log_drawer", Log)
            for line in getattr(self.app, "log_buffer", []):
                log_widget.write_line(line)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal_clear_log_btn":
            try:
                self.query_one("#modal_execution_log_drawer", Log).clear()
                if hasattr(self.app, "log_buffer"):
                    self.app.log_buffer.clear()
                self.app.notify("Activity log cleared", severity="information")
            except Exception:
                pass
        elif event.button.id == "modal_close_btn":
            self.dismiss()
