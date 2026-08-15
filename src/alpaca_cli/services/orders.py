from typing import Optional
from alpaca.trading.requests import TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderClass

def _build_bracket_params(
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    stop_loss_limit: Optional[float] = None,
) -> dict:
    """Build bracket order parameters (take profit and stop loss)."""
    params = {}
    if take_profit is not None:
        params["take_profit"] = TakeProfitRequest(limit_price=take_profit)
    if stop_loss is not None:
        params["stop_loss"] = StopLossRequest(
            stop_price=stop_loss, limit_price=stop_loss_limit
        )
    # Set order_class when bracket params are present
    if params:
        params["order_class"] = OrderClass.BRACKET
    return params


from alpaca_cli.api.client import get_trading_client
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest

def submit_trade(symbol: str, qty: float, side: str, order_type: str, time_in_force: str, limit_price: Optional[float] = None):
    client = get_trading_client()
    req_args = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "time_in_force": time_in_force
    }
    if order_type.lower() == "market":
        req = MarketOrderRequest(**req_args)
    else:
        if limit_price is None:
            raise ValueError("limit_price is required for limit orders")
        req_args["limit_price"] = limit_price
        req = LimitOrderRequest(**req_args)
    return client.submit_order(req)
