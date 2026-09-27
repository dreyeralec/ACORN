import pytest

from src.ai import call_trading_model, call_analysis_model
from src.acorn import _get_account_portfolio_json
from src.util import is_valid_ticker


def test_call_trading_model():
    port = _get_account_portfolio_json() # build some fake data instead of this
    res = call_trading_model(port)
    assert res is not None
    assert res.confidence in ["low", "medium", "high"]
    assert res.halt_trading is not None
    assert len(res.overall_reasoning) > 0
    for action in res.actions:
        assert is_valid_ticker(action.symbol)


def test_call_analysis_model():
    port = _get_account_portfolio_json() # build some fake data instead of this
    res = call_analysis_model(port)
    assert res is not None
    assert len(res) > 0



    # write tests for error messages