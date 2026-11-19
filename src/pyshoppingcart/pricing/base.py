"""Base discount policy protocol and ABC for PyShoppingCart."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pyshoppingcart.models.cart import Cart


class DiscountPolicy(ABC):
    """Abstract base class for all pricing and promotional discount policies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name or promotional code for the discount."""
        pass

    @abstractmethod
    def is_applicable(self, cart: Cart, current_balance_cents: int) -> bool:
        """Determine whether the policy applies to the given cart state."""
        pass

    @abstractmethod
    def calculate_discount(self, cart: Cart, current_balance_cents: int) -> int:
        """Calculate discount amount in integer cents.

        Args:
            cart: The active cart being priced.
            current_balance_cents: The remaining payable balance in cents before this discount.

        Returns:
            The calculated discount in integer cents (must be >= 0).
        """
        pass
