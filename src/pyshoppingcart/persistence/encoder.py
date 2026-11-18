"""Custom JSON encoder and object hook deserializer for PyShoppingCart."""

from __future__ import annotations

import json
from typing import Any

from pyshoppingcart.models.cart import Cart, CartItem
from pyshoppingcart.models.customer import Customer
from pyshoppingcart.models.order import Order, OrderItem
from pyshoppingcart.models.product import Product


class PyShoppingCartEncoder(json.JSONEncoder):
    """Custom JSON encoder handling domain models via their to_dict() methods."""

    def default(self, obj: Any) -> Any:
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return obj.to_dict()
        if isinstance(obj, (set, tuple)):
            return list(obj)
        return super().default(obj)


def domain_object_hook(data: dict[str, Any]) -> Any:
    """JSON object hook reconstructing domain objects based on their __type__ marker."""
    type_name = data.get("__type__")
    if type_name == "Product":
        return Product.from_dict(data)
    elif type_name == "Customer":
        return Customer.from_dict(data)
    elif type_name == "CartItem":
        return CartItem.from_dict(data)
    elif type_name == "Cart":
        return Cart.from_dict(data)
    elif type_name == "Order":
        return Order.from_dict(data)
    return data
