"""Customer domain model for PyShoppingCart."""

from __future__ import annotations

from typing import Any


class Customer:
    """Represents a store customer."""

    def __init__(self, id: str, name: str, email: str) -> None:
        self.id: str = str(id).strip()
        self.name: str = str(name).strip()
        self.email: str = str(email).strip().lower()

    def to_dict(self) -> dict[str, Any]:
        """Convert Customer instance to dictionary for JSON persistence."""
        return {
            "__type__": "Customer",
            "id": self.id,
            "name": self.name,
            "email": self.email,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Customer:
        """Construct Customer instance from dictionary representation."""
        return cls(
            id=data["id"],
            name=data["name"],
            email=data["email"],
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Customer):
            return self.id == other.id and self.email == other.email
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"Customer(id={self.id!r}, name={self.name!r}, email={self.email!r})"

    def __str__(self) -> str:
        return f"Customer {self.name} <{self.email}> (ID: {self.id})"
