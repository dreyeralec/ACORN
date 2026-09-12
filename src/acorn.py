import logging
import time

from ibapi.contract import Contract
from ibapi.order import Order

from pandas import DataFrame

from src.ai import call_trading_model, call_analysis_model, AIServiceError
from src.util import is_valid_nyse_ticker
from src.telegram import tel_notify, tel_send_trade, tel_get_updates, TelegramServiceError
from src.gateway import connect_ib_gateway

logger = logging.getLogger(__name__)


def _get_portfolio_data() -> DataFrame:
    """Fetch portfolio data and return as a DataFrame.
    
        Returns:
            Dataframe of portfolio positions.
    """
    gate = connect_ib_gateway()
    gate.reqPositions()
    return gate.positions


def _get_portfolio_json() -> str:
    """Fetch current portfolio positions as a JSON string.
    
        Returns:
            String of portfolio positions.
    """
    return _get_portfolio_data().to_json(orient="records")


def wait_res(wait: int) -> str | None:
    """Wait for response from telegram for specified amount of minutes.

        Args:
            Wait: Minutes ACORN should wait for a response.

        Returns:
            User's response as a string, or None if timed out. 
    """
    offset = None
    secs = wait * 60
    while secs > 0:
        time.sleep(1)
        secs -= 1
        data = tel_get_updates(offset)
        for update in data["result"]:
            offset = update["update_id"] + 1
            message = update["message"]
            if "message" not in update:
                continue

            return message["text"]
    return None

#probably could make this better but works for now
def eval_user_res(res: str | None) -> bool:
    """Process the user's telegram message in response to a trading recommendation.
    
        Args:
            response: String of the user's response.

        Returns:
            If the user confirmed or denied the recommendation.
    """
    if res is None:
        return False
    if "yes" in res.lower():
        return True
    return False


def get_user_approval(symbol: str, action: str, quantity: int, order_type: str, limit_price: float | None, reasoning: str, act: int, totalActs: int) -> bool:
    """Send trade recommendation information to user and wait for their approval.

        Args:
            symbol: Security's ticker.
            action: BUY or SELL.
            quantity: Number of shares/contracts.
            order_type: IB order type (MKT, LMT, etc.).
            limit_price:Limit price, if applicable.
            reasoning: Model's thesis for the trade.
            act: Index of the current action.
            totalActs: Amount of total actions model is recommending.
    
        Returns:
            The user's decision on the trade recommendation.
    """
    try:
        tel_send_trade(symbol, action, quantity, order_type, limit_price, reasoning, act, totalActs)
        userRes = wait_res(10)
        return eval_user_res(userRes)
    except TelegramServiceError as e:
        logger.error(f"Couldn't reach Telegram, decision defaulting to NO")
        return False

            
def trade_dec(portfolio_data: str) -> None:
    """Get a trading decision from the model and act on the recommendation.
    
        Args:
            portfolio_data: String of portfolio positions.
    """
    try:
        tradingDecision = call_trading_model(portfolio_data)
    except AIServiceError as e:
        logger.warning(f"Trading model returned no decision:\n{e}")
        return
    
    totalActs = len(tradingDecision.actions)
    for act, a in enumerate(tradingDecision.actions, start=1):
        if a.action == "HOLD":
            logger.info(f"Holding {a.symbol}")
            tel_notify(f"ACORN chose to hold {a.symbol}\n\n{act} of {totalActs}")
        else:
            stage_action(a.symbol, a.action, a.quantity, a.order_type, a.limit_price, a.reasoning, act, totalActs)


def eod_analysis(portfolio_data: str) -> None:
    """Run end of day analysis report and send to telegram.
    
        Args:
            portfolio_data: String of portfolio positions.
    """
    try:
        res = call_analysis_model(portfolio_data)
    except AIServiceError as e:
        logger.warning(f"Analysis model returned no response:\n{e}")
        return
    tel_notify(res)


def make_contract(symbol: str, sec_type: str = "STK", exchange: str = "SMART", currency: str = "USD") -> Contract:
    """Create IB Contract object.

        Args:
            symbol: Ticker symbol (AAPL, NVDA, etc.).
            sec_type: Securities supported: STK, OPT, FUT, CASH (forex), CFD.
            exchange: Exchange supported SMART.
            currency: Currency supported USD.

        Returns:
            IB Contract object.

        Raises:
            ValueError: An argument was invalid or not supported.
    """
    if not is_valid_nyse_ticker(symbol):
        logger.warning(f"Caught an invalid ticker {symbol} while trying to build a contract")
        raise ValueError(f"Invalid ticker {symbol}")
    if sec_type not in ["STK", "OPT", "FUT", "CASH", "CFD"]:
        logger.warning(f"Caught an invalid or unsupported security type {sec_type} while trying to build a contract")
        raise ValueError(f"Invalid or unsupported security type {sec_type}")
    if exchange != "SMART":
        logger.warning(f"Caught invalid or unsupported exchange type {exchange} while trying to build a contract")
        raise ValueError(f"Invalid or unsupported exchange type {exchange}")
    if currency != "USD":
        logger.warning(f"Caught invalid or unsupported currency type {currency} while trying to build a contract")
        raise ValueError(f"Invalid or unsupported currency type {currency}")
    
    c = Contract()
    c.symbol = symbol
    c.secType = sec_type
    c.exchange = exchange
    c.currency = currency
    return c


def make_order(action: str, order_type: str, limit_price: float | None, quantity: int) -> Order:
    """Create IB Market order object

        Args:
            action: Supported actions BUY, SELL.
            order_type: Supported order types MKT, LMT, STP, STP LMT, MIT, LIT, MOC, LOC, MTL.
            limit_price: Price per security.
            quantity: Amount of shares/contracts > 0.

        Returns:
            IB Order object.

        Raises:
            ValueError: An argument was invalid or not supported.
    """
    if action not in ["BUY", "SELL"]:
        logger.warning(f"Caught an invalid action {action} while trying to build an order")
        raise ValueError(f"Invalid or unsupported action {action}")
    if order_type not in ["MKT", "LMT", "STP", "STP LMT", "MIT", "LIT", "MOC", "LOC", "MTL"]:
        logger.warning(f"Caught an invalid order type {order_type} while trying to build an order")
        raise ValueError(f"Invalid or unsupported order type {order_type}")
    if quantity < 0:
        logger.warning(f"Caught an invalid quantity {quantity} while trying to build an order")
        raise ValueError(f"Invalid quantity {quantity}")

    requires_limit_price = order_type in ["LMT", "STP LMT", "LIT"]        
    
    o = Order()
    o.action = action # "BUY" or "SELL"
    o.orderType = order_type
    o.totalQuantity = quantity
    o.eTradeOnly = False # avoid deprecated-field errors on recent API versions
    o.firmQuoteOnly = False
    if requires_limit_price:
        if limit_price is None:
            logger.warning(f"Order type {order_type} requires a limit price but none was given")
            raise ValueError(f"Order type {order_type} requires a limit price")
        o.lmtPrice = limit_price
    return o


def stage_action(symbol: str, action: str, quantity: int, order_type: str, limit_price: float | None, reasoning: str, act: int, totalActs: int) -> None:
    """Get user approval, then place trade.
    
        Args:
            symbol: Security's ticker.
            action: BUY or SELL.
            quantity: Number of shares/contracts.
            order_type: IB order type (MKT, LMT, etc.).
            limit_price:Limit price, if applicable.
            reasoning: Model's thesis for the trade.
            act: Index of the current action.
            totalActs: Amount of total actions model is recommending.
        
        Raises:
            ValueError: A contract or order contained a bad value.
            RuntimeError: Contract or order was not created.
    """
    if (get_user_approval(symbol, action, quantity, order_type, limit_price, reasoning, act, totalActs)):
        place_trade(symbol, action, quantity, order_type, limit_price)
    else:
        logger.info(f"Discarded {action} order on {symbol}")
        tel_notify(f"Discarded {action} order on {symbol}")


def place_trade(symbol: str, action: str, quantity: int, order_type: str, limit_price: float | None) -> None:
    """Build and place an order, notify user of the outcome.
        
        Args:
            symbol: Security's ticker.
            action: BUY or SELL.
            quantity: Number of shares/contracts.
            order_type: IB order type (MKT, LMT, etc.).
            limit_price: Price for one security.
        
        Raises:
            ValueError: A contract or order contained a bad value.
            RuntimeError: contract or order was not created.
    """
    try:
        contract = make_contract(symbol)
        order = make_order(action, order_type, limit_price, quantity)
        submit_order(contract, order)
        logger.info(f"Performed {action} on {symbol}")
        tel_notify(f"{action} {symbol} succeeded")
    except ValueError as e:
        logger.error(f"ACORN rejected an order:\n\n{e}")
        tel_notify(f"ACORN rejected an order:\n\n{e}")
    except RuntimeError as e:
        logger.error(f"ACORN hit a runtime error:\n\n{e}")
        tel_notify(f"ACORN hit a runtime error:\n\n{e}")


def submit_order(contract: Contract, order: Order) -> None:
    """Places an order with the IB Gateway.

        Args:
            contract: IB Contract object.
            order: IB Order object.

        Raises:
            RuntimeError: contract or order was None, or gateway rejected the order.
    """
    if contract is None or order is None:
        raise RuntimeError(f"contract or order is None. Contract: {contract} Order: {order}")

    gateway = connect_ib_gateway()
    order_id = gateway.get_next_order_id()
    try:
        gateway.placeOrder(order_id, contract, order)
    except Exception:
        raise RuntimeError(f"Failed to place order {order.action} {contract.symbol}")


def dispatch_acorn(event: str) -> None:
    """ACORN's core processing. Fetch portfolio data and respond to the event.

        Args:
            event: event ACORN is responding to (open, noon, eod)
    """
    portfolio_data = _get_portfolio_json()

    if event in ("open", "noon"):
        trade_dec(portfolio_data)
    elif event == "eod":
        eod_analysis(portfolio_data)
    else:
        logger.warning(f"Unrecognized event type {event}")