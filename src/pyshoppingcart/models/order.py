"""Order domain model for PyShoppingCart.

Represents an immutable, confirmed transaction record created upon checkout.
Distinct from the temporary, mutable Cart state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class OrderStatus(str, Enum):
    """Lifecycle status for a store order."""
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class OrderItem:
    """Immutable snapshot of a purchased line item."""
    product_id: str
    product_name: str
    unit_price_cents: int
    quantity: int
    subtotal_cents: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "unit_price_cents": self.unit_price_cents,
            "quantity": self.quantity,
            "subtotal_cents": self.subtotal_cents,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrderItem:
        return cls(
            product_id=data["product_id"],
            product_name=data["product_name"],
            unit_price_cents=int(data["unit_price_cents"]),
            quantity=int(data["quantity"]),
            subtotal_cents=int(data["subtotal_cents"]),
        )


class Order:
    """Immutable confirmed order snapshot.

    Guarantees:
      - Once created, items and prices cannot be modified.
      - Total is strictly integer cents and cannot be negative.
    """

    def __init__(
        self,
        id: str,
        customer_id: str,
        items: list[OrderItem] | tuple[OrderItem, ...],
        subtotal_cents: int,
        discount_cents: int,
        total_cents: int,
        discount_notes: list[str] | tuple[str, ...] | None = None,
        created_at: str | None = None,
        status: OrderStatus | str = OrderStatus.CONFIRMED,
    ) -> None:
        self.id: str = str(id)
        self.customer_id: str = str(customer_id)
        self.items: tuple[OrderItem, ...] = tuple(items)
        self.subtotal_cents: int = subtotal_cents
        self.discount_cents: int = discount_cents
        self.total_cents: int = max(0, total_cents)
        self.discount_notes: tuple[str, ...] = tuple(discount_notes or ())
        self.created_at: str = created_at or datetime.now(timezone.utc).isoformat()
        self.status: OrderStatus = (
            status if isinstance(status, OrderStatus) else OrderStatus(status)
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert Order instance to dictionary for JSON persistence."""
        return {
            "__type__": "Order",
            "id": self.id,
            "customer_id": self.customer_id,
            "items": [item.to_dict() for item in self.items],
            "subtotal_cents": self.subtotal_cents,
            "discount_cents": self.discount_cents,
            "total_cents": self.total_cents,
            "discount_notes": list(self.discount_notes),
            "created_at": self.created_at,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Order:
        """Construct Order from dictionary representation."""
        items = tuple(
            item_data if isinstance(item_data, OrderItem) else OrderItem.from_dict(item_data)
            for item_data in data["items"]
        )
        return cls(
            id=data["id"],
            customer_id=data["customer_id"],
            items=items,
            subtotal_cents=int(data["subtotal_cents"]),
            discount_cents=int(data["discount_cents"]),
            total_cents=int(data["total_cents"]),
            discount_notes=tuple(data.get("discount_notes", ())),
            created_at=data.get("created_at"),
            status=OrderStatus(data.get("status", "CONFIRMED")),
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Order):
            return self.id == other.id and self.total_cents == other.total_cents
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return (
            f"Order(id={self.id!r}, customer_id={self.customer_id!r}, "
            f"total_cents={self.total_cents}, status={self.status.value!r})"
        )

    def __str__(self) -> str:
        dollars = self.total_cents / 100
        return (
            f"Order #{self.id} | Customer: {self.customer_id} | "
            f"Total: ${dollars:.2f} ({len(self.items)} items) | Status: {self.status.value}"
        )
