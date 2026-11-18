"""Unit tests for JSON persistence repository and encoder."""

from __future__ import annotations

from pathlib import Path

from pyshoppingcart.models import Cart, Customer, Order, OrderItem, Product
from pyshoppingcart.persistence import JsonStoreRepository


def test_json_store_save_and_load(tmp_path: Path) -> None:
    file_path = tmp_path / "test_store.json"
    repo = JsonStoreRepository(file_path)

    # Initial empty load
    prods, custs, ords, carts = repo.load()
    assert prods == {}
    assert custs == {}
    assert ords == {}
    assert carts == {}

    # Seed data
    p1 = Product("P1", "Keyboard", 10000, 5, "Electronics")
    p2 = Product("P2", "Mouse", 3000, 10, "Electronics")
    c1 = Customer("C1", "Alice", "alice@example.com")

    cart1 = Cart("C1")
    cart1.add_item(p1, 2)

    order1 = Order(
        id="ORD-01",
        customer_id="C1",
        items=[OrderItem("P1", "Keyboard", 10000, 1, 10000)],
        subtotal_cents=10000,
        discount_cents=1000,
        total_cents=9000,
    )

    products = {p1.id: p1, p2.id: p2}
    customers = {c1.id: c1}
    orders = {order1.id: order1}
    carts_dict = {cart1.customer_id: cart1}

    # Save
    repo.save(products, customers, orders, carts_dict)
    assert file_path.exists()

    # Load and verify roundtrip
    loaded_prods, loaded_custs, loaded_ords, loaded_carts = repo.load()

    assert len(loaded_prods) == 2
    assert loaded_prods["P1"].name == "Keyboard"
    assert loaded_prods["P1"].price_cents == 10000

    assert len(loaded_custs) == 1
    assert loaded_custs["C1"].email == "alice@example.com"

    assert len(loaded_ords) == 1
    assert loaded_ords["ORD-01"].total_cents == 9000
    assert len(loaded_ords["ORD-01"].items) == 1

    assert len(loaded_carts) == 1
    assert loaded_carts["C1"].total_items == 2
