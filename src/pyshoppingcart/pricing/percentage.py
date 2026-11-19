"""Percentage discount policy for PyShoppingCart."""

from __future__ import annotations

from pyshoppingcart.exceptions import DiscountError
from pyshoppingcart.models.cart import Cart
from pyshoppingcart.pricing.base import DiscountPolicy


class PercentageDiscount(DiscountPolicy):
    """Applies a percentage reduction to the remaining payable balance.

    Always computes values in integer cents using standard integer math.
    """

    def __init__(
        self,
        code: str,
        percentage: int,
        minimum_spend_cents: int = 0,
    ) -> None:
        if not (1 <= percentage <= 100):
            raise DiscountError(f"Percentage must be between 1 and 100, got {percentage}.")
        if minimum_spend_cents < 0:
            raise DiscountError(f"Minimum spend cannot be negative, got {minimum_spend_cents}.")

        self.code: str = str(code).strip().upper()
        self.percentage: int = percentage
        self.minimum_spend_cents: int = minimum_spend_cents

    @property
    def name(self) -> str:
        return f"PROMO:{self.code} ({self.percentage}% off)"

    def is_applicable(self, cart: Cart, current_balance_cents: int) -> bool:
        if cart.is_empty:
            return False
        return current_balance_cents >= self.minimum_spend_cents

    def calculate_discount(self, cart: Cart, current_balance_cents: int) -> int:
        if not self.is_applicable(cart, current_balance_cents):
            return 0
        # Integer cents calculation with standard rounding: (balance * percentage + 50) // 100
        discount = (current_balance_cents * self.percentage + 50) // 100
        return min(discount, current_balance_cents)

    def __repr__(self) -> str:
        return f"PercentageDiscount(code={self.code!r}, percentage={self.percentage}%)"
