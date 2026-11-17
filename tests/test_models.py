"""Unit tests for PyShoppingCart domain models."""

from __future__ import annotations

import pytest

from pyshoppingcart.exceptions import (
    EntityNotFoundError,
    InsufficientStockError,
    InvalidPriceError,
    InvalidQuantityError,
)
from pyshoppingcart.models import Cart, CartItem, Customer, Order, OrderItem, OrderStatus, Product


class TestProductModel:
    def test_product_initialization(self) -> None:
        p = Product("P1", "Keyboard", 10000, 5, "Electronics")
        assert p.id == "P1"
        assert p.name == "Keyboard"
        assert p.price_cents == 10000
        assert p.stock == 5
        assert p.category == "Electronics"

    def test_invalid_price_raises(self) -> None:
        with pytest.raises(InvalidPriceError):
            Product("P1", "Free Item", 0, 5)
        with pytest.raises(InvalidPriceError):
            Product("P1", "Negative Item", -500, 5)

    def test_invalid_stock_raises(self) -> None:
        with pytest.raises(InvalidQuantityError):
            Product("P1", "Item", 1000, -1)

    def test_stock_deduction_and_restock(self) -> None:
        p = Product("P1", "Item", 1000, 10)
        p.deduct_stock(3)
        assert p.stock == 7
        p.restock(5)
        assert p.stock == 12

    def test_deduct_more_than_stock_raises(self) -> None:
        p = Product("P1", "Item", 1000, 2)
        with pytest.raises(InsufficientStockError) as exc_info:
            p.deduct_stock(3)
        assert exc_info.value.requested == 3
        assert exc_info.value.available == 2

    def test_to_dict_and_from_dict(self) -> None:
        p1 = Product("P1", "Monitor", 25000, 4, "Displays")
        data = p1.to_dict()
        p2 = Product.from_dict(data)
        assert p1 == p2
        assert p2.category == "Displays"

    def test_equality_and_hashing(self) -> None:
        p1 = Product("P1", "Desk", 15000, 2)
        p2 = Product("P1", "Desk", 15000, 10)  # Same ID, price, name
        p3 = Product("P2", "Chair", 8000, 5)
        assert p1 == p2
        assert p1 != p3
        s = {p1, p2, p3}
        assert len(s) == 2


class TestCustomerModel:
    def test_customer_creation(self) -> None:
        c = Customer("C1", "Alice", "alice@example.com")
        assert c.id == "C1"
        assert c.name == "Alice"
        assert c.email == "alice@example.com"

    def test_customer_serialization(self) -> None:
        c = Customer("C1", "Bob", "bob@test.com")
        data = c.to_dict()
        c2 = Customer.from_dict(data)
        assert c == c2


class TestCartModel:
    def test_cart_operations(self) -> None:
        cart = Cart("CUST-1")
        p1 = Product("P1", "Pen", 200, 10)
        p2 = Product("P2", "Notebook", 500, 5)

        cart.add_item(p1, quantity=2)
        cart.add_item(p2, quantity=1)

        assert len(cart) == 2
        assert cart.total_items == 3
        assert cart.subtotal_cents == 2 * 200 + 1 * 500  # 900 cents

    def test_add_existing_item_increments_quantity(self) -> None:
        cart = Cart("CUST-1")
        p = Product("P1", "Pen", 200, 10)
        cart.add_item(p, quantity=2)
        cart.add_item(p, quantity=3)
        assert cart.get_item("P1").quantity == 5

    def test_add_exceeding_stock_raises(self) -> None:
        cart = Cart("CUST-1")
        p = Product("P1", "Rare", 1000, 2)
        with pytest.raises(InsufficientStockError):
            cart.add_item(p, quantity=3)

    def test_update_quantity_and_remove(self) -> None:
        cart = Cart("CUST-1")
        p = Product("P1", "Pen", 200, 10)
        cart.add_item(p, 2)
        cart.update_quantity("P1", 4, available_stock=10)
        assert cart.get_item("P1").quantity == 4

        # Setting to 0 removes item
        cart.update_quantity("P1", 0)
        assert cart.get_item("P1") is None
        assert cart.is_empty

    def test_cart_iteration(self) -> None:
        cart = Cart("CUST-1")
        cart.add_item(Product("P1", "Item1", 100, 10), 1)
        cart.add_item(Product("P2", "Item2", 200, 10), 2)
        items = list(cart)
        assert len(items) == 2
        assert all(isinstance(it, CartItem) for it in items)

    def test_cart_clear(self) -> None:
        cart = Cart("CUST-1")
        cart.add_item(Product("P1", "Item1", 100, 10), 1)
        cart.clear()
        assert cart.is_empty
        assert cart.subtotal_cents == 0


class TestOrderModel:
    def test_order_immutability(self) -> None:
        item = OrderItem("P1", "Item1", 500, 2, 1000)
        order = Order(
            id="ORD-1",
            customer_id="C1",
            items=[item],
            subtotal_cents=1000,
            discount_cents=100,
            total_cents=900,
            discount_notes=["Promo: -$1.00"],
            status=OrderStatus.CONFIRMED,
        )
        assert order.id == "ORD-1"
        assert order.total_cents == 900
        assert isinstance(order.items, tuple)

    def test_order_serialization(self) -> None:
        item = OrderItem("P1", "Item1", 500, 2, 1000)
        order = Order(
            id="ORD-1",
            customer_id="C1",
            items=[item],
            subtotal_cents=1000,
            discount_cents=100,
            total_cents=900,
        )
        data = order.to_dict()
        reconstructed = Order.from_dict(data)
        assert order == reconstructed
        assert reconstructed.total_cents == 900
