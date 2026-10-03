import os
import requests
import logging

from dotenv import load_dotenv
from requests import RequestException

logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_KEY")


class TelegramServiceError(Exception):
    """Raised if telegram service encounters an error."""
    pass


class TelegramClient:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.token = token
        self.offset = None

    def _post(self, endpoint: str, payload: dict) -> None:
        """Helper for posting to the Telegram API."""
        try:
            res = self.session.post(
                f"https://api.telegram.org/bot{TOKEN}/{endpoint}",
                json=payload,
                timeout=10
            )
            res.raise_for_status()
        except RequestException as e:
            raise TelegramServiceError(f"Telegram API call to {endpoint} failed:\n{e}") from e


    def _sync_telegram_offset(self) -> None:
        """Set offset variable to next telegram offset."""
        response = self.session.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={"offset": -1, "timeout": 0}
        )
        response.raise_for_status()
        updates = response.json()["result"]
        if updates:
            self.offset = updates[-1]["update_id"] + 1
        else:
            self.offset = None


    def tel_notify(self, message: str) -> None:
        """Send a string to the user.
        
            Args:
                message: string to send to the user.
        """
        try:
            self._post("sendMessage", {"chat_id": 8837613504, "text": message})
        except TelegramServiceError as e:
            logger.error(f"Failed to send Telegram notification: {e}")


    def tel_send_trade(self, symbol: str, action: str, quantity: int, order_type: str, limit_price: float | None, reasoning: str, act: int, totalActs: int) -> None:
        """Send a trade action to the user.

            Args:
                symbol: Security's ticker.
                action: BUY or SELL.
                quantity: Number of shares/contracts.
                order_type: IB order type (MKT, LMT, etc.).
                limit_price:Limit price, if applicable.
                reasoning: Model's thesis for the trade.
                act: Index of the current action.
                totalActs: Amount of total actions model is recommending.
        """
        price = limit_price if "LMT" in order_type else "Market price"
        content = (
            f"ACORN staged to execute action:"
            f"\nAction: {action}"
            f"\nTicker: {symbol}"
            f"\nOrder type: {order_type}"
            f"\nQuantity: {quantity}"
            f"\nPrice: {price}"
            f"\n\nACORN's reasoning:\n{reasoning}"
            "\n\nWould you like to procede (YES/NO)?"
            f"\n\n {act} of {totalActs}"
        )
        self._post("sendMessage", {"chat_id": 8837613504, "text": content})


    def tel_get_response(self) -> str | None:
        """Start longpolling with telegram api, timeout 5 minutes."""
        try:
            if self.offset is None:
                self._sync_telegram_offset()
            res = self.session.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"timeout": 3000, "offset": self.offset})
            res.raise_for_status()
            data = res.json()
            for update in data["result"]:
                self.offset = update["update_id"] + 1
                if "message" not in update:
                    continue
                message = update["message"]
                if "text" not in message: 
                    continue
                return message["text"]

        except RequestException as e:
            raise TelegramServiceError(f"Telegram API call to getUpdates failed:\n{e}") from e


def _get_telegram_client() -> TelegramClient:
    """Return telegram client singleton.
    
        Returns:
            Telegram client instance.
    """
    if TOKEN is None:
        raise TelegramServiceError("Couldn't get telegram api key")
    return TelegramClient(TOKEN)


telegram_client = _get_telegram_client()