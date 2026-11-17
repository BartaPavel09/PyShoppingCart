"""Domain and application exceptions for PyShoppingCart."""

from __future__ import annotations


class PyShoppingCartError(Exception):
    """Base exception for all PyShoppingCart domain and application errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DomainError(PyShoppingCartError):
    """Base exception for domain invariant and business rule violations."""
    pass


class InsufficientStockError(DomainError):
    """Raised when an operation requests more stock than currently available."""

    def __init__(self, product_id: str, requested: int, available: int) -> None:
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for product '{product_id}': "
            f"requested {requested}, but only {available} available."
        )


class InvalidQuantityError(DomainError):
    """Raised when an invalid item quantity (e.g. <= 0) is specified."""

    def __init__(self, quantity: int) -> None:
        self.quantity = quantity
        super().__init__(f"Quantity must be a positive integer, got {quantity}.")


class InvalidPriceError(DomainError):
    """Raised when an invalid price (e.g. <= 0 cents) is specified."""

    def __init__(self, price_cents: int) -> None:
        self.price_cents = price_cents
        super().__init__(f"Price must be a positive integer in cents, got {price_cents}.")


class EmptyCartError(DomainError):
    """Raised when checkout is attempted on an empty shopping cart."""

    def __init__(self, customer_id: str) -> None:
        self.customer_id = customer_id
        super().__init__(f"Cannot checkout empty cart for customer '{customer_id}'.")


class EntityNotFoundError(PyShoppingCartError):
    """Raised when a requested entity cannot be found in the store catalog/repository."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with ID '{entity_id}' not found.")


class DiscountError(DomainError):
    """Raised when an invalid discount configuration or rule is encountered."""
    pass
