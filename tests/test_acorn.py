import pytest

from ibapi.contract import Contract
from ibapi.order import Order
from acorn import (
    make_contract,
    make_order,
    safely_place_order,
    get_portfolio_data,
    stage_action,
    wait_response,
    handle_response,
    handle_event,
)

def test_make_valid_contract():
    c = Contract()
    c.symbol = "AAPL"
    c.secType = "STK"
    c.exchange = "SMART"
    c.currency = "USD"
    t = make_contract("AAPL")
    assert c == t


def test_make_invalid_contract_ticker():
    t = "NVIDIA"
    with pytest.raises(ValueError, match=f"Invalid ticker {t}"):
        make_contract(t)


def test_make_invalid_contract_sec_type():
    t = "NVDA"
    st = "LOAN"
    with pytest.raises(ValueError, match=f"Invalid or unsupported security type {st}"):
        make_contract(symbol=t, sec_type=st)


def test_make_invalid_contract_exchange():
    t = "PLTR"
    et = "GARAGE SALE"
    with pytest.raises(ValueError, match=f"Invalid or unsupported exchange type {et}"):
        make_contract(symbol=t, exchange=et)


def test_make_invalid_contract_currency():
    t = "MSFT"
    c = "EURO"
    with pytest.raises(ValueError, match=f"Invalid or unsupported currency type {c}"):
        make_contract(symbol=t, currency=c)


def test_make_valid_action():
    o = Order()
    o.action = "BUY"
    o.orderType = "MKT"
    o.totalQuantity = 2
    t = make_order("BUY", "MKT", 2)
    assert o == t


def test_make_invalid_order_action():
    a = "STEAL"
    ot = "MKT"
    q = 2
    with pytest.raises(ValueError, match=f"Invalid or unsupported action {a}"):
        make_order(a, ot, q)


def test_make_invalid_order_type():
    a = "BUY"
    ot = ""
    q = 2
    with pytest.raises(ValueError, match=f"Invalid or unsupported order type {ot}"):
        make_order(a, ot, q)


def test_make_invalid_order_quantity():
    a = "SELL"
    ot = "MKT"
    q = -2
    with pytest.raises(ValueError, match=f"Invalid quantity {q}"):
        make_order(a, ot, q)


def test_handle_response_yes():
    assert handle_response("Yes") is True
    assert handle_response("yes please") is True


def test_handle_response_no():
    assert handle_response("no") is False
    assert handle_response("") is False