import os
import requests
import logging

from dotenv import load_dotenv
from requests import RequestException

logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_KEY")


class TelegramServiceError(Exception):
    """Raised if telegram service encounters an error"""
    pass


class TelegramClient:
    def __init__(self, token: str):
        self.token = token
        self.offset = None

    def _post(self, endpoint: str, payload: dict):
        """Helper for posting to the Telegram API"""
        try:
            res = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/{endpoint}",
                json=payload,
                timeout=10
            )
            res.raise_for_status()
        except RequestException as e:
            raise TelegramServiceError(f"Telegram API call to {endpoint} failed:\n{e}")


    def tel_notify(self, message: str):
        try:
            self._post("sendMessage", {"chat_id": 8837613504, "text": message})
        except TelegramServiceError as e:
            logger.error(f"Failed to send Telegram notification:\n{e}")


    def tel_send_trade(self, symbol: str, action: str, quantity: int, order_type: str, limit_price: float | None, reasoning: str, act: int, totalActs: int):
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


    def tel_get_message(self):
        params = {"timeout": 35}
        if self.offset is not None:
            params["offset"] = self.offset
        try:
            res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params=params)
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
            raise TelegramServiceError(f"Telegram API call to getUpdates failed:\n{e}")


def get_telegram_client():
    if TOKEN is None:
        raise TelegramServiceError("Couldn't get telegram api key")
    return TelegramClient(TOKEN)


telegram_client = get_telegram_client()