"""JSON file persistence repository for PyShoppingCart store state.

Provides clean serialization and deserialization of catalog inventory,
customer records, active carts, and confirmed orders.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyshoppingcart.models.cart import Cart
from pyshoppingcart.models.customer import Customer
from pyshoppingcart.models.order import Order
from pyshoppingcart.models.product import Product
from pyshoppingcart.persistence.encoder import PyShoppingCartEncoder, domain_object_hook


class JsonStoreRepository:
    """Manages saving and loading store state to and from JSON files."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)

    def save(
        self,
        products: dict[str, Product],
        customers: dict[str, Customer],
        orders: dict[str, Order],
        carts: dict[str, Cart] | None = None,
    ) -> None:
        """Serialize current store state to the JSON file."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "products": [p.to_dict() for p in products.values()],
            "customers": [c.to_dict() for c in customers.values()],
            "orders": [o.to_dict() for o in orders.values()],
            "carts": [c.to_dict() for c in (carts or {}).values()],
        }

        # Write to temp file first then atomic rename to prevent corruption
        temp_file = self.file_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, cls=PyShoppingCartEncoder, indent=2)
        temp_file.replace(self.file_path)

    def load(
        self,
    ) -> tuple[dict[str, Product], dict[str, Customer], dict[str, Order], dict[str, Cart]]:
        """Load and reconstruct store state from the JSON file.

        Returns:
            Tuple of (products, customers, orders, carts) dictionaries keyed by ID.
        """
        if not self.file_path.exists():
            return {}, {}, {}, {}

        with open(self.file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f, object_hook=domain_object_hook)

        products: dict[str, Product] = {}
        for item in raw_data.get("products", []):
            prod = item if isinstance(item, Product) else Product.from_dict(item)
            products[prod.id] = prod

        customers: dict[str, Customer] = {}
        for item in raw_data.get("customers", []):
            cust = item if isinstance(item, Customer) else Customer.from_dict(item)
            customers[cust.id] = cust

        orders: dict[str, Order] = {}
        for item in raw_data.get("orders", []):
            ord_obj = item if isinstance(item, Order) else Order.from_dict(item)
            orders[ord_obj.id] = ord_obj

        carts: dict[str, Cart] = {}
        for item in raw_data.get("carts", []):
            cart_obj = item if isinstance(item, Cart) else Cart.from_dict(item)
            carts[cart_obj.customer_id] = cart_obj

        return products, customers, orders, carts
