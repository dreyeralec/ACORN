from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading
import queue
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Wrapper for handling callback functions called by the gateway connection
# custom functionality can be added here
class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.next_order_id = None
        self.connected_event = threading.Event()
        self.data_queue = queue.Queue(0)   # hand data off to your main thread
        self.positions = pd.DataFrame([], columns = ['Account', 'Symbol', 'Quantity', 'Average Cost'])
        self.account_values = {}
        self.open_orders = {}
        self.net_liquid = None
        self.lock = threading.Lock()

    # ---- Connection lifecycle ----
    # called on init
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId) # preserve original nextValidId() base functionality
        with self.lock:
            self.next_order_id = orderId
        self.connected_event.set()
        logger.info(f"Connected. Next order ID: {orderId}")

    def get_next_order_id(self):
        with self.lock:
            if self.next_order_id is not None:
                oid = self.next_order_id
                self.next_order_id += 1
                return oid
            else:
                logger.error("next_order_id is null in get_next_order_id()")
                raise RuntimeError("next_order_id is null in get_next_order_id()")

    def connectionClosed(self):
        logger.warning("Connection closed — need reconnect logic here")
        self.connected_event.clear()

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        # Codes 2104, 2106, 2158 etc. are informational, not errors
        if errorCode in (2104, 2106, 2158):
            logger.info(f"Info: {errorString}")
        else:
            logger.error(f"Error {errorCode} (reqId {reqId}): {errorString}")

    # ---- Order/account callbacks ----
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        logger.info(f"Order {orderId}: {status}, filled={filled}, avgPrice={avgFillPrice}")
        with self.lock:
            self.open_orders[orderId] = status

    def position(self, account, contract, position, avgCost):
        with self.lock:
            index = str(account) + str(contract.symbol)
            self.positions.loc[index] = account, contract.symbol, position, avgCost

    def positionEnd(self):
        return super().positionEnd()

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        if key == "NetLiquidation":
            self.net_liquid = val
        return super().updateAccountValue(key, val, currency, accountName)

    # ---- Market data ----
    def tickPrice(self, reqId, tickType, price, attrib):
        self.data_queue.put(("tick", reqId, tickType, price))

    def historicalData(self, reqId, bar):
        print(f"reqId={reqId} {bar.date} O:{bar.open} H:{bar.high} "
            f"L:{bar.low} C:{bar.close} V:{bar.volume}")
        self.data_queue.put(("bar", reqId, bar))

    def historicalDataEnd(self, reqId, start, end):
        print(f"Historical data complete for reqId {reqId}: {start} to {end}")
        self.data_queue.put(("bars_done", reqId))