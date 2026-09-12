from dotenv import load_dotenv
import os
import requests

load_dotenv()

TOKEN = os.environ["TELEGRAM_BOT_KEY"]


def telegram_send(message: str):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": 8837613504, "text": message}   
    )


def telegram_send_trade(symbol: str, action: str, quantity: int, order_type: str, limit_price: float | None, reasoning: str, act: int, totalActs: int):
    content = f"ACORN staged to execute action:"
    f"\nAction: {action}"
    f"\nTicker: {symbol}"
    f"\nOrder type: {order_type}"
    f"\nQuantity: {quantity}"
    f"\nLimit price: {limit_price if "LMT" in order_type else "Market price"}"
    f"\n\nACORN's reasoning:\n{reasoning}"
    "\n\nWould you like to procede (YES/NO)?"
    f"\n\n {act} of {totalActs}"

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": 8837613504, "text": content}
    )


def get_updates(offset=None):
    params = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params=params)
    return res.json()