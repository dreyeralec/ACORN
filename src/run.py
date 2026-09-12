import logging
import time

from src.util import time_to_next_position_update
from src.acorn import dispatch_acorn
from src.gateway import connect_ib_gateway

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_cycle():
    """Run a single event cycle"""
    nextUpdate, event = time_to_next_position_update()
    if nextUpdate > 0:
        logger.info(f"ACORN is dreaming of all the money it wants to make for the next {nextUpdate} seconds")
        time.sleep(nextUpdate)

    logger.info(f"Awoke for {event} event")

    gateway = connect_ib_gateway(port=4002, client_id=1) # paper gateway
    if not gateway.isConnected():
        logger.error("Connection to gateway was not established")
        return
    
    logger.info("Connected to ib gateway")
    dispatch_acorn(event)


def main() -> None:
    while True:
        try:
            run_cycle()
        except ConnectionError as e:
            logger.error(f"Disconnected from IB Gateway unexpectedly or trouble establishing connection:\n\n{e}")
            time.sleep(30)


if __name__ == "__main__":
    main()