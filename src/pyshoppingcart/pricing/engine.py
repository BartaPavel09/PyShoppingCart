"""Pricing engine for PyShoppingCart.

Orchestrates discount policies, defines stacking precedence, and enforces the non-negative
price invariant (totals never drop below 0 cents).
"""

from __future__ import annotations

from dataclasses import dataclass

from pyshoppingcart.models.cart import Cart
from pyshoppingcart.pricing.base import DiscountPolicy
from pyshoppingcart.pricing.percentage import PercentageDiscount
from pyshoppingcart.pricing.threshold import BulkThresholdDiscount


@dataclass(frozen=True)
class PricingResult:
    """Immutable result of a cart pricing computation."""
    subtotal_cents: int
    discount_cents: int
    total_cents: int
    applied_discounts: tuple[tuple[str, int], ...]
    discount_notes: tuple[str, ...]

    def __str__(self) -> str:
        sub_usd = self.subtotal_cents / 100
        disc_usd = self.discount_cents / 100
        tot_usd = self.total_cents / 100
        lines = [
            f"Subtotal: ${sub_usd:.2f}",
            f"Discounts: -${disc_usd:.2f}",
            f"Total: ${tot_usd:.2f}",
        ]
        if self.applied_discounts:
            lines.append("Applied Discounts:")
            for name, amount in self.applied_discounts:
                lines.append(f"  - {name}: -${amount / 100:.2f}")
        return "\n".join(lines)


class PricingEngine:
    """Evaluates and combines multiple discount policies sequentially.

    Stacking Rules:
      1. Ordering Precedence:
         - Bulk/Threshold discounts (fixed cent reduction) are evaluated first against gross subtotal.
         - Percentage discounts are evaluated second against the remaining balance.
      2. Floor Invariant:
         - The final payable total is strictly clamped with max(0, balance).
         - Total discount is clamped to min(subtotal_cents, sum_of_discounts).
      3. Integer cents arithmetic exclusively (zero floating point drift).
    """

    def __init__(self, policies: list[DiscountPolicy] | None = None) -> None:
        self.policies: list[DiscountPolicy] = list(policies or [])

    def add_policy(self, policy: DiscountPolicy) -> None:
        """Register a new discount policy."""
        self.policies.append(policy)

    def calculate_pricing(
        self,
        cart: Cart,
        extra_policies: list[DiscountPolicy] | None = None,
    ) -> PricingResult:
        """Calculate complete pricing snapshot for the given cart.

        Args:
            cart: The cart to evaluate.
            extra_policies: Additional policies (e.g. customer-entered promo code).
        """
        subtotal = cart.subtotal_cents
        if subtotal <= 0:
            return PricingResult(
                subtotal_cents=0,
                discount_cents=0,
                total_cents=0,
                applied_discounts=(),
                discount_notes=(),
            )

        all_policies = list(self.policies) + list(extra_policies or [])

        # Sort policies by precedence: BulkThresholdDiscount first, then PercentageDiscount
        sorted_policies = sorted(
            all_policies,
            key=lambda p: 0 if isinstance(p, BulkThresholdDiscount) else (1 if isinstance(p, PercentageDiscount) else 2),
        )

        current_balance = subtotal
        applied: list[tuple[str, int]] = []
        notes: list[str] = []

        for policy in sorted_policies:
            if current_balance <= 0:
                break
            if policy.is_applicable(cart, current_balance):
                discount_amount = policy.calculate_discount(cart, current_balance)
                if discount_amount > 0:
                    # Enforce that discount cannot exceed remaining balance
                    actual_deduction = min(discount_amount, current_balance)
                    current_balance -= actual_deduction
                    applied.append((policy.name, actual_deduction))
                    notes.append(f"{policy.name}: -${actual_deduction / 100:.2f}")

        total_discount = subtotal - current_balance
        final_total = max(0, current_balance)

        return PricingResult(
            subtotal_cents=subtotal,
            discount_cents=total_discount,
            total_cents=final_total,
            applied_discounts=tuple(applied),
            discount_notes=tuple(notes),
        )
