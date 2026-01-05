"""Tests for order models."""
import pytest


def test_action_enum():
    from src.models.orders import Action

    assert Action.HOLD.value == "hold"
    assert Action.BUY.value == "buy"
    assert Action.EXIT.value == "exit"


def test_order_creation():
    from src.models.orders import Order

    order = Order(
        strategy_name="value_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="MARKET",
        limit_price=None
    )

    assert order.strategy_name == "value_strategy"
    assert order.symbol == "AAPL"
    assert order.action == "BUY"
    assert order.quantity == 100


def test_order_with_limit():
    from src.models.orders import Order

    order = Order(
        strategy_name="value_strategy",
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="LIMIT",
        limit_price=150.50
    )

    assert order.order_type == "LIMIT"
    assert order.limit_price == 150.50


def test_order_result():
    from src.models.orders import OrderResult

    result = OrderResult(
        order_id=123,
        status="filled",
        fill_price=150.25,
        fill_quantity=100,
        message=None
    )

    assert result.order_id == 123
    assert result.status == "filled"
    assert result.fill_price == 150.25
