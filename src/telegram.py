import os
import requests
import logging

from requests import RequestException

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.environ["TELEGRAM_BOT_KEY"]


class TelegramServiceError(Exception):
    """Raised if telegram service encounters an error"""


def _post(endpoint: str, payload: dict) -> dict:
    """Helper for posting to the Telegram API"""
    try:
        res = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/{endpoint}",
            json=payload,
            timeout=10
        )
        res.raise_for_status()
        return res.json()
    except RequestException as e:
        raise TelegramServiceError(f"Telegram API call to {endpoint} failed:\n{e}")


def tel_notify(message: str):
    try:
        _post("sendMessage", {"chat_id": 8837613504, "text": message})
    except TelegramServiceError as e:
        logger.error(f"Failed to send Telegram notification:\n{e}")


def tel_send_trade(symbol: str, action: str, quantity: int, order_type: str, limit_price: float | None, reasoning: str, act: int, totalActs: int):
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
    _post("sendMessage", {"chat_id": 8837613504, "text": content})


def tel_get_updates(offset=None):
    params = {"timeout": 35}
    if offset is not None:
        params["offset"] = offset
    try:
        res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params=params)
        res.raise_for_status()
        return res.json()
    except RequestException as e:
        raise TelegramServiceError(f"Telegram API call to getUpdates failed:\n{e}")