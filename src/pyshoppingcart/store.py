"""Single Store aggregate managing catalog, carts, orders, and thread-safe checkout."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from pyshoppingcart.exceptions import (
    EmptyCartError,
    EntityNotFoundError,
    InsufficientStockError,
    InvalidQuantityError,
)
from pyshoppingcart.models.cart import Cart
from pyshoppingcart.models.customer import Customer
from pyshoppingcart.models.order import Order, OrderItem, OrderStatus
from pyshoppingcart.models.product import Product
from pyshoppingcart.persistence.json_store import JsonStoreRepository
from pyshoppingcart.pricing.base import DiscountPolicy
from pyshoppingcart.pricing.engine import PricingEngine, PricingResult
from pyshoppingcart.utils.decorators import log_state_transition, timed_operation

logger = logging.getLogger("pyshoppingcart.store")


class Store:
    """The central e-commerce store instance.

    Responsibilities:
      - Catalog inventory management (add/lookup/restock products).
      - Customer registration.
      - Cart management (temporary shopping sessions).
      - Pricing engine coordination.
      - Thread-safe checkout protecting shared stock deductions.
      - State persistence to/from JSON.
    """

    def __init__(
        self,
        name: str = "PyShoppingCart Store",
        persistence_file: str | Path | None = None,
        pricing_engine: PricingEngine | None = None,
    ) -> None:
        self.name: str = name
        self._products: dict[str, Product] = {}
        self._customers: dict[str, Customer] = {}
        self._carts: dict[str, Cart] = {}
        self._orders: dict[str, Order] = {}

        self.pricing_engine: PricingEngine = pricing_engine or PricingEngine()
        self.repository: JsonStoreRepository | None = (
            JsonStoreRepository(persistence_file) if persistence_file else None
        )

        # Thread synchronization primitive protecting critical stock modifications
        self._inventory_lock = threading.Lock()

    # -------------------------------------------------------------------------
    # Product Catalog Management
    # -------------------------------------------------------------------------

    def add_product(self, product: Product) -> None:
        """Register or update a product in the catalog."""
        with self._inventory_lock:
            self._products[product.id] = product

    def get_product(self, product_id: str) -> Product:
        """Retrieve a product by ID. Raises EntityNotFoundError if absent."""
        if product_id not in self._products:
            raise EntityNotFoundError("Product", product_id)
        return self._products[product_id]

    def list_products(self) -> list[Product]:
        """Return a snapshot of all catalog products."""
        with self._inventory_lock:
            return list(self._products.values())

    def restock_product(self, product_id: str, quantity: int) -> None:
        """Restock an existing product under lock."""
        with self._inventory_lock:
            product = self.get_product(product_id)
            product.restock(quantity)

    # -------------------------------------------------------------------------
    # Customer Management
    # -------------------------------------------------------------------------

    def register_customer(self, customer: Customer) -> None:
        """Register a new customer."""
        self._customers[customer.id] = customer

    def get_customer(self, customer_id: str) -> Customer:
        """Retrieve customer by ID. Raises EntityNotFoundError if absent."""
        if customer_id not in self._customers:
            raise EntityNotFoundError("Customer", customer_id)
        return self._customers[customer_id]

    def list_customers(self) -> list[Customer]:
        """Return list of all registered customers."""
        return list(self._customers.values())

    # -------------------------------------------------------------------------
    # Cart Operations
    # -------------------------------------------------------------------------

    def get_or_create_cart(self, customer_id: str) -> Cart:
        """Retrieve the customer's active cart or create a new empty one."""
        self.get_customer(customer_id)  # Validate customer exists
        if customer_id not in self._carts:
            self._carts[customer_id] = Cart(customer_id=customer_id)
        return self._carts[customer_id]

    def add_to_cart(self, customer_id: str, product_id: str, quantity: int = 1) -> Cart:
        """Add product to customer cart with stock validation."""
        cart = self.get_or_create_cart(customer_id)
        product = self.get_product(product_id)
        cart.add_item(product, quantity)
        return cart

    def update_cart_item(self, customer_id: str, product_id: str, quantity: int) -> Cart:
        """Update item quantity in customer cart."""
        cart = self.get_or_create_cart(customer_id)
        product = self.get_product(product_id)
        cart.update_quantity(product_id, quantity, available_stock=product.stock)
        return cart

    def remove_from_cart(self, customer_id: str, product_id: str) -> Cart:
        """Remove product from customer cart."""
        cart = self.get_or_create_cart(customer_id)
        cart.remove_item(product_id)
        return cart

    # -------------------------------------------------------------------------
    # Orders & Checkout (Thread-Safe Critical Section)
    # -------------------------------------------------------------------------

    @timed_operation
    @log_state_transition("Checkout")
    def checkout(
        self,
        customer_id: str,
        extra_policies: list[DiscountPolicy] | None = None,
        use_lock: bool = True,
        simulate_race_delay: float = 0.0,
    ) -> Order:
        """Execute atomic, thread-safe checkout for a customer.

        Critical Section Synchronization:
          - Uses `with self._inventory_lock:` when use_lock=True.
          - Atomically checks available stock for all line items.
          - Atomically deducts inventory stock.
          - Creates an immutable Order snapshot.
          - Clears the temporary cart.

        Args:
            customer_id: Customer performing checkout.
            extra_policies: Optional one-time discounts (e.g. promo code).
            use_lock: If True (default), protects inventory with self._inventory_lock.
                      If False, allows demonstrating concurrency race conditions.
            simulate_race_delay: Artificial sleep (seconds) between stock check and deduction
                                 to widen the race window for concurrency acceptance testing.

        Raises:
            EntityNotFoundError: If customer does not exist.
            EmptyCartError: If the cart has no items.
            InsufficientStockError: If any item in the cart exceeds available stock.
        """
        self.get_customer(customer_id)
        cart = self.get_or_create_cart(customer_id)

        if cart.is_empty:
            raise EmptyCartError(customer_id)

        # Compute final pricing snapshot
        pricing: PricingResult = self.pricing_engine.calculate_pricing(cart, extra_policies)

        # Synchronization helper function
        def _execute_atomic_checkout() -> Order:
            # 1. Validate all items against current stock
            for item in cart.items:
                product = self.get_product(item.product_id)
                if not product.has_stock(item.quantity):
                    raise InsufficientStockError(product.id, item.quantity, product.stock)

            # Optional artificial delay to demonstrate race conditions when unlocked
            if simulate_race_delay > 0.0:
                time.sleep(simulate_race_delay)

            # 2. Deduct stock for all items
            order_items: list[OrderItem] = []
            for item in cart.items:
                product = self.get_product(item.product_id)
                product.deduct_stock(item.quantity, simulate_race_delay=simulate_race_delay)
                order_items.append(
                    OrderItem(
                        product_id=product.id,
                        product_name=product.name,
                        unit_price_cents=item.unit_price_cents,
                        quantity=item.quantity,
                        subtotal_cents=item.subtotal_cents,
                    )
                )

            # 3. Create immutable confirmed Order snapshot
            order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            order = Order(
                id=order_id,
                customer_id=customer_id,
                items=order_items,
                subtotal_cents=pricing.subtotal_cents,
                discount_cents=pricing.discount_cents,
                total_cents=pricing.total_cents,
                discount_notes=pricing.discount_notes,
                status=OrderStatus.CONFIRMED,
            )

            # 4. Save order to store and clear the temporary cart
            self._orders[order.id] = order
            cart.clear()
            return order

        if use_lock:
            with self._inventory_lock:
                return _execute_atomic_checkout()
        else:
            return _execute_atomic_checkout()

    def get_order(self, order_id: str) -> Order:
        """Retrieve confirmed order by ID."""
        if order_id not in self._orders:
            raise EntityNotFoundError("Order", order_id)
        return self._orders[order_id]

    def list_orders(self, customer_id: str | None = None) -> list[Order]:
        """Return list of confirmed orders, optionally filtered by customer."""
        with self._inventory_lock:
            all_orders = list(self._orders.values())
        if customer_id:
            return [o for o in all_orders if o.customer_id == customer_id]
        return all_orders

    # -------------------------------------------------------------------------
    # State Persistence
    # -------------------------------------------------------------------------

    @timed_operation
    def save_state(self, filepath: str | Path | None = None) -> None:
        """Persist complete store state to JSON file."""
        target_repo = JsonStoreRepository(filepath) if filepath else self.repository
        if not target_repo:
            raise ValueError("No persistence file path configured.")
        with self._inventory_lock:
            target_repo.save(
                products=self._products,
                customers=self._customers,
                orders=self._orders,
                carts=self._carts,
            )

    @timed_operation
    def load_state(self, filepath: str | Path | None = None) -> None:
        """Load store state from JSON file."""
        target_repo = JsonStoreRepository(filepath) if filepath else self.repository
        if not target_repo:
            raise ValueError("No persistence file path configured.")
        with self._inventory_lock:
            products, customers, orders, carts = target_repo.load()
            self._products = products
            self._customers = customers
            self._orders = orders
            self._carts = carts
