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


