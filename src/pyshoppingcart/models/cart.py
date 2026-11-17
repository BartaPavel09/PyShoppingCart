"""Shopping Cart domain models for PyShoppingCart.

Maintains temporary user selections prior to checkout.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from pyshoppingcart.exceptions import (
    EntityNotFoundError,
    InsufficientStockError,
    InvalidQuantityError,
)
from pyshoppingcart.models.product import Product


class CartItem:
    """Represents a product and requested quantity inside an active shopping cart."""

    def __init__(
        self,
        product_id: str,
        product_name: str,
        unit_price_cents: int,
        quantity: int,
    ) -> None:
        if quantity <= 0:
            raise InvalidQuantityError(quantity)
        self.product_id: str = str(product_id)
        self.product_name: str = str(product_name)
        self.unit_price_cents: int = unit_price_cents
        self.quantity: int = quantity

    @property
    def subtotal_cents(self) -> int:
        """Compute subtotal for this item in integer cents."""
        return self.unit_price_cents * self.quantity

    def update_quantity(self, new_quantity: int) -> None:
        """Update item quantity."""
        if new_quantity <= 0:
            raise InvalidQuantityError(new_quantity)
        self.quantity = new_quantity

    def to_dict(self) -> dict[str, Any]:
        """Convert CartItem to dictionary for persistence."""
        return {
            "__type__": "CartItem",
            "product_id": self.product_id,
            "product_name": self.product_name,
            "unit_price_cents": self.unit_price_cents,
            "quantity": self.quantity,
            "subtotal_cents": self.subtotal_cents,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CartItem:
        """Construct CartItem from dictionary representation."""
        return cls(
            product_id=data["product_id"],
            product_name=data["product_name"],
            unit_price_cents=int(data["unit_price_cents"]),
            quantity=int(data["quantity"]),
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CartItem):
            return self.product_id == other.product_id and self.quantity == other.quantity
        return False

    def __repr__(self) -> str:
        return (
            f"CartItem(product_id={self.product_id!r}, product_name={self.product_name!r}, "
            f"unit_price_cents={self.unit_price_cents}, quantity={self.quantity})"
        )


class Cart:
    """Represents an active, temporary shopping session for a customer.

    Encapsulates cart operations: adding, updating, removing items, and calculating subtotal.
    Implements the Iterable interface to allow direct item iteration.
    """

    def __init__(self, customer_id: str) -> None:
        self.customer_id: str = str(customer_id)
        self._items: dict[str, CartItem] = {}

    @property
    def is_empty(self) -> bool:
        """Return True if the cart contains zero items."""
        return len(self._items) == 0

    @property
    def total_items(self) -> int:
        """Return total count of physical units in the cart."""
        return sum(item.quantity for item in self._items.values())

    @property
    def subtotal_cents(self) -> int:
        """Calculate total pre-discount cost of all items in integer cents."""
        return sum(item.subtotal_cents for item in self._items.values())

    @property
    def items(self) -> list[CartItem]:
        """Return a copy of the list of cart items."""
        return list(self._items.values())

    def get_item(self, product_id: str) -> CartItem | None:
        """Retrieve a specific CartItem by product ID, or None if not present."""
        return self._items.get(product_id)

    def add_item(self, product: Product, quantity: int = 1) -> None:
        """Add product to the cart or increment quantity if already present.

        Validates available stock limits without yet mutating store inventory.

        Raises:
            InvalidQuantityError: If quantity <= 0.
            InsufficientStockError: If existing quantity + requested quantity exceeds product stock.
        """
        if quantity <= 0:
            raise InvalidQuantityError(quantity)

        current_qty = self._items[product.id].quantity if product.id in self._items else 0
        total_requested = current_qty + quantity

        if not product.has_stock(total_requested):
            raise InsufficientStockError(product.id, total_requested, product.stock)

        if product.id in self._items:
            self._items[product.id].update_quantity(total_requested)
        else:
            self._items[product.id] = CartItem(
                product_id=product.id,
                product_name=product.name,
                unit_price_cents=product.price_cents,
                quantity=quantity,
            )

    def update_quantity(self, product_id: str, new_quantity: int, available_stock: int | None = None) -> None:
        """Update quantity of an existing item in the cart.

        If new_quantity is 0, the item is removed.

        Raises:
            EntityNotFoundError: If product is not in the cart.
            InvalidQuantityError: If new_quantity < 0.
            InsufficientStockError: If available_stock is given and new_quantity > available_stock.
        """
        if product_id not in self._items:
            raise EntityNotFoundError("CartItem", product_id)

        if new_quantity == 0:
            del self._items[product_id]
            return

        if new_quantity < 0:
            raise InvalidQuantityError(new_quantity)

        if available_stock is not None and new_quantity > available_stock:
            raise InsufficientStockError(product_id, new_quantity, available_stock)

        self._items[product_id].update_quantity(new_quantity)

    def remove_item(self, product_id: str) -> None:
        """Remove an item completely from the cart."""
        if product_id not in self._items:
            raise EntityNotFoundError("CartItem", product_id)
        del self._items[product_id]

    def clear(self) -> None:
        """Reset cart to empty state (called automatically upon successful checkout)."""
        self._items.clear()

    def __iter__(self) -> Iterator[CartItem]:
        """Custom iterator over cart items (Lab 2 Iterators pattern)."""
        return iter(list(self._items.values()))

    def __len__(self) -> int:
        """Return the number of distinct products in the cart."""
        return len(self._items)

    def to_dict(self) -> dict[str, Any]:
        """Convert Cart to dictionary for persistence."""
        return {
            "__type__": "Cart",
            "customer_id": self.customer_id,
            "items": [item.to_dict() for item in self._items.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Cart:
        """Reconstruct Cart instance from dictionary."""
        cart = cls(customer_id=data["customer_id"])
        for item_data in data.get("items", []):
            item = item_data if isinstance(item_data, CartItem) else CartItem.from_dict(item_data)
            cart._items[item.product_id] = item
        return cart

    def __repr__(self) -> str:
        return f"Cart(customer_id={self.customer_id!r}, items_count={len(self._items)})"

    def __str__(self) -> str:
        dollars = self.subtotal_cents / 100
        return f"Cart for customer {self.customer_id} ({self.total_items} items, subtotal: ${dollars:.2f})"
