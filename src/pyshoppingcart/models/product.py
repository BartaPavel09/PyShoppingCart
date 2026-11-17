"""Product domain model for PyShoppingCart."""

from __future__ import annotations

from typing import Any

from pyshoppingcart.exceptions import (
    InsufficientStockError,
    InvalidPriceError,
    InvalidQuantityError,
)


class Product:
    """Represents an item in the store's inventory catalog.

    Invariants:
      - price_cents must be an integer > 0 (monetary values strictly in cents).
      - stock must be an integer >= 0.
    """

    def __init__(
        self,
        id: str,
        name: str,
        price_cents: int,
        stock: int,
        category: str = "General",
    ) -> None:
        if not isinstance(price_cents, int) or price_cents <= 0:
            raise InvalidPriceError(price_cents)
        if not isinstance(stock, int) or stock < 0:
            raise InvalidQuantityError(stock)

        self.id: str = str(id)
        self.name: str = str(name).strip()
        self.price_cents: int = price_cents
        self.stock: int = stock
        self.category: str = str(category).strip()

    def has_stock(self, requested_quantity: int) -> bool:
        """Check whether sufficient inventory exists to satisfy requested quantity."""
        if requested_quantity <= 0:
            return False
        return self.stock >= requested_quantity

    def deduct_stock(self, quantity: int, simulate_race_delay: float = 0.0) -> None:
        """Deduct inventory stock.

        When simulate_race_delay > 0, widens the read-modify-write gap to test race conditions.

        Raises:
            InvalidQuantityError: If quantity is <= 0.
            InsufficientStockError: If requested quantity exceeds available stock.
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise InvalidQuantityError(quantity)
        if quantity > self.stock:
            raise InsufficientStockError(self.id, quantity, self.stock)

        current_stock = self.stock
        if simulate_race_delay > 0.0:
            import time
            time.sleep(simulate_race_delay)
        self.stock = current_stock - quantity

    def restock(self, quantity: int) -> None:
        """Add inventory stock.

        Raises:
            InvalidQuantityError: If quantity is <= 0.
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise InvalidQuantityError(quantity)
        self.stock += quantity

    def to_dict(self) -> dict[str, Any]:
        """Convert product state to dictionary for JSON serialization."""
        return {
            "__type__": "Product",
            "id": self.id,
            "name": self.name,
            "price_cents": self.price_cents,
            "stock": self.stock,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Product:
        """Construct Product instance from dictionary (alternative constructor)."""
        return cls(
            id=data["id"],
            name=data["name"],
            price_cents=int(data["price_cents"]),
            stock=int(data["stock"]),
            category=data.get("category", "General"),
        )

    def __eq__(self, other: object) -> bool:
        """Equality based on product ID and core properties."""
        if isinstance(other, Product):
            return self.id == other.id and self.name == other.name and self.price_cents == other.price_cents
        return False

    def __hash__(self) -> int:
        """Hash based on immutable identity (id)."""
        return hash(self.id)

    def __repr__(self) -> str:
        return (
            f"Product(id={self.id!r}, name={self.name!r}, "
            f"price_cents={self.price_cents}, stock={self.stock}, category={self.category!r})"
        )

    def __str__(self) -> str:
        dollars = self.price_cents / 100
        return f"[{self.id}] {self.name} (${dollars:.2f}) - Stock: {self.stock}"
