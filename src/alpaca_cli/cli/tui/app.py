from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, TabbedContent, TabPane, Static, Input, Button, Label, Select, Log, Rule
from textual.containers import Horizontal, Vertical, Grid, VerticalScroll
from textual.reactive import reactive
from textual.message import Message
from textual.events import Click
from textual.screen import ModalScreen
from rich.text import Text

from alpaca_cli.api.client import get_trading_client, get_stock_data_client
from alpaca_cli.cli.tui.stream import MarketStreamer, NewsStreamer
from alpaca.data.requests import StockSnapshotRequest, NewsRequest
from alpaca.data.historical.news import NewsClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca_cli.core.config import config

def generate_sparkline(prices: list[float]) -> str:
    """Generate an 8-level ASCII Unicode sparkline string from a price series."""
    if not prices or len(prices) < 2:
        return " ─── "
        
    min_p = min(prices)
    max_p = max(prices)
    rng = max_p - min_p
    
    ticks = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    if rng == 0:
        return ticks[3] * min(len(prices), 8)
        
    result = []
    if len(prices) > 8:
        step = len(prices) / 8.0
        sampled = [prices[int(i * step)] for i in range(8)]
    else:
        sampled = prices
        
    for p in sampled:
        idx = int(((p - min_p) / rng) * 7)
        idx = max(0, min(7, idx))
        result.append(ticks[idx])
        
    return "".join(result)

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

class DashboardApp(App):
    BINDINGS = [
        ("ctrl+b", "quick_buy", "Quick Buy"),
        ("ctrl+k", "liquidate_selected", "Liquidate Selected"),
        ("ctrl+r", "refresh_all", "Refresh All"),
        ("ctrl+l", "toggle_activity_log", "Activity Log"),
        ("slash", "focus_search", "Search Focus"),
    ]

    CSS = """
    .form-group {
        margin: 1;
        layout: horizontal;
        height: 3;
    }
    #portfolio_tab {
        layout: vertical;
    }
    .portfolio-header-bar {
        height: 3;
        margin-bottom: 1;
        layout: horizontal;
    }
    .summary-grid-v2 {
        layout: grid;
        grid-size: 3;
        grid-gutter: 1 1;
        height: auto;
        margin-bottom: 1;
    }
    .summary-box-v2 {
        border: round $accent;
        background: $panel;
        text-align: center;
        content-align: center middle;
        height: 4;
        padding: 0 1;
    }
    #portfolio_main_container {
        height: 1fr;
        width: 100%;
        layout: horizontal;
    }
    #portfolio_table_container {
        width: 2fr;
        height: 100%;
        margin-right: 1;
    }
    #portfolio_side_panel {
        width: 1fr;
        height: 100%;
    }
    #portfolio_table {
        height: 1fr;
        width: 100%;
    }
    #portfolio_chart {
        height: 1fr;
        width: 100%;
        border: round $accent;
        background: $panel;
        padding: 1;
    }
    .portfolio-section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    .preset-btn {
        margin-left: 1;
    }
    #markets_table {
        height: 1fr;
        width: 100%;
    }
    #order_ticket_container {
        align: center middle;
        min-height: 100%;
        padding: 1;
    }
    #order_ticket {
        width: 70;
        height: auto;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    .ticket-grid {
        grid-size: 2;
        grid-gutter: 1 2;
        height: auto;
        margin-bottom: 1;
    }
    .ticket-group {
        height: auto;
    }
    .ticket-label {
        text-style: bold;
        color: $text-muted;
    }
    .ticket-divider {
        height: 1;
        background: $primary;
        margin-top: 1;
        margin-bottom: 1;
    }
    #ticker_marquee_bar {
        height: 3;
        background: $panel;
        border: round $accent;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    #log_tab {
        layout: vertical;
    }
    #execution_log_drawer {
        height: 1fr;
        width: 100%;
        border: round $accent;
        background: $panel;
        padding: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.market_widgets = {}
        self.streamer = None
        self.news_streamer = None
        self.live_news_items = []
        self.symbols = config.watchlist
        self.current_orders = []
        self.current_positions = []
        self.market_snapshots = {}
        self.index_snapshots = {}
        self.market_table_symbols = []
        self.log_buffer = []

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Portfolio", id="portfolio_tab"):
                with Grid(classes="summary-grid-v2"):
                    yield Static(id="summary_equity", classes="summary-box-v2")
                    yield Static(id="summary_bp", classes="summary-box-v2")
                    yield Static(id="summary_cash", classes="summary-box-v2")
                    yield Static(id="summary_pnl", classes="summary-box-v2")
                    yield Static(id="summary_margin", classes="summary-box-v2")
                    yield Static(id="summary_daytrades", classes="summary-box-v2")
                    
                with Horizontal(id="portfolio_main_container"):
                    with Vertical(id="portfolio_table_container"):
                        yield Label("[b]Open Positions[/b] [dim](Click row to manage position)[/dim]", classes="portfolio-section-title")
                        yield DataTable(id="portfolio_table", cursor_type="row")
                    with Vertical(id="portfolio_side_panel"):
                        yield Label("[b]Asset Allocation[/b]", classes="portfolio-section-title")
                        yield Static(id="portfolio_chart")
                
            with TabPane("Markets", id="markets_tab"):
                yield Static(id="ticker_marquee_bar")
                with Horizontal(classes="form-group"):
                    yield Input(placeholder="Add Ticker (e.g. AAPL)", id="new_symbol_input")
                    yield Button("Add", id="add_symbol_btn", variant="primary")
                    yield Button("Remove", id="remove_symbol_btn", variant="error")
                    yield Button("+ Tech", id="preset_tech_btn", classes="preset-btn")
                    yield Button("+ Indices", id="preset_indices_btn", classes="preset-btn")
                    yield Button("+ Crypto", id="preset_crypto_btn", classes="preset-btn")
                    
                yield DataTable(id="markets_table", cursor_type="row")
                
            with TabPane("Trade", id="trade_tab"):
                with VerticalScroll(id="order_ticket_container"):
                    with Vertical(id="order_ticket"):
                        yield Label("[b]Advanced Order Ticket[/b]", id="ticket_title")
                        with Grid(classes="ticket-grid"):
                            with Vertical(classes="ticket-group"):
                                yield Label("Symbol", classes="ticket-label")
                                yield Input(placeholder="e.g. AAPL", id="trade_symbol")
                            with Vertical(classes="ticket-group"):
                                yield Label("Quantity", classes="ticket-label")
                                yield Input(placeholder="e.g. 10", id="trade_qty")
                            with Vertical(classes="ticket-group"):
                                yield Label("Side", classes="ticket-label")
                                yield Select([(s.upper(), s) for s in ["buy", "sell"]], id="trade_side", value="buy")
                            with Vertical(classes="ticket-group"):
                                yield Label("Order Type", classes="ticket-label")
                                yield Select([(s.upper(), s) for s in ["market", "limit"]], id="trade_type", value="market")
                            with Vertical(classes="ticket-group"):
                                yield Label("Time In Force", classes="ticket-label")
                                yield Select([(s.upper(), s) for s in ["day", "gtc", "ioc", "fok"]], id="trade_tif", value="day")
                            with Vertical(classes="ticket-group"):
                                yield Label("Limit Price ($)", classes="ticket-label")
                                yield Input(placeholder="Only for limit orders", id="trade_limit_price")
                                
                        yield Rule(line_style="dashed")
                        yield Label("[b]Bracket Configuration (Optional)[/b]", id="ticket_bracket_title")
                        with Grid(classes="ticket-grid"):
                            with Vertical(classes="ticket-group"):
                                yield Label("Bracket Mode", classes="ticket-label")
                                yield Select([("Price ($)", "price"), ("Percent (%)", "percent")], id="trade_bracket_mode", value="price")
                            with Vertical(classes="ticket-group"):
                                yield Label("Take Profit", classes="ticket-label")
                                yield Input(placeholder="Price ($) or %", id="trade_tp")
                            with Vertical(classes="ticket-group"):
                                yield Label("Stop Loss", classes="ticket-label")
                                yield Input(placeholder="Price ($) or %", id="trade_sl")
                                
                        with Horizontal(classes="ticket-btn-group"):
                            yield Button("Submit Order", id="submit_trade_btn", variant="primary")
                            yield Button("Clear Form", id="clear_trade_btn", variant="default")
                    
            with TabPane("Orders", id="orders_tab"):
                with Horizontal(classes="form-group"):
                    yield Button("Cancel All Open Orders", id="cancel_all_orders_btn", variant="warning")
                yield DataTable(id="orders_table", cursor_type="row")
                
            with TabPane("Market News", id="news_tab"):
                with Horizontal(classes="form-group"):
                    yield Input(placeholder="Filter by Symbol (e.g. NVDA)", id="news_symbol_input")
                    yield Button("Filter News", id="filter_news_btn", variant="primary")
                    yield Button("Fetch Latest", id="refresh_news_btn")
                    yield Button("Clear Filter", id="clear_news_btn", variant="error")
                yield DataTable(id="news_table", cursor_type="row")
                
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "Alpaca Dashboard"
        try:
            client = get_trading_client()
            clock = client.get_clock()
            market_state = "OPEN" if clock.is_open else "CLOSED"
        except Exception:
            market_state = "UNKNOWN"
            
        market_icon = "🟢" if market_state == "OPEN" else "⚪"
            
        from alpaca_cli.core.config import config
        mode_str = config.mode.upper()
        mode_icon = "🟡" if mode_str == "PAPER" else "🔴"
        
        self.sub_title = f"{mode_icon} {mode_str}   |   {market_icon} {market_state}"
        self.marquee_offset = 0
        
        self.load_portfolio()
        self.load_markets()
        self.load_orders()
        self.load_news()
        self.set_interval(0.15, self.animate_ticker_marquee)
        self.log_event(f"System Initialized in {mode_str} mode. Market state: {market_state}.", "info")

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        pane_id = getattr(event.pane, "id", "") or getattr(event.tab, "id", "")
        if "news" in pane_id:
            try:
                self.query_one("#news_table", DataTable).focus()
            except Exception:
                pass
        elif "markets" in pane_id:
            try:
                self.query_one("#markets_table", DataTable).focus()
            except Exception:
                pass
        elif "portfolio" in pane_id:
            try:
                self.query_one("#portfolio_table", DataTable).focus()
            except Exception:
                pass
        elif "orders" in pane_id:
            try:
                self.query_one("#orders_table", DataTable).focus()
            except Exception:
                pass

    def log_event(self, msg: str, level: str = "info") -> None:
        try:
            from datetime import datetime
            time_str = datetime.now().strftime("%H:%M:%S")
            
            if level == "error":
                formatted = f"[{time_str}] [bold red]ERROR [/bold red]  {msg}"
            elif level == "warning":
                formatted = f"[{time_str}] [bold yellow]WARN  [/bold yellow]  {msg}"
            elif level == "success":
                formatted = f"[{time_str}] [bold green]EXEC  [/bold green]  {msg}"
            else:
                formatted = f"[{time_str}] [cyan]INFO  [/cyan]  {msg}"
                
            if hasattr(self, "log_buffer"):
                self.log_buffer.append(formatted)
                
            try:
                log_widget = self.screen.query_one("#modal_execution_log_drawer", Log)
                log_widget.write_line(formatted)
            except Exception:
                pass
        except Exception:
            pass

    def action_toggle_activity_log(self) -> None:
        """Open Activity Log Modal Screen on Ctrl+L."""
        self.push_screen(ActivityLogModal())

    def action_quick_buy(self) -> None:
        try:
            tabbed = self.query_one(TabbedContent)
            active_tab = tabbed.active
            sym = None
            if active_tab == "markets_tab":
                table = self.query_one("#markets_table", DataTable)
                if table.cursor_row < len(self.market_table_symbols):
                    sym = self.market_table_symbols[table.cursor_row]
            elif active_tab == "portfolio_tab":
                table = self.query_one("#portfolio_table", DataTable)
                if table.cursor_row < len(self.current_positions):
                    sym = self.current_positions[table.cursor_row].symbol
            elif self.symbols:
                sym = self.symbols[0]
                
            if sym:
                self.query_one("#trade_symbol", Input).value = sym
                tabbed.active = "trade_tab"
                self.notify(f"HotKey [Ctrl+B]: Trade ticket loaded with {sym}", severity="information")
                self.log_event(f"HOTKEY [Ctrl+B]: Loaded order ticket for {sym}", "info")
            else:
                self.notify("No symbol selected for Quick Buy.", severity="warning")
        except Exception as e:
            self.notify(f"Quick Buy error: {e}", severity="error")

    def action_liquidate_selected(self) -> None:
        try:
            tabbed = self.query_one(TabbedContent)
            table = self.query_one("#portfolio_table", DataTable)
            if table.cursor_row < len(self.current_positions):
                pos = self.current_positions[table.cursor_row]
                self.push_screen(PositionModal(pos))
                self.log_event(f"HOTKEY [Ctrl+K]: Liquidation modal opened for {pos.symbol}", "warning")
            else:
                self.notify("No position selected in Portfolio tab.", severity="warning")
        except Exception as e:
            self.notify(f"Liquidate error: {e}", severity="error")

    def action_refresh_all(self) -> None:
        try:
            self.load_portfolio()
            self.load_markets()
            self.load_orders()
            self.load_news()
            self.notify("HotKey [Ctrl+R]: Refreshed all workspace data.", severity="information")
            self.log_event("HOTKEY [Ctrl+R]: All workspace data reloaded.", "info")
        except Exception as e:
            self.notify(f"Refresh error: {e}", severity="error")

    def action_focus_search(self) -> None:
        try:
            tabbed = self.query_one(TabbedContent)
            active_tab = tabbed.active
            if active_tab == "markets_tab":
                self.query_one("#new_symbol_input", Input).focus()
            elif active_tab == "news_tab":
                self.query_one("#news_symbol_input", Input).focus()
            elif active_tab == "trade_tab":
                self.query_one("#trade_symbol", Input).focus()
        except Exception:
            pass

    def load_portfolio(self):
        try:
            client = get_trading_client()
            acct = client.get_account()
            positions = client.get_all_positions()
            
            self.query_one("#summary_equity", Static).update(f"[dim]TOTAL EQUITY[/dim]\n[b cyan]${float(acct.equity):,.2f}[/b cyan]")
            self.query_one("#summary_bp", Static).update(f"[dim]BUYING POWER[/dim]\n[b white]${float(acct.buying_power):,.2f}[/b white]")
            self.query_one("#summary_cash", Static).update(f"[dim]CASH BALANCE[/dim]\n[b white]${float(acct.cash):,.2f}[/b white]")
            
            day_pnl = float(acct.equity) - float(acct.last_equity)
            pnl_pct = (day_pnl / float(acct.last_equity)) * 100 if float(acct.last_equity) > 0 else 0.0
            pnl_color = "bold green" if day_pnl >= 0 else "bold red"
            sign = "+" if day_pnl >= 0 else ""
            self.query_one("#summary_pnl", Static).update(f"[dim]DAY P&L[/dim]\n[{pnl_color}]{sign}${abs(day_pnl):,.2f} ({sign}{pnl_pct:.2f}%)[/{pnl_color}]")
            
            margin_val = float(acct.maintenance_margin) if acct.maintenance_margin else 0.0
            margin_pct = (margin_val / float(acct.equity)) * 100 if float(acct.equity) > 0 else 0.0
            self.query_one("#summary_margin", Static).update(f"[dim]MARGIN MAINT.[/dim]\n[b]${margin_val:,.2f} ({margin_pct:.1f}%)[/b]")
            
            dt_count = int(acct.daytrade_count) if acct.daytrade_count else 0
            dt_color = "bold red" if dt_count >= 3 else "bold green"
            self.query_one("#summary_daytrades", Static).update(f"[dim]DAY TRADES (PDT)[/dim]\n[{dt_color}]{dt_count} / 3 Used[/{dt_color}]")

            table = self.query_one("#portfolio_table", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "Symbol", 
                "Side",
                Text("Qty", justify="right"), 
                Text("Avg Price", justify="right"),
                Text("Current Price", justify="right"),
                Text("Market Value", justify="right"), 
                Text("Cost Basis", justify="right"),
                Text("Unrealized PnL", justify="right"),
                Text("PnL %", justify="right")
            )

            pie_labels = []
            pie_values = []
            if float(acct.cash) > 0:
                pie_labels.append("CASH")
                pie_values.append(float(acct.cash))

            self.current_positions = positions
            for pos in positions:
                pie_labels.append(pos.symbol)
                pie_values.append(float(pos.market_value))
                
                side_str = pos.side.value if hasattr(pos.side, 'value') else str(pos.side)
                side_text = Text(side_str.upper(), style="blue" if side_str.lower() == "long" else "magenta")
                
                avg_px = float(pos.avg_entry_price)
                avg_text = Text(f"${avg_px:.2f}", justify="right")
                cur_px = float(pos.current_price)
                cur_text = Text(f"${cur_px:.2f}", justify="right")
                cb = float(pos.cost_basis)
                cb_text = Text(f"${cb:.2f}", justify="right")
                pnl_pc = float(pos.unrealized_plpc) * 100
                pnl_pc_text = Text(f"{pnl_pc:.2f}%", style="bold green" if pnl_pc >= 0 else "bold red", justify="right")

                pnl_val = float(pos.unrealized_pl)
                pnl_text = Text(f"${pnl_val:.2f}", style="bold green" if pnl_val >= 0 else "bold red", justify="right")
                qty_text = Text(str(pos.qty), justify="right")
                mv_val = float(pos.market_value)
                mv_text = Text(f"${mv_val:.2f}", justify="right")

                table.add_row(
                    pos.symbol,
                    side_text,
                    qty_text,
                    avg_text,
                    cur_text,
                    mv_text,
                    cb_text,
                    pnl_text,
                    pnl_pc_text
                )
                
            chart_text = "[b]Asset Weight Distribution[/b]\n\n"
            if sum(pie_values) > 0:
                total_val = sum(pie_values)
                sorted_assets = sorted(zip(pie_labels, pie_values), key=lambda x: x[1], reverse=True)
                
                colors = ["bold cyan", "bold green", "bold yellow", "bold magenta", "bold blue", "bold white"]
                for i, (label, val) in enumerate(sorted_assets):
                    pct = (val / total_val) * 100
                    bar_len = int(round((pct / 100.0) * 12))
                    bar_str = "█" * bar_len + "░" * (12 - bar_len)
                    c = colors[i % len(colors)]
                    chart_text += f"[{c}]{label:6s}[/{c}] [{c}]{bar_str}[/{c}] [b]{pct:5.1f}%[/b] (${val:,.0f})\n"
            else:
                chart_text += "[dim]No active assets in portfolio.[/dim]"
                
            self.query_one("#portfolio_chart", Static).update(chart_text)
            
        except Exception as e:
            self.notify(f"Error loading portfolio: {str(e)}", severity="error")

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        table = event.data_table
        if table.id == "portfolio_table":
            if not hasattr(self, "_portfolio_sort_reverse"):
                self._portfolio_sort_reverse = False
                self._portfolio_sort_col = None
                
            if self._portfolio_sort_col == event.column_key:
                self._portfolio_sort_reverse = not self._portfolio_sort_reverse
            else:
                self._portfolio_sort_reverse = False
                self._portfolio_sort_col = event.column_key

            def sort_key(val):
                if hasattr(val, "plain"):
                    val = val.plain
                if isinstance(val, str):
                    val = val.replace("$", "").replace(",", "")
                    try:
                        return float(val)
                    except ValueError:
                        return val
                return val
                
            table.sort(event.column_key, key=sort_key, reverse=self._portfolio_sort_reverse)

    def load_markets(self):
        try:
            table = self.query_one("#markets_table", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "Symbol",
                Text("Price", justify="right"),
                Text("Change ($)", justify="right"),
                Text("Change (%)", justify="right"),
                Text("Day High", justify="right"),
                Text("Day Low", justify="right"),
                Text("Prev Close", justify="right"),
            )
            
            benchmarks = ["SPY", "QQQ", "DIA", "IWM", "VIX"]
            
            client = get_stock_data_client()
            
            # Fetch Index Benchmarks Snapshots for Top Marquee
            self.index_snapshots = {}
            try:
                idx_req = StockSnapshotRequest(symbol_or_symbols=benchmarks)
                idx_snaps = client.get_stock_snapshot(idx_req)
                for b in benchmarks:
                    if b in idx_snaps and idx_snaps[b].latest_trade:
                        snap = idx_snaps[b]
                        px = float(snap.latest_trade.price)
                        prev_close = float(snap.previous_daily_bar.close) if (hasattr(snap, "previous_daily_bar") and snap.previous_daily_bar) else px
                        chg = px - prev_close
                        chg_pct = (chg / prev_close) * 100 if prev_close > 0 else 0.0
                        self.index_snapshots[b] = {
                            "price": px,
                            "prev_close": prev_close,
                            "chg": chg,
                            "chg_pct": chg_pct,
                        }
            except Exception:
                pass
            
            # Fetch User Watchlist Snapshots for Bottom Table
            snapshots = {}
            if self.symbols:
                stock_syms = [s for s in self.symbols if "/" not in s]
                crypto_syms = [s for s in self.symbols if "/" in s]
                
                if stock_syms:
                    try:
                        req = StockSnapshotRequest(symbol_or_symbols=stock_syms)
                        stock_snaps = client.get_stock_snapshot(req)
                        if isinstance(stock_snaps, dict):
                            snapshots.update(stock_snaps)
                    except Exception:
                        for s in stock_syms:
                            try:
                                single_snap = client.get_stock_snapshot(StockSnapshotRequest(symbol_or_symbols=[s]))
                                if isinstance(single_snap, dict) and s in single_snap:
                                    snapshots[s] = single_snap[s]
                            except Exception:
                                pass
                                
                if crypto_syms:
                    try:
                        crypto_client = get_crypto_data_client()
                        c_req = CryptoSnapshotRequest(symbol_or_symbols=crypto_syms)
                        crypto_snaps = crypto_client.get_crypto_snapshot(c_req)
                        if isinstance(crypto_snaps, dict):
                            snapshots.update(crypto_snaps)
                    except Exception:
                        for s in crypto_syms:
                            try:
                                crypto_client = get_crypto_data_client()
                                single_snap = crypto_client.get_crypto_snapshot(CryptoSnapshotRequest(symbol_or_symbols=[s]))
                                if isinstance(single_snap, dict) and s in single_snap:
                                    snapshots[s] = single_snap[s]
                            except Exception:
                                pass
                
            self.market_snapshots = {}
            for sym in self.symbols:
                if sym in snapshots and snapshots[sym].latest_trade:
                    snap = snapshots[sym]
                    px = float(snap.latest_trade.price)
                    prev_close = float(snap.previous_daily_bar.close) if (hasattr(snap, "previous_daily_bar") and snap.previous_daily_bar) else px
                    chg = px - prev_close
                    chg_pct = (chg / prev_close) * 100 if prev_close > 0 else 0.0
                    day_high = float(snap.daily_bar.high) if (hasattr(snap, "daily_bar") and snap.daily_bar) else px
                    day_low = float(snap.daily_bar.low) if (hasattr(snap, "daily_bar") and snap.daily_bar) else px
                    
                    self.market_snapshots[sym] = {
                        "price": px,
                        "prev_close": prev_close,
                        "chg": chg,
                        "chg_pct": chg_pct,
                        "high": day_high,
                        "low": day_low,
                    }

            # Populate markets_table
            self.market_table_symbols = [s for s in self.symbols if s in self.market_snapshots]
            table.clear(columns=True)
            table.add_columns(
                "Symbol", 
                Text("Price", justify="right"),
                Text("Change ($)", justify="right"),
                Text("Change (%)", justify="right"),
                Text("Day High", justify="right"),
                Text("Day Low", justify="right"),
                Text("Prev Close", justify="right"),
                Text("Intraday Trend", justify="center")
            )
            for sym in self.market_table_symbols:
                d = self.market_snapshots[sym]
                c_color = "green" if d["chg"] >= 0 else "red"
                sign = "+" if d["chg"] >= 0 else ""
                
                # Generate 8-level sparkline trajectory
                spark_series = [d["prev_close"], d["low"], (d["high"]+d["low"])/2, d["price"], d["high"]]
                spark_str = generate_sparkline(spark_series)
                
                table.add_row(
                    sym,
                    Text(f"${d['price']:.2f}", justify="right"),
                    Text(f"{sign}${abs(d['chg']):.2f}", style=c_color, justify="right"),
                    Text(f"{sign}{d['chg_pct']:.2f}%", style=c_color, justify="right"),
                    Text(f"${d['high']:.2f}", justify="right"),
                    Text(f"${d['low']:.2f}", justify="right"),
                    Text(f"${d['prev_close']:.2f}", justify="right"),
                    Text(spark_str, style="bold green" if d["chg"] >= 0 else "bold red", justify="center"),
                    key=sym,
                )
        except Exception as e:
            self.notify(f"Markets error: {e}", severity="error")
            
        self.start_stream()

    def start_stream(self):
        if self.streamer:
            self.streamer.stop()
            
        async def on_trade(t):
            self.call_from_thread(self.update_market_widget, t.symbol, float(t.price))

        benchmarks = ["SPY", "QQQ", "DIA", "IWM", "VIX"]
        stock_stream_syms = [s for s in list(set(self.symbols + benchmarks)) if "/" not in s]
        if stock_stream_syms:
            self.streamer = MarketStreamer(stock_stream_syms, on_trade=on_trade)
            self.streamer.start()
        
        if not self.news_streamer:
            async def on_news(n):
                self.call_from_thread(self.update_news_widget, n)
            self.news_streamer = NewsStreamer(["*"], on_news=on_news)
            self.news_streamer.start()

    def animate_ticker_marquee(self):
        try:
            benchmarks = ["SPY", "QQQ", "DIA", "IWM", "VIX"]
            full_text = Text()
            for b in benchmarks:
                if hasattr(self, "index_snapshots") and b in self.index_snapshots:
                    d = self.index_snapshots[b]
                    c_color = "bold green" if d["chg"] >= 0 else "bold red"
                    sign = "+" if d["chg"] >= 0 else ""
                    full_text.append(f" {b} ", style="bold cyan")
                    full_text.append(f"${d['price']:.2f} ", style="bold white")
                    full_text.append(f"{sign}{d['chg_pct']:.2f}% ", style=c_color)
                else:
                    full_text.append(f" {b} ", style="bold cyan")
                    full_text.append("-- ", style="dim white")
                full_text.append(" │ ", style="dim white")
                
            length = len(full_text)
            if length == 0:
                return
                
            self.marquee_offset = (getattr(self, "marquee_offset", 0) + 1) % length
            sliced_text = full_text[self.marquee_offset:] + full_text[:self.marquee_offset]
            self.query_one("#ticker_marquee_bar", Static).update(sliced_text)
        except Exception:
            pass

    def update_market_widget(self, symbol: str, price: float):
        if hasattr(self, "index_snapshots") and symbol in self.index_snapshots:
            d = self.index_snapshots[symbol]
            d["price"] = price
            d["chg"] = price - d["prev_close"]
            d["chg_pct"] = (d["chg"] / d["prev_close"]) * 100 if d["prev_close"] > 0 else 0.0

        if hasattr(self, "market_snapshots") and symbol in self.market_snapshots:
            d = self.market_snapshots[symbol]
            d["price"] = price
            d["chg"] = price - d["prev_close"]
            d["chg_pct"] = (d["chg"] / d["prev_close"]) * 100 if d["prev_close"] > 0 else 0.0
            if price > d["high"]:
                d["high"] = price
            if price < d["low"]:
                d["low"] = price
                
            try:
                table = self.query_one("#markets_table", DataTable)
                c_color = "green" if d["chg"] >= 0 else "red"
                sign = "+" if d["chg"] >= 0 else ""
                table.update_cell(symbol, "Price", Text(f"${d['price']:.2f}", justify="right"))
                table.update_cell(symbol, "Change ($)", Text(f"{sign}${abs(d['chg']):.2f}", style=c_color, justify="right"))
                table.update_cell(symbol, "Change (%)", Text(f"{sign}{d['chg_pct']:.2f}%", style=c_color, justify="right"))
                table.update_cell(symbol, "Day High", Text(f"${d['high']:.2f}", justify="right"))
                table.update_cell(symbol, "Day Low", Text(f"${d['low']:.2f}", justify="right"))
            except Exception:
                pass

    def load_orders(self):
        try:
            table = self.query_one("#orders_table", DataTable)
            table.clear(columns=True)
            table.add_columns("ID", "Symbol", "Side", "Qty", "Type", "Status")
            
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus
            
            client = get_trading_client()
            req = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=50)
            self.current_orders = client.get_orders(req)
            for o in self.current_orders:
                table.add_row(str(o.id)[:8], o.symbol, o.side, str(o.qty), o.order_type, o.status)
        except Exception as e:
            self.notify(f"Error loading orders: {e}", severity="error")

    def load_news(self, symbols=None):
        try:
            client = NewsClient(config.API_KEY, config.API_SECRET)
            if symbols:
                if isinstance(symbols, (list, tuple, set)):
                    sym_str = ",".join(symbols)
                else:
                    sym_str = str(symbols).strip()
                req = NewsRequest(symbols=sym_str, limit=25)
            else:
                req = NewsRequest(limit=25)
            res = client.get_news(req)
            
            articles = []
            if hasattr(res, "data") and isinstance(res.data, dict) and "news" in res.data:
                articles = res.data["news"]
            elif hasattr(res, "news"):
                articles = res.news
            elif isinstance(res, dict) and "news" in res:
                articles = res["news"]
            elif isinstance(res, list):
                articles = res
                
            self.live_news_items = articles
            self.refresh_news_table()
        except Exception as e:
            self.notify(f"News error: {e}", severity="error")

    def update_news_widget(self, n):
        self.live_news_items.insert(0, n)
        self.live_news_items = self.live_news_items[:25]
        self.refresh_news_table()

    def refresh_news_table(self):
        try:
            table = self.query_one("#news_table", DataTable)
            table.clear(columns=True)
            table.add_columns("Time", "Source", "Headline", "Tickers")
            
            for n in self.live_news_items:
                created_at = n.get("created_at") if isinstance(n, dict) else getattr(n, "created_at", None)
                source = n.get("source") if isinstance(n, dict) else getattr(n, "source", "News")
                headline = n.get("headline") if isinstance(n, dict) else getattr(n, "headline", "-")
                symbols = n.get("symbols", []) if isinstance(n, dict) else getattr(n, "symbols", [])
                
                symbols_str = "-"
                if symbols:
                    symbols_str = ", ".join(symbols[:3])
                    if len(symbols) > 3:
                        symbols_str += ", ..."
                        
                time_str = str(created_at)[11:16] if created_at else "-"
                
                table.add_row(
                    Text(time_str, style="dim", justify="left"),
                    Text(str(source).upper(), style="cyan", justify="left"),
                    Text(str(headline), justify="left"),
                    Text(symbols_str, style="bold green", justify="left")
                )
        except Exception:
            pass

    async def on_unmount(self):
        if self.streamer:
            self.streamer.stop()
        if self.news_streamer:
            self.news_streamer.stop()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_symbol_btn":
            inp = self.query_one("#new_symbol_input", Input)
            await self.action_add_symbol(inp.value.upper().strip())
            inp.value = ""
            
        elif event.button.id == "remove_symbol_btn":
            inp = self.query_one("#new_symbol_input", Input)
            sym = inp.value.upper().strip()
            if not sym:
                try:
                    table = self.query_one("#markets_table", DataTable)
                    if table.cursor_row < len(self.market_table_symbols):
                        sym = self.market_table_symbols[table.cursor_row]
                except Exception:
                    pass
            if sym:
                await self.action_remove_symbol(sym)
                inp.value = ""
            
        elif event.button.id == "preset_tech_btn":
            for s in ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]:
                if s not in self.symbols:
                    self.symbols.append(s)
                    config.add_to_watchlist(s)
            self.load_markets()
            self.notify("Added Tech MegaCaps to watchlist.", severity="information")

        elif event.button.id == "preset_indices_btn":
            for s in ["SPY", "QQQ", "DIA", "IWM"]:
                if s not in self.symbols:
                    self.symbols.append(s)
                    config.add_to_watchlist(s)
            self.load_markets()
            self.notify("Added Major Indices to watchlist.", severity="information")

        elif event.button.id == "preset_crypto_btn":
            for s in ["BTC/USD", "ETH/USD"]:
                if s not in self.symbols:
                    self.symbols.append(s)
                    config.add_to_watchlist(s)
            self.load_markets()
            self.notify("Added Crypto pairs to watchlist.", severity="information")

        elif event.button.id == "filter_news_btn":
            sym = self.query_one("#news_symbol_input", Input).value.upper().strip()
            if sym:
                self.load_news(symbols=sym)
                self.notify(f"Filtered news for {sym}", severity="information")
            else:
                self.load_news()
                self.notify("Loaded latest market news", severity="information")

        elif event.button.id == "refresh_news_btn":
            self.load_news()
            self.notify("Refreshed latest market news", severity="information")

        elif event.button.id == "clear_news_btn":
            self.query_one("#news_symbol_input", Input).value = ""
            self.load_news()
            self.notify("Cleared news filter", severity="information")

        elif event.button.id == "clear_log_btn":
            try:
                self.query_one("#execution_log_drawer", Log).clear()
                self.notify("Activity log cleared", severity="information")
            except Exception:
                pass

        elif event.button.id == "refresh_portfolio_btn":
            self.load_portfolio()
            self.notify("Refreshed portfolio details", severity="information")

        elif event.button.id == "liquidate_all_btn":
            try:
                client = get_trading_client()
                client.close_all_positions()
                self.notify("Liquidating all open positions...", title="Portfolio Liquidation", severity="warning")
                self.load_portfolio()
            except Exception as e:
                self.notify(f"Liquidate all failed: {e}", severity="error")
                
        elif event.button.id == "clear_trade_btn":
            self.clear_trade_form()

        elif event.button.id == "cancel_all_orders_btn":
            try:
                client = get_trading_client()
                client.cancel_orders()
                self.notify("Cancelled all open orders", title="Orders Cancelled", severity="warning")
                self.load_orders()
            except Exception as e:
                self.notify(f"Cancel all failed: {e}", severity="error")

        elif event.button.id == "submit_trade_btn":
            try:
                sym = self.query_one("#trade_symbol", Input).value.upper().strip()
                if not sym:
                    raise ValueError("Symbol is required")
                    
                client = get_trading_client()
                try:
                    asset = client.get_asset(sym)
                    if not getattr(asset, "tradable", True):
                        raise ValueError(f"Symbol '{sym}' is not currently tradable.")
                except Exception:
                    raise ValueError(f"Invalid symbol '{sym}'. Asset does not exist on Alpaca.")

                qty_str = self.query_one("#trade_qty", Input).value
                if not qty_str:
                    raise ValueError("Quantity is required")
                qty = float(qty_str)
                side = self.query_one("#trade_side", Select).value
                otype = self.query_one("#trade_type", Select).value
                tif = self.query_one("#trade_tif", Select).value
                
                limit_str = self.query_one("#trade_limit_price", Input).value
                limit_px = float(limit_str) if limit_str else None
                
                bracket_mode = self.query_one("#trade_bracket_mode", Select).value
                tp_str = self.query_one("#trade_tp", Input).value.strip()
                sl_str = self.query_one("#trade_sl", Input).value.strip()
                
                # Fetch live market snapshot price if bracket parameters are provided
                cur_px = None
                if tp_str or sl_str:
                    try:
                        snap_client = get_stock_data_client()
                        snap = snap_client.get_stock_snapshot(StockSnapshotRequest(symbol_or_symbols=[sym]))
                        if sym in snap:
                            if snap[sym].latest_trade:
                                cur_px = float(snap[sym].latest_trade.price)
                            elif snap[sym].previous_daily_bar:
                                cur_px = float(snap[sym].previous_daily_bar.close)
                    except Exception:
                        pass
                
                tp_px = None
                if tp_str:
                    clean_tp = tp_str.replace("$", "").replace("%", "").strip()
                    val = float(clean_tp)
                    if bracket_mode == "percent":
                        if not cur_px:
                            raise ValueError(f"Unable to fetch live price for {sym} to calculate percentage bracket.")
                        pct = abs(val) / 100.0
                        if side == "buy":
                            tp_px = round(cur_px * (1.0 + pct), 2)
                        else: # sell (short)
                            tp_px = round(cur_px * (1.0 - pct), 2)
                    else:
                        tp_px = val
                        
                sl_px = None
                if sl_str:
                    clean_sl = sl_str.replace("$", "").replace("%", "").strip()
                    val = float(clean_sl)
                    if bracket_mode == "percent":
                        if not cur_px:
                            raise ValueError(f"Unable to fetch live price for {sym} to calculate percentage bracket.")
                        pct = abs(val) / 100.0
                        if side == "buy":
                            sl_px = round(cur_px * (1.0 - pct), 2)
                        else: # sell (short)
                            sl_px = round(cur_px * (1.0 + pct), 2)
                    else:
                        sl_px = val

                # Validate bracket price thresholds against current market price
                if cur_px:
                    if side == "buy":
                        if tp_px and tp_px <= cur_px:
                            raise ValueError(f"Take Profit (${tp_px:.2f}) must be GREATER than market price (${cur_px:.2f}) for BUY orders.")
                        if sl_px and sl_px >= cur_px:
                            raise ValueError(f"Stop Loss (${sl_px:.2f}) must be LESS than market price (${cur_px:.2f}) for BUY orders.")
                    elif side == "sell":
                        if tp_px and tp_px >= cur_px:
                            raise ValueError(f"Take Profit (${tp_px:.2f}) must be LESS than market price (${cur_px:.2f}) for SELL (short) orders.")
                        if sl_px and sl_px <= cur_px:
                            raise ValueError(f"Stop Loss (${sl_px:.2f}) must be GREATER than market price (${cur_px:.2f}) for SELL (short) orders.")
                
                from alpaca_cli.cli.commands.trading.orders import create_market_order, create_limit_order, submit_order
                from alpaca.trading.enums import OrderSide
                
                aside = OrderSide.BUY if side == "buy" else OrderSide.SELL
                
                if otype == "market":
                    req = create_market_order(sym, side=aside, qty=qty, tif=tif, take_profit=tp_px, stop_loss=sl_px)
                else:
                    if not limit_px:
                        raise ValueError("Limit price required for limit orders")
                    req = create_limit_order(sym, side=aside, qty=qty, limit_price=limit_px, tif=tif, take_profit=tp_px, stop_loss=sl_px)
                    
                order_res = submit_order(req)
                if order_res is None:
                    raise ValueError("Order rejected by Alpaca API. Please verify order parameters and price thresholds.")
                    
                bracket_info = ""
                if tp_px or sl_px:
                    bracket_info = f" (TP: ${tp_px:.2f}" if tp_px else ""
                    if sl_px:
                        bracket_info += f", SL: ${sl_px:.2f})" if bracket_info else f" (SL: ${sl_px:.2f})"
                    else:
                        bracket_info += ")"
                        
                self.notify(f"Order for {qty} shares of {sym} submitted successfully!{bracket_info}", title="Trade Executed", severity="information")
                self.clear_trade_form()
                self.load_orders()
            except Exception as e:
                self.notify(f"Trade Error: {e}", title="Order Failed", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = event.data_table
        if table.id == "orders_table":
            if event.cursor_row < len(self.current_orders):
                order = self.current_orders[event.cursor_row]
                self.push_screen(OrderInfoModal(order))
        elif table.id == "portfolio_table":
            if event.cursor_row < len(self.current_positions):
                pos = self.current_positions[event.cursor_row]
                self.push_screen(PositionModal(pos))
        elif table.id == "markets_table":
            if event.cursor_row < len(self.market_table_symbols):
                sym = self.market_table_symbols[event.cursor_row]
                try:
                    client = get_trading_client()
                    asset = client.get_asset(sym)
                    self.push_screen(AssetInfoModal(asset))
                except Exception as e:
                    self.notify(f"Asset Info error: {e}", severity="error")
        elif table.id == "news_table":
            if event.cursor_row < len(self.live_news_items):
                article = self.live_news_items[event.cursor_row]
                self.push_screen(NewsReaderModal(article))

    def clear_trade_form(self):
        for input_id in ["#trade_symbol", "#trade_qty", "#trade_limit_price", "#trade_tp", "#trade_sl"]:
            try:
                self.query_one(input_id, Input).value = ""
            except Exception:
                pass

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "new_symbol_input":
            await self.action_add_symbol(event.value.upper().strip())
            event.input.value = ""
        elif event.input.id == "news_symbol_input":
            sym = event.value.upper().strip()
            if sym:
                self.load_news(symbols=sym)
                self.notify(f"Filtered news for {sym}", severity="information")
            else:
                self.load_news()

    async def action_add_symbol(self, sym: str) -> None:
        if sym and sym not in self.symbols:
            try:
                if "/" in sym:
                    crypto_client = get_crypto_data_client()
                    snap = crypto_client.get_crypto_snapshot(CryptoSnapshotRequest(symbol_or_symbols=[sym]))
                else:
                    client = get_stock_data_client()
                    snap = client.get_stock_snapshot(StockSnapshotRequest(symbol_or_symbols=[sym]))
                if sym not in snap or not snap[sym].latest_trade:
                    raise ValueError("No trade data found")
            except Exception:
                self.notify(f"Ticker '{sym}' not found or no data available.", severity="error")
                return

            self.symbols.append(sym)
            config.add_to_watchlist(sym)
            self.load_markets()
            self.notify(f"Added {sym} to watchlist.", severity="information")
            self.log_event(f"Added {sym} to market watchlist.", "info")

    async def action_remove_symbol(self, sym: str) -> None:
        if sym in self.symbols:
            self.symbols.remove(sym)
            config.remove_from_watchlist(sym)
            self.load_markets()
            self.notify(f"Removed {sym} from watchlist.", severity="information")
        elif sym:
            self.notify(f"{sym} not in watchlist.", severity="error")

    async def on_asset_selected(self, event: AssetSelected):
        try:
            client = get_trading_client()
            asset = client.get_asset(event.symbol)
            self.push_screen(AssetInfoModal(asset))
        except Exception as e:
            self.notify(f"Could not load asset info: {e}", severity="error")
